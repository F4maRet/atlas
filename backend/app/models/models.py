from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, Boolean, Date, BigInteger, UniqueConstraint
import json
from datetime import date

from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin

# ── Many-to-many: authors ↔ articles / proposals / software ─────────────────

article_authors = Table(
    "article_authors", Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

proposal_authors = Table(
    "proposal_authors", Base.metadata,
    Column("proposal_id", Integer, ForeignKey("proposals.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

software_authors = Table(
    "software_authors", Base.metadata,
    Column("software_id", Integer, ForeignKey("software.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

conference_participants = Table(
    "conference_participants", Base.metadata,
    Column("conference_id", Integer, ForeignKey("conferences.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)


# ── Author ────────────────────────────────────────────────────────────────────

class Author(Base, TimestampMixin):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, unique=True)
    short_name = Column(String(100))
    email = Column(String(255))
    organization = Column(String(500))
    position = Column(String(255))

    articles = relationship("Article", secondary=article_authors, back_populates="authors", passive_deletes=True)
    proposals = relationship("Proposal", secondary=proposal_authors, back_populates="authors", passive_deletes=True)
    software = relationship("Software", secondary=software_authors, back_populates="authors", passive_deletes=True)
    conferences = relationship("Conference", secondary=conference_participants, back_populates="participants",
                               passive_deletes=True)


# ── Collection (Сборник) ──────────────────────────────────────────────────────

class Collection(Base, TimestampMixin):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    university = Column(String(500))
    date_start = Column(Date)
    date_end = Column(Date)
    url = Column(Text)
    photo_path = Column(String(500))
    description = Column(Text)

    articles = relationship("Article", back_populates="collection", passive_deletes=True)

    @property
    def photo_url(self):
        from app.api.common import photo_url
        return photo_url(self.photo_path)

    @property
    def is_past(self):
        return self.date_end < date.today() if self.date_end else None


# ── Article (Научная статья) ──────────────────────────────────────────────────

class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(1000), nullable=False)
    article_type = Column(String(100))
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="SET NULL"), nullable=True)
    catalog = Column(String(500))
    file_path = Column(String(500))
    original_filename = Column(String(500))
    file_size_original = Column(BigInteger, default=0)
    file_size_compressed = Column(BigInteger, default=0)
    preview_path = Column(String(500))
    lead_author_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"), nullable=True)

    collection = relationship("Collection", back_populates="articles")
    authors = relationship("Author", secondary=article_authors, back_populates="articles", passive_deletes=True)
    conclusion = relationship("Conclusion", back_populates="article", uselist=False,
                              cascade="all, delete-orphan", passive_deletes=True)
    lead_author = relationship("Author", foreign_keys=[lead_author_id])

    @property
    def has_file(self):
        return bool(self.file_path)

    @property
    def has_conclusion(self):
        return self.conclusion is not None

    @property
    def conclusion_has_file(self):
        return bool(self.conclusion and self.conclusion.file_path)

    @property
    def conclusion_generated(self):
        return bool(self.conclusion and self.conclusion.generated_from_template)


# ── Proposal (Рац предложение) ────────────────────────────────────────────────

class Proposal(Base, TimestampMixin):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(1000), nullable=False)
    proposal_type = Column(String(100))
    catalog = Column(String(500))
    file_path = Column(String(500))
    original_filename = Column(String(500))
    file_size_original = Column(BigInteger, default=0)
    file_size_compressed = Column(BigInteger, default=0)

    authors = relationship("Author", secondary=proposal_authors, back_populates="proposals", passive_deletes=True)
    certificate = relationship("ProposalCertificate", back_populates="proposal", uselist=False,
                               cascade="all, delete-orphan", passive_deletes=True)

    @property
    def has_file(self):
        return bool(self.file_path)


# ── Software (Программное обеспечение) ────────────────────────────────────────

class Software(Base, TimestampMixin):
    __tablename__ = "software"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(1000), nullable=False)
    software_type = Column(String(100))
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="SET NULL"), nullable=True)
    catalog = Column(String(500))
    file_path = Column(String(500))
    original_filename = Column(String(500))
    file_size_original = Column(BigInteger, default=0)
    file_size_compressed = Column(BigInteger, default=0)
    file_structure = Column(Text)

    collection = relationship("Collection")
    authors = relationship("Author", secondary=software_authors, back_populates="software", passive_deletes=True)
    documents = relationship("SoftwareDocument", back_populates="software", cascade="all, delete-orphan",
                             passive_deletes=True,
                             order_by="SoftwareDocument.id")

    @property
    def has_file(self):
        return bool(self.file_path)

    @property
    def tree(self):
        try:
            return json.loads(self.file_structure) if self.file_structure else []
        except ValueError:
            return []

    @property
    def files_count(self):
        if not self.file_structure:
            return None
        from app.services.file_service import count_tree_files
        return count_tree_files(self.tree)


# ── Conclusion ────────────────────────────────────────────────────────────────

class Conclusion(Base, TimestampMixin):
    __tablename__ = "conclusions"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), unique=True)
    file_path = Column(String(500))
    original_filename = Column(String(500))
    generated_from_template = Column(Boolean, default=False)
    template_id = Column(Integer, ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text)

    article = relationship("Article", back_populates="conclusion")
    template = relationship("DocumentTemplate")

    @property
    def has_file(self):
        return bool(self.file_path)


