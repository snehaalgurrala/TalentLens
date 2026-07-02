"""
Unit tests for resume upload endpoints and service validation.

Strategy (endpoint tests):
  - get_resume_service is overridden with a MagicMock — no database required.
  - get_current_user is overridden per-test to simulate different roles.
  - RequireRoles runs against the mocked user, so RBAC 403s are verified
    without any service involvement.
  - _enqueue_parse is patched (autouse) in TestUploadResumes to prevent real
    Celery dispatch; the mock is also used to assert dispatch calls.

Strategy (service tests):
  - ResumeFileService is instantiated directly with mocked repo, campaign_repo,
    and storage — tests exercise actual validation logic (extension, size, ZIP).
"""
import io
import uuid
import zipfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.api.deps import get_current_user
from app.api.v1.endpoints.resumes import get_resume_service
from app.main import app
from app.models.campaign import Campaign, CampaignStatus
from app.models.resume_file import PipelineStage, ResumeFile, ReviewStatus, UploadStatus
from app.models.user import User, UserRole
from app.services.resume_file import ResumeFileService

# ── Shared constants & factories ──────────────────────────────────────────────

_ORG_ID = uuid.uuid4()
_CAMPAIGN_ID = uuid.uuid4()
_OTHER_USER_ID = uuid.uuid4()


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


def make_resume_file(user: User, **overrides) -> ResumeFile:
    rf = ResumeFile(
        id=uuid.uuid4(),
        campaign_id=_CAMPAIGN_ID,
        original_filename="resume.pdf",
        stored_filename=f"{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size=1024,
        storage_path=f"{_CAMPAIGN_ID}/{uuid.uuid4()}.pdf",
        upload_status=UploadStatus.UPLOADED,
        uploaded_by=user.id,
        candidate_id=None,
        error_message=None,
        review_status=ReviewStatus.PENDING,
        reviewed_at=None,
        is_deleted=False,
        deleted_at=None,
        uploaded_at=datetime.now(UTC),
        pipeline_stage=PipelineStage.APPLIED,
        assigned_recruiter_id=None,
        notes=None,
    )
    for k, v in overrides.items():
        object.__setattr__(rf, k, v)
    return rf


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


def make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


# ── Endpoint fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_resume_service():
    svc = MagicMock()
    app.dependency_overrides[get_resume_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_resume_service, None)


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


# ── Upload endpoint ───────────────────────────────────────────────────────────


