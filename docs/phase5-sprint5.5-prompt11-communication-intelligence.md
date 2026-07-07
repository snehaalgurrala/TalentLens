# TalentLens — Phase 5, Sprint 5.5, Prompt 11
# Communication Intelligence Engine

Combines the already-completed Read Aloud and Listen & Repeat
`AssessmentAnalysis` results for one `AssessmentSession` into a single
recruiter-facing `CommunicationAssessment`. This is a pure aggregation layer:
it does not re-run Whisper, does not re-run embeddings, and does not call an
LLM anywhere — every score, strength, improvement, and summary sentence is a
deterministic function of the two existing analysis rows.

```
Recording
    │
    ▼
Transcript  (Whisper — Sprint 5.3)
    │
    ├──────────────┬───────────────────┐
    ▼              ▼                   │
Read Analysis  Listen Analysis         │  (Sprint 5.4 — deterministic
    │              │                   │   text/embedding comparison)
    └──────┬───────┘                   │
           ▼                           │
  CommunicationAssessment  ◄───────────┘  (this sprint — deterministic
           │                               aggregation + rule engine)
           ▼
   Recruiter API (GET, read-only)
```

Structural sibling of
[prompt9](phase5-sprint5.4-prompt9-read-aloud-analysis.md) /
[prompt10](phase5-sprint5.4-prompt10-listen-repeat-analysis.md): same
Model → Repository → Service → Celery task → API layering, same
PENDING/COMPLETED/FAILED lifecycle, same idempotency-by-status-check pattern.

## 1. Architecture

| Layer | File |
|---|---|
| Model | `app/models/communication_assessment.py` |
| Migration | `alembic/versions/f4a5b6c7d8e9_create_communication_assessments.py` |
| Repository | `app/repositories/communication_assessment.py` |
| Service (persistence) | `app/services/communication_assessment.py` |
| Scoring engine (pure) | `app/ai/communication/communication_assessment_engine.py` |
| Rule engine (pure) | `app/ai/communication/assessment_rules.py` |
| Config (weights/thresholds) | `app/ai/communication/config.py` |
| Celery task | `app/workers/communication_assessment.py` |
| API | `app/api/v1/endpoints/communication_assessment.py` |
| Schema | `app/schemas/communication_assessment.py` |

`CommunicationAssessment` is kept separate from `AssessmentAnalysis`: it has
at most one row per **session** (both analysis types feed into it), while
`AssessmentAnalysis` has one row per **transcript**. `organization_id` is
denormalized from `AssessmentSession.org_id`, same rationale as
`AssessmentAnalysis.organization_id` — org-scoped lookups avoid an extra join.

## 2. Entity: `CommunicationAssessment`

```
id, organization_id, assessment_session_id (unique FK -> assessment_sessions),
status (PENDING | COMPLETED | FAILED),
overall_score, reading_score, listening_score, confidence_score,
strengths_json (list[str]), improvements_json (list[str]),
summary_json ({"overview": str}),
error_message, created_at, updated_at
```

## 3. Scoring formula

Both sub-scores are simply the `overall_score` already computed by the Read
Aloud / Listen & Repeat analyzers (each of those already blends its own
metrics — see prompt9/prompt10):

```
reading_score   = ReadAloudAnalysis.overall_score
listening_score = ListenRepeatAnalysis.overall_score
overall_score   = 0.5 * reading_score + 0.5 * listening_score
```

`OVERALL_READ_ALOUD_WEIGHT` / `OVERALL_LISTEN_REPEAT_WEIGHT` (both `0.5`) live
in `config.py`. **Assumption**: equal weighting — there's no product signal
yet that either communication skill matters more for the roles this MVP
targets.

### Confidence score

```
confidence_score = (1/3) * read_aloud.completion_percentage
                  + (1/3) * listen_repeat.completion_percentage
                  + (1/3) * listen_repeat.semantic_similarity
```

