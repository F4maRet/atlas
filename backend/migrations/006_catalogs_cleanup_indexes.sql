-- 006: постоянные каталоги, чистка дублей, недостающие индексы

-- Каталоги раньше жили только в браузере: пустой каталог пропадал после
-- перезагрузки страницы. Теперь они хранятся в БД (scope = articles|proposals|software).
CREATE TABLE IF NOT EXISTS catalogs (
    id          SERIAL PRIMARY KEY,
    scope       VARCHAR(32)  NOT NULL,
    name        VARCHAR(500) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (scope, name)
);

-- Пустая строка и NULL означали одно и то же «без каталога» — приводим к NULL
UPDATE articles  SET catalog = NULL WHERE catalog IS NOT NULL AND btrim(catalog) = '';
UPDATE proposals SET catalog = NULL WHERE catalog IS NOT NULL AND btrim(catalog) = '';
UPDATE software  SET catalog = NULL WHERE catalog IS NOT NULL AND btrim(catalog) = '';

-- Дубли шаблонов-заглушек (без файла), которые плодил старый код при каждом старте
DELETE FROM document_templates t
USING document_templates d
WHERE t.name = d.name AND t.doc_type = d.doc_type
  AND t.id > d.id AND t.file_path IS NULL;

-- Один документ каждого типа на ПО (дубли, если были, оставляем самые свежие)
DELETE FROM software_documents t
USING software_documents d
WHERE t.software_id = d.software_id AND t.doc_type = d.doc_type AND t.id < d.id;
CREATE UNIQUE INDEX IF NOT EXISTS uq_software_documents_type ON software_documents(software_id, doc_type);

-- Индексы под обратные связи «автор → работы» и выборки по внешним ключам
CREATE INDEX IF NOT EXISTS idx_article_authors_author  ON article_authors(author_id);
CREATE INDEX IF NOT EXISTS idx_proposal_authors_author ON proposal_authors(author_id);
CREATE INDEX IF NOT EXISTS idx_software_authors_author ON software_authors(author_id);
CREATE INDEX IF NOT EXISTS idx_articles_lead_author    ON articles(lead_author_id);
CREATE INDEX IF NOT EXISTS idx_software_collection     ON software(collection_id);
