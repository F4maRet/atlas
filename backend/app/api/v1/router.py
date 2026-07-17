from fastapi import APIRouter, Depends
from app.api.v1.endpoints import (
    auth, authors, collections, articles, proposals,
    software, conferences, reports, documents, templates
)
from app.core.security import require_auth

api_router = APIRouter()

# Публичный роутер — без него никто не сможет залогиниться
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Всё остальное закрыто общим паролем (см. app/core/security.py)
protected = [Depends(require_auth)]
api_router.include_router(authors.router, prefix="/authors", tags=["authors"], dependencies=protected)
api_router.include_router(collections.router, prefix="/collections", tags=["collections"], dependencies=protected)
api_router.include_router(articles.router, prefix="/articles", tags=["articles"], dependencies=protected)
api_router.include_router(proposals.router, prefix="/proposals", tags=["proposals"], dependencies=protected)
api_router.include_router(software.router, prefix="/software", tags=["software"], dependencies=protected)
api_router.include_router(conferences.router, prefix="/conferences", tags=["conferences"], dependencies=protected)
api_router.include_router(reports.router, prefix="/reports", tags=["reports"], dependencies=protected)
api_router.include_router(documents.router, prefix="/documents", tags=["documents"], dependencies=protected)
api_router.include_router(templates.router, prefix="/templates", tags=["templates"], dependencies=protected)
