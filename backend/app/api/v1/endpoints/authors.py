from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, insert, literal_column, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import (
    Article, Author, Conference, Proposal, Software,
    article_authors, conference_participants, proposal_authors, software_authors,
)
from app.schemas.schemas import AuthorCreate, AuthorMerge, AuthorOut, AuthorStats, AuthorUpdate, AuthorWorks
from app.services.conclusion_service import abbreviate_name

router = APIRouter()

# (таблица связи, колонка-владелец, ключ в статистике)
LINKS = (
    (article_authors, article_authors.c.article_id, "articles_count"),
    (proposal_authors, proposal_authors.c.proposal_id, "proposals_count"),
    (software_authors, software_authors.c.software_id, "software_count"),
    (conference_participants, conference_participants.c.conference_id, "conferences_count"),
)


async def _get(db: AsyncSession, author_id: int) -> Author:
    a = await db.get(Author, author_id)
    if not a:
        raise HTTPException(404, "Автор не найден")
    return a


async def _check_unique(db: AsyncSession, name: str, exclude_id: int | None = None) -> Author | None:
    q = select(Author).where(func.lower(Author.full_name) == name.lower())
    if exclude_id:
        q = q.where(Author.id != exclude_id)
    return await db.scalar(q)


@router.get("/", response_model=List[AuthorOut])
async def list_authors(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Author).order_by(Author.full_name))).scalars().all()


@router.get("/stats", response_model=List[AuthorStats])
async def authors_stats(db: AsyncSession = Depends(get_db)):
    """Оценочная ведомость. Раньше — 3 запроса на каждого автора, теперь — один."""
    q = select(Author)
    subs = []
    for table, _, key in LINKS:
        sub = (select(table.c.author_id, func.count().label("n")).group_by(table.c.author_id).subquery())
        q = q.outerjoin(sub, sub.c.author_id == Author.id).add_columns(func.coalesce(sub.c.n, 0).label(key))
        subs.append(key)
    rows = (await db.execute(q)).all()
    stats = []
    for row in rows:
        counts = {k: row._mapping[k] for k in subs}
        stats.append(AuthorStats(
            **AuthorOut.model_validate(row[0]).model_dump(),
            **counts,
            total=counts["articles_count"] + counts["proposals_count"] + counts["software_count"],
        ))
    return sorted(stats, key=lambda s: (-s.total, -s.conferences_count, s.full_name))


@router.get("/{author_id}", response_model=AuthorOut)
async def get_author(author_id: int, db: AsyncSession = Depends(get_db)):
    return await _get(db, author_id)


@router.get("/{author_id}/works", response_model=AuthorWorks)
async def author_works(author_id: int, db: AsyncSession = Depends(get_db)):
    """Все работы и участие автора — для карточки автора."""
    author = await _get(db, author_id)

    arts = await db.execute(
        select(Article.id, Article.title, Article.article_type, Article.created_at)
        .join(article_authors, article_authors.c.article_id == Article.id)
        .where(article_authors.c.author_id == author_id).order_by(Article.created_at.desc()))
    props = await db.execute(
        select(Proposal.id, Proposal.title, Proposal.proposal_type, Proposal.created_at)
        .join(proposal_authors, proposal_authors.c.proposal_id == Proposal.id)
        .where(proposal_authors.c.author_id == author_id).order_by(Proposal.created_at.desc()))
    sws = await db.execute(
        select(Software.id, Software.title, Software.software_type, Software.created_at)
        .join(software_authors, software_authors.c.software_id == Software.id)
        .where(software_authors.c.author_id == author_id).order_by(Software.created_at.desc()))
    confs = await db.execute(
        select(Conference.id, Conference.title, Conference.organizer, Conference.date_start)
        .join(conference_participants, conference_participants.c.conference_id == Conference.id)
        .where(conference_participants.c.author_id == author_id)
        .order_by(Conference.date_start.desc().nullslast()))

    def items(rows, kind):
        return [{"type": kind, "id": r[0], "title": r[1], "subtitle": r[2], "date": r[3]} for r in rows]

    return {
        "author": author,
        "articles": items(arts, "article"),
        "proposals": items(props, "proposal"),
        "software": items(sws, "software"),
        "conferences": items(confs, "conference"),
    }


@router.post("/", response_model=AuthorOut, status_code=201)
async def create_author(data: AuthorCreate, db: AsyncSession = Depends(get_db)):
    if not data.full_name:
        raise HTTPException(400, "ФИО не может быть пустым")
    existing = await _check_unique(db, data.full_name)
    if existing:
        # Возвращаем существующего автора вместо ошибки (для AuthorPicker)
        return existing
    author = Author(**data.model_dump())
    if not author.short_name:
        author.short_name = abbreviate_name(author.full_name)
    db.add(author)
    await db.commit()
    await db.refresh(author)
    return author


@router.put("/{author_id}", response_model=AuthorOut)
async def update_author(author_id: int, data: AuthorUpdate, db: AsyncSession = Depends(get_db)):
    author = await _get(db, author_id)
    values = data.model_dump(exclude_unset=True)
    if "full_name" in values:
        if not values["full_name"]:
            raise HTTPException(400, "ФИО не может быть пустым")
        if await _check_unique(db, values["full_name"], exclude_id=author_id):
            raise HTTPException(409, f"Автор «{values['full_name']}» уже существует. "
                                     f"Чтобы свести дубли, используйте объединение авторов.")
    for k, v in values.items():
        setattr(author, k, v)
    if not author.short_name:
        author.short_name = abbreviate_name(author.full_name)
    await db.commit()
    await db.refresh(author)
    return author


@router.post("/{author_id}/merge", response_model=AuthorOut)
async def merge_authors(author_id: int, data: AuthorMerge, db: AsyncSession = Depends(get_db)):
    """
    Объединить дубль с основной записью: все статьи, рац. предложения, ПО
    и участия в конференциях переходят к автору into_id, дубль удаляется.
    """
    if author_id == data.into_id:
        raise HTTPException(400, "Нельзя объединить автора с самим собой")
    source = await _get(db, author_id)
    target = await _get(db, data.into_id)

    for table, owner_col, _ in LINKS:
        # Переносим связи, которых у основного автора ещё нет
        already = select(owner_col).where(table.c.author_id == target.id)
        await db.execute(
            insert(table).from_select(
                [owner_col.name, "author_id"],
                select(owner_col, literal_column(str(target.id)))
                .where(table.c.author_id == source.id, owner_col.not_in(already)),
            )
        )
        await db.execute(delete(table).where(table.c.author_id == source.id))
    await db.execute(update(Article).where(Article.lead_author_id == source.id).values(lead_author_id=target.id))
    for field in ("email", "organization", "position"):
        if not getattr(target, field) and getattr(source, field):
            setattr(target, field, getattr(source, field))
    await db.delete(source)
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/{author_id}", status_code=204)
async def delete_author(author_id: int, db: AsyncSession = Depends(get_db)):
    author = await _get(db, author_id)
    await db.delete(author)
    await db.commit()
