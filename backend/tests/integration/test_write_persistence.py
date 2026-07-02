"""
Real-Postgres integration tests for Task 1: DB writes must actually commit.

Before the get_db() fix, every one of these calls would return a 200/201
response but the row would vanish the instant the request finished (the
session was closed without ever calling commit(), which rolls back any
pending transaction). Every test here re-queries via a fresh db_session to
prove the row is really there.
"""
import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_token
from app.models.campaign import Campaign
from app.models.job_description import JobDescription
from app.models.resume_file import ResumeFile
from app.models.user import User


async def _register_recruiter(client: AsyncClient, bootstrapped_admin: dict, email: str) -> dict:
    invite_res = await client.post(
        f"/api/v1/organizations/{bootstrapped_admin['org_id']}/invitations",
        json={"email": email},
        headers=bootstrapped_admin["headers"],
    )
    token = invite_res.json()["token"]
    register_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass1",
            "full_name": "Recruiter",
            "invitation_token": token,
        },
    )
    assert register_res.status_code == 201, register_res.text
    body = register_res.json()
    return {"headers": {"Authorization": f"Bearer {body['access_token']}"}}


class TestLoginPersistence:
    async def test_login_rotates_refresh_token_hash_in_db(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        await _register_recruiter(client, bootstrapped_admin, "recruiter@example.com")

        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "recruiter@example.com", "password": "securepass1"},
        )
        assert login_res.status_code == 200
        issued_refresh_token = login_res.json()["refresh_token"]

        after = (
            await db_session.execute(select(User).where(User.email == "recruiter@example.com"))
        ).scalar_one()
        # Proves the UPDATE committed with exactly the value the API returned,
        # not just that *a* row exists.
        assert after.refresh_token_hash == hash_token(issued_refresh_token)


class TestCampaignPersistence:
    async def test_create_campaign_persists(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        res = await client.post(
            "/api/v1/campaigns/",
            json={"title": "Senior Backend Engineer", "description": "Hiring"},
            headers=bootstrapped_admin["headers"],
        )
        assert res.status_code == 201, res.text
        campaign_id = uuid.UUID(res.json()["id"])

        campaign = (
            await db_session.execute(select(Campaign).where(Campaign.id == campaign_id))
        ).scalar_one()
        assert campaign.title == "Senior Backend Engineer"
        assert str(campaign.org_id) == bootstrapped_admin["org_id"]


class TestResumeUploadPersistence:
    async def test_upload_resume_persists_metadata(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        campaign_res = await client.post(
            "/api/v1/campaigns/",
            json={"title": "Data Engineer", "description": None},
            headers=bootstrapped_admin["headers"],
        )
        campaign_id = campaign_res.json()["id"]

        files = [("files", ("resume.pdf", b"%PDF-1.4 fake resume content", "application/pdf"))]
        res = await client.post(
            f"/api/v1/campaigns/{campaign_id}/resumes/upload",
            files=files,
            headers=bootstrapped_admin["headers"],
        )
        assert res.status_code == 201, res.text
        resume_id = uuid.UUID(res.json()["uploaded"][0]["id"])

        resume_file = (
            await db_session.execute(select(ResumeFile).where(ResumeFile.id == resume_id))
        ).scalar_one()
        assert resume_file.original_filename == "resume.pdf"
        assert str(resume_file.campaign_id) == campaign_id
        assert resume_file.file_size == len(b"%PDF-1.4 fake resume content")


class TestJobDescriptionPersistence:
    async def test_create_job_description_persists(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        campaign_res = await client.post(
            "/api/v1/campaigns/",
            json={"title": "Platform Engineer", "description": None},
            headers=bootstrapped_admin["headers"],
        )
        campaign_id = campaign_res.json()["id"]

        res = await client.post(
            f"/api/v1/campaigns/{campaign_id}/job-descriptions",
            json={"text": "We are looking for a Platform Engineer with Kubernetes experience."},
            headers=bootstrapped_admin["headers"],
        )
        assert res.status_code == 201, res.text
        jd_id = uuid.UUID(res.json()["id"])

        jd = (
            await db_session.execute(select(JobDescription).where(JobDescription.id == jd_id))
        ).scalar_one()
        assert "Kubernetes" in jd.raw_text
        assert str(jd.campaign_id) == campaign_id
