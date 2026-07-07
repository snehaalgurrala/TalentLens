"""
Deterministic semantic similarity between two texts, using the same local
sentence-transformers model already loaded for resume/job-description
matching (app.services.local_embedding_service) — no LLM, no external API
call, and no second embedding framework introduced. Cosine similarity reuses
app.services.matching_service.cosine_similarity, the same formula already
used to score resume/JD embedding similarity.

Encoding the same string through the same model always yields the same
vector, so semantic_similarity_score is a pure function of its two inputs.
"""

from __future__ import annotations

from app.services.local_embedding_service import get_model, l2_normalize
from app.services.matching_service import cosine_similarity


def _encode_pair(text_a: str, text_b: str) -> tuple[list[float], list[float]]:
    model = get_model()
    raw = model.encode(
        [text_a, text_b],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return l2_normalize(list(raw[0])), l2_normalize(list(raw[1]))


def semantic_similarity_score(text_a: str, text_b: str) -> float:
    """
    Embed text_a and text_b with the local model and rescale their cosine
    similarity from [-1, 1] to [0, 100] — the same rescaling
    MatchingService._semantic_score applies to resume/JD cosine similarity —
    so 0 reads as "unrelated meaning" and 100 as "identical meaning" rather
    than the less intuitive raw cosine range.

    Callers with an empty text_a/text_b should not call this at all: an empty
    string still embeds to some fixed, model-dependent vector rather than a
    zero vector, so it can produce a misleadingly nonzero score against
    unrelated text. See ListenRepeatAnalyzer, which guards this case.
    """
    vector_a, vector_b = _encode_pair(text_a, text_b)
    similarity = cosine_similarity(vector_a, vector_b)
    return round(max(0.0, min(100.0, ((similarity + 1) / 2) * 100)), 2)
