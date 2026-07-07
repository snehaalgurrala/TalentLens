# TalentLens — Phase 5, Sprint 5.4, Prompt 9
# Read Aloud Analysis Engine

Status: Implemented. Every completed Read Aloud transcript is now
automatically scored against a fixed reference sentence with a deterministic,
LLM-free text-comparison engine — off the request path, same as
transcription itself. No Listen & Repeat analysis, no aptitude scoring, no
recruiter dashboard; this prompt only wires Read Aloud scoring end-to-end and
makes it retrievable.

```
Recording → Whisper → AssessmentTranscript (COMPLETED, READ_ALOUD only)
                              │
                              ▼
                        Celery Queue
                              │
                              ▼
                 ReadAloudAnalysisService (app.ai.communication)
                    │                    │
              comparison.py        metrics.py
                    │                    │
                    └────────┬───────────┘
                              ▼
                      AssessmentAnalysis
                              │
                              ▼
             GET /assessment/analysis/{transcript_id}
```

---

## 1. Architecture

```
backend/app/
├── ai/communication/
│   ├── config.py                 # reference sentence + scoring weights
│   ├── exceptions.py             # CommunicationAnalysisError, InvalidDurationError
│   ├── schemas.py                # WordComparisonResult, ReadAloudMetrics, ReadAloudAnalysisResult
│   ├── comparison.py             # normalize_text, compare_words (difflib alignment)
│   ├── metrics.py                # calculate_metrics — the scoring formula
│   ├── read_aloud_analyzer.py    # ReadAloudAnalyzer — sentence+transcript+duration -> result
│   └── analysis_service.py       # ReadAloudAnalysisService — facade, validates duration
├── models/assessment_analysis.py # AssessmentAnalysis, AnalysisType, AnalysisStatus
├── repositories/assessment_analysis.py
├── services/assessment_analysis.py   # create/complete/fail/get/retry — no AI imports
├── workers/communication_analysis.py # analyze_read_aloud Celery task
├── schemas/assessment_analysis.py    # AssessmentAnalysisResponse
└── api/v1/endpoints/
    └── assessment_analysis.py    # GET /assessment/analysis/{transcript_id}
```

This is a structural copy of the transcription pipeline
(`docs/phase5-sprint5.3-prompt8-async-transcription.md`) applied to scoring
instead of speech-to-text, with one addition: an AI *engine* module
(`app/ai/communication/`) that is pure Python — no database, no Celery, no
network calls, no LLM.

### Layering rules preserved

- **Routers never touch AI or Celery internals directly.** The read endpoint
  (`assessment_analysis.py`) only calls `AssessmentAnalysisService.get_analysis`.
- **Services never import AI schemas or Celery tasks at module scope.**
  `AssessmentAnalysisService.complete_processing` takes plain scalar kwargs
  (score, counts, wpm, a raw `dict` for `analysis_json`) rather than the AI
  layer's `ReadAloudAnalysisResult` object — exactly how
  `AssessmentTranscriptService.complete_processing` takes flat kwargs instead
  of a `TranscriptionResult`. Only the Celery worker glues AI-layer output to
  service-layer kwargs. Its one exception, `retry_failed()`, lazily imports
  the Celery task inside `_default_dispatcher`, never at import time.
- **Only `app/workers/communication_analysis.py` calls `ReadAloudAnalysisService`.**
  No other module imports `app.ai.communication.*`.
- **No LLM calls anywhere in this pipeline.** Comparison is `difflib`-based
  sequence alignment; scoring is arithmetic. Same transcript + same reference
  sentence always produces the same analysis.

---

## 2. Entity: `AssessmentAnalysis`

Kept **separate** from `AssessmentTranscript`, which continues to store the
raw transcription result only (`app/models/assessment_transcript.py` is
unchanged).

