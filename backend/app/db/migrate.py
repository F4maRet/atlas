"""
Простой раннер SQL-миграций.

Файлы backend/migrations/NNN_*.sql применяются по порядку, каждый — один раз
(учёт в таблице schema_migrations). Все файлы написаны идемпотентно
(IF NOT EXISTS / WHERE NOT EXISTS), поэтому безопасно применяются и к базам,
где старая версия системы уже прогоняла их без учёта.

Файл выполняется целиком одним скриптом (а не разбивкой по «;», как раньше),
поэтому внутри можно использовать DO $$ ... $$ и строки с «;».
"""
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger("atlas.migrate")

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"
# Произвольный ключ advisory-lock, чтобы несколько воркеров не мигрировали одновременно
_LOCK_KEY = 74_271_001


async def run_migrations(engine: AsyncEngine, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    files = sorted(p for p in migrations_dir.glob("*.sql") if p.name[:3].isdigit())
    applied_now: list[str] = []

    async with engine.connect() as conn:
        raw = await conn.get_raw_connection()
        pg = raw.driver_connection  # asyncpg.Connection
        await pg.execute("SELECT pg_advisory_lock($1)", _LOCK_KEY)
        try:
            await pg.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " filename VARCHAR(255) PRIMARY KEY,"
                " applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
            )
            done = {r["filename"] for r in await pg.fetch("SELECT filename FROM schema_migrations")}
            for f in files:
                if f.name in done:
                    continue
                logger.info("Применяется миграция %s", f.name)
                async with pg.transaction():
                    await pg.execute(f.read_text(encoding="utf-8"))
                    await pg.execute("INSERT INTO schema_migrations (filename) VALUES ($1)", f.name)
                applied_now.append(f.name)
        finally:
            await pg.execute("SELECT pg_advisory_unlock($1)", _LOCK_KEY)
    return applied_now


async def mark_once(engine: AsyncEngine, key: str) -> bool:
    """Одноразовый флаг в schema_migrations. True — если флаг поставлен сейчас (действие ещё не выполнялось)."""
    async with engine.connect() as conn:
        raw = await conn.get_raw_connection()
        pg = raw.driver_connection
        status = await pg.execute(
            "INSERT INTO schema_migrations (filename) VALUES ($1) ON CONFLICT DO NOTHING", key
        )
        return status.endswith(" 1")
