"""Unit tests for app.ai.communication.listen_repeat_analyzer and
analysis_service (ListenRepeatAnalyzer / ListenRepeatAnalysisService) — the
end-to-end Communication AI facade, original sentence + candidate transcript
+ duration in, structured semantic analysis out.

semantic_similarity_score is patched throughout (never loads the real
sentence-transformers model in these tests) so results are deterministic and
instantaneous — matches test_local_embedding_service.py's "no download, no
network at test time" convention, and isolates the analyzer's own arithmetic
(keyword coverage, completion, weighted overall score) from embedding-model
behavior, which is covered separately in
test_communication_semantic_similarity.py.
"""

from unittest.mock import patch

import pytest

from app.ai.communication.analysis_service import ListenRepeatAnalysisService
from app.ai.communication.config import (
    KEYWORD_COVERAGE_WEIGHT,
    LISTEN_COMPLETION_WEIGHT,
    SEMANTIC_SIMILARITY_WEIGHT,
)
from app.ai.communication.exceptions import InvalidDurationError
from app.ai.communication.listen_repeat_analyzer import ListenRepeatAnalyzer


def _patch_similarity(value: float):
    return patch(
        "app.ai.communication.listen_repeat_analyzer.semantic_similarity_score",
        return_value=value,
    )


def _expected_overall(similarity: float, coverage: float, completion: float) -> float:
    return round(
        SEMANTIC_SIMILARITY_WEIGHT * similarity
        + KEYWORD_COVERAGE_WEIGHT * coverage
        + LISTEN_COMPLETION_WEIGHT * completion,
        2,
    )


class TestListenRepeatAnalyzer:
    def test_close_paraphrase_with_full_keyword_coverage(self):
        analyzer = ListenRepeatAnalyzer()
        original = "Innovation distinguishes a leader from a follower."
        # Every reference keyword (innovation, distinguishes, leader, follower)
        # literally reappears here, just reordered/reworded around them.
        transcript = "A leader distinguishes itself from a follower through innovation."

        with _patch_similarity(95.0):
            result = analyzer.analyze(original, transcript, duration_seconds=4.0)

        assert result.metrics.semantic_similarity == 95.0
        assert result.metrics.keyword_coverage == 100.0
        assert result.metrics.completion_percentage == 100.0
        assert result.metrics.overall_score == _expected_overall(95.0, 100.0, 100.0)

    def test_synonym_paraphrase_has_partial_keyword_coverage(self):
        analyzer = ListenRepeatAnalyzer()
        original = "The quick brown fox jumps over the lazy dog."
        # "fast"/"leaps" are synonyms of "quick"/"jumps" but not literal
        # matches — keyword coverage alone can't see the paraphrase, which is
        # exactly why semantic_similarity is weighted highest in the formula.
        transcript = "A fast brown fox leaps over a lazy dog."

        with _patch_similarity(88.0):
            result = analyzer.analyze(original, transcript, duration_seconds=4.0)

        assert result.metrics.semantic_similarity == 88.0
        assert 0.0 < result.metrics.keyword_coverage < 100.0
        assert "brown" in result.metrics.matched_keywords
        assert "quick" in result.metrics.missing_keywords

    def test_short_response_has_low_completion_percentage(self):
        analyzer = ListenRepeatAnalyzer()
        original = "Innovation distinguishes a leader from a follower in every industry."
        transcript = "Innovation matters."

        with _patch_similarity(40.0):
            result = analyzer.analyze(original, transcript, duration_seconds=1.0)

        assert result.metrics.hypothesis_word_count == 2
        assert result.metrics.completion_percentage < 50.0

    def test_empty_transcript_scores_zero_without_calling_similarity(self):
        analyzer = ListenRepeatAnalyzer()

        with patch(
            "app.ai.communication.listen_repeat_analyzer.semantic_similarity_score"
        ) as mock_similarity:
            result = analyzer.analyze(
                "Innovation distinguishes a leader.", "", duration_seconds=3.0
            )

        mock_similarity.assert_not_called()
        assert result.metrics.semantic_similarity == 0.0
        assert result.metrics.keyword_coverage == 0.0
        assert result.metrics.completion_percentage == 0.0
        assert result.metrics.overall_score == 0.0

    def test_empty_original_sentence_scores_zero_without_calling_similarity(self):
        analyzer = ListenRepeatAnalyzer()

        with patch(
            "app.ai.communication.listen_repeat_analyzer.semantic_similarity_score"
        ) as mock_similarity:
            result = analyzer.analyze("", "hello world", duration_seconds=3.0)

        mock_similarity.assert_not_called()
        assert result.metrics.reference_word_count == 0
        assert result.metrics.keyword_coverage == 0.0
        assert result.metrics.completion_percentage == 0.0
        assert result.metrics.overall_score == 0.0

    def test_perfect_repeat_scores_100_across_the_board(self):
        analyzer = ListenRepeatAnalyzer()
        sentence = "Innovation distinguishes a leader from a follower."

        with _patch_similarity(100.0):
            result = analyzer.analyze(sentence, sentence, duration_seconds=3.0)

        assert result.metrics.semantic_similarity == 100.0
        assert result.metrics.keyword_coverage == 100.0
        assert result.metrics.completion_percentage == 100.0
        assert result.metrics.overall_score == 100.0

    def test_long_response_completion_is_capped_at_100(self):
        analyzer = ListenRepeatAnalyzer()
        original = "Innovation distinguishes a leader."
        transcript = "Innovation, more than anything else, is what truly distinguishes a leader from everyone else around them."

        with _patch_similarity(70.0):
            result = analyzer.analyze(original, transcript, duration_seconds=6.0)

        assert result.metrics.completion_percentage == 100.0


class TestListenRepeatAnalysisService:
    def test_delegates_to_analyzer(self):
        service = ListenRepeatAnalysisService()
        with _patch_similarity(100.0):
            result = service.analyze("hello world", "hello world", duration_seconds=1.0)

        assert result.metrics.overall_score == 100.0

    def test_negative_duration_raises(self):
        service = ListenRepeatAnalysisService()

        with pytest.raises(InvalidDurationError):
            service.analyze("hello world", "hello world", duration_seconds=-1.0)

    def test_zero_duration_is_valid(self):
        service = ListenRepeatAnalysisService()
        with _patch_similarity(100.0):
            result = service.analyze("hello world", "hello world", duration_seconds=0.0)

        assert result.metrics.overall_score == 100.0