| Column | Type | Notes |
|---|---|---|
| `id` | `Uuid`, PK | |
| `organization_id` | `Uuid`, FK → `organizations.id` | Denormalized from the transcript at creation time, same rationale as `AssessmentTranscript.organization_id`. |
| `transcript_id` | `Uuid`, FK → `assessment_transcripts.id`, **unique** | One analysis per transcript. |
| `analysis_type` | `Enum(AnalysisType)` | `READ_ALOUD` only this sprint — the column exists so `LISTEN_REPEAT`/pronunciation analyses can share this table later without a new migration. |
| `status` | `Enum(AnalysisStatus)` | `PENDING` → `COMPLETED` \| `FAILED`. No `PROCESSING` state — unlike Whisper, analysis has no long-running external call to distinguish "queued" from "running." |
| `overall_score` | `Float`, nullable | 0–100, see §4 |
| `word_accuracy` | `Float`, nullable | 0–100 |
| `correct_words` / `missing_words` / `extra_words` / `substituted_words` / `total_words` | `Integer`, nullable | Aggregate counts from the comparison |
| `reading_speed_wpm` | `Float`, nullable | |
| `completion_percentage` | `Float`, nullable | 0–100, see §4 |
| `analysis_json` | `JSONB`, nullable | The full `WordComparisonResult` — correct/missing/extra word lists and substitution pairs. Metrics are already columns, so only the per-word detail is duplicated here. |
| `error_message` | `String(1000)`, nullable | Set on `FAILED`, truncated to 1000 chars |
| `created_at` / `updated_at` | `DateTime(timezone=True)` | |

Migration: `alembic/versions/d2e3f4a5b6c7_create_assessment_analyses.py`
(`down_revision = "c1d2e3f4a5b6"`). Follows the project's established Enum +
`create_table` rule exactly: both `analysistype` and `analysisstatus` enums
are passed directly into their column definitions and **never** `.create()`-d
separately.

---

## 3. Comparison engine (`app/ai/communication/comparison.py`)

Deterministic, case-insensitive, punctuation-insensitive word-level
alignment — no fuzzy or semantic matching.

1. **`normalize_text(text)`** — lowercase, strip all non-word/non-whitespace
   characters (punctuation), collapse whitespace, split into a word list.
   Empty/whitespace-only input normalizes to `[]`.
2. **`compare_words(reference_words, hypothesis_words)`** — aligns the two
   word lists with `difflib.SequenceMatcher` (`autojunk=False`), which
   matches by **position**, not by set membership. This matters for repeated
   words: dropping one "the" out of "the the the dog" is reported as exactly
   one missing word, not silently absorbed by an earlier duplicate the way a
   bag-of-words diff would.

   | Opcode | Meaning |
   |---|---|
   | `equal` | correct words |
   | `delete` | missing words (in reference, not in hypothesis) |
   | `insert` | extra words (in hypothesis, not in reference) |
   | `replace` | paired position-by-position into substitutions; any length mismatch within the block spills into missing/extra |

---

## 4. Metrics & scoring formula (`app/ai/communication/metrics.py`)

```
word_accuracy         = correct_words / total_words * 100
completion_percentage = min(correct_words + substituted_words, total_words) / total_words * 100
reading_speed_wpm     = hypothesis_word_count / (duration_seconds / 60)
overall_score         = 0.7 * word_accuracy + 0.3 * completion_percentage   (clamped to [0, 100])
```

- **`word_accuracy`** rewards only exact matches at the correct position.
- **`completion_percentage`** additionally credits substituted words — a
  position where the candidate attempted a word, even the wrong one — to
  separate "read the whole sentence with some mistakes" from "stopped
  partway through." These are different reading behaviors that
  `word_accuracy` alone can't distinguish.
- **`overall_score`** weights correctness above completion (70/30) — reading
  the whole sentence badly should not outscore reading most of it
  correctly. Weights live as constants in `app/ai/communication/config.py`
  (`WORD_ACCURACY_WEIGHT`, `COMPLETION_WEIGHT`), not `Settings`, since they
  define the algorithm rather than an environment-specific knob.

### Degenerate cases (never raise)

| Input | Behavior |
|---|---|
| `total_words == 0` (empty reference sentence) | `word_accuracy` and `completion_percentage` both `0.0` — there's no meaningful signal to compute, but a malformed reference should never crash the pipeline. |
| `duration_seconds <= 0` | `reading_speed_wpm = 0.0`. |
| Empty transcript | Falls out of the comparison naturally: every reference word is `missing`, so `word_accuracy`/`completion_percentage` are `0.0`. |

