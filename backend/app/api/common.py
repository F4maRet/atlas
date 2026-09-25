"""Общие помощники для эндпоинтов (разбор форм, загрузка связей, файлы)."""
import json
from datetime import date
from typing import Iterable, Optional, Sequence, Type, TypeVar

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Author, Collection
from app.services.file_service import delete_file, save_file

T = TypeVar("T")


# ── Разбор полей формы ────────────────────────────────────────────────────────
#
# Соглашение для multipart-форм при создании/изменении:
#   поле не передано  → не меняется
#   пустая строка ""  → очистить значение (NULL)
# Раньше пустые значения фронтенд просто не отправлял, а бэкенд их игнорировал —
# в итоге нельзя было убрать статью из сборника, очистить каталог, тип и т.д.

def clean_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def require_str(value: Optional[str], field: str) -> str:
    v = clean_str(value)
    if not v:
        raise HTTPException(400, f"Поле «{field}» обязательно")
    return v


def parse_opt_int(value: Optional[str], field: str) -> Optional[int]:
    v = clean_str(value)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        raise HTTPException(400, f"Поле «{field}»: ожидается число")


def parse_date(value: Optional[str], field: str) -> Optional[date]:
    v = clean_str(value)
    if v is None:
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise HTTPException(400, f"Поле «{field}»: некорректная дата «{v}» (ожидается ГГГГ-ММ-ДД)")


def check_date_range(start: Optional[date], end: Optional[date]) -> None:
    if start and end and end < start:
        raise HTTPException(400, "Дата окончания раньше даты начала")


def parse_ids(value: Optional[str], field: str = "author_ids") -> list[int]:
    if not value:
        return []
    try:
        data = json.loads(value)
        if not isinstance(data, list):
            raise ValueError
        ids = [int(x) for x in data]
    except (ValueError, TypeError):
        raise HTTPException(400, f"Поле «{field}»: ожидается JSON-массив чисел")
    return list(dict.fromkeys(ids))  # без дублей, порядок сохраняется


# ── Загрузка связанных объектов ───────────────────────────────────────────────

async def load_authors(db: AsyncSession, ids: Sequence[int]) -> list[Author]:
    """Один запрос вместо N; порядок — как в ids; несуществующие id → 400."""
    if not ids:
        return []
    with db.no_autoflush:
        rows = (await db.execute(select(Author).where(Author.id.in_(ids)))).scalars().all()
    by_id = {a.id: a for a in rows}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise HTTPException(400, f"Авторы не найдены: {', '.join(map(str, missing))}")
    return [by_id[i] for i in ids]


async def check_collection(db: AsyncSession, collection_id: Optional[int]) -> None:
    if collection_id is None:
        return
    with db.no_autoflush:
        found = await db.get(Collection, collection_id)
    if not found:
        raise HTTPException(400, "Сборник не найден")


async def get_or_404(db: AsyncSession, model: Type[T], obj_id: int, what: str = "Запись") -> T:
    obj = await db.get(model, obj_id)
    if not obj:
        raise HTTPException(404, f"{what} не найдена")
    return obj


# ── Файлы ─────────────────────────────────────────────────────────────────────

FILE_FIELDS = ("file_path", "original_filename", "file_size_original", "file_size_compressed")


def has_upload(upload: Optional[UploadFile]) -> bool:
    return bool(upload is not None and upload.filename)


async def replace_file(obj, upload: UploadFile, subdir: str, allowed_ext: Optional[set] = None,
                       fields: Iterable[str] = FILE_FIELDS) -> Optional[str]:
    """
    Сохранить новый файл в объект и вернуть путь старого — удалить его вызывающий
    должен ПОСЛЕ успешного commit (раньше старый файл удалялся первым, и при любой
    ошибке дальше по коду документ терялся безвозвратно).
    """
    meta = await save_file(upload, subdir, compress=True, allowed_ext=allowed_ext)
    old = getattr(obj, "file_path", None)
    for f in fields:
        setattr(obj, f, meta[f])
    return old


async def commit_and_cleanup(db: AsyncSession, *old_paths: Optional[str]) -> None:
    await db.commit()
    for p in old_paths:
        delete_file(p)


def photo_url(stored: Optional[str]) -> Optional[str]:
    if not stored:
        return None
    marker = "/uploads/"
    rel = stored.split(marker, 1)[1] if marker in stored else stored.lstrip("/")
    return f"/uploads/{rel}"
