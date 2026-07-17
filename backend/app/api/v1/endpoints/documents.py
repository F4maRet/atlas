from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.session import get_db
from app.models.models import Conclusion, Article, DocumentTemplate
from app.schemas.schemas import ConclusionOut
from app.services.file_service import save_file, read_file_bytes, delete_file
from app.services.preview_service import safe_content_disposition

router = APIRouter()


@router.get("/conclusion/{article_id}", response_model=ConclusionOut)
async def get_conclusion(article_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Conclusion).where(Conclusion.article_id == article_id))
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Conclusion not found")
    return c


@router.post("/conclusion/{article_id}", response_model=ConclusionOut, status_code=201)
async def upload_conclusion(
    article_id: int,
    notes: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    # Remove existing
    r = await db.execute(select(Conclusion).where(Conclusion.article_id == article_id))
    existing = r.scalar_one_or_none()
    if existing:
        delete_file(existing.file_path)
        await db.delete(existing)
        await db.flush()

    c = Conclusion(
        article_id=article_id,
        notes=notes,
        template_id=template_id,
        generated_from_template=template_id is not None,
    )
    if file and file.filename:
        meta = await save_file(file, "documents", compress=True)
        c.file_path = meta["file_path"]
        c.original_filename = meta["original_filename"]
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/conclusion/{article_id}", status_code=204)
async def delete_conclusion(article_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Conclusion).where(Conclusion.article_id == article_id))
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Not found")
    delete_file(c.file_path)
    await db.delete(c)
    await db.commit()


@router.get("/conclusion/{article_id}/download")
async def download_conclusion(article_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Conclusion).where(Conclusion.article_id == article_id))
    c = r.scalar_one_or_none()
    if not c or not c.file_path:
        raise HTTPException(404, "File not found")
    content = await read_file_bytes(c.file_path)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": safe_content_disposition("attachment", c.original_filename or "conclusion.docx")},
    )


@router.post("/conclusion/{article_id}/generate", response_model=ConclusionOut, status_code=201)
async def generate_conclusion(
    article_id: int,
    template_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-generate a conclusion DOCX.
    If template_id is provided — use that specific template.
    Otherwise use the latest active conclusion template from document_templates.
    Falls back to built-in template if none found.
    """
    from sqlalchemy.orm import selectinload
    from app.services.conclusion_service import generate_conclusion as gen_doc
    from pathlib import Path
    import gzip, uuid, os
    from app.core.config import settings

    # Load article with authors and lead_author
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.authors), selectinload(Article.lead_author))
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    author_names = [a.full_name for a in article.authors]
    lead_author_name = article.lead_author.full_name if article.lead_author else None

    from datetime import datetime
    upload_date = article.created_at or datetime.utcnow()

    # Resolve template: explicit id > latest active > None (builtin)
    if template_id:
        tmpl = await db.get(DocumentTemplate, template_id)
        if not tmpl:
            raise HTTPException(404, f"Template {template_id} not found")
    else:
        tmpl_result = await db.execute(
            select(DocumentTemplate)
            .where(
                DocumentTemplate.doc_type == "conclusion",
                DocumentTemplate.is_active == True,
            )
            .order_by(DocumentTemplate.id.desc())
            .limit(1)
        )
        tmpl = tmpl_result.scalar_one_or_none()
    used_template_id = tmpl.id if tmpl else None

    # Determine physical template path
    template_path = None
    if tmpl and tmpl.file_path:
        fp = tmpl.file_path
        # Strip .gz if needed — conclusion_service needs raw .docx
        if fp.endswith(".gz"):
            import tempfile
            raw = gzip.open(fp, "rb").read()
            tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
            tmp.write(raw)
            tmp.close()
            template_path = Path(tmp.name)
        else:
            template_path = Path(fp) if os.path.exists(fp) else None

    # Generate DOCX bytes
    docx_bytes = gen_doc(
        article_title=article.title,
        author_names=author_names,
        upload_date=upload_date,
        lead_author_name=lead_author_name,
        template_path=template_path,
    )

    # Clean up temp file if created
    if template_path and str(template_path).startswith("/tmp"):
        try:
            os.unlink(str(template_path))
        except OSError:
            pass

    # Save compressed
    subdir = "documents"
    os.makedirs(os.path.join(settings.UPLOAD_DIR, subdir), exist_ok=True)
    uid = uuid.uuid4().hex[:12]
    gz_path = os.path.join(settings.UPLOAD_DIR, subdir, f"{uid}.docx.gz")
    with gzip.open(gz_path, "wb", compresslevel=6) as f:
        f.write(docx_bytes)

    # Remove existing conclusion if any
    r = await db.execute(select(Conclusion).where(Conclusion.article_id == article_id))
    existing = r.scalar_one_or_none()
    if existing:
        delete_file(existing.file_path)
        await db.delete(existing)
        await db.flush()

    c = Conclusion(
        article_id=article_id,
        notes="Сгенерировано автоматически по шаблону",
        generated_from_template=True,
        template_id=used_template_id,
        file_path=gz_path,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@router.get("/conclusion/{article_id}/download-generated")
async def download_generated_conclusion(article_id: int, db: AsyncSession = Depends(get_db)):
    """Download the auto-generated conclusion DOCX with smart filename."""
    from sqlalchemy.orm import selectinload
    from app.services.conclusion_service import abbreviate_name

    result = await db.execute(
        select(Article)
        .options(selectinload(Article.lead_author), selectinload(Article.authors))
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    r = await db.execute(select(Conclusion).where(Conclusion.article_id == article_id))
    c = r.scalar_one_or_none()
    if not c or not c.file_path:
        raise HTTPException(404, "File not found")
    content = await read_file_bytes(c.file_path)

    # Build smart filename: Заключение_Лаукарт_М.С._2026-04-12.docx
    if article:
        lead = article.lead_author or (article.authors[0] if article.authors else None)
        if lead:
            abbr = abbreviate_name(lead.full_name).replace(" ", "_").replace(".", "")
        else:
            abbr = ""
        upload_date = article.created_at
        date_str = upload_date.strftime("%Y-%m-%d") if upload_date else ""
        parts = ["Заключение"]
        if abbr:
            parts.append(abbr)
        if date_str:
            parts.append(date_str)
        filename = "_".join(parts) + ".docx"
    else:
        filename = "Заключение_об_открытом_опубликовании.docx"

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": safe_content_disposition("attachment", filename)},
    )
