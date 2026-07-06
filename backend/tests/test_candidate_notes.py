"""
Unit tests for the candidate notes endpoints:
  - GET/POST /candidates/{id}/notes
  - PATCH/DELETE /candidates/{id}/notes/{note_id}

Strategy mirrors test_candidate_management.py: CandidateNoteService is
mocked via dependency override; ownership (edit/delete own only) is
exercised through the service's HTTPException behavior, since the
service itself is mocked here (ownership logic has its own unit tests
implicitly covered by the 403 the service raises).
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.candidate_profile import get_candidate_note_service
from app.main import app
from app.models.candidate_note import CandidateNote
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


def make_note(author_id: uuid.UUID, **overrides) -> CandidateNote:
    now = datetime.now(UTC)
    note = CandidateNote(
        id=overrides.get("id", uuid.uuid4()),
        resume_file_id=overrides.get("resume_file_id", uuid.uuid4()),
        author_id=author_id,
        body=overrides.get("body", "Strong candidate, move forward."),
        created_at=now,
        updated_at=now,
        is_pinned=overrides.get("is_pinned", False),
        mentioned_user_ids=overrides.get("mentioned_user_ids", []),
    )
    # `author` is lazy="raise" — a transient object needs it explicitly set
    # (even to None) or Pydantic's from_attributes read will trigger a raise.
    # The endpoint only reads .author when author_id != the acting user, so
    # tests exercising that path must pass an explicit `author=`.
    note.author = overrides.get("author")
    return note


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_candidate_note_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_candidate_note_service, None)


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


class TestListNotes:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/notes"

    async def test_returns_notes_with_can_edit_flag(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        other_author = make_user(role=UserRole.RECRUITER)
        own_note = make_note(recruiter.id, body="My note")
        other_note = make_note(other_author.id, body="Someone else's note", author=other_author)
        mock_service.list = AsyncMock(return_value=[own_note, other_note])

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 200
        body = res.json()
        assert len(body) == 2
        assert body[0]["can_edit"] is True
        assert body[1]["can_edit"] is False
        assert body[1]["author"]["id"] == str(other_author.id)

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 403
        mock_service.list.assert_not_called()


class TestCreateNote:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/notes"

    async def test_creates_note_authored_by_current_user(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        note = make_note(recruiter.id, body="Great communication skills.")
        mock_service.create = AsyncMock(return_value=note)

        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()), json={"body": "Great communication skills."}
        )

        assert res.status_code == 201
        body = res.json()
        assert body["body"] == "Great communication skills."
        assert body["can_edit"] is True
        assert body["author"]["id"] == str(recruiter.id)

    async def test_empty_body_rejected(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json={"body": ""})

        assert res.status_code == 422
        mock_service.create.assert_not_called()


class TestUpdateNote:
    def _url(self, id_: uuid.UUID, note_id: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/notes/{note_id}"

    async def test_updates_own_note(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        note_id = uuid.uuid4()
        updated = make_note(recruiter.id, id=note_id, body="Updated note.")
        mock_service.update = AsyncMock(return_value=updated)

        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4(), note_id), json={"body": "Updated note."}
        )

        assert res.status_code == 200
        assert res.json()["body"] == "Updated note."

    async def test_forbidden_editing_others_note_bubbles_403(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.update = AsyncMock(
            side_effect=HTTPException(
                status_code=403, detail="You can only edit or delete your own notes."
            )
        )

        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4(), uuid.uuid4()), json={"body": "Trying to edit."}
        )

        assert res.status_code == 403


class TestDeleteNote:
    def _url(self, id_: uuid.UUID, note_id: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/notes/{note_id}"

    async def test_deletes_own_note(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.delete = AsyncMock(return_value=None)

        res = await client_no_lifespan.delete(self._url(uuid.uuid4(), uuid.uuid4()))

        assert res.status_code == 204

    async def test_forbidden_deleting_others_note_bubbles_403(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.delete = AsyncMock(
            side_effect=HTTPException(
                status_code=403, detail="You can only edit or delete your own notes."
            )
        )

        res = await client_no_lifespan.delete(self._url(uuid.uuid4(), uuid.uuid4()))

        assert res.status_code == 403


class TestPinNote:
    def _url(self, id_: uuid.UUID, note_id: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/notes/{note_id}/pin"

    async def test_pins_someone_elses_note(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        other_author = make_user(role=UserRole.RECRUITER)
        note_id = uuid.uuid4()
        pinned = make_note(other_author.id, id=note_id, author=other_author, is_pinned=True)
        mock_service.pin = AsyncMock(return_value=pinned)

        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4(), note_id), json={"is_pinned": True}
        )

        assert res.status_code == 200
        assert res.json()["is_pinned"] is True

    async def test_unpins_note(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        note_id = uuid.uuid4()
        unpinned = make_note(recruiter.id, id=note_id, is_pinned=False)
        mock_service.pin = AsyncMock(return_value=unpinned)

        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4(), note_id), json={"is_pinned": False}
        )

        assert res.status_code == 200
        assert res.json()["is_pinned"] is False

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4(), uuid.uuid4()), json={"is_pinned": True}
        )
        assert res.status_code == 403
        mock_service.pin.assert_not_called()


class TestMentionedUserIdsRoundTrip:
    async def test_create_note_returns_mentioned_user_ids(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mentioned_id = uuid.uuid4()
        note = make_note(recruiter.id, body="cc @Jane", mentioned_user_ids=[mentioned_id])
        mock_service.create = AsyncMock(return_value=note)

        res = await client_no_lifespan.post(
            "/api/v1/candidates/{}/notes".format(uuid.uuid4()),
            json={"body": "cc @Jane", "mentioned_user_ids": [str(mentioned_id)]},
        )

        assert res.status_code == 201
        assert res.json()["mentioned_user_ids"] == [str(mentioned_id)]
