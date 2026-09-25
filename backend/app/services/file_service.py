"""
Хранение загруженных файлов.

* Файлы лежат в UPLOAD_DIR/<subdir>/<uuid><ext>[.gz]; в БД хранится путь
  ОТНОСИТЕЛЬНО UPLOAD_DIR (раньше — абсолютный, такие записи тоже читаются).
* Текстовые/офисные форматы сжимаются gzip (решение — по расширению, а не по
  Content-Type от браузера, который для .docx/.doc часто присылает octet-stream).
* Уже сжатые форматы (zip, изображения) хранятся как есть.
* Все операции с диском выполняются в пуле потоков, чтобы не блокировать event loop.
"""
import gzip
import os
import re
import shutil
import unicodedata
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import IO, Iterator, Optional

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

CHUNK = 1024 * 1024

DOC_EXT = {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ZIP_EXT = {".zip"}
TEMPLATE_EXT = {".docx"}
COMPRESS_EXT = {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".xml", ".csv", ".json", ".md", ".html"}

SUBDIRS = ["articles", "proposals", "software", "documents", "certificates", "templates", "images"]

ZIP_MAX_ENTRIES = 20_000


def ensure_dirs() -> None:
    for sub in SUBDIRS:
        os.makedirs(os.path.join(settings.UPLOAD_DIR, sub), exist_ok=True)


def upload_root() -> Path:
    return Path(settings.UPLOAD_DIR).resolve()


def abs_path(stored: Optional[str]) -> Optional[Path]:
    """Путь из БД → абсолютный путь на диске (с проверкой, что он внутри UPLOAD_DIR)."""
    if not stored:
        return None
    root = upload_root()
    p = Path(stored)
    if not p.is_absolute():
        p = root / p
    elif not str(p.resolve()).startswith(str(root)):
        # Старые абсолютные пути из другого UPLOAD_DIR: берём часть после "uploads/"
        marker = "/uploads/"
        s = str(p)
        if marker in s:
            p = root / s.split(marker, 1)[1]
    p = p.resolve()
    if p != root and root not in p.parents:
        return None
    return p


def relative_path(p: Path) -> str:
    return str(p.resolve().relative_to(upload_root()))


def exists(stored: Optional[str]) -> bool:
    p = abs_path(stored)
    return bool(p and p.is_file())


def clean_filename(name: Optional[str], default: str = "file") -> str:
    """Имя файла для отображения/скачивания: без путей и управляющих символов."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in unicodedata.normalize("NFC", name) if unicodedata.category(ch)[0] != "C")
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    if not name:
        return default
    if len(name) > 200:
        stem, ext = os.path.splitext(name)
        name = stem[: 200 - len(ext)] + ext
    return name


def file_ext(name: Optional[str]) -> str:
    return Path(name or "").suffix.lower()


def _new_path(subdir: str, ext: str, gz: bool) -> Path:
    root = upload_root()
    d = root / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{uuid.uuid4().hex}{ext}{'.gz' if gz else ''}"


def _too_large(name: str, size: int) -> HTTPException:
    return HTTPException(
        413,
        f"Файл «{name}» слишком большой ({size / 1024 / 1024:.1f} МБ). "
        f"Максимально допустимый размер: {settings.MAX_FILE_SIZE_MB} МБ.",
    )


def _store_stream(src: IO[bytes], name: str, subdir: str, compress: bool) -> dict:
    ext = file_ext(name)
    gz = compress and ext in COMPRESS_EXT
    target = _new_path(subdir, ext, gz)
    size = 0
    limit = settings.max_file_bytes
    try:
        with (gzip.open(target, "wb", compresslevel=6) if gz else open(target, "wb")) as out:
            while chunk := src.read(CHUNK):
                size += len(chunk)
                if size > limit:
                    raise _too_large(name, size)
                out.write(chunk)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(400, f"Файл «{name}» пустой")
    return {
        "file_path": relative_path(target),
        "original_filename": name,
        "file_size_original": size,
        "file_size_compressed": target.stat().st_size,
        "compressed": gz,
    }


async def save_file(
    upload: UploadFile,
    subdir: str,
    compress: bool = True,
    allowed_ext: Optional[set[str]] = None,
) -> dict:
    """Сохранить загруженный файл. Возвращает метаданные (путь, имя, размеры)."""
    name = clean_filename(upload.filename)
    ext = file_ext(name)
    if allowed_ext is not None and ext not in allowed_ext:
        allowed = ", ".join(sorted(allowed_ext))
        raise HTTPException(400, f"Недопустимый формат «{ext or 'без расширения'}». Разрешены: {allowed}")
    await upload.seek(0)
    return await run_in_threadpool(_store_stream, upload.file, name, subdir, compress)


async def save_bytes(data: bytes, filename: str, subdir: str, compress: bool = True) -> dict:
    import io
    return await run_in_threadpool(_store_stream, io.BytesIO(data), clean_filename(filename), subdir, compress)


def open_stored(stored: str) -> IO[bytes]:
    p = abs_path(stored)
    if not p or not p.is_file():
        raise HTTPException(404, "Файл не найден в хранилище")
    return gzip.open(p, "rb") if p.name.endswith(".gz") else open(p, "rb")


def _read_all(stored: str) -> bytes:
    with open_stored(stored) as f:
        return f.read()


async def read_file_bytes(stored: str) -> bytes:
    """Прочитать файл целиком (с распаковкой gzip)."""
    return await run_in_threadpool(_read_all, stored)


def iter_file(stored: str) -> Iterator[bytes]:
    """Потоковое чтение (для StreamingResponse) — файл не грузится в память целиком."""
    f = open_stored(stored)
    try:
        while chunk := f.read(CHUNK):
            yield chunk
    finally:
        f.close()


def delete_file(stored: Optional[str]) -> None:
    p = abs_path(stored)
    if p and p.is_file():
        try:
            p.unlink()
        except OSError:
            pass


def copy_builtin(src: Path, subdir: str) -> str:
    target = _new_path(subdir, src.suffix.lower(), False)
    shutil.copy2(src, target)
    return relative_path(target)


# ── ZIP-архивы ПО ─────────────────────────────────────────────────────────────

def _open_zip(stored: str) -> zipfile.ZipFile:
    # GzipFile поддерживает seek, поэтому .zip.gz (старые загрузки) читаются
    # без распаковки во временный файл
    return zipfile.ZipFile(open_stored(stored), "r")


def _safe_member(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return bool(parts) and not name.startswith("/") and ".." not in parts


def get_zip_structure(stored: str) -> list:
    """Дерево файлов ZIP в виде JSON-совместимого списка (с размерами файлов)."""
    tree: dict = {}
    with _open_zip(stored) as zf:
        infos = zf.infolist()[:ZIP_MAX_ENTRIES]
        for info in sorted(infos, key=lambda i: i.filename.lower()):
            name = info.filename
            if not _safe_member(name) or name.startswith("__MACOSX/"):
                continue
            parts = [p for p in name.split("/") if p]
            node = tree
            for part in parts[:-1]:
                node = node.setdefault(part, {})
                if not isinstance(node, dict):  # файл и папка с одним именем
                    break
            else:
                if name.endswith("/"):
                    node.setdefault(parts[-1], {})
                else:
                    node[parts[-1]] = info.file_size
    return _dict_to_tree(tree, "")


def _dict_to_tree(d: dict, path: str) -> list:
    dirs, files = [], []
    for key, val in d.items():
        full = f"{path}/{key}" if path else key
        if isinstance(val, dict):
            dirs.append({"name": key, "path": full, "type": "dir", "children": _dict_to_tree(val, full)})
        else:
            files.append({"name": key, "path": full, "type": "file", "size": val})
    key = lambda n: n["name"].lower()  # noqa: E731
    return sorted(dirs, key=key) + sorted(files, key=key)


def count_tree_files(nodes: list) -> int:
    return sum(count_tree_files(n.get("children", [])) if n["type"] == "dir" else 1 for n in nodes or [])


def read_zip_member(stored: str, inner_path: str, max_bytes: int) -> tuple[bytes, int, bool]:
    """(содержимое не длиннее max_bytes, полный размер, обрезано ли)."""
    if not _safe_member(inner_path):
        raise HTTPException(400, "Некорректный путь")
    with _open_zip(stored) as zf:
        try:
            info = zf.getinfo(inner_path)
        except KeyError:
            raise HTTPException(404, "Файл в архиве не найден")
        with zf.open(info) as f:
            data = f.read(max_bytes + 1)
    return data[:max_bytes], info.file_size, len(data) > max_bytes
