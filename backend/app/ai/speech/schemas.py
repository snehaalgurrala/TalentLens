from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    confidence: float | None = None


class TranscriptionResult(BaseModel):
    transcript: str
    language: str
    duration_seconds: float
    processing_time_seconds: float
    model_name: str
    confidence: float | None = None
    segments: list[TranscriptSegment] = []
