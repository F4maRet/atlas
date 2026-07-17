from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from datetime import datetime, date


# ── Author ────────────────────────────────────────────────────────────────────

class AuthorBase(BaseModel):
    full_name: str
    short_name: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    position: Optional[str] = None


class AuthorCreate(AuthorBase):
    pass


class AuthorUpdate(AuthorBase):
    full_name: Optional[str] = None


class AuthorOut(AuthorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AuthorStats(AuthorOut):
    articles_count: int = 0
    proposals_count: int = 0
    software_count: int = 0
    total: int = 0


# ── Collection ────────────────────────────────────────────────────────────────

class CollectionBase(BaseModel):
    name: str
    university: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    url: Optional[str] = None
    description: Optional[str] = None


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(CollectionBase):
    name: Optional[str] = None


class CollectionOut(CollectionBase):
    id: int
    photo_path: Optional[str] = None
    created_at: datetime
    is_past: Optional[bool] = None

    class Config:
        from_attributes = True


# ── Article ───────────────────────────────────────────────────────────────────

class ArticleBase(BaseModel):
    title: str
    article_type: Optional[str] = None
    collection_id: Optional[int] = None
    catalog: Optional[str] = None
    author_ids: List[int] = []


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(ArticleBase):
    title: Optional[str] = None
    author_ids: Optional[List[int]] = None


class ArticleOut(BaseModel):
    id: int
    title: str
    article_type: Optional[str]
    collection_id: Optional[int]
    catalog: Optional[str]
    file_path: Optional[str]
    original_filename: Optional[str]
    file_size_original: int
    file_size_compressed: int
    preview_path: Optional[str]
    created_at: datetime
    lead_author_id: Optional[int] = None
    authors: List[AuthorOut] = []
    collection: Optional[CollectionOut] = None
    has_conclusion: bool = False

    class Config:
        from_attributes = True


# ── Proposal ──────────────────────────────────────────────────────────────────

class ProposalBase(BaseModel):
    title: str
    proposal_type: Optional[str] = None
    catalog: Optional[str] = None
    author_ids: List[int] = []


class ProposalCreate(ProposalBase):
    pass


class ProposalUpdate(ProposalBase):
    title: Optional[str] = None
    author_ids: Optional[List[int]] = None


class ProposalCertificateOut(BaseModel):
    id: int
    proposal_id: int
    file_path: Optional[str]
    original_filename: Optional[str]
    file_size_original: int
    file_size_compressed: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProposalOut(BaseModel):
    id: int
    title: str
    proposal_type: Optional[str]
    catalog: Optional[str]
    file_path: Optional[str]
    original_filename: Optional[str]
    file_size_original: int
    file_size_compressed: int
    created_at: datetime
    authors: List[AuthorOut] = []
    certificate: Optional[ProposalCertificateOut] = None

    class Config:
        from_attributes = True


# ── Software ──────────────────────────────────────────────────────────────────

class SoftwareBase(BaseModel):
    title: str
    software_type: Optional[str] = None
    collection_id: Optional[int] = None
    catalog: Optional[str] = None
    author_ids: List[int] = []


class SoftwareCreate(SoftwareBase):
    pass


class SoftwareUpdate(SoftwareBase):
    title: Optional[str] = None
    author_ids: Optional[List[int]] = None


class SoftwareDocumentOut(BaseModel):
    id: int
    doc_type: str
    file_path: Optional[str]
    original_filename: Optional[str]
    file_size_original: int
    file_size_compressed: int
    created_at: datetime

    class Config:
        from_attributes = True


class SoftwareOut(BaseModel):
    id: int
    title: str
    software_type: Optional[str]
    collection_id: Optional[int]
    catalog: Optional[str]
    file_path: Optional[str]
    original_filename: Optional[str]
    file_size_original: int
    file_size_compressed: int
    file_structure: Optional[Any]
    created_at: datetime
    authors: List[AuthorOut] = []
    documents: List[SoftwareDocumentOut] = []

    class Config:
        from_attributes = True


# ── Conclusion ────────────────────────────────────────────────────────────────

class ConclusionOut(BaseModel):
    id: int
    article_id: int
    file_path: Optional[str]
    generated_from_template: bool
    template_id: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── DocumentTemplate ──────────────────────────────────────────────────────────

class TemplateBase(BaseModel):
    name: str
    doc_type: str
    description: Optional[str] = None
    is_active: bool = True


class TemplateCreate(TemplateBase):
    pass


class TemplateOut(TemplateBase):
    id: int
    file_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Conference ────────────────────────────────────────────────────────────────

class ConferenceBase(BaseModel):
    title: str
    organizer: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    url: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_online: bool = False


class ConferenceCreate(ConferenceBase):
    pass


class ConferenceUpdate(ConferenceBase):
    title: Optional[str] = None


class ConferenceOut(ConferenceBase):
    id: int
    photo_path: Optional[str]
    source: str
    created_at: datetime
    participants: List[AuthorOut] = []

    class Config:
        from_attributes = True


# ── Reports ───────────────────────────────────────────────────────────────────

class PublicationPlanItem(BaseModel):
    type: str  # article | proposal | software
    id: int
    title: str
    authors: List[str]
    collection_name: Optional[str]
    created_at: datetime
