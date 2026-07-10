"""Direct unit tests for AssessmentInvitationRepository against a lightweight
fake AsyncSession (add/execute/flush/refresh mocked individually, no real
DB)."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.models.assessment_invitation import AssessmentInvitation, AssessmentInvitationStatus
from app.repositories.assessment_invitation import AssessmentInvitationRepository

_ORG_ID = uuid.uuid4()


def _make_row(**overrides) -> AssessmentInvitation:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        assessment_session_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        token_hash="deadbeef",
        status=AssessmentInvitationStatus.PENDING,
        expires_at=now + timedelta(hours=48),
        sent_at=None,
        opened_at=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentInvitation(**defaults)


def _make_fake_session(execute_result=None):
    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result or MagicMock())
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


class TestGetByTokenHash:
    async def test_returns_row_when_present(self):
        row = _make_row()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=row)
        session = _make_fake_session(execute_result)
        repo = AssessmentInvitationRepository(session)

        result = await repo.get_by_token_hash(row.token_hash)

        assert result is row
        session.execute.assert_awaited_once()

    async def test_returns_none_when_absent(self):
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        session = _make_fake_session(execute_result)
        repo = AssessmentInvitationRepository(session)

        result = await repo.get_by_token_hash("nonexistent")

        assert result is None


class TestGetBySession:
    async def test_returns_row_when_present(self):
        row = _make_row()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=row)
        session = _make_fake_session(execute_result)
        repo = AssessmentInvitationRepository(session)

        result = await repo.get_by_session(row.assessment_session_id)

        assert result is row


class TestCreate:
    async def test_adds_flushes_refreshes_and_returns_row(self):
        session = _make_fake_session()
        repo = AssessmentInvitationRepository(session)
        assessment_session_id = uuid.uuid4()

        created = await repo.create(
            organization_id=_ORG_ID,
            assessment_session_id=assessment_session_id,
            candidate_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            token_hash="abc123",
            status=AssessmentInvitationStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

        assert created.assessment_session_id == assessment_session_id
        assert created.organization_id == _ORG_ID
        assert created.status == AssessmentInvitationStatus.PENDING
        session.add.assert_called_once_with(created)
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once_with(created)


class TestUpdate:
    async def test_sets_attributes_flushes_and_refreshes(self):
        row = _make_row()
        session = _make_fake_session()
        repo = AssessmentInvitationRepository(session)

        updated = await repo.update(row, status=AssessmentInvitationStatus.SENT, token_hash="new")

        assert updated is row
        assert updated.status == AssessmentInvitationStatus.SENT
        assert updated.token_hash == "new"
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once_with(row)


class TestLifecycleTransitions:
    async def test_mark_sent_sets_status_and_timestamp(self):
        row = _make_row()
        session = _make_fake_session()
        repo = AssessmentInvitationRepository(session)

        updated = await repo.mark_sent(row)

        assert updated.status == AssessmentInvitationStatus.SENT
        assert updated.sent_at is not None

    async def test_mark_opened_sets_status_and_timestamp(self):
        row = _make_row()
        session = _make_fake_session()
        repo = AssessmentInvitationRepository(session)

        updated = await repo.mark_opened(row)

        assert updated.status == AssessmentInvitationStatus.OPENED
        assert updated.opened_at is not None

    async def test_mark_started_sets_status_and_timestamp(self):
        row = _make_row()
        session = _make_fake_session()
        repo = AssessmentInvitationRepository(session)

        updated = await repo.mark_started(row)

        assert updated.status == AssessmentInvitationStatus.STARTED
        assert updated.started_at is not None

    async def test_mark_completed_sets_status_and_timestamp(self):
        row = _make_row()
        session = _make_fake_session()
        repo = AssessmentInvitationRepository(session)

        updated = await repo.mark_completed(row)

        assert updated.status == AssessmentInvitationStatus.COMPLETED
        assert updated.completed_at is not None

    async def test_expire_sets_status(self):
        row = _make_row()
        session = _make_fake_session()
        repo = AssessmentInvitationRepository(session)

        updated = await repo.expire(row)

        assert updated.status == AssessmentInvitationStatus.EXPIRED

    async def test_revoke_sets_status(self):
        row = _make_row()
        session = _make_fake_session()
        repo = AssessmentInvitationRepository(session)

        updated = await repo.revoke(row)

        assert updated.status == AssessmentInvitationStatus.REVOKED
