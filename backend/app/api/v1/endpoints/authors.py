from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.db.session import get_db
from app.models.models import Author, article_authors, proposal_authors, software_authors
from app.schemas.schemas import AuthorCreate, AuthorUpdate, AuthorOut, AuthorStats

router = APIRouter()


@router.get("/", response_model=List[AuthorOut])
async def list_authors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Author).order_by(Author.full_name))
    return result.scalars().all()


@router.get("/stats", response_model=List[AuthorStats])
async def authors_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Author).order_by(Author.full_name))
    authors = result.scalars().all()
    stats = []
    for a in authors:
        art_count = await db.scalar(
            select(func.count()).select_from(article_authors).where(article_authors.c.author_id == a.id)
        ) or 0
        prop_count = await db.scalar(
            select(func.count()).select_from(proposal_authors).where(proposal_authors.c.author_id == a.id)
        ) or 0
        sw_count = await db.scalar(
            select(func.count()).select_from(software_authors).where(software_authors.c.author_id == a.id)
        ) or 0
        stats.append(AuthorStats(
            **AuthorOut.model_validate(a).model_dump(),
            articles_count=art_count,
            proposals_count=prop_count,
            software_count=sw_count,
            total=art_count + prop_count + sw_count,
        ))
    return sorted(stats, key=lambda x: x.total, reverse=True)


@router.get("/{author_id}", response_model=AuthorOut)
async def get_author(author_id: int, db: AsyncSession = Depends(get_db)):
    author = await db.get(Author, author_id)
    if not author:
        raise HTTPException(404, "Author not found")
    return author


@router.post("/", response_model=AuthorOut, status_code=201)
async def create_author(data: AuthorCreate, db: AsyncSession = Depends(get_db)):
    name = data.full_name.strip()
    if not name:
        raise HTTPException(400, "ФИО не может быть пустым")

    existing = await db.scalar(select(Author).where(
        func.lower(Author.full_name) == func.lower(name)
    ))
    if existing:
        # Возвращаем существующего автора вместо ошибки (для совместимости с AuthorPicker)
        return existing

    author = Author(**{**data.model_dump(), "full_name": name})
    db.add(author)
    await db.commit()
    await db.refresh(author)
    return author


@router.put("/{author_id}", response_model=AuthorOut)
async def update_author(author_id: int, data: AuthorUpdate, db: AsyncSession = Depends(get_db)):
    author = await db.get(Author, author_id)
    if not author:
        raise HTTPException(404, "Author not found")

    # Проверяем уникальность нового имени (исключая самого себя)
    if data.full_name:
        name = data.full_name.strip()
        duplicate = await db.scalar(select(Author).where(
            func.lower(Author.full_name) == func.lower(name),
            Author.id != author_id
        ))
        if duplicate:
            raise HTTPException(409, f"Автор с ФИО «{name}» уже существует")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(author, k, v if k != 'full_name' else v.strip())
    await db.commit()
    await db.refresh(author)
    return author


@router.delete("/{author_id}", status_code=204)
async def delete_author(author_id: int, db: AsyncSession = Depends(get_db)):
    author = await db.get(Author, author_id)
    if not author:
        raise HTTPException(404, "Author not found")
    await db.delete(author)
    await db.commit()
