from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    articles, auth, authors, catalogs, collections, conferences, documents, proposals, reports,
    software, templates,
)
from app.core.security import require_auth

api_router = APIRouter()

# Публичный роутер — без него никто не сможет залогиниться
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Всё остальное закрыто общим паролем (см. app/core/security.py)
protected = [Depends(require_auth)]
for module, prefix in (
    (authors, "/authors"),
    (collections, "/collections"),
    (articles, "/articles"),
    (proposals, "/proposals"),
    (software, "/software"),
    (conferences, "/conferences"),
    (reports, "/reports"),
    (documents, "/documents"),
    (templates, "/templates"),
    (catalogs, "/catalogs"),
):
    api_router.include_router(module.router, prefix=prefix, tags=[prefix.strip("/")], dependencies=protected)
