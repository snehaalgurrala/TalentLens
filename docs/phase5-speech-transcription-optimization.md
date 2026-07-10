# TalentLens — Speech Transcription Optimization

Status: Implemented. Improves transcript quality feeding the existing
communication-assessment pipeline. No scoring logic changed, no new
external services, everything still runs fully offline on the local Whisper
model already in use.

```
Candidate mic → getUserMedia (constrained) → MediaRecorder
             → upload → Celery worker
             → audio preprocessing (trim + normalize)
             → Whisper ("small", deterministic decode)
             → transcript cleanup (filler words, whitespace)
             → AssessmentTranscript (unchanged schema/consumers)
```

---

## 1. Files modified / added

| File | Change |
|---|---|
| `frontend/src/features/candidate-runner/use-audio-recorder.ts` | `getUserMedia` now requests `echoCancellation`, `noiseSuppression`, `autoGainControl`, `channelCount: 1`, `sampleRate: 16000` instead of bare `audio: true` |
| `backend/app/core/config.py` | `WHISPER_MODEL_NAME` default changed `"base"` → `"small"` (still overridable via env var) |
| `backend/app/ai/speech/whisper_service.py` | `model.transcribe(...)` now passes `language="en"`, `task="transcribe"`, `temperature=0.0`, `beam_size=5`, `best_of=5`, `condition_on_previous_text=False`, `fp16=(device != "cpu")` — previously only the audio path was passed, everything else was Whisper's own default |
| `backend/app/ai/speech/audio_preprocessing.py` | **New.** `preprocess_audio_file()` — trims leading/trailing silence, normalizes peak level, resamples to 16kHz mono, via `pydub` |
| `backend/app/ai/speech/transcript_cleanup.py` | **New.** `clean_transcript()` — collapses whitespace, drops standalone filler words |
| `backend/app/ai/speech/speech_service.py` | Wires preprocessing in before `whisper_service.transcribe()` and cleanup after it |
| `backend/requirements.txt` | Added `pydub==0.25.1` (uses the `ffmpeg` binary already required by Whisper — no new OS dependency) |
| `backend/scripts/benchmark_transcription.py` | **New.** Manual, non-test script used to produce the measurements in §5 |
| `backend/tests/test_audio_preprocessing.py`, `backend/tests/test_transcript_cleanup.py` | **New** test files |
| `backend/tests/test_speech_service.py` | Updated `WhisperService.transcribe` call-argument assertions for the new decoding kwargs |

Nothing in `app/workers/speech_transcription.py`, the `AssessmentTranscript`/`AssessmentAnalysis` schemas, the communication-assessment scoring engine, or any API contract changed — this is purely an input-quality improvement ahead of the existing pipeline, matching the task's constraint not to touch scoring.

---

## 2. Part 1 — Frontend recording constraints

`use-audio-recorder.ts`, `startRecording()`:

```ts
const AUDIO_CONSTRAINTS: MediaTrackConstraints = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  channelCount: 1,
  sampleRate: 16000,
}
...
stream = await navigator.mediaDevices.getUserMedia({ audio: AUDIO_CONSTRAINTS })
```

**Why this helps:** none of these were requested before (`{ audio: true }` only) — the browser/OS default settings for the active input device were used as-is, which vary across laptops/headsets. Echo cancellation and noise suppression remove room echo and steady background noise before the signal is even encoded, and auto gain control keeps quiet speakers from being clipped by silence-adjacent thresholds. `sampleRate: 16000, channelCount: 1` requests audio at the exact rate/channel count Whisper resamples to internally anyway, so the browser (not a lossy intermediate re-encode) does that conversion when possible.

**Why it's safe:** every key here is a bare value (not `{ exact: ... }`), which the [MediaTrackConstraints spec](https://www.w3.org/TR/mediacapture-streams/#dom-mediatrackconstraints) treats as an `ideal` hint. A device or browser that can't honor a given constraint simply gets as close as it can — `getUserMedia` never throws `OverconstrainedError` because of it. No fallback code was needed.

---

## 3. Part 2 — Audio preprocessing

`backend/app/ai/speech/audio_preprocessing.py`, wired into `SpeechService.transcribe()`:

```python
with (
    staged_audio_file(data, normalized_mime) as audio_path,
    preprocess_audio_file(audio_path) as processed_path,
):
    raw = await asyncio.to_thread(self.whisper_service.transcribe, processed_path)
```

