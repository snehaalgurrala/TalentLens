"""
Deterministic word-level comparison between a reference (original) sentence
and a hypothesis (transcribed) sentence. No LLM, no fuzzy/semantic matching —
pure sequence alignment over normalized word tokens, so the same two strings
always produce the same comparison.
"""

from __future__ import annotations

import difflib
import re

from app.ai.communication.schemas import WordComparisonResult, WordSubstitution

_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> list[str]:
    """Lowercase, strip punctuation, collapse whitespace, split into words.

    Case-insensitive and punctuation-insensitive per spec: "Dog!" and "dog"
    are the same word for comparison purposes. An empty/whitespace-only
    string normalizes to an empty word list rather than raising.
    """
    if not text:
        return []
    stripped = _PUNCTUATION_RE.sub("", text.lower())
    collapsed = _WHITESPACE_RE.sub(" ", stripped).strip()
    return collapsed.split(" ") if collapsed else []


def compare_words(reference_words: list[str], hypothesis_words: list[str]) -> WordComparisonResult:
    """
    Align reference_words against hypothesis_words with difflib's
    SequenceMatcher (Ratcliff/Obershelp). It operates on token *positions*
    rather than a bag-of-words set, so repeated words (e.g. "the the the")
    are each matched against their own position instead of being collapsed —
    a dropped repeat is correctly reported as one missing word rather than
    silently absorbed by an earlier duplicate.

    - equal   -> correct words
    - delete  -> missing words (present in reference, absent from hypothesis)
    - insert  -> extra words (present in hypothesis, absent from reference)
    - replace -> paired position-by-position into substitutions; any length
      mismatch within the replace block spills into missing/extra.
    """
    matcher = difflib.SequenceMatcher(a=reference_words, b=hypothesis_words, autojunk=False)
    correct: list[str] = []
    missing: list[str] = []
    extra: list[str] = []
    substitutions: list[WordSubstitution] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        ref_chunk = reference_words[i1:i2]
        hyp_chunk = hypothesis_words[j1:j2]
        if tag == "equal":
            correct.extend(ref_chunk)
        elif tag == "delete":
            missing.extend(ref_chunk)
        elif tag == "insert":
            extra.extend(hyp_chunk)
        elif tag == "replace":
            paired = min(len(ref_chunk), len(hyp_chunk))
            substitutions.extend(
                WordSubstitution(expected=ref_chunk[k], actual=hyp_chunk[k])
                for k in range(paired)
            )
            missing.extend(ref_chunk[paired:])
            extra.extend(hyp_chunk[paired:])

    return WordComparisonResult(
        correct_words=correct,
        missing_words=missing,
        extra_words=extra,
        substitutions=substitutions,
    )
