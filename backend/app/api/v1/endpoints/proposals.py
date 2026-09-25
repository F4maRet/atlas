from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.common import (
    clean_str, commit_and_cleanup, has_upload, load_authors, parse_ids, replace_file, require_str,
)
from app.db.session import get_db
from app.models.models import Proposal, ProposalCertificate
from app.schemas.schemas import ProposalCertificateOut, ProposalOut
from app.services.file_service import DOC_EXT, IMAGE_EXT, delete_file
from app.services.preview_service import download_response, preview_response

router = APIRouter()

CERT_EXT = DOC_EXT | IMAGE_EXT  # свидетельство часто — скан


async def _load(db: AsyncSession, pid: int) -> Proposal:
    p = await db.scalar(
        select(Proposal).options(selectinload(Proposal.authors), selectinload(Proposal.certificate))
        .where(Proposal.id == pid)
    )
    if not p:
        raise HTTPException(404, "Рац. предложение не найдено")
    return p


@router.get("/", response_model=List[ProposalOut])
async def list_proposals(db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Proposal).options(selectinload(Proposal.authors), selectinload(Proposal.certificate))
        .order_by(Proposal.created_at.desc())
    )
    return r.scalars().all()


@router.get("/{pid}", response_model=ProposalOut)
async def get_proposal(pid: int, db: AsyncSession = Depends(get_db)):
    return await _load(db, pid)


@router.post("/", response_model=ProposalOut, status_code=201)
async def create_proposal(
    title: str = Form(...),
    proposal_type: Optional[str] = Form(None),
    catalog: Optional[str] = Form(None),
    author_ids: str = Form("[]"),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    p = Proposal(
        title=require_str(title, "Название"),
        proposal_type=clean_str(proposal_type),
        catalog=clean_str(catalog),
        authors=await load_authors(db, parse_ids(author_ids)),
    )
    if has_upload(file):
        await replace_file(p, file, "proposals", DOC_EXT)
    db.add(p)
    try:
        await db.commit()
    except Exception:
        delete_file(p.file_path)
        raise
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
    p = await _load(db, pid)
    if title is not None:
        p.title = require_str(title, "Название")
    if proposal_type is not None:
        p.proposal_type = clean_str(proposal_type)
    if catalog is not None:
        p.catalog = clean_str(catalog)
    if author_ids is not None:
        p.authors = await load_authors(db, parse_ids(author_ids))
    old_file = await replace_file(p, file, "proposals", DOC_EXT) if has_upload(file) else None
    await commit_and_cleanup(db, old_file)
    return await _load(db, pid)


@router.delete("/{pid}", status_code=204)
async def delete_proposal(pid: int, db: AsyncSession = Depends(get_db)):
    p = await _load(db, pid)
    # Файл свидетельства раньше оставался на диске после удаления предложения
    paths = [p.file_path, p.certificate.file_path if p.certificate else None]
    await db.delete(p)
    await commit_and_cleanup(db, *paths)


@router.get("/{pid}/download")
async def download_proposal(pid: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(Proposal, pid)
    if not p or not p.file_path:
        raise HTTPException(404, "Файл не найден")
    return download_response(p.file_path, p.original_filename or "file")


@router.get("/{pid}/preview")
async def preview_proposal(pid: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(Proposal, pid)
    if not p or not p.file_path:
        raise HTTPException(404, "Файл не найден")
    return await preview_response(p.file_path, p.original_filename or "file")


# ── Свидетельство ─────────────────────────────────────────────────────────────

async def _get_cert(db: AsyncSession, pid: int) -> ProposalCertificate:
    cert = await db.scalar(select(ProposalCertificate).where(ProposalCertificate.proposal_id == pid))
    if not cert or not cert.file_path:
        raise HTTPException(404, "Свидетельство не найдено")
    return cert


@router.post("/{pid}/certificate", response_model=ProposalCertificateOut, status_code=201)
async def upload_proposal_certificate(pid: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Загрузить или заменить свидетельство (одно на предложение)."""
    if not await db.get(Proposal, pid):
        raise HTTPException(404, "Рац. предложение не найдено")
    cert = await db.scalar(select(ProposalCertificate).where(ProposalCertificate.proposal_id == pid))
    if cert is None:
        cert = ProposalCertificate(proposal_id=pid)
        db.add(cert)
    # раньше каталог uploads/certificates не создавался при старте — загрузка падала с 500
    old = await replace_file(cert, file, "certificates", CERT_EXT)
    await commit_and_cleanup(db, old)
    await db.refresh(cert)
    return cert


@router.delete("/{pid}/certificate", status_code=204)
async def delete_proposal_certificate(pid: int, db: AsyncSession = Depends(get_db)):
    cert = await db.scalar(select(ProposalCertificate).where(ProposalCertificate.proposal_id == pid))
    if not cert:
        raise HTTPException(404, "Свидетельство не найдено")
    path = cert.file_path
    await db.delete(cert)
    await commit_and_cleanup(db, path)


@router.get("/{pid}/certificate/download")
async def download_proposal_certificate(pid: int, db: AsyncSession = Depends(get_db)):
    cert = await _get_cert(db, pid)
    return download_response(cert.file_path, cert.original_filename or "certificate")


@router.get("/{pid}/certificate/preview")
async def preview_proposal_certificate(pid: int, db: AsyncSession = Depends(get_db)):
    cert = await _get_cert(db, pid)
    return await preview_response(cert.file_path, cert.original_filename or "certificate")
