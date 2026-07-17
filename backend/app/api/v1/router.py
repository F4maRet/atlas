from fastapi import APIRouter
from app.api.v1.endpoints import (
    authors, collections, articles, proposals,
    software, conferences, reports, documents, templates
)

api_router = APIRouter()

api_router.include_router(authors.router, prefix="/authors", tags=["authors"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
api_router.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
api_router.include_router(software.router, prefix="/software", tags=["software"])
api_router.include_router(conferences.router, prefix="/conferences", tags=["conferences"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
