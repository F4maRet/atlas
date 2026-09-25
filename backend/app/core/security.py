"""
Простая защита доступа единым паролем.

Без пользователей и ролей: общий пароль на вход и подписанная cookie-сессия.
Полноценную авторизацию с ролями можно добавить позже отдельным слоем.

Токен сессии: "<unix_ts_истечения>.<hmac_sha256(ключ, ts)>".
Ключ подписи зависит и от SECRET_KEY, и от ADMIN_PASSWORD — поэтому смена
пароля в .env сразу завершает все ранее выданные сессии.
"""
import hashlib
import hmac
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

SESSION_COOKIE_NAME = "atlas_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 дней


def _signing_key() -> bytes:
    return hashlib.sha256(f"{settings.SECRET_KEY}\x00{settings.ADMIN_PASSWORD}".encode("utf-8")).digest()


def _sign(payload: str) -> str:
    return hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token() -> str:
    payload = str(int(time.time()) + SESSION_MAX_AGE)
    return f"{payload}.{_sign(payload)}"


def verify_session_token(token: str) -> bool:
    if not token or "." not in token:
        return False
    payload, _, signature = token.rpartition(".")
    if not signature or not hmac.compare_digest(signature, _sign(payload)):
        return False
    try:
        return int(payload) > int(time.time())
    except ValueError:
        return False


def is_authenticated(request: Request) -> bool:
    return verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")


async def require_auth(request: Request) -> None:
    """FastAPI dependency — подключается к защищённым роутерам."""
    if not is_authenticated(request):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход в систему")


class LoginRateLimiter:
    """Ограничение неудачных попыток входа по IP (в памяти процесса)."""

    def __init__(self):
        self._failures: dict[str, deque] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque:
        q = self._failures[key]
        while q and now - q[0] > settings.LOGIN_WINDOW_SECONDS:
            q.popleft()
        return q

    def check(self, key: str) -> None:
        now = time.time()
        q = self._prune(key, now)
        if len(q) >= settings.LOGIN_MAX_ATTEMPTS:
            retry = int(settings.LOGIN_WINDOW_SECONDS - (now - q[0])) + 1
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Слишком много неудачных попыток. Повторите через {retry} с.",
                headers={"Retry-After": str(retry)},
            )

    def fail(self, key: str) -> None:
        self._failures[key].append(time.time())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


login_limiter = LoginRateLimiter()


def client_ip(request: Request) -> str:
    # За nginx реальный адрес приходит в X-Real-IP (см. frontend/nginx.conf)
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
