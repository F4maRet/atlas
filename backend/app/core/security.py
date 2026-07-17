"""
Простая защита доступа единым паролем.

Раньше в проекте не было НИКАКОЙ аутентификации — любой, кто мог достучаться
до backend по сети, мог создавать/удалять/скачивать что угодно. Здесь — без
пользователей и ролей, просто общий пароль на вход и подписанная cookie-сессия,
как договорились. Полноценную авторизацию с ролями (кандидат/делегат/руководитель)
можно добавить позже отдельным слоем поверх этого.

Токен сессии: "<unix_ts_истечения>.<hmac_sha256(SECRET_KEY, ts)>"
Подпись не даёт подделать/продлить cookie, не зная SECRET_KEY.
"""
import hmac
import hashlib
import time

from fastapi import Request, HTTPException, status

from app.core.config import settings

SESSION_COOKIE_NAME = "atlas_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 дней


def _sign(payload: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token() -> str:
    expires_at = int(time.time()) + SESSION_MAX_AGE
    payload = str(expires_at)
    return f"{payload}.{_sign(payload)}"


def verify_session_token(token: str) -> bool:
    if not token or "." not in token:
        return False
    payload, _, signature = token.rpartition(".")
    if not signature or not hmac.compare_digest(signature, _sign(payload)):
        return False
    try:
        expires_at = int(payload)
    except ValueError:
        return False
    return expires_at > int(time.time())


async def require_auth(request: Request) -> None:
    """FastAPI dependency — подключается к защищённым роутерам."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not verify_session_token(token or ""):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход в систему")
