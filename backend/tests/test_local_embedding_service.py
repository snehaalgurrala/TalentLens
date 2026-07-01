"""
Unit tests for app.services.local_embedding_service.

The real sentence-transformers model is never loaded in these tests —
get_model()/_load_model() are patched everywhere, so tests run instantly
with no download, no GPU, and no network access, matching this pipeline's
"never call external APIs" requirement even at test time.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.embedding import EmbeddingStatus
from app.services.local_embedding_service import (
    LocalEmbeddingService,
    ModelLoadError,
    build_job_description_embedding_text,
    build_resume_embedding_text,
    get_model,
    l2_normalize,
    normalize_text,
    preload_model,
    reset_model_cache,
)

# ── Fixture builders ────────────────────────────────────────────────────────


def _resume_structured_json(**overrides) -> dict:
    base = {
        "candidate": {
            "years_of_experience": 5.0,
            "current_role": "Engineer",
            "current_company": "Acme",
        },
        "structured_resume": {
            "skills": ["Python", "SQL"],
            "experience": [
                {"role": "Engineer", "company": "Acme", "description": "Built things."}
            ],
            "education": [{"degree": "B.Sc.", "field": "CS", "institution": "MIT"}],
            "projects": [{"name": "Widget", "description": "A widget."}],
            "certifications": [{"name": "AWS Cert", "issuer": "Amazon"}],
            "summary": "Backend engineer.",
        },
        "confidence": 0.9,
    }
    base.update(overrides)
    return base


def _jd_structured_json(**overrides) -> dict:
    base = {
        "job": {
            "title": "Backend Engineer",
            "experience_min": 3,
            "experience_max": 6,
            "industry": "Software",
            "employment_type": "Full-time",
            "location": "Remote",
        },
        "structured_jd": {
            "required_skills": ["Python"],
            "preferred_skills": ["SQL"],
            "education": ["B.Sc. CS"],
            "projects": ["Widget"],
            "responsibilities": ["Build things"],
            "certifications": ["AWS Cert"],
        },
        "confidence": 0.9,
    }
    base.update(overrides)
    return base


def _make_resume(**kwargs) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        structured_json=_resume_structured_json(**kwargs),
        embedding=None,
        embedding_model=None,
        embedding_dimension=None,
        embedding_generated_at=None,
        embedding_status=EmbeddingStatus.PENDING,
    )


def _make_jd(**kwargs) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        structured_json=_jd_structured_json(**kwargs),
        embedding=None,
        embedding_model=None,
        embedding_dimension=None,
        embedding_generated_at=None,
        embedding_status=EmbeddingStatus.PENDING,
    )


def _make_repo_update_passthrough(repo: AsyncMock) -> None:
    """repo.update() mutates and returns the same object, like the real repos do."""

    async def _update(obj, **kwargs):
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    repo.update = AsyncMock(side_effect=_update)


def _mock_model(vector_dim: int = 4) -> MagicMock:
    model = MagicMock()
    model.encode = MagicMock(side_effect=lambda texts, **kwargs: [[0.1] * vector_dim for _ in texts])
    return model


# ── normalize_text / l2_normalize ───────────────────────────────────────────


class TestNormalizeText:
    def test_collapses_whitespace(self):
        assert normalize_text("hello   world\n\nfoo", max_chars=100) == "hello world foo"

    def test_truncates_to_max_chars(self):
        assert len(normalize_text("x" * 50, max_chars=10)) == 10


class TestL2Normalize:
    def test_result_has_unit_norm(self):
        result = l2_normalize([3.0, 4.0])
        norm = sum(x * x for x in result) ** 0.5
        assert norm == pytest.approx(1.0)
        assert result == pytest.approx([0.6, 0.8])

    def test_zero_vector_unchanged(self):
        assert l2_normalize([0.0, 0.0]) == [0.0, 0.0]


# ── text builders ────────────────────────────────────────────────────────────


class TestBuildResumeEmbeddingText:
    def test_includes_summary_skills_and_experience(self):
        text = build_resume_embedding_text(_resume_structured_json())
        assert "Backend engineer." in text
        assert "Skills: Python, SQL" in text
        assert "Engineer" in text and "Acme" in text

    def test_empty_structured_resume_returns_empty_string(self):
        assert build_resume_embedding_text({"structured_resume": {}}) == ""

    def test_missing_structured_resume_key_returns_empty_string(self):
        assert build_resume_embedding_text({}) == ""


class TestBuildJobDescriptionEmbeddingText:
    def test_includes_job_and_structured_jd_fields(self):
        text = build_job_description_embedding_text(_jd_structured_json())
        assert "Backend Engineer Full-time" in text
        assert "Industry: Software" in text
        assert "Required skills: Python" in text
        assert "Experience: 3-6 years" in text

    def test_empty_returns_empty_string(self):
        assert build_job_description_embedding_text({"job": {}, "structured_jd": {}}) == ""


# ── Model loading ─────────────────────────────────────────────────────────────


class TestGetModel:
    def setup_method(self):
        reset_model_cache()

    def teardown_method(self):
        reset_model_cache()

    def test_loads_once_and_reuses_singleton(self):
        fake_model = _mock_model()
        with patch(
            "app.services.local_embedding_service._load_model", return_value=fake_model
        ) as mock_load:
            m1 = get_model("some-model", "cpu")
            m2 = get_model("some-model", "cpu")

        assert m1 is m2
        mock_load.assert_called_once_with("some-model", "cpu")

    def test_reloads_when_model_name_changes(self):
        with patch(
            "app.services.local_embedding_service._load_model", return_value=_mock_model()
        ) as mock_load:
            get_model("model-a", "cpu")
            get_model("model-b", "cpu")

        assert mock_load.call_count == 2

    def test_load_failure_raises_model_load_error(self):
        with patch(
            "app.services.local_embedding_service._load_model",
            side_effect=ModelLoadError("boom"),
        ):
            with pytest.raises(ModelLoadError):
                get_model("bad-model", "cpu")


class TestPreloadModel:
    def setup_method(self):
        reset_model_cache()

    def teardown_method(self):
        reset_model_cache()

    async def test_preload_success_loads_model(self):
        with patch(
            "app.services.local_embedding_service._load_model", return_value=_mock_model()
        ) as mock_load:
            await preload_model()

        mock_load.assert_called_once()

    async def test_preload_failure_is_swallowed_not_raised(self):
        with patch(
            "app.services.local_embedding_service._load_model",
            side_effect=ModelLoadError("no network"),
        ):
            await preload_model()  # must not raise


# ── LocalEmbeddingService — resume embedding ──────────────────────────────


class TestEmbedResume:
    async def test_embed_single_resume_happy_path(self):
        resume = _make_resume()
        parsed_resume_repo = AsyncMock()
        parsed_resume_repo.get_by_id.return_value = resume
        _make_repo_update_passthrough(parsed_resume_repo)
        svc = LocalEmbeddingService(parsed_resume_repo, AsyncMock(), model_name="test-model")

        with patch(
            "app.services.local_embedding_service.get_model", return_value=_mock_model(4)
        ):
            result = await svc.embed_resume(resume.id)

        assert result.embedding_status == EmbeddingStatus.READY
        assert result.embedding_model == "test-model"
        assert result.embedding_dimension == 4
        assert result.embedding_generated_at is not None
        assert len(result.embedding) == 4

    async def test_embed_resume_not_found_raises(self):
        parsed_resume_repo = AsyncMock()
        parsed_resume_repo.get_by_id.return_value = None
        svc = LocalEmbeddingService(parsed_resume_repo, AsyncMock())

        with pytest.raises(ValueError, match="not found"):
            await svc.embed_resume(uuid.uuid4())

    async def test_embed_resume_missing_structured_json_raises(self):
        resume = _make_resume()
        resume.structured_json = None
        parsed_resume_repo = AsyncMock()
        parsed_resume_repo.get_by_id.return_value = resume
        svc = LocalEmbeddingService(parsed_resume_repo, AsyncMock())

        with pytest.raises(ValueError, match="structured_json"):
            await svc.embed_resume(resume.id)

    async def test_embed_resumes_empty_list_returns_empty(self):
        svc = LocalEmbeddingService(AsyncMock(), AsyncMock())
        assert await svc.embed_resumes([]) == []

    async def test_embed_resumes_batches_in_a_single_model_call(self):
        resumes = [_make_resume(), _make_resume(), _make_resume()]
        parsed_resume_repo = AsyncMock()
        parsed_resume_repo.get_by_id.side_effect = lambda rid: next(
            (r for r in resumes if r.id == rid), None
        )
        _make_repo_update_passthrough(parsed_resume_repo)
        svc = LocalEmbeddingService(parsed_resume_repo, AsyncMock())

        mock_model = _mock_model(4)
        with patch("app.services.local_embedding_service.get_model", return_value=mock_model):
            results = await svc.embed_resumes([r.id for r in resumes])

        assert len(results) == 3
        assert mock_model.encode.call_count == 1  # one batched call, not three
        encoded_texts = mock_model.encode.call_args.args[0]
        assert len(encoded_texts) == 3
        for r in results:
            assert r.embedding_status == EmbeddingStatus.READY

    async def test_model_load_failure_marks_all_failed_and_reraises(self):
        resumes = [_make_resume(), _make_resume()]
        parsed_resume_repo = AsyncMock()
        parsed_resume_repo.get_by_id.side_effect = lambda rid: next(
            (r for r in resumes if r.id == rid), None
        )
        _make_repo_update_passthrough(parsed_resume_repo)
        svc = LocalEmbeddingService(parsed_resume_repo, AsyncMock())

        with patch(
            "app.services.local_embedding_service.get_model",
            side_effect=ModelLoadError("no network"),
        ):
            with pytest.raises(ModelLoadError):
                await svc.embed_resumes([r.id for r in resumes])

        for r in resumes:
            assert r.embedding_status == EmbeddingStatus.FAILED


# ── LocalEmbeddingService — job description embedding ─────────────────────


class TestEmbedJobDescription:
    async def test_embed_job_description_happy_path(self):
        jd = _make_jd()
        jd_repo = AsyncMock()
        jd_repo.get_by_id.return_value = jd
        _make_repo_update_passthrough(jd_repo)
        svc = LocalEmbeddingService(AsyncMock(), jd_repo, model_name="test-model")

        with patch(
            "app.services.local_embedding_service.get_model", return_value=_mock_model(4)
        ):
            result = await svc.embed_job_description(jd.id)

        assert result.embedding_status == EmbeddingStatus.READY
        assert result.embedding_model == "test-model"
        assert result.embedding_dimension == 4
        assert result.embedding_generated_at is not None

    async def test_embed_job_description_not_found_raises(self):
        jd_repo = AsyncMock()
        jd_repo.get_by_id.return_value = None
        svc = LocalEmbeddingService(AsyncMock(), jd_repo)

        with pytest.raises(ValueError, match="not found"):
            await svc.embed_job_description(uuid.uuid4())

    async def test_embed_job_description_missing_structured_json_raises(self):
        jd = _make_jd()
        jd.structured_json = None
        jd_repo = AsyncMock()
        jd_repo.get_by_id.return_value = jd
        svc = LocalEmbeddingService(AsyncMock(), jd_repo)

        with pytest.raises(ValueError, match="structured_json"):
            await svc.embed_job_description(jd.id)

    async def test_model_load_failure_marks_failed_and_reraises(self):
        jd = _make_jd()
        jd_repo = AsyncMock()
        jd_repo.get_by_id.return_value = jd
        _make_repo_update_passthrough(jd_repo)
        svc = LocalEmbeddingService(AsyncMock(), jd_repo)

        with patch(
            "app.services.local_embedding_service.get_model",
            side_effect=ModelLoadError("boom"),
        ):
            with pytest.raises(ModelLoadError):
                await svc.embed_job_description(jd.id)

        assert jd.embedding_status == EmbeddingStatus.FAILED


# ── End-to-end: persisted vectors are normalized ───────────────────────────


class TestVectorNormalization:
    async def test_persisted_embedding_is_l2_normalized(self):
        resume = _make_resume()
        parsed_resume_repo = AsyncMock()
        parsed_resume_repo.get_by_id.return_value = resume
        _make_repo_update_passthrough(parsed_resume_repo)
        svc = LocalEmbeddingService(parsed_resume_repo, AsyncMock())

        model = MagicMock()
        model.encode = MagicMock(return_value=[[3.0, 4.0]])  # norm 5 -> not yet unit length
        with patch("app.services.local_embedding_service.get_model", return_value=model):
            result = await svc.embed_resume(resume.id)

        norm = sum(x * x for x in result.embedding) ** 0.5
        assert norm == pytest.approx(1.0)
