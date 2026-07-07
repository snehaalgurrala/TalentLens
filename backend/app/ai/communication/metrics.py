"""
Deterministic communication metrics computed from a WordComparisonResult.

Scoring formula (see docs/phase5-sprint5.4-prompt9-read-aloud-analysis.md
for the full write-up):

    word_accuracy         = correct_words / total_words * 100
    completion_percentage = min(correct_words + substituted_words, total_words)
                             / total_words * 100
    reading_speed_wpm     = hypothesis_word_count / (duration_seconds / 60)
    overall_score         = WORD_ACCURACY_WEIGHT * word_accuracy
                           + COMPLETION_WEIGHT * completion_percentage

word_accuracy rewards only exact matches; completion_percentage additionally
credits substituted words (an attempt was made at that position, even if
wrong) to distinguish "read the whole sentence with some mistakes" from
"stopped partway through" — two very different reading behaviors that
word_accuracy alone can't tell apart.

total_words == 0 (empty reference sentence) is a degenerate case with no
meaningful accuracy/completion signal; both metrics are defined as 0.0
rather than raising, so a malformed reference never crashes the pipeline.
duration_seconds <= 0 likewise defines reading_speed_wpm as 0.0.
"""

from __future__ import annotations

from app.ai.communication.config import COMPLETION_WEIGHT, WORD_ACCURACY_WEIGHT
from app.ai.communication.schemas import ReadAloudMetrics, WordComparisonResult


def calculate_metrics(
    comparison: WordComparisonResult,
    *,
    total_words: int,
    hypothesis_word_count: int,
    duration_seconds: float,
) -> ReadAloudMetrics:
    correct_words = len(comparison.correct_words)
    missing_words = len(comparison.missing_words)
    extra_words = len(comparison.extra_words)
    substituted_words = len(comparison.substitutions)

    word_accuracy = round((correct_words / total_words) * 100, 2) if total_words else 0.0
    completion_percentage = (
        round(min(correct_words + substituted_words, total_words) / total_words * 100, 2)
        if total_words
        else 0.0
    )
    reading_speed_wpm = (
        round(hypothesis_word_count / (duration_seconds / 60), 2) if duration_seconds > 0 else 0.0
    )
    overall_score = round(
        max(
            0.0,
            min(
                100.0,
                WORD_ACCURACY_WEIGHT * word_accuracy + COMPLETION_WEIGHT * completion_percentage,
            ),
        ),
        2,
    )

    return ReadAloudMetrics(
        total_words=total_words,
        correct_words=correct_words,
        missing_words=missing_words,
        extra_words=extra_words,
        substituted_words=substituted_words,
        word_accuracy=word_accuracy,
        completion_percentage=completion_percentage,
        reading_speed_wpm=reading_speed_wpm,
        overall_score=overall_score,
    )
