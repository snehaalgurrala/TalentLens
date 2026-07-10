from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlatformAIConfigUpdate(BaseModel):
    llm_provider: str | None = Field(None, max_length=50)
    llm_model: str | None = Field(None, max_length=100)
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=32000)
    prompt_logging_enabled: bool | None = None
    embedding_model: str | None = Field(None, max_length=200)
    similarity_threshold: float | None = Field(None, ge=0, le=1)
    reranking_enabled: bool | None = None
    explainable_ai_enabled: bool | None = None
    retention_policy_days: int | None = Field(None, ge=1, le=3650)
    retention_policy_notes: str | None = None


class PlatformAIConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    llm_provider: str
    llm_model: str
    temperature: float
    max_tokens: int
    prompt_logging_enabled: bool
    embedding_model: str
    similarity_threshold: float
    reranking_enabled: bool
    explainable_ai_enabled: bool
    retention_policy_days: int
    retention_policy_notes: str | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime
    # Set true by the service whenever an update changes embedding_model —
    # changing it does not hot-reload the process-wide embedding model
    # singleton (see local_embedding_service.preload_model, called once at
    # FastAPI startup).
    restart_required: bool = False
