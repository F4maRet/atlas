from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://atlas_user:atlas_pass@db:5432/atlas"
    SECRET_KEY: str = "change-me"
    UPLOAD_DIR: str = "/app/uploads"
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_ORIGINS: List[str] = ["http://localhost", "http://localhost:80", "http://localhost:5173"]

    # Единый пароль на вход в систему (простая защита без ролей).
    # ОБЯЗАТЕЛЬНО смените в .env перед боевым использованием.
    ADMIN_PASSWORD: str = "change-me"
    # Ставить True, если система работает по HTTPS — тогда cookie сессии
    # будет передаваться только по защищённому соединению.
    COOKIE_SECURE: bool = False

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            # Поддерживаем как JSON-массив ["..."], так и строку через запятую
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
