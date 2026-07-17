from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date
import json

from app.db.session import get_db
from app.models.models import Conference, Author
from app.schemas.schemas import ConferenceOut
from app.services.file_service import save_file, delete_file

router = APIRouter()


async def _load(db: AsyncSession, cid: int):
    r = await db.execute(
        select(Conference)
        .options(selectinload(Conference.participants))
        .where(Conference.id == cid)
    )
    return r.scalar_one_or_none()


@router.get("/", response_model=List[ConferenceOut])
async def list_conferences(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Conference)
        .options(selectinload(Conference.participants))
        .order_by(Conference.date_start.asc().nullslast())
    )
    if date_from:
        q = q.where(Conference.date_start >= date.fromisoformat(date_from))
    if date_to:
        q = q.where(Conference.date_start <= date.fromisoformat(date_to))
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{cid}", response_model=ConferenceOut)
async def get_conference(cid: int, db: AsyncSession = Depends(get_db)):
    c = await _load(db, cid)
    if not c:
        raise HTTPException(404, "Conference not found")
    return c


@router.post("/", response_model=ConferenceOut, status_code=201)
async def create_conference(
    title: str = Form(...),
    organizer: Optional[str] = Form(None),
    date_start: Optional[str] = Form(None),
    date_end: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    is_online: bool = Form(False),
    participant_ids: str = Form("[]"),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    ids = json.loads(participant_ids)

    # Загружаем участников до добавления конференции в сессию
    participants = []
    for pid in ids:
        a = await db.get(Author, pid)
        if a:
            participants.append(a)

    c = Conference(
        title=title,
        organizer=organizer,
        date_start=date.fromisoformat(date_start) if date_start else None,
        date_end=date.fromisoformat(date_end) if date_end else None,
        url=url,
        description=description,
        location=location,
        is_online=is_online,
        source="manual",
        participants=participants,
    )
    if photo and photo.filename:
        meta = await save_file(photo, "documents", compress=False)
        c.photo_path = meta["file_path"]

    db.add(c)
    await db.commit()
    return await _load(db, c.id)


@router.put("/{cid}", response_model=ConferenceOut)
async def update_conference(
    cid: int,
    title: Optional[str] = Form(None),
    organizer: Optional[str] = Form(None),
    date_start: Optional[str] = Form(None),
    date_end: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    is_online: Optional[bool] = Form(None),
    participant_ids: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    c = await _load(db, cid)
    if not c:
        raise HTTPException(404, "Conference not found")

    if title is not None: c.title = title
    if organizer is not None: c.organizer = organizer
    if date_start is not None: c.date_start = date.fromisoformat(date_start)
    if date_end is not None: c.date_end = date.fromisoformat(date_end)
    if url is not None: c.url = url
    if description is not None: c.description = description
    if location is not None: c.location = location
    if is_online is not None: c.is_online = is_online

    if photo and photo.filename:
        delete_file(c.photo_path)
        meta = await save_file(photo, "documents", compress=False)
        c.photo_path = meta["file_path"]

    if participant_ids is not None:
        ids = json.loads(participant_ids)
        participants = []
        for pid in ids:
            a = await db.get(Author, pid)
            if a:
                participants.append(a)
        c.participants = participants

    await db.commit()
    return await _load(db, cid)


@router.delete("/{cid}", status_code=204)
async def delete_conference(cid: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Conference, cid)
    if not c:
        raise HTTPException(404, "Conference not found")
    delete_file(c.photo_path)
    await db.delete(c)
    await db.commit()
