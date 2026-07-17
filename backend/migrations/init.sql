-- СНД «АТЛАС» — инициализация базы данных

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Authors
CREATE TABLE IF NOT EXISTS authors (
    id          SERIAL PRIMARY KEY,
    full_name   VARCHAR(255) NOT NULL UNIQUE,
    short_name  VARCHAR(100),
    email       VARCHAR(255),
    organization VARCHAR(500),
    position    VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Collections (Сборники)
CREATE TABLE IF NOT EXISTS collections (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(500) NOT NULL,
    university  VARCHAR(500),
    date_start  DATE,
    date_end    DATE,
    url         TEXT,
    photo_path  VARCHAR(500),
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Articles
CREATE TABLE IF NOT EXISTS articles (
    id                   SERIAL PRIMARY KEY,
    title                VARCHAR(1000) NOT NULL,
    article_type         VARCHAR(100),
    collection_id        INTEGER REFERENCES collections(id) ON DELETE SET NULL,
    catalog              VARCHAR(500),
    file_path            VARCHAR(500),
    original_filename    VARCHAR(500),
    file_size_original   BIGINT DEFAULT 0,
    file_size_compressed BIGINT DEFAULT 0,
    preview_path         VARCHAR(500),
    lead_author_id       INTEGER REFERENCES authors(id) ON DELETE SET NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Proposals (Рац предложения)
CREATE TABLE IF NOT EXISTS proposals (
    id                   SERIAL PRIMARY KEY,
    title                VARCHAR(1000) NOT NULL,
    proposal_type        VARCHAR(100),
    catalog              VARCHAR(500),
    file_path            VARCHAR(500),
    original_filename    VARCHAR(500),
    file_size_original   BIGINT DEFAULT 0,
    file_size_compressed BIGINT DEFAULT 0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Software
CREATE TABLE IF NOT EXISTS software (
    id                   SERIAL PRIMARY KEY,
    title                VARCHAR(1000) NOT NULL,
    software_type        VARCHAR(100),
    collection_id        INTEGER REFERENCES collections(id) ON DELETE SET NULL,
    catalog              VARCHAR(500),
    file_path            VARCHAR(500),
    original_filename    VARCHAR(500),
    file_size_original   BIGINT DEFAULT 0,
    file_size_compressed BIGINT DEFAULT 0,
    file_structure       TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Document Templates
CREATE TABLE IF NOT EXISTS document_templates (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(500) NOT NULL,
    doc_type    VARCHAR(100),
    file_path   VARCHAR(500),
    description TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Conclusions (Заключения об открытом публиковании)
CREATE TABLE IF NOT EXISTS conclusions (
    id                       SERIAL PRIMARY KEY,
    article_id               INTEGER NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    file_path                VARCHAR(500),
    generated_from_template  BOOLEAN DEFAULT FALSE,
    template_id              INTEGER REFERENCES document_templates(id) ON DELETE SET NULL,
    notes                    TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Software Documents (7 документов)
CREATE TABLE IF NOT EXISTS software_documents (
    id                   SERIAL PRIMARY KEY,
    software_id          INTEGER NOT NULL REFERENCES software(id) ON DELETE CASCADE,
    doc_type             VARCHAR(100) NOT NULL,
    file_path            VARCHAR(500),
    original_filename    VARCHAR(500),
    file_size_original   BIGINT DEFAULT 0,
    file_size_compressed BIGINT DEFAULT 0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Conferences
CREATE TABLE IF NOT EXISTS conferences (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(1000) NOT NULL,
    organizer   VARCHAR(500),
    date_start  DATE,
    date_end    DATE,
    url         TEXT,
    photo_path  VARCHAR(500),
    description TEXT,
    location    VARCHAR(500),
    is_online   BOOLEAN DEFAULT FALSE,
    source      VARCHAR(100) DEFAULT 'manual',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Junction tables
CREATE TABLE IF NOT EXISTS article_authors (
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    author_id  INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, author_id)
);

CREATE TABLE IF NOT EXISTS proposal_authors (
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    author_id   INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    PRIMARY KEY (proposal_id, author_id)
);

CREATE TABLE IF NOT EXISTS software_authors (
    software_id INTEGER NOT NULL REFERENCES software(id) ON DELETE CASCADE,
    author_id   INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    PRIMARY KEY (software_id, author_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_articles_collection ON articles(collection_id);
CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_proposals_created ON proposals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_software_created ON software(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conferences_date ON conferences(date_start);
CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(full_name);

-- Seed default document templates
INSERT INTO document_templates (name, doc_type, description, is_active)
VALUES
  ('Заключение об открытом публиковании (стандарт)', 'conclusion', 'Стандартный шаблон заключения', TRUE),
  ('Аннотация программы', 'annotation', 'Шаблон аннотации для ПО', TRUE),
  ('Заявление на регистрацию', 'registration', 'Заявление на регистрацию ПО', TRUE),
  ('Описание программы', 'description', 'Техническое описание программы', TRUE),
  ('Руководство пользователя', 'manual', 'Руководство пользователя', TRUE),
  ('Акт приёма и ввода в эксплуатацию', 'act', 'Акт для ввода ПО в эксплуатацию', TRUE),
  ('Реферат по исходникам', 'abstract', 'Реферат исходного кода', TRUE),
  ('Листинг по исходникам', 'listing', 'Листинг исходного кода', TRUE)
ON CONFLICT DO NOTHING;
