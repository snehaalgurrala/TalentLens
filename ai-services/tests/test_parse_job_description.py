"""
Unit tests for the /parse-job-description endpoint and underlying parser service.

All LLM calls are replaced with a MockLLMClient that returns pre-scripted
responses — no network calls, no API keys required.
"""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.job_description import ParseJobDescriptionResponse
from app.services.job_description_parser import ParsingError, parse_job_description
from app.services.llm import BaseLLMClient, get_llm_client


# ── Test helpers ──────────────────────────────────────────────────────────────


class MockLLMClient(BaseLLMClient):
    """Returns responses from a fixed list in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)

    async def complete(self, prompt: str) -> str:  # noqa: ARG002
        return next(self._responses)


def _valid_response(confidence: float = 0.97) -> str:
    return json.dumps(
        {
            "job": {
                "title": "Senior Backend Engineer",
                "experience_min": 5,
                "experience_max": 8,
                "industry": "Software",
                "employment_type": "Full-time",
                "location": "Remote",
            },
            "structured_jd": {
                "required_skills": ["Python", "FastAPI", "PostgreSQL"],
                "preferred_skills": ["Kubernetes"],
                "education": ["B.Sc. Computer Science"],
                "projects": ["Payments platform rewrite"],
                "responsibilities": ["Design APIs", "Mentor engineers"],
                "certifications": ["AWS Certified Developer"],
            },
            "confidence": confidence,
        }
    )


def _minimal_response() -> str:
    """LLM returns only the required top-level keys; sub-fields are missing."""
    return json.dumps(
        {
            "job": {},
            "structured_jd": {},
            "confidence": 0.1,
        }
    )


def _make_client(responses: list[str]) -> TestClient:
    """Override the LLM dependency and return a sync TestClient."""
    mock = MockLLMClient(responses)
    app.dependency_overrides[get_llm_client] = lambda: mock
    return TestClient(app)


# ── parse_job_description service ─────────────────────────────────────────────


class TestParseJobDescriptionService:
    @pytest.mark.asyncio
    async def test_primary_success(self):
        llm = MockLLMClient([_valid_response(0.85)])
        result = await parse_job_description("Some job description text", "v1", llm)
        assert isinstance(result, ParseJobDescriptionResponse)
        assert result.job.title == "Senior Backend Engineer"
        assert result.job.experience_min == 5
        assert result.job.experience_max == 8
        assert result.structured_jd.required_skills == [
            "Python",
            "FastAPI",
            "PostgreSQL",
        ]
        assert result.confidence == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_bad_json(self):
        llm = MockLLMClient(["not json", _valid_response(0.5)])
        result = await parse_job_description("Some job description text", "v1", llm)
        assert result.job.employment_type == "Full-time"

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_schema_mismatch(self):
        bad = json.dumps({"confidence": "not-a-number", "job": "wrong-type"})
        llm = MockLLMClient([bad, _valid_response(0.4)])
        result = await parse_job_description("text", "v1", llm)
        assert result.confidence == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_strict_type_mismatch(self):
        """experience_min as a string should fail strict validation and trigger fallback."""
        bad = json.dumps(
            {
                "job": {"title": "", "experience_min": "5", "experience_max": 8},
                "structured_jd": {},
                "confidence": 0.5,
            }
        )
        llm = MockLLMClient([bad, _valid_response(0.6)])
        result = await parse_job_description("text", "v1", llm)
        assert result.confidence == pytest.approx(0.6)

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_unknown_field(self):
        """extra='forbid' should reject unexpected fields and trigger fallback."""
        bad = json.dumps(
            {
                "job": {"title": "", "seniority_level": "Senior"},  # dropped field
                "structured_jd": {},
                "confidence": 0.5,
            }
        )
        llm = MockLLMClient([bad, _valid_response(0.6)])
        result = await parse_job_description("text", "v1", llm)
        assert result.confidence == pytest.approx(0.6)

    @pytest.mark.asyncio
    async def test_both_attempts_fail_raises_parsing_error(self):
        llm = MockLLMClient(["bad", "also bad"])
        with pytest.raises(ParsingError):
            await parse_job_description("text", "v1", llm)

    @pytest.mark.asyncio
    async def test_missing_optional_sub_fields_get_defaults(self):
        llm = MockLLMClient([_minimal_response()])
        result = await parse_job_description("sparse jd", "v1", llm)
        assert result.job.title == ""
        assert result.job.experience_min == 0
        assert result.structured_jd.required_skills == []
        assert result.confidence == pytest.approx(0.1)

    @pytest.mark.asyncio
    async def test_unsupported_version_raises(self):
        llm = MockLLMClient([])
        with pytest.raises(ParsingError, match="Unsupported parser_version"):
            await parse_job_description("text", "v99", llm)

    @pytest.mark.asyncio
    async def test_markdown_fence_stripped(self):
        fenced = f"```json\n{_valid_response()}\n```"
        llm = MockLLMClient([fenced])
        result = await parse_job_description("job description text", "v1", llm)
        assert result.job.employment_type == "Full-time"


# ── Schema-level strict validation ────────────────────────────────────────────


class TestStrictValidation:
    def test_extra_field_on_job_rejected(self):
        with pytest.raises(ValidationError):
            ParseJobDescriptionResponse(
                job={"title": "Eng", "extra_field": "nope"},
                structured_jd={},
                confidence=0.5,
            )

    def test_string_experience_rejected_in_strict_mode(self):
        with pytest.raises(ValidationError):
            ParseJobDescriptionResponse(
                job={"experience_min": "5"},
                structured_jd={},
                confidence=0.5,
            )

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            ParseJobDescriptionResponse(job={}, structured_jd={}, confidence=1.5)

    def test_negative_experience_rejected(self):
        with pytest.raises(ValidationError):
            ParseJobDescriptionResponse(
                job={"experience_min": -1}, structured_jd={}, confidence=0.5
            )


# ── /parse-job-description HTTP endpoint ──────────────────────────────────────


class TestParseJobDescriptionEndpoint:
    def setup_method(self):
        app.dependency_overrides.clear()

    def test_happy_path_returns_200(self):
        client = _make_client([_valid_response()])
        resp = client.post(
            "/parse-job-description",
            json={"jd_text": "We are hiring...", "parser_version": "v1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["job"]["title"] == "Senior Backend Engineer"
        assert isinstance(body["structured_jd"]["required_skills"], list)
        assert 0.0 <= body["confidence"] <= 1.0

    def test_response_matches_schema_exactly(self):
        client = _make_client([_valid_response()])
        resp = client.post(
            "/parse-job-description",
            json={"jd_text": "jd text", "parser_version": "v1"},
        )
        assert resp.status_code == 200
        ParseJobDescriptionResponse(**resp.json())

    def test_fallback_path_returns_200(self):
        client = _make_client(["garbage", _valid_response(0.3)])
        resp = client.post(
            "/parse-job-description",
            json={"jd_text": "some text", "parser_version": "v1"},
        )
        assert resp.status_code == 200
        assert resp.json()["confidence"] == pytest.approx(0.3)

    def test_both_fail_returns_422(self):
        client = _make_client(["bad1", "bad2"])
        resp = client.post(
            "/parse-job-description",
            json={"jd_text": "text", "parser_version": "v1"},
        )
        assert resp.status_code == 422

    def test_unsupported_version_returns_422(self):
        client = _make_client([])
        resp = client.post(
            "/parse-job-description",
            json={"jd_text": "text", "parser_version": "v99"},
        )
        assert resp.status_code == 422
        assert "Unsupported" in resp.json()["detail"]

    def test_missing_text_returns_422(self):
        client = _make_client([])
        resp = client.post("/parse-job-description", json={"parser_version": "v1"})
        assert resp.status_code == 422

    def test_old_field_name_rejected(self):
        """The old job_description_text field name must no longer be accepted."""
        client = _make_client([])
        resp = client.post(
            "/parse-job-description",
            json={"job_description_text": "text", "parser_version": "v1"},
        )
        assert resp.status_code == 422

    def test_default_parser_version_is_v1(self):
        client = _make_client([_valid_response()])
        resp = client.post("/parse-job-description", json={"jd_text": "jd text"})
        assert resp.status_code == 200