Three equally-weighted components, each documented in `config.py`:
- **Reading completion** — how much of the Read Aloud recording the
  candidate actually finished.
- **Listening completion** — same, for Listen & Repeat.
- **Similarity confidence** — semantic similarity doubles as a proxy for how
  trustworthy the Listen & Repeat comparison itself is; a low-similarity
  transcript could mean poor paraphrasing or a noisy comparison — either way,
  confidence should drop.

**Assumption**: equal thirds, no empirical weighting yet.

## 4. Rule engine (`app/ai/communication/assessment_rules.py`)

Pure functions, no DB, no LLM — every rule is a fixed threshold comparison
against a constant in `config.py`.

### Strength detection

| Condition | Strength |
|---|---|
| `word_accuracy > 95` | "Reads clearly and accurately" |
| `semantic_similarity > 90` | "Demonstrates strong listening comprehension" |
| `110 <= reading_speed_wpm <= 160` | "Maintains a comfortable speaking pace" |

### Improvement detection

| Condition | Improvement |
|---|---|
| `word_accuracy < 80` | "Misses important words while reading" |
| `semantic_similarity < 75` | "Could improve listening comprehension" |
| `reading_speed_wpm > 180` | "Speaking pace may be difficult to follow" |
| `reading_speed_wpm < 90` | "Speaking pace is slower than recommended" |

**Assumption**: the bands between the comfortable zone (110–160) and the
too-slow/too-fast bounds (90 / 180) are a deliberate dead zone — neither a
strength nor an improvement fires there, rather than picking an arbitrary
split point. Revisit once real candidate speech-rate data is available.

## 5. Summary generation (`generate_summary`)

Template-based, no AI calls. Driven off the *labels* already produced by
`detect_strengths`/`detect_improvements` (not raw scores), so the summary
sentence can never contradict the strengths/improvements lists:

```
"The candidate demonstrated strong reading accuracy and good listening
comprehension. Minor improvements are recommended in speaking pace."
```

Each improvement message maps to a short recruiter-facing topic
(`reading accuracy` / `listening comprehension` / `speaking pace`); both
pace-related improvements collapse to the single topic "speaking pace" so it
isn't mentioned twice.

## 6. Celery flow (`app/workers/communication_assessment.py`)

`generate_communication_assessment(session_id: str)`:

