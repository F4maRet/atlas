import io
import json
import zipfile
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.api.common import (
    check_collection, clean_str, commit_and_cleanup, has_upload, load_authors, parse_ids,
    parse_opt_int, replace_file, require_str,
)
from app.db.session import get_db
from app.models.models import Software, SoftwareDocument
from app.schemas.schemas import SoftwareDocumentOut, SoftwareOut, SoftwareStructure
from app.services.file_service import (
    DOC_EXT, IMAGE_EXT, ZIP_EXT, clean_filename, delete_file, file_ext, get_zip_structure,
    read_file_bytes, read_zip_member,
)
from app.services.preview_service import (
    decode_text, download_response, is_binary, preview_response, safe_content_disposition,
)

router = APIRouter()

# Комплект документов ПО (порядок = порядок в интерфейсе и в архиве)
SOFTWARE_DOC_TYPES = {
    "annotation": "Аннотация программы",
    "registration": "Заявление на регистрацию",
    "description": "Описание программы",
    "manual": "Руководство пользователя",
    "act": "Акт приёма и ввода в эксплуатацию",
    "abstract": "Реферат по исходникам",
    "listing": "Листинг по исходникам",
    "certificate": "Свидетельство о регистрации",
}
MAX_TEXT_BYTES = 1024 * 1024


async def _load(db: AsyncSession, sid: int) -> Software:
    s = await db.scalar(
        select(Software).options(selectinload(Software.authors), selectinload(Software.documents))
        .where(Software.id == sid)
    )
    if not s:
        raise HTTPException(404, "ПО не найдено")
    return s


async def _parse_structure(sw: Software) -> None:
    try:
        tree = await run_in_threadpool(get_zip_structure, sw.file_path)
    except (zipfile.BadZipFile, OSError):
        raise HTTPException(400, "Файл не является корректным ZIP-архивом")
    sw.file_structure = json.dumps(tree, ensure_ascii=False)


@router.get("/doc-types")
async def doc_types():
    return [{"key": k, "label": v} for k, v in SOFTWARE_DOC_TYPES.items()]


@router.get("/", response_model=List[SoftwareOut])
async def list_software(db: AsyncSession = Depends(get_db)):
    # Дерево файлов в список не входит (оно бывает большим) — см. /{id}/structure
    r = await db.execute(
        select(Software).options(selectinload(Software.authors), selectinload(Software.documents))
        .order_by(Software.created_at.desc())
    )
    return r.scalars().all()


@router.get("/{sid}", response_model=SoftwareOut)
async def get_software(sid: int, db: AsyncSession = Depends(get_db)):
    return await _load(db, sid)


@router.get("/{sid}/structure", response_model=SoftwareStructure)
async def get_structure(sid: int, db: AsyncSession = Depends(get_db)):
    sw = await db.get(Software, sid)
    if not sw or not sw.file_path:
        raise HTTPException(404, "Архив не загружен")
    if not sw.file_structure or sw.file_structure == "[]":
        await _parse_structure(sw)
        await db.commit()
    return {"id": sw.id, "tree": sw.tree}


