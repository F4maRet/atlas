import json
import logging
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("atlas")

INSECURE_DEFAULTS = {"change-me", "change-me-in-production-very-long-secret-key",
                     "change-me-strong-password", "change-me-to-very-long-random-secret-key-in-production"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://atlas_user:atlas_pass@db:5432/atlas"
    SECRET_KEY: str = "change-me"
    UPLOAD_DIR: str = "/app/uploads"
    MAX_FILE_SIZE_MB: int = 100
    # Строка через запятую или JSON-массив. Хранится строкой: pydantic-settings
    # пытается декодировать List[str] из env как JSON и падал на значении
    # "http://localhost,http://localhost:80" из docker-compose — backend не стартовал.
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:80,http://localhost:5173"

    # Единый пароль на вход в систему (простая защита без ролей).
    # ОБЯЗАТЕЛЬНО смените в .env перед боевым использованием.
    ADMIN_PASSWORD: str = "change-me"
    # True, если система работает по HTTPS — cookie сессии пойдёт только по защищённому каналу.
    COOKIE_SECURE: bool = False

    # Защита от подбора пароля: не более N неудачных попыток с одного IP за окно
    LOGIN_MAX_ATTEMPTS: int = 10
    LOGIN_WINDOW_SECONDS: int = 300

    @property
    def allowed_origins(self) -> List[str]:
        v = self.ALLOWED_ORIGINS.strip()
        if v.startswith("["):
            return [str(i).strip() for i in json.loads(v) if str(i).strip()]
        return [i.strip() for i in v.split(",") if i.strip()]

    @property
    def max_file_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    def warn_insecure(self) -> None:
        if self.SECRET_KEY in INSECURE_DEFAULTS or len(self.SECRET_KEY) < 16:
            logger.warning("SECRET_KEY не задан или слишком короткий — смените его в .env!")
        if self.ADMIN_PASSWORD in INSECURE_DEFAULTS:
            logger.warning("ADMIN_PASSWORD имеет значение по умолчанию — смените его в .env!")


settings = Settings()
