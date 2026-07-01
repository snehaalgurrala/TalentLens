from pydantic import BaseModel, Field


class CandidateInfo(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    years_of_experience: float = 0.0
    current_company: str = ""
    current_role: str = ""


class ExperienceEntry(BaseModel):
    company: str = ""
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""


class EducationEntry(BaseModel):
    institution: str = ""
    degree: str = ""
    field: str = ""
    graduation_year: str = ""


class ProjectEntry(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    name: str = ""
    issuer: str = ""
    date: str = ""


class StructuredResume(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    summary: str = ""


class ParseResumeRequest(BaseModel):
    resume_text: str
    parser_version: str = "v1"


class ParseResumeResponse(BaseModel):
    candidate: CandidateInfo
    structured_resume: StructuredResume
    confidence: float = Field(ge=0.0, le=1.0)
