# TalentLens — Phase 5, Sprint 5.3, Prompt 7
# Speech AI Foundation (Local Whisper)

Status: Implemented (new `app/ai/speech/` module, unit tests, docs). No
Celery integration, no database tables, no `AssessmentSession` wiring, no
communication/pronunciation scoring, no recruiter-facing surface. This
prompt only builds the reusable primitive:

```
Audio bytes → SpeechService.transcribe() → Transcript + language + metadata
```

A future sprint decides how (and whether) transcripts get persisted against
an `AssessmentRecording` and surfaced to recruiters.

---

## 1. Architecture

```
backend/app/ai/
├── __init__.py
└── speech/
    ├── __init__.py          # empty — matches app/services, app/schemas convention
    ├── config.py            # thin wrapper over app.core.config.settings + mime-type table
    ├── exceptions.py         # SpeechAIError, AudioValidationError, ModelLoadError, TranscriptionError
    ├── schemas.py             # TranscriptSegment, TranscriptionResult (plain Pydantic models)
    ├── transcription.py       # validate_audio(), staged_audio_file() — pure, no Whisper import
    ├── whisper_service.py     # WhisperService + module-level model singleton (get_model/_load_model)
    └── speech_service.py      # SpeechService — the public entry point
```

This is a new top-level `app/ai/` namespace (none existed before). Everything
AI-model-related for speech lives under it, mirroring how
`app/services/local_embedding_service.py` is the existing precedent for "a
local ML model wrapped in a service" — Whisper's module-level singleton
(`get_model` / `_load_model` / `reset_model_cache`) is a deliberate structural
copy of that file's pattern, not a new design.

### Why a dedicated `app/ai/` module instead of `app/services/`

The prompt for this sprint explicitly calls for AI code to live in its own
module, separate from the Service layer that talks to repositories and the
database. `SpeechService` and `WhisperService` know nothing about
`AssessmentSession`, `AssessmentRecording`, or any repository — they take raw
bytes in and return a structured result out. A future integration point
(e.g. a Celery worker, following the existing `app/workers/*.py` pattern)
will own fetching bytes via `StorageBackend.load(recording.storage_path)`
and persisting the result; that plumbing does not exist yet.

### Layering

- **`transcription.py`** — pure validation and temp-file staging. No
  Whisper import at all, so it's trivially unit-testable and reusable if the
  underlying STT engine is ever swapped.
