import hmac

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE,
    client_ip,
    create_session_token,
    is_authenticated,
    login_limiter,
)

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(data: LoginRequest, request: Request, response: Response):
    ip = client_ip(request)
    login_limiter.check(ip)
    if not hmac.compare_digest(data.password.encode("utf-8"), settings.ADMIN_PASSWORD.encode("utf-8")):
        login_limiter.fail(ip)
        raise HTTPException(401, "Неверный пароль")
    login_limiter.reset(ip)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return {"status": "ok"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME, httponly=True, samesite="lax", secure=settings.COOKIE_SECURE)
    return {"status": "ok"}


@router.get("/check")
async def check(request: Request):
    return {"authenticated": is_authenticated(request)}
