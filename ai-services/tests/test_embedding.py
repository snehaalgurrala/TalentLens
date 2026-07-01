"""
Unit tests for app.services.embedding, app.services.embedding_text, and the
/generate-embedding endpoint.

All provider calls are mocked — no network calls to OpenAI, no real
SentenceTransformers model download. asyncio.sleep is patched wherever
retry backoff is exercised so retry tests run instantly.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import EmbeddingProvider, Settings
from app.main import app
from app.schemas.job_description import JobInfo, StructuredJD
from app.schemas.resume import (
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    StructuredResume,
)
from app.services.embedding import (
    BaseEmbeddingProvider,
    EmbeddingGenerationError,
    EmbeddingService,
    create_embedding_provider,
    get_embedding_service,
    normalize_text,
)
from app.services.embedding_text import (
    build_job_description_embedding_text,
    build_resume_embedding_text,
)


class FakeProvider(BaseEmbeddingProvider):
    """Test double — returns pre-scripted vectors or raises pre-scripted errors."""

    def __init__(self, *, vectors=None, errors_then_vectors=None, model_name="fake-model"):
        self.model_name = model_name
        self._vectors = vectors
        self._errors_then_vectors = list(errors_then_vectors) if errors_then_vectors else None
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if self._errors_then_vectors is not None:
            item = self._errors_then_vectors.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return self._vectors


# ── normalize_text ─────────────────────────────────────────────────────────────


class TestNormalizeText:
    def test_collapses_whitespace(self):
        assert normalize_text("hello   world\n\nfoo") == "hello world foo"

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_text("   hello   ") == "hello"

    def test_truncates_to_max_chars(self):
        result = normalize_text("x" * 100, max_chars=10)
        assert len(result) == 10

    def test_unicode_nfkc_normalization(self):
        # Fullwidth "Ａ" (U+FF21) NFKC-normalizes to ASCII "A"
        assert normalize_text("ＡＢＣ") == "ABC"

    def test_empty_string(self):
        assert normalize_text("") == ""


# ── EmbeddingService — happy path ─────────────────────────────────────────────


class TestEmbeddingServiceHappyPath:
    async def test_generate_embedding_returns_result(self):
        provider = FakeProvider(vectors=[[0.1, 0.2, 0.3]], model_name="text-embedding-3-large")
        service = EmbeddingService(provider)

        result = await service.generate_embedding("Some text")

        assert result.embedding == [0.1, 0.2, 0.3]
        assert result.model == "text-embedding-3-large"
        assert result.dimension == 3

    async def test_generate_embedding_normalizes_text_before_embedding(self):
        provider = FakeProvider(vectors=[[0.1]])
        service = EmbeddingService(provider)

        await service.generate_embedding("hello   \n\n  world")

        assert provider.calls[0] == ["hello world"]

    async def test_generate_embeddings_batch(self):
        provider = FakeProvider(vectors=[[0.1, 0.2], [0.3, 0.4]])
        service = EmbeddingService(provider)

        results = await service.generate_embeddings(["text one", "text two"])

        assert len(results) == 2
        assert results[0].embedding == [0.1, 0.2]
        assert results[1].embedding == [0.3, 0.4]
        assert provider.calls[0] == ["text one", "text two"]

    async def test_respects_max_input_chars(self):
        provider = FakeProvider(vectors=[[0.1]])
        service = EmbeddingService(provider, max_input_chars=5)

        await service.generate_embedding("abcdefghij")

        assert provider.calls[0] == ["abcde"]


# ── EmbeddingService — retry behavior ─────────────────────────────────────────


class TestEmbeddingServiceRetry:
    async def test_retries_then_succeeds(self):
        provider = FakeProvider(
            errors_then_vectors=[ConnectionError("blip"), [[0.5, 0.5]]]
        )
        service = EmbeddingService(provider, max_retries=3, backoff_seconds=0.01)

        with patch("asyncio.sleep", AsyncMock()):
            result = await service.generate_embedding("text")

        assert result.embedding == [0.5, 0.5]
        assert len(provider.calls) == 2

    async def test_exhausts_retries_and_raises(self):
        provider = FakeProvider(
            errors_then_vectors=[
                ConnectionError("1"),
                ConnectionError("2"),
                ConnectionError("3"),
            ]
        )
        service = EmbeddingService(provider, max_retries=2, backoff_seconds=0.01)

        with patch("asyncio.sleep", AsyncMock()):
            with pytest.raises(EmbeddingGenerationError, match="failed after 3 attempts"):
                await service.generate_embedding("text")

        assert len(provider.calls) == 3  # initial attempt + 2 retries

    async def test_backoff_doubles_each_attempt(self):
        provider = FakeProvider(
            errors_then_vectors=[ConnectionError("1"), ConnectionError("2"), [[0.1]]]
        )
        service = EmbeddingService(provider, max_retries=3, backoff_seconds=1.0)

        sleep_calls = []

        async def fake_sleep(seconds):
            sleep_calls.append(seconds)

        with patch("asyncio.sleep", fake_sleep):
            await service.generate_embedding("text")

        assert sleep_calls == [1.0, 2.0]

    async def test_no_retry_needed_does_not_sleep(self):
        provider = FakeProvider(vectors=[[0.1]])
        service = EmbeddingService(provider)

        with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
            await service.generate_embedding("text")

        mock_sleep.assert_not_called()


# ── create_embedding_provider factory ─────────────────────────────────────────


class TestCreateEmbeddingProvider:
    def test_openai_provider_selected(self):
        settings = Settings(
            EMBEDDING_PROVIDER=EmbeddingProvider.openai,
            OPENAI_API_KEY="sk-test",
            OPENAI_EMBEDDING_MODEL="text-embedding-3-large",
        )
        with patch("app.services.embedding.OpenAIEmbeddingProvider") as mock_cls:
            create_embedding_provider(settings)
        mock_cls.assert_called_once_with(api_key="sk-test", model="text-embedding-3-large")

    def test_sentence_transformers_provider_selected(self):
        settings = Settings(
            EMBEDDING_PROVIDER=EmbeddingProvider.sentence_transformers,
            SENTENCE_TRANSFORMERS_MODEL="all-MiniLM-L6-v2",
        )
        with patch("app.services.embedding.SentenceTransformerEmbeddingProvider") as mock_cls:
            create_embedding_provider(settings)
        mock_cls.assert_called_once_with(model="all-MiniLM-L6-v2")


# ── embedding_text builders ───────────────────────────────────────────────────


class TestBuildResumeEmbeddingText:
    def test_includes_summary_and_skills(self):
        structured = StructuredResume(summary="Backend engineer.", skills=["Python", "SQL"])
        text = build_resume_embedding_text(structured)
        assert "Backend engineer." in text
        assert "Skills: Python, SQL" in text

    def test_includes_experience_entries(self):
        structured = StructuredResume(
            experience=[
                ExperienceEntry(
                    company="Acme", role="Engineer", description="Built things."
                )
            ]
        )
        text = build_resume_embedding_text(structured)
        assert "Engineer" in text
        assert "Acme" in text
        assert "Built things." in text

    def test_includes_education_projects_certifications(self):
        structured = StructuredResume(
            education=[EducationEntry(institution="MIT", degree="B.Sc.", field="CS")],
            projects=[ProjectEntry(name="Widget", description="A widget.")],
            certifications=[CertificationEntry(name="AWS Cert", issuer="Amazon")],
        )
        text = build_resume_embedding_text(structured)
        assert "MIT" in text
        assert "Widget" in text
        assert "AWS Cert" in text

    def test_empty_structured_resume_returns_empty_string(self):
        assert build_resume_embedding_text(StructuredResume()) == ""


class TestBuildJobDescriptionEmbeddingText:
    def test_includes_all_populated_fields(self):
        job = JobInfo(
            title="Senior Backend Engineer",
            experience_min=5,
            experience_max=8,
            industry="Software",
            employment_type="Full-time",
            location="Remote",
        )
        structured_jd = StructuredJD(
            required_skills=["Python", "SQL"],
            preferred_skills=["Kubernetes"],
            education=["B.Sc. Computer Science"],
            projects=["Payments rewrite"],
            certifications=["AWS Certified"],
            responsibilities=["Design APIs"],
        )
        text = build_job_description_embedding_text(job, structured_jd)
        assert "Senior Backend Engineer Full-time" in text
        assert "Industry: Software" in text
        assert "Location: Remote" in text
        assert "Experience: 5-8 years" in text
        assert "Required skills: Python, SQL" in text
        assert "Preferred skills: Kubernetes" in text
        assert "Responsibilities: Design APIs" in text
        assert "Education: B.Sc. Computer Science" in text
        assert "Certifications: AWS Certified" in text
        assert "Projects: Payments rewrite" in text

    def test_empty_structured_job_description_returns_empty_string(self):
        assert build_job_description_embedding_text(JobInfo(), StructuredJD()) == ""


# ── /generate-embedding HTTP endpoint ─────────────────────────────────────────


class TestGenerateEmbeddingEndpoint:
    def setup_method(self):
        app.dependency_overrides.clear()

    def _make_client(self, service: EmbeddingService) -> TestClient:
        app.dependency_overrides[get_embedding_service] = lambda: service
        return TestClient(app)

    def test_happy_path_returns_200(self):
        provider = FakeProvider(vectors=[[0.1, 0.2, 0.3]], model_name="text-embedding-3-large")
        client = self._make_client(EmbeddingService(provider))

        resp = client.post("/generate-embedding", json={"text": "Some text to embed"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["embedding"] == [0.1, 0.2, 0.3]
        assert body["model"] == "text-embedding-3-large"
        assert body["dimension"] == 3

    def test_provider_failure_after_retries_returns_502(self):
        provider = FakeProvider(errors_then_vectors=[ConnectionError("down")])
        service = EmbeddingService(provider, max_retries=0, backoff_seconds=0.01)
        client = self._make_client(service)

        resp = client.post("/generate-embedding", json={"text": "text"})

        assert resp.status_code == 502

    def test_empty_text_returns_422(self):
        provider = FakeProvider(vectors=[[0.1]])
        client = self._make_client(EmbeddingService(provider))

        resp = client.post("/generate-embedding", json={"text": ""})

        assert resp.status_code == 422

    def test_missing_text_returns_422(self):
        provider = FakeProvider(vectors=[[0.1]])
        client = self._make_client(EmbeddingService(provider))

        resp = client.post("/generate-embedding", json={})

        assert resp.status_code == 422
