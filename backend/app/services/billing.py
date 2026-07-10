import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_session import AssessmentSession
from app.models.campaign import Campaign
from app.models.resume_file import PipelineStage, ResumeFile
from app.models.user import User
from app.schemas.billing import BillingUsageResponse


class BillingService:
    """Real, computed usage numbers only — no fabricated metrics. plan_name
    is always "Coming Soon" per the explicit product decision to ship
    Billing as a usage-only placeholder (no payments) in this build."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_usage(self, org_id: uuid.UUID, admin: User) -> BillingUsageResponse:
        users_count = (
            await self.session.execute(
                select(func.count()).select_from(User).where(User.org_id == org_id)
            )
        ).scalar_one()

        storage_bytes = (
            await self.session.execute(
                select(func.coalesce(func.sum(ResumeFile.file_size), 0))
                .select_from(ResumeFile)
                .join(Campaign, Campaign.id == ResumeFile.campaign_id)
                .where(Campaign.org_id == org_id, ResumeFile.is_deleted.is_(False))
            )
        ).scalar_one()

        assessments_used = (
            await self.session.execute(
                select(func.count())
                .select_from(AssessmentSession)
                .where(AssessmentSession.org_id == org_id)
            )
        ).scalar_one()

        # No dedicated AI-invocation log exists — the closest honest proxy is
        # resumes that have progressed past embedding generation (every
        # resume that reaches EMBEDDING/RANKED or later triggered exactly one
        # local-embedding-service call). Labeled "Embedding/Matching
        # Operations" in the UI rather than a generic "AI Requests" so it
        # doesn't overclaim what's actually being counted.
        embedding_ops = (
            await self.session.execute(
                select(func.count())
                .select_from(ResumeFile)
                .join(Campaign, Campaign.id == ResumeFile.campaign_id)
                .where(
                    Campaign.org_id == org_id,
                    ResumeFile.is_deleted.is_(False),
                    ResumeFile.pipeline_stage.not_in(
                        [PipelineStage.APPLIED, PipelineStage.PARSING]
                    ),
                )
            )
        ).scalar_one()

        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return BillingUsageResponse(
            users_count=users_count,
            storage_used_mb=round(storage_bytes / (1024 * 1024), 2),
            assessments_used=assessments_used,
            embedding_operations_count=embedding_ops,
            period_start=period_start,
            period_end=now,
        )
