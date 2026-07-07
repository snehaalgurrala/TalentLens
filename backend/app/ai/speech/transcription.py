"""
Audio validation and temp-file staging for Whisper transcription.

No database access. No Whisper import here — this module only prepares raw
bytes into something WhisperService can hand to ffmpeg, and validates them
first so bad input never reaches the model.
"""

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager

from app.ai.speech.config import ALLOWED_AUDIO_MIME_TYPES, get_max_audio_size_bytes
from app.ai.speech.exceptions import AudioValidationError


def validate_audio(data: bytes | None, mime_type: str | None) -> str:
    """
    Validate raw audio bytes and mime type. Returns the normalized
    (base, lower-cased) mime type on success.

    Raises AudioValidationError for a missing file, an unsupported mime
    type, or a file exceeding the configured size cap.
    """
    if not data:
        raise AudioValidationError("No audio data provided.")

    base_mime = (mime_type or "").split(";")[0].strip().lower()
    if base_mime not in ALLOWED_AUDIO_MIME_TYPES:
        allowed = ", ".join(sorted(ALLOWED_AUDIO_MIME_TYPES))
        raise AudioValidationError(
            f"Unsupported audio type '{mime_type or '(none)'}'. Allowed: {allowed}."
        )

    max_bytes = get_max_audio_size_bytes()
    if len(data) > max_bytes:
        raise AudioValidationError(
            f"Audio file size ({len(data) / (1024 * 1024):.1f} MB) exceeds the "
            f"{max_bytes / (1024 * 1024):.0f} MB limit."
        )

    return base_mime


@contextmanager
def staged_audio_file(data: bytes, mime_type: str) -> Iterator[str]:
    """
    Write already-validated audio bytes to a temp file with the extension
    matching `mime_type`, so ffmpeg (invoked internally by Whisper) can
    sniff the container format. The file is removed on exit.
    """
    suffix = ALLOWED_AUDIO_MIME_TYPES[mime_type]
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        yield path
    finally:
        if os.path.exists(path):
            os.remove(path)
