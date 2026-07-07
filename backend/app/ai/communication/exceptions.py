class CommunicationAnalysisError(Exception):
    """Base class for all Communication Analysis errors."""


class InvalidDurationError(CommunicationAnalysisError):
    """Raised when recording duration is missing or not a non-negative number.

    Permanent — retrying analysis of the same (already-persisted) duration
    value can't produce a different result.
    """
