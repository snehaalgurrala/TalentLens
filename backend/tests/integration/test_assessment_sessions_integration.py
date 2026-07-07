"""
Real-Postgres integration/repository tests for assessment session persistence.

Do NOT run this file against a database you care about — see
tests/integration/conftest.py's _clean_tables fixture (truncates every app
table before each test). Run explicitly with a disposable database, e.g.:

    POSTGRES_HOST=localhost POSTGRES_DB=talentlens_test REDIS_HOST=localhost \
        pytest tests/integration/test_assessment_sessions_integration.py

Exercises the full router -> service -> repository -> DB path (unlike
tests/test_assessment_sessions.py, which mocks the service) and asserts
state via a fresh session, proving upserts/uniqueness constraints hold
against real Postgres.
"""
import uuid
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models.assessment_answer import AssessmentAnswer
from app.models.assessment_recording import AssessmentRecording, RecordingStatus
from app.models.assessment_session import AssessmentSession, AssessmentSessionStatus
from app.models.candidate import Candidate
from app.repositories.candidate import CandidateRepository


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


class TestAssessmentSessionLifecyclePersistence:
    async def test_full_lifecycle_persists_to_db(
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

        # Re-posting the same campaign/candidate resumes rather than duplicating.
        resume_res = await client.post(
            "/api/v1/assessment/session",
            json={"campaign_id": campaign_id, "candidate_id": candidate_id},
            headers=headers,
        )
        assert resume_res.status_code == 201
        assert resume_res.json()["id"] == session_id

        progress_res = await client.patch(
            f"/api/v1/assessment/session/{session_id}",
            json={"current_question": 3},
            headers=headers,
        )
        assert progress_res.status_code == 200
        assert progress_res.json()["current_question"] == 3

        answer_res = await client.post(
            f"/api/v1/assessment/session/{session_id}/answers",
            json={"question_number": 1, "answer": "OPTION_A"},
            headers=headers,
        )
        assert answer_res.status_code == 201

        # Upsert: same question_number overwrites, not duplicates.
        answer_res_2 = await client.post(
            f"/api/v1/assessment/session/{session_id}/answers",
            json={"question_number": 1, "answer": "OPTION_C"},
            headers=headers,
        )
        assert answer_res_2.status_code == 201
        assert answer_res_2.json()["answer"] == "OPTION_C"

        recording_res = await client.post(
            f"/api/v1/assessment/session/{session_id}/recordings",
            json={
                "recording_type": "READ_ALOUD",
                "filename": "clip.webm",
                "mime_type": "audio/webm",
                "duration_seconds": 9.5,
                "file_size": 2048,
            },
            headers=headers,
        )
        assert recording_res.status_code == 201
        assert recording_res.json()["status"] == "PENDING"

        complete_res = await client.post(
            f"/api/v1/assessment/session/{session_id}/complete", headers=headers
        )
        assert complete_res.status_code == 200
        assert complete_res.json()["status"] == "COMPLETED"

        # Further mutation is rejected once completed.
        blocked_res = await client.post(
            f"/api/v1/assessment/session/{session_id}/answers",
            json={"question_number": 2, "answer": "OPTION_B"},
            headers=headers,
        )
        assert blocked_res.status_code == 422

        session_uuid = uuid.UUID(session_id)
        db_session_row = (
            await db_session.execute(
                select(AssessmentSession).where(AssessmentSession.id == session_uuid)
            )
        ).scalar_one()
        assert db_session_row.status == AssessmentSessionStatus.COMPLETED
        assert db_session_row.completed_at is not None

        answers = (
            await db_session.execute(
                select(AssessmentAnswer).where(AssessmentAnswer.session_id == session_uuid)
            )
        ).scalars().all()
        assert len(answers) == 1
        assert answers[0].answer == "OPTION_C"

        recordings = (
            await db_session.execute(
                select(AssessmentRecording).where(AssessmentRecording.session_id == session_uuid)
            )
        ).scalars().all()
        assert len(recordings) == 1
        assert recordings[0].storage_path.startswith(f"assessment-recordings/{session_id}/")

        candidate = (
            await db_session.execute(
                select(Candidate).where(Candidate.id == uuid.UUID(candidate_id))
            )
        ).scalar_one()
        assert str(candidate.organization_id) == bootstrapped_admin["org_id"]


class TestUploadRecordingPersistence:
    """Exercises router -> service -> StorageBackend -> real Postgres for the
    audio-upload endpoint specifically. Same dev-DB-truncation hazard as the
    rest of this file — do NOT run without a disposable database (see module
    docstring above)."""

    async def test_upload_stores_bytes_and_marks_uploaded(
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
        body = upload_res.json()
        assert body["status"] == "UPLOADED"
        assert body["uploaded_at"] is not None

        session_uuid = uuid.UUID(session_id)
        recording = (
            await db_session.execute(
                select(AssessmentRecording).where(
                    AssessmentRecording.session_id == session_uuid
                )
            )
        ).scalar_one()
        assert recording.status == RecordingStatus.UPLOADED
        assert recording.uploaded_at is not None
        assert recording.file_size == len(audio_bytes)

        stored_file = Path(settings.LOCAL_STORAGE_PATH) / recording.storage_path
        assert stored_file.read_bytes() == audio_bytes
        stored_file.unlink()
