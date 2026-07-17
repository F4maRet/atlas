from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.db.session import get_db
from app.models.models import DocumentTemplate
from app.schemas.schemas import TemplateCreate, TemplateOut
from app.services.file_service import save_file, read_file_bytes, delete_file

router = APIRouter()


@router.get("/", response_model=List[TemplateOut])
async def list_templates(db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(DocumentTemplate).order_by(DocumentTemplate.name))
    return r.scalars().all()


@router.get("/{tid}", response_model=TemplateOut)
async def get_template(tid: int, db: AsyncSession = Depends(get_db)):
    t = await db.get(DocumentTemplate, tid)
    if not t:
        raise HTTPException(404, "Template not found")
    return t


@router.post("/", response_model=TemplateOut, status_code=201)
async def create_template(
    name: str = Form(...),
    doc_type: str = Form(...),
    description: Optional[str] = Form(None),
    is_active: bool = Form(True),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    t = DocumentTemplate(name=name, doc_type=doc_type, description=description, is_active=is_active)
    if file and file.filename:
        meta = await save_file(file, "templates", compress=True)
        t.file_path = meta["file_path"]
    db.add(t)
    await db.commit()
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
    t = await db.get(DocumentTemplate, tid)
    if not t:
        raise HTTPException(404, "Template not found")
    if name is not None: t.name = name
    if doc_type is not None: t.doc_type = doc_type
    if description is not None: t.description = description
    if is_active is not None: t.is_active = is_active
    if file and file.filename:
        delete_file(t.file_path)
        meta = await save_file(file, "templates", compress=True)
        t.file_path = meta["file_path"]
    await db.commit()
    await db.refresh(t)
    return t


@router.delete("/{tid}", status_code=204)
async def delete_template(tid: int, db: AsyncSession = Depends(get_db)):
    t = await db.get(DocumentTemplate, tid)
    if not t:
        raise HTTPException(404, "Template not found")
    delete_file(t.file_path)
    await db.delete(t)
    await db.commit()


@router.get("/{tid}/download")
async def download_template(tid: int, db: AsyncSession = Depends(get_db)):
    t = await db.get(DocumentTemplate, tid)
    if not t or not t.file_path:
        raise HTTPException(404, "File not found")
    content = await read_file_bytes(t.file_path)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{t.name}.docx"'},
    )


@router.get("/{tid}/preview")
async def preview_template(tid: int, db: AsyncSession = Depends(get_db)):
    """Serve template file for in-browser preview."""
    from app.services.preview_service import docx_to_html, safe_content_disposition
    t = await db.get(DocumentTemplate, tid)
    if not t or not t.file_path:
        raise HTTPException(404, "File not found")
    name_lower = (t.file_path or "").lower()
    if name_lower.endswith(".docx") or name_lower.endswith(".docx.gz"):
        html = docx_to_html(t.file_path)
        return Response(
            content=html.encode("utf-8"),
            media_type="text/html; charset=utf-8",
        )
    content = await read_file_bytes(t.file_path)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": safe_content_disposition("attachment", f"{t.name}.docx")},
    )