- **Phase 1** (own transaction) — fetch the `AssessmentSession`; create
  (idempotently) the `CommunicationAssessment` row as `PENDING` as soon as
  the session is known to exist, so recruiters can observe `PENDING` before
  both analyses land. If already `COMPLETED`, skip (this is how duplicate
  processing is avoided — see below). Fetch both sibling
  `AssessmentAnalysis` rows for the session (joined
  `assessment_analyses -> assessment_transcripts -> assessment_recordings`,
  filtered by `session_id`). If either is missing or not yet `COMPLETED`,
  return silently — not an error, just not ready. If either is `FAILED`,
  mark the assessment `FAILED` with a message naming which side failed, and
  stop (retrying can't fix an upstream permanent failure).
- **Phase 2** (no DB) — `CommunicationAssessmentEngine.assess(...)`.
- **Phase 3** (own transaction) — persist scores/strengths/improvements/
  summary, mark `COMPLETED`.

### Dispatch (`app/workers/communication_analysis.py`)

Both `analyze_read_aloud` and `analyze_listen_repeat` fire-and-forget
dispatch `generate_communication_assessment` at the end of their own Phase 3,
resolving the owning `assessment_session_id` via the transcript's
`recording_id -> AssessmentRecording.session_id`. It's expected and safe for
**both** sibling tasks to independently trigger this task — whichever one
finishes second is the one that actually finds both analyses `COMPLETED` and
does the scoring; the other's trigger is a no-op via the "not ready yet"
check.

### Duplicate processing avoidance

1. `CommunicationAssessmentService.create_pending` is idempotent — returns
   the existing row untouched if one already exists for the session.
2. Phase 1 checks `status == COMPLETED` and returns immediately if so.

Combined, this covers the expected case (both siblings dispatching the same
aggregation task). A true concurrent double-computation race — two workers
both passing the `COMPLETED` check in the same instant, before either
commits — is explicitly out of scope for this MVP (see §10); a unique
constraint on `assessment_session_id` at least guarantees only one row can
ever exist, so the worst case is a redundant recomputation, not a duplicate
row.

## 7. Retry strategy

Same shape as every other worker in this codebase: up to 3 retries,
exponential backoff (30s / 60s / 120s), `acks_late=True`,
`reject_on_worker_lost=True`. Unlike `analyze_read_aloud`/
`analyze_listen_repeat`, there is no permanent-error exception class here —
every failure this task can hit beyond "not ready yet" (which isn't an
exception at all) is a DB-layer problem, so every exception is treated as
transient and retried.

## 8. API

```
GET /api/v1/assessment/communication/{session_id}
```

Returns `overall_score`, `reading_score`, `listening_score`,
`confidence_score`, `strengths_json`, `improvements_json`, `summary_json`,
`status`, `error_message`, and timestamps. Same access model and org-scoping
(404 on missing-or-cross-org, 422 if the caller has no `org_id`) as
`assessment_analysis.py` — only `RECRUITER` / `ORG_ADMIN` / `SUPER_ADMIN` may
call it; candidates have no platform account/token yet.

## 9. Explicitly deferred

- No recruiter UI (per the sprint scope) — API only.
- No `retry_failed` API endpoint — `CommunicationAssessmentService.
  retry_failed` exists and is exercised in service tests, but is a manual/
  administrative capability only, same as `AssessmentAnalysisService.
  retry_failed` / `AssessmentTranscriptService.retry_failed`.
- No true concurrency guard against two workers racing past the
  `COMPLETED` idempotency check simultaneously (see §6) — acceptable for
  this MVP's traffic volume; a `SELECT ... FOR UPDATE` or a DB-level
  upsert-on-conflict would close this gap if it becomes a real issue.
- No per-campaign customization of scoring weights or thresholds — all
  constants in `config.py` are global, matching the fixed reference
  sentences from prompt9/prompt10.

## 10. Future LLM enhancement points

The deterministic rule engine (`assessment_rules.py`) and template summary
(`generate_summary`) are intentionally the seam where a future sprint could
swap in an LLM without touching any other layer:

- `generate_summary(strengths, improvements)` could become an LLM call that
  takes the same deterministic strengths/improvements lists as grounding
  context, producing more natural recruiter prose while keeping the
  underlying signals auditable and deterministic.
- `detect_strengths`/`detect_improvements` could be extended with
  LLM-derived qualitative signals (e.g. tone, filler-word usage) alongside
  the existing threshold rules, without changing `CommunicationAssessmentEngine`'s
  contract.
- The confidence-score formula could eventually incorporate an LLM's own
  self-reported confidence in a semantic comparison, as an additional
  weighted component.

## 11. Testing

- `tests/test_communication_assessment_rules.py` — rule engine (strength/
  improvement/summary threshold behavior, boundary values, dead zones).
- `tests/test_communication_assessment_engine.py` — scoring formulas
  (overall/confidence score math, pass-through of reading/listening scores).
- `tests/test_communication_assessment_repository.py` — repository CRUD.
- `tests/test_communication_assessment_service.py` — service persistence/
  idempotency/org-scoping/retry, mirrors `test_assessment_analysis_service.py`.
- `tests/test_communication_assessment_worker.py` — Celery task, including
  the edge cases called out by this sprint: missing analyses (only one or
  neither sibling present), one analysis `FAILED`, and duplicate processing
  (assessment already `COMPLETED`).
- `tests/test_communication_assessment_api.py` — GET endpoint, RBAC.
- `tests/test_communication_analysis_worker.py` — updated for the new
  fire-and-forget dispatch added to `analyze_read_aloud`/
  `analyze_listen_repeat`'s Phase 3.
