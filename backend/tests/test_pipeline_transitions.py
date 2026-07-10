import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.candidate_activity import ActivityEventType
from app.models.resume_file import PipelineStage
from app.services.pipeline_transitions import advance_pipeline_stage


def make_resume_file(**overrides) -> MagicMock:
    defaults = dict(id=uuid.uuid4(), pipeline_stage=PipelineStage.APPLIED)
    defaults.update(overrides)
    resume_file = MagicMock()
    resume_file.id = defaults["id"]
    resume_file.pipeline_stage = defaults["pipeline_stage"]
    return resume_file


class TestAdvancePipelineStage:
    async def test_no_matching_resume_file_returns_none(self):
        resume_file_repo = MagicMock()
        resume_file_repo.get_by_candidate_and_campaign = AsyncMock(return_value=None)
        activity_repo = MagicMock()
        activity_repo.create = AsyncMock()

        result = await advance_pipeline_stage(
            resume_file_repo,
            activity_repo,
            candidate_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            target_stage=PipelineStage.ASSESSMENT_SENT,
            event_type=ActivityEventType.ASSESSMENT_INVITATION_SENT,
        )

        assert result is None
        activity_repo.create.assert_not_called()

    async def test_advances_stage_and_logs_activity(self):
        resume_file = make_resume_file(pipeline_stage=PipelineStage.SHORTLISTED)
        resume_file_repo = MagicMock()
        resume_file_repo.get_by_candidate_and_campaign = AsyncMock(return_value=resume_file)
        resume_file_repo.update = AsyncMock(return_value=resume_file)
        activity_repo = MagicMock()
        activity_repo.create = AsyncMock()
        candidate_id, campaign_id = uuid.uuid4(), uuid.uuid4()

        result = await advance_pipeline_stage(
            resume_file_repo,
            activity_repo,
            candidate_id=candidate_id,
            campaign_id=campaign_id,
            target_stage=PipelineStage.ASSESSMENT_SENT,
            event_type=ActivityEventType.ASSESSMENT_INVITATION_SENT,
        )

        assert result is resume_file
        resume_file_repo.get_by_candidate_and_campaign.assert_awaited_once_with(
            candidate_id, campaign_id
        )
        resume_file_repo.update.assert_awaited_once_with(
            resume_file, pipeline_stage=PipelineStage.ASSESSMENT_SENT
        )
        activity_repo.create.assert_awaited_once_with(
            resume_file.id, None, ActivityEventType.ASSESSMENT_INVITATION_SENT
        )

    async def test_does_not_move_stage_backward(self):
        resume_file = make_resume_file(pipeline_stage=PipelineStage.ASSESSMENT_COMPLETED)
        resume_file_repo = MagicMock()
        resume_file_repo.get_by_candidate_and_campaign = AsyncMock(return_value=resume_file)
        resume_file_repo.update = AsyncMock()
        activity_repo = MagicMock()
        activity_repo.create = AsyncMock()

        result = await advance_pipeline_stage(
            resume_file_repo,
            activity_repo,
            candidate_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            target_stage=PipelineStage.ASSESSMENT_SENT,
            event_type=ActivityEventType.ASSESSMENT_INVITATION_SENT,
        )

        assert result is resume_file
        resume_file_repo.update.assert_not_called()
        activity_repo.create.assert_not_called()

    async def test_same_stage_is_a_no_op(self):
        resume_file = make_resume_file(pipeline_stage=PipelineStage.ASSESSMENT_SENT)
        resume_file_repo = MagicMock()
        resume_file_repo.get_by_candidate_and_campaign = AsyncMock(return_value=resume_file)
        resume_file_repo.update = AsyncMock()
        activity_repo = MagicMock()
        activity_repo.create = AsyncMock()

        await advance_pipeline_stage(
            resume_file_repo,
            activity_repo,
            candidate_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            target_stage=PipelineStage.ASSESSMENT_SENT,
            event_type=ActivityEventType.ASSESSMENT_INVITATION_SENT,
        )

        resume_file_repo.update.assert_not_called()
        activity_repo.create.assert_not_called()
