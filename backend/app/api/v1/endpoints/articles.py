from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.common import (
    check_collection, clean_str, commit_and_cleanup, has_upload, load_authors, parse_ids,
    parse_opt_int, replace_file, require_str,
)
from app.db.session import get_db
from app.models.models import Article
from app.schemas.schemas import ArticleOut
from app.services.file_service import DOC_EXT, delete_file
from app.services.preview_service import download_response, preview_response

router = APIRouter()

_LOAD = (
    selectinload(Article.authors),
    selectinload(Article.collection),
    selectinload(Article.conclusion),
)


async def _load(db: AsyncSession, article_id: int) -> Article:
    a = await db.scalar(select(Article).options(*_LOAD).where(Article.id == article_id))
    if not a:
        raise HTTPException(404, "Статья не найдена")
    return a


def _normalize_lead(article: Article) -> None:
    """Главный автор должен быть среди авторов статьи."""
    if article.lead_author_id and article.lead_author_id not in {a.id for a in article.authors}:
        article.lead_author_id = None


@router.get("/", response_model=List[ArticleOut])
async def list_articles(collection_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    q = select(Article).options(*_LOAD).order_by(Article.created_at.desc())
    if collection_id:
        q = q.where(Article.collection_id == collection_id)
    return (await db.execute(q)).scalars().all()


@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    return await _load(db, article_id)


@router.post("/", response_model=ArticleOut, status_code=201)
async def create_article(
    title: str = Form(...),
    article_type: Optional[str] = Form(None),
    collection_id: Optional[str] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: str = Form("[]"),
    lead_author_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    col_id = parse_opt_int(collection_id, "collection_id")
    await check_collection(db, col_id)
    article = Article(
        title=require_str(title, "Название"),
        article_type=clean_str(article_type),
        collection_id=col_id,
        catalog=clean_str(catalog),
        lead_author_id=parse_opt_int(lead_author_id, "lead_author_id"),
        authors=await load_authors(db, parse_ids(author_ids)),
    )
    _normalize_lead(article)
    if has_upload(file):
        await replace_file(article, file, "articles", DOC_EXT)
    db.add(article)
    try:
        await db.commit()
    except Exception:
        delete_file(article.file_path)
        raise
    return await _load(db, article.id)


@router.put("/{article_id}", response_model=ArticleOut)
async def update_article(
    article_id: int,
    title: Optional[str] = Form(None),
    article_type: Optional[str] = Form(None),
    collection_id: Optional[str] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: Optional[str] = Form(None),
    lead_author_id: Optional[str] = Form(None),
    clear_lead_author: bool = Form(False),  # совместимость со старым клиентом
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    article = await _load(db, article_id)
    if title is not None:
        article.title = require_str(title, "Название")
    if article_type is not None:
        article.article_type = clean_str(article_type)
    if collection_id is not None:
        col_id = parse_opt_int(collection_id, "collection_id")
        await check_collection(db, col_id)
        article.collection_id = col_id
    if catalog is not None:
        article.catalog = clean_str(catalog)
    if author_ids is not None:
        article.authors = await load_authors(db, parse_ids(author_ids))
    if clear_lead_author:
        article.lead_author_id = None
    elif lead_author_id is not None:
        article.lead_author_id = parse_opt_int(lead_author_id, "lead_author_id")
    _normalize_lead(article)

    old_file = await replace_file(article, file, "articles", DOC_EXT) if has_upload(file) else None
    await commit_and_cleanup(db, old_file)
    db.expire_all()
    return await _load(db, article_id)


@router.delete("/{article_id}", status_code=204)
async def delete_article(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await _load(db, article_id)
    # Файл заключения раньше оставался на диске «сиротой» после удаления статьи
    paths = [article.file_path, article.preview_path, article.conclusion.file_path if article.conclusion else None]
    await db.delete(article)
    await commit_and_cleanup(db, *paths)


@router.get("/{article_id}/download")
async def download_article(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article or not article.file_path:
        raise HTTPException(404, "Файл не найден")
    return download_response(article.file_path, article.original_filename or "article")


@router.get("/{article_id}/preview")
async def preview_article(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article or not article.file_path:
        raise HTTPException(404, "Файл не найден")
    return await preview_response(article.file_path, article.original_filename or "file")
