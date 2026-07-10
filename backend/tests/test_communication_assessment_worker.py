"""Unit tests for app.workers.communication_assessment.

No real database, no real Redis. All dependencies are injected via the
_session_factory / _engine keyword arguments on
_run_generate_communication_assessment and _mark_failed, mirroring
test_communication_analysis_worker.py.

Async tests run automatically because asyncio_mode = "auto" in pyproject.toml.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry

from app.ai.communication.schemas import (
    CommunicationAssessmentResult,
    CommunicationAssessmentSummary,
)
from app.models.assessment_analysis import AnalysisStatus, AnalysisType
from app.models.communication_assessment import CommunicationAssessmentStatus
from app.workers.communication_assessment import (
    _generate_communication_assessment_task,
    _mark_failed,
    _run_generate_communication_assessment,
)

# ── Shared fixture helpers ────────────────────────────────────────────────────


def _make_session_row(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(), org_id=uuid.uuid4(), candidate_id=uuid.uuid4(), campaign_id=uuid.uuid4()
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_assessment(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        assessment_session_id=overrides.get("assessment_session_id", uuid.uuid4()),
        organization_id=uuid.uuid4(),
        status=CommunicationAssessmentStatus.PENDING,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_analysis(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        analysis_type=AnalysisType.READ_ALOUD,
        status=AnalysisStatus.COMPLETED,
        overall_score=90.0,
        word_accuracy=96.0,
        reading_speed_wpm=130.0,
        completion_percentage=100.0,
        semantic_similarity=93.0,
        keyword_coverage=85.0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_result(**overrides) -> CommunicationAssessmentResult:
    defaults = dict(
        overall_score=85.0,
        reading_score=90.0,
        listening_score=80.0,
        confidence_score=88.0,
        strengths=["Reads clearly and accurately"],
        improvements=[],
        summary=CommunicationAssessmentSummary(overview="Great job."),
    )
    defaults.update(overrides)
    return CommunicationAssessmentResult(**defaults)


def _make_async_cm(return_value=None) -> MagicMock:
    """A bare AsyncMock's `.begin_nested()`/etc. return a coroutine, not an
    async context manager — real SQLAlchemy sessions return one, so tests
    exercising `async with session.begin_nested():` need this instead."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=return_value)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


def _make_session_factory(session_mock: AsyncMock) -> MagicMock:
    """Wrap a mock session in an async context manager returned by a callable."""
    return _make_async_cm(session_mock)


def _make_execute_result(rows: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


# ── Happy path ────────────────────────────────────────────────────────────────


class TestRunGenerateCommunicationAssessmentHappyPath:
    async def test_scores_and_marks_completed_when_both_analyses_ready(self):
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.PENDING,
        )
        read_aloud = _make_analysis(analysis_type=AnalysisType.READ_ALOUD)
        listen_repeat = _make_analysis(analysis_type=AnalysisType.LISTEN_REPEAT)
        result = _make_result()

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.execute = AsyncMock(
            return_value=_make_execute_result([read_aloud, listen_repeat])
        )
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)

        engine = MagicMock()
        engine.assess = MagicMock(return_value=result)

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
            patch(
                "app.workers.communication_assessment.advance_pipeline_stage",
                AsyncMock(return_value=None),
            ) as mock_advance,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)
            mock_service.complete_processing = AsyncMock(return_value=assessment)

            await _run_generate_communication_assessment(
                str(assessment_session.id),
                _session_factory=session_factory,
                _engine=engine,
            )

            mock_service.create_pending.assert_awaited_once_with(
                assessment_session.id, assessment_session.org_id
            )
            engine.assess.assert_called_once()
            mock_service.complete_processing.assert_awaited_once_with(
                assessment_session.id,
                overall_score=result.overall_score,
                reading_score=result.reading_score,
                listening_score=result.listening_score,
                confidence_score=result.confidence_score,
                strengths_json=result.strengths,
                improvements_json=result.improvements,
                summary_json=result.summary.model_dump(mode="json"),
            )
            mock_advance.assert_awaited_once()
            _, advance_kwargs = mock_advance.call_args
            assert advance_kwargs["candidate_id"] == assessment_session.candidate_id
            assert advance_kwargs["campaign_id"] == assessment_session.campaign_id
        assert session.commit.await_count == 2

    async def test_session_not_found_returns_silently(self):
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session_factory = _make_session_factory(session)

        await _run_generate_communication_assessment(
            str(uuid.uuid4()), _session_factory=session_factory
        )

        session.commit.assert_not_awaited()


