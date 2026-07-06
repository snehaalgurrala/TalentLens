"""
Direct unit tests for CandidateManagementService's newer methods
(archive/restore/_resolve_restore_target/assign_recruiter's from_recruiter_id
metadata), using mocked repositories rather than mocking the service itself —
this logic isn't otherwise exercised by the HTTP-level tests, which mock the
whole service.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.candidate_activity import ActivityEventType, CandidateActivity
from app.models.resume_file import PipelineStage, ResumeFile, ReviewStatus, UploadStatus
from app.models.user import User, UserRole
from app.services.candidate_management import CandidateManagementService

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


def make_resume_file(**overrides) -> ResumeFile:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        original_filename="resume.pdf",
        stored_filename="stored.pdf",
        mime_type="application/pdf",
        file_size=1024,
        storage_path="path/stored.pdf",
        upload_status=UploadStatus.PARSED,
        uploaded_by=None,
        is_deleted=False,
        deleted_at=None,
        uploaded_at=now,
        candidate_id=None,
        error_message=None,
        review_status=ReviewStatus.PENDING,
        reviewed_at=None,
        pipeline_stage=PipelineStage.APPLIED,
        assigned_recruiter_id=None,
        notes=None,
    )
    defaults.update(overrides)
    return ResumeFile(**defaults)


def make_activity(event_type: ActivityEventType, event_metadata: dict | None) -> CandidateActivity:
    return CandidateActivity(
        id=uuid.uuid4(),
        resume_file_id=uuid.uuid4(),
        actor_id=uuid.uuid4(),
        event_type=event_type,
        event_metadata=event_metadata,
        created_at=datetime.now(UTC),
    )


def make_service(**repo_overrides) -> CandidateManagementService:
    defaults = dict(
        resume_file_repo=MagicMock(),
        candidate_repo=MagicMock(),
        parsed_resume_repo=MagicMock(),
        campaign_repo=MagicMock(),
        user_repo=MagicMock(),
        ranking_service=MagicMock(),
        activity_repo=MagicMock(),
    )
    defaults.update(repo_overrides)
    return CandidateManagementService(**defaults)


@pytest.fixture
def user():
    return make_user()


class TestArchive:
    async def test_sets_pipeline_stage_and_logs_activity(self, user: User):
        rf = make_resume_file(pipeline_stage=PipelineStage.SHORTLISTED)
        svc = make_service()
        svc.resume_file_repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=MagicMock())
        svc.resume_file_repo.update = AsyncMock(
            side_effect=lambda r, **kw: make_resume_file(id=r.id, **kw)
        )
        svc.activity_repo.create = AsyncMock()

        result = await svc.archive(rf.id, user)

        assert result.pipeline_stage == PipelineStage.ARCHIVED
        svc.activity_repo.create.assert_awaited_once_with(
            rf.id,
            user.id,
            ActivityEventType.ARCHIVED,
            {"from_stage": "SHORTLISTED", "to_stage": "ARCHIVED"},
        )


class TestRestore:
    async def test_rejects_non_terminal_stage(self, user: User):
        rf = make_resume_file(pipeline_stage=PipelineStage.RANKED)
        svc = make_service()
        svc.resume_file_repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await svc.restore(rf.id, user)
        assert exc_info.value.status_code == 422

    async def test_restores_to_prior_stage_from_activity_history(self, user: User):
        rf = make_resume_file(pipeline_stage=PipelineStage.ARCHIVED, review_status=ReviewStatus.PENDING)
        svc = make_service()
        svc.resume_file_repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=MagicMock())
        svc.activity_repo.list_by_resume_file = AsyncMock(
            return_value=[
                make_activity(
                    ActivityEventType.ARCHIVED,
                    {"from_stage": "SHORTLISTED", "to_stage": "ARCHIVED"},
                ),
            ]
        )
        svc.resume_file_repo.update = AsyncMock(
            side_effect=lambda r, **kw: make_resume_file(id=r.id, **kw)
        )
        svc.activity_repo.create = AsyncMock()

        result = await svc.restore(rf.id, user)

        assert result.pipeline_stage == PipelineStage.SHORTLISTED

    async def test_falls_back_to_applied_when_no_history(self, user: User):
        rf = make_resume_file(pipeline_stage=PipelineStage.REJECTED, review_status=ReviewStatus.REJECTED)
        svc = make_service()
        svc.resume_file_repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=MagicMock())
        svc.activity_repo.list_by_resume_file = AsyncMock(return_value=[])
        svc.resume_file_repo.update = AsyncMock(
            side_effect=lambda r, **kw: make_resume_file(id=r.id, **kw)
        )
        svc.activity_repo.create = AsyncMock()

        result = await svc.restore(rf.id, user)

        assert result.pipeline_stage == PipelineStage.APPLIED
        assert result.review_status == ReviewStatus.PENDING


class TestAssignRecruiterTransfer:
    async def test_reassign_includes_from_recruiter_id(self, user: User):
        previous_recruiter_id = uuid.uuid4()
        new_recruiter_id = uuid.uuid4()
        rf = make_resume_file(assigned_recruiter_id=previous_recruiter_id)
        svc = make_service()
        svc.resume_file_repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=MagicMock())
        svc.user_repo.get_by_id = AsyncMock(
            return_value=make_user(role=UserRole.RECRUITER, org_id=user.org_id)
        )
        svc.resume_file_repo.update = AsyncMock(
            side_effect=lambda r, **kw: make_resume_file(id=r.id, **kw)
        )
        svc.activity_repo.create = AsyncMock()

        await svc.assign_recruiter(rf.id, new_recruiter_id, user)

        svc.activity_repo.create.assert_awaited_once_with(
            rf.id,
            user.id,
            ActivityEventType.RECRUITER_ASSIGNED,
            {
                "assigned_recruiter_id": str(new_recruiter_id),
                "from_recruiter_id": str(previous_recruiter_id),
            },
        )

    async def test_first_assignment_omits_from_recruiter_id(self, user: User):
        new_recruiter_id = uuid.uuid4()
        rf = make_resume_file(assigned_recruiter_id=None)
        svc = make_service()
        svc.resume_file_repo.get_by_id = AsyncMock(return_value=rf)
        svc.campaign_repo.get_by_id = AsyncMock(return_value=MagicMock())
        svc.user_repo.get_by_id = AsyncMock(
            return_value=make_user(role=UserRole.RECRUITER, org_id=user.org_id)
        )
        svc.resume_file_repo.update = AsyncMock(
            side_effect=lambda r, **kw: make_resume_file(id=r.id, **kw)
        )
        svc.activity_repo.create = AsyncMock()

        await svc.assign_recruiter(rf.id, new_recruiter_id, user)

        _, kwargs = (
            svc.activity_repo.create.call_args.args,
            svc.activity_repo.create.call_args.kwargs,
        )
        metadata = svc.activity_repo.create.call_args.args[3]
        assert "from_recruiter_id" not in metadata
