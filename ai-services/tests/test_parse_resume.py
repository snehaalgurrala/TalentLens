"""
Unit tests for the /parse-resume endpoint and underlying parser service.

All LLM calls are replaced with a MockLLMClient that returns pre-scripted
responses — no network calls, no API keys required.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.resume import ParseResumeResponse
from app.services.llm import BaseLLMClient, get_llm_client
from app.services.parser import ParsingError, _extract_json, parse_resume


# ── Test helpers ──────────────────────────────────────────────────────────────


class MockLLMClient(BaseLLMClient):
    """Returns responses from a fixed list in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)

    async def complete(self, prompt: str) -> str:  # noqa: ARG002
        return next(self._responses)


def _valid_response(confidence: float = 0.9) -> str:
    return json.dumps(
        {
            "candidate": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
                "phone": "+1-555-0100",
                "location": "San Francisco, CA",
                "years_of_experience": 5.0,
                "current_company": "Acme Corp",
                "current_role": "Senior Engineer",
            },
            "structured_resume": {
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "experience": [
                    {
                        "company": "Acme Corp",
                        "role": "Senior Engineer",
                        "start_date": "2021-01",
                        "end_date": "present",
                        "description": "Built backend services.",
                    }
                ],
                "education": [
                    {
                        "institution": "State University",
                        "degree": "B.Sc.",
                        "field": "Computer Science",
                        "graduation_year": "2019",
                    }
                ],
                "projects": [],
                "certifications": [],
                "summary": "Experienced backend engineer.",
            },
            "confidence": confidence,
        }
    )


def _minimal_response() -> str:
    """LLM returns only required top-level keys; optional sub-fields are missing."""
    return json.dumps(
        {
            "candidate": {},
            "structured_resume": {},
            "confidence": 0.1,
        }
    )


def _make_client(responses: list[str]) -> TestClient:
    """Override the LLM dependency and return a sync TestClient."""
    mock = MockLLMClient(responses)
    app.dependency_overrides[get_llm_client] = lambda: mock
    return TestClient(app)


# ── _extract_json ─────────────────────────────────────────────────────────────


class TestExtractJson:
    def test_plain_json(self):
        raw = '{"a": 1}'
        assert _extract_json(raw) == {"a": 1}

    def test_strips_markdown_json_fence(self):
        raw = "```json\n{\"a\": 1}\n```"
        assert _extract_json(raw) == {"a": 1}

    def test_strips_plain_fence(self):
        raw = "```\n{\"a\": 1}\n```"
        assert _extract_json(raw) == {"a": 1}

    def test_extracts_json_from_surrounding_prose(self):
        raw = 'Here is the data: {"a": 1} — hope that helps!'
        assert _extract_json(raw) == {"a": 1}

    def test_invalid_raises_json_error(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("not json at all")


# ── parse_resume service ──────────────────────────────────────────────────────


class TestParseResumeService:
    @pytest.mark.asyncio
    async def test_primary_success(self):
        llm = MockLLMClient([_valid_response(0.85)])
        result = await parse_resume("Some resume text", "v1", llm)
        assert isinstance(result, ParseResumeResponse)
        assert result.candidate.first_name == "Jane"
        assert result.confidence == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_bad_json(self):
        """Primary returns non-JSON; fallback returns valid JSON."""
        llm = MockLLMClient(["not json", _valid_response(0.5)])
        result = await parse_resume("Some resume text", "v1", llm)
        assert result.candidate.email == "jane@example.com"

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_schema_mismatch(self):
        """Primary returns JSON that fails Pydantic validation; fallback succeeds."""
        bad = json.dumps({"confidence": "not-a-number", "candidate": "wrong-type"})
        llm = MockLLMClient([bad, _valid_response(0.4)])
        result = await parse_resume("text", "v1", llm)
        assert result.confidence == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_both_attempts_fail_raises_parsing_error(self):
        llm = MockLLMClient(["bad", "also bad"])
        with pytest.raises(ParsingError):
            await parse_resume("text", "v1", llm)

    @pytest.mark.asyncio
    async def test_missing_optional_sub_fields_get_defaults(self):
        """LLM omits optional sub-fields; Pydantic fills in defaults."""
        llm = MockLLMClient([_minimal_response()])
        result = await parse_resume("sparse resume", "v1", llm)
        assert result.candidate.first_name == ""
        assert result.structured_resume.skills == []
        assert result.confidence == pytest.approx(0.1)

    @pytest.mark.asyncio
    async def test_unsupported_version_raises(self):
        llm = MockLLMClient([])
        with pytest.raises(ParsingError, match="Unsupported parser_version"):
            await parse_resume("text", "v99", llm)

    @pytest.mark.asyncio
    async def test_markdown_fence_stripped(self):
        """LLM wraps JSON in ```json ... ``` despite instructions — should still parse."""
        fenced = f"```json\n{_valid_response()}\n```"
        llm = MockLLMClient([fenced])
        result = await parse_resume("resume text", "v1", llm)
        assert result.candidate.last_name == "Doe"


# ── /parse-resume HTTP endpoint ───────────────────────────────────────────────


class TestParseResumeEndpoint:
    def setup_method(self):
        app.dependency_overrides.clear()

    def test_happy_path_returns_200(self):
        client = _make_client([_valid_response()])
        resp = client.post(
            "/parse-resume",
            json={"resume_text": "Jane Doe resume...", "parser_version": "v1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["candidate"]["first_name"] == "Jane"
        assert body["candidate"]["email"] == "jane@example.com"
        assert isinstance(body["structured_resume"]["skills"], list)
        assert 0.0 <= body["confidence"] <= 1.0

    def test_response_matches_schema_exactly(self):
        client = _make_client([_valid_response()])
        resp = client.post(
            "/parse-resume",
            json={"resume_text": "resume", "parser_version": "v1"},
        )
        assert resp.status_code == 200
        # Validate that the response parses cleanly into the response model
        ParseResumeResponse(**resp.json())

    def test_fallback_path_returns_200(self):
        """First LLM response is garbage; second (fallback) succeeds."""
        client = _make_client(["garbage", _valid_response(0.3)])
        resp = client.post(
            "/parse-resume",
            json={"resume_text": "some text", "parser_version": "v1"},
        )
        assert resp.status_code == 200
        assert resp.json()["confidence"] == pytest.approx(0.3)

    def test_both_fail_returns_422(self):
        client = _make_client(["bad1", "bad2"])
        resp = client.post(
            "/parse-resume",
            json={"resume_text": "text", "parser_version": "v1"},
        )
        assert resp.status_code == 422

    def test_unsupported_version_returns_422(self):
        client = _make_client([])
        resp = client.post(
            "/parse-resume",
            json={"resume_text": "text", "parser_version": "v99"},
        )
        assert resp.status_code == 422
        assert "Unsupported" in resp.json()["detail"]

    def test_missing_resume_text_returns_422(self):
        client = _make_client([])
        resp = client.post("/parse-resume", json={"parser_version": "v1"})
        assert resp.status_code == 422

    def test_empty_resume_text_still_calls_llm(self):
        client = _make_client([_valid_response(0.1)])
        resp = client.post(
            "/parse-resume",
            json={"resume_text": "", "parser_version": "v1"},
        )
        assert resp.status_code == 200

    def test_default_parser_version_is_v1(self):
        """Omitting parser_version should default to v1 without error."""
        client = _make_client([_valid_response()])
        resp = client.post("/parse-resume", json={"resume_text": "resume text"})
        assert resp.status_code == 200

    def test_health_endpoint(self):
        resp = TestClient(app).get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
