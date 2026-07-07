"""
Speech AI configuration — thin wrapper around app.core.config.settings.

Deployment-tunable values (model name, device, cache dir, size cap) live on
the global Settings object, same as every other subsystem (see
LOCAL_EMBEDDING_* in app.core.config). Module-local constants that are not
deployment config (the supported audio containers) live here instead.
"""

from app.core.config import settings

# Mime type -> file extension. Extension is required so ffmpeg (invoked by
# Whisper) can sniff the container format from a staged temp file.
ALLOWED_AUDIO_MIME_TYPES: dict[str, str] = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
}


def get_model_name() -> str:
    return settings.WHISPER_MODEL_NAME


def get_device() -> str:
    return settings.WHISPER_DEVICE


def get_cache_dir() -> str | None:
    return settings.WHISPER_MODEL_CACHE_DIR


def get_max_audio_size_bytes() -> int:
    return settings.WHISPER_MAX_AUDIO_SIZE_MB * 1024 * 1024
