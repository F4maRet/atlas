-- Migration: add original_filename to conclusions
-- Without this, an uploaded (non-generated) conclusion always downloaded as "conclusion.docx",
-- losing the file name the user actually uploaded.
ALTER TABLE conclusions ADD COLUMN IF NOT EXISTS original_filename VARCHAR(500);