`preprocess_audio_file()`:
1. Loads the staged recording via `pydub` (which shells out to the same `ffmpeg` binary Whisper already requires).
2. Resamples to 16kHz mono (`set_frame_rate` / `set_channels`) — matches Whisper's own internal target, so the file handed to Whisper is already in its native format.
3. Trims leading/trailing silence (`pydub.silence.detect_leading_silence`, threshold `-40 dBFS`), guarded by a `_MIN_AUDIO_MS = 200` floor so a near-silent or fully-silent recording is never reduced to (almost) nothing.
4. Normalizes peak level (`pydub.effects.normalize`) — brings the loudest sample up to (near) 0 dBFS without changing the waveform's shape, so quiet recordings aren't sitting closer to the noise floor than they need to be.
5. Exports to a new temp WAV file and yields its path.

**Why it's safe:** the whole function is wrapped in a `try`/`except Exception` that falls back to yielding the *original, untouched* staged file on any failure (corrupt input, missing codec, unexpected pydub/ffmpeg error) — logged as a warning, never raised. A bug in preprocessing degrades gracefully back to today's behavior; it can't take transcription down. This was exercised directly in `test_falls_back_to_original_file_on_undecodable_input`.

**Why it's not a scoring change:** trimming/normalizing shapes *when* speech starts/ends and *how loud* it is — it does not add, remove, or reorder words. "Do not reduce speech quality" is enforced by the `_MIN_AUDIO_MS` floor (never trims into real content) and by normalizing rather than compressing/gating (peak normalization is linear gain, not dynamic range reduction).

---

## 4. Part 3 — Whisper configuration

`backend/app/ai/speech/whisper_service.py`, `WhisperService.transcribe()`:

```python
result = model.transcribe(
    audio_path,
    language="en",
    task="transcribe",
    temperature=0.0,
    beam_size=5,
    best_of=5,
    condition_on_previous_text=False,
    fp16=self.device != "cpu",
)
```