`duration_seconds < 0` is the one case treated as an actual error
(`InvalidDurationError`, raised by `ReadAloudAnalysisService.analyze`,
classified as permanent/non-retryable by the Celery task) — a negative
duration can only come from a data/upstream bug, not a valid reading
attempt.

---

## 5. Celery flow (`app/workers/communication_analysis.py`)

Three phases (one fewer than transcription's four — there's no external
model call to isolate from the DB transactions):

1. **Phase 1** (DB transaction) — fetch the `AssessmentTranscript` by id. If
   missing, or not yet `COMPLETED`, return silently (nothing to analyze).
   Idempotently create-or-fetch the `AssessmentAnalysis` row
   (`service.create_pending`). If it's already `COMPLETED`, skip everything
   else (safe against a duplicate `.delay()` or a retried task).
2. **Phase 2** (no DB) — `ReadAloudAnalysisService.analyze(reference_sentence,
   transcript_text, duration_seconds)`. Pure CPU, no `asyncio.to_thread`
   needed (unlike Whisper, this never blocks long enough to matter).
3. **Phase 3** (DB transaction) — persist all metrics and the comparison
   detail (`analysis_json`), mark `COMPLETED`, commit.

Registered in `celery_app.py`'s `include=[...]` list alongside the other
four worker modules.

### Dispatch

`app.workers.speech_transcription._run_transcribe_recording` gained a
**Phase 5**: immediately after Phase 4 commits a `COMPLETED` transcript, if
the recording's `recording_type == RecordingType.READ_ALOUD`, it calls
`analyze_read_aloud.delay(str(transcript_id), duration_seconds)`. `LISTEN_REPEAT`
recordings are transcribed exactly as before but never trigger analysis.
`duration_seconds` is passed through from the `AssessmentRecording` row
already in scope in Phase 1 (captured into a local before the session
closes) rather than re-queried by the analysis worker — this keeps
`communication_analysis.py`'s DB access to `AssessmentTranscript` only, per
spec ("Consume only AssessmentTranscript").

The pattern mirrors `resume_parser.py`'s Phase 5 dispatch of
`generate_resume_embedding.delay(...)`: a direct top-level import
(`from app.workers.communication_analysis import analyze_read_aloud`) since
`communication_analysis.py` never imports back into `speech_transcription.py`
— no circular dependency.

---

## 6. Retry strategy

| Failure | Classification | Behavior |
|---|---|---|
| `InvalidDurationError` (negative duration) | Permanent | No retry — logged and re-raised; analysis marked `FAILED` |
| Any other exception (almost always a DB hiccup — analysis has no external service call) | Transient | Retried up to **3** times with exponential backoff: 30 s, 60 s, 120 s (`30 * 2**retries`, same formula as every other worker) |

`_mark_failed` runs in the same coroutine/event loop as the main work (via
`_run_analyze_read_aloud_with_recovery`), never as a second `asyncio.run()`
call — see `celery_app.run_task`'s docstring.

### Manual retry (service-level, no API endpoint)

`AssessmentAnalysisService.retry_failed(transcript_id, user, duration_seconds)`
resets a `FAILED` analysis back to `PENDING` and re-dispatches the Celery
task. Not exposed via an API route this sprint — a service capability only,
exercised directly in `tests/test_assessment_analysis_service.py`.

---

## 7. API

```
GET /api/v1/assessment/analysis/{transcript_id}
```

Read-only. Same RBAC as the transcript endpoint (`RECRUITER`, `ORG_ADMIN`,
`SUPER_ADMIN`). Returns 404 until an analysis row exists for that transcript,
and 404 (not 403) if it belongs to a different organization — same
denormalized-`organization_id` scoping as `AssessmentTranscriptService`.

Response includes status, every metric column, and `analysis_json` (the
correct/missing/extra word lists and substitution pairs) — satisfying "word
lists" and "analysis metadata" from a single payload without inventing a
second endpoint.

No trigger/create endpoint exists — analysis is queued automatically after
transcription completes, per spec.

---

## 8. The Read Aloud reference sentence

