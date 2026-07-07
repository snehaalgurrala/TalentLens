"""
Real-Postgres integration tests for the deterministic Read Aloud analysis
pipeline.

Do NOT run this file against a database you care about — see
tests/integration/conftest.py's _clean_tables fixture (truncates every app
table before each test). Run explicitly with a disposable database, e.g.:

    POSTGRES_HOST=localhost POSTGRES_DB=talentlens_test REDIS_HOST=localhost \
        pytest tests/integration/test_assessment_analysis_integration.py

Exercises the repository -> service -> DB path for AssessmentAnalysis, and
runs the Celery task's async body (_run_analyze_read_aloud) directly against
a real Postgres connection. No LLM, no Whisper — analysis is pure
deterministic text comparison, so nothing needs to be mocked out for "never
load a real model in tests" the way speech tests do.
"""
import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models.assessment_analysis import AnalysisStatus, AnalysisType, AssessmentAnalysis
from app.models.assessment_transcript import AssessmentTranscript, TranscriptStatus
from app.repositories.assessment_analysis import AssessmentAnalysisRepository
from app.repositories.assessment_transcript import AssessmentTranscriptRepository
from app.repositories.candidate import CandidateRepository
from app.workers.communication_analysis import _run_analyze_read_aloud


async def _create_campaign(client: AsyncClient, admin: dict, title: str) -> str:
    res = await client.post(
        "/api/v1/campaigns/",
        json={"title": title, "description": "Hiring"},
        headers=admin["headers"],
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def _create_candidate(db_session, org_id: str, email: str) -> str:
    candidate = await CandidateRepository(db_session).create(
        organization_id=uuid.UUID(org_id),
        first_name="Ada",
        last_name="Lovelace",
        email=email,
    )
    await db_session.commit()
    return str(candidate.id)


async def _create_session_and_upload_recording(
    client: AsyncClient, admin: dict, campaign_id: str, candidate_id: str
) -> str:
    headers = admin["headers"]
    create_res = await client.post(
        "/api/v1/assessment/session",
        json={"campaign_id": campaign_id, "candidate_id": candidate_id},
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    session_id = create_res.json()["id"]

    upload_res = await client.post(
        f"/api/v1/assessment/session/{session_id}/recordings/READ_ALOUD/upload",
        files={"file": ("clip.webm", b"fake-webm-audio-bytes", "audio/webm")},
        data={"duration_seconds": "9.5"},
        headers=headers,
    )
    assert upload_res.status_code == 201, upload_res.text
    return upload_res.json()["id"]


class TestAssessmentAnalysisRepositoryPersistence:
    """Exercises AssessmentAnalysisRepository directly against real Postgres."""

    async def test_create_and_get_by_transcript_id(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        campaign_id = await _create_campaign(client, bootstrapped_admin, "Backend Engineer")
        candidate_id = await _create_candidate(
            db_session, bootstrapped_admin["org_id"], "ada@example.com"
        )
        recording_id = uuid.UUID(
            await _create_session_and_upload_recording(
                client, bootstrapped_admin, campaign_id, candidate_id
            )
        )
        org_id = uuid.UUID(bootstrapped_admin["org_id"])

        transcript_repo = AssessmentTranscriptRepository(db_session)
        transcript = await transcript_repo.create(
            recording_id,
            org_id,
            status=TranscriptStatus.COMPLETED,
            transcript="the quick brown fox",
        )
        await db_session.commit()

        analysis_repo = AssessmentAnalysisRepository(db_session)
        created = await analysis_repo.create(
            transcript.id,
            org_id,
            analysis_type=AnalysisType.READ_ALOUD,
            status=AnalysisStatus.PENDING,
        )
        await db_session.commit()
        assert created.status == AnalysisStatus.PENDING

        fetched = await analysis_repo.get_by_transcript_id(transcript.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.organization_id == org_id

        updated = await analysis_repo.update(
            fetched, status=AnalysisStatus.COMPLETED, overall_score=100.0
        )
        await db_session.commit()
        assert updated.status == AnalysisStatus.COMPLETED
        assert updated.overall_score == 100.0

        row = (
            await db_session.execute(
                select(AssessmentAnalysis).where(
                    AssessmentAnalysis.transcript_id == transcript.id
                )
            )
        ).scalar_one()
        assert row.status == AnalysisStatus.COMPLETED


class TestAnalyzeReadAloudTaskPersistence:
    """Runs the Celery task's async body directly against real Postgres."""

    async def test_full_pipeline_persists_completed_analysis(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        campaign_id = await _create_campaign(client, bootstrapped_admin, "Backend Engineer")
        candidate_id = await _create_candidate(
            db_session, bootstrapped_admin["org_id"], "grace@example.com"
        )
        recording_id = uuid.UUID(
            await _create_session_and_upload_recording(
                client, bootstrapped_admin, campaign_id, candidate_id
            )
        )
        org_id = uuid.UUID(bootstrapped_admin["org_id"])

        transcript_repo = AssessmentTranscriptRepository(db_session)
        transcript = await transcript_repo.create(
            recording_id,
            org_id,
            status=TranscriptStatus.COMPLETED,
            transcript=settings.READ_ALOUD_REFERENCE_SENTENCE,
        )
        await db_session.commit()

        await _run_analyze_read_aloud(str(transcript.id), 9.5)

        analysis_row = (
            await db_session.execute(
                select(AssessmentAnalysis).where(
                    AssessmentAnalysis.transcript_id == transcript.id
                )
            )
        ).scalar_one()
        assert analysis_row.status == AnalysisStatus.COMPLETED
        assert analysis_row.overall_score == 100.0
        assert analysis_row.word_accuracy == 100.0
        assert analysis_row.organization_id == org_id

    async def test_transcript_not_completed_is_skipped(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        campaign_id = await _create_campaign(client, bootstrapped_admin, "Backend Engineer")
        candidate_id = await _create_candidate(
            db_session, bootstrapped_admin["org_id"], "linus@example.com"
        )
        recording_id = uuid.UUID(
            await _create_session_and_upload_recording(
                client, bootstrapped_admin, campaign_id, candidate_id
            )
        )
        org_id = uuid.UUID(bootstrapped_admin["org_id"])

        transcript_repo = AssessmentTranscriptRepository(db_session)
        transcript = await transcript_repo.create(
            recording_id, org_id, status=TranscriptStatus.PROCESSING
        )
        await db_session.commit()

        await _run_analyze_read_aloud(str(transcript.id), 9.5)

        result = await db_session.execute(
            select(AssessmentTranscript).where(AssessmentTranscript.id == transcript.id)
        )
        assert result.scalar_one() is not None

        analysis_result = await db_session.execute(
            select(AssessmentAnalysis).where(AssessmentAnalysis.transcript_id == transcript.id)
        )
        assert analysis_result.scalar_one_or_none() is None
