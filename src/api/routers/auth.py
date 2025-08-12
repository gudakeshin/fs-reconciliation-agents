"""
Authentication router for FS Reconciliation Agents API.

Provides a token endpoint to obtain JWTs for authenticated requests.
This uses the in-memory user store defined in security utilities.
"""

from datetime import timedelta
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.utils.security_utils.authentication import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    fake_users_db,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/token")
async def login_for_access_token(payload: LoginRequest) -> Dict[str, Any]:
    """Issue a JWT access token for valid credentials."""
    user = authenticate_user(fake_users_db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": str(access_token), "token_type": "bearer"}