# ── Assessment-completed side effects: pipeline stage + notification ─────────


class TestAssessmentCompletedSideEffects:
    async def test_notifies_assigned_recruiter_when_resume_file_advances(self):
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.PENDING,
        )
        read_aloud = _make_analysis(analysis_type=AnalysisType.READ_ALOUD)
        listen_repeat = _make_analysis(analysis_type=AnalysisType.LISTEN_REPEAT)
        result = _make_result()
        recruiter_id = uuid.uuid4()
        resume_file = SimpleNamespace(id=uuid.uuid4(), assigned_recruiter_id=recruiter_id)
        candidate = SimpleNamespace(first_name="Jane", last_name="Doe")
        campaign = SimpleNamespace(title="Data Scientist", created_by=uuid.uuid4())

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.execute = AsyncMock(return_value=_make_execute_result([read_aloud, listen_repeat]))
        session.commit = AsyncMock()
        session.begin_nested = _make_async_cm()
        session_factory = _make_session_factory(session)
        engine = MagicMock()
        engine.assess = MagicMock(return_value=result)

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
            patch(
                "app.workers.communication_assessment.advance_pipeline_stage",
                AsyncMock(return_value=resume_file),
            ),
            patch("app.workers.communication_assessment.CampaignRepository") as mock_campaign_repo_cls,
            patch("app.workers.communication_assessment.CandidateRepository") as mock_candidate_repo_cls,
            patch("app.workers.communication_assessment.NotificationRepository"),
            patch(
                "app.workers.communication_assessment.NotificationService"
            ) as mock_notification_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)
            mock_service.complete_processing = AsyncMock(return_value=assessment)
            mock_campaign_repo_cls.return_value.get_by_id = AsyncMock(return_value=campaign)
            mock_candidate_repo_cls.return_value.get_by_id_and_org = AsyncMock(return_value=candidate)
            mock_notification_service = mock_notification_service_cls.return_value
            mock_notification_service.create = AsyncMock()

            await _run_generate_communication_assessment(
                str(assessment_session.id), _session_factory=session_factory, _engine=engine
            )

            mock_notification_service.create.assert_awaited_once()
            _, notify_kwargs = mock_notification_service.create.call_args
            assert notify_kwargs["organization_id"] == assessment_session.org_id
            assert notify_kwargs["user_id"] == recruiter_id
            assert notify_kwargs["resume_file_id"] == resume_file.id
            assert "Jane Doe" in notify_kwargs["message"]
            assert "Data Scientist" in notify_kwargs["message"]

    async def test_notification_failure_does_not_block_the_outer_commit(self):
        """Regression test: a real SQLAlchemy session that fails a flush
        stays unusable until an explicit rollback — swallowing the
        exception alone isn't enough, the notification must run inside its
        own savepoint (session.begin_nested()) or the caller's later
        session.commit() raises too, silently discarding the pipeline-stage
        advance in the same transaction."""
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.PENDING,
        )
        read_aloud = _make_analysis(analysis_type=AnalysisType.READ_ALOUD)
        listen_repeat = _make_analysis(analysis_type=AnalysisType.LISTEN_REPEAT)
        result = _make_result()
        resume_file = SimpleNamespace(id=uuid.uuid4(), assigned_recruiter_id=uuid.uuid4())
        campaign = SimpleNamespace(title="Data Scientist", created_by=uuid.uuid4())

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.execute = AsyncMock(return_value=_make_execute_result([read_aloud, listen_repeat]))
        session.commit = AsyncMock()
        session.begin_nested = _make_async_cm()
        session_factory = _make_session_factory(session)
        engine = MagicMock()
        engine.assess = MagicMock(return_value=result)

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
            patch(
                "app.workers.communication_assessment.advance_pipeline_stage",
                AsyncMock(return_value=resume_file),
            ),
            patch("app.workers.communication_assessment.CampaignRepository") as mock_campaign_repo_cls,
            patch("app.workers.communication_assessment.CandidateRepository") as mock_candidate_repo_cls,
            patch("app.workers.communication_assessment.NotificationRepository"),
            patch(
                "app.workers.communication_assessment.NotificationService"
            ) as mock_notification_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)
            mock_service.complete_processing = AsyncMock(return_value=assessment)
            mock_campaign_repo_cls.return_value.get_by_id = AsyncMock(return_value=campaign)
            mock_candidate_repo_cls.return_value.get_by_id_and_org = AsyncMock(return_value=None)
            mock_notification_service_cls.return_value.create = AsyncMock(
                side_effect=RuntimeError("invalid input value for enum notificationtype")
            )

            await _run_generate_communication_assessment(
                str(assessment_session.id), _session_factory=session_factory, _engine=engine
            )

            # The failure must be contained to the begin_nested() block, not
            # propagate and prevent the final commit — both Phase 1's
            # (create_pending) and Phase 3's (complete_processing) commits
            # must still happen, same as the happy path.
            assert session.commit.await_count == 2

    async def test_no_notification_when_no_resume_file_matched(self):
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.PENDING,
        )
        read_aloud = _make_analysis(analysis_type=AnalysisType.READ_ALOUD)
        listen_repeat = _make_analysis(analysis_type=AnalysisType.LISTEN_REPEAT)
        result = _make_result()

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.execute = AsyncMock(return_value=_make_execute_result([read_aloud, listen_repeat]))
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)
        engine = MagicMock()
        engine.assess = MagicMock(return_value=result)

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
            patch(
                "app.workers.communication_assessment.advance_pipeline_stage",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.workers.communication_assessment._notify_assessment_completed",
                AsyncMock(),
            ) as mock_notify,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)
            mock_service.complete_processing = AsyncMock(return_value=assessment)

            await _run_generate_communication_assessment(
                str(assessment_session.id), _session_factory=session_factory, _engine=engine
            )

            mock_notify.assert_not_called()

    async def test_no_recipient_skips_notification_without_raising(self):
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.PENDING,
        )
        read_aloud = _make_analysis(analysis_type=AnalysisType.READ_ALOUD)
        listen_repeat = _make_analysis(analysis_type=AnalysisType.LISTEN_REPEAT)
        result = _make_result()
        resume_file = SimpleNamespace(id=uuid.uuid4(), assigned_recruiter_id=None)
        campaign = SimpleNamespace(title="Data Scientist", created_by=None)

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.execute = AsyncMock(return_value=_make_execute_result([read_aloud, listen_repeat]))
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)
        engine = MagicMock()
        engine.assess = MagicMock(return_value=result)

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
            patch(
                "app.workers.communication_assessment.advance_pipeline_stage",
                AsyncMock(return_value=resume_file),
            ),
            patch("app.workers.communication_assessment.CampaignRepository") as mock_campaign_repo_cls,
            patch(
                "app.workers.communication_assessment.NotificationService"
            ) as mock_notification_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)
            mock_service.complete_processing = AsyncMock(return_value=assessment)
            mock_campaign_repo_cls.return_value.get_by_id = AsyncMock(return_value=campaign)

            await _run_generate_communication_assessment(
                str(assessment_session.id), _session_factory=session_factory, _engine=engine
            )

            mock_notification_service_cls.return_value.create.assert_not_called()


