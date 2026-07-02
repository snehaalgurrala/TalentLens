"""
CampaignSummaryService — the campaign-detail-page equivalent of
DashboardService: aggregates ResumeFile/ParsedResume state for a single
campaign into the summary cards and processing-monitor stages the UI needs.

Match scores are never persisted (see CandidateRankingService's docstring),
so "ranked candidates" / "average match score" are computed by live-ranking
the campaign. A campaign with no ranking-ready job description yet is a
normal, expected state — not an error — so it's treated as zero ranked
candidates rather than surfaced as a failure.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.models.embedding import EmbeddingStatus
from app.models.resume_file import ReviewStatus, UploadStatus
from app.schemas.campaign import CampaignProcessingStatusResponse, CampaignSummaryResponse

if TYPE_CHECKING:
    from app.models.user import User
    from app.repositories.campaign import CampaignRepository
    from app.services.candidate_ranking import CandidateRankingService


class CampaignSummaryService:
    def __init__(
        self,
        repo: CampaignRepository,
        ranking_service: CandidateRankingService,
    ) -> None:
        self.repo = repo
        self.ranking_service = ranking_service

    async def _ranked_count_and_average(
        self, campaign_id: uuid.UUID, user: User
    ) -> tuple[int, float | None]:
        try:
            entries = await self.ranking_service.rank_campaign(campaign_id, user)
        except HTTPException:
            # No ready job description yet — a normal, common setup state.
            return 0, None
        if not entries:
            return 0, None
        average = round(sum(e.overall_score for e in entries) / len(entries), 1)
        return len(entries), average

    async def get_summary(self, campaign_id: uuid.UUID, user: User) -> CampaignSummaryResponse:
        by_upload_status = await self.repo.count_resumes_by_upload_status(campaign_id)
        by_review_status = await self.repo.count_resumes_by_review_status(campaign_id)
        total_candidates = await self.repo.count_total_resumes(campaign_id)
        ranked_count, average_match_score = await self._ranked_count_and_average(
            campaign_id, user
        )

        processing_candidates = sum(
            by_upload_status.get(s, 0)
            for s in (UploadStatus.PENDING, UploadStatus.UPLOADED, UploadStatus.PROCESSING)
        )

        return CampaignSummaryResponse(
            total_candidates=total_candidates,
            processing_candidates=processing_candidates,
            ranked_candidates=ranked_count,
            shortlisted_candidates=by_review_status.get(ReviewStatus.SHORTLISTED, 0),
            rejected_candidates=by_review_status.get(ReviewStatus.REJECTED, 0),
            average_match_score=average_match_score,
        )

    async def get_processing_status(
        self, campaign_id: uuid.UUID, user: User  # noqa: ARG002 (kept for symmetry/future use)
    ) -> CampaignProcessingStatusResponse:
        by_upload_status = await self.repo.count_resumes_by_upload_status(campaign_id)
        by_embedding_status = await self.repo.count_parsed_resumes_by_embedding_status(
            campaign_id
        )
        ready_for_ranking = await self.repo.count_resumes_ready_for_ranking(campaign_id)
        total = await self.repo.count_total_resumes(campaign_id)

        uploaded_count = sum(
            by_upload_status.get(s, 0) for s in (UploadStatus.PENDING, UploadStatus.UPLOADED)
        )
        parsing_count = by_upload_status.get(UploadStatus.PROCESSING, 0)
        embedding_count = sum(
            by_embedding_status.get(s, 0)
            for s in (EmbeddingStatus.PENDING, EmbeddingStatus.GENERATING)
        )
        failed_count = by_upload_status.get(UploadStatus.FAILED, 0)

        return CampaignProcessingStatusResponse(
            uploaded_count=uploaded_count,
            parsing_count=parsing_count,
            embedding_count=embedding_count,
            ready_for_ranking_count=ready_for_ranking,
            # Ranking is computed live rather than persisted per-resume, so
            # "ready to be ranked" is the closest real proxy for "completed".
            completed_count=ready_for_ranking,
            failed_count=failed_count,
            total_count=total,
        )
