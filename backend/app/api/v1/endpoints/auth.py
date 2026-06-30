from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth import AuthService

router = APIRouter()


# ── Dependency factory (overridable in tests) ─────────────────────────────────

def get_auth_service(db: DBSession) -> AuthService:
    return AuthService(UserRepository(db))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    responses={
        201: {"description": "Account created; access + refresh tokens returned."},
        409: {"description": "Email address is already registered."},
        422: {"description": "Validation error (e.g. password too short)."},
    },
)
async def register(data: RegisterRequest, service: AuthServiceDep) -> TokenResponse:
    _, tokens = await service.register(data)
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
async def login(data: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    _, tokens = await service.login(data)
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
async def refresh(data: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    return await service.refresh(data.refresh_token)