| Setting | Before | After | Why |
|---|---|---|---|
| Model size | `base` (74M params) | `small` (244M params) | Materially lower published word-error-rate (see §5) for ~1.5–2x more CPU time — acceptable since transcription runs out-of-band in a Celery worker, never blocking the candidate or recruiter UI |
| `language` | auto-detect | `"en"` | Every assessment sentence is English; skipping language detection removes a source of misdetection on short clips and saves a small amount of time |
| `task` | `"transcribe"` (already the default) | `"transcribe"` (explicit) | Documents intent; guards against ever silently picking up `"translate"` |
| `temperature` | Whisper's default fallback tuple `(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)` | `0.0` (single value) | A tuple makes Whisper retry at higher (sampling) temperatures when it's unhappy with its own output — non-deterministic and unnecessary for short, clear assessment clips. A single `0.0` forces one deterministic beam-search decode: same audio in, same transcript out, every time |
| `beam_size` | `None` (greedy) | `5` | Beam search explores multiple candidate transcriptions per step instead of always taking the single most-likely token; materially reduces token-level errors on short utterances |
| `best_of` | `None` | `5` | Only takes effect when temperature-based sampling is active (it isn't, at `temperature=0.0`); set as requested for parity/documentation and to make behavior explicit if temperature is ever reintroduced |
| `condition_on_previous_text` | `True` (default) | `False` | Every recording here is one isolated sentence (Read Aloud / Listen & Repeat) — conditioning on prior segments only risks compounding one misheard word into the next, a known Whisper hallucination-loop failure mode |
| `fp16` | unset → Whisper defaults to `True`, then silently downgrades to fp32 on CPU with a warning | `device != "cpu"` | Cosmetic on CPU (removes the "FP16 is not supported" warning every run) but gives a real speed benefit if `WHISPER_DEVICE` is ever set to a CUDA device |

---

## 5. Part 4 — Transcript post-processing

`backend/app/ai/speech/transcript_cleanup.py`, applied to the final transcript string in `SpeechService.transcribe()`:

```python
_FILLER_WORDS = {"um", "umm", "uhm", "uh", "uhh", "erm", "hmm", "mhm"}

def clean_transcript(text: str) -> str:
    tokens = [token for token in text.split() if not _is_filler(token)]
    cleaned = " ".join(tokens)
    return re.sub(r"\s+", " ", cleaned).strip()
```

- **Collapses repeated whitespace** — Whisper occasionally emits doubled spaces around segment boundaries; a single regex pass normalizes this.
- **Removes standalone filler words only** — matched whole-token (via `str.split()`), case-insensitively, against a fixed list of non-lexical interjections. `_is_filler` strips surrounding punctuation only to *decide* whether a token is filler; real words are never partially edited (`"umpire"` and `"hummed"` are left alone — verified in `test_does_not_remove_words_containing_filler_as_substring`).
- **Preserves punctuation** — punctuation attached to a real word is never touched; punctuation attached to a removed filler token is removed along with it (e.g. `"Um, I think"` → `"I think"`), which does not affect the surrounding sentence's punctuation.
- **Never changes spoken words** — the filler list is a fixed, conservative set of disfluencies (`um`, `uh`, `erm`, `hmm`, ...); no content words, no rephrasing, no reordering.

This runs *before* the transcript reaches `AssessmentTranscript`/`AssessmentAnalysis`, so read-aloud/listen-repeat scoring (which compares the transcript against a reference sentence) is comparing a cleaner signal — without this task touching the scoring algorithm itself, exactly as scoped.

---

## 6. Part 5 — Metrics

### What was actually measured

A real recorded file already present in local storage (`storage/resumes/assessment-recordings/.../read_aloud/*.webm`, 7.92s, mono, 48kHz, produced by Chromium's fake-audio-capture device during earlier end-to-end testing) was run through both pipelines via `backend/scripts/benchmark_transcription.py`:

| | Old (base, no preprocessing, default args) | New (small, preprocessing, deterministic args) |
|---|---|---|
| Preprocessing time | n/a | 1.99s |
| Transcription time | 15.88s | 21.66s |
| **Total** | **15.88s** | **23.65s** |
| Slowdown factor | — | **1.49x** |

This is a single real, wall-clock measurement on this container's CPU (not a statistically averaged benchmark) — a directional result, not a lab-grade figure. It confirms the whole new pipeline (preprocessing → small model → deterministic decode) runs correctly end-to-end on a real, production-shaped `.webm` file, and that the runtime cost of moving to `small` is closer to ~1.5x than the ~3x a naive base→small parameter-count comparison would suggest.

**Important honesty note on word accuracy:** the file above came from Chromium's `--use-fake-device-for-media-stream` flag (used in this project's own Playwright E2E tests), which does not play back real human speech — so neither pipeline's transcript is a meaningful ground-truth accuracy comparison, and no word-accuracy percentage is fabricated here. Both pipelines produced plausible-sounding hallucinated fragments on this non-speech input, which is expected Whisper behavior on out-of-distribution audio, not evidence for or against this change.

### Expected transcription improvement (cited, not measured here)

For the *directional* accuracy claim, this relies on OpenAI's own published Whisper benchmarks (model card / paper), which report word-error-rate roughly halving from `base` to `small` on standard English benchmarks, with further, smaller gains from beam search (`beam_size=5`) over greedy decoding and from deterministic (non-sampling) decoding avoiding occasional degenerate high-temperature fallback outputs. Silence-trimming and level-normalization are standard ASR pre-processing steps precisely because they reduce the amount of non-speech signal (and quiet, noise-floor-adjacent speech) the acoustic model has to reason about — the mechanism, not a specific percentage, is what's being relied on here.

### Runtime impact

- **Preprocessing:** ~2s for an 8s clip in this measurement — small relative to transcription time, and it runs once per recording in a background Celery task, not in a request/response path.
- **Model size (`base` → `small`):** ~1.5x slower per transcription in this measurement. Still entirely acceptable for an async worker — candidates and recruiters never wait on this call.
- **Decoding (`beam_size=5`, deterministic `temperature=0.0`):** included in the "Transcription time" figure above (this is what `small` was measured with); beam search is inherently slower than greedy decoding per token, which is part of why `small` shows a measurable but not extreme slowdown rather than a negligible one.

### Memory impact

- **`base` model:** ~74M parameters, ~1GB RAM footprint as a loaded PyTorch model (per OpenAI's published model table).
- **`small` model:** ~244M parameters, ~2GB RAM footprint (per the same table) — roughly double `base`.
- Both are loaded once as a process-wide singleton (`app/ai/speech/whisper_service.py::get_model`), not per-request, so this is a one-time increase in the worker process's resident memory, not a per-transcription cost.
- `pydub`/preprocessing adds negligible memory: it operates on one recording (typically a few seconds of 16kHz mono audio, a few hundred KB in memory) at a time and is released once the temp WAV is written.

---

## 7. What was deliberately not changed

- No scoring/analysis logic (`app/ai/communication/*`) was touched — this task is scoped to transcript quality feeding that pipeline, not the pipeline itself.
- No cloud speech API, no OpenAI API, no Deepgram/AssemblyAI, no network call anywhere in this change — `pydub` only shells out to the local `ffmpeg` binary already required by Whisper.
- `WHISPER_MODEL_NAME`/`WHISPER_DEVICE` remain environment-overridable, so a deployment that needs to stay on `base` (e.g. very constrained hardware) can still do so without a code change.
