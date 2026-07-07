"""Unit tests for app.ai.communication.metrics.calculate_metrics."""

from app.ai.communication.metrics import calculate_metrics
from app.ai.communication.schemas import WordComparisonResult, WordSubstitution


def _comparison(
    correct: list[str] | None = None,
    missing: list[str] | None = None,
    extra: list[str] | None = None,
    substitutions: list[WordSubstitution] | None = None,
) -> WordComparisonResult:
    return WordComparisonResult(
        correct_words=correct or [],
        missing_words=missing or [],
        extra_words=extra or [],
        substitutions=substitutions or [],
    )


class TestCalculateMetrics:
    def test_perfect_reading_scores_100(self):
        comparison = _comparison(correct=["the", "quick", "brown", "fox"])
        metrics = calculate_metrics(
            comparison, total_words=4, hypothesis_word_count=4, duration_seconds=60.0
        )

        assert metrics.word_accuracy == 100.0
        assert metrics.completion_percentage == 100.0
        assert metrics.overall_score == 100.0
        assert metrics.reading_speed_wpm == 4.0

    def test_word_accuracy_only_counts_exact_matches(self):
        comparison = _comparison(
            correct=["the", "brown", "fox"],
            substitutions=[WordSubstitution(expected="quick", actual="slow")],
        )
        metrics = calculate_metrics(
            comparison, total_words=4, hypothesis_word_count=4, duration_seconds=60.0
        )

        assert metrics.word_accuracy == 75.0

    def test_completion_percentage_credits_substitutions_but_not_missing(self):
        comparison = _comparison(
            correct=["the", "fox"],
            missing=["brown"],
            substitutions=[WordSubstitution(expected="quick", actual="slow")],
        )
        metrics = calculate_metrics(
            comparison, total_words=4, hypothesis_word_count=3, duration_seconds=60.0
        )

        # 2 correct + 1 substituted out of 4 reference words = 75% completion,
        # but word_accuracy only credits the 2 exact matches = 50%.
        assert metrics.completion_percentage == 75.0
        assert metrics.word_accuracy == 50.0

    def test_empty_transcript_scores_zero_without_raising(self):
        comparison = _comparison(missing=["the", "quick", "brown", "fox"])
        metrics = calculate_metrics(
            comparison, total_words=4, hypothesis_word_count=0, duration_seconds=10.0
        )

        assert metrics.word_accuracy == 0.0
        assert metrics.completion_percentage == 0.0
        assert metrics.overall_score == 0.0
        assert metrics.reading_speed_wpm == 0.0

    def test_empty_reference_sentence_defaults_to_zero(self):
        comparison = _comparison(extra=["hello"])
        metrics = calculate_metrics(
            comparison, total_words=0, hypothesis_word_count=1, duration_seconds=5.0
        )

        assert metrics.word_accuracy == 0.0
        assert metrics.completion_percentage == 0.0
        assert metrics.overall_score == 0.0

    def test_zero_duration_defaults_reading_speed_to_zero(self):
        comparison = _comparison(correct=["hi"])
        metrics = calculate_metrics(
            comparison, total_words=1, hypothesis_word_count=1, duration_seconds=0.0
        )

        assert metrics.reading_speed_wpm == 0.0

    def test_reading_speed_wpm_formula(self):
        comparison = _comparison(correct=["a"] * 10)
        metrics = calculate_metrics(
            comparison, total_words=10, hypothesis_word_count=10, duration_seconds=30.0
        )

        # 10 words in 30s == 20 words/minute
        assert metrics.reading_speed_wpm == 20.0

    def test_overall_score_is_weighted_blend(self):
        comparison = _comparison(correct=["a", "b"], missing=["c", "d"])
        metrics = calculate_metrics(
            comparison, total_words=4, hypothesis_word_count=2, duration_seconds=60.0
        )

        # word_accuracy = 50%, completion_percentage = 50% -> overall = 50%
        assert metrics.word_accuracy == 50.0
        assert metrics.completion_percentage == 50.0
        assert metrics.overall_score == 50.0

    def test_counts_mirror_comparison_lengths(self):
        comparison = _comparison(
            correct=["a"],
            missing=["b", "c"],
            extra=["d"],
            substitutions=[WordSubstitution(expected="e", actual="f")],
        )
        metrics = calculate_metrics(
            comparison, total_words=4, hypothesis_word_count=3, duration_seconds=30.0
        )

        assert metrics.correct_words == 1
        assert metrics.missing_words == 2
        assert metrics.extra_words == 1
        assert metrics.substituted_words == 1
        assert metrics.total_words == 4
