from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import clean_str, commit_and_cleanup, has_upload, require_str
from app.db.session import get_db
from app.models.models import DocumentTemplate
from app.schemas.schemas import TemplateOut
from app.services.file_service import DOC_EXT, clean_filename, delete_file, file_ext, save_file
from app.services.preview_service import download_response, preview_response

router = APIRouter()

TEMPLATE_TYPES = {
    "conclusion": "Заключение об открытом опубликовании",
    "annotation": "Аннотация программы",
    "registration": "Заявление на регистрацию",
    "description": "Описание программы",
    "manual": "Руководство пользователя",
    "act": "Акт приёма и ввода в эксплуатацию",
    "abstract": "Реферат по исходникам",
    "listing": "Листинг по исходникам",
    "certificate": "Свидетельство о регистрации",
}


def _check_type(doc_type: str) -> str:
    doc_type = require_str(doc_type, "Тип документа")
    if doc_type not in TEMPLATE_TYPES:
        raise HTTPException(400, f"Неизвестный тип документа: {doc_type}")
    return doc_type


async def _save(file: UploadFile, doc_type: str) -> str:
    # Для заключений нужен именно DOCX — по нему идёт автозаполнение
    allowed = {".docx"} if doc_type == "conclusion" else DOC_EXT
    return (await save_file(file, "templates", compress=True, allowed_ext=allowed))["file_path"]


def _filename(t: DocumentTemplate) -> str:
    ext = file_ext((t.file_path or "").removesuffix(".gz")) or ".docx"
    return clean_filename(t.name) + ext


async def _get(db: AsyncSession, tid: int, need_file: bool = False) -> DocumentTemplate:
    t = await db.get(DocumentTemplate, tid)
    if not t or (need_file and not t.file_path):
        raise HTTPException(404, "Шаблон не найден")
    return t


@router.get("/types")
async def template_types():
    return [{"key": k, "label": v} for k, v in TEMPLATE_TYPES.items()]


@router.get("/", response_model=List[TemplateOut])
async def list_templates(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(DocumentTemplate).order_by(DocumentTemplate.name))).scalars().all()


@router.get("/{tid}", response_model=TemplateOut)
async def get_template(tid: int, db: AsyncSession = Depends(get_db)):
    return await _get(db, tid)


@router.post("/", response_model=TemplateOut, status_code=201)
async def create_template(
    name: str = Form(...),
    doc_type: str = Form(...),
    description: Optional[str] = Form(None),
    is_active: bool = Form(True),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    t = DocumentTemplate(name=require_str(name, "Название"), doc_type=_check_type(doc_type),
                         description=clean_str(description), is_active=is_active)
    if has_upload(file):
        t.file_path = await _save(file, t.doc_type)
    db.add(t)
    try:
        await db.commit()
    except Exception:
        delete_file(t.file_path)
        raise
    await db.refresh(t)
    return t


@router.put("/{tid}", response_model=TemplateOut)
async def update_template(
    tid: int,
    name: Optional[str] = Form(None),
    doc_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    t = await _get(db, tid)
    if name is not None:
        t.name = require_str(name, "Название")
    if doc_type is not None:
        t.doc_type = _check_type(doc_type)
    if description is not None:
        t.description = clean_str(description)
    if is_active is not None:
        t.is_active = is_active
    old = None
    if has_upload(file):
        old, t.file_path = t.file_path, await _save(file, t.doc_type)
    await commit_and_cleanup(db, old)
    await db.refresh(t)
    return t


@router.delete("/{tid}", status_code=204)
async def delete_template(tid: int, db: AsyncSession = Depends(get_db)):
    t = await _get(db, tid)
    path = t.file_path
    await db.delete(t)
    await commit_and_cleanup(db, path)


@router.get("/{tid}/download")
async def download_template(tid: int, db: AsyncSession = Depends(get_db)):
    # Раньше имя шаблона на кириллице подставлялось в заголовок как есть → 500 (latin-1)
    t = await _get(db, tid, need_file=True)
    return download_response(t.file_path, _filename(t))


@router.get("/{tid}/preview")
async def preview_template(tid: int, db: AsyncSession = Depends(get_db)):
    t = await _get(db, tid, need_file=True)
    return await preview_response(t.file_path, _filename(t))
