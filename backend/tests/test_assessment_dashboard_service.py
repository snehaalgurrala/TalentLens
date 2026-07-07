"""Direct unit tests for AssessmentDashboardService, using mocked repositories
rather than mocking the service itself — mirrors test_assessment_session_service.py.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.assessment_analysis import AnalysisStatus, AnalysisType, AssessmentAnalysis
from app.models.assessment_recording import AssessmentRecording, RecordingStatus, RecordingType
from app.models.assessment_session import (
    AssessmentSection,
    AssessmentSession,
    AssessmentSessionStatus,
)
from app.models.assessment_transcript import AssessmentTranscript, TranscriptStatus
from app.models.communication_assessment import (
    CommunicationAssessment,
    CommunicationAssessmentStatus,
)
from app.models.user import User, UserRole
from app.services.assessment_dashboard import AssessmentDashboardService

_ORG_ID = uuid.uuid4()


def make_user(role: UserRole = UserRole.RECRUITER, org_id: uuid.UUID | None = _ORG_ID) -> User:
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        full_name="Test User",
        password_hash="$2b$12$irrelevant",
        role=role,
        org_id=org_id,
        is_active=True,
        refresh_token_hash=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_session(**overrides) -> AssessmentSession:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        org_id=_ORG_ID,
        campaign_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        current_section=AssessmentSection.APTITUDE,
        current_question=1,
        status=AssessmentSessionStatus.IN_PROGRESS,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentSession(**defaults)


def make_recording(**overrides) -> AssessmentRecording:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        recording_type=RecordingType.READ_ALOUD,
        filename="clip.webm",
        mime_type="audio/webm",
        duration_seconds=12.5,
        storage_path="assessment-recordings/x/read_aloud/y.webm",
        file_size=4096,
        status=RecordingStatus.UPLOADED,
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentRecording(**defaults)


def make_transcript(**overrides) -> AssessmentTranscript:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        recording_id=uuid.uuid4(),
        status=TranscriptStatus.COMPLETED,
        transcript="The quick brown fox.",
        language="en",
        model_name="whisper-base",
        processing_time_ms=1200,
        segment_count=1,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentTranscript(**defaults)


def make_analysis(**overrides) -> AssessmentAnalysis:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        transcript_id=uuid.uuid4(),
        analysis_type=AnalysisType.READ_ALOUD,
        status=AnalysisStatus.COMPLETED,
        overall_score=91.0,
        word_accuracy=95.0,
        correct_words=18,
        missing_words=1,
        extra_words=0,
        substituted_words=1,
        total_words=20,
        reading_speed_wpm=140.0,
        completion_percentage=95.0,
        semantic_similarity=None,
        keyword_coverage=None,
        analysis_json=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentAnalysis(**defaults)


def make_communication_assessment(**overrides) -> CommunicationAssessment:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        assessment_session_id=uuid.uuid4(),
        status=CommunicationAssessmentStatus.COMPLETED,
        overall_score=85.0,
        reading_score=90.0,
        listening_score=80.0,
        confidence_score=88.0,
        strengths_json=["Reads clearly and accurately"],
        improvements_json=["Speaking pace slightly fast"],
        summary_json={"overview": "Great job."},
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return CommunicationAssessment(**defaults)


def make_service(**repo_overrides) -> AssessmentDashboardService:
    defaults = dict(
        session_repo=MagicMock(),
        recording_repo=MagicMock(),
        transcript_repo=MagicMock(),
        analysis_repo=MagicMock(),
        communication_assessment_repo=MagicMock(),
        campaign_repo=MagicMock(),
        candidate_repo=MagicMock(),
    )
    defaults.update(repo_overrides)
    return AssessmentDashboardService(**defaults)


# ── get_full ─────────────────────────────────────────────────────────────────


class TestGetFull:
    async def test_session_not_found(self):
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=None)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_full(uuid.uuid4(), make_user())
        assert exc_info.value.status_code == 404

    async def test_no_recordings_yet(self):
        session = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session)
        recording_repo = MagicMock()
        recording_repo.list_by_session = AsyncMock(return_value=[])
        communication_assessment_repo = MagicMock()
        communication_assessment_repo.get_by_session_id = AsyncMock(return_value=None)
        service = make_service(
            session_repo=session_repo,
            recording_repo=recording_repo,
            communication_assessment_repo=communication_assessment_repo,
        )

        result = await service.get_full(session.id, make_user())

        assert result.session.id == session.id
        assert result.recordings == []
        assert result.communication_assessment is None

    async def test_full_chain_recording_transcript_analysis(self):
        session = make_session()
        recording = make_recording(session_id=session.id, recording_type=RecordingType.READ_ALOUD)
        transcript = make_transcript(recording_id=recording.id)
        analysis = make_analysis(transcript_id=transcript.id, analysis_type=AnalysisType.READ_ALOUD)
        comm_assessment = make_communication_assessment(assessment_session_id=session.id)

        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session)
        recording_repo = MagicMock()
        recording_repo.list_by_session = AsyncMock(return_value=[recording])
        transcript_repo = MagicMock()
        transcript_repo.get_by_recording_id = AsyncMock(return_value=transcript)
        analysis_repo = MagicMock()
        analysis_repo.get_by_transcript_id = AsyncMock(return_value=analysis)
        communication_assessment_repo = MagicMock()
        communication_assessment_repo.get_by_session_id = AsyncMock(return_value=comm_assessment)

        service = make_service(
            session_repo=session_repo,
            recording_repo=recording_repo,
            transcript_repo=transcript_repo,
            analysis_repo=analysis_repo,
            communication_assessment_repo=communication_assessment_repo,
        )

        result = await service.get_full(session.id, make_user())

        assert len(result.recordings) == 1
        detail = result.recordings[0]
        assert detail.recording.id == recording.id
        assert detail.reference_sentence
        assert detail.transcript.id == transcript.id
        assert detail.analysis.id == analysis.id
        assert result.communication_assessment.id == comm_assessment.id

    async def test_recording_without_transcript_yet(self):
        session = make_session()
        recording = make_recording(session_id=session.id, recording_type=RecordingType.LISTEN_REPEAT)

        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session)
        recording_repo = MagicMock()
        recording_repo.list_by_session = AsyncMock(return_value=[recording])
        transcript_repo = MagicMock()
        transcript_repo.get_by_recording_id = AsyncMock(return_value=None)
        analysis_repo = MagicMock()
        analysis_repo.get_by_transcript_id = AsyncMock()
        communication_assessment_repo = MagicMock()
        communication_assessment_repo.get_by_session_id = AsyncMock(return_value=None)

        service = make_service(
            session_repo=session_repo,
            recording_repo=recording_repo,
            transcript_repo=transcript_repo,
            analysis_repo=analysis_repo,
            communication_assessment_repo=communication_assessment_repo,
        )

        result = await service.get_full(session.id, make_user())

        detail = result.recordings[0]
        assert detail.transcript is None
        assert detail.analysis is None
        analysis_repo.get_by_transcript_id.assert_not_called()


# ── get_recording_audio ──────────────────────────────────────────────────────


class TestGetRecordingAudio:
    async def test_session_not_found(self):
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=None)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_recording_audio(uuid.uuid4(), RecordingType.READ_ALOUD, make_user())
        assert exc_info.value.status_code == 404

    async def test_recording_not_uploaded_yet(self):
        session = make_session()
        recording = make_recording(status=RecordingStatus.PENDING)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session)
        recording_repo = MagicMock()
        recording_repo.get_by_session_and_type = AsyncMock(return_value=recording)
        service = make_service(session_repo=session_repo, recording_repo=recording_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_recording_audio(session.id, RecordingType.READ_ALOUD, make_user())
        assert exc_info.value.status_code == 404

    async def test_returns_uploaded_recording(self):
        session = make_session()
        recording = make_recording(status=RecordingStatus.UPLOADED)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session)
        recording_repo = MagicMock()
        recording_repo.get_by_session_and_type = AsyncMock(return_value=recording)
        service = make_service(session_repo=session_repo, recording_repo=recording_repo)

        result = await service.get_recording_audio(session.id, RecordingType.READ_ALOUD, make_user())
        assert result.id == recording.id


# ── get_session_by_candidate ─────────────────────────────────────────────────


class TestGetSessionByCandidate:
    async def test_campaign_not_found(self):
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=None)
        service = make_service(campaign_repo=campaign_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_session_by_candidate(uuid.uuid4(), uuid.uuid4(), make_user())
        assert exc_info.value.status_code == 404

    async def test_candidate_not_found(self):
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=MagicMock())
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=None)
        service = make_service(campaign_repo=campaign_repo, candidate_repo=candidate_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_session_by_candidate(uuid.uuid4(), uuid.uuid4(), make_user())
        assert exc_info.value.status_code == 404

    async def test_no_session_yet(self):
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=MagicMock())
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=MagicMock())
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=None)
        service = make_service(
            campaign_repo=campaign_repo, candidate_repo=candidate_repo, session_repo=session_repo
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.get_session_by_candidate(uuid.uuid4(), uuid.uuid4(), make_user())
        assert exc_info.value.status_code == 404

    async def test_returns_session(self):
        session = make_session()
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=MagicMock())
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=MagicMock())
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=session)
        service = make_service(
            campaign_repo=campaign_repo, candidate_repo=candidate_repo, session_repo=session_repo
        )

        result = await service.get_session_by_candidate(
            session.candidate_id, session.campaign_id, make_user()
        )
        assert result.id == session.id

    async def test_requires_org(self):
        service = make_service()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_session_by_candidate(
                uuid.uuid4(), uuid.uuid4(), make_user(org_id=None)
            )
        assert exc_info.value.status_code == 422
