"""CommunicationAssessmentService — backend persistence for a session's
aggregate communication assessment, produced by the
generate_communication_assessment Celery task
(app.workers.communication_assessment).

No Whisper imports, no embedding imports here — this service only consumes
already-persisted AssessmentAnalysis rows (via the worker) and creates/
transitions CommunicationAssessment rows, enforcing org scoping for the
read-only lookup. Scoring and rule detection live entirely in
app.ai.communication.communication_assessment_engine; this service never
computes a score itself.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status

from app.models.communication_assessment import CommunicationAssessmentStatus

if TYPE_CHECKING:
    from app.models.communication_assessment import CommunicationAssessment
    from app.models.user import User
    from app.repositories.communication_assessment import CommunicationAssessmentRepository


def _default_dispatcher(assessment_session_id: str) -> None:
    """Lazy import avoids Celery at module import time (mirrors
    app.services.assessment_analysis._default_dispatcher)."""
    from app.workers.communication_assessment import (  # noqa: PLC0415
        generate_communication_assessment as _task,
    )

    _task.delay(assessment_session_id)


class CommunicationAssessmentService:
    def __init__(self, repo: CommunicationAssessmentRepository) -> None:
        self.repo = repo

    # ── Internal guards ───────────────────────────────────────────────────────

    async def _require_by_session(
        self, assessment_session_id: uuid.UUID
    ) -> CommunicationAssessment:
        row = await self.repo.get_by_session_id(assessment_session_id)
        if row is None:
            raise ValueError(
                f"CommunicationAssessment for session {assessment_session_id} not found."
            )
        return row

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_pending(
        self, assessment_session_id: uuid.UUID, organization_id: uuid.UUID
    ) -> CommunicationAssessment:
        """Idempotent: returns the existing row untouched if an assessment
        already exists for this session (a retry re-fetches and continues
        rather than duplicating), same idempotency shape as
        AssessmentAnalysisService.create_pending."""
        existing = await self.repo.get_by_session_id(assessment_session_id)
        if existing is not None:
            return existing
        return await self.repo.create(
            assessment_session_id,
            organization_id,
            status=CommunicationAssessmentStatus.PENDING,
        )

    async def complete_processing(
        self,
        assessment_session_id: uuid.UUID,
        *,
        overall_score: float,
        reading_score: float,
        listening_score: float,
        confidence_score: float,
        strengths_json: list[str],
        improvements_json: list[str],
        summary_json: dict[str, Any],
    ) -> CommunicationAssessment:
        row = await self._require_by_session(assessment_session_id)
        return await self.repo.update(
            row,
            status=CommunicationAssessmentStatus.COMPLETED,
            overall_score=overall_score,
            reading_score=reading_score,
            listening_score=listening_score,
            confidence_score=confidence_score,
            strengths_json=strengths_json,
            improvements_json=improvements_json,
            summary_json=summary_json,
            error_message=None,
        )

    async def fail_processing(
        self, assessment_session_id: uuid.UUID, error_message: str
    ) -> CommunicationAssessment | None:
        """Best-effort: no-ops if the assessment row doesn't exist (e.g. the
        session itself disappeared before Phase 1 could create it)."""
        row = await self.repo.get_by_session_id(assessment_session_id)
        if row is None:
            return None
        return await self.repo.update(
            row, status=CommunicationAssessmentStatus.FAILED, error_message=error_message[:1000]
        )

    async def get_assessment(
        self, assessment_session_id: uuid.UUID, user: User
    ) -> CommunicationAssessment:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view communication assessments.",
            )
        row = await self.repo.get_by_session_id(assessment_session_id)
        if row is None or row.organization_id != user.org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Communication assessment not found.",
            )
        return row

    async def retry_failed(
        self, assessment_session_id: uuid.UUID, user: User, *, _dispatcher: Any = None
    ) -> CommunicationAssessment:
        """Reset a FAILED assessment back to PENDING and re-dispatch the
        Celery task. Not exposed via an API endpoint this sprint — a manual/
        administrative capability only, exercised directly in service tests."""
        dispatch = _dispatcher or _default_dispatcher
        row = await self.get_assessment(assessment_session_id, user)
        if row.status != CommunicationAssessmentStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only a FAILED communication assessment can be retried.",
            )
        row = await self.repo.update(
            row, status=CommunicationAssessmentStatus.PENDING, error_message=None
        )
        dispatch(str(assessment_session_id))
        return row