# ── Edge case: missing analyses ───────────────────────────────────────────────


class TestMissingAnalyses:
    async def test_only_read_aloud_present_waits(self):
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.PENDING,
        )
        read_aloud = _make_analysis(analysis_type=AnalysisType.READ_ALOUD)

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.execute = AsyncMock(return_value=_make_execute_result([read_aloud]))
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)
        engine = MagicMock()

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)

            await _run_generate_communication_assessment(
                str(assessment_session.id), _session_factory=session_factory, _engine=engine
            )

        engine.assess.assert_not_called()
        # create_pending's own commit happened, but nothing further.
        assert session.commit.await_count == 1

    async def test_neither_analysis_present_waits(self):
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.PENDING,
        )

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.execute = AsyncMock(return_value=_make_execute_result([]))
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)
        engine = MagicMock()

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)

            await _run_generate_communication_assessment(
                str(assessment_session.id), _session_factory=session_factory, _engine=engine
            )

        engine.assess.assert_not_called()


# ── Edge case: one analysis failed ────────────────────────────────────────────


class TestOneAnalysisFailed:
    async def test_read_aloud_failed_marks_assessment_failed(self):
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.PENDING,
        )
        read_aloud = _make_analysis(
            analysis_type=AnalysisType.READ_ALOUD, status=AnalysisStatus.FAILED
        )
        listen_repeat = _make_analysis(analysis_type=AnalysisType.LISTEN_REPEAT)

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.execute = AsyncMock(
            return_value=_make_execute_result([read_aloud, listen_repeat])
        )
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)
        engine = MagicMock()

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)
            mock_service.fail_processing = AsyncMock()

            await _run_generate_communication_assessment(
                str(assessment_session.id), _session_factory=session_factory, _engine=engine
            )

            mock_service.fail_processing.assert_awaited_once()
            error_message = mock_service.fail_processing.call_args.args[1]
            assert "Read Aloud" in error_message
            assert "Listen & Repeat" not in error_message
        engine.assess.assert_not_called()
        assert session.commit.await_count == 2

    async def test_both_failed_mentions_both_in_error_message(self):
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.PENDING,
        )
        read_aloud = _make_analysis(
            analysis_type=AnalysisType.READ_ALOUD, status=AnalysisStatus.FAILED
        )
        listen_repeat = _make_analysis(
            analysis_type=AnalysisType.LISTEN_REPEAT, status=AnalysisStatus.FAILED
        )

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.execute = AsyncMock(
            return_value=_make_execute_result([read_aloud, listen_repeat])
        )
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)
            mock_service.fail_processing = AsyncMock()

            await _run_generate_communication_assessment(
                str(assessment_session.id), _session_factory=session_factory
            )

            error_message = mock_service.fail_processing.call_args.args[1]
            assert "Read Aloud" in error_message
            assert "Listen & Repeat" in error_message


