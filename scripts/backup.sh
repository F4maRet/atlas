#!/bin/sh
# Резервная копия СНД «АТЛАС»: дамп БД + все загруженные файлы.
#   ./scripts/backup.sh [каталог]        (по умолчанию ./backups)
# Восстановление — см. README, раздел «Резервное копирование».
set -eu
cd "$(dirname "$0")/.."
[ -f .env ] && . ./.env
OUT="${1:-./backups}"
STAMP="$(date +%Y-%m-%d_%H-%M)"
mkdir -p "$OUT"

echo "→ Дамп базы данных…"
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-atlas_user}" -Fc "${POSTGRES_DB:-atlas}" > "$OUT/atlas_db_$STAMP.dump"

echo "→ Архив загруженных файлов…"
docker compose exec -T backend tar -C /app -czf - uploads > "$OUT/atlas_uploads_$STAMP.tar.gz"

echo "Готово: $OUT/atlas_db_$STAMP.dump, $OUT/atlas_uploads_$STAMP.tar.gz"
