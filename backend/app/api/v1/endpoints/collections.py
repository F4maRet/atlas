from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import (
    check_date_range, clean_str, commit_and_cleanup, has_upload, parse_date, require_str,
)
from app.db.session import get_db
from app.models.models import Article, Collection
from app.schemas.schemas import CollectionOut
from app.services.file_service import IMAGE_EXT, delete_file, save_file

router = APIRouter()


async def _counts(db: AsyncSession) -> dict[int, int]:
    rows = await db.execute(
        select(Article.collection_id, func.count()).where(Article.collection_id.isnot(None))
        .group_by(Article.collection_id)
    )
    return dict(rows.all())


def _out(c: Collection, counts: dict[int, int]) -> CollectionOut:
    out = CollectionOut.model_validate(c)
    out.articles_count = counts.get(c.id, 0)
    return out


async def _get(db: AsyncSession, col_id: int) -> Collection:
    c = await db.get(Collection, col_id)
    if not c:
        raise HTTPException(404, "Сборник не найден")
    return c


async def _save_photo(photo: UploadFile) -> str:
    meta = await save_file(photo, "images", compress=False, allowed_ext=IMAGE_EXT)
    return meta["file_path"]


@router.get("/", response_model=List[CollectionOut])
async def list_collections(db: AsyncSession = Depends(get_db)):
    cols = (await db.execute(
        select(Collection).order_by(Collection.date_start.desc().nullslast(), Collection.name)
    )).scalars().all()
    counts = await _counts(db)
    return [_out(c, counts) for c in cols]


@router.get("/{col_id}", response_model=CollectionOut)
async def get_collection(col_id: int, db: AsyncSession = Depends(get_db)):
    return _out(await _get(db, col_id), await _counts(db))


@router.post("/", response_model=CollectionOut, status_code=201)
async def create_collection(
    name: str = Form(...),
    university: Optional[str] = Form(None),
    date_start: Optional[str] = Form(None),
    date_end: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    col = Collection(
        name=require_str(name, "Название"),
        university=clean_str(university),
        date_start=parse_date(date_start, "Дата начала"),
        date_end=parse_date(date_end, "Дата окончания"),
        url=clean_str(url),
        description=clean_str(description),
    )
    check_date_range(col.date_start, col.date_end)
    if has_upload(photo):
        col.photo_path = await _save_photo(photo)
    db.add(col)
    try:
        await db.commit()
    except Exception:
        delete_file(col.photo_path)
        raise
    return _out(col, {})


@router.put("/{col_id}", response_model=CollectionOut)
async def update_collection(
    col_id: int,
    name: Optional[str] = Form(None),
    university: Optional[str] = Form(None),
    date_start: Optional[str] = Form(None),
    date_end: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    remove_photo: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    col = await _get(db, col_id)
    # Раньше стояло `if university: ...` — очистить поле было невозможно
    if name is not None:
        col.name = require_str(name, "Название")
    if university is not None:
        col.university = clean_str(university)
    if date_start is not None:
        col.date_start = parse_date(date_start, "Дата начала")
    if date_end is not None:
        col.date_end = parse_date(date_end, "Дата окончания")
    if url is not None:
        col.url = clean_str(url)
    if description is not None:
        col.description = clean_str(description)
    check_date_range(col.date_start, col.date_end)

    old_photo = None
    if has_upload(photo):
        old_photo, col.photo_path = col.photo_path, await _save_photo(photo)
    elif remove_photo:
        old_photo, col.photo_path = col.photo_path, None
    await commit_and_cleanup(db, old_photo)
    return _out(col, await _counts(db))


@router.delete("/{col_id}", status_code=204)
async def delete_collection(col_id: int, db: AsyncSession = Depends(get_db)):
    col = await _get(db, col_id)
    path = col.photo_path
    await db.delete(col)
    await commit_and_cleanup(db, path)
