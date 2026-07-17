-- Add certificate support for proposals
CREATE TABLE IF NOT EXISTS proposal_certificates (
    id                   SERIAL PRIMARY KEY,
    proposal_id          INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE UNIQUE,
    file_path            VARCHAR(500),
    original_filename    VARCHAR(500),
    file_size_original   BIGINT DEFAULT 0,
    file_size_compressed BIGINT DEFAULT 0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proposal_certificates_proposal ON proposal_certificates(proposal_id);

-- Add certificate doc type to software seed data
INSERT INTO document_templates (name, doc_type, description, is_active)
VALUES ('Свидетельство о государственной регистрации', 'certificate', 'Свидетельство о регистрации ПО', TRUE)
ON CONFLICT DO NOTHING;
