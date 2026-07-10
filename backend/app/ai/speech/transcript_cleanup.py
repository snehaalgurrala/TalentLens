"""
Post-processing for Whisper's raw transcript text — cosmetic cleanup only.

Never rewrites, reorders, or removes anything a candidate actually said.
Only collapses whitespace noise and drops standalone non-lexical filler
interjections ("um", "uh", ...) that Whisper sometimes transcribes
literally — punctuation and every real word are left exactly as decoded.
"""

from __future__ import annotations

import re
import string

_FILLER_WORDS = {"um", "umm", "uhm", "uh", "uhh", "erm", "hmm", "mhm"}


def _is_filler(token: str) -> bool:
    return token.strip(string.punctuation).lower() in _FILLER_WORDS


def clean_transcript(text: str) -> str:
    """Collapse repeated whitespace and drop standalone filler words."""
    if not text:
        return text

    tokens = [token for token in text.split() if not _is_filler(token)]
    cleaned = " ".join(tokens)
    return re.sub(r"\s+", " ", cleaned).strip()
