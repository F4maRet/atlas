from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.api.common import clean_str, commit_and_cleanup, has_upload, parse_opt_int, replace_file
from app.db.session import get_db
from app.models.models import Article, Conclusion, DocumentTemplate
from app.schemas.schemas import ConclusionOut
from app.services.conclusion_service import conclusion_filename, generate_conclusion as gen_doc
from app.services.file_service import DOC_EXT, IMAGE_EXT, delete_file, file_ext, read_file_bytes, save_bytes
from app.services.preview_service import download_response, preview_response

router = APIRouter()


async def _get_conclusion(db: AsyncSession, article_id: int, need_file: bool = False) -> Conclusion:
    c = await db.scalar(select(Conclusion).where(Conclusion.article_id == article_id))
    if not c or (need_file and not c.file_path):
        raise HTTPException(404, "Заключение не найдено")
    return c


async def _article(db: AsyncSession, article_id: int) -> Article:
    a = await db.scalar(
        select(Article).options(selectinload(Article.authors), selectinload(Article.conclusion))
        .where(Article.id == article_id)
    )
    if not a:
        raise HTTPException(404, "Статья не найдена")
    return a


def _lead_name(article: Article) -> Optional[str]:
    lead = next((a for a in article.authors if a.id == article.lead_author_id), None)
    lead = lead or (article.authors[0] if article.authors else None)
    return lead.full_name if lead else None


@router.get("/conclusion/{article_id}", response_model=ConclusionOut)
async def get_conclusion(article_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_conclusion(db, article_id)


@router.post("/conclusion/{article_id}", response_model=ConclusionOut, status_code=201)
async def upload_conclusion(
    article_id: int,
    notes: Optional[str] = Form(None),
    template_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Прикрепить своё заключение (файл и/или примечание). Заменяет существующее."""
    article = await _article(db, article_id)
    if not has_upload(file) and not clean_str(notes):
        raise HTTPException(400, "Прикрепите файл или укажите примечание")
    c = article.conclusion or Conclusion(article_id=article_id)
    if article.conclusion is None:
        db.add(c)
    old = None
    if has_upload(file):
        old = await replace_file(c, file, "documents", DOC_EXT | IMAGE_EXT,
                                 fields=("file_path", "original_filename"))
    c.notes = clean_str(notes)
    c.template_id = parse_opt_int(template_id, "template_id")
    c.generated_from_template = False
    await commit_and_cleanup(db, old)
    await db.refresh(c)
    return c


@router.delete("/conclusion/{article_id}", status_code=204)
async def delete_conclusion(article_id: int, db: AsyncSession = Depends(get_db)):
    c = await _get_conclusion(db, article_id)
    path = c.file_path
    await db.delete(c)
    await commit_and_cleanup(db, path)


async def _resolve_template(db: AsyncSession, template_id: Optional[int]) -> Optional[DocumentTemplate]:
    """Явно выбранный шаблон > последний активный шаблон заключения с файлом > встроенный."""
    if template_id:
        tmpl = await db.get(DocumentTemplate, template_id)
        if not tmpl:
            raise HTTPException(404, "Шаблон не найден")
        if tmpl.doc_type != "conclusion":
            raise HTTPException(400, "Выбранный шаблон не является шаблоном заключения")
        return tmpl
    return await db.scalar(
        select(DocumentTemplate)
        .where(DocumentTemplate.doc_type == "conclusion", DocumentTemplate.is_active.is_(True),
               DocumentTemplate.file_path.isnot(None))
        .order_by(DocumentTemplate.id.desc()).limit(1)
    )


@router.post("/conclusion/{article_id}/generate", response_model=ConclusionOut, status_code=201)
async def generate_conclusion(article_id: int, template_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    """Сформировать DOCX-заключение по шаблону (подставляются название, авторы, дата)."""
    article = await _article(db, article_id)
    tmpl = await _resolve_template(db, template_id)

    template_bytes = None
    if tmpl and tmpl.file_path:
        if file_ext(tmpl.file_path.removesuffix(".gz")) != ".docx":
            raise HTTPException(400, "Файл шаблона должен быть в формате DOCX")
        template_bytes = await read_file_bytes(tmpl.file_path)

    upload_date = article.created_at or datetime.now()
    try:
        docx_bytes = await run_in_threadpool(
            gen_doc,
            article_title=article.title,
            author_names=[a.full_name for a in article.authors],
            upload_date=upload_date,
            lead_author_name=_lead_name(article),
            template_bytes=template_bytes,
        )
    except Exception:
        raise HTTPException(400, "Не удалось заполнить шаблон: файл шаблона повреждён или не является DOCX")

    filename = conclusion_filename(_lead_name(article), upload_date)
    meta = await save_bytes(docx_bytes, filename, "documents")

    c = article.conclusion or Conclusion(article_id=article_id)
    if article.conclusion is None:
        db.add(c)
    old = c.file_path
    c.file_path = meta["file_path"]
    c.original_filename = filename
    c.notes = "Сформировано автоматически по шаблону"
    c.generated_from_template = True
    c.template_id = tmpl.id if tmpl else None
    try:
        await commit_and_cleanup(db, old)
    except Exception:
        delete_file(meta["file_path"])
        raise
    await db.refresh(c)
    return c


async def _download(db: AsyncSession, article_id: int):
    c = await _get_conclusion(db, article_id, need_file=True)
    filename = c.original_filename
    if not filename:  # старые сгенерированные записи — без имени файла
        article = await _article(db, article_id)
        ext = file_ext(c.file_path.removesuffix(".gz")) or ".docx"
        filename = conclusion_filename(_lead_name(article), article.created_at).removesuffix(".docx") + ext
    return download_response(c.file_path, filename)


@router.get("/conclusion/{article_id}/download")
async def download_conclusion(article_id: int, db: AsyncSession = Depends(get_db)):
    return await _download(db, article_id)


@router.get("/conclusion/{article_id}/download-generated")
async def download_generated_conclusion(article_id: int, db: AsyncSession = Depends(get_db)):
    """Совместимость со старым клиентом (раньше отдавал любой файл как .docx)."""
    return await _download(db, article_id)


@router.get("/conclusion/{article_id}/preview")
async def preview_conclusion(article_id: int, db: AsyncSession = Depends(get_db)):
    c = await _get_conclusion(db, article_id, need_file=True)
    return await preview_response(c.file_path, c.original_filename or "conclusion.docx")
