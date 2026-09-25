from datetime import date, datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.common import parse_date
from app.api.v1.endpoints.authors import authors_stats
from app.api.v1.endpoints.software import SOFTWARE_DOC_TYPES
from app.db.session import get_db
from app.models.models import (
    Article, Author, Collection, Conclusion, Conference, Proposal, Software, SoftwareDocument,
)
from app.schemas.schemas import PublicationPlanItem, SearchHit
from app.services.export_service import to_csv, to_docx
from app.services.preview_service import safe_content_disposition

router = APIRouter()

TYPE_LABELS = {"article": "Статья", "proposal": "Рац. предложение", "software": "ПО"}
MEDIA = {"csv": "text/csv; charset=utf-8",
         "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def _file(data: bytes, fmt: str, base: str) -> Response:
    name = f"{base}_{date.today():%Y-%m-%d}.{fmt}"
    return Response(data, media_type=MEDIA[fmt],
                    headers={"Content-Disposition": safe_content_disposition("attachment", name)})


# ── План публикаций ───────────────────────────────────────────────────────────

async def _plan(db: AsyncSession, type_: Optional[str], d_from: Optional[date], d_to: Optional[date]):
    items: List[PublicationPlanItem] = []

    def period(q, model):
        if d_from:
            q = q.where(func.date(model.created_at) >= d_from)
        if d_to:
            q = q.where(func.date(model.created_at) <= d_to)
        return q

    if type_ in (None, "article"):
        r = await db.execute(period(select(Article).options(
            selectinload(Article.authors), selectinload(Article.collection)), Article))
        items += [PublicationPlanItem(
            type="article", id=a.id, title=a.title, subtype=a.article_type,
            authors=[au.full_name for au in a.authors],
            collection_name=a.collection.name if a.collection else None, created_at=a.created_at,
        ) for a in r.scalars()]
    if type_ in (None, "proposal"):
        r = await db.execute(period(select(Proposal).options(selectinload(Proposal.authors)), Proposal))
        items += [PublicationPlanItem(
            type="proposal", id=p.id, title=p.title, subtype=p.proposal_type,
            authors=[au.full_name for au in p.authors], created_at=p.created_at,
        ) for p in r.scalars()]
    if type_ in (None, "software"):
        r = await db.execute(period(select(Software).options(selectinload(Software.authors)), Software))
        items += [PublicationPlanItem(
            type="software", id=s.id, title=s.title, subtype=s.software_type,
            authors=[au.full_name for au in s.authors], created_at=s.created_at,
        ) for s in r.scalars()]
    # Раньше записи шли блоками по типам; теперь — единая хронология
    return sorted(items, key=lambda i: i.created_at, reverse=True)


PlanType = Optional[Literal["article", "proposal", "software"]]


@router.get("/publication-plan", response_model=List[PublicationPlanItem])
async def publication_plan(
    type: PlanType = None, date_from: Optional[str] = None, date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await _plan(db, type, parse_date(date_from, "date_from"), parse_date(date_to, "date_to"))


@router.get("/publication-plan/export")
async def export_publication_plan(
    format: Literal["csv", "docx"] = "docx", type: PlanType = None,
    date_from: Optional[str] = None, date_to: Optional[str] = None, db: AsyncSession = Depends(get_db),
):
    d_from, d_to = parse_date(date_from, "date_from"), parse_date(date_to, "date_to")
    items = await _plan(db, type, d_from, d_to)
    headers = ["№", "Вид", "Название", "Тип", "Авторы", "Сборник", "Дата"]
    rows = [[i + 1, TYPE_LABELS[it.type], it.title, it.subtype or "", ", ".join(it.authors),
             it.collection_name or "", f"{it.created_at:%d.%m.%Y}"] for i, it in enumerate(items)]
    if format == "csv":
        return _file(to_csv(headers, rows), "csv", "План_публикаций")
    period = ""
    if d_from or d_to:
        period = f"за период {d_from:%d.%m.%Y} " if d_from else "за период "
        period += f"— {d_to:%d.%m.%Y}" if d_to else "— н.в."
    return _file(to_docx("План публикаций", headers, rows, subtitle=period,
                         col_widths_cm=[1, 2.5, 8, 2.5, 6, 4, 2.5]), "docx", "План_публикаций")


# ── Оценочная ведомость авторов ──────────────────────────────────────────────

@router.get("/authors-rating/export")
async def export_authors_rating(format: Literal["csv", "docx"] = "docx", db: AsyncSession = Depends(get_db)):
    stats = await authors_stats(db)
    headers = ["№", "ФИО", "Организация", "Статьи", "Рац. предл.", "ПО", "Конференции", "Итого"]
    rows = [[i + 1, s.full_name, s.organization or "", s.articles_count, s.proposals_count, s.software_count,
             s.conferences_count, s.total] for i, s in enumerate(stats)]
    if format == "csv":
        return _file(to_csv(headers, rows), "csv", "Оценочная_ведомость")
    return _file(to_docx("Оценочная ведомость авторов", headers, rows,
                         col_widths_cm=[1, 7, 7, 2, 2.5, 2, 2.5, 2]), "docx", "Оценочная_ведомость")


# ── Сборники ─────────────────────────────────────────────────────────────────

@router.get("/collections-list")
async def collections_list(db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Collection).options(selectinload(Collection.articles))
        .order_by(Collection.date_start.desc().nullslast())
    )
    return [{
        "id": c.id, "name": c.name, "university": c.university,
        "date_start": c.date_start, "date_end": c.date_end, "url": c.url, "is_past": c.is_past,
        "articles_count": len(c.articles),
        "articles": [{"id": a.id, "title": a.title} for a in sorted(c.articles, key=lambda a: a.title.lower())],
    } for c in r.scalars()]


@router.get("/collections-list/export")
async def export_collections(format: Literal["csv", "docx"] = "docx", db: AsyncSession = Depends(get_db)):
    cols = await collections_list(db)
    headers = ["№", "Сборник", "Организатор", "Сроки", "Статей", "Статьи"]
    rows = []
    for i, c in enumerate(cols):
        dates = " — ".join(f"{d:%d.%m.%Y}" for d in (c["date_start"], c["date_end"]) if d)
        rows.append([i + 1, c["name"], c["university"] or "", dates, c["articles_count"],
                     "; ".join(a["title"] for a in c["articles"])])
    if format == "csv":
        return _file(to_csv(headers, rows), "csv", "Сборники")
    return _file(to_docx("Список сборников", headers, rows, col_widths_cm=[1, 6, 5, 4, 1.8, 9]), "docx", "Сборники")


# ── Дашборд ──────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Всё для главной страницы одним запросом (раньше фронт скачивал все таблицы целиком)."""
    async def count(model, *where):
        return await db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    today = date.today()
    counts = {
        "articles": await count(Article), "proposals": await count(Proposal), "software": await count(Software),
        "collections": await count(Collection), "authors": await count(Author), "conferences": await count(Conference),
    }

    # Недавние добавления
    recent = []
    for model, kind in ((Article, "article"), (Proposal, "proposal"), (Software, "software")):
        r = await db.execute(select(model).options(selectinload(model.authors))
                             .order_by(model.created_at.desc()).limit(8))
        recent += [{"type": kind, "id": x.id, "title": x.title, "created_at": x.created_at,
                    "authors": [a.short_name or a.full_name for a in x.authors]} for x in r.scalars()]
    recent.sort(key=lambda x: x["created_at"], reverse=True)

    # Распределения по типам
    async def by_type(col):
        rows = (await db.execute(select(col, func.count()).group_by(col).order_by(func.count().desc()))).all()
        return [{"label": k or "Не указан", "count": v} for k, v in rows]

    # Конференции
    end = func.coalesce(Conference.date_end, Conference.date_start)
    upcoming = (await db.execute(
        select(Conference).where(end >= today).order_by(Conference.date_start).limit(5))).scalars().all()
    past = (await db.execute(
        select(Conference).where(end < today).order_by(Conference.date_start.desc()).limit(3))).scalars().all()

    def conf(c):
        return {"id": c.id, "title": c.title, "date_start": c.date_start, "date_end": c.date_end,
                "location": c.location, "is_online": c.is_online,
                "ongoing": bool(c.date_start and c.date_start <= today)}

    # Сборники с количеством статей
    col_rows = (await db.execute(
        select(Collection, func.count(Article.id))
        .outerjoin(Article, Article.collection_id == Collection.id)
        .group_by(Collection.id).order_by(Collection.date_start.desc().nullslast()).limit(5)
    )).all()

    # Что требует внимания
    no_conclusion = await count(Article, ~select(Conclusion.id).where(Conclusion.article_id == Article.id).exists())
    no_file = await count(Article, Article.file_path.is_(None))
    docs_per_sw = (select(SoftwareDocument.software_id, func.count().label("n"))
                   .group_by(SoftwareDocument.software_id).subquery())
    incomplete_sw = await db.scalar(
        select(func.count()).select_from(Software).outerjoin(docs_per_sw, docs_per_sw.c.software_id == Software.id)
        .where(func.coalesce(docs_per_sw.c.n, 0) < len(SOFTWARE_DOC_TYPES))) or 0

    top = (await authors_stats(db))[:6]
    return {
        **counts,
        "recent": recent[:8],
        "article_types": await by_type(Article.article_type),
        "proposal_types": await by_type(Proposal.proposal_type),
        "upcoming_conferences": [conf(c) for c in upcoming],
        "past_conferences": [conf(c) for c in past],
        "collections_list": [{"id": c.id, "name": c.name, "university": c.university, "articles_count": n,
                              "is_past": c.is_past} for c, n in col_rows],
        "top_authors": [a.model_dump() for a in top if a.total or a.conferences_count],
        "attention": {
            "articles_without_conclusion": no_conclusion,
            "articles_without_file": no_file,
            "software_incomplete_docs": incomplete_sw,
            "software_doc_types": len(SOFTWARE_DOC_TYPES),
        },
        "generated_at": datetime.now(),
    }


# ── Глобальный поиск ─────────────────────────────────────────────────────────

@router.get("/search", response_model=List[SearchHit])
async def global_search(q: str = Query(..., min_length=2), limit: int = Query(5, ge=1, le=20),
                        db: AsyncSession = Depends(get_db)):
    pattern = f"%{q.strip()}%"
    hits: List[SearchHit] = []

    async def run(model, kind, title_col, sub_col, *extra):
        cond = or_(title_col.ilike(pattern), *(c.ilike(pattern) for c in extra))
        rows = (await db.execute(select(model.id, title_col, sub_col).where(cond).limit(limit))).all()
        hits.extend(SearchHit(type=kind, id=r[0], title=r[1], subtitle=r[2]) for r in rows)

    await run(Article, "article", Article.title, Article.article_type, Article.catalog)
    await run(Proposal, "proposal", Proposal.title, Proposal.proposal_type, Proposal.catalog)
    await run(Software, "software", Software.title, Software.software_type, Software.catalog)
    await run(Author, "author", Author.full_name, Author.organization, Author.short_name, Author.email)
    await run(Collection, "collection", Collection.name, Collection.university)
    await run(Conference, "conference", Conference.title, Conference.organizer, Conference.location)

    # Работы, где автор совпал по ФИО
    for model, kind in ((Article, "article"), (Proposal, "proposal"), (Software, "software")):
        rows = (await db.execute(
            select(model.id, model.title).join(model.authors).where(Author.full_name.ilike(pattern))
            .distinct().limit(limit))).all()
        seen = {(h.type, h.id) for h in hits}
        hits.extend(SearchHit(type=kind, id=r[0], title=r[1], subtitle="по автору")
                    for r in rows if (kind, r[0]) not in seen)
    return hits
