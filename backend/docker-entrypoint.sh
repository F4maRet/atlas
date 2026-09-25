#!/bin/sh
# Каталог загрузок мог быть создан старой версией от root — отдаём его пользователю
# atlas и запускаем приложение уже без привилегий root.
set -e
if [ "$(id -u)" = "0" ]; then
    mkdir -p "${UPLOAD_DIR:-/app/uploads}"
    if [ "$(stat -c %u "${UPLOAD_DIR:-/app/uploads}")" != "1000" ]; then
        chown -R atlas:atlas "${UPLOAD_DIR:-/app/uploads}"
    fi
    export HOME=/home/atlas  # setpriv не меняет HOME, а asyncpg читает ~/.postgresql
    exec setpriv --reuid=atlas --regid=atlas --init-groups "$@"
fi
exec "$@"
