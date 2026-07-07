"""AssessmentAnalysisService — backend persistence for a transcript's
deterministic Read Aloud / Listen & Repeat communication analysis, produced
by the analyze_read_aloud / analyze_listen_repeat Celery pipelines
(app.workers.communication_analysis).

No AI logic here — ReadAloudAnalysisService/ListenRepeatAnalysisService
(app.ai.communication) own comparison/scoring. This service just creates and
transitions AssessmentAnalysis rows and enforces org scoping for the
read-only lookup. No aptitude, no recruiter reports — future-sprint
concerns.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status

from app.models.assessment_analysis import AnalysisStatus, AnalysisType

if TYPE_CHECKING:
    from app.models.assessment_analysis import AssessmentAnalysis
    from app.models.user import User
    from app.repositories.assessment_analysis import AssessmentAnalysisRepository


def _default_dispatcher(transcript_id: str, duration_seconds: float) -> None:
    """Lazy import avoids Celery at module import time (mirrors
    app.services.assessment_transcript._default_dispatcher)."""
    from app.workers.communication_analysis import analyze_read_aloud as _task  # noqa: PLC0415

    _task.delay(transcript_id, duration_seconds)


class AssessmentAnalysisService:
    def __init__(self, repo: AssessmentAnalysisRepository) -> None:
        self.repo = repo

    # ── Internal guards ───────────────────────────────────────────────────────

    async def _require_by_transcript(self, transcript_id: uuid.UUID) -> AssessmentAnalysis:
        row = await self.repo.get_by_transcript_id(transcript_id)
        if row is None:
            raise ValueError(f"AssessmentAnalysis for transcript {transcript_id} not found.")
        return row

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_pending(
        self,
        transcript_id: uuid.UUID,
        organization_id: uuid.UUID,
        *,
        analysis_type: AnalysisType = AnalysisType.READ_ALOUD,
    ) -> AssessmentAnalysis:
        """Idempotent: returns the existing row untouched if an analysis
        already exists for this transcript (a retry re-fetches and continues
        rather than duplicating), same idempotency shape as
        AssessmentTranscriptService.create_pending."""
        existing = await self.repo.get_by_transcript_id(transcript_id)
        if existing is not None:
            return existing
        return await self.repo.create(
            transcript_id,
            organization_id,
            analysis_type=analysis_type,
            status=AnalysisStatus.PENDING,
        )

    async def complete_processing(
        self,
        transcript_id: uuid.UUID,
        *,
        overall_score: float,
        word_accuracy: float,
        correct_words: int,
        missing_words: int,
        extra_words: int,
        substituted_words: int,
        total_words: int,
        reading_speed_wpm: float,
        completion_percentage: float,
        analysis_json: dict,
    ) -> AssessmentAnalysis:
        row = await self._require_by_transcript(transcript_id)
        return await self.repo.update(
            row,
            status=AnalysisStatus.COMPLETED,
            overall_score=overall_score,
            word_accuracy=word_accuracy,
            correct_words=correct_words,
            missing_words=missing_words,
            extra_words=extra_words,
            substituted_words=substituted_words,
            total_words=total_words,
            reading_speed_wpm=reading_speed_wpm,
            completion_percentage=completion_percentage,
            analysis_json=analysis_json,
            error_message=None,
        )

    async def complete_listen_repeat_processing(
        self,
        transcript_id: uuid.UUID,
        *,
        overall_score: float,
        semantic_similarity: float,
        keyword_coverage: float,
        completion_percentage: float,
        analysis_json: dict,
    ) -> AssessmentAnalysis:
        row = await self._require_by_transcript(transcript_id)
        return await self.repo.update(
            row,
            status=AnalysisStatus.COMPLETED,
            overall_score=overall_score,
            semantic_similarity=semantic_similarity,
            keyword_coverage=keyword_coverage,
            completion_percentage=completion_percentage,
            analysis_json=analysis_json,
            error_message=None,
        )

    async def fail_processing(
        self, transcript_id: uuid.UUID, error_message: str
    ) -> AssessmentAnalysis | None:
        """Best-effort: no-ops if the analysis row doesn't exist (e.g. the
        transcript itself disappeared before Phase 1 could create it)."""
        row = await self.repo.get_by_transcript_id(transcript_id)
        if row is None:
            return None
        return await self.repo.update(
            row, status=AnalysisStatus.FAILED, error_message=error_message[:1000]
        )

    async def get_analysis(self, transcript_id: uuid.UUID, user: User) -> AssessmentAnalysis:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view analyses.",
            )
        row = await self.repo.get_by_transcript_id(transcript_id)
        if row is None or row.organization_id != user.org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found."
            )
        return row

    async def retry_failed(
        self, transcript_id: uuid.UUID, user: User, duration_seconds: float, *, _dispatcher: Any = None
    ) -> AssessmentAnalysis:
        """Reset a FAILED analysis back to PENDING and re-dispatch the Celery
        task. Not exposed via an API endpoint this sprint — a manual/
        administrative capability only, exercised directly in service tests."""
        dispatch = _dispatcher or _default_dispatcher
        row = await self.get_analysis(transcript_id, user)
        if row.status != AnalysisStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only a FAILED analysis can be retried.",
            )
        row = await self.repo.update(row, status=AnalysisStatus.PENDING, error_message=None)
        dispatch(str(transcript_id), duration_seconds)
        return row
