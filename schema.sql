-- ============================================================
-- Tunes Pharma — Doctor Portal Schema
-- Run this in your Supabase SQL Editor (supabase.com > SQL Editor)
-- ============================================================

-- Doctors registered by admin
CREATE TABLE IF NOT EXISTS doctors (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  email         TEXT,
  phone         TEXT,
  hospital      TEXT,
  specialty     TEXT,
  is_active     BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Research papers / articles / links uploaded by admin
CREATE TABLE IF NOT EXISTS papers (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title         TEXT NOT NULL,
  description   TEXT,
  content_type  TEXT NOT NULL CHECK (content_type IN ('pdf', 'doc', 'link')),
  file_url      TEXT NOT NULL,
  therapy_area  TEXT DEFAULT 'all' CHECK (therapy_area IN ('diabetes', 'neuropathy', 'gastro', 'general', 'all')),
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- In-app notifications: one row per doctor per paper
CREATE TABLE IF NOT EXISTS notifications (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doctor_id   UUID REFERENCES doctors(id) ON DELETE CASCADE,
  paper_id    UUID REFERENCES papers(id) ON DELETE CASCADE,
  is_read     BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- AI chat history per doctor (rolling messages array)
CREATE TABLE IF NOT EXISTS ai_chats (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doctor_id   UUID REFERENCES doctors(id) ON DELETE CASCADE UNIQUE,
  messages    JSONB NOT NULL DEFAULT '[]',
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Storage bucket (run ONCE — creates the 'papers' bucket)
-- ============================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('papers', 'papers', TRUE)
ON CONFLICT DO NOTHING;

-- Allow public read on the papers bucket
CREATE POLICY IF NOT EXISTS "papers_public_read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'papers');

-- Allow authenticated service-role write
CREATE POLICY IF NOT EXISTS "papers_service_write"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'papers');