There is currently no per-campaign assessment-content model: the frontend
shows every candidate the same hardcoded sentence
(`frontend/src/features/candidate-runner/mock-data.ts::readAloudSentence`,
"The quick brown fox jumps over the lazy dog while carrying a bag of
documents to the office."). This sprint mirrors that exact string on the
backend as `Settings.READ_ALOUD_REFERENCE_SENTENCE`
(`app/core/config.py`), read via
`app.ai.communication.config.get_read_aloud_reference_sentence()`, rather
than inventing a content-management system out of scope for a scoring-engine
sprint. When a future sprint adds per-campaign Read Aloud content, that
getter is the one place that needs to change to resolve a session-specific
sentence instead of the global default.

---

## 9. Explicitly deferred

No Listen & Repeat analysis, no pronunciation/fluency scoring, no aptitude
scoring, no recruiter dashboard, no LLM calls anywhere in this pipeline, no
per-campaign reference sentence, no analysis-trigger API endpoint. This
sprint's only deliverable is: completed Read Aloud transcript → automatic
deterministic scoring → retrievable read-only result.

---

## 10. Future WhisperX / pronunciation compatibility

`ReadAloudAnalyzer`/`ReadAloudAnalysisService` only depend on plain strings
(`original_sentence`, `transcript`) and a duration — they have no coupling to
how the transcript was produced. Swapping Whisper for WhisperX (word-level
timestamps) would require no changes here. A future pronunciation-analysis
engine can live alongside `ReadAloudAnalyzer` in
`app/ai/communication/`, reusing `comparison.py`'s word alignment and
`AssessmentAnalysis.analysis_json` for its own structured detail, without
touching this sprint's Read Aloud scoring path.

---

## 11. Testing

- `backend/tests/test_communication_comparison.py` — `normalize_text`
  (punctuation, capitalization, whitespace, empty string) and `compare_words`
  (identical sentences, missing/extra/substituted words, repeated words,
  empty reference, empty hypothesis, uneven replace-block lengths).
- `backend/tests/test_communication_metrics.py` — `calculate_metrics`
  (perfect reading, partial accuracy, completion vs. accuracy distinction,
  empty transcript, empty reference sentence, zero duration, WPM formula,
  weighted overall score).
- `backend/tests/test_read_aloud_analyzer.py` — `ReadAloudAnalyzer` end-to-end
  (perfect reading, case/punctuation insensitivity, empty transcript, empty
  sentence, repeated words) and `ReadAloudAnalysisService` (delegates to the
  analyzer, rejects negative duration, accepts zero duration).
- `backend/tests/test_assessment_analysis_service.py` — repository mocked,
  exercises `create_pending` (idempotent), `complete_processing`,
  `fail_processing` (incl. 1000-char truncation and missing-row no-op),
  `get_analysis` (org scoping, 404s), and `retry_failed`.
- `backend/tests/test_communication_analysis_worker.py` — mirrors
  `test_speech_transcription_worker.py`'s structure: every collaborator is
  patched, `ReadAloudAnalysisService` is injected via `_analysis_service`,
  covering the happy path, transcript-not-found, transcript-not-COMPLETED,
  already-analyzed idempotent skip, `_mark_failed`, and the Celery task's
  permanent-vs-transient error classification/backoff math.
- `backend/tests/test_speech_transcription_worker.py` — extended with a test
  asserting `analyze_read_aloud` is dispatched with `(transcript_id,
  duration_seconds)` after a READ_ALOUD recording's transcription completes,
  and a test asserting it is **not** dispatched for a LISTEN_REPEAT recording.
- `backend/tests/test_assessment_analysis.py` — API tests for the read
  endpoint (`AssessmentAnalysisService` mocked via dependency override),
  covering completed/pending payload shapes, 404, and RBAC (`CANDIDATE`
  forbidden).
- `backend/tests/integration/test_assessment_analysis_integration.py` —
  real-Postgres tests (same disposable-database caveat as every other file
  under `tests/integration/`): exercises `AssessmentAnalysisRepository`
  directly, and runs `_run_analyze_read_aloud`'s full async body against a
  real database — no model to fake here, analysis is pure deterministic text
  processing.

Verified before completion: `ruff check` clean and the full `pytest tests
--ignore=tests/integration` suite passes with no regressions.
