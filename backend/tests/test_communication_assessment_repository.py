"""Direct unit tests for CommunicationAssessmentRepository against a
lightweight fake AsyncSession (add/execute/flush/refresh mocked individually,
no real DB)."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.communication_assessment import (
    CommunicationAssessment,
    CommunicationAssessmentStatus,
)
from app.repositories.communication_assessment import CommunicationAssessmentRepository

_ORG_ID = uuid.uuid4()


def _make_row(**overrides) -> CommunicationAssessment:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        assessment_session_id=uuid.uuid4(),
        status=CommunicationAssessmentStatus.PENDING,
        overall_score=None,
        reading_score=None,
        listening_score=None,
        confidence_score=None,
        strengths_json=None,
        improvements_json=None,
        summary_json=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return CommunicationAssessment(**defaults)


def _make_fake_session(execute_result=None):
    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result or MagicMock())
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


class TestGetBySessionId:
    async def test_returns_row_when_present(self):
        row = _make_row()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=row)
        session = _make_fake_session(execute_result)
        repo = CommunicationAssessmentRepository(session)

        result = await repo.get_by_session_id(row.assessment_session_id)

        assert result is row
        session.execute.assert_awaited_once()

    async def test_returns_none_when_absent(self):
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        session = _make_fake_session(execute_result)
        repo = CommunicationAssessmentRepository(session)

        result = await repo.get_by_session_id(uuid.uuid4())

        assert result is None


class TestCreate:
    async def test_adds_flushes_refreshes_and_returns_row(self):
        session = _make_fake_session()
        repo = CommunicationAssessmentRepository(session)
        assessment_session_id = uuid.uuid4()

        created = await repo.create(
            assessment_session_id, _ORG_ID, status=CommunicationAssessmentStatus.PENDING
        )

        assert created.assessment_session_id == assessment_session_id
        assert created.organization_id == _ORG_ID
        assert created.status == CommunicationAssessmentStatus.PENDING
        session.add.assert_called_once_with(created)
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once_with(created)


class TestUpdate:
    async def test_sets_attributes_flushes_and_refreshes(self):
        row = _make_row()
        session = _make_fake_session()
        repo = CommunicationAssessmentRepository(session)

        updated = await repo.update(
            row, status=CommunicationAssessmentStatus.COMPLETED, overall_score=88.0
        )

        assert updated is row
        assert updated.status == CommunicationAssessmentStatus.COMPLETED
        assert updated.overall_score == 88.0
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once_with(row)