- **`whisper_service.py`** — the *only* file that imports `whisper`. Nothing
  else in the codebase should `import whisper` directly. Returns Whisper's
  own plain result `dict` (not Whisper's internal types), so callers never
  need to know Whisper's API.
- **`speech_service.py`** — orchestrates validate → stage → transcribe →
  build `TranscriptionResult`. This is the one function a future worker or
  endpoint calls: `SpeechService().transcribe(data, mime_type=..., filename=...)`.

---

## 2. Installation

### Python package

Added to `backend/requirements.txt`:

```
openai-whisper==20250625
```

This is the **local, open-source** `openai-whisper` PyPI package (runs
entirely on-device), not the hosted OpenAI Whisper API — no network calls
happen during transcription. It pulls in `torch`, `numpy`, and `tiktoken` as
dependencies; `torch` and `numpy` are already present transitively via
`sentence-transformers` (used by `local_embedding_service.py`), so no new
heavy dependency conflict is introduced.

### FFmpeg (system binary, not a pip package)

`openai-whisper` shells out to the **`ffmpeg` command-line binary** to
decode arbitrary audio containers (webm/ogg/wav/mp3/m4a) into raw PCM before
feeding it to the model. This is a system dependency, not something `pip
install` provides.

- **Docker**: added to `backend/Dockerfile`'s existing `apt-get install`
  step alongside `gcc`/`curl`:
  ```dockerfile
  RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      curl \
      ffmpeg \
      && rm -rf /var/lib/apt/lists/*
  ```
- **Local dev (Windows)**: install via `winget install ffmpeg` or
  `choco install ffmpeg`, then ensure `ffmpeg.exe` is on `PATH`.
- **Local dev (macOS/Linux)**: `brew install ffmpeg` / `apt install ffmpeg`.

Without `ffmpeg` on `PATH`, `WhisperService.transcribe()` raises
`TranscriptionError` (audio load/decode failure), not a crash — the
temp-file path is still cleaned up by `staged_audio_file`'s `finally` block.

### Model download and cache location

`whisper.load_model(name, ...)` downloads the requested model checkpoint
from OpenAI's public CDN **on first use only** and caches it on disk;
every subsequent call reuses the cached file with no network access.

- Default cache location: `~/.cache/whisper` (matches `openai-whisper`'s own
  default `download_root`).
- Override via `WHISPER_MODEL_CACHE_DIR` (see §3) to point at a
  container-persistent volume in production, so the model isn't re-downloaded
  on every container restart.

---

## 3. Configuration

All Speech AI settings are flat fields on the existing global
`Settings` class (`app/core/config.py`) — no nested/sub-namespace settings
model, matching every other subsystem (`LOCAL_EMBEDDING_*`, `ZIP_MAX_*`, etc.):

```python
# ── Speech AI — local Whisper transcription (no external API calls) ──
WHISPER_MODEL_NAME: str = "base"
WHISPER_DEVICE: str = "cpu"
WHISPER_MODEL_CACHE_DIR: str | None = None
WHISPER_MAX_AUDIO_SIZE_MB: int = 25
```

`app/ai/speech/config.py` wraps these behind small accessor functions
(`get_model_name()`, `get_device()`, `get_cache_dir()`,
`get_max_audio_size_bytes()`) plus the module-local
`ALLOWED_AUDIO_MIME_TYPES` mime-type → extension table. Switching from
`base` to `tiny`/`small`/`medium`/`large` is a config change
(`WHISPER_MODEL_NAME` env var) — **no code change** required; the next
`get_model()` call with a different name transparently loads and caches the
new model (see §5).

---

## 4. `SpeechService` / `WhisperService`

```python
from app.ai.speech import SpeechService

result = await SpeechService().transcribe(
    audio_bytes, mime_type="audio/webm", filename="reading.webm"
)
result.transcript             # str
result.language                # str, e.g. "en"
result.duration_seconds         # float — end timestamp of the last segment
result.processing_time_seconds  # float — wall-clock time spent in Whisper
result.model_name               # str, e.g. "base"
result.confidence               # float | None — see note below
result.segments                 # list[TranscriptSegment]
```

`SpeechService.transcribe()`:
1. `validate_audio()` — rejects missing data, unsupported mime types, and
   oversized files (`WHISPER_MAX_AUDIO_SIZE_MB`, default 25 MB) before any
   Whisper call.
2. `staged_audio_file()` — writes the validated bytes to a temp file with
   the correct extension (so ffmpeg can sniff the container), yielded via a
   context manager that always removes the file afterward.
3. `WhisperService.transcribe(path)` — runs the (blocking, CPU/GPU-bound)
   Whisper call via `asyncio.to_thread`, so it never blocks the event loop.
4. Builds `TranscriptionResult` from Whisper's raw `{text, language,
   segments}` dict.

Supported input mime types (`ALLOWED_AUDIO_MIME_TYPES` in `config.py`):
`audio/webm`, `audio/ogg`, `audio/wav`, `audio/x-wav`, `audio/mpeg`,
`audio/mp4`, `audio/x-m4a` — a superset of the two types the existing
candidate-recording upload pipeline already produces
(`audio/webm` / `audio/ogg`, see
`docs/phase5-sprint5.2-prompt6-assessment-recording-upload.md`).

**Confidence note**: Whisper does not expose a single calibrated 0–1
confidence score. Each segment carries `avg_logprob` (average
log-probability per token); `_segment_confidence()` rescales it via
`exp(avg_logprob)` as a common approximate-confidence heuristic, and the
top-level `confidence` is the mean of per-segment confidences. This is an
approximation, not a calibrated probability — documented here so a future
sprint doesn't mistake it for one.

### Failure modes → exceptions

| Condition                                   | Exception              |
|----------------------------------------------|-------------------------|
| No audio bytes / empty file                   | `AudioValidationError` |
| Unsupported or missing mime type              | `AudioValidationError` |
| File exceeds `WHISPER_MAX_AUDIO_SIZE_MB`      | `AudioValidationError` |
| Model checkpoint can't be loaded/downloaded   | `ModelLoadError`       |
| Whisper/ffmpeg fails on a validly-typed file (corrupted/unreadable audio) | `TranscriptionError` |

All four inherit from `SpeechAIError` (`app/ai/speech/exceptions.py`),
following the existing project convention of small, module-local exception
classes (e.g. `ExtractionError` in `resume_extraction.py`, `ModelLoadError`
in `local_embedding_service.py`) rather than a shared
`app/core/exceptions.py` — none exists in this codebase.

---

## 5. Model lifecycle

Mirrors `local_embedding_service.py`'s model-loading pattern exactly:

- `get_model(model_name, device)` is a thread-safe, process-wide singleton
  keyed by model name (`whisper_service.py`). The first call loads and
  caches the model; every subsequent call with the same name returns the
  cached instance — **the model loads at most once per process, never
  per-request.**
- Calling with a *different* `model_name` (e.g. switching `base` → `small`
  at runtime) reloads and replaces the cached model.
- `reset_model_cache()` is a test-only hook to force the next `get_model()`
  call to reload — used by `tests/test_speech_service.py` to isolate tests
  from each other's cached state.
- No FastAPI startup preload hook was added this sprint (unlike
  `local_embedding_service.preload_model()`) — there is no endpoint calling
  `SpeechService` yet, so there's nothing to warm on startup. A future
  sprint wiring this into a worker or endpoint should add an equivalent
  `preload_model()` call to `app/main.py`'s lifespan, following that
  existing precedent.

### Logging

Every stage logs through the standard `logging.getLogger(__name__)` +
`extra={...}` convention (`app/core/logging.py`'s JSON formatter):
model loading start/success/failure, transcription start/finish with
elapsed seconds, and a final "Transcription complete" summary in
`speech_service.py`. (One gotcha worth flagging: `filename` is a **reserved**
`LogRecord` attribute — passing it through `extra` collides with Python's
own `logging` internals and raises `KeyError: "Attempt to overwrite
'filename'"` once any handler is configured. The audio's filename is logged
as `extra={"audio_filename": ...}` instead.)

