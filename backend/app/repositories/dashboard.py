import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.models.candidate import Candidate
from app.models.embedding import EmbeddingStatus
from app.models.job_description import JobDescription, ParsingStatus
from app.models.parsed_resume import ParsedResume
from app.models.resume_file import ResumeFile, ReviewStatus, UploadStatus


class DashboardRepository:
    """Read-only aggregate queries for the recruiter dashboard, all scoped
    to a single organization. Reuses the existing Campaign / Candidate /
    ResumeFile / ParsedResume / JobDescription models directly rather than
    introducing new tables."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_campaigns_by_status(self, org_id: uuid.UUID) -> dict[CampaignStatus, int]:
        result = await self.session.execute(
            select(Campaign.status, func.count(Campaign.id))
            .where(Campaign.org_id == org_id, Campaign.is_deleted.is_(False))
            .group_by(Campaign.status)
        )
        return dict(result.tuples().all())

    async def count_candidates(self, org_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(Candidate.id)).where(Candidate.organization_id == org_id)
        )
        return result.scalar_one()

    async def count_resume_files_by_upload_status(
        self, org_id: uuid.UUID
    ) -> dict[UploadStatus, int]:
        result = await self.session.execute(
            select(ResumeFile.upload_status, func.count(ResumeFile.id))
            .join(Campaign, ResumeFile.campaign_id == Campaign.id)
            .where(Campaign.org_id == org_id, ResumeFile.is_deleted.is_(False))
            .group_by(ResumeFile.upload_status)
        )
        return dict(result.tuples().all())

    async def count_resume_files_by_review_status(
        self, org_id: uuid.UUID
    ) -> dict[ReviewStatus, int]:
        result = await self.session.execute(
            select(ResumeFile.review_status, func.count(ResumeFile.id))
            .join(Campaign, ResumeFile.campaign_id == Campaign.id)
            .where(Campaign.org_id == org_id, ResumeFile.is_deleted.is_(False))
            .group_by(ResumeFile.review_status)
        )
        return dict(result.tuples().all())

    async def count_parsed_resumes_by_embedding_status(
        self, org_id: uuid.UUID
    ) -> dict[EmbeddingStatus, int]:
        result = await self.session.execute(
            select(ParsedResume.embedding_status, func.count(ParsedResume.id))
            .join(ResumeFile, ParsedResume.resume_file_id == ResumeFile.id)
            .join(Campaign, ResumeFile.campaign_id == Campaign.id)
            .where(Campaign.org_id == org_id, ResumeFile.is_deleted.is_(False))
            .group_by(ParsedResume.embedding_status)
        )
        return dict(result.tuples().all())

    async def count_job_descriptions_by_status(
        self, org_id: uuid.UUID
    ) -> tuple[dict[ParsingStatus, int], dict[EmbeddingStatus, int]]:
        parsing_result = await self.session.execute(
            select(JobDescription.parsing_status, func.count(JobDescription.id))
            .join(Campaign, JobDescription.campaign_id == Campaign.id)
            .where(Campaign.org_id == org_id, JobDescription.is_deleted.is_(False))
            .group_by(JobDescription.parsing_status)
        )
        embedding_result = await self.session.execute(
            select(JobDescription.embedding_status, func.count(JobDescription.id))
            .join(Campaign, JobDescription.campaign_id == Campaign.id)
            .where(Campaign.org_id == org_id, JobDescription.is_deleted.is_(False))
            .group_by(JobDescription.embedding_status)
        )
        return dict(parsing_result.tuples().all()), dict(embedding_result.tuples().all())

    async def count_resumes_ready_for_ranking(self, org_id: uuid.UUID) -> int:
        """Resumes whose parsing + embedding are both done, i.e. available
        to be ranked on demand (ranking itself is computed live, not
        queued, so this is the closest real proxy for a 'ranking queue')."""
        result = await self.session.execute(
            select(func.count(func.distinct(ResumeFile.id)))
            .select_from(ResumeFile)
            .join(Campaign, ResumeFile.campaign_id == Campaign.id)
            .join(ParsedResume, ParsedResume.resume_file_id == ResumeFile.id)
            .where(
                Campaign.org_id == org_id,
                ResumeFile.is_deleted.is_(False),
                ResumeFile.upload_status == UploadStatus.PARSED,
                ParsedResume.embedding_status == EmbeddingStatus.READY,
            )
        )
        return result.scalar_one()

    async def list_recent_campaigns_with_candidate_counts(
        self, org_id: uuid.UUID, *, limit: int = 5
    ) -> list[tuple[Campaign, int]]:
        candidate_counts = (
            select(
                ResumeFile.campaign_id.label("campaign_id"),
                func.count(func.distinct(ResumeFile.candidate_id)).label("candidate_count"),
            )
            .where(ResumeFile.is_deleted.is_(False), ResumeFile.candidate_id.isnot(None))
            .group_by(ResumeFile.campaign_id)
            .subquery()
        )
        result = await self.session.execute(
            select(Campaign, func.coalesce(candidate_counts.c.candidate_count, 0))
            .outerjoin(candidate_counts, candidate_counts.c.campaign_id == Campaign.id)
            .where(Campaign.org_id == org_id, Campaign.is_deleted.is_(False))
            .order_by(Campaign.created_at.desc())
            .limit(limit)
        )
        return list(result.tuples().all())

    async def list_active_campaigns(self, org_id: uuid.UUID) -> list[Campaign]:
        result = await self.session.execute(
            select(Campaign).where(
                Campaign.org_id == org_id,
                Campaign.is_deleted.is_(False),
                Campaign.status == CampaignStatus.ACTIVE,
            )
        )
        return list(result.scalars().all())

    async def get_review_statuses(
        self, resume_file_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, ReviewStatus]:
        if not resume_file_ids:
            return {}
        result = await self.session.execute(
            select(ResumeFile.id, ResumeFile.review_status).where(
                ResumeFile.id.in_(resume_file_ids)
            )
        )
        return dict(result.tuples().all())

    async def list_recent_campaign_events(
        self, org_id: uuid.UUID, *, limit: int = 20
    ) -> list[Campaign]:
        result = await self.session.execute(
            select(Campaign)
            .where(Campaign.org_id == org_id, Campaign.is_deleted.is_(False))
            .order_by(Campaign.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent_resume_events(
        self, org_id: uuid.UUID, *, limit: int = 20
    ) -> list[tuple[ResumeFile, str]]:
        result = await self.session.execute(
            select(ResumeFile, Campaign.title)
            .join(Campaign, ResumeFile.campaign_id == Campaign.id)
            .where(Campaign.org_id == org_id, ResumeFile.is_deleted.is_(False))
            .order_by(ResumeFile.uploaded_at.desc())
            .limit(limit)
        )
        return list(result.tuples().all())

    async def list_recently_reviewed_resumes(
        self, org_id: uuid.UUID, *, limit: int = 20
    ) -> list[tuple[ResumeFile, str]]:
        result = await self.session.execute(
            select(ResumeFile, Campaign.title)
            .join(Campaign, ResumeFile.campaign_id == Campaign.id)
            .where(
                Campaign.org_id == org_id,
                ResumeFile.is_deleted.is_(False),
                ResumeFile.reviewed_at.isnot(None),
            )
            .order_by(ResumeFile.reviewed_at.desc())
            .limit(limit)
        )
        return list(result.tuples().all())
