import hmac

from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import (
    create_session_token,
    verify_session_token,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE,
)

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(data: LoginRequest, response: Response):
    if not hmac.compare_digest(data.password, settings.ADMIN_PASSWORD):
        raise HTTPException(401, "Неверный пароль")

    token = create_session_token()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return {"status": "ok"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"status": "ok"}


@router.get("/check")
async def check(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return {"authenticated": verify_session_token(token or "")}
