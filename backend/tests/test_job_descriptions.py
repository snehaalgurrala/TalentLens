"""
Unit tests for job description endpoints and service validation.

Strategy (endpoint tests):
  - get_job_description_service is overridden with a MagicMock — no database required.
  - get_current_user is overridden per-test to simulate different roles.
  - RequireRoles runs against the mocked user, so RBAC 403s are verified
    without any service involvement.
  - _enqueue_parse is patched (autouse) to prevent real Celery dispatch; the
    mock is also used to assert dispatch calls.

Strategy (service tests):
  - JobDescriptionService is instantiated directly with mocked repo and
    campaign_repo — tests exercise actual validation logic (text, extension, size).
"""
import io
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.api.deps import get_current_user
from app.api.v1.endpoints.job_descriptions import get_job_description_service
from app.main import app
from app.models.campaign import Campaign, CampaignStatus
from app.models.job_description import EmbeddingStatus, JobDescription, ParsingStatus
from app.models.user import User, UserRole
from app.services.job_description import JobDescriptionService

# ── Shared constants & factories ──────────────────────────────────────────────

_ORG_ID = uuid.uuid4()
_CAMPAIGN_ID = uuid.uuid4()


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


def make_job_description(user: User, **overrides) -> JobDescription:
    jd = JobDescription(
        id=uuid.uuid4(),
        campaign_id=_CAMPAIGN_ID,
        created_by=user.id,
        original_filename=None,
        raw_text="We are hiring a Senior Backend Engineer...",
        structured_json=None,
        parser_version=None,
        parsed_at=None,
        parsing_status=ParsingStatus.PENDING,
        parsing_error=None,
        embedding_status=EmbeddingStatus.PENDING,
        embedding_model=None,
        embedding_generated_at=None,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    for k, v in overrides.items():
        object.__setattr__(jd, k, v)
    return jd


def make_campaign(org_id: uuid.UUID = _ORG_ID) -> Campaign:
    return Campaign(
        id=_CAMPAIGN_ID,
        org_id=org_id,
        created_by=uuid.uuid4(),
        title="Test Campaign",
        description=None,
        status=CampaignStatus.ACTIVE,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_upload_file(
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> StarletteUploadFile:
    return StarletteUploadFile(
        filename=filename,
        file=io.BytesIO(content),
        size=len(content),
        headers={"content-type": content_type},
    )


# ── Endpoint fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_jd_service():
    svc = MagicMock()
    app.dependency_overrides[get_job_description_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_job_description_service, None)


@pytest.fixture
def recruiter():
    user = make_user(role=UserRole.RECRUITER)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def org_admin():
    user = make_user(role=UserRole.ORG_ADMIN)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def candidate():
    user = make_user(role=UserRole.CANDIDATE)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _no_celery():
    """Prevent real Celery dispatch in every test in this module."""
    with patch("app.api.v1.endpoints.job_descriptions._enqueue_parse") as m:
        yield m


# ── Paste (text) endpoint ─────────────────────────────────────────────────────


class TestCreateJobDescription:
    _url = f"/api/v1/campaigns/{_CAMPAIGN_ID}/job-descriptions"

    async def test_recruiter_can_paste_text(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User, _no_celery
    ):
        jd = make_job_description(recruiter)
        mock_jd_service.create_from_text = AsyncMock(return_value=jd)

        res = await client_no_lifespan.post(self._url, json={"text": "We are hiring..."})

        assert res.status_code == 201
        body = res.json()
        assert body["parsing_status"] == ParsingStatus.PENDING.value
        assert body["structured_json"] is None

    async def test_dispatches_parse_task(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User, _no_celery
    ):
        jd = make_job_description(recruiter)
        mock_jd_service.create_from_text = AsyncMock(return_value=jd)

        await client_no_lifespan.post(self._url, json={"text": "We are hiring..."})

        _no_celery.assert_called_once_with(str(jd.id))

    async def test_candidate_cannot_create(
        self, client_no_lifespan: AsyncClient, mock_jd_service, candidate: User
    ):
        res = await client_no_lifespan.post(self._url, json={"text": "We are hiring..."})
        assert res.status_code == 403

    async def test_empty_text_returns_422(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        mock_jd_service.create_from_text = AsyncMock(
            side_effect=HTTPException(422, "Job description text must not be empty.")
        )
        res = await client_no_lifespan.post(self._url, json={"text": "   "})
        assert res.status_code == 422

    async def test_campaign_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        mock_jd_service.create_from_text = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.post(self._url, json={"text": "We are hiring..."})
        assert res.status_code == 404

    async def test_unauthenticated_returns_401(
        self, client_no_lifespan: AsyncClient, mock_jd_service
    ):
        res = await client_no_lifespan.post(self._url, json={"text": "We are hiring..."})
        assert res.status_code == 401

    async def test_missing_body_field_returns_422(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        res = await client_no_lifespan.post(self._url, json={})
        assert res.status_code == 422


# ── Upload endpoint ───────────────────────────────────────────────────────────


class TestUploadJobDescription:
    _url = f"/api/v1/campaigns/{_CAMPAIGN_ID}/job-descriptions/upload"

    async def test_recruiter_can_upload_pdf(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User, _no_celery
    ):
        jd = make_job_description(recruiter, original_filename="jd.pdf")
        mock_jd_service.create_from_upload = AsyncMock(return_value=jd)

        res = await client_no_lifespan.post(
            self._url,
            files={"file": ("jd.pdf", b"%PDF-1.4 content", "application/pdf")},
        )

        assert res.status_code == 201
        assert res.json()["original_filename"] == "jd.pdf"

    async def test_dispatches_parse_task(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User, _no_celery
    ):
        jd = make_job_description(recruiter)
        mock_jd_service.create_from_upload = AsyncMock(return_value=jd)

        await client_no_lifespan.post(
            self._url,
            files={"file": ("jd.pdf", b"%PDF content", "application/pdf")},
        )

        _no_celery.assert_called_once_with(str(jd.id))

    async def test_candidate_cannot_upload(
        self, client_no_lifespan: AsyncClient, mock_jd_service, candidate: User
    ):
        res = await client_no_lifespan.post(
            self._url,
            files={"file": ("jd.pdf", b"content", "application/pdf")},
        )
        assert res.status_code == 403

    async def test_unsupported_file_type_returns_422(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        mock_jd_service.create_from_upload = AsyncMock(
            side_effect=HTTPException(422, "Unsupported extension '.exe'.")
        )
        res = await client_no_lifespan.post(
            self._url,
            files={"file": ("malware.exe", b"content", "application/octet-stream")},
        )
        assert res.status_code == 422

    async def test_unauthenticated_returns_401(
        self, client_no_lifespan: AsyncClient, mock_jd_service
    ):
        res = await client_no_lifespan.post(
            self._url,
            files={"file": ("jd.pdf", b"content", "application/pdf")},
        )
        assert res.status_code == 401


# ── Get job description (status polling) endpoint ─────────────────────────────


class TestGetJobDescription:
    async def test_returns_pending_status(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        jd = make_job_description(recruiter)
        mock_jd_service.get_by_id = AsyncMock(return_value=jd)

        res = await client_no_lifespan.get(f"/api/v1/job-descriptions/{jd.id}")

        assert res.status_code == 200
        assert res.json()["parsing_status"] == ParsingStatus.PENDING.value

    async def test_returns_completed_status_with_structured_json(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        jd = make_job_description(
            recruiter,
            parsing_status=ParsingStatus.COMPLETED,
            structured_json={"required_skills": ["Python"]},
            parser_version="v1",
            parsed_at=datetime.now(UTC),
        )
        mock_jd_service.get_by_id = AsyncMock(return_value=jd)

        res = await client_no_lifespan.get(f"/api/v1/job-descriptions/{jd.id}")

        assert res.status_code == 200
        body = res.json()
        assert body["parsing_status"] == ParsingStatus.COMPLETED.value
        assert body["structured_json"] == {"required_skills": ["Python"]}

    async def test_returns_failed_status_with_error(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        jd = make_job_description(
            recruiter,
            parsing_status=ParsingStatus.FAILED,
            parsing_error="AI service 503: server unavailable",
        )
        mock_jd_service.get_by_id = AsyncMock(return_value=jd)

        res = await client_no_lifespan.get(f"/api/v1/job-descriptions/{jd.id}")

        assert res.status_code == 200
        assert res.json()["parsing_error"] == "AI service 503: server unavailable"

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        mock_jd_service.get_by_id = AsyncMock(
            side_effect=HTTPException(404, "Job description not found.")
        )
        res = await client_no_lifespan.get(f"/api/v1/job-descriptions/{uuid.uuid4()}")
        assert res.status_code == 404

    async def test_candidate_can_view_status(
        self, client_no_lifespan: AsyncClient, mock_jd_service, candidate: User
    ):
        jd = make_job_description(make_user())
        mock_jd_service.get_by_id = AsyncMock(return_value=jd)

        res = await client_no_lifespan.get(f"/api/v1/job-descriptions/{jd.id}")
        assert res.status_code == 200


# ── List endpoint ─────────────────────────────────────────────────────────────


class TestListJobDescriptions:
    _url = f"/api/v1/campaigns/{_CAMPAIGN_ID}/job-descriptions"

    async def test_returns_job_descriptions_for_campaign(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        jds = [make_job_description(recruiter), make_job_description(recruiter)]
        mock_jd_service.list_by_campaign = AsyncMock(return_value=jds)

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        assert len(res.json()) == 2

    async def test_empty_list(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        mock_jd_service.list_by_campaign = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200
        assert res.json() == []

    async def test_campaign_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        mock_jd_service.list_by_campaign = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 404

    async def test_unauthenticated_returns_401(
        self, client_no_lifespan: AsyncClient, mock_jd_service
    ):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 401


# ── Delete endpoint ───────────────────────────────────────────────────────────


class TestDeleteJobDescription:
    async def test_recruiter_can_delete_own(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        mock_jd_service.delete = AsyncMock(return_value=None)
        res = await client_no_lifespan.delete(f"/api/v1/job-descriptions/{uuid.uuid4()}")
        assert res.status_code == 204

    async def test_candidate_cannot_delete(
        self, client_no_lifespan: AsyncClient, mock_jd_service, candidate: User
    ):
        res = await client_no_lifespan.delete(f"/api/v1/job-descriptions/{uuid.uuid4()}")
        assert res.status_code == 403

    async def test_not_owner_recruiter_gets_403(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        mock_jd_service.delete = AsyncMock(
            side_effect=HTTPException(403, "You do not have permission to delete this job description.")
        )
        res = await client_no_lifespan.delete(f"/api/v1/job-descriptions/{uuid.uuid4()}")
        assert res.status_code == 403

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_jd_service, recruiter: User
    ):
        mock_jd_service.delete = AsyncMock(
            side_effect=HTTPException(404, "Job description not found.")
        )
        res = await client_no_lifespan.delete(f"/api/v1/job-descriptions/{uuid.uuid4()}")
        assert res.status_code == 404


# ── Service validation (no HTTP layer) ───────────────────────────────────────


def _make_service() -> JobDescriptionService:
    from app.repositories.campaign import CampaignRepository
    from app.repositories.job_description import JobDescriptionRepository

    repo = MagicMock(spec=JobDescriptionRepository)
    campaign_repo = MagicMock(spec=CampaignRepository)
    repo.create = AsyncMock()
    campaign_repo.get_by_id = AsyncMock()
    return JobDescriptionService(repo, campaign_repo)


class TestServiceTextValidation:
    async def test_rejects_empty_text(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_from_text(_CAMPAIGN_ID, "   ", user)
        assert exc_info.value.status_code == 422

    async def test_rejects_text_over_limit(self, monkeypatch):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        monkeypatch.setattr("app.services.job_description._MAX_TEXT_LENGTH", 10)

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_from_text(_CAMPAIGN_ID, "x" * 100, user)
        assert exc_info.value.status_code == 422

    async def test_accepts_valid_text(self):
        svc = _make_service()
        user = make_user()
        campaign = make_campaign()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        jd = make_job_description(user)
        svc.repo.create = AsyncMock(return_value=jd)

        result = await svc.create_from_text(_CAMPAIGN_ID, "We are hiring...", user)

        assert result is jd
        svc.repo.create.assert_awaited_once()
        create_kwargs = svc.repo.create.call_args.kwargs
        assert create_kwargs["raw_text"] == "We are hiring..."
        assert create_kwargs["created_by"] == user.id

    async def test_campaign_not_found_raises_404(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_from_text(_CAMPAIGN_ID, "text", user)
        assert exc_info.value.status_code == 404

    async def test_user_without_org_raises_422(self):
        svc = _make_service()
        user = make_user(org_id=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_from_text(_CAMPAIGN_ID, "text", user)
        assert exc_info.value.status_code == 422


class TestServiceUploadValidation:
    async def test_rejects_unsupported_extension(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_from_upload(
                _CAMPAIGN_ID, make_upload_file("jd.txt", b"text content"), user
            )
        assert exc_info.value.status_code == 422
        assert ".txt" in exc_info.value.detail

    async def test_rejects_file_exceeding_size_limit(self, monkeypatch):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        monkeypatch.setattr("app.services.job_description.settings.MAX_UPLOAD_SIZE_MB", 0)

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_from_upload(
                _CAMPAIGN_ID, make_upload_file("jd.pdf", b"%PDF-1.4"), user
            )
        assert exc_info.value.status_code == 422
        assert "limit" in exc_info.value.detail

    async def test_accepts_pdf(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        jd = make_job_description(user, original_filename="jd.pdf")
        svc.repo.create = AsyncMock(return_value=jd)

        with patch(
            "app.services.job_description.extract_text_from_pdf_bytes",
            AsyncMock(return_value="extracted pdf text"),
        ):
            result = await svc.create_from_upload(
                _CAMPAIGN_ID,
                make_upload_file("jd.pdf", b"%PDF-1.4 content", "application/pdf"),
                user,
            )

        assert result is jd
        create_kwargs = svc.repo.create.call_args.kwargs
        assert create_kwargs["raw_text"] == "extracted pdf text"
        assert create_kwargs["original_filename"] == "jd.pdf"

    async def test_accepts_docx(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        jd = make_job_description(user, original_filename="jd.docx")
        svc.repo.create = AsyncMock(return_value=jd)

        with patch(
            "app.services.job_description.extract_text_from_docx_bytes",
            AsyncMock(return_value="extracted docx text"),
        ):
            result = await svc.create_from_upload(
                _CAMPAIGN_ID, make_upload_file("jd.docx", b"PK content"), user
            )

        assert result is jd

    async def test_extraction_error_returns_422(self):
        from app.services.resume_extraction import ExtractionError

        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        with patch(
            "app.services.job_description.extract_text_from_pdf_bytes",
            AsyncMock(side_effect=ExtractionError("corrupted PDF")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await svc.create_from_upload(
                    _CAMPAIGN_ID, make_upload_file("jd.pdf", b"%PDF"), user
                )
        assert exc_info.value.status_code == 422

    async def test_campaign_not_found_raises_404(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_from_upload(
                _CAMPAIGN_ID, make_upload_file("jd.pdf", b"%PDF"), user
            )
        assert exc_info.value.status_code == 404


class TestServiceGetAndDelete:
    async def test_get_by_id_returns_job_description(self):
        svc = _make_service()
        user = make_user()
        jd = make_job_description(user)
        svc.repo.get_by_id = AsyncMock(return_value=jd)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        result = await svc.get_by_id(jd.id, user)

        assert result is jd

    async def test_get_by_id_wrong_org_raises_404(self):
        svc = _make_service()
        user = make_user()
        jd = make_job_description(user)
        svc.repo.get_by_id = AsyncMock(return_value=jd)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_by_id(jd.id, user)
        assert exc_info.value.status_code == 404

    async def test_delete_own_succeeds(self):
        svc = _make_service()
        user = make_user()
        jd = make_job_description(user)
        object.__setattr__(jd, "created_by", user.id)
        svc.repo.get_by_id = AsyncMock(return_value=jd)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        svc.repo.soft_delete = AsyncMock()

        await svc.delete(jd.id, user)

        svc.repo.soft_delete.assert_called_once_with(jd)

    async def test_delete_other_user_raises_403(self):
        svc = _make_service()
        user = make_user()
        other = make_user()
        jd = make_job_description(other)
        svc.repo.get_by_id = AsyncMock(return_value=jd)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        with pytest.raises(HTTPException) as exc_info:
            await svc.delete(jd.id, user)
        assert exc_info.value.status_code == 403

    async def test_org_admin_can_delete_any(self):
        svc = _make_service()
        admin = make_user(role=UserRole.ORG_ADMIN)
        creator = make_user()
        jd = make_job_description(creator)
        svc.repo.get_by_id = AsyncMock(return_value=jd)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        svc.repo.soft_delete = AsyncMock()

        await svc.delete(jd.id, admin)

        svc.repo.soft_delete.assert_called_once_with(jd)
