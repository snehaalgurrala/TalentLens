from pydantic import BaseModel, ConfigDict, Field


class JobInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    title: str = ""
    experience_min: int = Field(default=0, ge=0)
    experience_max: int = Field(default=0, ge=0)
    industry: str = ""
    employment_type: str = ""
    location: str = ""


class StructuredJD(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ParseJobDescriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jd_text: str = Field(..., min_length=1)
    parser_version: str = "v1"


class ParseJobDescriptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    job: JobInfo
    structured_jd: StructuredJD
    confidence: float = Field(ge=0.0, le=1.0)
