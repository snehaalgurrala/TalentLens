"""
Builds normalized, embedding-ready text from structured resume / job
description data.

Kept separate from EmbeddingService so that service stays provider-agnostic
and input-agnostic — it just embeds whatever text string it's given. These
builders are the piece that knows how a StructuredResume or a
JobInfo/StructuredJD pair should be flattened into a single text blob.
"""

from app.schemas.job_description import JobInfo, StructuredJD
from app.schemas.resume import StructuredResume


def build_resume_embedding_text(structured: StructuredResume) -> str:
    parts: list[str] = []

    if structured.summary:
        parts.append(structured.summary)
    if structured.skills:
        parts.append("Skills: " + ", ".join(structured.skills))

    for exp in structured.experience:
        segment = " ".join(filter(None, [exp.role, "at", exp.company, "-", exp.description]))
        if segment.strip():
            parts.append(segment)

    for edu in structured.education:
        segment = " ".join(filter(None, [edu.degree, edu.field, "at", edu.institution]))
        if segment.strip():
            parts.append(segment)

    for proj in structured.projects:
        segment = " ".join(filter(None, [proj.name, proj.description]))
        if segment.strip():
            parts.append(segment)

    for cert in structured.certifications:
        segment = " ".join(filter(None, [cert.name, cert.issuer]))
        if segment.strip():
            parts.append(segment)

    return "\n".join(parts)


def build_job_description_embedding_text(job: JobInfo, structured_jd: StructuredJD) -> str:
    parts: list[str] = []

    header = " ".join(filter(None, [job.title, job.employment_type]))
    if header:
        parts.append(header)
    if job.industry:
        parts.append(f"Industry: {job.industry}")
    if job.location:
        parts.append(f"Location: {job.location}")
    if job.experience_min or job.experience_max:
        parts.append(f"Experience: {job.experience_min}-{job.experience_max} years")
    if structured_jd.required_skills:
        parts.append("Required skills: " + ", ".join(structured_jd.required_skills))
    if structured_jd.preferred_skills:
        parts.append("Preferred skills: " + ", ".join(structured_jd.preferred_skills))
    if structured_jd.responsibilities:
        parts.append("Responsibilities: " + "; ".join(structured_jd.responsibilities))
    if structured_jd.education:
        parts.append("Education: " + ", ".join(structured_jd.education))
    if structured_jd.certifications:
        parts.append("Certifications: " + ", ".join(structured_jd.certifications))
    if structured_jd.projects:
        parts.append("Projects: " + ", ".join(structured_jd.projects))

    return "\n".join(parts)
