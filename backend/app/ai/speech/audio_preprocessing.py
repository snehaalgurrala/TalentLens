"""
Audio preprocessing — trims leading/trailing silence and normalizes peak
level before the audio reaches Whisper. Runs entirely offline via pydub,
which shells out to the same `ffmpeg` binary Whisper itself already requires
(see requirements.txt / Dockerfile) — no new external service, no network
call.

Silence padding around a candidate's answer wastes decoding steps and can
bias Whisper's segment boundaries; inconsistent recording levels (quiet
mics, browsers that don't apply gain) push speech closer to the noise floor.
Trimming + normalizing before transcription addresses both without altering
the words spoken.
"""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Whisper resamples to 16kHz mono internally regardless; doing it explicitly
# here means preprocessing and transcription agree on the same audio.
_TARGET_SAMPLE_RATE = 16000
_TARGET_CHANNELS = 1

# Audio quieter than this (dBFS, relative to digital full scale) is treated
# as silence when trimming leading/trailing padding.
_SILENCE_THRESHOLD_DBFS = -40.0

# Never trim below this much audio. Protects a fully (or near-fully) silent
# recording — e.g. a synthetic test clip, or a candidate who never
# spoke — from being reduced to a near-empty file that would give Whisper
# nothing to work with.
_MIN_AUDIO_MS = 200


def _trim_silence(audio: object) -> object:
    from pydub import silence as pydub_silence

    leading_ms = pydub_silence.detect_leading_silence(
        audio, silence_threshold=_SILENCE_THRESHOLD_DBFS
    )
    trailing_ms = pydub_silence.detect_leading_silence(
        audio.reverse(), silence_threshold=_SILENCE_THRESHOLD_DBFS
    )
    start = leading_ms
    end = len(audio) - trailing_ms

    if end - start < _MIN_AUDIO_MS:
        return audio
    return audio[start:end]


@contextmanager
def preprocess_audio_file(audio_path: str) -> Iterator[str]:
    """
    Trim leading/trailing silence and normalize peak level, writing the
    result to a new temp WAV file and yielding its path.

    Falls back to yielding the original, untouched file if preprocessing
    fails for any reason (corrupt input, unsupported container, missing
    ffmpeg) — a preprocessing bug must never take down transcription, which
    already works today without it.
    """
    processed_path: str | None = None
    try:
        from pydub import AudioSegment
        from pydub.effects import normalize

        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_frame_rate(_TARGET_SAMPLE_RATE).set_channels(_TARGET_CHANNELS)
        audio = _trim_silence(audio)
        audio = normalize(audio)

        fd, processed_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        audio.export(processed_path, format="wav")
    except Exception:
        logger.warning(
            "Audio preprocessing failed; transcribing the original recording instead",
            extra={"audio_path": audio_path},
            exc_info=True,
        )
        yield audio_path
        return

    try:
        yield processed_path
    finally:
        if processed_path and os.path.exists(processed_path):
            os.remove(processed_path)
