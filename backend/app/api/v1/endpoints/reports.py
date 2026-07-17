from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.models.models import Article, Proposal, Software, Collection
from app.schemas.schemas import PublicationPlanItem

router = APIRouter()


@router.get("/publication-plan", response_model=List[PublicationPlanItem])
async def publication_plan(db: AsyncSession = Depends(get_db)):
    items: List[PublicationPlanItem] = []

    # Articles
    r = await db.execute(
        select(Article).options(selectinload(Article.authors), selectinload(Article.collection))
        .order_by(Article.created_at.desc())
    )
    for a in r.scalars().all():
        items.append(PublicationPlanItem(
            type="article",
            id=a.id,
            title=a.title,
            authors=[au.full_name for au in a.authors],
            collection_name=a.collection.name if a.collection else None,
            created_at=a.created_at,
        ))

    # Proposals
    r = await db.execute(
        select(Proposal).options(selectinload(Proposal.authors))
        .order_by(Proposal.created_at.desc())
    )
    for p in r.scalars().all():
        items.append(PublicationPlanItem(
            type="proposal",
            id=p.id,
            title=p.title,
            authors=[au.full_name for au in p.authors],
            collection_name=None,
            created_at=p.created_at,
        ))

    # Software
    r = await db.execute(
        select(Software).options(selectinload(Software.authors))
        .order_by(Software.created_at.desc())
    )
    for s in r.scalars().all():
        items.append(PublicationPlanItem(
            type="software",
            id=s.id,
            title=s.title,
            authors=[au.full_name for au in s.authors],
            collection_name=None,
            created_at=s.created_at,
        ))

    return items


@router.get("/collections-list")
async def collections_list(db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Collection).options(selectinload(Collection.articles))
        .order_by(Collection.date_start.desc().nullslast())
    )
    cols = r.scalars().all()
    from datetime import date
    today = date.today()
    result = []
    for c in cols:
        result.append({
            "id": c.id,
            "name": c.name,
            "university": c.university,
            "date_start": c.date_start.isoformat() if c.date_start else None,
            "date_end": c.date_end.isoformat() if c.date_end else None,
            "url": c.url,
            "is_past": (c.date_end < today) if c.date_end else None,
            "articles_count": len(c.articles),
            "articles": [{"id": a.id, "title": a.title} for a in c.articles],
        })
    return result


@router.get("/dashboard")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    articles_count = await db.scalar(select(func.count()).select_from(Article))
    proposals_count = await db.scalar(select(func.count()).select_from(Proposal))
    software_count = await db.scalar(select(func.count()).select_from(Software))
    collections_count = await db.scalar(select(func.count()).select_from(Collection))
    from app.models.models import Author, Conference
    authors_count = await db.scalar(select(func.count()).select_from(Author))
    conferences_count = await db.scalar(select(func.count()).select_from(Conference))
    return {
        "articles": articles_count,
        "proposals": proposals_count,
        "software": software_count,
        "collections": collections_count,
        "authors": authors_count,
        "conferences": conferences_count,
    }
