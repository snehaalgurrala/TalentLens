class SpeechAIError(Exception):
    """Base class for all Speech AI (Whisper) errors."""


class AudioValidationError(SpeechAIError):
    """Raised when input audio fails validation before transcription is attempted."""


class ModelLoadError(SpeechAIError):
    """Raised when the local Whisper model cannot be loaded."""


class TranscriptionError(SpeechAIError):
    """Raised when Whisper fails to transcribe an already-validated audio file."""
