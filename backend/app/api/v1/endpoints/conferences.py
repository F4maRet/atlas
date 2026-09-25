from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.common import (
    check_date_range, clean_str, commit_and_cleanup, has_upload, load_authors, parse_date, parse_ids,
    require_str,
)
from app.db.session import get_db
from app.models.models import Conference
from app.schemas.schemas import ConferenceOut
from app.services.file_service import IMAGE_EXT, clean_filename, delete_file, save_file
from app.services.preview_service import safe_content_disposition

router = APIRouter()


async def _load(db: AsyncSession, cid: int) -> Conference:
    c = await db.scalar(select(Conference).options(selectinload(Conference.participants)).where(Conference.id == cid))
    if not c:
        raise HTTPException(404, "Конференция не найдена")
    return c


async def _save_photo(photo: UploadFile) -> str:
    return (await save_file(photo, "images", compress=False, allowed_ext=IMAGE_EXT))["file_path"]


@router.get("/", response_model=List[ConferenceOut])
async def list_conferences(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Conference)
        .options(selectinload(Conference.participants))
        .order_by(Conference.date_start.asc().nullslast(), Conference.title)
    )
    d_from, d_to = parse_date(date_from, "date_from"), parse_date(date_to, "date_to")
    # Пересечение интервалов: конференция, идущая в указанный период, тоже попадает в выборку
    end = func.coalesce(Conference.date_end, Conference.date_start)
    if d_from:
        q = q.where(or_(Conference.date_start.is_(None), end >= d_from))
    if d_to:
        q = q.where(or_(Conference.date_start.is_(None), Conference.date_start <= d_to))
    return (await db.execute(q)).scalars().all()


@router.get("/{cid}", response_model=ConferenceOut)
async def get_conference(cid: int, db: AsyncSession = Depends(get_db)):
    return await _load(db, cid)


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
    c = Conference(
        title=require_str(title, "Название"),
        organizer=clean_str(organizer),
        date_start=parse_date(date_start, "Дата начала"),
        date_end=parse_date(date_end, "Дата окончания"),
        url=clean_str(url),
        description=clean_str(description),
        location=clean_str(location),
        is_online=is_online,
        source="manual",
        participants=await load_authors(db, parse_ids(participant_ids, "participant_ids")),
    )
    check_date_range(c.date_start, c.date_end)
    if has_upload(photo):
        c.photo_path = await _save_photo(photo)
    db.add(c)
    try:
        await db.commit()
    except Exception:
        delete_file(c.photo_path)
        raise
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
    remove_photo: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    c = await _load(db, cid)
    if title is not None:
        c.title = require_str(title, "Название")
    for field, value in (("organizer", organizer), ("url", url), ("description", description), ("location", location)):
        if value is not None:
            setattr(c, field, clean_str(value))
    # Раньше пустая дата ("") давала 500 (date.fromisoformat("")) и дату нельзя было убрать
    if date_start is not None:
        c.date_start = parse_date(date_start, "Дата начала")
    if date_end is not None:
        c.date_end = parse_date(date_end, "Дата окончания")
    check_date_range(c.date_start, c.date_end)
    if is_online is not None:
        c.is_online = is_online
    if participant_ids is not None:
        c.participants = await load_authors(db, parse_ids(participant_ids, "participant_ids"))

    old_photo = None
    if has_upload(photo):
        old_photo, c.photo_path = c.photo_path, await _save_photo(photo)
    elif remove_photo:
        old_photo, c.photo_path = c.photo_path, None
    await commit_and_cleanup(db, old_photo)
    return await _load(db, cid)


@router.delete("/{cid}", status_code=204)
async def delete_conference(cid: int, db: AsyncSession = Depends(get_db)):
    c = await _load(db, cid)
    path = c.photo_path
    await db.delete(c)
    await commit_and_cleanup(db, path)


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@router.get("/{cid}/ics")
async def conference_ics(cid: int, db: AsyncSession = Depends(get_db)):
    """Событие в формате iCalendar — для импорта в Outlook / календарь телефона."""
    c = await _load(db, cid)
    if not c.date_start:
        raise HTTPException(400, "У конференции не указана дата начала")
    end = (c.date_end or c.date_start) + timedelta(days=1)  # DTEND для событий «на весь день» не включительно
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ATLAS//Conferences//RU", "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:conference-{c.id}@atlas",
        f"DTSTAMP:{datetime.utcnow():%Y%m%dT%H%M%SZ}",
        f"DTSTART;VALUE=DATE:{c.date_start:%Y%m%d}",
        f"DTEND;VALUE=DATE:{end:%Y%m%d}",
        f"SUMMARY:{_ics_escape(c.title)}",
    ]
    desc = "\n".join(filter(None, [c.organizer, c.description, c.url]))
    if desc:
        lines.append(f"DESCRIPTION:{_ics_escape(desc)}")
    if c.location or c.is_online:
        lines.append(f"LOCATION:{_ics_escape(c.location or 'Онлайн')}")
    if c.url:
        lines.append(f"URL:{c.url}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    name = clean_filename(f"{c.title[:60]}.ics")
    return Response("\r\n".join(lines) + "\r\n", media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": safe_content_disposition("attachment", name)})
