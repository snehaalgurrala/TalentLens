"""
DashboardService — aggregates data that already exists across the Campaign,
Candidate, ResumeFile, ParsedResume and JobDescription tables into the
metrics a recruiter dashboard needs.

Match scores are never persisted (see CandidateRankingService's docstring),
so "average match score" and "top candidates" are computed by live-ranking
every ACTIVE campaign in the organization and combining the results.
Campaigns without a ranking-ready job description are skipped rather than
treated as an error — that's an expected, common state for a campaign that
hasn't finished setup yet.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.models.campaign import Campaign, CampaignStatus
from app.models.embedding import EmbeddingStatus
from app.models.job_description import ParsingStatus
from app.models.resume_file import ReviewStatus, UploadStatus
from app.schemas.dashboard import (
    ActivityItemResponse,
    DashboardSummaryResponse,
    ProcessingStatusResponse,
    RecentCampaignResponse,
    TopCandidateResponse,
)

if TYPE_CHECKING:
    from app.models.user import User
    from app.repositories.candidate import CandidateRepository
    from app.repositories.dashboard import DashboardRepository
    from app.services.candidate_ranking import CandidateRankingEntry, CandidateRankingService


class DashboardService:
    def __init__(
        self,
        repo: DashboardRepository,
        candidate_repo: CandidateRepository,
        ranking_service: CandidateRankingService,
    ) -> None:
        self.repo = repo
        self.candidate_repo = candidate_repo
        self.ranking_service = ranking_service

    # ── Internal guards ──────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view the dashboard.",
            )
        return user.org_id

    async def _rank_active_campaigns(
        self, org_id: uuid.UUID, user: User
    ) -> list[tuple[Campaign, CandidateRankingEntry]]:
        active_campaigns = await self.repo.list_active_campaigns(org_id)
        ranked: list[tuple[Campaign, CandidateRankingEntry]] = []
        for campaign in active_campaigns:
            try:
                entries = await self.ranking_service.rank_campaign(campaign.id, user)
            except HTTPException:
                # No ready job description yet, or another expected 4xx state
                # for this campaign — skip it rather than fail the dashboard.
                continue
            ranked.extend((campaign, entry) for entry in entries)
        return ranked

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_summary(self, user: User) -> DashboardSummaryResponse:
        org_id = self._require_org(user)

        campaigns_by_status = await self.repo.count_campaigns_by_status(org_id)
        resumes_by_upload_status = await self.repo.count_resume_files_by_upload_status(org_id)
        resumes_by_review_status = await self.repo.count_resume_files_by_review_status(org_id)
        total_candidates = await self.repo.count_candidates(org_id)
        ranked = await self._rank_active_campaigns(org_id, user)

        processing_candidates = sum(
            resumes_by_upload_status.get(s, 0)
            for s in (UploadStatus.PENDING, UploadStatus.UPLOADED, UploadStatus.PROCESSING)
        )
        average_match_score = (
            round(sum(entry.overall_score for _, entry in ranked) / len(ranked), 1)
            if ranked
            else None
        )

        return DashboardSummaryResponse(
            total_campaigns=sum(campaigns_by_status.values()),
            active_campaigns=campaigns_by_status.get(CampaignStatus.ACTIVE, 0),
            closed_campaigns=campaigns_by_status.get(CampaignStatus.CLOSED, 0),
            total_candidates=total_candidates,
            processing_candidates=processing_candidates,
            shortlisted_candidates=resumes_by_review_status.get(ReviewStatus.SHORTLISTED, 0),
            rejected_candidates=resumes_by_review_status.get(ReviewStatus.REJECTED, 0),
            average_match_score=average_match_score,
        )

    async def get_recent_campaigns(
        self, user: User, *, limit: int = 5
    ) -> list[RecentCampaignResponse]:
        org_id = self._require_org(user)
        rows = await self.repo.list_recent_campaigns_with_candidate_counts(org_id, limit=limit)
        return [
            RecentCampaignResponse(
                id=campaign.id,
                title=campaign.title,
                status=campaign.status,
                created_at=campaign.created_at,
                candidate_count=count,
            )
            for campaign, count in rows
        ]

    async def get_top_candidates(
        self, user: User, *, limit: int = 10
    ) -> list[TopCandidateResponse]:
        org_id = self._require_org(user)
        ranked = await self._rank_active_campaigns(org_id, user)
        ranked.sort(key=lambda pair: -pair[1].overall_score)
        top = ranked[:limit]
        if not top:
            return []

        candidate_ids = list({entry.candidate_id for _, entry in top})
        candidates_by_id = {c.id: c for c in await self.candidate_repo.list_by_ids(candidate_ids)}
        review_status_by_resume = await self.repo.get_review_statuses(
            [entry.resume_file_id for _, entry in top]
        )

        responses = []
        for campaign, entry in top:
            candidate = candidates_by_id.get(entry.candidate_id)
            responses.append(
                TopCandidateResponse(
                    candidate_id=entry.candidate_id,
                    candidate_name=entry.candidate_name,
                    resume_file_id=entry.resume_file_id,
                    match_score=entry.overall_score,
                    campaign_id=campaign.id,
                    campaign_name=campaign.title,
                    years_of_experience=candidate.years_of_experience if candidate else None,
                    current_company=candidate.current_company if candidate else None,
                    review_status=review_status_by_resume.get(
                        entry.resume_file_id, ReviewStatus.PENDING
                    ),
                )
            )
        return responses

    async def get_processing_status(self, user: User) -> ProcessingStatusResponse:
        org_id = self._require_org(user)

        resumes_by_upload_status = await self.repo.count_resume_files_by_upload_status(org_id)
        parsed_by_embedding_status = await self.repo.count_parsed_resumes_by_embedding_status(
            org_id
        )
        jd_parsing_status, jd_embedding_status = await self.repo.count_job_descriptions_by_status(
            org_id
        )
        ranking_queue = await self.repo.count_resumes_ready_for_ranking(org_id)

        parsing_queue = sum(
            resumes_by_upload_status.get(s, 0)
            for s in (UploadStatus.PENDING, UploadStatus.UPLOADED, UploadStatus.PROCESSING)
        ) + sum(
            jd_parsing_status.get(s, 0) for s in (ParsingStatus.PENDING, ParsingStatus.PROCESSING)
        )
        embedding_queue = sum(
            parsed_by_embedding_status.get(s, 0)
            for s in (EmbeddingStatus.PENDING, EmbeddingStatus.GENERATING)
        ) + sum(
            jd_embedding_status.get(s, 0)
            for s in (EmbeddingStatus.PENDING, EmbeddingStatus.GENERATING)
        )
        failed_jobs = resumes_by_upload_status.get(
            UploadStatus.FAILED, 0
        ) + jd_parsing_status.get(ParsingStatus.FAILED, 0)
        completed_jobs = resumes_by_upload_status.get(
            UploadStatus.PARSED, 0
        ) + jd_parsing_status.get(ParsingStatus.COMPLETED, 0)

        return ProcessingStatusResponse(
            parsing_queue=parsing_queue,
            embedding_queue=embedding_queue,
            ranking_queue=ranking_queue,
            failed_jobs=failed_jobs,
            completed_jobs=completed_jobs,
        )

    async def get_activity(self, user: User, *, limit: int = 20) -> list[ActivityItemResponse]:
        org_id = self._require_org(user)

        campaigns = await self.repo.list_recent_campaign_events(org_id, limit=limit)
        resumes = await self.repo.list_recent_resume_events(org_id, limit=limit)
        reviewed = await self.repo.list_recently_reviewed_resumes(org_id, limit=limit)

        events: list[ActivityItemResponse] = []
        for campaign in campaigns:
            events.append(
                ActivityItemResponse(
                    id=f"campaign-created:{campaign.id}",
                    type="CAMPAIGN_CREATED",
                    description=f'Campaign "{campaign.title}" was created.',
                    occurred_at=campaign.created_at,
                    campaign_id=campaign.id,
                    campaign_name=campaign.title,
                )
            )
        for resume_file, campaign_title in resumes:
            events.append(
                ActivityItemResponse(
                    id=f"resume-uploaded:{resume_file.id}",
                    type="RESUME_UPLOADED",
                    description=(
                        f'Resume "{resume_file.original_filename}" was uploaded '
                        f'to "{campaign_title}".'
                    ),
                    occurred_at=resume_file.uploaded_at,
                    campaign_id=resume_file.campaign_id,
                    campaign_name=campaign_title,
                )
            )
        for resume_file, campaign_title in reviewed:
            if resume_file.reviewed_at is None:
                continue
            if resume_file.review_status == ReviewStatus.SHORTLISTED:
                events.append(
                    ActivityItemResponse(
                        id=f"candidate-shortlisted:{resume_file.id}",
                        type="CANDIDATE_SHORTLISTED",
                        description=f'A candidate was shortlisted for "{campaign_title}".',
                        occurred_at=resume_file.reviewed_at,
                        campaign_id=resume_file.campaign_id,
                        campaign_name=campaign_title,
                    )
                )
            elif resume_file.review_status == ReviewStatus.REJECTED:
                events.append(
                    ActivityItemResponse(
                        id=f"candidate-rejected:{resume_file.id}",
                        type="CANDIDATE_REJECTED",
                        description=f'A candidate was rejected for "{campaign_title}".',
                        occurred_at=resume_file.reviewed_at,
                        campaign_id=resume_file.campaign_id,
                        campaign_name=campaign_title,
                    )
                )

        events.sort(key=lambda e: e.occurred_at, reverse=True)
        return events[:limit]
