"""Unit tests for resolve_recording_upload_org_id — the dependency that
authorizes POST /assessment/session/{id}/recordings/{type}/upload via
EITHER a recruiter/admin JWT (existing dev-testing path) OR a candidate's
own invitation token scoped to this exact session (candidates have no
platform account). Repositories are patched at the class level; no real DB.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.assessment_sessions import resolve_recording_upload_org_id
from app.core.security import create_access_token, hash_token
from app.models.assessment_invitation import AssessmentInvitation, AssessmentInvitationStatus
from app.models.user import User, UserRole

_ORG_ID = uuid.uuid4()
_SESSION_ID = uuid.uuid4()


def make_user(role: UserRole = UserRole.RECRUITER, is_active: bool = True) -> User:
    return User(
        id=uuid.uuid4(),
        email="recruiter@example.com",
        full_name="Recruiter",
        password_hash="$2b$12$irrelevant",
        role=role,
        org_id=_ORG_ID,
        is_active=is_active,
        refresh_token_hash=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_invitation(**overrides) -> AssessmentInvitation:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        assessment_session_id=_SESSION_ID,
        candidate_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        token_hash="irrelevant",
        status=AssessmentInvitationStatus.SENT,
        expires_at=now + timedelta(hours=1),
        sent_at=now,
        opened_at=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentInvitation(**defaults)


class TestRecruiterJwtPath:
    async def test_valid_recruiter_jwt_returns_org_id(self):
        user = make_user(role=UserRole.RECRUITER)
        token = create_access_token(user_id=str(user.id), role=user.role.value, org_id=str(user.org_id))

        with patch(
            "app.repositories.user.UserRepository.get_by_id", AsyncMock(return_value=user)
        ):
            org_id = await resolve_recording_upload_org_id(
                _SESSION_ID, db=object(), token=token, x_assessment_token=None
            )

        assert org_id == _ORG_ID

    async def test_admin_role_also_accepted(self):
        user = make_user(role=UserRole.ORG_ADMIN)
        token = create_access_token(user_id=str(user.id), role=user.role.value, org_id=str(user.org_id))

        with patch(
            "app.repositories.user.UserRepository.get_by_id", AsyncMock(return_value=user)
        ):
            org_id = await resolve_recording_upload_org_id(
                _SESSION_ID, db=object(), token=token, x_assessment_token=None
            )

        assert org_id == _ORG_ID

    async def test_candidate_role_jwt_is_rejected_without_invitation_token(self):
        user = make_user(role=UserRole.CANDIDATE)
        token = create_access_token(user_id=str(user.id), role=user.role.value, org_id=str(user.org_id))

        with patch(
            "app.repositories.user.UserRepository.get_by_id", AsyncMock(return_value=user)
        ):
            with pytest.raises(HTTPException) as exc_info:
                await resolve_recording_upload_org_id(
                    _SESSION_ID, db=object(), token=token, x_assessment_token=None
                )

        assert exc_info.value.status_code == 401

    async def test_inactive_user_is_rejected(self):
        user = make_user(role=UserRole.RECRUITER, is_active=False)
        token = create_access_token(user_id=str(user.id), role=user.role.value, org_id=str(user.org_id))

        with patch(
            "app.repositories.user.UserRepository.get_by_id", AsyncMock(return_value=user)
        ):
            with pytest.raises(HTTPException) as exc_info:
                await resolve_recording_upload_org_id(
                    _SESSION_ID, db=object(), token=token, x_assessment_token=None
                )

        assert exc_info.value.status_code == 401

    async def test_garbage_token_falls_through_to_401_with_no_invitation_token(self):
        with pytest.raises(HTTPException) as exc_info:
            await resolve_recording_upload_org_id(
                _SESSION_ID, db=object(), token="not-a-real-jwt", x_assessment_token=None
            )

        assert exc_info.value.status_code == 401


class TestInvitationTokenPath:
    async def test_valid_invitation_token_returns_organization_id(self):
        invitation = make_invitation(status=AssessmentInvitationStatus.SENT)

        with patch(
            "app.repositories.assessment_invitation.AssessmentInvitationRepository.get_by_token_hash",
            AsyncMock(return_value=invitation),
        ):
            org_id = await resolve_recording_upload_org_id(
                _SESSION_ID, db=object(), token=None, x_assessment_token="raw-token"
            )

        assert org_id == _ORG_ID

    async def test_token_for_a_different_session_is_rejected(self):
        invitation = make_invitation(assessment_session_id=uuid.uuid4())

        with patch(
            "app.repositories.assessment_invitation.AssessmentInvitationRepository.get_by_token_hash",
            AsyncMock(return_value=invitation),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await resolve_recording_upload_org_id(
                    _SESSION_ID, db=object(), token=None, x_assessment_token="raw-token"
                )

        assert exc_info.value.status_code == 401

    async def test_revoked_invitation_is_rejected(self):
        invitation = make_invitation(status=AssessmentInvitationStatus.REVOKED)

        with patch(
            "app.repositories.assessment_invitation.AssessmentInvitationRepository.get_by_token_hash",
            AsyncMock(return_value=invitation),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await resolve_recording_upload_org_id(
                    _SESSION_ID, db=object(), token=None, x_assessment_token="raw-token"
                )

        assert exc_info.value.status_code == 401

    async def test_expired_invitation_is_rejected(self):
        invitation = make_invitation(expires_at=datetime.now(UTC) - timedelta(hours=1))

        with patch(
            "app.repositories.assessment_invitation.AssessmentInvitationRepository.get_by_token_hash",
            AsyncMock(return_value=invitation),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await resolve_recording_upload_org_id(
                    _SESSION_ID, db=object(), token=None, x_assessment_token="raw-token"
                )

        assert exc_info.value.status_code == 401

    async def test_unknown_token_is_rejected(self):
        with patch(
            "app.repositories.assessment_invitation.AssessmentInvitationRepository.get_by_token_hash",
            AsyncMock(return_value=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await resolve_recording_upload_org_id(
                    _SESSION_ID, db=object(), token=None, x_assessment_token="raw-token"
                )

        assert exc_info.value.status_code == 401

    async def test_hashes_the_raw_token_before_lookup(self):
        invitation = make_invitation()
        mock_lookup = AsyncMock(return_value=invitation)

        with patch(
            "app.repositories.assessment_invitation.AssessmentInvitationRepository.get_by_token_hash",
            mock_lookup,
        ):
            await resolve_recording_upload_org_id(
                _SESSION_ID, db=object(), token=None, x_assessment_token="raw-token"
            )

        mock_lookup.assert_awaited_once_with(hash_token("raw-token"))


class TestNoCredentials:
    async def test_neither_token_nor_header_returns_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await resolve_recording_upload_org_id(
                _SESSION_ID, db=object(), token=None, x_assessment_token=None
            )

        assert exc_info.value.status_code == 401
