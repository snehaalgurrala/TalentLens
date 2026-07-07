"""AssessmentTranscriptService — backend persistence for a recording's async
speech-to-text transcript, produced by the transcribe_recording Celery
pipeline (app.workers.speech_transcription).

No Whisper imports here, no StorageBackend access — SpeechService and
StorageBackend are only ever touched by the Celery worker. This service just
creates and transitions AssessmentTranscript rows and enforces org scoping
for the read-only lookup. No communication scoring, no transcript
comparison, no recruiter reports — future-sprint concerns.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status

from app.models.assessment_transcript import TranscriptStatus

if TYPE_CHECKING:
    from app.models.assessment_transcript import AssessmentTranscript
    from app.models.user import User
    from app.repositories.assessment_transcript import AssessmentTranscriptRepository


def _default_dispatcher(recording_id: str) -> None:
    """Lazy import avoids Celery at module import time (mirrors
    app.api.v1.endpoints.resumes._enqueue_parse)."""
    from app.workers.speech_transcription import transcribe_recording as _task  # noqa: PLC0415

    _task.delay(recording_id)


class AssessmentTranscriptService:
    def __init__(self, repo: AssessmentTranscriptRepository) -> None:
        self.repo = repo

    # ── Internal guards ───────────────────────────────────────────────────────

    async def _require_by_recording(self, recording_id: uuid.UUID) -> AssessmentTranscript:
        row = await self.repo.get_by_recording_id(recording_id)
        if row is None:
            raise ValueError(f"AssessmentTranscript for recording {recording_id} not found.")
        return row

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_pending(
        self, recording_id: uuid.UUID, organization_id: uuid.UUID
    ) -> AssessmentTranscript:
        """Idempotent: returns the existing row untouched if a transcript
        already exists for this recording (a retry re-fetches and continues
        rather than duplicating), same idempotency shape as
        resume_parser/job_description_parser's already-parsed guards."""
        existing = await self.repo.get_by_recording_id(recording_id)
        if existing is not None:
            return existing
        return await self.repo.create(
            recording_id, organization_id, status=TranscriptStatus.PENDING
        )

    async def start_processing(self, recording_id: uuid.UUID) -> AssessmentTranscript:
        transcript = await self._require_by_recording(recording_id)
        return await self.repo.update(
            transcript, status=TranscriptStatus.PROCESSING, error_message=None
        )

    async def complete_processing(
        self,
        recording_id: uuid.UUID,
        *,
        transcript: str,
        language: str,
        model_name: str,
        processing_time_ms: int,
        segment_count: int,
    ) -> AssessmentTranscript:
        row = await self._require_by_recording(recording_id)
        return await self.repo.update(
            row,
            status=TranscriptStatus.COMPLETED,
            transcript=transcript,
            language=language,
            model_name=model_name,
            processing_time_ms=processing_time_ms,
            segment_count=segment_count,
            error_message=None,
        )

    async def fail_processing(
        self, recording_id: uuid.UUID, error_message: str
    ) -> AssessmentTranscript | None:
        """Best-effort: no-ops if the transcript row doesn't exist (e.g. the
        recording itself disappeared before Phase 1 could create it)."""
        row = await self.repo.get_by_recording_id(recording_id)
        if row is None:
            return None
        return await self.repo.update(
            row, status=TranscriptStatus.FAILED, error_message=error_message[:1000]
        )

    async def get_transcript(self, recording_id: uuid.UUID, user: User) -> AssessmentTranscript:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view transcripts.",
            )
        row = await self.repo.get_by_recording_id(recording_id)
        if row is None or row.organization_id != user.org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found."
            )
        return row

    async def retry_failed(
        self, recording_id: uuid.UUID, user: User, *, _dispatcher: Any = None
    ) -> AssessmentTranscript:
        """Reset a FAILED transcript back to PENDING and re-dispatch the
        Celery task. Not exposed via an API endpoint this sprint — a manual/
        administrative capability only, exercised directly in service tests."""
        dispatch = _dispatcher or _default_dispatcher
        row = await self.get_transcript(recording_id, user)
        if row.status != TranscriptStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only a FAILED transcript can be retried.",
            )
        row = await self.repo.update(row, status=TranscriptStatus.PENDING, error_message=None)
        dispatch(str(recording_id))
        return row
