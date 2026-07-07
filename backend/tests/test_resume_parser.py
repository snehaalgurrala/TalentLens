"""
Unit tests for app.workers.resume_parser.

No real database, no real Redis, no real AI service.
All dependencies are injected via the _session_factory / _http_client
keyword arguments on _run_parse_resume and _mark_failed, so no
module-level patching of AsyncSessionLocal is needed.

Async tests run automatically because asyncio_mode = "auto" in pyproject.toml.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from celery.exceptions import Retry

from app.models.resume_file import PipelineStage, UploadStatus
from app.workers.resume_parser import (
    _PARSER_VERSION,
    _candidate_kwargs,
    _extract_text,
    _mark_failed,
    _parse_resume_task,
    _run_parse_resume,
)

# ── Shared fixture helpers ────────────────────────────────────────────────────


def _make_rf(
    *,
    status: UploadStatus = UploadStatus.UPLOADED,
    mime_type: str = "application/pdf",
    pipeline_stage: PipelineStage = PipelineStage.APPLIED,
) -> SimpleNamespace:
    campaign_id = uuid.uuid4()
    return SimpleNamespace(
        id=uuid.uuid4(),
        upload_status=status,
        campaign_id=campaign_id,
        storage_path=f"{campaign_id}/file.pdf",
        mime_type=mime_type,
        original_filename="cv.pdf",
        error_message=None,
        candidate_id=None,
        pipeline_stage=pipeline_stage,
    )


def _make_candidate() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


def _make_ai_response(*, email: str | None = "alice@example.com") -> dict:
    # Matches ai-services' actual ParseResumeResponse shape (CandidateInfo
    # nested under "candidate" — see ai-services/app/schemas/resume.py).
    return {
        "candidate": {
            "first_name": "Alice",
            "last_name": "Smith",
            "email": email,
            "phone": "+1-555-0100",
            "linkedin_url": None,
            "github_url": "https://github.com/alice",
            "location": "New York",
            "years_of_experience": 5.0,
            "current_company": "Acme Corp",
            "current_role": "Software Engineer",
        },
        "structured_resume": {},
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


def _make_repos(
    rf: SimpleNamespace,
    candidate: SimpleNamespace,
    *,
    existing_candidate: SimpleNamespace | None = None,
    existing_pr: object = None,
) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    """Return (rf_repo, candidate_repo, parsed_repo) mocks wired to the given objects."""
    rf_repo = AsyncMock()
    rf_repo.get_by_id.return_value = rf
    rf_repo.update.return_value = rf

    candidate_repo = AsyncMock()
    candidate_repo.find_by_email_and_org.return_value = existing_candidate
    candidate_repo.create.return_value = candidate
    candidate_repo.update.return_value = existing_candidate or candidate

    parsed_repo = AsyncMock()
    parsed_repo.find_by_resume_file.return_value = existing_pr

    return rf_repo, candidate_repo, parsed_repo


# ── _candidate_kwargs ─────────────────────────────────────────────────────────


class TestCandidateKwargs:
    def test_maps_all_known_fields(self):
        data = _make_ai_response()
        kwargs = _candidate_kwargs(data)
        assert kwargs["first_name"] == "Alice"
        assert kwargs["last_name"] == "Smith"
        assert kwargs["email"] == "alice@example.com"
        assert kwargs["location"] == "New York"
        assert kwargs["years_of_experience"] == 5.0

    def test_missing_names_default_to_unknown(self):
        kwargs = _candidate_kwargs({})
        assert kwargs["first_name"] == "Unknown"
        assert kwargs["last_name"] == "Unknown"

    def test_empty_string_names_default_to_unknown(self):
        kwargs = _candidate_kwargs({"candidate": {"first_name": "  ", "last_name": ""}})
        assert kwargs["first_name"] == "Unknown"
        assert kwargs["last_name"] == "Unknown"

    def test_null_optional_fields_become_none(self):
        kwargs = _candidate_kwargs({})
        assert kwargs["email"] is None
        assert kwargs["phone"] is None
        assert kwargs["linkedin_url"] is None
        assert kwargs["github_url"] is None
        assert kwargs["location"] is None
        assert kwargs["current_company"] is None
        assert kwargs["current_role"] is None

    def test_fields_at_top_level_are_ignored(self):
        """Regression: ai-services' ParseResumeResponse always nests candidate
        fields under "candidate" (see ai-services/app/schemas/resume.py). A
        top-level first_name/email etc. (the wrong, pre-fix shape) must NOT
        be picked up -- every real parse silently produced "Unknown Unknown"
        with no email/phone/company until this was caught in a live E2E run."""
        kwargs = _candidate_kwargs({"first_name": "Alice", "email": "alice@example.com"})
        assert kwargs["first_name"] == "Unknown"
        assert kwargs["email"] is None


# ── _extract_text ─────────────────────────────────────────────────────────────


class TestExtractText:
    async def test_pdf_mime_calls_pdf_extractor(self):
        with patch(
            "app.workers.resume_parser.extract_text_from_pdf",
            AsyncMock(return_value="pdf text"),
        ) as mock_fn:
            result = await _extract_text("some/path.pdf", "application/pdf")
        assert result == "pdf text"
        mock_fn.assert_awaited_once()

    async def test_docx_mime_calls_docx_extractor(self):
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        with patch(
            "app.workers.resume_parser.extract_text_from_docx",
            AsyncMock(return_value="docx text"),
        ) as mock_fn:
            result = await _extract_text("some/path.docx", mime)
        assert result == "docx text"
        mock_fn.assert_awaited_once()

    async def test_zip_mime_joins_extracted_texts(self):
        with patch(
            "app.workers.resume_parser.extract_text_from_zip",
            AsyncMock(return_value=[("a.pdf", "first"), ("b.pdf", "second")]),
        ):
            result = await _extract_text("some/batch.zip", "application/zip")
        assert "first" in result
        assert "second" in result

    async def test_unsupported_mime_raises_extraction_error(self):
        from app.services.resume_extraction import ExtractionError

        with pytest.raises(ExtractionError, match="Unsupported MIME type"):
            await _extract_text("file.rtf", "application/rtf")


# ── _run_parse_resume — happy paths ──────────────────────────────────────────


class TestRunParseResumeHappyPath:
    async def test_pdf_creates_new_candidate_and_parsed_resume(self):
        rf = _make_rf()
        candidate = _make_candidate()
        ai_response = _make_ai_response()
        rf_repo, candidate_repo, parsed_repo = _make_repos(rf, candidate)

        session = AsyncMock()
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)

        http_client = _make_http_client(ai_response)
        org_id = uuid.uuid4()

        with (
            patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo),
            patch("app.workers.resume_parser.CandidateRepository", return_value=candidate_repo),
            patch("app.workers.resume_parser.ParsedResumeRepository", return_value=parsed_repo),
            patch(
                "app.workers.resume_parser._get_campaign_org_id",
                AsyncMock(return_value=org_id),
            ),
            patch(
                "app.workers.resume_parser._extract_text",
                AsyncMock(return_value="extracted pdf text"),
            ),
        ):
            await _run_parse_resume(
                str(rf.id),
                _session_factory=session_factory,
                _http_client=http_client,
                _embedding_dispatcher=MagicMock(),
            )

        # Candidate created (no existing match)
        candidate_repo.create.assert_awaited_once()
        create_kwargs = candidate_repo.create.call_args.kwargs
        assert create_kwargs["organization_id"] == org_id
        assert create_kwargs["first_name"] == "Alice"

        # ParsedResume created
        parsed_repo.create.assert_awaited_once()
        pr_kwargs = parsed_repo.create.call_args.kwargs
        assert pr_kwargs["raw_text"] == "extracted pdf text"
        assert pr_kwargs["parser_version"] == _PARSER_VERSION
        assert pr_kwargs["candidate_id"] == candidate.id

        # ResumeFile marked PARSED with candidate linked
        rf_update_calls = rf_repo.update.call_args_list
        # Phase 1: PROCESSING; Phase 4: PARSED
        assert len(rf_update_calls) == 2
        final_call_kwargs = rf_update_calls[-1].kwargs
        assert final_call_kwargs["upload_status"] == UploadStatus.PARSED
        assert final_call_kwargs["candidate_id"] == candidate.id
        assert final_call_kwargs["error_message"] is None

        # Session committed twice (once per phase)
        assert session.commit.await_count == 2

    async def test_dispatches_embedding_generation_with_parsed_resume_id(self):
        rf = _make_rf()
        candidate = _make_candidate()
        parsed_resume = SimpleNamespace(id=uuid.uuid4())
        rf_repo, candidate_repo, parsed_repo = _make_repos(rf, candidate)
        parsed_repo.create.return_value = parsed_resume

        session_factory = _make_session_factory(AsyncMock())
        http_client = _make_http_client(_make_ai_response())
        embedding_dispatcher = MagicMock()

        with (
            patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo),
            patch("app.workers.resume_parser.CandidateRepository", return_value=candidate_repo),
            patch("app.workers.resume_parser.ParsedResumeRepository", return_value=parsed_repo),
            patch(
                "app.workers.resume_parser._get_campaign_org_id",
                AsyncMock(return_value=uuid.uuid4()),
            ),
            patch("app.workers.resume_parser._extract_text", AsyncMock(return_value="text")),
        ):
            await _run_parse_resume(
                str(rf.id),
                _session_factory=session_factory,
                _http_client=http_client,
                _embedding_dispatcher=embedding_dispatcher,
            )

        embedding_dispatcher.assert_called_once_with(str(parsed_resume.id))

    async def test_existing_candidate_matched_by_email_is_updated(self):
        rf = _make_rf()
        existing_candidate = _make_candidate()
        ai_response = _make_ai_response(email="existing@example.com")
        rf_repo, candidate_repo, parsed_repo = _make_repos(
            rf, existing_candidate, existing_candidate=existing_candidate
        )

        session = AsyncMock()
        session_factory = _make_session_factory(session)
        http_client = _make_http_client(ai_response)

        with (
            patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo),
            patch("app.workers.resume_parser.CandidateRepository", return_value=candidate_repo),
            patch("app.workers.resume_parser.ParsedResumeRepository", return_value=parsed_repo),
            patch(
                "app.workers.resume_parser._get_campaign_org_id",
                AsyncMock(return_value=uuid.uuid4()),
            ),
            patch("app.workers.resume_parser._extract_text", AsyncMock(return_value="text")),
        ):
            await _run_parse_resume(
                str(rf.id),
                _session_factory=session_factory,
                _http_client=http_client,
                _embedding_dispatcher=MagicMock(),
            )

        # create should NOT be called; update should be
        candidate_repo.create.assert_not_awaited()
        candidate_repo.update.assert_awaited_once()

    async def test_existing_parsed_resume_is_updated_on_retry(self):
        rf = _make_rf()
        candidate = _make_candidate()
        ai_response = _make_ai_response()
        existing_pr = MagicMock()  # simulates an already-existing ParsedResume
        rf_repo, candidate_repo, parsed_repo = _make_repos(
            rf, candidate, existing_pr=existing_pr
        )

        session = AsyncMock()
        session_factory = _make_session_factory(session)
        http_client = _make_http_client(ai_response)

        with (
            patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo),
            patch("app.workers.resume_parser.CandidateRepository", return_value=candidate_repo),
            patch("app.workers.resume_parser.ParsedResumeRepository", return_value=parsed_repo),
            patch(
                "app.workers.resume_parser._get_campaign_org_id",
                AsyncMock(return_value=uuid.uuid4()),
            ),
            patch("app.workers.resume_parser._extract_text", AsyncMock(return_value="text")),
        ):
            await _run_parse_resume(
                str(rf.id),
                _session_factory=session_factory,
                _http_client=http_client,
                _embedding_dispatcher=MagicMock(),
            )

        # ParsedResume updated in place, not recreated
        parsed_repo.create.assert_not_awaited()
        parsed_repo.update.assert_awaited_once_with(
            existing_pr,
            candidate_id=candidate.id,
            raw_text="text",
            structured_json=ai_response,
            parser_version=_PARSER_VERSION,
        )

    async def test_docx_file_uses_docx_extractor(self):
        rf = _make_rf(
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        candidate = _make_candidate()
        rf_repo, candidate_repo, parsed_repo = _make_repos(rf, candidate)

        session = AsyncMock()
        session_factory = _make_session_factory(session)
        http_client = _make_http_client(_make_ai_response())

        with (
            patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo),
            patch("app.workers.resume_parser.CandidateRepository", return_value=candidate_repo),
            patch("app.workers.resume_parser.ParsedResumeRepository", return_value=parsed_repo),
            patch(
                "app.workers.resume_parser._get_campaign_org_id",
                AsyncMock(return_value=uuid.uuid4()),
            ),
            patch(
                "app.workers.resume_parser.extract_text_from_docx",
                AsyncMock(return_value="docx body"),
            ) as mock_docx,
        ):
            await _run_parse_resume(
                str(rf.id),
                _session_factory=session_factory,
                _http_client=http_client,
                _embedding_dispatcher=MagicMock(),
            )

        mock_docx.assert_awaited_once()


# ── _run_parse_resume — idempotency / guard paths ─────────────────────────────


class TestRunParseResumeGuards:
    async def test_already_parsed_skips_all_work(self):
        rf = _make_rf(status=UploadStatus.PARSED)
        rf_repo = AsyncMock()
        rf_repo.get_by_id.return_value = rf

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo):
            await _run_parse_resume(str(rf.id), _session_factory=session_factory)

        # No update, no commit for phase 1
        rf_repo.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    async def test_resume_file_not_found_returns_silently(self):
        rf_repo = AsyncMock()
        rf_repo.get_by_id.return_value = None

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo):
            await _run_parse_resume(str(uuid.uuid4()), _session_factory=session_factory)

        rf_repo.update.assert_not_awaited()

    async def test_missing_org_raises(self):
        rf = _make_rf()
        rf_repo = AsyncMock()
        rf_repo.get_by_id.return_value = rf
        rf_repo.update.return_value = rf

        session = AsyncMock()
        session_factory = _make_session_factory(session)
        http_client = _make_http_client(_make_ai_response())

        with (
            patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo),
            patch(
                "app.workers.resume_parser._get_campaign_org_id",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.workers.resume_parser._extract_text",
                AsyncMock(return_value="text"),
            ),
        ):
            with pytest.raises(RuntimeError, match="org_id"):
                await _run_parse_resume(
                    str(rf.id),
                    _session_factory=session_factory,
                    _http_client=http_client,
                )


# ── _mark_failed ──────────────────────────────────────────────────────────────


class TestMarkFailed:
    async def test_sets_status_and_error_message(self):
        rf = _make_rf()
        rf_repo = AsyncMock()
        rf_repo.get_by_id.return_value = rf

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo):
            await _mark_failed(str(rf.id), "something went wrong", _session_factory=session_factory)

        rf_repo.update.assert_awaited_once_with(
            rf,
            upload_status=UploadStatus.FAILED,
            error_message="something went wrong",
        )
        session.commit.assert_awaited_once()

    async def test_truncates_long_error_message(self):
        rf = _make_rf()
        rf_repo = AsyncMock()
        rf_repo.get_by_id.return_value = rf

        session = AsyncMock()
        session_factory = _make_session_factory(session)
        long_error = "x" * 2000

        with patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo):
            await _mark_failed(str(rf.id), long_error, _session_factory=session_factory)

        stored_msg = rf_repo.update.call_args.kwargs["error_message"]
        assert len(stored_msg) == 1000

    async def test_missing_record_does_not_raise(self):
        rf_repo = AsyncMock()
        rf_repo.get_by_id.return_value = None

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo):
            # Should not raise even though the record is gone
            await _mark_failed(str(uuid.uuid4()), "error", _session_factory=session_factory)

        rf_repo.update.assert_not_awaited()

    async def test_db_error_is_swallowed(self):
        rf_repo = AsyncMock()
        rf_repo.get_by_id.side_effect = RuntimeError("DB is down")

        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with patch("app.workers.resume_parser.ResumeFileRepository", return_value=rf_repo):
            # Must not propagate the DB error
            await _mark_failed(str(uuid.uuid4()), "original error", _session_factory=session_factory)


# ── _parse_resume_task (Celery error classification) ─────────────────────────


class TestCeleryTaskErrorClassification:
    """Tests for the sync task wrapper — verifies retry vs. no-retry decisions."""

    def _make_self(self, retries: int = 0) -> MagicMock:
        mock_self = MagicMock()
        mock_self.request.retries = retries
        mock_self.retry.side_effect = Retry()  # simulates celery task retry
        return mock_self

    def test_extraction_error_raises_without_retry(self):
        from app.services.resume_extraction import ExtractionError

        mock_self = self._make_self()

        # Test the classification logic directly with asyncio.run mocked
        run_calls = []

        def fake_run(coro):
            run_calls.append(coro)
            if not run_calls[1:]:  # first call: _run_parse_resume
                raise ExtractionError("corrupted")
            # second call: _mark_failed — succeeds

        with patch("asyncio.run", fake_run):
            with pytest.raises(ExtractionError):
                _parse_resume_task(mock_self, "some-uuid")

        mock_self.retry.assert_not_called()

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
                _parse_resume_task(mock_self, "some-uuid")

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
            if call_count == 1:  # _run_parse_resume
                raise http_exc
            # _mark_failed succeeds

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _parse_resume_task(mock_self, "some-uuid")

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
                _parse_resume_task(mock_self, "some-uuid")

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
                _parse_resume_task(mock_self, "some-uuid")

        mock_self.retry.assert_called_once()
