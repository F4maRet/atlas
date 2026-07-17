from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json

from app.db.session import get_db
from app.models.models import Software, Author, SoftwareDocument
from app.schemas.schemas import SoftwareOut
from app.services.file_service import save_file, read_file_bytes, delete_file, get_zip_structure, read_file_from_zip
from app.services.preview_service import safe_content_disposition

router = APIRouter()

SOFTWARE_DOC_TYPES = ["annotation", "registration", "description", "manual", "act", "abstract", "listing", "certificate"]


async def _load(db, sid):
    r = await db.execute(
        select(Software)
        .options(selectinload(Software.authors), selectinload(Software.documents))
        .where(Software.id == sid)
    )
    return r.scalar_one_or_none()


@router.get("/", response_model=List[SoftwareOut])
async def list_software(db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Software).options(selectinload(Software.authors), selectinload(Software.documents))
        .order_by(Software.created_at.desc())
    )
    items = r.scalars().all()
    out = []
    for s in items:
        d = SoftwareOut.model_validate(s).model_dump()
        if s.file_structure:
            try:
                d["file_structure"] = json.loads(s.file_structure)
            except Exception:
                pass
        out.append(d)
    return out


@router.get("/{sid}", response_model=SoftwareOut)
async def get_software(sid: int, db: AsyncSession = Depends(get_db)):
    s = await _load(db, sid)
    if not s:
        raise HTTPException(404, "Not found")
    d = SoftwareOut.model_validate(s).model_dump()
    if s.file_structure:
        try:
            d["file_structure"] = json.loads(s.file_structure)
        except Exception:
            pass
    return d


