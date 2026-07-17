from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.security import verify_session_token, SESSION_COOKIE_NAME
from app.db.session import engine
from app.db.base import Base
from app.api.v1.router import api_router


class UploadsAuthMiddleware(BaseHTTPMiddleware):
    """/uploads is served via StaticFiles, which bypasses FastAPI's Depends()
    system entirely — so the same session-cookie check used everywhere else
    has to be applied here separately, or uploaded files would stay world
    readable to anyone who can guess/observe a file path."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/uploads"):
            token = request.cookies.get(SESSION_COOKIE_NAME)
            if not verify_session_token(token or ""):
                return JSONResponse({"detail": "Требуется вход в систему"}, status_code=401)
        return await call_next(request)


async def _seed_conclusion_template():
    """
    Ensure the built-in conclusion template is registered in document_templates.
    If a row with doc_type='conclusion' and name='Заключение об открытом опубликовании' exists,
    do nothing. Otherwise copy the .docx into the uploads/templates directory and insert a row.
    """
    import shutil
    import sqlalchemy as sa
    from pathlib import Path
    from app.db.session import AsyncSessionLocal
    from app.models.models import DocumentTemplate

    builtin_src = Path("/app/backend/app/templates/conclusion_template.docx")
    # Also check relative path for dev environments
    fallback_src = Path(__file__).parent / "templates" / "conclusion_template.docx"
    src = builtin_src if builtin_src.exists() else fallback_src

    dest_dir = os.path.join(settings.UPLOAD_DIR, "templates")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "conclusion_template.docx")

    TEMPLATE_NAME = "Заключение об открытом опубликовании"

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            sa.select(DocumentTemplate).where(
                DocumentTemplate.doc_type == "conclusion",
                DocumentTemplate.name == TEMPLATE_NAME,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Make sure the physical file is in place (might have been lost on volume re-create)
            if src.exists() and not os.path.exists(dest):
                shutil.copy2(str(src), dest)
            return

        # Copy physical file
        if src.exists():
            shutil.copy2(str(src), dest)
            file_path = dest
        else:
            file_path = None

        tmpl = DocumentTemplate(
            name=TEMPLATE_NAME,
            doc_type="conclusion",
            description=(
                "Официальный шаблон заключения об открытом опубликовании. "
                "Используется при автоматической генерации документа для статьи."
            ),
            file_path=file_path,
            is_active=True,
        )
        db.add(tmpl)
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create upload dirs
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    for subdir in ["articles", "proposals", "software", "documents", "previews", "templates"]:
        os.makedirs(os.path.join(settings.UPLOAD_DIR, subdir), exist_ok=True)

    # Run safe schema patches (idempotent — every statement uses IF NOT EXISTS).
    #
    # init.sql only runs once, when Postgres creates a brand-new data volume.
    # Deployments that already have data won't see new columns/tables added to
    # init.sql later — so every patch file below is also re-applied on every
    # startup, which keeps existing installations in sync without recreating
    # the volume. (This is also what backfills schema that earlier versions
    # of init.sql were missing entirely — see migrations/add_*.sql.)
    from app.db.session import engine
    from pathlib import Path
    import sqlalchemy as sa
    import logging

    migrations_dir = Path(__file__).parent.parent / "migrations"
    patch_files = [
        "add_lead_author.sql",
        "add_certificates.sql",
        "add_conference_participants.sql",
        "add_conclusion_filename.sql",
    ]

    async with engine.begin() as conn:
        for fname in patch_files:
            fpath = migrations_dir / fname
            if not fpath.exists():
                continue
            sql_text = fpath.read_text(encoding="utf-8")
            for raw_statement in sql_text.split(";"):
                # strip SQL line comments before checking if anything is left
                lines = [l for l in raw_statement.splitlines() if not l.strip().startswith("--")]
                statement = "\n".join(lines).strip()
                if not statement:
                    continue
                try:
                    await conn.execute(sa.text(statement))
                except Exception as e:
                    logging.warning(f"Migration patch skipped ({fname}): {e}")

    # Seed built-in conclusion template into document_templates if absent
    await _seed_conclusion_template()

    yield
    # Shutdown


app = FastAPI(
    title="СНД «АТЛАС»",
    description="Автоматизированная система научной деятельности",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(UploadsAuthMiddleware)

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "atlas-backend"}
