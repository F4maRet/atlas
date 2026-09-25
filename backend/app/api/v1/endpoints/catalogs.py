"""
Каталоги хранения для статей, рац. предложений и ПО.

Раньше каталоги существовали только в браузере: новый пустой каталог исчезал
после перезагрузки, а переименование/удаление делалось отдельным PUT-запросом
на каждую запись (с риском остановиться на середине). Теперь — таблица catalogs
и групповые операции в одной транзакции.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import Article, Catalog, Proposal, Software
from app.schemas.schemas import CatalogCreate, CatalogMove, CatalogOut

router = APIRouter()

SCOPES = {"articles": Article, "proposals": Proposal, "software": Software}


class CatalogRenameBody(BaseModel):
    old_name: str = Field(min_length=1, max_length=500)
    new_name: str = Field(min_length=1, max_length=500)


def _model(scope: str):
    if scope not in SCOPES:
        raise HTTPException(404, "Неизвестный раздел")
    return SCOPES[scope]


def _name(value: str | None) -> str | None:
    v = " ".join((value or "").split())
    return v or None


@router.get("/{scope}", response_model=List[CatalogOut])
async def list_catalogs(scope: str, db: AsyncSession = Depends(get_db)):
    model = _model(scope)
    counts = dict((await db.execute(
        select(model.catalog, func.count()).where(model.catalog.isnot(None)).group_by(model.catalog)
    )).all())
    stored = (await db.execute(select(Catalog.name).where(Catalog.scope == scope))).scalars().all()
    names = sorted(set(stored) | set(counts), key=str.lower)
    return [{"name": n, "count": counts.get(n, 0)} for n in names]


@router.post("/{scope}", response_model=CatalogOut, status_code=201)
async def create_catalog(scope: str, data: CatalogCreate, db: AsyncSession = Depends(get_db)):
    _model(scope)
    name = _name(data.name)
    if not name:
        raise HTTPException(400, "Название каталога не может быть пустым")
    exists = await db.scalar(select(Catalog).where(Catalog.scope == scope, Catalog.name == name))
    if not exists:
        db.add(Catalog(scope=scope, name=name))
        await db.commit()
    return {"name": name, "count": 0}


@router.put("/{scope}/rename", response_model=CatalogOut)
async def rename_catalog(scope: str, data: CatalogRenameBody, db: AsyncSession = Depends(get_db)):
    model = _model(scope)
    old, new = _name(data.old_name), _name(data.new_name)
    if not old or not new:
        raise HTTPException(400, "Название каталога не может быть пустым")
    res = await db.execute(update(model).where(model.catalog == old).values(catalog=new))
    await db.execute(delete(Catalog).where(Catalog.scope == scope, Catalog.name.in_([old, new])))
    db.add(Catalog(scope=scope, name=new))
    await db.commit()
    count = await db.scalar(select(func.count()).select_from(model).where(model.catalog == new))
    return {"name": new, "count": count or res.rowcount}


@router.delete("/{scope}", status_code=204)
async def delete_catalog(scope: str, name: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Удаляет каталог; записи остаются, но становятся «без каталога»."""
    model = _model(scope)
    await db.execute(update(model).where(model.catalog == name).values(catalog=None))
    await db.execute(delete(Catalog).where(Catalog.scope == scope, Catalog.name == name))
    await db.commit()


@router.post("/{scope}/move")
async def move_to_catalog(scope: str, data: CatalogMove, db: AsyncSession = Depends(get_db)):
    """Переместить записи (drag&drop, групповое действие) в каталог или убрать из каталога."""
    model = _model(scope)
    name = _name(data.catalog)
    if not data.ids:
        return {"moved": 0}
    res = await db.execute(update(model).where(model.id.in_(data.ids)).values(catalog=name))
    if name and not await db.scalar(select(Catalog).where(Catalog.scope == scope, Catalog.name == name)):
        db.add(Catalog(scope=scope, name=name))
    await db.commit()
    return {"moved": res.rowcount}
