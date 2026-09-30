-- ============================================================
-- Migration 003: Add missing columns to papers table
-- Run this in your Supabase SQL Editor AFTER migration 002.
--
-- The production papers table was created with only:
--   id, title, description, content_type, file_url, therapy_area, created_at
--
-- The application code (article_service.py, feed_service.py,
-- admin routes) expects these additional columns:
--   status, published_at, author, category, thumbnail_url
--
-- ADDITIVE and IDEMPOTENT — safe to run multiple times.
-- ============================================================

ALTER TABLE papers
  ADD COLUMN IF NOT EXISTS status        TEXT DEFAULT 'published' CHECK (status IN ('draft', 'published', 'archived')),
  ADD COLUMN IF NOT EXISTS author        TEXT,
  ADD COLUMN IF NOT EXISTS category      TEXT DEFAULT 'General',
  ADD COLUMN IF NOT EXISTS thumbnail_url TEXT,
  ADD COLUMN IF NOT EXISTS published_at  TIMESTAMPTZ;

-- Backfill: set published_at to created_at for existing rows
-- that don't have it set yet, and ensure status is 'published'
-- for all existing content (they were published before the
-- status column existed).
UPDATE papers
  SET published_at = created_at
  WHERE published_at IS NULL;

-- ── Rollback notes ──────────────────────────────────────────
-- To reverse this migration:
--   ALTER TABLE papers DROP COLUMN IF EXISTS status;
--   ALTER TABLE papers DROP COLUMN IF EXISTS author;
--   ALTER TABLE papers DROP COLUMN IF EXISTS category;
--   ALTER TABLE papers DROP COLUMN IF EXISTS thumbnail_url;
--   ALTER TABLE papers DROP COLUMN IF EXISTS published_at;
