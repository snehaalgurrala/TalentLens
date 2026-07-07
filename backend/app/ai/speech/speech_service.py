"""
SpeechService — transcription-only facade over the local Whisper foundation.

Validates raw audio bytes, stages them to a temp file, delegates to
WhisperService, and returns a structured TranscriptionResult. No database
access, no repositories, no knowledge of AssessmentSession — a future sprint
decides how transcripts get persisted and used; this module only turns
audio bytes into a transcript.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time

from app.ai.speech.schemas import TranscriptionResult, TranscriptSegment
from app.ai.speech.transcription import staged_audio_file, validate_audio
from app.ai.speech.whisper_service import WhisperService

logger = logging.getLogger(__name__)


def _segment_confidence(avg_logprob: float | None) -> float | None:
    """
    Whisper doesn't expose a single 0-1 confidence score; `avg_logprob`
    (average log-probability per token) is the closest signal it returns.
    exp(avg_logprob) rescales it into an approximate (0, 1] confidence —
    a common heuristic, not a calibrated probability.
    """
    if avg_logprob is None:
        return None
    return math.exp(avg_logprob)


class SpeechService:
    """Reusable Speech AI entry point: audio bytes in, transcript out."""

    def __init__(self, whisper_service: WhisperService | None = None) -> None:
        self.whisper_service = whisper_service or WhisperService()

    async def transcribe(
        self, data: bytes, *, mime_type: str, filename: str | None = None
    ) -> TranscriptionResult:
        """
        Validate `data` as an audio file of type `mime_type` and transcribe
        it with the configured local Whisper model.

        Raises AudioValidationError for missing/unsupported/oversized
        input, ModelLoadError if the model can't be loaded, and
        TranscriptionError if Whisper fails on a corrupted or unreadable
        (but validly-typed) file.
        """
        normalized_mime = validate_audio(data, mime_type)

        with staged_audio_file(data, normalized_mime) as audio_path:
            started = time.monotonic()
            raw = await asyncio.to_thread(self.whisper_service.transcribe, audio_path)
            elapsed = time.monotonic() - started

        segments = [
            TranscriptSegment(
                id=segment.get("id", index),
                start=segment.get("start", 0.0),
                end=segment.get("end", 0.0),
                text=(segment.get("text") or "").strip(),
                confidence=_segment_confidence(segment.get("avg_logprob")),
            )
            for index, segment in enumerate(raw.get("segments") or [])
        ]

        duration_seconds = segments[-1].end if segments else 0.0
        confidences = [s.confidence for s in segments if s.confidence is not None]
        overall_confidence = sum(confidences) / len(confidences) if confidences else None

        result = TranscriptionResult(
            transcript=(raw.get("text") or "").strip(),
            language=raw.get("language") or "unknown",
            duration_seconds=duration_seconds,
            processing_time_seconds=round(elapsed, 3),
            model_name=self.whisper_service.model_name,
            confidence=overall_confidence,
            segments=segments,
        )
        logger.info(
            "Transcription complete",
            extra={
                "model": result.model_name,
                "language": result.language,
                "duration_seconds": result.duration_seconds,
                "processing_time_seconds": result.processing_time_seconds,
                "segment_count": len(result.segments),
                "audio_filename": filename,
            },
        )
        return result
