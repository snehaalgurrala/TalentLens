from pydantic import BaseModel, Field


class GenerateEmbeddingRequest(BaseModel):
    text: str = Field(..., min_length=1)


class GenerateEmbeddingResponse(BaseModel):
    embedding: list[float]
    model: str
    dimension: int
