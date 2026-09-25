import logging
from contextlib import asynccontextmanager

import sqlalchemy as sa
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.security import is_authenticated
from app.db.migrate import mark_once, run_migrations
from app.db.session import AsyncSessionLocal, engine
from app.services.file_service import IMAGE_EXT, ensure_dirs, file_ext

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("atlas")

CONCLUSION_TEMPLATE_NAME = "Заключение об открытом опубликовании"


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    * /uploads отдаётся StaticFiles, мимо Depends() — поэтому проверка сессии здесь.
      Напрямую отдаются только изображения (обложки сборников/конференций):
      документы доступны лишь через API, где они распаковываются и получают
      правильный Content-Disposition. Это же не даёт отдать загруженный .html
      как страницу с того же origin (stored XSS).
    * Базовые защитные заголовки для всех ответов.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/uploads/"):
            if not is_authenticated(request):
                return JSONResponse({"detail": "Требуется вход в систему"}, status_code=401)
            if file_ext(request.url.path) not in IMAGE_EXT:
                return JSONResponse({"detail": "Не найдено"}, status_code=404)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        return response


async def _seed_conclusion_template() -> None:
    """
    Один раз регистрирует встроенный шаблон заключения в «Шаблонах документов».
    Раньше это делалось при каждом старте — удалённый пользователем шаблон
    появлялся снова. Теперь факт посева запоминается в schema_migrations.
    """
    from app.models.models import DocumentTemplate
    from app.services.conclusion_service import BUILTIN_TEMPLATE_PATH
    from app.services.file_service import copy_builtin

    if not await mark_once(engine, "seed:conclusion_template"):
        return
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(
            sa.select(DocumentTemplate).where(
                DocumentTemplate.doc_type == "conclusion", DocumentTemplate.name == CONCLUSION_TEMPLATE_NAME
            )
        )
        if existing and existing.file_path:
            return
        file_path = copy_builtin(BUILTIN_TEMPLATE_PATH, "templates") if BUILTIN_TEMPLATE_PATH.exists() else None
        if existing:
            existing.file_path = file_path
        else:
            db.add(DocumentTemplate(
                name=CONCLUSION_TEMPLATE_NAME,
                doc_type="conclusion",
                description="Официальный шаблон заключения. Используется при автоматической генерации документа для статьи.",
                file_path=file_path,
                is_active=True,
            ))
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.warn_insecure()
    ensure_dirs()
    applied = await run_migrations(engine)
    if applied:
        logger.info("Применены миграции: %s", ", ".join(applied))
    await _seed_conclusion_template()
    yield
    await engine.dispose()


app = FastAPI(
    title="СНД «АТЛАС»",
    description="Автоматизированная система научной деятельности",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("IntegrityError: %s", exc.orig)
    return JSONResponse({"detail": "Операция нарушает целостность данных (дубликат или несуществующая ссылка)"},
                        status_code=409)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    msgs = []
    for err in exc.errors():
        field = ".".join(str(x) for x in err.get("loc", [])[1:]) or "запрос"
        msgs.append(f"{field}: {err.get('msg')}")
    return JSONResponse({"detail": "; ".join(msgs) or "Некорректный запрос"}, status_code=422)


ensure_dirs()
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return JSONResponse(
        {"status": "ok" if db_ok else "degraded", "database": db_ok, "service": "atlas-backend"},
        status_code=200 if db_ok else 503,
    )
