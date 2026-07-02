from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """
    Public registration always creates a RECRUITER in the organization tied
    to a valid invitation — clients can never choose their own role or
    organization. Creating the first ORG_ADMIN of a new organization goes
    through POST /organizations/bootstrap instead.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="Minimum 8 characters")
    full_name: str = Field(min_length=1, max_length=255)
    invitation_token: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
