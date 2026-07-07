# TalentLens — Phase 5, Sprint 5.4, Prompt 10
# Listen & Repeat Analysis Engine

Status: Implemented. Every completed Listen & Repeat transcript is now
automatically scored against a fixed reference sentence with a
deterministic, LLM-free **semantic** analysis engine — off the request path,
same as Read Aloud and transcription before it. Unlike Read Aloud's exact
word-for-word comparison, Listen & Repeat evaluates whether the candidate
understood and could paraphrase the sentence, not whether they repeated it
verbatim.

```
Recording → Whisper → AssessmentTranscript (COMPLETED, LISTEN_REPEAT only)
                              │
                              ▼
                        Celery Queue
                              │
                              ▼
              ListenRepeatAnalysisService (app.ai.communication)
                    │              │              │
        semantic_similarity.py  keyword_extraction.py  (completion: word count)
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
                          AssessmentAnalysis
                                   │
                                   ▼
                 GET /assessment/analysis/{transcript_id}
```

No new table, no new endpoint, no second embedding framework — this sprint
is a structural sibling of
`docs/phase5-sprint5.4-prompt9-read-aloud-analysis.md`, reusing everything
that pipeline already built except the scoring algorithm itself.

---

## 1. Architecture

```
backend/app/
├── ai/communication/
│   ├── config.py                    # reference sentences + scoring weights (both engines)
│   ├── exceptions.py                # CommunicationAnalysisError, InvalidDurationError (shared)
│   ├── schemas.py                   # + ListenRepeatMetrics, ListenRepeatAnalysisResult
│   ├── comparison.py                # normalize_text (shared tokenizer), compare_words (Read Aloud only)
│   ├── metrics.py                   # Read Aloud scoring formula (unchanged)
│   ├── keyword_extraction.py        # NEW — extract_keywords, keyword_coverage
│   ├── semantic_similarity.py       # NEW — semantic_similarity_score (local embedding model)
│   ├── read_aloud_analyzer.py       # ReadAloudAnalyzer (unchanged)
│   ├── listen_repeat_analyzer.py    # NEW — ListenRepeatAnalyzer
│   └── analysis_service.py          # + ListenRepeatAnalysisService facade
├── models/assessment_analysis.py    # + AnalysisType.LISTEN_REPEAT, semantic_similarity/keyword_coverage columns
├── repositories/assessment_analysis.py  # unchanged — already transcript_id-generic
├── services/assessment_analysis.py  # create_pending(analysis_type=...), + complete_listen_repeat_processing
├── workers/communication_analysis.py    # + analyze_listen_repeat Celery task
├── workers/speech_transcription.py  # Phase 5 dispatches by recording_type (READ_ALOUD | LISTEN_REPEAT)
├── schemas/assessment_analysis.py   # + semantic_similarity, keyword_coverage fields
└── api/v1/endpoints/
    └── assessment_analysis.py       # unchanged — already analysis_type-agnostic
```

### Layering rules preserved

- **Routers never touch AI or Celery internals directly** — no change needed;
  the existing `GET /assessment/analysis/{transcript_id}` endpoint already
  just calls `AssessmentAnalysisService.get_analysis` and returns whatever
  row exists, regardless of `analysis_type`.
- **Services never import AI schemas or Celery tasks at module scope.**
  `AssessmentAnalysisService.complete_listen_repeat_processing` takes plain
  scalar kwargs, exactly like `complete_processing` does for Read Aloud —
  only the Celery worker glues AI-layer output (`ListenRepeatMetrics`) to
  service-layer kwargs.
- **Only `app/workers/communication_analysis.py` calls
  `ListenRepeatAnalysisService`.** No other module imports
  `app.ai.communication.*`.
- **No LLM calls anywhere in this pipeline.** Semantic similarity is cosine
  distance over sentence-transformers embeddings (the same local model
  already used for resume/JD matching); keyword coverage is set membership
  over normalized tokens. Same transcript + same reference sentence always
  produces the same analysis — deterministic, offline, reproducible.