class TestUploadResumes:
    _url = f"/api/v1/campaigns/{_CAMPAIGN_ID}/resumes/upload"

    @pytest.fixture(autouse=True)
    def _no_celery(self):
        """Prevent real Celery dispatch in every test in this class."""
        with patch("app.api.v1.endpoints.resumes._enqueue_parse") as m:
            self._mock_enqueue = m
            yield m

    async def test_recruiter_can_upload_pdf(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        rf = make_resume_file(recruiter)
        mock_resume_service.upload = AsyncMock(return_value=[rf])

        res = await client_no_lifespan.post(
            self._url,
            files=[("files", ("resume.pdf", b"%PDF-1.4 content", "application/pdf"))],
        )

        assert res.status_code == 201
        body = res.json()
        assert body["count"] == 1
        assert body["uploaded"][0]["original_filename"] == "resume.pdf"
        assert body["uploaded"][0]["upload_status"] == UploadStatus.UPLOADED.value

    async def test_org_admin_can_upload(
        self, client_no_lifespan: AsyncClient, mock_resume_service, org_admin: User
    ):
        rf = make_resume_file(org_admin)
        mock_resume_service.upload = AsyncMock(return_value=[rf])

        res = await client_no_lifespan.post(
            self._url,
            files=[("files", ("cv.docx", b"PK content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        )
        assert res.status_code == 201

    async def test_candidate_cannot_upload(
        self, client_no_lifespan: AsyncClient, mock_resume_service, candidate: User
    ):
        res = await client_no_lifespan.post(
            self._url,
            files=[("files", ("resume.pdf", b"content", "application/pdf"))],
        )
        assert res.status_code == 403

    async def test_upload_multiple_files(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        rfs = [make_resume_file(recruiter, original_filename=f"resume_{i}.pdf") for i in range(3)]
        mock_resume_service.upload = AsyncMock(return_value=rfs)

        res = await client_no_lifespan.post(
            self._url,
            files=[
                ("files", (f"resume_{i}.pdf", b"%PDF content", "application/pdf"))
                for i in range(3)
            ],
        )

        assert res.status_code == 201
        assert res.json()["count"] == 3

    async def test_parse_task_dispatched_for_each_uploaded_file(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        """Verify _enqueue_parse is called once per created ResumeFile."""
        rfs = [make_resume_file(recruiter, original_filename=f"cv_{i}.pdf") for i in range(2)]
        mock_resume_service.upload = AsyncMock(return_value=rfs)

        await client_no_lifespan.post(
            self._url,
            files=[("files", (f"cv_{i}.pdf", b"%PDF", "application/pdf")) for i in range(2)],
        )

        assert self._mock_enqueue.call_count == 2
        dispatched_ids = {call.args[0] for call in self._mock_enqueue.call_args_list}
        expected_ids = {str(rf.id) for rf in rfs}
        assert dispatched_ids == expected_ids

    async def test_parse_task_not_dispatched_on_upload_failure(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        """If upload raises, no parse tasks should be enqueued."""
        mock_resume_service.upload = AsyncMock(
            side_effect=HTTPException(422, "Unsupported extension.")
        )

        res = await client_no_lifespan.post(
            self._url,
            files=[("files", ("resume.exe", b"content", "application/octet-stream"))],
        )

        assert res.status_code == 422
        self._mock_enqueue.assert_not_called()

    async def test_campaign_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.upload = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.post(
            self._url,
            files=[("files", ("resume.pdf", b"content", "application/pdf"))],
        )
        assert res.status_code == 404

    async def test_unsupported_file_type_returns_422(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.upload = AsyncMock(
            side_effect=HTTPException(422, "Unsupported extension '.exe'.")
        )
        res = await client_no_lifespan.post(
            self._url,
            files=[("files", ("malware.exe", b"content", "application/octet-stream"))],
        )
        assert res.status_code == 422

    async def test_file_too_large_returns_422(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.upload = AsyncMock(
            side_effect=HTTPException(422, "exceeds the 10 MB limit.")
        )
        res = await client_no_lifespan.post(
            self._url,
            files=[("files", ("big.pdf", b"%PDF", "application/pdf"))],
        )
        assert res.status_code == 422

    async def test_invalid_zip_returns_422(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.upload = AsyncMock(
            side_effect=HTTPException(422, "is not a valid ZIP file.")
        )
        res = await client_no_lifespan.post(
            self._url,
            files=[("files", ("bad.zip", b"not a zip", "application/zip"))],
        )
        assert res.status_code == 422

    async def test_unauthenticated_returns_401(
        self, client_no_lifespan: AsyncClient, mock_resume_service
    ):
        res = await client_no_lifespan.post(
            self._url,
            files=[("files", ("resume.pdf", b"content", "application/pdf"))],
        )
        assert res.status_code == 401

    async def test_response_contains_metadata_fields(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        rf = make_resume_file(recruiter)
        mock_resume_service.upload = AsyncMock(return_value=[rf])

        body = (
            await client_no_lifespan.post(
                self._url,
                files=[("files", ("resume.pdf", b"%PDF content", "application/pdf"))],
            )
        ).json()

        first = body["uploaded"][0]
        for field in (
            "id", "campaign_id", "original_filename", "mime_type",
            "file_size", "storage_path", "upload_status", "uploaded_by",
            "candidate_id", "error_message", "uploaded_at",
        ):
            assert field in first, f"Missing field: {field}"

    async def test_upload_status_is_uploaded_immediately(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        """Newly uploaded files have UPLOADED status; parsing happens asynchronously."""
        rf = make_resume_file(recruiter)
        mock_resume_service.upload = AsyncMock(return_value=[rf])

        body = (
            await client_no_lifespan.post(
                self._url,
                files=[("files", ("resume.pdf", b"%PDF", "application/pdf"))],
            )
        ).json()

        assert body["uploaded"][0]["upload_status"] == UploadStatus.UPLOADED.value
        assert body["uploaded"][0]["candidate_id"] is None


# ── Get resume (status polling) endpoint ──────────────────────────────────────


class TestGetResume:
    async def test_returns_uploaded_file(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        rf = make_resume_file(recruiter)
        mock_resume_service.get_by_id = AsyncMock(return_value=rf)

        res = await client_no_lifespan.get(f"/api/v1/resumes/{rf.id}")

        assert res.status_code == 200
        assert res.json()["id"] == str(rf.id)
        assert res.json()["upload_status"] == UploadStatus.UPLOADED.value

    async def test_returns_processing_status(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        rf = make_resume_file(recruiter, upload_status=UploadStatus.PROCESSING)
        mock_resume_service.get_by_id = AsyncMock(return_value=rf)

        res = await client_no_lifespan.get(f"/api/v1/resumes/{rf.id}")

        assert res.status_code == 200
        assert res.json()["upload_status"] == UploadStatus.PROCESSING.value

    async def test_returns_parsed_status_with_candidate_id(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        candidate_id = uuid.uuid4()
        rf = make_resume_file(
            recruiter,
            upload_status=UploadStatus.PARSED,
            candidate_id=candidate_id,
        )
        mock_resume_service.get_by_id = AsyncMock(return_value=rf)

        res = await client_no_lifespan.get(f"/api/v1/resumes/{rf.id}")

        assert res.status_code == 200
        body = res.json()
        assert body["upload_status"] == UploadStatus.PARSED.value
        assert body["candidate_id"] == str(candidate_id)

    async def test_returns_failed_status_with_error_message(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        rf = make_resume_file(
            recruiter,
            upload_status=UploadStatus.FAILED,
            error_message="AI service 503: server unavailable",
        )
        mock_resume_service.get_by_id = AsyncMock(return_value=rf)

        res = await client_no_lifespan.get(f"/api/v1/resumes/{rf.id}")

        assert res.status_code == 200
        body = res.json()
        assert body["upload_status"] == UploadStatus.FAILED.value
        assert body["error_message"] == "AI service 503: server unavailable"

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.get_by_id = AsyncMock(
            side_effect=HTTPException(404, "Resume file not found.")
        )
        res = await client_no_lifespan.get(f"/api/v1/resumes/{uuid.uuid4()}")
        assert res.status_code == 404

    async def test_unauthenticated_returns_401(
        self, client_no_lifespan: AsyncClient, mock_resume_service
    ):
        res = await client_no_lifespan.get(f"/api/v1/resumes/{uuid.uuid4()}")
        assert res.status_code == 401

    async def test_candidate_can_view_status(
        self, client_no_lifespan: AsyncClient, mock_resume_service, candidate: User
    ):
        """Read access is not role-restricted — any authenticated user can poll status."""
        rf = make_resume_file(make_user(), upload_status=UploadStatus.PARSED)
        mock_resume_service.get_by_id = AsyncMock(return_value=rf)

        res = await client_no_lifespan.get(f"/api/v1/resumes/{rf.id}")
        assert res.status_code == 200


# ── List endpoint ─────────────────────────────────────────────────────────────


class TestListResumes:
    _url = f"/api/v1/campaigns/{_CAMPAIGN_ID}/resumes"

    async def test_returns_files_for_campaign(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        rfs = [
            make_resume_file(recruiter),
            make_resume_file(recruiter, original_filename="cv.docx"),
        ]
        mock_resume_service.list_by_campaign = AsyncMock(return_value=rfs)

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        assert len(res.json()) == 2

    async def test_empty_list(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.list_by_campaign = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200
        assert res.json() == []

    async def test_candidate_can_list(
        self, client_no_lifespan: AsyncClient, mock_resume_service, candidate: User
    ):
        mock_resume_service.list_by_campaign = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200

    async def test_campaign_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.list_by_campaign = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 404

    async def test_unauthenticated_returns_401(
        self, client_no_lifespan: AsyncClient, mock_resume_service
    ):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 401

    async def test_files_linked_to_campaign(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        rfs = [make_resume_file(recruiter), make_resume_file(recruiter)]
        mock_resume_service.list_by_campaign = AsyncMock(return_value=rfs)

        body = (await client_no_lifespan.get(self._url)).json()
        assert all(f["campaign_id"] == str(_CAMPAIGN_ID) for f in body)


# ── Delete endpoint ───────────────────────────────────────────────────────────


class TestDeleteResume:
    async def test_recruiter_can_delete_own_file(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.delete = AsyncMock(return_value=None)
        res = await client_no_lifespan.delete(f"/api/v1/resumes/{uuid.uuid4()}")
        assert res.status_code == 204

    async def test_org_admin_can_delete_any(
        self, client_no_lifespan: AsyncClient, mock_resume_service, org_admin: User
    ):
        mock_resume_service.delete = AsyncMock(return_value=None)
        res = await client_no_lifespan.delete(f"/api/v1/resumes/{uuid.uuid4()}")
        assert res.status_code == 204

    async def test_candidate_cannot_delete(
        self, client_no_lifespan: AsyncClient, mock_resume_service, candidate: User
    ):
        res = await client_no_lifespan.delete(f"/api/v1/resumes/{uuid.uuid4()}")
        assert res.status_code == 403

    async def test_not_owner_recruiter_gets_403(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.delete = AsyncMock(
            side_effect=HTTPException(403, "You do not have permission to delete this file.")
        )
        res = await client_no_lifespan.delete(f"/api/v1/resumes/{uuid.uuid4()}")
        assert res.status_code == 403

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.delete = AsyncMock(
            side_effect=HTTPException(404, "Resume file not found.")
        )
        res = await client_no_lifespan.delete(f"/api/v1/resumes/{uuid.uuid4()}")
        assert res.status_code == 404

    async def test_no_body_on_success(
        self, client_no_lifespan: AsyncClient, mock_resume_service, recruiter: User
    ):
        mock_resume_service.delete = AsyncMock(return_value=None)
        res = await client_no_lifespan.delete(f"/api/v1/resumes/{uuid.uuid4()}")
        assert res.content == b""

    async def test_unauthenticated_returns_401(
        self, client_no_lifespan: AsyncClient, mock_resume_service
    ):
        res = await client_no_lifespan.delete(f"/api/v1/resumes/{uuid.uuid4()}")
        assert res.status_code == 401


# ── Service validation (no HTTP layer) ───────────────────────────────────────


def _make_service() -> ResumeFileService:
    repo = MagicMock()
    campaign_repo = MagicMock()
    storage = MagicMock()
    storage.save = AsyncMock(side_effect=lambda path, data: path)
    repo.create = AsyncMock()
    campaign_repo.get_by_id = AsyncMock()
    return ResumeFileService(repo, campaign_repo, storage)


class TestServiceFileValidation:
    """Tests for extension / size / ZIP validation inside the service."""

    async def test_rejects_unsupported_extension(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID,
                [make_upload_file("resume.txt", b"text content")],
                user,
            )
        assert exc_info.value.status_code == 422
        assert ".txt" in exc_info.value.detail

    async def test_rejects_file_exceeding_size_limit(self, monkeypatch):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        monkeypatch.setattr("app.services.resume_file.settings.MAX_UPLOAD_SIZE_MB", 0)

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID,
                [make_upload_file("resume.pdf", b"%PDF-1.4")],
                user,
            )
        assert exc_info.value.status_code == 422
        assert "limit" in exc_info.value.detail

    async def test_accepts_pdf(self):
        svc = _make_service()
        user = make_user()
        campaign = make_campaign()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        rf = make_resume_file(user)
        svc.repo.create = AsyncMock(return_value=rf)

        result = await svc.upload(
            _CAMPAIGN_ID,
            [make_upload_file("resume.pdf", b"%PDF-1.4 content", "application/pdf")],
            user,
        )
        assert len(result) == 1
        svc.storage.save.assert_called_once()

    async def test_accepts_docx(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        rf = make_resume_file(user, original_filename="cv.docx")
        svc.repo.create = AsyncMock(return_value=rf)

        result = await svc.upload(
            _CAMPAIGN_ID,
            [make_upload_file("cv.docx", b"PK content")],
            user,
        )
        assert len(result) == 1

    async def test_zip_extracts_pdf_and_docx(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        call_count = 0

        async def _create(**kwargs):
            nonlocal call_count
            call_count += 1
            return make_resume_file(user, original_filename=kwargs["original_filename"])

        svc.repo.create = _create

        zip_content = make_zip({"alice.pdf": b"%PDF content", "bob.docx": b"PK content"})

        result = await svc.upload(
            _CAMPAIGN_ID,
            [make_upload_file("batch.zip", zip_content, "application/zip")],
            user,
        )
        assert len(result) == 2
        assert svc.storage.save.call_count == 2

    async def test_zip_rejects_unsupported_inner_file(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        zip_content = make_zip({"resume.pdf": b"%PDF", "notes.txt": b"text"})

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID,
                [make_upload_file("batch.zip", zip_content)],
                user,
            )
        assert exc_info.value.status_code == 422
        assert ".txt" in exc_info.value.detail

    async def test_invalid_zip_raises_422(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID,
                [make_upload_file("bad.zip", b"this is not a zip file")],
                user,
            )
        assert exc_info.value.status_code == 422
        assert "valid ZIP" in exc_info.value.detail

    async def test_empty_zip_raises_422(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        zip_content = make_zip({})

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID,
                [make_upload_file("empty.zip", zip_content)],
                user,
            )
        assert exc_info.value.status_code == 422
        assert "no supported" in exc_info.value.detail

    async def test_zip_rejects_too_many_entries(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ZIP_MAX_ENTRIES", 2)

        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        zip_content = make_zip({"a.pdf": b"%PDF a", "b.pdf": b"%PDF b", "c.pdf": b"%PDF c"})

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID, [make_upload_file("batch.zip", zip_content)], user
            )
        assert exc_info.value.status_code == 422
        assert "entries" in exc_info.value.detail

    async def test_zip_rejects_uncompressed_size_over_limit(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ZIP_MAX_UNCOMPRESSED_TOTAL_MB", 0)

        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        zip_content = make_zip({"a.pdf": b"%PDF" * 1000})

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID, [make_upload_file("batch.zip", zip_content)], user
            )
        assert exc_info.value.status_code == 422
        assert "uncompressed size" in exc_info.value.detail

    async def test_zip_rejects_high_compression_ratio(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ZIP_MAX_COMPRESSION_RATIO", 5)

        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        # Highly compressible content — a real zip bomb pattern — triggers
        # the ratio check even though the compressed upload itself is tiny.
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("bomb.pdf", b"0" * 1_000_000)
        zip_content = buf.getvalue()

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID, [make_upload_file("batch.zip", zip_content)], user
            )
        assert exc_info.value.status_code == 422
        assert "compression ratio" in exc_info.value.detail

    async def test_campaign_not_found_raises_404(self):
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID,
                [make_upload_file("resume.pdf", b"%PDF")],
                user,
            )
        assert exc_info.value.status_code == 404

    async def test_user_without_org_raises_422(self):
        svc = _make_service()
        user = make_user(org_id=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload(
                _CAMPAIGN_ID,
                [make_upload_file("resume.pdf", b"%PDF")],
                user,
            )
        assert exc_info.value.status_code == 422

    async def test_no_files_saved_before_validation_fails(self):
        """Phase-1 validation must reject before any storage.save is called."""
        svc = _make_service()
        user = make_user()
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        zip_content = make_zip({"resume.pdf": b"%PDF", "bad.exe": b"MZ"})

        with pytest.raises(HTTPException):
            await svc.upload(
                _CAMPAIGN_ID,
                [make_upload_file("batch.zip", zip_content)],
                user,
            )
        svc.storage.save.assert_not_called()

    async def test_get_by_id_returns_file(self):
        svc = _make_service()
        user = make_user()
        rf = make_resume_file(user)
        svc.repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        result = await svc.get_by_id(rf.id, user)

        assert result is rf

    async def test_get_by_id_not_found_raises_404(self):
        svc = _make_service()
        user = make_user()
        svc.repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_by_id(uuid.uuid4(), user)
        assert exc_info.value.status_code == 404

    async def test_get_by_id_wrong_org_raises_404(self):
        """File exists but belongs to a different org — must not leak it."""
        svc = _make_service()
        user = make_user()
        rf = make_resume_file(user)
        svc.repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=None)  # org mismatch

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_by_id(rf.id, user)
        assert exc_info.value.status_code == 404

    async def test_get_by_id_user_without_org_raises_422(self):
        svc = _make_service()
        user = make_user(org_id=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_by_id(uuid.uuid4(), user)
        assert exc_info.value.status_code == 422

    async def test_delete_own_file_succeeds(self):
        svc = _make_service()
        user = make_user()
        rf = make_resume_file(user)
        object.__setattr__(rf, "uploaded_by", user.id)
        svc.repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        svc.repo.soft_delete = AsyncMock()

        await svc.delete(rf.id, user)

        svc.repo.soft_delete.assert_called_once_with(rf)

    async def test_delete_other_user_file_raises_403(self):
        svc = _make_service()
        user = make_user()
        other = make_user()
        rf = make_resume_file(other)
        svc.repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())

        with pytest.raises(HTTPException) as exc_info:
            await svc.delete(rf.id, user)
        assert exc_info.value.status_code == 403

    async def test_org_admin_can_delete_any_file(self):
        svc = _make_service()
        admin = make_user(role=UserRole.ORG_ADMIN)
        uploader = make_user()
        rf = make_resume_file(uploader)
        svc.repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=make_campaign())
        svc.repo.soft_delete = AsyncMock()

        await svc.delete(rf.id, admin)

        svc.repo.soft_delete.assert_called_once_with(rf)
