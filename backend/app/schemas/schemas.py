from datetime import date, datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Author ────────────────────────────────────────────────────────────────────

class AuthorBase(BaseModel):
    full_name: str = Field(max_length=255)
    short_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    organization: Optional[str] = Field(None, max_length=500)
    position: Optional[str] = Field(None, max_length=255)

    @field_validator("full_name", "short_name", "email", "organization", "position", mode="before")
    @classmethod
    def _strip(cls, v):
        if isinstance(v, str):
            v = " ".join(v.split())
            return v or None
        return v


class AuthorCreate(AuthorBase):
    pass


class AuthorUpdate(AuthorBase):
    full_name: Optional[str] = Field(None, max_length=255)


class AuthorOut(AuthorBase, ORM):
    id: int
    created_at: datetime


class AuthorStats(AuthorOut):
    articles_count: int = 0
    proposals_count: int = 0
    software_count: int = 0
    conferences_count: int = 0
    total: int = 0


class AuthorMerge(BaseModel):
    into_id: int


class WorkItem(BaseModel):
    type: str
    id: int
    title: str
    subtitle: Optional[str] = None
    date: Optional[date | datetime] = None


class AuthorWorks(BaseModel):
    author: AuthorOut
    articles: List[WorkItem] = []
    proposals: List[WorkItem] = []
    software: List[WorkItem] = []
    conferences: List[WorkItem] = []


# ── Collection ────────────────────────────────────────────────────────────────

class CollectionBrief(ORM):
    id: int
    name: str


class CollectionOut(ORM):
    id: int
    name: str
    university: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    url: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime
    is_past: Optional[bool] = None
    articles_count: int = 0


# ── Article ───────────────────────────────────────────────────────────────────

class ArticleOut(ORM):
    id: int
    title: str
    article_type: Optional[str] = None
    collection_id: Optional[int] = None
    catalog: Optional[str] = None
    original_filename: Optional[str] = None
    file_size_original: int = 0
    file_size_compressed: int = 0
    has_file: bool = False
    created_at: datetime
    lead_author_id: Optional[int] = None
    authors: List[AuthorOut] = []
    collection: Optional[CollectionBrief] = None
    has_conclusion: bool = False
    conclusion_has_file: bool = False
    conclusion_generated: bool = False


# ── Proposal ──────────────────────────────────────────────────────────────────

class ProposalCertificateOut(ORM):
    id: int
    proposal_id: int
    original_filename: Optional[str] = None
    file_size_original: int = 0
    file_size_compressed: int = 0
    created_at: datetime


class ProposalOut(ORM):
    id: int
    title: str
    proposal_type: Optional[str] = None
    catalog: Optional[str] = None
    original_filename: Optional[str] = None
    file_size_original: int = 0
    file_size_compressed: int = 0
    has_file: bool = False
    created_at: datetime
    authors: List[AuthorOut] = []
    certificate: Optional[ProposalCertificateOut] = None


# ── Software ──────────────────────────────────────────────────────────────────

class SoftwareDocumentOut(ORM):
    id: int
    doc_type: str
    original_filename: Optional[str] = None
    file_size_original: int = 0
    file_size_compressed: int = 0
    created_at: datetime


class SoftwareOut(ORM):
    id: int
    title: str
    software_type: Optional[str] = None
    collection_id: Optional[int] = None
    catalog: Optional[str] = None
    original_filename: Optional[str] = None
    file_size_original: int = 0
    file_size_compressed: int = 0
    has_file: bool = False
    files_count: Optional[int] = None
    created_at: datetime
    authors: List[AuthorOut] = []
    documents: List[SoftwareDocumentOut] = []


class SoftwareStructure(BaseModel):
    id: int
    tree: List[Any] = []


# ── Conclusion ────────────────────────────────────────────────────────────────

class ConclusionOut(ORM):
    id: int
    article_id: int
    original_filename: Optional[str] = None
    has_file: bool = False
    generated_from_template: bool = False
    template_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime


# ── DocumentTemplate ──────────────────────────────────────────────────────────

class TemplateOut(ORM):
    id: int
    name: str
    doc_type: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    has_file: bool = False
    created_at: datetime


# ── Conference ────────────────────────────────────────────────────────────────

class ConferenceOut(ORM):
    id: int
    title: str
    organizer: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    url: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_online: bool = False
    photo_url: Optional[str] = None
    source: Optional[str] = "manual"
    created_at: datetime
    participants: List[AuthorOut] = []


# ── Catalogs ──────────────────────────────────────────────────────────────────

class CatalogOut(BaseModel):
    name: str
    count: int = 0


class CatalogCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)



class CatalogMove(BaseModel):
    ids: List[int]
    catalog: Optional[str] = None  # None / "" — убрать из каталога


# ── Reports ───────────────────────────────────────────────────────────────────

class PublicationPlanItem(BaseModel):
    type: str  # article | proposal | software
    id: int
    title: str
    subtype: Optional[str] = None
    authors: List[str]
    collection_name: Optional[str] = None
    created_at: datetime


class SearchHit(BaseModel):
    type: str
    id: int
    title: str
    subtitle: Optional[str] = None
