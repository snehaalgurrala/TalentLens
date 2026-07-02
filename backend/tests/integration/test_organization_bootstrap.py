"""
Real-Postgres integration tests for Task 2/3: secure registration + org
bootstrap. Every assertion checks actual database state (via db_session),
not just the HTTP response.
"""
import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.models.organization import Organization
from app.models.organization_invitation import InvitationStatus, OrganizationInvitation
from app.models.user import User, UserRole


class TestBootstrap:
    async def test_bootstrap_persists_org_and_admin(
        self, client: AsyncClient, db_session
    ):
        res = await client.post(
            "/api/v1/organizations/bootstrap",
            json={
                "org_name": "Wonka Industries",
                "org_slug": "wonka-industries",
                "admin_email": "willy@example.com",
                "admin_password": "securepass1",
                "admin_full_name": "Willy Wonka",
            },
        )
        assert res.status_code == 201, res.text
        org_id = uuid.UUID(res.json()["organization"]["id"])
        admin_id = uuid.UUID(res.json()["admin"]["id"])

        org = (
            await db_session.execute(select(Organization).where(Organization.id == org_id))
        ).scalar_one()
        assert org.slug == "wonka-industries"

        admin = (await db_session.execute(select(User).where(User.id == admin_id))).scalar_one()
        assert admin.role == UserRole.ORG_ADMIN
        assert admin.org_id == org_id
        assert admin.refresh_token_hash is not None  # login tokens were persisted

    async def test_duplicate_slug_returns_409_and_creates_nothing(
        self, client: AsyncClient, db_session
    ):
        payload = {
            "org_name": "Wonka Industries",
            "org_slug": "wonka-industries",
            "admin_email": "willy@example.com",
            "admin_password": "securepass1",
            "admin_full_name": "Willy Wonka",
        }
        first = await client.post("/api/v1/organizations/bootstrap", json=payload)
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/organizations/bootstrap",
            json={**payload, "admin_email": "someone-else@example.com"},
        )
        assert second.status_code == 409

        count = (
            await db_session.execute(select(Organization).where(Organization.slug == "wonka-industries"))
        ).scalars().all()
        assert len(count) == 1


class TestInvitationFlow:
    async def test_invite_then_register_creates_recruiter_in_same_org(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        invite_res = await client.post(
            f"/api/v1/organizations/{bootstrapped_admin['org_id']}/invitations",
            json={"email": "recruiter@example.com"},
            headers=bootstrapped_admin["headers"],
        )
        assert invite_res.status_code == 201, invite_res.text
        token = invite_res.json()["token"]
        invitation_id = uuid.UUID(invite_res.json()["id"])

        register_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "recruiter@example.com",
                "password": "securepass1",
                "full_name": "New Recruiter",
                "invitation_token": token,
            },
        )
        assert register_res.status_code == 201, register_res.text

        recruiter = (
            await db_session.execute(select(User).where(User.email == "recruiter@example.com"))
        ).scalar_one()
        assert recruiter.role == UserRole.RECRUITER
        assert str(recruiter.org_id) == bootstrapped_admin["org_id"]

        invitation = (
            await db_session.execute(
                select(OrganizationInvitation).where(OrganizationInvitation.id == invitation_id)
            )
        ).scalar_one()
        assert invitation.status == InvitationStatus.ACCEPTED
        assert invitation.accepted_at is not None

    async def test_register_cannot_choose_role_or_org(
        self, client: AsyncClient, db_session, bootstrapped_admin: dict
    ):
        """Even if a client sends role/org_id, the schema silently drops
        them — registration always creates a RECRUITER in the invitation's
        organization, never a SUPER_ADMIN or an arbitrary org."""
        other_org_id = str(uuid.uuid4())
        invite_res = await client.post(
            f"/api/v1/organizations/{bootstrapped_admin['org_id']}/invitations",
            json={"email": "hacker@example.com"},
            headers=bootstrapped_admin["headers"],
        )
        token = invite_res.json()["token"]

        register_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "hacker@example.com",
                "password": "securepass1",
                "full_name": "Hacker",
                "invitation_token": token,
                "role": "SUPER_ADMIN",
                "org_id": other_org_id,
            },
        )
        assert register_res.status_code == 201

        user = (
            await db_session.execute(select(User).where(User.email == "hacker@example.com"))
        ).scalar_one()
        assert user.role == UserRole.RECRUITER
        assert str(user.org_id) == bootstrapped_admin["org_id"]

    async def test_invalid_invitation_token_returns_400_and_creates_no_user(
        self, client: AsyncClient, db_session
    ):
        res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "nobody@example.com",
                "password": "securepass1",
                "full_name": "Nobody",
                "invitation_token": "not-a-real-token",
            },
        )
        assert res.status_code == 400

        users = (
            await db_session.execute(select(User).where(User.email == "nobody@example.com"))
        ).scalars().all()
        assert users == []

    async def test_reused_invitation_token_is_rejected(
        self, client: AsyncClient, bootstrapped_admin: dict
    ):
        invite_res = await client.post(
            f"/api/v1/organizations/{bootstrapped_admin['org_id']}/invitations",
            json={"email": "onetime@example.com"},
            headers=bootstrapped_admin["headers"],
        )
        token = invite_res.json()["token"]
        payload = {
            "email": "onetime@example.com",
            "password": "securepass1",
            "full_name": "One Time",
            "invitation_token": token,
        }

        first = await client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/auth/register",
            json={**payload, "email": "onetime2@example.com"},
        )
        assert second.status_code == 400

    async def test_recruiter_cannot_invite_other_recruiters(
        self, client: AsyncClient, bootstrapped_admin: dict
    ):
        # Create a recruiter via a valid invitation first.
        invite_res = await client.post(
            f"/api/v1/organizations/{bootstrapped_admin['org_id']}/invitations",
            json={"email": "recruiter2@example.com"},
            headers=bootstrapped_admin["headers"],
        )
        token = invite_res.json()["token"]
        register_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "recruiter2@example.com",
                "password": "securepass1",
                "full_name": "Recruiter Two",
                "invitation_token": token,
            },
        )
        recruiter_access_token = register_res.json()["access_token"]

        res = await client.post(
            f"/api/v1/organizations/{bootstrapped_admin['org_id']}/invitations",
            json={"email": "another@example.com"},
            headers={"Authorization": f"Bearer {recruiter_access_token}"},
        )
        assert res.status_code == 403
