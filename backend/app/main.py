from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
from app.api.v1.router import api_router


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

    # Run safe migrations (idempotent ALTER TABLE IF NOT EXISTS)
    from app.db.session import engine
    import sqlalchemy as sa
    migrations = [
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS lead_author_id INTEGER REFERENCES authors(id) ON DELETE SET NULL",
    ]
    async with engine.begin() as conn:
        for sql in migrations:
            try:
                await conn.execute(sa.text(sql))
            except Exception as e:
                import logging
                logging.warning(f"Migration skipped: {e}")

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

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "atlas-backend"}
