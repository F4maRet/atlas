-- Migration: add lead_author_id to articles
ALTER TABLE articles ADD COLUMN IF NOT EXISTS lead_author_id INTEGER REFERENCES authors(id) ON DELETE SET NULL;
