from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json

from app.db.session import get_db
from app.models.models import Proposal, Author, ProposalCertificate
from app.schemas.schemas import ProposalOut
from app.services.file_service import save_file, read_file_bytes, delete_file
from app.services.preview_service import safe_content_disposition

router = APIRouter()


async def _load(db, pid):
    r = await db.execute(
        select(Proposal)
        .options(selectinload(Proposal.authors), selectinload(Proposal.certificate))
        .where(Proposal.id == pid)
    )
    return r.scalar_one_or_none()


@router.get("/", response_model=List[ProposalOut])
async def list_proposals(db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Proposal)
        .options(selectinload(Proposal.authors), selectinload(Proposal.certificate))
        .order_by(Proposal.created_at.desc())
    )
    return r.scalars().all()


@router.get("/{pid}", response_model=ProposalOut)
async def get_proposal(pid: int, db: AsyncSession = Depends(get_db)):
    p = await _load(db, pid)
    if not p:
        raise HTTPException(404, "Proposal not found")
    return p


@router.post("/", response_model=ProposalOut, status_code=201)
async def create_proposal(
    title: str = Form(...),
    proposal_type: Optional[str] = Form(None),
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

    p = Proposal(title=title, proposal_type=proposal_type, catalog=catalog, authors=authors)
    if file and file.filename:
        meta = await save_file(file, "proposals", compress=True)
        p.file_path = meta["file_path"]
        p.original_filename = meta["original_filename"]
        p.file_size_original = meta["file_size_original"]
        p.file_size_compressed = meta["file_size_compressed"]

    db.add(p)
    await db.commit()
    return await _load(db, p.id)


@router.put("/{pid}", response_model=ProposalOut)
async def update_proposal(
    pid: int,
    title: Optional[str] = Form(None),
    proposal_type: Optional[str] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    p = await _load(db, pid)  # загружаем с selectinload — lazy load не нужен
    if not p:
        raise HTTPException(404, "Proposal not found")
    if title: p.title = title
    if proposal_type is not None: p.proposal_type = proposal_type
    if catalog is not None: p.catalog = catalog
    if file and file.filename:
        delete_file(p.file_path)
        meta = await save_file(file, "proposals", compress=True)
        p.file_path = meta["file_path"]
        p.original_filename = meta["original_filename"]
        p.file_size_original = meta["file_size_original"]
        p.file_size_compressed = meta["file_size_compressed"]
    if author_ids is not None:
        ids = json.loads(author_ids)
        authors = []
        for aid in ids:
            a = await db.get(Author, aid)
            if a:
                authors.append(a)
        p.authors = authors
    await db.commit()
    return await _load(db, pid)


@router.delete("/{pid}", status_code=204)
async def delete_proposal(pid: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(Proposal, pid)
    if not p:
        raise HTTPException(404, "Not found")
    delete_file(p.file_path)
    await db.delete(p)
    await db.commit()


@router.get("/{pid}/download")
async def download_proposal(pid: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(Proposal, pid)
    if not p or not p.file_path:
        raise HTTPException(404, "File not found")
    content = await read_file_bytes(p.file_path)
    return Response(content=content, media_type="application/octet-stream",
                    headers={"Content-Disposition": safe_content_disposition("attachment", p.original_filename or "file")})


@router.get("/{pid}/preview")
async def preview_proposal(pid: int, db: AsyncSession = Depends(get_db)):
    """Serve file for in-browser preview. PDF inline, DOCX converted to HTML."""
    from app.services.preview_service import docx_to_html
    p = await db.get(Proposal, pid)
    if not p or not p.file_path:
        raise HTTPException(404, "File not found")
    filename = p.original_filename or "file"
    name_lower = filename.lower()
    path_lower = (p.file_path or "").lower()

    is_docx = name_lower.endswith(".docx") or name_lower.endswith(".doc") or               path_lower.endswith(".docx.gz") or path_lower.endswith(".docx")
    is_pdf = name_lower.endswith(".pdf") or path_lower.endswith(".pdf.gz") or path_lower.endswith(".pdf")

    if is_docx:
        try:
            html = docx_to_html(p.file_path)
            return Response(
                content=html.encode("utf-8"),
                media_type="text/html; charset=utf-8",
                headers={"Content-Disposition": safe_content_disposition("inline", filename + ".html")},
            )
        except Exception:
            ext = name_lower.split(".")[-1] if "." in name_lower else "doc"
            fallback_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:sans-serif;display:flex;align-items:center;justify-content:center;
height:100vh;margin:0;background:#f8f9fa;color:#555;text-align:center;}}
.box{{padding:32px;}} .icon{{font-size:48px;margin-bottom:16px;}}
.title{{font-size:16px;font-weight:600;margin-bottom:8px;color:#333;}}
.sub{{font-size:13px;color:#888;}}</style></head>
<body><div class="box"><div class="icon">📎</div>
<div class="title">Предпросмотр недоступен</div>
<div class="sub">Формат .{ext} не поддерживается для просмотра.<br>Скачайте файл для открытия.</div>
</div></body></html>"""
            return Response(content=fallback_html.encode("utf-8"), media_type="text/html; charset=utf-8")
    if is_pdf:
        content = await read_file_bytes(p.file_path)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": safe_content_disposition("inline", filename)},
        )
    else:
        content = await read_file_bytes(p.file_path)
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": safe_content_disposition("attachment", filename)},
        )


# ── Certificate (Свидетельство) ───────────────────────────────────────────────

@router.post("/{pid}/certificate", status_code=201)
async def upload_proposal_certificate(
    pid: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload or replace the certificate for a proposal (one per proposal)."""
    p = await db.get(Proposal, pid)
    if not p:
        raise HTTPException(404, "Proposal not found")

    # Replace existing certificate if present
    r = await db.execute(
        select(ProposalCertificate).where(ProposalCertificate.proposal_id == pid)
    )
    existing = r.scalar_one_or_none()

    if existing:
        delete_file(existing.file_path)
        await db.delete(existing)
        await db.flush()

    meta = await save_file(file, "certificates", compress=True)
    cert = ProposalCertificate(
        proposal_id=pid,
        file_path=meta["file_path"],
        original_filename=meta["original_filename"],
        file_size_original=meta["file_size_original"],
        file_size_compressed=meta["file_size_compressed"],
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


@router.delete("/{pid}/certificate", status_code=204)
async def delete_proposal_certificate(pid: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(ProposalCertificate).where(ProposalCertificate.proposal_id == pid)
    )
    cert = r.scalar_one_or_none()
    if not cert:
        raise HTTPException(404, "Certificate not found")
    delete_file(cert.file_path)
    await db.delete(cert)
    await db.commit()


@router.get("/{pid}/certificate/download")
async def download_proposal_certificate(
    pid: int,
    inline: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(ProposalCertificate).where(ProposalCertificate.proposal_id == pid)
    )
    cert = r.scalar_one_or_none()
    if not cert or not cert.file_path:
        raise HTTPException(404, "Certificate not found")
    content = await read_file_bytes(cert.file_path)
    orig_lower = (cert.original_filename or "").lower()
    if inline and orig_lower.endswith(".pdf"):
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": safe_content_disposition("attachment", cert.original_filename or "certificate")},
    )


@router.get("/{pid}/certificate/preview")
async def preview_proposal_certificate(pid: int, db: AsyncSession = Depends(get_db)):
    """Preview certificate: PDF inline, DOCX→HTML, .doc→unavailable message."""
    from app.services.preview_service import docx_to_html
    r = await db.execute(
        select(ProposalCertificate).where(ProposalCertificate.proposal_id == pid)
    )
    cert = r.scalar_one_or_none()
    if not cert or not cert.file_path:
        raise HTTPException(404, "Certificate not found")

    orig_lower = (cert.original_filename or "").lower()
    path_lower = (cert.file_path or "").lower()

    is_docx = orig_lower.endswith(".docx") or path_lower.endswith(".docx.gz") or path_lower.endswith(".docx")
    is_doc_legacy = orig_lower.endswith(".doc") and not is_docx
    is_pdf = orig_lower.endswith(".pdf") or path_lower.endswith(".pdf.gz") or path_lower.endswith(".pdf")

    if is_doc_legacy:
        html = (
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            "<style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;"
            "height:100vh;margin:0;background:#f8f9fa;color:#555;text-align:center;}"
            ".box{padding:32px;}.icon{font-size:48px;margin-bottom:16px;}"
            ".title{font-size:16px;font-weight:600;margin-bottom:8px;color:#333;}"
            ".sub{font-size:13px;color:#888;line-height:1.6;}</style></head>"
            "<body><div class=\"box\"><div class=\"icon\">📎</div>"
            "<div class=\"title\">Предпросмотр недоступен</div>"
            "<div class=\"sub\">Формат .doc не поддерживается для просмотра.<br>"
            "Скачайте файл для открытия.</div></div></body></html>"
        )
        return Response(content=html.encode("utf-8"), media_type="text/html; charset=utf-8")

    if is_docx:
        try:
            html = docx_to_html(cert.file_path)
            return Response(content=html.encode("utf-8"), media_type="text/html; charset=utf-8")
        except Exception:
            html = (
                "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
                "<style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;"
                "height:100vh;margin:0;background:#f8f9fa;color:#555;text-align:center;}"
                ".box{padding:32px;}.icon{font-size:48px;margin-bottom:16px;}"
                ".title{font-size:16px;font-weight:600;margin-bottom:8px;color:#333;}"
                ".sub{font-size:13px;color:#888;}</style></head>"
                "<body><div class=\"box\"><div class=\"icon\">📎</div>"
                "<div class=\"title\">Предпросмотр недоступен</div>"
                "<div class=\"sub\">Файл не удалось открыть для предпросмотра.<br>"
                "Скачайте файл для открытия.</div></div></body></html>"
            )
            return Response(content=html.encode("utf-8"), media_type="text/html; charset=utf-8")

    if is_pdf:
        content = await read_file_bytes(cert.file_path)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    content = await read_file_bytes(cert.file_path)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": safe_content_disposition("attachment", cert.original_filename or "file")},
    )
