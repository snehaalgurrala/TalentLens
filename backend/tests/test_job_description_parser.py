"""
Unit tests for app.workers.job_description_parser.

No real database, no real Redis, no real AI service.
All dependencies are injected via the _session_factory / _http_client
keyword arguments on _run_parse_job_description and _mark_failed, so no
module-level patching of AsyncSessionLocal is needed.

Async tests run automatically because asyncio_mode = "auto" in pyproject.toml.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from celery.exceptions import Retry

from app.models.job_description import ParsingStatus
from app.workers.job_description_parser import (
    _PARSER_VERSION,
    _mark_failed,
    _parse_job_description_task,
    _run_parse_job_description,
)

# ── Shared fixture helpers ────────────────────────────────────────────────────


def _make_jd(*, status: ParsingStatus = ParsingStatus.PENDING) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        parsing_status=status,
        parsing_error=None,
        raw_text="We are hiring a Senior Backend Engineer...",
        structured_json=None,
        parser_version=None,
        parsed_at=None,
    )


def _make_ai_response() -> dict:
    return {
        "job": {
            "title": "Senior Backend Engineer",
            "experience_min": 5,
            "experience_max": 8,
            "industry": "Software",
            "employment_type": "Full-time",
            "location": "Remote",
        },
        "structured_jd": {
            "required_skills": ["Python", "SQL"],
            "preferred_skills": ["Kubernetes"],
            "education": ["B.Sc. Computer Science"],
            "projects": [],
            "responsibilities": ["Design APIs", "Mentor engineers"],
            "certifications": [],
        },
        "confidence": 0.9,
    }


def _make_http_client(ai_response: dict) -> AsyncMock:
    """Return a mock AsyncClient whose .post() returns ai_response as JSON."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = ai_response

    client = AsyncMock(spec=httpx.AsyncClient)
    client.post.return_value = mock_resp
    return client


