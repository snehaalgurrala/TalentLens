"""
ReadAloudAnalyzer — deterministic engine turning (original sentence,
transcript, recording duration) into a structured ReadAloudAnalysisResult.
No database access, no Celery, no Whisper — pure text in, structured
analysis out, same isolation shape as app.ai.speech.whisper_service.
"""

from __future__ import annotations

from app.ai.communication.comparison import compare_words, normalize_text
from app.ai.communication.metrics import calculate_metrics
from app.ai.communication.schemas import ReadAloudAnalysisResult


class ReadAloudAnalyzer:
    """Reusable Read Aloud scoring engine: sentence + transcript in, analysis out.

    Kept generic enough (normalize -> compare -> score) that a future
    pronunciation-analysis engine can reuse comparison.py/metrics.py, or sit
    alongside this class behind the same ReadAloudAnalysisService facade.
    """

    def analyze(
        self, original_sentence: str, transcript: str, duration_seconds: float
    ) -> ReadAloudAnalysisResult:
        reference_words = normalize_text(original_sentence)
        hypothesis_words = normalize_text(transcript)
        comparison = compare_words(reference_words, hypothesis_words)
        metrics = calculate_metrics(
            comparison,
            total_words=len(reference_words),
            hypothesis_word_count=len(hypothesis_words),
            duration_seconds=duration_seconds,
        )
        return ReadAloudAnalysisResult(comparison=comparison, metrics=metrics)
