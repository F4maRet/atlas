from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date

from app.db.session import get_db
from app.models.models import Collection
from app.schemas.schemas import CollectionCreate, CollectionUpdate, CollectionOut
from app.services.file_service import save_file, delete_file

router = APIRouter()


@router.get("/", response_model=List[CollectionOut])
async def list_collections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Collection).order_by(Collection.date_start.desc().nullslast()))
    cols = result.scalars().all()
    today = date.today()
    out = []
    for c in cols:
        d = CollectionOut.model_validate(c).model_dump()
        if c.date_end:
            d["is_past"] = c.date_end < today
        out.append(d)
    return out


@router.get("/{col_id}", response_model=CollectionOut)
async def get_collection(col_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Collection, col_id)
    if not c:
        raise HTTPException(404, "Collection not found")
    today = date.today()
    d = CollectionOut.model_validate(c).model_dump()
    if c.date_end:
        d["is_past"] = c.date_end < today
    return d


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
        name=name,
        university=university,
        date_start=date.fromisoformat(date_start) if date_start else None,
        date_end=date.fromisoformat(date_end) if date_end else None,
        url=url,
        description=description,
    )
    if photo and photo.filename:
        meta = await save_file(photo, "documents", compress=False)
        col.photo_path = meta["file_path"]
    db.add(col)
    await db.commit()
    await db.refresh(col)
    return col


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
    db: AsyncSession = Depends(get_db),
):
    col = await db.get(Collection, col_id)
    if not col:
        raise HTTPException(404, "Collection not found")
    if name: col.name = name
    if university: col.university = university
    if date_start: col.date_start = date.fromisoformat(date_start)
    if date_end: col.date_end = date.fromisoformat(date_end)
    if url: col.url = url
    if description: col.description = description
    if photo and photo.filename:
        delete_file(col.photo_path)
        meta = await save_file(photo, "documents", compress=False)
        col.photo_path = meta["file_path"]
    await db.commit()
    await db.refresh(col)
    return col


@router.delete("/{col_id}", status_code=204)
async def delete_collection(col_id: int, db: AsyncSession = Depends(get_db)):
    col = await db.get(Collection, col_id)
    if not col:
        raise HTTPException(404, "Collection not found")
    delete_file(col.photo_path)
    await db.delete(col)
    await db.commit()