---

## 6. Future compatibility

- **Model size**: switching `tiny`/`base`/`small`/`medium`/`large` is a
  `WHISPER_MODEL_NAME` config change only.
- **Device**: `WHISPER_DEVICE` (`"cpu"` default) can be set to `"cuda"` on a
  GPU-enabled host with no code change.
- **Persistence**: `TranscriptionResult` is a plain Pydantic model, ready to
  be mapped onto a future `Transcript` ORM model / repository once that
  sprint is scoped — this module deliberately does not create one.
- **Celery integration**: not part of this sprint. A future worker would
  follow the exact structural template in
  `app/workers/embedding_worker.py` / `resume_parser.py` (phase-based DB
  transactions, retry classification, `run_task()` sync entry point) and
  call `SpeechService().transcribe(...)` as the CPU-bound step in Phase 2,
  the same way `embedding_worker.py` calls `LocalEmbeddingService`.

---

## 7. Explicitly deferred

No communication scoring, no pronunciation scoring, no semantic similarity,
no recruiter reports, no AI evaluation, no Celery task, no database table,
no `AssessmentSession`/`AssessmentRecording` wiring, no API endpoint. This
sprint's only deliverable is `SpeechService.transcribe()` being callable and
correct in isolation.

---

## 8. Testing

`backend/tests/test_speech_service.py` (flat under `tests/`, **not**
`tests/integration/` — this module makes no database calls, so there's
nothing for the integration-DB-truncation caveat in
`tests/integration/conftest.py` to apply to). 22 tests, all Whisper model
loading mocked at the `_load_model` boundary (same approach as
`test_local_embedding_service.py` — no real model download, no GPU, no
`ffmpeg` dependency at test time):

- Audio validation: missing/empty data, unsupported mime type, oversized
  file, codec-suffix stripping, mime normalization.
- Temp-file staging: correct extension per mime type, cleanup after use.
- Model singleton: loads once and reuses, reloads on model-name change,
  load failure raises `ModelLoadError`.
- `WhisperService.transcribe()`: happy path, corrupted-audio → `TranscriptionError`, model-load failure propagates.
- `SpeechService.transcribe()`: validation short-circuits before touching
  Whisper, structured-result construction (transcript/language/duration/
  confidence/segments), no-segments edge case, corrupted-audio and
  model-load-failure propagation, default `WhisperService` construction.

Verified before completion: `ruff check` clean, `mypy` clean (`strict =
false`, `ignore_missing_imports = true` per `pyproject.toml`), full
`pytest tests --ignore=tests/integration` suite (620 tests) passes with no
regressions.
