"""
WhisperService — every interaction with the local openai-whisper package
lives here. Nothing outside this module imports `whisper` directly.

Model loading mirrors app.services.local_embedding_service's pattern: a
thread-safe, process-wide singleton keyed by model name, loaded lazily on
first use and reused for every subsequent call. Loading is expensive
(reads model weights from WHISPER_MODEL_CACHE_DIR / the whisper default
cache, downloading them on first run if absent) so it must happen at most
once per model name per process.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

from app.ai.speech.config import get_cache_dir, get_device, get_model_name
from app.ai.speech.exceptions import ModelLoadError, TranscriptionError

if TYPE_CHECKING:
    from whisper.model import Whisper

logger = logging.getLogger(__name__)

_model: Whisper | None = None
_model_name: str | None = None
_model_lock = threading.Lock()


def _load_model(model_name: str, device: str) -> Whisper:
    logger.info("Loading Whisper model", extra={"model": model_name, "device": device})
    started = time.monotonic()
    try:
        import whisper  # lazy import — heavy (torch), only needed once a model is requested

        model = whisper.load_model(model_name, device=device, download_root=get_cache_dir())
    except Exception as exc:
        logger.error(
            "Failed to load Whisper model",
            extra={"model": model_name, "device": device, "error": str(exc)},
        )
        raise ModelLoadError(f"Could not load Whisper model '{model_name}': {exc}") from exc

    elapsed = time.monotonic() - started
    logger.info(
        "Whisper model loaded",
        extra={"model": model_name, "device": device, "seconds": round(elapsed, 2)},
    )
    return model


def get_model(model_name: str | None = None, device: str | None = None) -> Whisper:
    """Return the process-wide model singleton, loading it on first call."""
    global _model, _model_name
    resolved_name = model_name or get_model_name()
    resolved_device = device or get_device()

    if _model is not None and _model_name == resolved_name:
        return _model

    with _model_lock:
        if _model is None or _model_name != resolved_name:
            _model = _load_model(resolved_name, resolved_device)
            _model_name = resolved_name
    return _model


def reset_model_cache() -> None:
    """Test hook: force the next get_model() call to reload."""
    global _model, _model_name
    with _model_lock:
        _model = None
        _model_name = None


def is_loaded() -> bool:
    """For System Health reporting — the model loads lazily on first
    transcription request, so "not loaded" is a normal, expected state, not
    an error."""
    return _model is not None


class WhisperService:
    """
    Thin, synchronous wrapper around a loaded Whisper model. Callers run
    `.transcribe()` off the event loop (e.g. via asyncio.to_thread) — this
    class does no async work itself.
    """

    def __init__(self, *, model_name: str | None = None, device: str | None = None) -> None:
        self.model_name = model_name or get_model_name()
        self.device = device or get_device()

    def transcribe(self, audio_path: str) -> dict[str, Any]:
        """
        Transcribe an audio file already staged on disk. Returns Whisper's
        own result dict (text / segments / language) — plain data, no
        Whisper objects, so nothing outside this module needs to know
        about Whisper's internal types.
        """
        model = get_model(self.model_name, self.device)
        logger.info(
            "Transcription started", extra={"model": self.model_name, "audio_path": audio_path}
        )
        started = time.monotonic()
        try:
            result = model.transcribe(
                audio_path,
                language="en",
                task="transcribe",
                # A single float (not Whisper's default fallback tuple of
                # rising temperatures) disables temperature-fallback retries,
                # so every run of the same audio decodes identically.
                temperature=0.0,
                beam_size=5,
                best_of=5,
                # Every recording here is one isolated sentence (Read Aloud /
                # Listen & Repeat) — carrying decoding context from a
                # previous segment into the next only risks compounding a
                # misheard word instead of helping.
                condition_on_previous_text=False,
                # fp16 is a no-op on CPU (Whisper silently falls back to
                # fp32 with a warning); being explicit avoids that warning
                # and lets a GPU deployment (WHISPER_DEVICE=cuda) get real
                # fp16 speed.
                fp16=self.device != "cpu",
            )
        except Exception as exc:
            logger.error(
                "Transcription failed", extra={"model": self.model_name, "error": str(exc)}
            )
            raise TranscriptionError(f"Whisper failed to transcribe audio: {exc}") from exc

        elapsed = time.monotonic() - started
        logger.info(
            "Transcription finished",
            extra={"model": self.model_name, "seconds": round(elapsed, 2)},
        )
        return result
