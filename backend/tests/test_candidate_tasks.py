"""
Unit tests for the candidate tasks endpoints:
  - GET/POST /candidates/{id}/tasks
  - PATCH /candidates/{id}/tasks/{task_id}
  - POST /candidates/{id}/tasks/{task_id}/complete
  - PATCH /candidates/{id}/tasks/{task_id}/reassign
  - DELETE /candidates/{id}/tasks/{task_id}

Strategy mirrors test_candidate_notes.py: CandidateTaskService is mocked via
dependency override.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.candidate_profile import get_candidate_task_service
from app.main import app
from app.models.candidate_task import CandidateTask, TaskPriority, TaskStatus
from app.models.user import User, UserRole

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


def make_task(**overrides) -> CandidateTask:
    now = datetime.now(UTC)
    task = CandidateTask(
        id=overrides.get("id", uuid.uuid4()),
        resume_file_id=overrides.get("resume_file_id", uuid.uuid4()),
        title=overrides.get("title", "Call candidate"),
        description=overrides.get("description"),
        due_date=overrides.get("due_date"),
        priority=overrides.get("priority", TaskPriority.MEDIUM),
        status=overrides.get("status", TaskStatus.OPEN),
        assignee_id=overrides.get("assignee_id"),
        created_by_id=overrides.get("created_by_id"),
        completed_at=overrides.get("completed_at"),
        created_at=now,
        updated_at=now,
    )
    # assignee/created_by are lazy="raise" — transient objects need them
    # explicitly set (even to None) before Pydantic's from_attributes reads them.
    task.assignee = overrides.get("assignee")
    task.created_by = overrides.get("created_by")
    return task


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_candidate_task_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_candidate_task_service, None)


@pytest.fixture
def recruiter():
    user = make_user(role=UserRole.RECRUITER)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def candidate_role():
    user = make_user(role=UserRole.CANDIDATE)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


class TestListTasks:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/tasks"

    async def test_returns_tasks(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.list = AsyncMock(return_value=[make_task(title="Review resume")])

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 200
        body = res.json()
        assert len(body) == 1
        assert body[0]["title"] == "Review resume"
        assert body[0]["status"] == "OPEN"

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 403
        mock_service.list.assert_not_called()


class TestCreateTask:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/tasks"

    async def test_creates_task(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        task = make_task(title="Schedule interview", priority=TaskPriority.HIGH)
        mock_service.create = AsyncMock(return_value=task)

        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()),
            json={"title": "Schedule interview", "priority": "HIGH"},
        )

        assert res.status_code == 201
        body = res.json()
        assert body["title"] == "Schedule interview"
        assert body["priority"] == "HIGH"

    async def test_empty_title_rejected(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json={"title": ""})
        assert res.status_code == 422
        mock_service.create.assert_not_called()

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json={"title": "Follow up"})
        assert res.status_code == 403
        mock_service.create.assert_not_called()


class TestUpdateTask:
    def _url(self, id_: uuid.UUID, task_id: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/tasks/{task_id}"

    async def test_updates_task(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        task_id = uuid.uuid4()
        mock_service.update = AsyncMock(return_value=make_task(id=task_id, title="Updated title"))

        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4(), task_id), json={"title": "Updated title"}
        )

        assert res.status_code == 200
        assert res.json()["title"] == "Updated title"

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4(), uuid.uuid4()), json={"title": "x"}
        )
        assert res.status_code == 403
        mock_service.update.assert_not_called()


class TestCompleteTask:
    def _url(self, id_: uuid.UUID, task_id: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/tasks/{task_id}/complete"

    async def test_completes_task(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        task_id = uuid.uuid4()
        mock_service.complete = AsyncMock(
            return_value=make_task(
                id=task_id, status=TaskStatus.COMPLETED, completed_at=datetime.now(UTC)
            )
        )

        res = await client_no_lifespan.post(self._url(uuid.uuid4(), task_id))

        assert res.status_code == 200
        assert res.json()["status"] == "COMPLETED"

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(self._url(uuid.uuid4(), uuid.uuid4()))
        assert res.status_code == 403
        mock_service.complete.assert_not_called()


class TestReassignTask:
    def _url(self, id_: uuid.UUID, task_id: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/tasks/{task_id}/reassign"

    async def test_reassigns_task(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        task_id = uuid.uuid4()
        new_assignee_id = uuid.uuid4()
        mock_service.reassign = AsyncMock(
            return_value=make_task(id=task_id, assignee_id=new_assignee_id)
        )

        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4(), task_id), json={"assignee_id": str(new_assignee_id)}
        )

        assert res.status_code == 200

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4(), uuid.uuid4()), json={"assignee_id": None}
        )
        assert res.status_code == 403
        mock_service.reassign.assert_not_called()


class TestDeleteTask:
    def _url(self, id_: uuid.UUID, task_id: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/tasks/{task_id}"

    async def test_deletes_task(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.delete = AsyncMock(return_value=None)

        res = await client_no_lifespan.delete(self._url(uuid.uuid4(), uuid.uuid4()))

        assert res.status_code == 204

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.delete(self._url(uuid.uuid4(), uuid.uuid4()))
        assert res.status_code == 403
        mock_service.delete.assert_not_called()
