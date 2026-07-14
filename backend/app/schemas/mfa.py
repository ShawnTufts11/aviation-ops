"""MFA challenge response — returned when user has MFA enabled."""

from pydantic import BaseModel


class MfaChallengeRequest(BaseModel):
    temp_token: str
    totp_code: str


class MfaChallengeResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
