"""
ReadAloudAnalysisService / ListenRepeatAnalysisService — Communication AI
facades over ReadAloudAnalyzer / ListenRepeatAnalyzer.

Validate recording duration, delegate to their respective analyzer, and log
the result. No database access, no repositories, no knowledge of
AssessmentTranscript/AssessmentAnalysis — a future sprint decides how
analyses get persisted; this module only turns (sentence, transcript,
duration) into a structured analysis. Mirrors app.ai.speech.speech_service's
isolation from persistence.
"""

from __future__ import annotations

import logging

from app.ai.communication.exceptions import InvalidDurationError
from app.ai.communication.listen_repeat_analyzer import ListenRepeatAnalyzer
from app.ai.communication.read_aloud_analyzer import ReadAloudAnalyzer
from app.ai.communication.schemas import ListenRepeatAnalysisResult, ReadAloudAnalysisResult

logger = logging.getLogger(__name__)


class ReadAloudAnalysisService:
    """Reusable Communication AI entry point: sentence + transcript + duration in, analysis out."""

    def __init__(self, analyzer: ReadAloudAnalyzer | None = None) -> None:
        self.analyzer = analyzer or ReadAloudAnalyzer()

    def analyze(
        self, original_sentence: str, transcript: str, duration_seconds: float
    ) -> ReadAloudAnalysisResult:
        """
        Raises InvalidDurationError for a missing/negative duration. Empty
        transcripts and empty reference sentences are not errors — they are
        valid (if degenerate) inputs that produce zeroed-out metrics.
        """
        if duration_seconds is None or duration_seconds < 0:
            raise InvalidDurationError(
                f"Recording duration must be a non-negative number, got {duration_seconds!r}."
            )
        result = self.analyzer.analyze(original_sentence, transcript, duration_seconds)
        logger.info(
            "Read Aloud analysis complete",
            extra={
                "overall_score": result.metrics.overall_score,
                "word_accuracy": result.metrics.word_accuracy,
                "completion_percentage": result.metrics.completion_percentage,
                "reading_speed_wpm": result.metrics.reading_speed_wpm,
                "total_words": result.metrics.total_words,
            },
        )
        return result


class ListenRepeatAnalysisService:
    """Reusable Communication AI entry point: original sentence + candidate
    transcript + duration in, semantic analysis out."""

    def __init__(self, analyzer: ListenRepeatAnalyzer | None = None) -> None:
        self.analyzer = analyzer or ListenRepeatAnalyzer()

    def analyze(
        self, original_sentence: str, transcript: str, duration_seconds: float
    ) -> ListenRepeatAnalysisResult:
        """
        Raises InvalidDurationError for a missing/negative duration. Empty
        transcripts and empty reference sentences are not errors — they are
        valid (if degenerate) inputs that produce zeroed-out metrics.
        """
        if duration_seconds is None or duration_seconds < 0:
            raise InvalidDurationError(
                f"Recording duration must be a non-negative number, got {duration_seconds!r}."
            )
        result = self.analyzer.analyze(original_sentence, transcript, duration_seconds)
        logger.info(
            "Listen & Repeat analysis complete",
            extra={
                "overall_score": result.metrics.overall_score,
                "semantic_similarity": result.metrics.semantic_similarity,
                "keyword_coverage": result.metrics.keyword_coverage,
                "completion_percentage": result.metrics.completion_percentage,
            },
        )
        return result