- **No second embedding framework.** `semantic_similarity.py` consumes the
  existing `app.services.local_embedding_service.get_model()` singleton and
  `app.services.matching_service.cosine_similarity` — it never loads its own
  model or vendors its own cosine implementation.

---

## 2. Entity: `AssessmentAnalysis` (extended, not duplicated)

Per spec, Listen & Repeat reuses the existing `AssessmentAnalysis` entity —
no new table. Two nullable columns were added for the metrics that don't
already have a Read-Aloud-shaped equivalent:

| Column | Type | Used by |
|---|---|---|
| `semantic_similarity` | `Float`, nullable | LISTEN_REPEAT only |
| `keyword_coverage` | `Float`, nullable | LISTEN_REPEAT only |
| `overall_score` | `Float`, nullable | **both** |
| `completion_percentage` | `Float`, nullable | **both** (different formula per type — see §4) |
| `word_accuracy` / `correct_words` / `missing_words` / `extra_words` / `substituted_words` / `total_words` / `reading_speed_wpm` | nullable | READ_ALOUD only — stay `NULL` on LISTEN_REPEAT rows |
| `analysis_json` | `JSONB`, nullable | **both** — holds the full metrics payload (matched/missing keywords, word counts) for LISTEN_REPEAT, and the word comparison detail for READ_ALOUD |
| `analysis_type` | `Enum(AnalysisType)` | `READ_ALOUD` \| `LISTEN_REPEAT` |

Migration: `alembic/versions/e3f4a5b6c7d8_add_listen_repeat_analysis.py`
(`down_revision = "d2e3f4a5b6c7"`). Adds the `LISTEN_REPEAT` value to the
existing `analysistype` Postgres enum via `ALTER TYPE ... ADD VALUE` inside
an `autocommit_block()` (required — Postgres forbids `ALTER TYPE ... ADD
VALUE` and a later read of that value in the same transaction; env.py wraps
the whole migration run in one transaction otherwise), then adds the two new
nullable columns with a plain `op.add_column`. Downgrade is intentionally
unsupported (roll-forward only) — Postgres cannot drop a single enum value
without a full type rebuild, same convention as
`d1e2f3a4b5c6_extend_pipeline_and_activity_enums.py`.

---

## 3. Keyword extraction (`app/ai/communication/keyword_extraction.py`)

```python
extract_keywords(text) -> list[str]
keyword_coverage(reference_keywords, hypothesis_words) -> (coverage_pct, matched, missing)
```

- **`extract_keywords`** reuses `comparison.normalize_text` for tokenization
  (same lowercase/punctuation-strip/whitespace-collapse rules as Read Aloud),
  then drops a small fixed stopword set and single-character tokens, and
  deduplicates keeping first occurrence — deterministic, no NLP library.
