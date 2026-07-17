import gzip
import shutil
import zipfile
import json
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException

from app.core.config import settings


COMPRESSIBLE_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/json",
    "text/html",
    "text/xml",
    "application/xml",
}

ZIP_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
}


def _unique_filename(original: str, subdir: str) -> tuple[str, str]:
    """Returns (storage_path, unique_filename)"""
    ext = Path(original).suffix.lower()
    uid = uuid.uuid4().hex[:12]
    unique_name = f"{uid}{ext}"
    storage_path = os.path.join(settings.UPLOAD_DIR, subdir, unique_name)
    return storage_path, unique_name


async def save_file(
    upload: UploadFile,
    subdir: str,
    compress: bool = True,
) -> dict:
    """
    Save uploaded file with optional gzip compression.
    Returns metadata dict with paths and sizes.
    """
    original_filename = upload.filename or "file"
    content = await upload.read()
    original_size = len(content)

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if original_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Файл «{original_filename}» слишком большой "
                f"({original_size / 1024 / 1024:.1f} МБ). "
                f"Максимально допустимый размер: {settings.MAX_FILE_SIZE_MB} МБ."
            ),
        )

    # Determine whether to compress
    content_type = upload.content_type or ""
    should_compress = compress and content_type in COMPRESSIBLE_TYPES

    if should_compress:
        storage_path, unique_name = _unique_filename(original_filename, subdir)
        gz_path = storage_path + ".gz"
        with gzip.open(gz_path, "wb", compresslevel=6) as f:
            f.write(content)
        compressed_size = os.path.getsize(gz_path)
        return {
            "file_path": gz_path,
            "original_filename": original_filename,
            "file_size_original": original_size,
            "file_size_compressed": compressed_size,
            "compressed": True,
        }
    else:
        storage_path, unique_name = _unique_filename(original_filename, subdir)
        with open(storage_path, "wb") as f:
            f.write(content)
        file_size = os.path.getsize(storage_path)
        return {
            "file_path": storage_path,
            "original_filename": original_filename,
            "file_size_original": original_size,
            "file_size_compressed": file_size,
            "compressed": False,
        }


async def read_file_bytes(file_path: str) -> bytes:
    """Read file, decompressing if needed."""
    if file_path.endswith(".gz"):
        with gzip.open(file_path, "rb") as f:
            return f.read()
    with open(file_path, "rb") as f:
        return f.read()


def delete_file(file_path: Optional[str]) -> None:
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


def _unpack_gz_to_temp(gz_path: str) -> str:
    """Decompress a .gz file to a temp file and return its path. Caller must unlink."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with gzip.open(gz_path, "rb") as gz:
            shutil.copyfileobj(gz, tmp)
    finally:
        tmp.close()
    return tmp.name


def get_zip_structure(zip_path: str) -> list:
    """Parse ZIP archive and return file tree as JSON-serializable list."""
    tmp_path = None
    real_path = zip_path
    if zip_path.endswith(".gz"):
        real_path = tmp_path = _unpack_gz_to_temp(zip_path)

    tree = {}
    try:
        with zipfile.ZipFile(real_path, "r") as zf:
            for name in sorted(zf.namelist()):
                parts = name.split("/")
                node = tree
                for part in parts[:-1]:
                    if part:
                        node = node.setdefault(part, {})
                if parts[-1]:
                    node[parts[-1]] = None
    finally:
        if tmp_path:
            os.unlink(tmp_path)

    return _dict_to_tree(tree, "")


def _dict_to_tree(d: dict, path: str) -> list:
    nodes = []
    for key, val in d.items():
        full = f"{path}/{key}" if path else key
        if val is None:
            nodes.append({"name": key, "path": full, "type": "file"})
        else:
            nodes.append({
                "name": key,
                "path": full,
                "type": "dir",
                "children": _dict_to_tree(val, full),
            })
    return nodes


async def read_file_from_zip(zip_path: str, inner_path: str) -> bytes:
    """Read a specific file from inside a ZIP (possibly gzip-compressed)."""
    tmp_path = None
    real_path = zip_path
    if zip_path.endswith(".gz"):
        real_path = tmp_path = _unpack_gz_to_temp(zip_path)

    try:
        with zipfile.ZipFile(real_path, "r") as zf:
            return zf.read(inner_path)
    finally:
        if tmp_path:
            os.unlink(tmp_path)
