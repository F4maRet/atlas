from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json
import io

from app.db.session import get_db
from app.models.models import Article, Author, Collection
from app.schemas.schemas import ArticleCreate, ArticleOut
from app.services.file_service import save_file, read_file_bytes, delete_file
from app.services.preview_service import safe_content_disposition

router = APIRouter()


async def _load_article(db, article_id):
    result = await db.execute(
        select(Article)
        .options(
            selectinload(Article.authors),
            selectinload(Article.collection),
            selectinload(Article.conclusion),
            selectinload(Article.lead_author),
        )
        .where(Article.id == article_id)
    )
    return result.scalar_one_or_none()


@router.get("/", response_model=List[ArticleOut])
async def list_articles(
    collection_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    q = select(Article).options(
        selectinload(Article.authors),
        selectinload(Article.collection),
        selectinload(Article.conclusion),
        selectinload(Article.lead_author),
    )
    if collection_id:
        q = q.where(Article.collection_id == collection_id)
    result = await db.execute(q.order_by(Article.created_at.desc()))
    articles = result.scalars().all()
    out = []
    for a in articles:
        d = ArticleOut.model_validate(a).model_dump()
        d["has_conclusion"] = a.conclusion is not None
        out.append(d)
    return out


@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    a = await _load_article(db, article_id)
    if not a:
        raise HTTPException(404, "Article not found")
    d = ArticleOut.model_validate(a).model_dump()
    d["has_conclusion"] = a.conclusion is not None
    return d


@router.post("/", response_model=ArticleOut, status_code=201)
async def create_article(
    title: str = Form(...),
    article_type: Optional[str] = Form(None),
    collection_id: Optional[int] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: str = Form("[]"),
    lead_author_id: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    ids = json.loads(author_ids)

    # Загружаем авторов ДО создания объекта, передаём в конструктор —
    # это предотвращает lazy load в async-контексте
    authors = []
    for aid in ids:
        author = await db.get(Author, aid)
        if author:
            authors.append(author)

    article = Article(
        title=title,
        article_type=article_type,
        collection_id=collection_id,
        catalog=catalog,
        lead_author_id=lead_author_id if lead_author_id else None,
        authors=authors,  # инициализируем сразу, без append
    )
    if file and file.filename:
        meta = await save_file(file, "articles", compress=True)
        article.file_path = meta["file_path"]
        article.original_filename = meta["original_filename"]
        article.file_size_original = meta["file_size_original"]
        article.file_size_compressed = meta["file_size_compressed"]

    db.add(article)
    await db.commit()
    return await _load_article(db, article.id)


@router.put("/{article_id}", response_model=ArticleOut)
async def update_article(
    article_id: int,
    title: Optional[str] = Form(None),
    article_type: Optional[str] = Form(None),
    collection_id: Optional[int] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: Optional[str] = Form(None),
    lead_author_id: Optional[int] = Form(None),
    clear_lead_author: Optional[bool] = Form(False),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    article = await _load_article(db, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    if title is not None:
        article.title = title
    if article_type is not None:
        article.article_type = article_type
    if collection_id is not None:
        article.collection_id = collection_id
    if catalog is not None:
        article.catalog = catalog
    if clear_lead_author:
        article.lead_author_id = None
    elif lead_author_id is not None:
        article.lead_author_id = lead_author_id

    if file and file.filename:
        delete_file(article.file_path)
        meta = await save_file(file, "articles", compress=True)
        article.file_path = meta["file_path"]
        article.original_filename = meta["original_filename"]
        article.file_size_original = meta["file_size_original"]
        article.file_size_compressed = meta["file_size_compressed"]

    if author_ids is not None:
        ids = json.loads(author_ids)
        new_authors = []
        for aid in ids:
            author = await db.get(Author, aid)
            if author:
                new_authors.append(author)
        article.authors = new_authors

    await db.commit()
    return await _load_article(db, article_id)


@router.delete("/{article_id}", status_code=204)
async def delete_article(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    delete_file(article.file_path)
    delete_file(article.preview_path)
    await db.delete(article)
    await db.commit()


@router.get("/{article_id}/download")
async def download_article(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article or not article.file_path:
        raise HTTPException(404, "File not found")
    content = await read_file_bytes(article.file_path)
    filename = article.original_filename or "article.pdf"
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": safe_content_disposition("attachment", filename)},
    )


@router.get("/{article_id}/preview")
async def preview_article(article_id: int, db: AsyncSession = Depends(get_db)):
    """Serve file for in-browser preview. PDF inline, DOCX converted to HTML."""
    from app.services.preview_service import docx_to_html
    article = await db.get(Article, article_id)
    if not article or not article.file_path:
        raise HTTPException(404, "File not found")
    filename = article.original_filename or "file"
    name_lower = filename.lower()
    if name_lower.endswith(".docx"):
        html = docx_to_html(article.file_path)
        return Response(
            content=html.encode("utf-8"),
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": safe_content_disposition("inline", filename + ".html")},
        )
    elif name_lower.endswith(".pdf"):
        content = await read_file_bytes(article.file_path)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": safe_content_disposition("inline", filename)},
        )
    else:
        content = await read_file_bytes(article.file_path)
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": safe_content_disposition("attachment", filename)},
        )
