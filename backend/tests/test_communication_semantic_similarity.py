"""
Unit tests for app.ai.communication.semantic_similarity.

The real sentence-transformers model is never loaded here — get_model() is
patched, matching test_local_embedding_service.py's "no download, no
network at test time" convention.
"""

from unittest.mock import MagicMock, patch

from app.ai.communication.semantic_similarity import semantic_similarity_score


def _mock_model(vectors: list[list[float]]) -> MagicMock:
    model = MagicMock()
    model.encode = MagicMock(return_value=vectors)
    return model


class TestSemanticSimilarityScore:
    def test_identical_embeddings_score_100(self):
        model = _mock_model([[1.0, 0.0], [1.0, 0.0]])
        with patch("app.ai.communication.semantic_similarity.get_model", return_value=model):
            score = semantic_similarity_score("hello world", "hello world")

        assert score == 100.0

    def test_orthogonal_embeddings_score_50(self):
        model = _mock_model([[1.0, 0.0], [0.0, 1.0]])
        with patch("app.ai.communication.semantic_similarity.get_model", return_value=model):
            score = semantic_similarity_score("a", "b")

        assert score == 50.0

    def test_opposite_embeddings_score_0(self):
        model = _mock_model([[1.0, 0.0], [-1.0, 0.0]])
        with patch("app.ai.communication.semantic_similarity.get_model", return_value=model):
            score = semantic_similarity_score("a", "b")

        assert score == 0.0

    def test_encodes_both_texts_in_a_single_batched_call(self):
        model = _mock_model([[1.0, 0.0], [1.0, 0.0]])
        with patch("app.ai.communication.semantic_similarity.get_model", return_value=model):
            semantic_similarity_score("original sentence", "candidate transcript")

        model.encode.assert_called_once()
        args, _ = model.encode.call_args
        assert args[0] == ["original sentence", "candidate transcript"]
