"""Unit tests for app.ai.communication.read_aloud_analyzer and analysis_service
(ReadAloudAnalyzer / ReadAloudAnalysisService) — the end-to-end Communication
AI facade, sentence + transcript + duration in, structured analysis out.
"""

import pytest

from app.ai.communication.analysis_service import ReadAloudAnalysisService
from app.ai.communication.exceptions import InvalidDurationError
from app.ai.communication.read_aloud_analyzer import ReadAloudAnalyzer


class TestReadAloudAnalyzer:
    def test_perfect_reading(self):
        analyzer = ReadAloudAnalyzer()
        sentence = "The quick brown fox jumps over the lazy dog."
        result = analyzer.analyze(sentence, sentence, duration_seconds=3.0)

        assert result.metrics.word_accuracy == 100.0
        assert result.metrics.completion_percentage == 100.0
        assert result.metrics.overall_score == 100.0
        assert result.comparison.missing_words == []
        assert result.comparison.extra_words == []

    def test_case_and_punctuation_are_ignored(self):
        analyzer = ReadAloudAnalyzer()
        result = analyzer.analyze("Hello, World!", "hello world", duration_seconds=2.0)

        assert result.metrics.word_accuracy == 100.0
        assert result.comparison.correct_words == ["hello", "world"]

    def test_empty_transcript(self):
        analyzer = ReadAloudAnalyzer()
        result = analyzer.analyze("The quick brown fox", "", duration_seconds=5.0)

        assert result.metrics.word_accuracy == 0.0
        assert result.metrics.completion_percentage == 0.0
        assert result.comparison.missing_words == ["the", "quick", "brown", "fox"]

    def test_empty_sentence(self):
        analyzer = ReadAloudAnalyzer()
        result = analyzer.analyze("", "hello world", duration_seconds=5.0)

        assert result.metrics.total_words == 0
        assert result.metrics.word_accuracy == 0.0
        assert result.metrics.completion_percentage == 0.0
        assert result.comparison.extra_words == ["hello", "world"]

    def test_repeated_words_in_sentence(self):
        analyzer = ReadAloudAnalyzer()
        result = analyzer.analyze("run run run away", "run run away", duration_seconds=2.0)

        assert result.comparison.correct_words == ["run", "run", "away"]
        assert result.comparison.missing_words == ["run"]


class TestReadAloudAnalysisService:
    def test_delegates_to_analyzer(self):
        service = ReadAloudAnalysisService()
        result = service.analyze("hello world", "hello world", duration_seconds=1.0)

        assert result.metrics.overall_score == 100.0

    def test_negative_duration_raises(self):
        service = ReadAloudAnalysisService()

        with pytest.raises(InvalidDurationError):
            service.analyze("hello world", "hello world", duration_seconds=-1.0)

    def test_zero_duration_is_valid(self):
        service = ReadAloudAnalysisService()
        result = service.analyze("hello world", "hello world", duration_seconds=0.0)

        assert result.metrics.reading_speed_wpm == 0.0
