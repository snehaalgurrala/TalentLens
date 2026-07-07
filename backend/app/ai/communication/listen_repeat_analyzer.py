"""
ListenRepeatAnalyzer — deterministic engine turning (original sentence,
candidate transcript, recording duration) into a structured
ListenRepeatAnalysisResult.

Unlike ReadAloudAnalyzer (exact word-for-word comparison via difflib),
Listen & Repeat evaluates semantic understanding: the candidate is expected
to paraphrase, not transcribe verbatim, so scoring leans on sentence-
embedding cosine similarity (semantic_similarity.py) and set-based keyword
coverage (keyword_extraction.py) rather than positional word alignment. No
LLM, no external API call — same local sentence-transformers model already
used for resume/job-description matching, consumed only through its module-
level get_model() singleton, never a second embedding framework.

Scoring formula (see
docs/phase5-sprint5.4-prompt10-listen-repeat-analysis.md for the full
write-up):

    semantic_similarity   = rescaled cosine similarity of the two sentence
                             embeddings, in [0, 100] (semantic_similarity.py)
    keyword_coverage      = % of the reference sentence's significant words
                             also present in the response, order-independent
    completion_percentage = min(hypothesis_word_count / reference_word_count, 1) * 100
    overall_score         = SEMANTIC_SIMILARITY_WEIGHT * semantic_similarity
                           + KEYWORD_COVERAGE_WEIGHT * keyword_coverage
                           + LISTEN_COMPLETION_WEIGHT * completion_percentage

completion_percentage here measures response *length* relative to the
original (did the candidate say roughly as much as was asked?), not
word-for-word positional completion like ReadAloudMetrics — a paraphrase can
legitimately reorder or compress wording, so length is the only completion
signal that doesn't fight against paraphrasing.

recording_duration_seconds is accepted for interface parity with
ReadAloudAnalyzer/AssessmentAnalysisService (and to leave room for a future
speaking-rate metric) but does not currently factor into any Listen & Repeat
metric — unlike Read Aloud, there is no fixed word count to divide by
duration, since a valid paraphrase can be shorter or longer than the
original.
"""

from __future__ import annotations

from app.ai.communication.comparison import normalize_text
from app.ai.communication.config import (
    KEYWORD_COVERAGE_WEIGHT,
    LISTEN_COMPLETION_WEIGHT,
    SEMANTIC_SIMILARITY_WEIGHT,
)
from app.ai.communication.keyword_extraction import extract_keywords, keyword_coverage
from app.ai.communication.schemas import ListenRepeatAnalysisResult, ListenRepeatMetrics
from app.ai.communication.semantic_similarity import semantic_similarity_score


class ListenRepeatAnalyzer:
    """Reusable Listen & Repeat scoring engine: original sentence + candidate
    transcript + duration in, semantic analysis out."""

    def analyze(
        self, original_sentence: str, transcript: str, duration_seconds: float
    ) -> ListenRepeatAnalysisResult:
        reference_words = normalize_text(original_sentence)
        hypothesis_words = normalize_text(transcript)
        reference_word_count = len(reference_words)
        hypothesis_word_count = len(hypothesis_words)

        reference_keywords = extract_keywords(original_sentence)
        coverage_pct, matched, missing = keyword_coverage(reference_keywords, hypothesis_words)

        # An empty response has nothing to compare semantically — skip the
        # embedding call rather than scoring "" against the model, which
        # would otherwise produce a misleading nonzero similarity (see
        # semantic_similarity_score's docstring).
        similarity = (
            semantic_similarity_score(original_sentence, transcript)
            if hypothesis_word_count > 0 and reference_word_count > 0
            else 0.0
        )

        completion_percentage = (
            round(min(hypothesis_word_count / reference_word_count, 1.0) * 100, 2)
            if reference_word_count
            else 0.0
        )

        overall_score = round(
            max(
                0.0,
                min(
                    100.0,
                    SEMANTIC_SIMILARITY_WEIGHT * similarity
                    + KEYWORD_COVERAGE_WEIGHT * coverage_pct
                    + LISTEN_COMPLETION_WEIGHT * completion_percentage,
                ),
            ),
            2,
        )

        metrics = ListenRepeatMetrics(
            reference_word_count=reference_word_count,
            hypothesis_word_count=hypothesis_word_count,
            semantic_similarity=similarity,
            keyword_coverage=coverage_pct,
            completion_percentage=completion_percentage,
            overall_score=overall_score,
            matched_keywords=matched,
            missing_keywords=missing,
        )
        return ListenRepeatAnalysisResult(metrics=metrics)
