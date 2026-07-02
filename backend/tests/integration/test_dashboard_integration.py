"""
Real-Postgres integration tests for the dashboard module.

Exercises the dashboard endpoints against real campaign/resume rows created
through the normal API, plus direct db_session writes for states that have
no write endpoint yet (review_status), to prove the read-side aggregation
is correct end-to-end.
"""
import io
import uuid
from datetime import UTC, datetime

from httpx import AsyncClient
from pypdf import PdfWriter
from sqlalchemy import select

from app.models.resume_file import ResumeFile, ReviewStatus


def _make_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


async def test_summary_reflects_real_campaign_and_resume_state(
    client: AsyncClient, db_session, bootstrapped_admin: dict
):
    headers = bootstrapped_admin["headers"]

    active_res = await client.post(
        "/api/v1/campaigns/",
        json={"title": "Active Campaign", "status": "ACTIVE"},
        headers=headers,
    )
    assert active_res.status_code == 201, active_res.text
    active_campaign_id = active_res.json()["id"]

    closed_res = await client.post(
        "/api/v1/campaigns/",
        json={"title": "Closed Campaign", "status": "CLOSED"},
        headers=headers,
    )
    assert closed_res.status_code == 201, closed_res.text

    summary_res = await client.get("/api/v1/dashboard/summary", headers=headers)
    assert summary_res.status_code == 200, summary_res.text
    summary = summary_res.json()
    assert summary["total_campaigns"] == 2
    assert summary["active_campaigns"] == 1
    assert summary["closed_campaigns"] == 1
    assert summary["total_candidates"] == 0
    assert summary["shortlisted_candidates"] == 0
    assert summary["rejected_candidates"] == 0
    # No active campaign has a ranking-ready job description yet.
    assert summary["average_match_score"] is None

    files = [("files", ("resume.pdf", _make_pdf_bytes(), "application/pdf"))]
    upload_res = await client.post(
        f"/api/v1/campaigns/{active_campaign_id}/resumes/upload",
        files=files,
        headers=headers,
    )
    assert upload_res.status_code == 201, upload_res.text
    resume_file_id = uuid.UUID(upload_res.json()["uploaded"][0]["id"])

    summary_res = await client.get("/api/v1/dashboard/summary", headers=headers)
    summary = summary_res.json()
    assert summary["processing_candidates"] == 1

    processing_res = await client.get("/api/v1/dashboard/processing-status", headers=headers)
    assert processing_res.status_code == 200, processing_res.text
    processing = processing_res.json()
    assert processing["parsing_queue"] == 1
    assert processing["completed_jobs"] == 0
    assert processing["failed_jobs"] == 0

    # No write endpoint sets review_status yet (that's a future recruiter-actions
    # feature) — set it directly to prove the dashboard picks up real state.
    resume_row = (
        await db_session.execute(select(ResumeFile).where(ResumeFile.id == resume_file_id))
    ).scalar_one()
    resume_row.review_status = ReviewStatus.SHORTLISTED
    resume_row.reviewed_at = datetime.now(UTC)
    await db_session.commit()

    summary_res = await client.get("/api/v1/dashboard/summary", headers=headers)
    summary = summary_res.json()
    assert summary["shortlisted_candidates"] == 1


async def test_recent_campaigns_ordered_most_recent_first(
    client: AsyncClient, bootstrapped_admin: dict
):
    headers = bootstrapped_admin["headers"]

    first = await client.post(
        "/api/v1/campaigns/", json={"title": "First Campaign"}, headers=headers
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        "/api/v1/campaigns/", json={"title": "Second Campaign"}, headers=headers
    )
    assert second.status_code == 201, second.text

    res = await client.get("/api/v1/dashboard/recent-campaigns", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) == 2
    assert body[0]["title"] == "Second Campaign"
    assert body[0]["candidate_count"] == 0
    assert body[1]["title"] == "First Campaign"


async def test_activity_feed_includes_campaign_and_resume_events(
    client: AsyncClient, bootstrapped_admin: dict
):
    headers = bootstrapped_admin["headers"]

    campaign_res = await client.post(
        "/api/v1/campaigns/", json={"title": "Platform Engineer"}, headers=headers
    )
    assert campaign_res.status_code == 201, campaign_res.text
    campaign_id = campaign_res.json()["id"]

    files = [("files", ("resume.pdf", _make_pdf_bytes(), "application/pdf"))]
    upload_res = await client.post(
        f"/api/v1/campaigns/{campaign_id}/resumes/upload",
        files=files,
        headers=headers,
    )
    assert upload_res.status_code == 201, upload_res.text

    res = await client.get("/api/v1/dashboard/activity", headers=headers)
    assert res.status_code == 200, res.text
    events = res.json()
    event_types = {e["type"] for e in events}
    assert "CAMPAIGN_CREATED" in event_types
    assert "RESUME_UPLOADED" in event_types
    # Newest first.
    occurred_ats = [e["occurred_at"] for e in events]
    assert occurred_ats == sorted(occurred_ats, reverse=True)


async def test_top_candidates_empty_when_no_ranking_ready_campaign(
    client: AsyncClient, bootstrapped_admin: dict
):
    headers = bootstrapped_admin["headers"]

    campaign_res = await client.post(
        "/api/v1/campaigns/",
        json={"title": "No JD Yet", "status": "ACTIVE"},
        headers=headers,
    )
    assert campaign_res.status_code == 201, campaign_res.text

    res = await client.get("/api/v1/dashboard/top-candidates", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json() == []
