from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import DBSession
from app.repositories.organization_invitation import OrganizationInvitationRepository
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter()


# ── Dependency factory (overridable in tests) ─────────────────────────────────

def get_auth_service(db: DBSession) -> AuthService:
    return AuthService(
        UserRepository(db),
        OrganizationInvitationRepository(db),
        UserSessionRepository(db),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new recruiter account via invitation",
    responses={
        201: {"description": "Account created; access + refresh tokens returned."},
        400: {"description": "Invitation token is invalid, expired, or already used."},
        409: {"description": "Email address is already registered."},
        422: {"description": "Validation error (e.g. password too short)."},
    },
)
async def register(data: RegisterRequest, service: AuthServiceDep, request: Request) -> TokenResponse:
    _, tokens = await service.register(data, request)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password",
    responses={
        200: {"description": "Credentials valid; access + refresh tokens returned."},
        401: {"description": "Invalid email or password."},
        403: {"description": "Account is inactive."},
    },
)
async def login(data: LoginRequest, service: AuthServiceDep, request: Request) -> TokenResponse:
    _, tokens = await service.login(data, request)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new token pair",
    responses={
        200: {"description": "New access + refresh tokens issued (old refresh token invalidated)."},
        401: {"description": "Refresh token is invalid, expired, or already rotated."},
    },
)
async def refresh(data: RefreshRequest, service: AuthServiceDep, request: Request) -> TokenResponse:
    return await service.refresh(data.refresh_token, request)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the session tied to the given refresh token",
    responses={204: {"description": "Session revoked (or already invalid — logout never fails loudly)."}},
)
async def logout(data: RefreshRequest, service: AuthServiceDep) -> None:
    await service.logout(data.refresh_token)
