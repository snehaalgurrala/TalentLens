import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_invitation import AssessmentInvitation, AssessmentInvitationStatus


class AssessmentInvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_token_hash(self, token_hash: str) -> AssessmentInvitation | None:
        result = await self.session.execute(
            select(AssessmentInvitation).where(AssessmentInvitation.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_session(
        self, assessment_session_id: uuid.UUID
    ) -> AssessmentInvitation | None:
        result = await self.session.execute(
            select(AssessmentInvitation).where(
                AssessmentInvitation.assessment_session_id == assessment_session_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(self, organization_id: uuid.UUID) -> list[AssessmentInvitation]:
        result = await self.session.execute(
            select(AssessmentInvitation).where(
                AssessmentInvitation.organization_id == organization_id
            )
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> AssessmentInvitation:
        invitation = AssessmentInvitation(**kwargs)
        self.session.add(invitation)
        await self.session.flush()
        await self.session.refresh(invitation)
        return invitation

    async def update(self, invitation: AssessmentInvitation, **kwargs: Any) -> AssessmentInvitation:
        for key, value in kwargs.items():
            setattr(invitation, key, value)
        await self.session.flush()
        await self.session.refresh(invitation)
        return invitation

    async def mark_sent(self, invitation: AssessmentInvitation) -> AssessmentInvitation:
        return await self.update(
            invitation, status=AssessmentInvitationStatus.SENT, sent_at=datetime.now(UTC)
        )

    async def mark_opened(self, invitation: AssessmentInvitation) -> AssessmentInvitation:
        return await self.update(
            invitation, status=AssessmentInvitationStatus.OPENED, opened_at=datetime.now(UTC)
        )

    async def mark_started(self, invitation: AssessmentInvitation) -> AssessmentInvitation:
        return await self.update(
            invitation, status=AssessmentInvitationStatus.STARTED, started_at=datetime.now(UTC)
        )

    async def mark_completed(self, invitation: AssessmentInvitation) -> AssessmentInvitation:
        return await self.update(
            invitation,
            status=AssessmentInvitationStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )

    async def expire(self, invitation: AssessmentInvitation) -> AssessmentInvitation:
        return await self.update(invitation, status=AssessmentInvitationStatus.EXPIRED)

    async def revoke(self, invitation: AssessmentInvitation) -> AssessmentInvitation:
        return await self.update(invitation, status=AssessmentInvitationStatus.REVOKED)
