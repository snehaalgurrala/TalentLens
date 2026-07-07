"""Unit tests for app.ai.communication.assessment_rules — the deterministic
strength/improvement/summary rule engine that backs CommunicationAssessmentEngine.
Pure functions, no DB, no mocking required.
"""

from app.ai.communication.assessment_rules import (
    detect_improvements,
    detect_strengths,
    generate_summary,
)
from app.ai.communication.schemas import ListenRepeatAssessmentInput, ReadAloudAssessmentInput


def _read_aloud(**overrides) -> ReadAloudAssessmentInput:
    defaults = dict(
        overall_score=90.0,
        word_accuracy=96.0,
        reading_speed_wpm=130.0,
        completion_percentage=100.0,
    )
    defaults.update(overrides)
    return ReadAloudAssessmentInput(**defaults)


def _listen_repeat(**overrides) -> ListenRepeatAssessmentInput:
    defaults = dict(
        overall_score=90.0,
        semantic_similarity=93.0,
        keyword_coverage=85.0,
        completion_percentage=100.0,
    )
    defaults.update(overrides)
    return ListenRepeatAssessmentInput(**defaults)


# ── detect_strengths ──────────────────────────────────────────────────────────


class TestDetectStrengths:
    def test_high_accuracy_yields_reading_strength(self):
        strengths = detect_strengths(_read_aloud(word_accuracy=95.1), _listen_repeat())
        assert "Reads clearly and accurately" in strengths

    def test_accuracy_at_threshold_is_not_a_strength(self):
        strengths = detect_strengths(_read_aloud(word_accuracy=95.0), _listen_repeat())
        assert "Reads clearly and accurately" not in strengths

    def test_high_similarity_yields_listening_strength(self):
        strengths = detect_strengths(_read_aloud(), _listen_repeat(semantic_similarity=90.1))
        assert "Demonstrates strong listening comprehension" in strengths

    def test_similarity_at_threshold_is_not_a_strength(self):
        strengths = detect_strengths(_read_aloud(), _listen_repeat(semantic_similarity=90.0))
        assert "Demonstrates strong listening comprehension" not in strengths

    def test_comfortable_pace_is_a_strength(self):
        strengths = detect_strengths(_read_aloud(reading_speed_wpm=135.0), _listen_repeat())
        assert "Maintains a comfortable speaking pace" in strengths

    def test_pace_boundaries_are_inclusive(self):
        assert "Maintains a comfortable speaking pace" in detect_strengths(
            _read_aloud(reading_speed_wpm=110.0), _listen_repeat()
        )
        assert "Maintains a comfortable speaking pace" in detect_strengths(
            _read_aloud(reading_speed_wpm=160.0), _listen_repeat()
        )

    def test_pace_outside_comfortable_band_is_not_a_strength(self):
        strengths = detect_strengths(_read_aloud(reading_speed_wpm=170.0), _listen_repeat())
        assert "Maintains a comfortable speaking pace" not in strengths

    def test_all_strengths_present_when_every_metric_strong(self):
        strengths = detect_strengths(
            _read_aloud(word_accuracy=99.0, reading_speed_wpm=140.0),
            _listen_repeat(semantic_similarity=95.0),
        )
        assert strengths == [
            "Reads clearly and accurately",
            "Demonstrates strong listening comprehension",
            "Maintains a comfortable speaking pace",
        ]

    def test_no_strengths_when_every_metric_weak(self):
        strengths = detect_strengths(
            _read_aloud(word_accuracy=50.0, reading_speed_wpm=200.0),
            _listen_repeat(semantic_similarity=50.0),
        )
        assert strengths == []


# ── detect_improvements ───────────────────────────────────────────────────────


class TestDetectImprovements:
    def test_low_accuracy_yields_reading_improvement(self):
        improvements = detect_improvements(_read_aloud(word_accuracy=79.9), _listen_repeat())
        assert "Misses important words while reading" in improvements

    def test_accuracy_at_threshold_is_not_an_improvement(self):
        improvements = detect_improvements(_read_aloud(word_accuracy=80.0), _listen_repeat())
        assert "Misses important words while reading" not in improvements

    def test_low_similarity_yields_listening_improvement(self):
        improvements = detect_improvements(
            _read_aloud(), _listen_repeat(semantic_similarity=74.9)
        )
        assert "Could improve listening comprehension" in improvements

    def test_similarity_at_threshold_is_not_an_improvement(self):
        improvements = detect_improvements(
            _read_aloud(), _listen_repeat(semantic_similarity=75.0)
        )
        assert "Could improve listening comprehension" not in improvements

    def test_too_fast_pace_yields_improvement(self):
        improvements = detect_improvements(_read_aloud(reading_speed_wpm=180.1), _listen_repeat())
        assert "Speaking pace may be difficult to follow" in improvements
        assert "Speaking pace is slower than recommended" not in improvements

    def test_too_slow_pace_yields_improvement(self):
        improvements = detect_improvements(_read_aloud(reading_speed_wpm=89.9), _listen_repeat())
        assert "Speaking pace is slower than recommended" in improvements
        assert "Speaking pace may be difficult to follow" not in improvements

    def test_dead_zone_pace_yields_no_pace_improvement(self):
        improvements = detect_improvements(_read_aloud(reading_speed_wpm=170.0), _listen_repeat())
        assert "Speaking pace may be difficult to follow" not in improvements
        assert "Speaking pace is slower than recommended" not in improvements

    def test_no_improvements_when_every_metric_strong(self):
        improvements = detect_improvements(_read_aloud(), _listen_repeat())
        assert improvements == []

    def test_all_improvements_present_when_every_metric_weak_and_too_fast(self):
        improvements = detect_improvements(
            _read_aloud(word_accuracy=50.0, reading_speed_wpm=200.0),
            _listen_repeat(semantic_similarity=50.0),
        )
        assert improvements == [
            "Misses important words while reading",
            "Could improve listening comprehension",
            "Speaking pace may be difficult to follow",
        ]


# ── generate_summary ──────────────────────────────────────────────────────────


class TestGenerateSummary:
    def test_matches_worked_example_from_spec(self):
        strengths = [
            "Reads clearly and accurately",
            "Demonstrates strong listening comprehension",
        ]
        improvements = ["Speaking pace may be difficult to follow"]

        summary = generate_summary(strengths, improvements)

        assert summary.overview == (
            "The candidate demonstrated strong reading accuracy and good listening "
            "comprehension. Minor improvements are recommended in speaking pace."
        )

    def test_no_strengths_or_improvements(self):
        summary = generate_summary([], [])
        assert summary.overview == (
            "The candidate completed the communication assessment. "
            "No significant areas for improvement were identified."
        )

    def test_reading_strength_only(self):
        summary = generate_summary(["Reads clearly and accurately"], [])
        assert summary.overview.startswith("The candidate demonstrated strong reading accuracy.")

    def test_listening_strength_only(self):
        summary = generate_summary(["Demonstrates strong listening comprehension"], [])
        assert summary.overview.startswith(
            "The candidate demonstrated good listening comprehension."
        )

    def test_duplicate_pace_topic_mentioned_once(self):
        summary = generate_summary(
            [],
            [
                "Speaking pace may be difficult to follow",
                "Misses important words while reading",
            ],
        )
        assert summary.overview.endswith(
            "Minor improvements are recommended in speaking pace and reading accuracy."
        )
