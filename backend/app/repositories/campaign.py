import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign, CampaignPriority, CampaignStatus, EmploymentType
from app.models.embedding import EmbeddingStatus
from app.models.parsed_resume import ParsedResume
from app.models.resume_file import ResumeFile, ReviewStatus, UploadStatus

_PROCESSING_UPLOAD_STATUSES = (UploadStatus.PENDING, UploadStatus.UPLOADED, UploadStatus.PROCESSING)

_SORTABLE_COLUMNS = {
    "created_at": Campaign.created_at,
    "updated_at": Campaign.updated_at,
    "title": Campaign.title,
    "status": Campaign.status,
    "priority": Campaign.priority,
}


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _with_relations(self, stmt: Any) -> Any:
        return stmt.options(
            selectinload(Campaign.hiring_manager), selectinload(Campaign.recruiter)
        )

    async def get_by_id(self, campaign_id: uuid.UUID, org_id: uuid.UUID) -> Campaign | None:
        result = await self.session.execute(
            self._with_relations(select(Campaign)).where(
                Campaign.id == campaign_id,
                Campaign.org_id == org_id,
                Campaign.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org_filtered(
        self,
        org_id: uuid.UUID,
        *,
        search: str | None = None,
        status: CampaignStatus | None = None,
        department: str | None = None,
        employment_type: EmploymentType | None = None,
        priority: CampaignPriority | None = None,
        recruiter_id: uuid.UUID | None = None,
        hiring_manager_id: uuid.UUID | None = None,
        created_after: date | None = None,
        created_before: date | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        skip: int = 0,
        limit: int = 50,
    ) -> list[tuple[Campaign, int, int]]:
        processing_flag = case(
            (ResumeFile.upload_status.in_(_PROCESSING_UPLOAD_STATUSES), 1), else_=0
        )
        resume_counts = (
            select(
                ResumeFile.campaign_id.label("campaign_id"),
                func.count(ResumeFile.id).label("resume_count"),
                func.sum(processing_flag).label("processing_count"),
            )
            .where(ResumeFile.is_deleted.is_(False))
            .group_by(ResumeFile.campaign_id)
            .subquery()
        )

        stmt = (
            select(
                Campaign,
                func.coalesce(resume_counts.c.resume_count, 0),
                func.coalesce(resume_counts.c.processing_count, 0),
            )
            .outerjoin(resume_counts, resume_counts.c.campaign_id == Campaign.id)
            .where(Campaign.org_id == org_id, Campaign.is_deleted.is_(False))
        )
        stmt = self._with_relations(stmt)

        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(Campaign.title.ilike(like), Campaign.job_title.ilike(like)))
        if status is not None:
            stmt = stmt.where(Campaign.status == status)
        if department:
            stmt = stmt.where(Campaign.department.ilike(f"%{department}%"))
        if employment_type is not None:
            stmt = stmt.where(Campaign.employment_type == employment_type)
        if priority is not None:
            stmt = stmt.where(Campaign.priority == priority)
        if recruiter_id is not None:
            stmt = stmt.where(Campaign.recruiter_id == recruiter_id)
        if hiring_manager_id is not None:
            stmt = stmt.where(Campaign.hiring_manager_id == hiring_manager_id)
        if created_after is not None:
            stmt = stmt.where(func.date(Campaign.created_at) >= created_after)
        if created_before is not None:
            stmt = stmt.where(func.date(Campaign.created_at) <= created_before)

        sort_column = _SORTABLE_COLUMNS.get(sort_by, Campaign.created_at)
        stmt = stmt.order_by(sort_column.asc() if sort_dir == "asc" else sort_column.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return [(row[0], int(row[1]), int(row[2])) for row in result.all()]

    async def create(self, **kwargs: Any) -> Campaign:
        campaign = Campaign(**kwargs)
        self.session.add(campaign)
        await self.session.flush()
        return await self.get_by_id(campaign.id, campaign.org_id)  # type: ignore[return-value]

    async def update(self, campaign: Campaign, **kwargs: Any) -> Campaign:
        for key, value in kwargs.items():
            setattr(campaign, key, value)
        await self.session.flush()
        return await self.get_by_id(campaign.id, campaign.org_id)  # type: ignore[return-value]

    async def soft_delete(self, campaign: Campaign) -> None:
        campaign.is_deleted = True
        campaign.deleted_at = datetime.now(UTC)
        await self.session.flush()

    # ── Campaign-scoped aggregates (for summary / processing-status) ─────────

    async def count_resumes_by_upload_status(
        self, campaign_id: uuid.UUID
    ) -> dict[UploadStatus, int]:
        result = await self.session.execute(
            select(ResumeFile.upload_status, func.count(ResumeFile.id))
            .where(ResumeFile.campaign_id == campaign_id, ResumeFile.is_deleted.is_(False))
            .group_by(ResumeFile.upload_status)
        )
        return dict(result.tuples().all())

    async def count_resumes_by_review_status(
        self, campaign_id: uuid.UUID
    ) -> dict[ReviewStatus, int]:
        result = await self.session.execute(
            select(ResumeFile.review_status, func.count(ResumeFile.id))
            .where(ResumeFile.campaign_id == campaign_id, ResumeFile.is_deleted.is_(False))
            .group_by(ResumeFile.review_status)
        )
        return dict(result.tuples().all())

    async def count_parsed_resumes_by_embedding_status(
        self, campaign_id: uuid.UUID
    ) -> dict[EmbeddingStatus, int]:
        result = await self.session.execute(
            select(ParsedResume.embedding_status, func.count(ParsedResume.id))
            .join(ResumeFile, ParsedResume.resume_file_id == ResumeFile.id)
            .where(ResumeFile.campaign_id == campaign_id, ResumeFile.is_deleted.is_(False))
            .group_by(ParsedResume.embedding_status)
        )
        return dict(result.tuples().all())

    async def count_resumes_ready_for_ranking(self, campaign_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(ResumeFile.id)))
            .select_from(ResumeFile)
            .join(ParsedResume, ParsedResume.resume_file_id == ResumeFile.id)
            .where(
                ResumeFile.campaign_id == campaign_id,
                ResumeFile.is_deleted.is_(False),
                ResumeFile.upload_status == UploadStatus.PARSED,
                ParsedResume.embedding_status == EmbeddingStatus.READY,
            )
        )
        return result.scalar_one()

    async def count_total_resumes(self, campaign_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(ResumeFile.id)).where(
                ResumeFile.campaign_id == campaign_id, ResumeFile.is_deleted.is_(False)
            )
        )
        return result.scalar_one()
