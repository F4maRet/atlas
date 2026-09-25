"""
Интеграционные тесты API. Нужна пустая тестовая БД PostgreSQL:

    ATLAS_TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/atlas_test pytest

ВНИМАНИЕ: схема public тестовой БД полностью пересоздаётся.
"""
import asyncio
import io
import os
import tempfile

import pytest

TEST_DB = os.environ.get("ATLAS_TEST_DATABASE_URL")
if not TEST_DB:
    pytest.skip("ATLAS_TEST_DATABASE_URL не задан — интеграционные тесты пропущены", allow_module_level=True)

os.environ["DATABASE_URL"] = TEST_DB
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="atlas-test-uploads-")
os.environ["ADMIN_PASSWORD"] = "пароль-теста"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["MAX_FILE_SIZE_MB"] = "1"
os.environ["ALLOWED_ORIGINS"] = "http://localhost,http://localhost:80"


def _reset_schema():
    import asyncpg

    async def run():
        dsn = TEST_DB.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn)
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        await conn.close()

    asyncio.run(run())


@pytest.fixture(scope="session")
def client():
    _reset_schema()
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth(client):
    r = client.post("/api/v1/auth/login", json={"password": "пароль-теста"})
    assert r.status_code == 200, r.text
    return client


def make_docx(text: str = "Hello") -> bytes:
    from docx import Document
    d = Document()
    d.add_paragraph(text)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def make_zip(files: dict) -> bytes:
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for k, v in files.items():
            z.writestr(k, v)
    return buf.getvalue()


PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n" + b"x" * 500