def _make_session_factory(session_mock: AsyncMock) -> MagicMock:
    """Wrap a mock session in an async context manager returned by a callable."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


def _make_repo(jd: SimpleNamespace) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id.return_value = jd
    repo.update.return_value = jd
    return repo


# ── _run_parse_job_description — happy path ──────────────────────────────────


class TestRunParseJobDescriptionHappyPath:
    async def test_parses_and_marks_completed(self):
        jd = _make_jd()
        ai_response = _make_ai_response()
        repo = _make_repo(jd)

        session = AsyncMock()
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)
        http_client = _make_http_client(ai_response)

        with patch(
            "app.workers.job_description_parser.JobDescriptionRepository", return_value=repo
        ):
            await _run_parse_job_description(
                str(jd.id),
                _session_factory=session_factory,
                _http_client=http_client,
            )

        update_calls = repo.update.call_args_list
        # Phase 1: PROCESSING; Phase 3: COMPLETED
        assert len(update_calls) == 2
        assert update_calls[0].kwargs["parsing_status"] == ParsingStatus.PROCESSING

        final_kwargs = update_calls[-1].kwargs
        assert final_kwargs["parsing_status"] == ParsingStatus.COMPLETED
        assert final_kwargs["structured_json"] == {
            "job": ai_response["job"],
            "structured_jd": ai_response["structured_jd"],
            "confidence": ai_response["confidence"],
        }
        assert final_kwargs["parser_version"] == _PARSER_VERSION
        assert final_kwargs["parsing_error"] is None
        assert final_kwargs["parsed_at"] is not None

        assert session.commit.await_count == 2

    async def test_calls_ai_service_with_raw_text(self):
        jd = _make_jd()
        repo = _make_repo(jd)
        session = AsyncMock()
        session_factory = _make_session_factory(session)
        http_client = _make_http_client(_make_ai_response())

        with patch(
            "app.workers.job_description_parser.JobDescriptionRepository", return_value=repo
        ):
            await _run_parse_job_description(
                str(jd.id),
                _session_factory=session_factory,
                _http_client=http_client,
            )

        http_client.post.assert_awaited_once()
        _, kwargs = http_client.post.call_args
        assert kwargs["json"]["jd_text"] == jd.raw_text
        assert kwargs["json"]["parser_version"] == _PARSER_VERSION


# ── _run_parse_job_description — guard paths ─────────────────────────────────


class TestRunParseJobDescriptionGuards:
    async def test_already_completed_skips_all_work(self):
        jd = _make_jd(status=ParsingStatus.COMPLETED)
        repo = _make_repo(jd)

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch(
            "app.workers.job_description_parser.JobDescriptionRepository", return_value=repo
        ):
            await _run_parse_job_description(str(jd.id), _session_factory=session_factory)

        repo.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    async def test_not_found_returns_silently(self):
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch(
            "app.workers.job_description_parser.JobDescriptionRepository", return_value=repo
        ):
            await _run_parse_job_description(str(uuid.uuid4()), _session_factory=session_factory)

        repo.update.assert_not_awaited()

    async def test_missing_structured_key_raises(self):
        jd = _make_jd()
        repo = _make_repo(jd)
        session = AsyncMock()
        session_factory = _make_session_factory(session)
        http_client = _make_http_client({"confidence": 0.5})  # missing job/structured_jd

        with patch(
            "app.workers.job_description_parser.JobDescriptionRepository", return_value=repo
        ):
            with pytest.raises(ValueError, match="job.*structured_jd"):
                await _run_parse_job_description(
                    str(jd.id),
                    _session_factory=session_factory,
                    _http_client=http_client,
                )


# ── _mark_failed ──────────────────────────────────────────────────────────────


class TestMarkFailed:
    async def test_sets_status_and_error_message(self):
        jd = _make_jd()
        repo = _make_repo(jd)

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch(
            "app.workers.job_description_parser.JobDescriptionRepository", return_value=repo
        ):
            await _mark_failed(str(jd.id), "something went wrong", _session_factory=session_factory)

        repo.update.assert_awaited_once_with(
            jd,
            parsing_status=ParsingStatus.FAILED,
            parsing_error="something went wrong",
        )
        session.commit.assert_awaited_once()

    async def test_truncates_long_error_message(self):
        jd = _make_jd()
        repo = _make_repo(jd)
        session = AsyncMock()
        session_factory = _make_session_factory(session)
        long_error = "x" * 2000

        with patch(
            "app.workers.job_description_parser.JobDescriptionRepository", return_value=repo
        ):
            await _mark_failed(str(jd.id), long_error, _session_factory=session_factory)

        stored_msg = repo.update.call_args.kwargs["parsing_error"]
        assert len(stored_msg) == 1000

    async def test_missing_record_does_not_raise(self):
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch(
            "app.workers.job_description_parser.JobDescriptionRepository", return_value=repo
        ):
            await _mark_failed(str(uuid.uuid4()), "error", _session_factory=session_factory)

        repo.update.assert_not_awaited()

    async def test_db_error_is_swallowed(self):
        repo = AsyncMock()
        repo.get_by_id.side_effect = RuntimeError("DB is down")

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch(
            "app.workers.job_description_parser.JobDescriptionRepository", return_value=repo
        ):
            await _mark_failed(str(uuid.uuid4()), "original error", _session_factory=session_factory)


# ── _parse_job_description_task (Celery error classification) ────────────────


class TestCeleryTaskErrorClassification:
    """Tests for the sync task wrapper — verifies retry vs. no-retry decisions."""

    def _make_self(self, retries: int = 0) -> MagicMock:
        mock_self = MagicMock()
        mock_self.request.retries = retries
        mock_self.retry.side_effect = Retry()
        return mock_self

    def test_ai_4xx_raises_without_retry(self):
        mock_self = self._make_self()
        http_exc = httpx.HTTPStatusError(
            "bad request",
            request=MagicMock(),
            response=MagicMock(status_code=422),
        )

        def fake_run(coro):
            if not hasattr(fake_run, "_called"):
                fake_run._called = True
                raise http_exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(httpx.HTTPStatusError):
                _parse_job_description_task(mock_self, "some-uuid")

        mock_self.retry.assert_not_called()

    def test_ai_5xx_triggers_retry_with_backoff(self):
        mock_self = self._make_self(retries=0)
        http_exc = httpx.HTTPStatusError(
            "server error",
            request=MagicMock(),
            response=MagicMock(status_code=503),
        )

        call_count = 0

        def fake_run(coro):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise http_exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _parse_job_description_task(mock_self, "some-uuid")

        mock_self.retry.assert_called_once()
        _, retry_kwargs = mock_self.retry.call_args
        assert retry_kwargs["countdown"] == 30  # 30 * 2^0

    def test_retry_backoff_doubles_each_attempt(self):
        mock_self = self._make_self(retries=2)  # third attempt
        generic_exc = RuntimeError("something broke")

        call_count = 0

        def fake_run(coro):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise generic_exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _parse_job_description_task(mock_self, "some-uuid")

        _, retry_kwargs = mock_self.retry.call_args
        assert retry_kwargs["countdown"] == 120  # 30 * 2^2

    def test_unexpected_exception_triggers_retry(self):
        mock_self = self._make_self()
        generic_exc = ConnectionError("network blip")

        call_count = 0

        def fake_run(coro):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise generic_exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _parse_job_description_task(mock_self, "some-uuid")

        mock_self.retry.assert_called_once()