# ── ProposalCertificate (Свидетельство для рац. предложения) ──────────────────

class ProposalCertificate(Base, TimestampMixin):
    __tablename__ = "proposal_certificates"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id", ondelete="CASCADE"), unique=True)
    file_path = Column(String(500))
    original_filename = Column(String(500))
    file_size_original = Column(BigInteger, default=0)
    file_size_compressed = Column(BigInteger, default=0)

    proposal = relationship("Proposal", back_populates="certificate")


# ── SoftwareDocument (комплект документов ПО) ─────────────────────────────────

class SoftwareDocument(Base, TimestampMixin):
    __tablename__ = "software_documents"

    id = Column(Integer, primary_key=True, index=True)
    software_id = Column(Integer, ForeignKey("software.id", ondelete="CASCADE"))
    doc_type = Column(String(100), nullable=False)
    file_path = Column(String(500))
    original_filename = Column(String(500))
    file_size_original = Column(BigInteger, default=0)
    file_size_compressed = Column(BigInteger, default=0)

    software = relationship("Software", back_populates="documents")


# ── DocumentTemplate ──────────────────────────────────────────────────────────

class DocumentTemplate(Base, TimestampMixin):
    __tablename__ = "document_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    doc_type = Column(String(100))
    file_path = Column(String(500))
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    @property
    def has_file(self):
        return bool(self.file_path)


# ── Conference ────────────────────────────────────────────────────────────────

class Conference(Base, TimestampMixin):
    __tablename__ = "conferences"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(1000), nullable=False)
    organizer = Column(String(500))
    date_start = Column(Date)
    date_end = Column(Date)
    url = Column(Text)
    photo_path = Column(String(500))
    description = Column(Text)
    location = Column(String(500))
    is_online = Column(Boolean, default=False)
    source = Column(String(100), default="manual")

    participants = relationship("Author", secondary=conference_participants, back_populates="conferences",
                                passive_deletes=True)

    @property
    def photo_url(self):
        from app.api.common import photo_url
        return photo_url(self.photo_path)


# ── Catalog (папки хранения для статей / рац. предложений / ПО) ───────────────

class Catalog(Base, TimestampMixin):
    __tablename__ = "catalogs"
    __table_args__ = (UniqueConstraint("scope", "name"),)

    id = Column(Integer, primary_key=True)
    scope = Column(String(32), nullable=False)
    name = Column(String(500), nullable=False)