@router.post("/", response_model=SoftwareOut, status_code=201)
async def create_software(
    title: str = Form(...),
    software_type: Optional[str] = Form(None),
    collection_id: Optional[str] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: str = Form("[]"),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    col_id = parse_opt_int(collection_id, "collection_id")
    await check_collection(db, col_id)
    sw = Software(
        title=require_str(title, "Название"),
        software_type=clean_str(software_type),
        collection_id=col_id,
        catalog=clean_str(catalog),
        authors=await load_authors(db, parse_ids(author_ids)),
    )
    if has_upload(file):
        await replace_file(sw, file, "software", ZIP_EXT)
        try:
            await _parse_structure(sw)
        except HTTPException:
            delete_file(sw.file_path)
            raise
    db.add(sw)
    try:
        await db.commit()
    except Exception:
        delete_file(sw.file_path)
        raise
    return await _load(db, sw.id)


@router.put("/{sid}", response_model=SoftwareOut)
async def update_software(
    sid: int,
    title: Optional[str] = Form(None),
    software_type: Optional[str] = Form(None),
    collection_id: Optional[str] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    sw = await _load(db, sid)
    if title is not None:
        sw.title = require_str(title, "Название")
    if software_type is not None:
        sw.software_type = clean_str(software_type)
    if collection_id is not None:
        col_id = parse_opt_int(collection_id, "collection_id")
        await check_collection(db, col_id)
        sw.collection_id = col_id
    if catalog is not None:
        sw.catalog = clean_str(catalog)
    if author_ids is not None:
        sw.authors = await load_authors(db, parse_ids(author_ids))
    old_file = None
    if has_upload(file):
        old_file = await replace_file(sw, file, "software", ZIP_EXT)
        try:
            await _parse_structure(sw)
        except HTTPException:
            delete_file(sw.file_path)
            raise
    await commit_and_cleanup(db, old_file)
    return await _load(db, sid)


@router.delete("/{sid}", status_code=204)
async def delete_software(sid: int, db: AsyncSession = Depends(get_db)):
    sw = await _load(db, sid)
    paths = [sw.file_path, *(d.file_path for d in sw.documents)]
    await db.delete(sw)
    await commit_and_cleanup(db, *paths)


@router.get("/{sid}/download")
async def download_software(sid: int, db: AsyncSession = Depends(get_db)):
    sw = await db.get(Software, sid)
    if not sw or not sw.file_path:
        raise HTTPException(404, "Файл не найден")
    return download_response(sw.file_path, sw.original_filename or "software.zip", "application/zip")


async def _zip_sw(db: AsyncSession, sid: int) -> Software:
    sw = await db.get(Software, sid)
    if not sw or not sw.file_path:
        raise HTTPException(404, "Архив не загружен")
    return sw


@router.get("/{sid}/file-content")
async def get_file_content(sid: int, path: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Текст файла из ZIP (для просмотра). Бинарные файлы и большие файлы не отдаются целиком."""
    sw = await _zip_sw(db, sid)
    try:
        data, size, truncated = await run_in_threadpool(read_zip_member, sw.file_path, path, MAX_TEXT_BYTES)
    except zipfile.BadZipFile:
        raise HTTPException(400, "Архив повреждён")
    if is_binary(data):
        return {"path": path, "size": size, "binary": True, "truncated": False, "content": ""}
    return {"path": path, "size": size, "binary": False, "truncated": truncated, "content": decode_text(data)}


@router.get("/{sid}/file-download")
async def download_zip_member(sid: int, path: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Скачать отдельный файл из архива."""
    sw = await _zip_sw(db, sid)
    from app.core.config import settings
    data, size, truncated = await run_in_threadpool(read_zip_member, sw.file_path, path, settings.max_file_bytes)
    if truncated:
        raise HTTPException(413, "Файл слишком большой")
    name = clean_filename(path.rsplit("/", 1)[-1])
    return Response(data, media_type="application/octet-stream",
                    headers={"Content-Disposition": safe_content_disposition("attachment", name)})


# ── Комплект документов ───────────────────────────────────────────────────────

@router.post("/{sid}/documents", response_model=SoftwareDocumentOut, status_code=201)
async def upload_software_document(
    sid: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(Software, sid):
        raise HTTPException(404, "ПО не найдено")
    if doc_type not in SOFTWARE_DOC_TYPES:
        raise HTTPException(400, f"Неизвестный тип документа: {doc_type}")

    doc = await db.scalar(select(SoftwareDocument).where(
        SoftwareDocument.software_id == sid, SoftwareDocument.doc_type == doc_type))
    if doc is None:
        doc = SoftwareDocument(software_id=sid, doc_type=doc_type)
        db.add(doc)
    old = await replace_file(doc, file, "documents", DOC_EXT | IMAGE_EXT)
    await commit_and_cleanup(db, old)
    await db.refresh(doc)
    return doc


async def _get_doc(db: AsyncSession, sid: int, doc_id: int) -> SoftwareDocument:
    doc = await db.get(SoftwareDocument, doc_id)
    if not doc or doc.software_id != sid or not doc.file_path:
        raise HTTPException(404, "Документ не найден")
    return doc


@router.delete("/{sid}/documents/{doc_id}", status_code=204)
async def delete_software_document(sid: int, doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await _get_doc(db, sid, doc_id)
    path = doc.file_path
    await db.delete(doc)
    await commit_and_cleanup(db, path)


@router.get("/{sid}/documents/archive")
async def download_documents_archive(sid: int, db: AsyncSession = Depends(get_db)):
    """Весь комплект документов одним ZIP-архивом (01_Аннотация программы.pdf, ...)."""
    sw = await _load(db, sid)
    docs = [d for d in sw.documents if d.file_path]
    if not docs:
        raise HTTPException(404, "Документы не загружены")
    order = list(SOFTWARE_DOC_TYPES)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in sorted(docs, key=lambda d: order.index(d.doc_type) if d.doc_type in order else 99):
            num = order.index(d.doc_type) + 1 if d.doc_type in order else 99
            label = SOFTWARE_DOC_TYPES.get(d.doc_type, d.doc_type)
            zf.writestr(f"{num:02d}_{label}{file_ext(d.original_filename)}", await read_file_bytes(d.file_path))
    name = clean_filename(f"Документы_{sw.title[:80]}.zip")
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": safe_content_disposition("attachment", name)})


@router.get("/{sid}/documents/{doc_id}/download")
async def download_software_document(sid: int, doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await _get_doc(db, sid, doc_id)
    return download_response(doc.file_path, doc.original_filename or "document")


@router.get("/{sid}/documents/{doc_id}/preview")
async def preview_software_document(sid: int, doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await _get_doc(db, sid, doc_id)
    return await preview_response(doc.file_path, doc.original_filename or "document")
