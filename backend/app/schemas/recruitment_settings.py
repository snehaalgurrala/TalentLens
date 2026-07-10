from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ALLOWED_RESUME_FORMATS = {"pdf", "doc", "docx"}


def _validate_formats(formats: list[str]) -> list[str]:
    invalid = [f for f in formats if f.lower() not in _ALLOWED_RESUME_FORMATS]
    if invalid:
        raise ValueError(
            f"Unsupported resume format(s): {', '.join(invalid)}. "
            f"Allowed: {', '.join(sorted(_ALLOWED_RESUME_FORMATS))}."
        )
    return [f.lower() for f in formats]


class RecruitmentSettingsUpdate(BaseModel):
    default_resume_score_threshold: float | None = Field(None, ge=0, le=100)
    enable_explainable_ai: bool | None = None
    max_resume_upload_count: int | None = Field(None, ge=1, le=500)
    max_resume_size_mb: int | None = Field(None, ge=1, le=100)
    supported_resume_formats: list[str] | None = None

    @field_validator("supported_resume_formats")
    @classmethod
    def _check_formats(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        return _validate_formats(v)


class RecruitmentSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    default_resume_score_threshold: float
    enable_explainable_ai: bool
    max_resume_upload_count: int
    max_resume_size_mb: int
    supported_resume_formats: list[str]
    created_at: datetime
    updated_at: datetime
