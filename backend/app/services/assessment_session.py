"""AssessmentSessionService — backend persistence for a candidate's assessment
attempt (aptitude answers + read-aloud/listen-repeat recording metadata).

No AI, no transcription, no scoring, no Celery: this sprint only creates,
resumes, updates progress on, and completes a session. Every method takes
either a recruiter/admin `User` (RequireRoles, org-scoped via `_require_org`)
or, for `upload_recording` only, a bare `org_id` — the one call the candidate's
own browser makes directly, authorized instead via their invitation token (see
`assessment_sessions.py`'s `resolve_recording_upload_org_id`), since candidates
have no platform account. Every other method here stays recruiter-only, same
access model as candidate_profile.py's notes/tasks/activity endpoints.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import HTTPException, UploadFile, status

from app.models.assessment_recording import RecordingStatus, RecordingType
from app.models.assessment_session import AssessmentSection, AssessmentSessionStatus
from app.storage.base import StorageBackend

if TYPE_CHECKING:
    from app.models.assessment_answer import AssessmentAnswer
    from app.models.assessment_recording import AssessmentRecording
    from app.models.assessment_session import AssessmentSession
    from app.models.user import User
    from app.repositories.assessment_answer import AssessmentAnswerRepository
    from app.repositories.assessment_recording import AssessmentRecordingRepository
    from app.repositories.assessment_session import AssessmentSessionRepository
    from app.repositories.campaign import CampaignRepository
    from app.repositories.candidate import CandidateRepository
    from app.schemas.assessment_session import (
        AssessmentAnswerCreate,
        AssessmentRecordingCreate,
        AssessmentSessionCreate,
        AssessmentSessionProgressUpdate,
    )

logger = logging.getLogger(__name__)

# First aptitude question a freshly created session lands on.
_INITIAL_QUESTION_NUMBER = 1

# Audio-upload validation (distinct from MAX_RECORDING_SIZE_MB, which is only
# a sanity ceiling on the metadata-only endpoint's *claimed* file_size).
_ALLOWED_RECORDING_MIME_TYPES = {"audio/webm", "audio/ogg"}
_MAX_RECORDING_UPLOAD_MB = 10
_EXT_BY_MIME = {"audio/webm": ".webm", "audio/ogg": ".ogg"}


class AssessmentSessionService:
    def __init__(
        self,
        session_repo: AssessmentSessionRepository,
        answer_repo: AssessmentAnswerRepository,
        recording_repo: AssessmentRecordingRepository,
        campaign_repo: CampaignRepository,
        candidate_repo: CandidateRepository,
        storage: StorageBackend,
    ) -> None:
        self.session_repo = session_repo
        self.answer_repo = answer_repo
        self.recording_repo = recording_repo
        self.campaign_repo = campaign_repo
        self.candidate_repo = candidate_repo
        self.storage = storage

    # ── Internal guards ───────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage assessment sessions.",
            )
        return user.org_id

    async def _require_campaign(self, campaign_id: uuid.UUID, org_id: uuid.UUID) -> None:
        campaign = await self.campaign_repo.get_by_id(campaign_id, org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found."
            )

    async def _require_candidate(self, candidate_id: uuid.UUID, org_id: uuid.UUID) -> None:
        candidate = await self.candidate_repo.get_by_id_and_org(candidate_id, org_id)
        if candidate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found."
            )

    async def _get_session(self, session_id: uuid.UUID, org_id: uuid.UUID) -> AssessmentSession:
        assessment_session = await self.session_repo.get_by_id(session_id, org_id)
        if assessment_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assessment session not found."
            )
        return assessment_session

    async def _get_session_for_user(self, session_id: uuid.UUID, user: User) -> AssessmentSession:
        return await self._get_session(session_id, self._require_org(user))

    def _assert_not_completed(self, assessment_session: AssessmentSession) -> None:
        if assessment_session.status == AssessmentSessionStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This assessment session has already been completed.",
            )

    def _build_recording_storage_path(
        self, session_id: uuid.UUID, recording_type: RecordingType, filename: str
    ) -> str:
        ext = Path(filename).suffix.lower()
        stored_name = f"{uuid.uuid4()}{ext}"
        return f"assessment-recordings/{session_id}/{recording_type.value.lower()}/{stored_name}"

    # ── Recording upload validation ─────────────────────────────────────────────

    def _validate_recording_mime_type(self, mime_type: str) -> str:
        base = mime_type.split(";")[0].strip().lower()
        if base not in _ALLOWED_RECORDING_MIME_TYPES:
            allowed_str = ", ".join(sorted(_ALLOWED_RECORDING_MIME_TYPES))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported audio type '{mime_type or '(none)'}'. Allowed: {allowed_str}.",
            )
        return base

    def _validate_recording_size(self, data: bytes) -> None:
        max_bytes = _MAX_RECORDING_UPLOAD_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Recording is {len(data) / (1024 * 1024):.1f} MB, which exceeds the "
                    f"{_MAX_RECORDING_UPLOAD_MB} MB limit."
                ),
            )

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_or_resume(
        self, data: AssessmentSessionCreate, user: User
    ) -> AssessmentSession:
        org_id = self._require_org(user)
        await self._require_campaign(data.campaign_id, org_id)
        await self._require_candidate(data.candidate_id, org_id)

        existing = await self.session_repo.get_by_campaign_and_candidate(
            data.campaign_id, data.candidate_id, org_id
        )
        if existing is not None:
            return existing

        return await self.session_repo.create(
            org_id=org_id,
            campaign_id=data.campaign_id,
            candidate_id=data.candidate_id,
            current_section=AssessmentSection.APTITUDE,
            current_question=_INITIAL_QUESTION_NUMBER,
            status=AssessmentSessionStatus.IN_PROGRESS,
        )

    async def get_session(self, session_id: uuid.UUID, user: User) -> AssessmentSession:
        return await self._get_session_for_user(session_id, user)

    async def update_progress(
        self, session_id: uuid.UUID, data: AssessmentSessionProgressUpdate, user: User
    ) -> AssessmentSession:
        assessment_session = await self._get_session_for_user(session_id, user)
        self._assert_not_completed(assessment_session)
        fields = data.model_dump(exclude_unset=True)
        if not fields:
            return assessment_session
        return await self.session_repo.update(assessment_session, **fields)

    async def save_answer(
        self, session_id: uuid.UUID, data: AssessmentAnswerCreate, user: User
    ) -> AssessmentAnswer:
        assessment_session = await self._get_session_for_user(session_id, user)
        self._assert_not_completed(assessment_session)
        return await self.answer_repo.upsert(
            assessment_session.id, data.question_number, data.answer
        )

    async def save_recording(
        self, session_id: uuid.UUID, data: AssessmentRecordingCreate, user: User
    ) -> AssessmentRecording:
        assessment_session = await self._get_session_for_user(session_id, user)
        self._assert_not_completed(assessment_session)

        # Relative, storage-backend-agnostic path; no bytes are written here —
        # AssessmentSessionService.upload_recording is what actually calls
        # StorageBackend.save() at this path and flips status to UPLOADED.
        storage_path = self._build_recording_storage_path(
            assessment_session.id, data.recording_type, data.filename
        )

        return await self.recording_repo.upsert(
            assessment_session.id,
            data.recording_type,
            filename=data.filename,
            mime_type=data.mime_type,
            duration_seconds=data.duration_seconds,
            storage_path=storage_path,
            file_size=data.file_size,
            # A retake overwrites metadata from a prior attempt at this
            # recording type — reset to PENDING even if the old row had
            # already progressed to UPLOADED/FAILED.
            status=RecordingStatus.PENDING,
        )

    async def upload_recording(
        self,
        session_id: uuid.UUID,
        recording_type: RecordingType,
        file: UploadFile,
        duration_seconds: float,
        org_id: uuid.UUID,
    ) -> AssessmentRecording:
        assessment_session = await self._get_session(session_id, org_id)
        self._assert_not_completed(assessment_session)

        mime_type = self._validate_recording_mime_type(file.content_type or "")
        data = await file.read()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded file is empty or missing.",
            )
        self._validate_recording_size(data)

        filename = file.filename or f"recording{_EXT_BY_MIME.get(mime_type, '')}"
        storage_path = self._build_recording_storage_path(
            assessment_session.id, recording_type, filename
        )

        logger.info(
            "Upload Started",
            extra={
                "session_id": str(session_id),
                "recording_type": recording_type.value,
                "file_size": len(data),
                "mime_type": mime_type,
            },
        )
        try:
            await self.storage.save(storage_path, data)
        except Exception:
            logger.exception(
                "Upload Failed",
                extra={"session_id": str(session_id), "recording_type": recording_type.value},
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Failed to store the recording. Please try again.",
            ) from None

        recording = await self.recording_repo.upsert(
            assessment_session.id,
            recording_type,
            filename=filename,
            mime_type=mime_type,
            duration_seconds=duration_seconds,
            storage_path=storage_path,
            file_size=len(data),
            status=RecordingStatus.UPLOADED,
            uploaded_at=datetime.now(UTC),
        )
        logger.info(
            "Upload Completed",
            extra={
                "session_id": str(session_id),
                "recording_type": recording_type.value,
                "file_size": len(data),
                "recording_id": str(recording.id),
            },
        )
        return recording

    async def complete_session(self, session_id: uuid.UUID, user: User) -> AssessmentSession:
        assessment_session = await self._get_session_for_user(session_id, user)
        if assessment_session.status == AssessmentSessionStatus.COMPLETED:
            return assessment_session
        return await self.session_repo.update(
            assessment_session,
            status=AssessmentSessionStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )
