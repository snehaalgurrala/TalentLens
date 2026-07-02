"""
Real-Postgres, real-pgvector, end-to-end integration test (Task 9).

Walks the full production workflow and asserts actual database state after
every stage, not just HTTP status codes:

  Organization creation -> ORG_ADMIN creation -> Recruiter invitation ->
  Recruiter registration -> Recruiter login -> Campaign creation ->
  JD upload -> JD parsing -> JD embedding -> Resume upload ->
  Resume parsing -> Resume embedding -> Matching -> Ranking ->
  Explainable matching.

Parsing is exercised via the same worker entry points Celery calls
(_run_parse_job_description / _run_parse_resume), with only the outbound
AI-service HTTP call mocked — everything else (DB session, repositories,
LocalEmbeddingService, pgvector storage, ranking/matching/explanation) is
real. This is the same testing convention already used by
test_resume_parser.py / test_job_description_parser.py, just chained
end-to-end against a real database instead of mocked repositories.
"""
import io
import uuid
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
from pypdf import PdfWriter
from sqlalchemy import select

from app.models.candidate import Candidate
from app.models.embedding import EmbeddingStatus
from app.models.job_description import JobDescription, ParsingStatus
from app.models.parsed_resume import ParsedResume
from app.models.resume_file import ResumeFile, UploadStatus
from app.workers.embedding_worker import (
    _run_generate_job_description_embedding,
    _run_generate_resume_embedding,
)
from app.workers.job_description_parser import _run_parse_job_description
from app.workers.resume_parser import _run_parse_resume


def _make_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_http_client(json_response: dict) -> AsyncMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = json_response
    client = AsyncMock()
    client.post.return_value = mock_resp
    return client


_JD_AI_RESPONSE = {
    "job": {
        "title": "Platform Engineer",
        "employment_type": "full_time",
        "industry": "Software",
        "location": "Remote",
        "experience_min": 3,
        "experience_max": 8,
    },
    "structured_jd": {
        "required_skills": ["Kubernetes", "Terraform", "Python"],
        "preferred_skills": ["Go"],
        "responsibilities": ["Own platform infrastructure"],
        "education": ["BS Computer Science"],
        "certifications": [],
        "projects": [],
    },
    "confidence": 0.92,
}

_RESUME_AI_RESPONSE = {
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice.candidate@example.com",
    "phone": "+1-555-0100",
    "linkedin_url": None,
    "github_url": None,
    "location": "Remote",
    "years_of_experience": 5.0,
    "current_company": "Acme",
    "current_role": "Platform Engineer",
}


async def test_full_workflow_persists_expected_state_at_every_stage(
    client: AsyncClient, db_session, bootstrapped_admin: dict
):
    org_id = bootstrapped_admin["org_id"]

    # ── Stage 1-2: Organization + ORG_ADMIN already created by the fixture ──
    # (see test_organization_bootstrap.py for dedicated bootstrap assertions)

    # ── Stage 3: Invite + register a recruiter ──────────────────────────────
    invite_res = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "recruiter@example.com"},
        headers=bootstrapped_admin["headers"],
    )
    assert invite_res.status_code == 201, invite_res.text
    invitation_token = invite_res.json()["token"]

    register_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "recruiter@example.com",
            "password": "securepass1",
            "full_name": "Riley Recruiter",
            "invitation_token": invitation_token,
        },
    )
    assert register_res.status_code == 201, register_res.text

    # ── Stage 4: Recruiter login ─────────────────────────────────────────────
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "recruiter@example.com", "password": "securepass1"},
    )
    assert login_res.status_code == 200, login_res.text
    recruiter_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # ── Stage 5: Campaign creation ───────────────────────────────────────────
    campaign_res = await client.post(
        "/api/v1/campaigns/",
        json={"title": "Platform Engineer Hiring", "description": "Q3 hiring push"},
        headers=recruiter_headers,
    )
    assert campaign_res.status_code == 201, campaign_res.text
    campaign_id = campaign_res.json()["id"]

    # ── Stage 6: Job description upload (as text) ────────────────────────────
    jd_res = await client.post(
        f"/api/v1/campaigns/{campaign_id}/job-descriptions",
        json={
            "text": "We need a Platform Engineer with Kubernetes and Terraform experience."
        },
        headers=recruiter_headers,
    )
    assert jd_res.status_code == 201, jd_res.text
    jd_id = uuid.UUID(jd_res.json()["id"])

    jd_row = (
        await db_session.execute(select(JobDescription).where(JobDescription.id == jd_id))
    ).scalar_one()
    assert jd_row.parsing_status == ParsingStatus.PENDING
    assert jd_row.embedding_status == EmbeddingStatus.PENDING

    # ── Stage 7: JD parsing (same code path Celery calls, AI HTTP call mocked) ──
    await _run_parse_job_description(
        str(jd_id), _http_client=_make_http_client(_JD_AI_RESPONSE), _embedding_dispatcher=MagicMock()
    )

    await db_session.refresh(jd_row)
    assert jd_row.parsing_status == ParsingStatus.COMPLETED
    assert jd_row.structured_json["job"]["title"] == "Platform Engineer"

    # ── Stage 8: JD embedding (real sentence-transformers model, real pgvector) ──
    await _run_generate_job_description_embedding(str(jd_id))

    await db_session.refresh(jd_row)
    assert jd_row.embedding_status == EmbeddingStatus.READY
    assert jd_row.embedding is not None
    assert jd_row.embedding_dimension is not None and jd_row.embedding_dimension > 0

    # ── Stage 9: Resume upload ───────────────────────────────────────────────
    files = [("files", ("alice.pdf", _make_pdf_bytes(), "application/pdf"))]
    upload_res = await client.post(
        f"/api/v1/campaigns/{campaign_id}/resumes/upload",
        files=files,
        headers=recruiter_headers,
    )
    assert upload_res.status_code == 201, upload_res.text
    resume_file_id = uuid.UUID(upload_res.json()["uploaded"][0]["id"])

    resume_row = (
        await db_session.execute(select(ResumeFile).where(ResumeFile.id == resume_file_id))
    ).scalar_one()
    assert resume_row.upload_status == UploadStatus.UPLOADED

    # ── Stage 10: Resume parsing (AI HTTP call mocked; extraction is real) ──────
    await _run_parse_resume(
        str(resume_file_id),
        _http_client=_make_http_client(_RESUME_AI_RESPONSE),
        _embedding_dispatcher=MagicMock(),
    )

    await db_session.refresh(resume_row)
    assert resume_row.upload_status == UploadStatus.PARSED
    assert resume_row.candidate_id is not None

    candidate = (
        await db_session.execute(select(Candidate).where(Candidate.id == resume_row.candidate_id))
    ).scalar_one()
    assert candidate.email == "alice.candidate@example.com"
    assert str(candidate.organization_id) == org_id

    parsed_resume = (
        await db_session.execute(
            select(ParsedResume).where(ParsedResume.resume_file_id == resume_file_id)
        )
    ).scalar_one()
    assert parsed_resume.embedding_status == EmbeddingStatus.PENDING

    # ── Stage 11: Resume embedding ───────────────────────────────────────────
    await _run_generate_resume_embedding(str(parsed_resume.id))

    await db_session.refresh(parsed_resume)
    assert parsed_resume.embedding_status == EmbeddingStatus.READY
    assert parsed_resume.embedding is not None

    # ── Stage 12-14: Matching, ranking, explainable matching ────────────────
    # All three are surfaced together by the single rankings endpoint —
    # CandidateRankingService computes matching + scoring + the human-
    # readable explanation fresh on every call (see its own docstring: no
    # cached ranking to separately "refresh").
    ranking_res = await client.get(
        f"/api/v1/campaigns/{campaign_id}/rankings", headers=recruiter_headers
    )
    assert ranking_res.status_code == 200, ranking_res.text
    rankings = ranking_res.json()
    assert len(rankings) == 1

    entry = rankings[0]
    assert entry["candidate_id"] == str(candidate.id)
    assert entry["resume_file_id"] == str(resume_file_id)
    assert 0 <= entry["overall_score"] <= 100
    assert entry["recommendation"] in {
        "Strong Match", "Good Match", "Possible Match", "Not a Match",
    }
    assert entry["scoring_rule_source"] == "system_default"
    assert entry["match_explanation"]  # non-empty explainable-matching output
    assert isinstance(entry["strengths"], list)
    assert isinstance(entry["weaknesses"], list)
