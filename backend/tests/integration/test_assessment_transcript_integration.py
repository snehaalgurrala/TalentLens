"""
Real-Postgres integration tests for the async transcription pipeline.

Do NOT run this file against a database you care about — see
tests/integration/conftest.py's _clean_tables fixture (truncates every app
table before each test). Run explicitly with a disposable database, e.g.:

    POSTGRES_HOST=localhost POSTGRES_DB=talentlens_test REDIS_HOST=localhost \
        pytest tests/integration/test_assessment_transcript_integration.py

Exercises the repository -> service -> DB path for AssessmentTranscript, and
runs the Celery task's async body (_run_transcribe_recording) directly
against a real Postgres connection with SpeechService mocked — the real
openai-whisper model is never loaded, matching this project's "never load
real Whisper in tests" rule.
"""
import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.ai.speech.schemas import TranscriptionResult
from app.models.assessment_recording import AssessmentRecording, RecordingStatus
from app.models.assessment_transcript import AssessmentTranscript, TranscriptStatus
from app.models.candidate import Candidate
from app.repositories.assessment_transcript import AssessmentTranscriptRepository
from app.repositories.candidate import CandidateRepository
from app.workers.speech_transcription import _run_transcribe_recording


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


class TestAssessmentTranscriptRepositoryPersistence:
    """Exercises AssessmentTranscriptRepository directly against real Postgres."""

    async def test_create_and_get_by_recording_id(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        campaign_id = await _create_campaign(client, bootstrapped_admin, "Backend Engineer")
        candidate_id = await _create_candidate(
            db_session, bootstrapped_admin["org_id"], "ada@example.com"
        )
        headers = bootstrapped_admin["headers"]

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
        recording_id = uuid.UUID(upload_res.json()["id"])

        repo = AssessmentTranscriptRepository(db_session)
        org_id = uuid.UUID(bootstrapped_admin["org_id"])

        created = await repo.create(recording_id, org_id, status=TranscriptStatus.PENDING)
        await db_session.commit()
        assert created.status == TranscriptStatus.PENDING

        fetched = await repo.get_by_recording_id(recording_id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.organization_id == org_id

        updated = await repo.update(
            fetched, status=TranscriptStatus.COMPLETED, transcript="hello world"
        )
        await db_session.commit()
        assert updated.status == TranscriptStatus.COMPLETED
        assert updated.transcript == "hello world"

        row = (
            await db_session.execute(
                select(AssessmentTranscript).where(AssessmentTranscript.recording_id == recording_id)
            )
        ).scalar_one()
        assert row.status == TranscriptStatus.COMPLETED


class TestTranscribeRecordingTaskPersistence:
    """Runs the Celery task's async body directly against real Postgres,
    with SpeechService mocked so no real Whisper model is ever loaded."""

    async def test_full_pipeline_persists_completed_transcript(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        campaign_id = await _create_campaign(client, bootstrapped_admin, "Backend Engineer")
        candidate_id = await _create_candidate(
            db_session, bootstrapped_admin["org_id"], "grace@example.com"
        )
        headers = bootstrapped_admin["headers"]

        create_res = await client.post(
            "/api/v1/assessment/session",
            json={"campaign_id": campaign_id, "candidate_id": candidate_id},
            headers=headers,
        )
        assert create_res.status_code == 201, create_res.text
        session_id = create_res.json()["id"]

        audio_bytes = b"fake-webm-audio-bytes"
        upload_res = await client.post(
            f"/api/v1/assessment/session/{session_id}/recordings/READ_ALOUD/upload",
            files={"file": ("clip.webm", audio_bytes, "audio/webm")},
            data={"duration_seconds": "9.5"},
            headers=headers,
        )
        assert upload_res.status_code == 201, upload_res.text
        recording_id = uuid.UUID(upload_res.json()["id"])

        class _FakeStorage:
            async def load(self, storage_path: str) -> bytes:
                return audio_bytes

        class _FakeSpeechService:
            async def transcribe(self, data: bytes, *, mime_type: str, filename: str | None = None):
                return TranscriptionResult(
                    transcript="the quick brown fox",
                    language="en",
                    duration_seconds=9.5,
                    processing_time_seconds=0.42,
                    model_name="base",
                    confidence=0.95,
                    segments=[],
                )

        await _run_transcribe_recording(
            str(recording_id),
            _speech_service=_FakeSpeechService(),
            _storage=_FakeStorage(),
        )

        transcript_row = (
            await db_session.execute(
                select(AssessmentTranscript).where(AssessmentTranscript.recording_id == recording_id)
            )
        ).scalar_one()
        assert transcript_row.status == TranscriptStatus.COMPLETED
        assert transcript_row.transcript == "the quick brown fox"
        assert transcript_row.language == "en"
        assert transcript_row.model_name == "base"
        assert transcript_row.processing_time_ms == 420
        assert transcript_row.organization_id == uuid.UUID(bootstrapped_admin["org_id"])

        recording_row = (
            await db_session.execute(
                select(AssessmentRecording).where(AssessmentRecording.id == recording_id)
            )
        ).scalar_one()
        assert recording_row.status == RecordingStatus.UPLOADED

        candidate_row = (
            await db_session.execute(select(Candidate).where(Candidate.id == uuid.UUID(candidate_id)))
        ).scalar_one()
        assert str(candidate_row.organization_id) == bootstrapped_admin["org_id"]
