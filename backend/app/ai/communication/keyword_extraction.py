"""
Deterministic keyword extraction and coverage scoring — no LLM, no NLP
library beyond the same normalize_text tokenizer used by comparison.py. A
"keyword" is any normalized token from the reference sentence that isn't a
stopword and isn't a single character; coverage is the fraction of those
keywords that also appear (in any order, anywhere) in the candidate's
response, since Listen & Repeat rewards paraphrasing rather than penalizing
reordered words the way ReadAloudAnalyzer's positional comparison does.
"""

from __future__ import annotations

from app.ai.communication.comparison import normalize_text

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "in", "on", "for", "to",
    "with", "at", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "as", "that", "this", "these", "those", "it", "its", "into",
    "over", "under", "than", "then", "so", "if", "not", "no", "do", "does",
    "did", "has", "have", "had", "will", "would", "shall", "should", "can",
    "could", "may", "might", "must", "we", "you", "he", "she", "they", "i",
    "his", "her", "their", "our", "your", "my",
}


def extract_keywords(text: str) -> list[str]:
    """Normalize `text` and return its significant words in order, deduplicated
    (first occurrence kept), filtering out stopwords and single-character
    tokens. Deterministic: the same string always yields the same list."""
    seen: set[str] = set()
    keywords: list[str] = []
    for word in normalize_text(text):
        if word in _STOPWORDS or len(word) <= 1 or word in seen:
            continue
        seen.add(word)
        keywords.append(word)
    return keywords


def keyword_coverage(
    reference_keywords: list[str], hypothesis_words: list[str]
) -> tuple[float, list[str], list[str]]:
    """
    Fraction of reference_keywords present anywhere in hypothesis_words
    (set membership, not position — the candidate may reorder concepts while
    still "covering" them). Returns (coverage_percentage, matched, missing).

    reference_keywords == [] (e.g. a reference sentence with no significant
    words) is a degenerate case with no meaningful coverage signal, scored
    0.0 rather than 100.0 — mirrors ReadAloudMetrics' total_words == 0
    convention (app.ai.communication.metrics) rather than treating "nothing
    to cover" as automatically satisfied.
    """
    if not reference_keywords:
        return 0.0, [], []
    hypothesis_set = set(hypothesis_words)
    matched = [kw for kw in reference_keywords if kw in hypothesis_set]
    missing = [kw for kw in reference_keywords if kw not in hypothesis_set]
    coverage = round(len(matched) / len(reference_keywords) * 100, 2)
    return coverage, matched, missing