- **`keyword_coverage`** is **set membership**, not position: it counts how
  many of the reference sentence's significant words appear *anywhere* in
  the candidate's response. This is the key difference from
  `comparison.compare_words` (Read Aloud's positional diff) — a paraphrase
  that reorders concepts should not be penalized for word order the way an
  exact reading should.
- `reference_keywords == []` (a reference sentence with no significant
  words) scores `0.0`, not `100.0` — mirrors `ReadAloudMetrics`'
  `total_words == 0 → 0.0` convention: "nothing to cover" is a degenerate
  input, not an automatically-satisfied one.

---

## 4. Semantic similarity (`app/ai/communication/semantic_similarity.py`)

```python
semantic_similarity_score(text_a, text_b) -> float   # [0, 100]
```

1. Both strings are encoded in a **single batched call** to the process-wide
   local embedding model singleton
   (`app.services.local_embedding_service.get_model()` — the same
   `sentence-transformers` model already loaded for resume/JD matching, no
   new model, no network call).
2. Each resulting vector is L2-normalized
   (`local_embedding_service.l2_normalize`, the same helper
   `LocalEmbeddingService._encode_sync` uses).
3. Cosine similarity is computed with
   `app.services.matching_service.cosine_similarity` — the exact function
   already scoring resume/JD embedding similarity, reused verbatim rather
   than reimplemented.
4. The raw `[-1, 1]` cosine value is rescaled to `[0, 100]` with
   `((similarity + 1) / 2) * 100` — the same rescaling
   `MatchingService._semantic_score` applies — so `0` reads as "unrelated
   meaning" and `100` as "identical meaning."

Encoding the same string through the same model always produces the same
vector, so this function is a pure, deterministic function of its two
inputs — no LLM sampling, no randomness.

**Guard in `ListenRepeatAnalyzer`:** an empty transcript (or empty reference
sentence) never reaches this function. An empty string still embeds to
*some* fixed, model-dependent vector — not a zero vector — so scoring `""`
against real text could produce a misleading nonzero similarity. The
analyzer short-circuits to `semantic_similarity = 0.0` whenever either side
normalizes to zero words, without paying the embedding-model cost.

---

## 5. Scoring formula (`app/ai/communication/listen_repeat_analyzer.py`)

```
semantic_similarity   = semantic_similarity_score(original_sentence, transcript)     [0, 100]
keyword_coverage      = keyword_coverage(reference_keywords, hypothesis_words)       [0, 100]
completion_percentage = min(hypothesis_word_count / reference_word_count, 1) * 100   [0, 100]
overall_score         = 0.6 * semantic_similarity
                      + 0.25 * keyword_coverage
                      + 0.15 * completion_percentage                (clamped to [0, 100])
```

Weights live in `app/ai/communication/config.py`
(`SEMANTIC_SIMILARITY_WEIGHT`, `KEYWORD_COVERAGE_WEIGHT`,
`LISTEN_COMPLETION_WEIGHT`) as module constants, not `Settings` fields — same
rationale as Read Aloud's `WORD_ACCURACY_WEIGHT`/`COMPLETION_WEIGHT`: they
define the scoring algorithm itself, not an environment-specific knob.

- **`semantic_similarity`** is weighted highest (0.6) because paraphrasing —
  not verbatim repetition — is the entire point of the exercise. This is the
  metric that correctly rewards a candidate who says "a fast brown fox
  leaps over a lazy dog" for the original "the quick brown fox jumps over
  the lazy dog," even though not one content word literally matches.
- **`keyword_coverage`** (0.25) checks that the specific concepts in the
  original sentence survived the paraphrase, not just its general vibe —
  catches a fluent-sounding but off-topic response that a pure embedding
  similarity might still score generously.
- **`completion_percentage`** (0.15, lowest weight) is a **length** signal —
  `min(response_words / original_words, 1) * 100` — not a positional-alignment
  signal like Read Aloud's. A valid paraphrase can legitimately be shorter or
  longer than the original, so this only guards against a response that's
  suspiciously truncated relative to what was asked (e.g. "innovation
  matters" in reply to a full sentence), rather than penalizing rewording.

### Degenerate cases (never raise)

| Input | Behavior |
|---|---|
| Empty transcript | `semantic_similarity = 0.0` (embedding call skipped — see §4), `keyword_coverage = 0.0` (no hypothesis words to match), `completion_percentage = 0.0`, `overall_score = 0.0`. |
| Empty original sentence | `reference_word_count = 0` → `completion_percentage = 0.0`; `extract_keywords("") = []` → `keyword_coverage = 0.0`; `semantic_similarity = 0.0` (guard). |
| Response longer than the original | `completion_percentage` is capped at `100.0`, never exceeds it. |

`duration_seconds < 0` is the one case treated as an actual error
(`InvalidDurationError`, raised by `ListenRepeatAnalysisService.analyze`,
classified as permanent/non-retryable by the Celery task) — identical
handling to Read Aloud. `duration_seconds` is otherwise accepted for
interface parity with `ReadAloudAnalyzer`/`AssessmentAnalysisService` (and to
leave room for a future speaking-rate metric) but does not currently factor
into any Listen & Repeat metric: unlike Read Aloud, there is no fixed word
count to divide by duration, since a valid paraphrase can be any length.

---

## 6. Celery flow (`app/workers/communication_analysis.py`)

`analyze_listen_repeat` mirrors `analyze_read_aloud`'s exact 3-phase shape
and retry policy:

1. **Phase 1** (DB transaction) — fetch the `AssessmentTranscript`. If
   missing or not yet `COMPLETED`, return silently. Idempotently
   create-or-fetch the `AssessmentAnalysis` row via
   `service.create_pending(transcript_id, org_id,
   analysis_type=AnalysisType.LISTEN_REPEAT)`. Skip if already `COMPLETED`.
2. **Phase 2** (no DB) —
   `ListenRepeatAnalysisService.analyze(get_listen_repeat_reference_sentence(),
   transcript_text, duration_seconds)`. The one local-model call (embedding
   two short strings) happens here; still fast enough not to need
   `asyncio.to_thread` at this scale, same call shape Read Aloud uses for its
   pure-CPU comparison.
3. **Phase 3** (DB transaction) —
   `service.complete_listen_repeat_processing(...)`, persisting
   `overall_score`, `semantic_similarity`, `keyword_coverage`,
   `completion_percentage`, and the full `ListenRepeatMetrics` (including
   matched/missing keyword lists and word counts) into `analysis_json`.
   Marks `COMPLETED`, commits.

`_mark_failed` is **reused unchanged** from Read Aloud — it already looks up
`AssessmentAnalysis` by `transcript_id` alone, with no `analysis_type`
branching, so no new failure-path code was needed.

### Dispatch (`app/workers/speech_transcription.py`)

Phase 5 of `_run_transcribe_recording` now branches on `recording_type`:

```python
if recording_type == RecordingType.READ_ALOUD:
    dispatch_analysis(str(transcript_id), duration_seconds)
elif recording_type == RecordingType.LISTEN_REPEAT:
    dispatch_listen_repeat_analysis(str(transcript_id), duration_seconds)
```

Both dispatchers are injectable (`_analysis_dispatcher` /
`_listen_repeat_analysis_dispatcher`) for testability, same pattern as
before. The transcription task never waits on analysis — both are
fire-and-forget `.delay()` calls, exactly like `resume_parser`'s
embedding-generation dispatch.

---

## 7. Retry strategy

Identical to Read Aloud: `InvalidDurationError` is permanent (no retry, task
marked `FAILURE`); any other exception is treated as a transient DB hiccup
(there's no external service call in either pipeline to fail transiently
other than the local embedding model, which either works or the process has
a bug) and retried up to 3 times with `30 * 2**retries` second backoff (30s,
60s, 120s).

---

## 8. API

```
GET /api/v1/assessment/analysis/{transcript_id}
```

**No changes required.** The endpoint and `AssessmentAnalysisResponse`
schema were already `analysis_type`-agnostic — they read/serialize whatever
row exists for a transcript. The response schema gained two new optional
fields (`semantic_similarity`, `keyword_coverage`) so both analysis types'
metrics round-trip through the same payload shape; a `READ_ALOUD` row simply
returns `null` for both, and a `LISTEN_REPEAT` row returns `null` for the
Read-Aloud-specific fields (`word_accuracy`, `reading_speed_wpm`, etc.).

---

## 9. The Listen & Repeat reference sentence

Same situation as Read Aloud: there is no per-campaign assessment-content
model, so the frontend shows every candidate the same hardcoded sentence
(`frontend/src/features/candidate-runner/mock-data.ts::listenRepeatSentence`,
"Innovation distinguishes between a leader and a follower in every industry
we serve."). This sprint mirrors that exact string on the backend as
`Settings.LISTEN_REPEAT_REFERENCE_SENTENCE` (`app/core/config.py`), read via
`app.ai.communication.config.get_listen_repeat_reference_sentence()`. When a
future sprint adds per-campaign content, that getter is the one place that
needs to change.

---

## 10. Explicitly deferred

No aptitude scoring, no recruiter dashboard, no analysis-trigger API
endpoint, no per-campaign reference sentence, no pronunciation/fluency
scoring, no LLM calls anywhere in this pipeline. This sprint's only
deliverable is: completed Listen & Repeat transcript → automatic
deterministic semantic scoring → retrievable via the existing read-only
endpoint.

---

## 11. Future multilingual compatibility

Both new AI-layer modules are already language-agnostic in shape, though the
current reference sentence and stopword list are English-only:

- **`semantic_similarity.py`** depends entirely on whichever
  `sentence-transformers` model `LOCAL_EMBEDDING_MODEL` resolves to
  (`app/core/config.py`). Swapping in a multilingual model (e.g.
  `paraphrase-multilingual-mpnet-base-v2`) requires no code change here —
  `get_model()` is already the single point of model configuration, shared
  with resume/JD matching. Cross-lingual comparison (reference sentence in
  one language, response in another) would work out of the box with a
  multilingual model, since cosine similarity doesn't care which language
  produced either embedding.
- **`keyword_extraction.py`** is the one English-coupled piece: `_STOPWORDS`
  is a fixed English word list, and `normalize_text` (reused from
  `comparison.py`) assumes whitespace-delimited tokenization, which doesn't
  hold for languages like Chinese or Japanese. A future multilingual sprint
  would need a per-language (or language-detected) stopword set and
  tokenizer here — `extract_keywords`/`keyword_coverage`'s signatures
  (`list[str] -> list[str]` / `(list[str], list[str]) -> tuple`) wouldn't
  need to change, only their internals.
- **`ListenRepeatAnalyzer`** itself has no language-specific logic at all —
  it only orchestrates the two modules above and applies the (language-
  independent) scoring weights — so it needs no changes either way.

---

## 12. Testing

- `backend/tests/test_communication_keyword_extraction.py` —
  `extract_keywords` (stopword filtering, case/punctuation insensitivity,
  deduplication, empty/stopword-only input) and `keyword_coverage` (full,
  partial, order-independent, empty-reference, empty-hypothesis cases).
- `backend/tests/test_communication_semantic_similarity.py` —
  `semantic_similarity_score` with `get_model` patched (never loads the real
  model): identical/orthogonal/opposite embedding vectors produce
  100/50/0, and both texts are encoded in a single batched `model.encode`
  call.
- `backend/tests/test_listen_repeat_analyzer.py` — `ListenRepeatAnalyzer`
  end-to-end with `semantic_similarity_score` patched to isolate the
  analyzer's own arithmetic: close paraphrase with full keyword coverage,
  synonym paraphrase with partial keyword coverage (paraphrased sentences /
  synonyms edge case), short response (low completion), empty transcript and
  empty original sentence (both score `0.0` without calling the embedding
  model), perfect repeat (100 across the board), and response-longer-than-
  original (completion capped at 100). Plus `ListenRepeatAnalysisService`
  (delegates to the analyzer, rejects negative duration, accepts zero
  duration).
- `backend/tests/test_assessment_analysis_service.py` — extended with
  `create_pending(..., analysis_type=AnalysisType.LISTEN_REPEAT)` and
  `complete_listen_repeat_processing` (persists metrics, missing-row raises).
- `backend/tests/test_communication_analysis_worker.py` — extended with
  `_run_analyze_listen_repeat` (happy path, transcript-not-found,
  transcript-not-COMPLETED, already-analyzed idempotent skip) and
  `_analyze_listen_repeat_task`'s permanent-vs-transient error
  classification/backoff, mirroring the Read Aloud worker test structure.
- `backend/tests/test_speech_transcription_worker.py` — the prior
  "LISTEN_REPEAT does not dispatch analysis" test is replaced with one
  asserting `analyze_listen_repeat` **is** dispatched with `(transcript_id,
  duration_seconds)`, while the Read Aloud dispatcher is confirmed **not**
  called for that recording.
- `backend/tests/test_assessment_analysis.py` — extended with a test
  asserting a completed `LISTEN_REPEAT` analysis round-trips
  `semantic_similarity`/`keyword_coverage` through the API response while
  Read-Aloud-only fields (`word_accuracy`, etc.) remain `null`.

Verified before completion: `ruff check` clean and the full `pytest tests
--ignore=tests/integration` suite passes with no regressions.
