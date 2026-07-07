"""Unit tests for CommunicationAssessmentEngine — the pure scoring layer
that combines assessment_rules output with the overall/confidence score
formulas. No DB, no mocking required.
"""

from app.ai.communication.communication_assessment_engine import CommunicationAssessmentEngine
from app.ai.communication.schemas import ListenRepeatAssessmentInput, ReadAloudAssessmentInput


def _read_aloud(**overrides) -> ReadAloudAssessmentInput:
    defaults = dict(
        overall_score=80.0,
        word_accuracy=96.0,
        reading_speed_wpm=130.0,
        completion_percentage=90.0,
    )
    defaults.update(overrides)
    return ReadAloudAssessmentInput(**defaults)


def _listen_repeat(**overrides) -> ListenRepeatAssessmentInput:
    defaults = dict(
        overall_score=60.0,
        semantic_similarity=93.0,
        keyword_coverage=85.0,
        completion_percentage=100.0,
    )
    defaults.update(overrides)
    return ListenRepeatAssessmentInput(**defaults)


class TestCommunicationAssessmentEngine:
    def test_overall_score_is_equal_weight_average(self):
        result = CommunicationAssessmentEngine().assess(
            _read_aloud(overall_score=80.0), _listen_repeat(overall_score=60.0)
        )
        assert result.overall_score == 70.0

    def test_reading_and_listening_scores_pass_through_overall_score(self):
        result = CommunicationAssessmentEngine().assess(
            _read_aloud(overall_score=88.5), _listen_repeat(overall_score=71.5)
        )
        assert result.reading_score == 88.5
        assert result.listening_score == 71.5

    def test_confidence_score_is_equal_weight_average_of_three_components(self):
        result = CommunicationAssessmentEngine().assess(
            _read_aloud(completion_percentage=90.0),
            _listen_repeat(completion_percentage=100.0, semantic_similarity=80.0),
        )
        # (90 + 100 + 80) / 3
        assert round(result.confidence_score, 4) == round(270.0 / 3, 4)

    def test_returns_strengths_and_improvements_from_rule_engine(self):
        result = CommunicationAssessmentEngine().assess(
            _read_aloud(word_accuracy=99.0, reading_speed_wpm=130.0),
            _listen_repeat(semantic_similarity=95.0),
        )
        assert "Reads clearly and accurately" in result.strengths
        assert "Demonstrates strong listening comprehension" in result.strengths
        assert result.improvements == []

    def test_summary_is_present_and_non_empty(self):
        result = CommunicationAssessmentEngine().assess(_read_aloud(), _listen_repeat())
        assert result.summary.overview
