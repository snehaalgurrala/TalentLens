"""
Unit tests for the assessment invitation endpoints:
  - POST /api/v1/assessment/invitations/send
  - GET  /api/v1/assessment/invitations/{token}

Strategy mirrors test_organizations.py / test_assessment_sessions.py:
AssessmentInvitationService is mocked via dependency override; RBAC is
exercised for the recruiter-only send endpoint. The token-lookup endpoint is
public, so no get_current_user override is needed for it.
"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.assessment_invitations import get_assessment_invitation_service
from app.main import app
from app.models.assessment_invitation import AssessmentInvitationStatus
from app.models.assessment_session import AssessmentSessionStatus
from app.models.user import User, UserRole
from app.schemas.assessment_invitation import (
    AssessmentInvitationCampaignInfo,
    AssessmentInvitationDetailResponse,
    AssessmentInvitationSendFailure,
    AssessmentInvitationSendResult,
    AssessmentInvitationSendSuccess,
    AssessmentInvitationSessionInfo,
)

_ORG_ID = uuid.uuid4()


def make_user(role: UserRole = UserRole.RECRUITER, org_id: uuid.UUID | None = _ORG_ID) -> User:
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        full_name="Test User",
        password_hash="$2b$12$irrelevant",
        role=role,
        org_id=org_id,
        is_active=True,
        refresh_token_hash=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_assessment_invitation_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_assessment_invitation_service, None)


@pytest.fixture
def recruiter():
    user = make_user(role=UserRole.RECRUITER)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def candidate_role_user():
    user = make_user(role=UserRole.CANDIDATE)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


# ── POST /send ───────────────────────────────────────────────────────────────


class TestSendInvitations:
    _url = "/api/v1/assessment/invitations/send"

    def _payload(self, **overrides) -> dict:
        payload = {
            "campaign_id": str(uuid.uuid4()),
            "candidate_ids": [str(uuid.uuid4())],
            "expiration_hours": 48,
        }
        payload.update(overrides)
        return payload

    async def test_recruiter_can_send_returns_201(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter
    ):
        candidate_id = uuid.uuid4()
        mock_service.send_invitations = AsyncMock(
            return_value=AssessmentInvitationSendResult(
                succeeded=[
                    AssessmentInvitationSendSuccess(
                        candidate_id=candidate_id, invitation_id=uuid.uuid4()
                    )
                ],
                failed=[],
            )
        )

        res = await client_no_lifespan.post(
            self._url, json=self._payload(candidate_ids=[str(candidate_id)])
        )

        assert res.status_code == 201
        body = res.json()
        assert body["succeeded"][0]["candidate_id"] == str(candidate_id)
        assert body["failed"] == []

    async def test_partial_failure_is_still_201(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter
    ):
        candidate_id = uuid.uuid4()
        mock_service.send_invitations = AsyncMock(
            return_value=AssessmentInvitationSendResult(
                succeeded=[],
                failed=[
                    AssessmentInvitationSendFailure(
                        candidate_id=candidate_id, reason="Candidate has no email on file."
                    )
                ],
            )
        )

        res = await client_no_lifespan.post(
            self._url, json=self._payload(candidate_ids=[str(candidate_id)])
        )

        assert res.status_code == 201
        body = res.json()
        assert body["succeeded"] == []
        assert body["failed"][0]["reason"] == "Candidate has no email on file."

    async def test_candidate_role_cannot_send_returns_403(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role_user
    ):
        res = await client_no_lifespan.post(self._url, json=self._payload())
        assert res.status_code == 403

    async def test_campaign_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter
    ):
        mock_service.send_invitations = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.post(self._url, json=self._payload())
        assert res.status_code == 404

    async def test_empty_candidate_ids_returns_422(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter
    ):
        res = await client_no_lifespan.post(self._url, json=self._payload(candidate_ids=[]))
        assert res.status_code == 422

    async def test_zero_expiration_hours_returns_422(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter
    ):
        res = await client_no_lifespan.post(self._url, json=self._payload(expiration_hours=0))
        assert res.status_code == 422


# ── GET /{token} ─────────────────────────────────────────────────────────────


class TestGetInvitationByToken:
    def _url(self, token: str) -> str:
        return f"/api/v1/assessment/invitations/{token}"

    async def test_valid_token_returns_200(self, client_no_lifespan: AsyncClient, mock_service):
        detail = AssessmentInvitationDetailResponse(
            assessment_session=AssessmentInvitationSessionInfo(
                id=uuid.uuid4(), status=AssessmentSessionStatus.IN_PROGRESS
            ),
            campaign=AssessmentInvitationCampaignInfo(id=uuid.uuid4(), title="Backend Engineer"),
            candidate_display_name="Jane Doe",
            status=AssessmentInvitationStatus.OPENED,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        mock_service.get_invitation_by_token = AsyncMock(return_value=detail)

        res = await client_no_lifespan.get(self._url("valid-token"))

        assert res.status_code == 200
        body = res.json()
        assert body["candidate_display_name"] == "Jane Doe"
        assert body["campaign"]["title"] == "Backend Engineer"
        assert body["status"] == "OPENED"

    async def test_unknown_token_returns_404(self, client_no_lifespan: AsyncClient, mock_service):
        mock_service.get_invitation_by_token = AsyncMock(
            side_effect=HTTPException(404, "Invitation not found.")
        )
        res = await client_no_lifespan.get(self._url("bogus"))
        assert res.status_code == 404

    async def test_expired_token_returns_410(self, client_no_lifespan: AsyncClient, mock_service):
        mock_service.get_invitation_by_token = AsyncMock(
            side_effect=HTTPException(410, "This invitation has expired.")
        )
        res = await client_no_lifespan.get(self._url("expired"))
        assert res.status_code == 410

    async def test_revoked_token_returns_410(self, client_no_lifespan: AsyncClient, mock_service):
        mock_service.get_invitation_by_token = AsyncMock(
            side_effect=HTTPException(410, "This invitation has been revoked.")
        )
        res = await client_no_lifespan.get(self._url("revoked"))
        assert res.status_code == 410

    async def test_no_auth_required_for_token_lookup(
        self, client_no_lifespan: AsyncClient, mock_service
    ):
        """No get_current_user override is installed in this test — the
        request must still succeed, proving the endpoint has no RBAC
        dependency."""
        detail = AssessmentInvitationDetailResponse(
            assessment_session=AssessmentInvitationSessionInfo(
                id=uuid.uuid4(), status=AssessmentSessionStatus.IN_PROGRESS
            ),
            campaign=AssessmentInvitationCampaignInfo(id=uuid.uuid4(), title="Backend Engineer"),
            candidate_display_name="Jane Doe",
            status=AssessmentInvitationStatus.SENT,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        mock_service.get_invitation_by_token = AsyncMock(return_value=detail)

        res = await client_no_lifespan.get(self._url("valid-token"))

        assert res.status_code == 200


# ── POST /{token}/start ──────────────────────────────────────────────────────


class TestStartInvitation:
    def _url(self, token: str) -> str:
        return f"/api/v1/assessment/invitations/{token}/start"

    def _detail(self, invitation_status: AssessmentInvitationStatus) -> AssessmentInvitationDetailResponse:
        return AssessmentInvitationDetailResponse(
            assessment_session=AssessmentInvitationSessionInfo(
                id=uuid.uuid4(), status=AssessmentSessionStatus.IN_PROGRESS
            ),
            campaign=AssessmentInvitationCampaignInfo(id=uuid.uuid4(), title="Backend Engineer"),
            candidate_display_name="Jane Doe",
            status=invitation_status,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

    async def test_no_auth_required_and_returns_200(
        self, client_no_lifespan: AsyncClient, mock_service
    ):
        mock_service.mark_started = AsyncMock(
            return_value=self._detail(AssessmentInvitationStatus.STARTED)
        )
        res = await client_no_lifespan.post(self._url("valid-token"))
        assert res.status_code == 200
        assert res.json()["status"] == "STARTED"

    async def test_unknown_token_returns_404(self, client_no_lifespan: AsyncClient, mock_service):
        mock_service.mark_started = AsyncMock(side_effect=HTTPException(404, "Invitation not found."))
        res = await client_no_lifespan.post(self._url("bogus"))
        assert res.status_code == 404

    async def test_completed_invitation_returns_410(
        self, client_no_lifespan: AsyncClient, mock_service
    ):
        mock_service.mark_started = AsyncMock(
            side_effect=HTTPException(410, "This assessment has already been completed.")
        )
        res = await client_no_lifespan.post(self._url("completed"))
        assert res.status_code == 410


# ── POST /{token}/complete ───────────────────────────────────────────────────


class TestCompleteInvitation:
    def _url(self, token: str) -> str:
        return f"/api/v1/assessment/invitations/{token}/complete"

    def _detail(self, invitation_status: AssessmentInvitationStatus) -> AssessmentInvitationDetailResponse:
        return AssessmentInvitationDetailResponse(
            assessment_session=AssessmentInvitationSessionInfo(
                id=uuid.uuid4(), status=AssessmentSessionStatus.COMPLETED
            ),
            campaign=AssessmentInvitationCampaignInfo(id=uuid.uuid4(), title="Backend Engineer"),
            candidate_display_name="Jane Doe",
            status=invitation_status,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

    async def test_no_auth_required_and_returns_200(
        self, client_no_lifespan: AsyncClient, mock_service
    ):
        mock_service.mark_completed = AsyncMock(
            return_value=self._detail(AssessmentInvitationStatus.COMPLETED)
        )
        res = await client_no_lifespan.post(self._url("valid-token"))
        assert res.status_code == 200
        assert res.json()["status"] == "COMPLETED"

    async def test_unknown_token_returns_404(self, client_no_lifespan: AsyncClient, mock_service):
        mock_service.mark_completed = AsyncMock(
            side_effect=HTTPException(404, "Invitation not found.")
        )
        res = await client_no_lifespan.post(self._url("bogus"))
        assert res.status_code == 404

    async def test_revoked_invitation_returns_410(
        self, client_no_lifespan: AsyncClient, mock_service
    ):
        mock_service.mark_completed = AsyncMock(
            side_effect=HTTPException(410, "This invitation has been revoked.")
        )
        res = await client_no_lifespan.post(self._url("revoked"))
        assert res.status_code == 410
