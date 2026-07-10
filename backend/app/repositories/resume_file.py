import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.resume_file import PipelineStage, ResumeFile


class ResumeFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, resume_id: uuid.UUID) -> ResumeFile | None:
        result = await self.session.execute(
            select(ResumeFile).where(
                ResumeFile.id == resume_id,
                ResumeFile.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_campaign(self, campaign_id: uuid.UUID) -> list[ResumeFile]:
        result = await self.session.execute(
            select(ResumeFile)
            .where(
                ResumeFile.campaign_id == campaign_id,
                ResumeFile.is_deleted.is_(False),
            )
            .order_by(ResumeFile.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_ids(self, resume_file_ids: list[uuid.UUID]) -> list[ResumeFile]:
        if not resume_file_ids:
            return []
        result = await self.session.execute(
            select(ResumeFile).where(
                ResumeFile.id.in_(resume_file_ids),
                ResumeFile.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def get_by_candidate_and_campaign(
        self, candidate_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> ResumeFile | None:
        """The per-campaign candidate row automatic pipeline-stage
        transitions key on — invitation/session events carry candidate_id
        + campaign_id, not resume_file_id directly.

        A candidate can have more than one ResumeFile row for the same
        campaign (re-uploads/reapplications) — same "most recent wins"
        resolution as get_latest_by_candidate_id, not scalar_one_or_none,
        which would raise on a second upload."""
        result = await self.session.execute(
            select(ResumeFile)
            .where(
                ResumeFile.candidate_id == candidate_id,
                ResumeFile.campaign_id == campaign_id,
                ResumeFile.is_deleted.is_(False),
            )
            .order_by(ResumeFile.uploaded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_by_candidate_id(self, candidate_id: uuid.UUID) -> ResumeFile | None:
        """Most recently uploaded resume file linked to this candidate — used
        to resolve a bare Candidate.id (as seen on the candidate list/profile
        routes) down to the resume_file_id every mutation endpoint keys on."""
        result = await self.session.execute(
            select(ResumeFile)
            .where(
                ResumeFile.candidate_id == candidate_id,
                ResumeFile.is_deleted.is_(False),
            )
            .order_by(ResumeFile.uploaded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> ResumeFile:
        rf = ResumeFile(**kwargs)
        self.session.add(rf)
        await self.session.flush()
        await self.session.refresh(rf)
        return rf

    async def update(self, resume_file: ResumeFile, **kwargs: Any) -> ResumeFile:
        for key, value in kwargs.items():
            setattr(resume_file, key, value)
        await self.session.flush()
        await self.session.refresh(resume_file)
        return resume_file

    async def soft_delete(self, resume_file: ResumeFile) -> None:
        resume_file.is_deleted = True
        resume_file.deleted_at = datetime.now(UTC)
        await self.session.flush()

    async def workload_by_org(
        self, org_id: uuid.UUID
    ) -> list[tuple[uuid.UUID, PipelineStage, int]]:
        """(assigned_recruiter_id, pipeline_stage, count) rows for every
        assigned, non-deleted resume file across every campaign in org_id —
        a real GROUP BY aggregate, unlike the in-memory scan pattern used by
        CandidateManagementService.list_campaign_candidates."""
        result = await self.session.execute(
            select(ResumeFile.assigned_recruiter_id, ResumeFile.pipeline_stage, func.count())
            .join(Campaign, Campaign.id == ResumeFile.campaign_id)
            .where(
                Campaign.org_id == org_id,
                ResumeFile.is_deleted.is_(False),
                ResumeFile.assigned_recruiter_id.is_not(None),
            )
            .group_by(ResumeFile.assigned_recruiter_id, ResumeFile.pipeline_stage)
        )
        return [(row[0], row[1], row[2]) for row in result.all()]
