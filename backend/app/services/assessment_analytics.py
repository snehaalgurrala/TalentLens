"""AssessmentAnalyticsService — recruiter-facing aggregate metrics over
assessment sessions, communication assessments, and invitations for an
organization (optionally scoped to one campaign).

Read-only, no AI: composes existing repository reads (the same
list_by_org/list_by_session_ids methods the sessions-list and dashboard
features already use) and reduces them in Python rather than issuing new
raw-SQL aggregate queries, keeping every number traceable back to a real row.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.models.assessment_invitation import AssessmentInvitationStatus
from app.models.assessment_session import AssessmentSessionStatus
from app.models.communication_assessment import CommunicationAssessmentStatus
from app.schemas.assessment_analytics import (
    AssessmentAnalyticsResponse,
    CompletionTrendPoint,
    PerformerEntry,
    ScoreDistributionBucket,
)

if TYPE_CHECKING:
    from app.models.assessment_session import AssessmentSession
    from app.models.communication_assessment import CommunicationAssessment
    from app.models.user import User
    from app.repositories.assessment_invitation import AssessmentInvitationRepository
    from app.repositories.assessment_session import AssessmentSessionRepository
    from app.repositories.communication_assessment import CommunicationAssessmentRepository

_TOP_N = 5
_TREND_DAYS = 14
_SCORE_BUCKETS = [(0, 20), (21, 40), (41, 60), (61, 80), (81, 100)]
_ACCEPTED_INVITATION_STATUSES = (
    AssessmentInvitationStatus.OPENED,
    AssessmentInvitationStatus.STARTED,
    AssessmentInvitationStatus.COMPLETED,
)


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _to_performer(
    assessment_session: AssessmentSession, communication_assessment: CommunicationAssessment
) -> PerformerEntry:
    candidate = assessment_session.candidate
    return PerformerEntry(
        session_id=assessment_session.id,
        candidate_name=f"{candidate.first_name} {candidate.last_name}",
        campaign_title=assessment_session.campaign.title,
        overall_score=communication_assessment.overall_score,
    )


class AssessmentAnalyticsService:
    def __init__(
        self,
        session_repo: AssessmentSessionRepository,
        communication_assessment_repo: CommunicationAssessmentRepository,
        invitation_repo: AssessmentInvitationRepository,
    ) -> None:
        self.session_repo = session_repo
        self.communication_assessment_repo = communication_assessment_repo
        self.invitation_repo = invitation_repo

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view assessment analytics.",
            )
        return user.org_id

    async def get_summary(
        self, user: User, campaign_id: uuid.UUID | None = None
    ) -> AssessmentAnalyticsResponse:
        org_id = self._require_org(user)

        sessions = await self.session_repo.list_by_org(org_id, campaign_id)
        comm_assessments = await self.communication_assessment_repo.list_by_session_ids(
            [s.id for s in sessions]
        )
        comm_by_session = {c.assessment_session_id: c for c in comm_assessments}

        invitations = await self.invitation_repo.list_by_org(org_id)
        if campaign_id is not None:
            invitations = [i for i in invitations if i.campaign_id == campaign_id]

        total_sessions = len(sessions)
        completed_sessions = sum(
            1 for s in sessions if s.status == AssessmentSessionStatus.COMPLETED
        )
        completion_rate = (
            round(completed_sessions / total_sessions * 100, 1) if total_sessions else 0.0
        )

        completed_comm = [
            c for c in comm_assessments if c.status == CommunicationAssessmentStatus.COMPLETED
        ]
        average_communication_score = _avg(
            [c.overall_score for c in completed_comm if c.overall_score is not None]
        )
        average_read_aloud_score = _avg(
            [c.reading_score for c in completed_comm if c.reading_score is not None]
        )
        average_listen_repeat_score = _avg(
            [c.listening_score for c in completed_comm if c.listening_score is not None]
        )

        sent_invitations = [
            i for i in invitations if i.status != AssessmentInvitationStatus.PENDING
        ]
        accepted_invitations = [
            i for i in sent_invitations if i.status in _ACCEPTED_INVITATION_STATUSES
        ]
        invitation_acceptance_rate = (
            round(len(accepted_invitations) / len(sent_invitations) * 100, 1)
            if sent_invitations
            else 0.0
        )

        scored = sorted(
            (
                (s, comm_by_session[s.id])
                for s in sessions
                if s.id in comm_by_session and comm_by_session[s.id].overall_score is not None
            ),
            key=lambda pair: pair[1].overall_score,
            reverse=True,
        )
        # On small datasets top/bottom N can overlap or repeat — expected
        # while an org has fewer completed assessments than 2x _TOP_N.
        top_performers = [_to_performer(s, c) for s, c in scored[:_TOP_N]]
        lowest_performers = [_to_performer(s, c) for s, c in reversed(scored[-_TOP_N:])]

        score_distribution = [
            ScoreDistributionBucket(
                label=f"{lo}-{hi}",
                count=sum(1 for _, c in scored if lo <= c.overall_score <= hi),
            )
            for lo, hi in _SCORE_BUCKETS
        ]

        today = datetime.now(UTC).date()
        completed_by_date: dict[object, int] = defaultdict(int)
        for s in sessions:
            if s.completed_at is not None:
                completed_by_date[s.completed_at.date()] += 1
        completion_trend = [
            CompletionTrendPoint(
                date=(today - timedelta(days=offset)).isoformat(),
                completed_count=completed_by_date.get(today - timedelta(days=offset), 0),
            )
            for offset in range(_TREND_DAYS - 1, -1, -1)
        ]

        return AssessmentAnalyticsResponse(
            total_sessions=total_sessions,
            completed_sessions=completed_sessions,
            completion_rate=completion_rate,
            average_communication_score=average_communication_score,
            average_read_aloud_score=average_read_aloud_score,
            average_listen_repeat_score=average_listen_repeat_score,
            total_invitations_sent=len(sent_invitations),
            invitations_accepted=len(accepted_invitations),
            invitation_acceptance_rate=invitation_acceptance_rate,
            top_performers=top_performers,
            lowest_performers=lowest_performers,
            score_distribution=score_distribution,
            completion_trend=completion_trend,
        )
