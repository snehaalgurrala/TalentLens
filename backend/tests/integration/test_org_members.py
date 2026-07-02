"""
Real-Postgres integration test for GET /users/org-members — the endpoint
that powers the Hiring Manager / Recruiter dropdowns on the campaign form.
Exercises the real invitation -> registration flow rather than mocking
UserRepository, since the endpoint talks to the DB directly (no service
layer to swap out).
"""

import uuid

from httpx import AsyncClient


async def _invite_and_register(
    client: AsyncClient, org_id: str, admin_headers: dict, *, role: str = "RECRUITER"
) -> dict:
    suffix = uuid.uuid4().hex[:8]
    email = f"member-{suffix}@example.com"
    invite_res = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": email},
        headers=admin_headers,
    )
    assert invite_res.status_code == 201, invite_res.text
    token = invite_res.json()["token"]

    register_res = await client.post(
        "/api/v1/auth/register",
        json={
            "invitation_token": token,
            "email": email,
            "full_name": f"Member {suffix}",
            "password": "securepass1",
        },
    )
    assert register_res.status_code == 201, register_res.text

    login_res = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "securepass1"}
    )
    assert login_res.status_code == 200, login_res.text
    return {
        "email": email,
        "headers": {"Authorization": f"Bearer {login_res.json()['access_token']}"},
    }


class TestOrgMembers:
    async def test_lists_admin_and_recruiters(
        self, client: AsyncClient, bootstrapped_admin: dict
    ):
        await _invite_and_register(client, bootstrapped_admin["org_id"], bootstrapped_admin["headers"])

        res = await client.get("/api/v1/users/org-members", headers=bootstrapped_admin["headers"])

        assert res.status_code == 200
        body = res.json()
        emails = {member["email"] for member in body}
        assert bootstrapped_admin["admin_email"] in emails
        assert len(body) == 2
        assert all(member["role"] in ("ORG_ADMIN", "RECRUITER") for member in body)

    async def test_recruiter_can_also_list_members(
        self, client: AsyncClient, bootstrapped_admin: dict
    ):
        recruiter = await _invite_and_register(
            client, bootstrapped_admin["org_id"], bootstrapped_admin["headers"]
        )

        res = await client.get("/api/v1/users/org-members", headers=recruiter["headers"])

        assert res.status_code == 200
        assert len(res.json()) == 2

    async def test_unauthenticated_request_rejected(self, client: AsyncClient):
        res = await client.get("/api/v1/users/org-members")
        assert res.status_code == 401