# ── Edge case: duplicate processing ───────────────────────────────────────────


class TestDuplicateProcessing:
    async def test_already_completed_assessment_skips_all_work(self):
        assessment_session = _make_session_row()
        assessment = _make_assessment(
            assessment_session_id=assessment_session.id,
            status=CommunicationAssessmentStatus.COMPLETED,
        )

        session = AsyncMock()
        session.get = AsyncMock(return_value=assessment_session)
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)
        engine = MagicMock()

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=assessment)

            await _run_generate_communication_assessment(
                str(assessment_session.id), _session_factory=session_factory, _engine=engine
            )

        engine.assess.assert_not_called()
        session.execute.assert_not_called()


# ── _mark_failed ──────────────────────────────────────────────────────────────


class TestMarkFailed:
    async def test_sets_status_and_error_message(self):
        session_id = uuid.uuid4()
        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with (
            patch("app.workers.communication_assessment.CommunicationAssessmentRepository"),
            patch(
                "app.workers.communication_assessment.CommunicationAssessmentService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.fail_processing = AsyncMock()

            await _mark_failed(str(session_id), "something went wrong", _session_factory=session_factory)

            mock_service.fail_processing.assert_awaited_once_with(
                session_id, "something went wrong"
            )
        session.commit.assert_awaited_once()

    async def test_db_error_is_swallowed(self):
        session_factory = MagicMock(side_effect=RuntimeError("DB is down"))

        await _mark_failed(str(uuid.uuid4()), "original error", _session_factory=session_factory)


# ── _generate_communication_assessment_task (Celery error classification) ────


class TestCeleryTaskErrorClassification:
    def _make_self(self, retries: int = 0) -> MagicMock:
        mock_self = MagicMock()
        mock_self.request.retries = retries
        mock_self.retry.side_effect = Retry()
        return mock_self

    def test_unexpected_exception_triggers_retry_with_backoff(self):
        mock_self = self._make_self(retries=0)
        exc = RuntimeError("db hiccup")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _generate_communication_assessment_task(mock_self, "some-uuid")

        mock_self.retry.assert_called_once()
        _, retry_kwargs = mock_self.retry.call_args
        assert retry_kwargs["countdown"] == 30  # 30 * 2^0

    def test_retry_backoff_doubles_each_attempt(self):
        mock_self = self._make_self(retries=2)  # third attempt
        exc = RuntimeError("something broke")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _generate_communication_assessment_task(mock_self, "some-uuid")

        _, retry_kwargs = mock_self.retry.call_args
        assert retry_kwargs["countdown"] == 120  # 30 * 2^2

    def test_happy_path_completes_without_retry(self):
        mock_self = self._make_self()

        with patch("asyncio.run", lambda coro: None):
            _generate_communication_assessment_task(mock_self, "some-uuid")

        mock_self.retry.assert_not_called()