@router.post("/", response_model=SoftwareOut, status_code=201)
async def create_software(
    title: str = Form(...),
    software_type: Optional[str] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: str = Form("[]"),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    ids = json.loads(author_ids)

    authors = []
    for aid in ids:
        a = await db.get(Author, aid)
        if a:
            authors.append(a)

    sw = Software(title=title, software_type=software_type or None, catalog=catalog or None, authors=authors)
    if file and file.filename:
        meta = await save_file(file, "software", compress=True)
        sw.file_path = meta["file_path"]
        sw.original_filename = meta["original_filename"]
        sw.file_size_original = meta["file_size_original"]
        sw.file_size_compressed = meta["file_size_compressed"]
        # Parse ZIP structure
        try:
            tree = get_zip_structure(meta["file_path"])
            sw.file_structure = json.dumps(tree, ensure_ascii=False)
        except Exception:
            sw.file_structure = "[]"
    db.add(sw)
    await db.commit()
    return await _load(db, sw.id)


@router.put("/{sid}", response_model=SoftwareOut)
async def update_software(
    sid: int,
    title: Optional[str] = Form(None),
    software_type: Optional[str] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    sw = await _load(db, sid)
    if not sw:
        raise HTTPException(404, "Not found")
    if title is not None:
        sw.title = title
    if software_type is not None:
        sw.software_type = software_type or None
    if catalog is not None:
        sw.catalog = catalog or None
    if file and file.filename:
        delete_file(sw.file_path)
        meta = await save_file(file, "software", compress=True)
        sw.file_path = meta["file_path"]
        sw.original_filename = meta["original_filename"]
        sw.file_size_original = meta["file_size_original"]
        sw.file_size_compressed = meta["file_size_compressed"]
        try:
            tree = get_zip_structure(meta["file_path"])
            sw.file_structure = json.dumps(tree, ensure_ascii=False)
        except Exception:
            sw.file_structure = "[]"
    if author_ids is not None:
        ids = json.loads(author_ids)
        authors = []
        for aid in ids:
            a = await db.get(Author, aid)
            if a:
                authors.append(a)
        sw.authors = authors
    await db.commit()
    return await _load(db, sid)


@router.delete("/{sid}", status_code=204)
async def delete_software(sid: int, db: AsyncSession = Depends(get_db)):
    sw = await _load(db, sid)
    if not sw:
        raise HTTPException(404, "Not found")
    delete_file(sw.file_path)
    for doc in sw.documents:
        delete_file(doc.file_path)
    await db.delete(sw)
    await db.commit()


@router.get("/{sid}/download")
async def download_software(sid: int, db: AsyncSession = Depends(get_db)):
    sw = await db.get(Software, sid)
    if not sw or not sw.file_path:
        raise HTTPException(404, "File not found")
    content = await read_file_bytes(sw.file_path)
    return Response(content=content, media_type="application/zip",
                    headers={"Content-Disposition": safe_content_disposition("attachment", sw.original_filename or "software.zip")})


@router.get("/{sid}/file-content")
async def get_file_content(sid: int, path: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Read content of a specific file inside the ZIP."""
    sw = await db.get(Software, sid)
    if not sw or not sw.file_path:
        raise HTTPException(404, "Not found")
    try:
        content = await read_file_from_zip(sw.file_path, path)
        try:
            text = content.decode("utf-8")
        except Exception:
            text = content.decode("latin-1", errors="replace")
        return {"path": path, "content": text}
    except Exception as e:
        raise HTTPException(400, f"Cannot read file: {e}")


# ── Software Documents (7 комплектных документов) ─────────────────────────────

@router.post("/{sid}/documents", status_code=201)
async def upload_software_document(
    sid: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    sw = await db.get(Software, sid)
    if not sw:
        raise HTTPException(404, "Software not found")
    if doc_type not in SOFTWARE_DOC_TYPES:
        raise HTTPException(400, f"doc_type must be one of: {SOFTWARE_DOC_TYPES}")

    # Upsert: если документ данного типа уже существует — удаляем старый файл и запись
    existing_r = await db.execute(
        select(SoftwareDocument).where(
            SoftwareDocument.software_id == sid,
            SoftwareDocument.doc_type == doc_type,
        )
    )
    existing = existing_r.scalars().all()
    for old_doc in existing:
        delete_file(old_doc.file_path)
        await db.delete(old_doc)
    await db.flush()  # убедимся, что старые записи удалены до вставки новой

    meta = await save_file(file, "documents", compress=True)
    doc = SoftwareDocument(
        software_id=sid,
        doc_type=doc_type,
        file_path=meta["file_path"],
        original_filename=meta["original_filename"],
        file_size_original=meta["file_size_original"],
        file_size_compressed=meta["file_size_compressed"],
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{sid}/documents/{doc_id}", status_code=204)
async def delete_software_document(sid: int, doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(SoftwareDocument, doc_id)
    if not doc or doc.software_id != sid:
        raise HTTPException(404, "Not found")
    delete_file(doc.file_path)
    await db.delete(doc)
    await db.commit()


@router.get("/{sid}/documents/{doc_id}/download")
async def download_software_document(
    sid: int,
    doc_id: int,
    inline: bool = Query(False, description="Set True to serve inline for in-browser preview"),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(SoftwareDocument, doc_id)
    if not doc or doc.software_id != sid or not doc.file_path:
        raise HTTPException(404, "File not found")
    content = await read_file_bytes(doc.file_path)

    orig_lower = (doc.original_filename or "").lower()
    if inline and orig_lower.endswith(".pdf"):
        # Serve as inline PDF so the browser renders it inside an <iframe>
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": safe_content_disposition("attachment", doc.original_filename or "document")},
    )


@router.get("/{sid}/documents/{doc_id}/preview")
async def preview_software_document(sid: int, doc_id: int, db: AsyncSession = Depends(get_db)):
    """
    Serve software document for in-browser preview.
      - PDF   → inline with correct Content-Type so the browser renders it
      - DOCX  → converted to HTML via python-docx
      - other → force download
    """
    from app.services.preview_service import docx_to_html

    doc = await db.get(SoftwareDocument, doc_id)
    if not doc or doc.software_id != sid or not doc.file_path:
        raise HTTPException(404, "File not found")

    orig_lower = (doc.original_filename or "").lower()
    path_lower = (doc.file_path or "").lower()

    is_docx = (
        orig_lower.endswith(".docx")
        or path_lower.endswith(".docx.gz")
        or path_lower.endswith(".docx")
    )
    # Legacy .doc — cannot be rendered, show friendly message
    is_doc_legacy = orig_lower.endswith(".doc") and not is_docx
    is_pdf = (
        orig_lower.endswith(".pdf")
        or path_lower.endswith(".pdf.gz")
        or path_lower.endswith(".pdf")
    )

    # ── Legacy DOC — unsupported, return friendly HTML ─────────────────────────
    if is_doc_legacy:
        unavailable_html = (
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            "<style>"
            "body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;"
            "height:100vh;margin:0;background:#f8f9fa;color:#555;text-align:center;}"
            ".box{padding:32px;} .icon{font-size:48px;margin-bottom:16px;}"
            ".title{font-size:16px;font-weight:600;margin-bottom:8px;color:#333;}"
            ".sub{font-size:13px;color:#888;line-height:1.6;}"
            "</style></head>"
            "<body><div class=\"box\">"
            "<div class=\"icon\">📎</div>"
            "<div class=\"title\">Предпросмотр недоступен</div>"
            "<div class=\"sub\">Формат .doc не поддерживается для просмотра.<br>Скачайте файл для открытия.</div>"
            "</div></body></html>"
        )
        return Response(content=unavailable_html.encode("utf-8"), media_type="text/html; charset=utf-8")

    # ── DOCX ──────────────────────────────────────────────────────────────────
    if is_docx:
        try:
            html = docx_to_html(doc.file_path)
            return Response(content=html.encode("utf-8"), media_type="text/html; charset=utf-8")
        except Exception as exc:
            ext = orig_lower.split(".")[-1] if "." in orig_lower else "docx"
            fallback_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:sans-serif;display:flex;align-items:center;justify-content:center;
height:100vh;margin:0;background:#f8f9fa;color:#555;text-align:center;}}
.box{{padding:32px;}} .icon{{font-size:48px;margin-bottom:16px;}}
.title{{font-size:16px;font-weight:600;margin-bottom:8px;color:#333;}}
.sub{{font-size:13px;color:#888;}}</style></head>
<body><div class="box"><div class="icon">📎</div>
<div class="title">Предпросмотр недоступен</div>
<div class="sub">Файл .{ext} не удалось открыть для предпросмотра.<br>Скачайте файл для открытия.</div>
</div></body></html>"""
            return Response(content=fallback_html.encode("utf-8"), media_type="text/html; charset=utf-8")

    # ── PDF ───────────────────────────────────────────────────────────────────
    if is_pdf:
        content = await read_file_bytes(doc.file_path)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    # ── Fallback: force download ───────────────────────────────────────────────
    content = await read_file_bytes(doc.file_path)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": safe_content_disposition("attachment", doc.original_filename or "file")},
    )
