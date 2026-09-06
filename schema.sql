-- ============================================================
-- Tunes Pharma — Doctor Portal + Admin Management Schema
-- Run this in your Supabase SQL Editor (supabase.com > SQL Editor)
-- ============================================================

-- Doctors registered by admin
CREATE TABLE IF NOT EXISTS doctors (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                TEXT NOT NULL,
  username            TEXT UNIQUE NOT NULL,
  password_hash       TEXT NOT NULL,
  email               TEXT,
  phone               TEXT,
  whatsapp_number     TEXT,
  hospital            TEXT,
  specialty           TEXT,
  is_active           BOOLEAN DEFAULT TRUE,
  whatsapp_consent    BOOLEAN DEFAULT FALSE,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Research papers / articles / links uploaded by admin
CREATE TABLE IF NOT EXISTS papers (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title         TEXT NOT NULL,
  description   TEXT,
  content_type  TEXT NOT NULL CHECK (content_type IN ('pdf', 'doc', 'link')),
  file_url      TEXT NOT NULL,
  therapy_area  TEXT DEFAULT 'all' CHECK (therapy_area IN ('diabetes', 'neuropathy', 'gastro', 'general', 'all')),
  status        TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  author        TEXT,
  category      TEXT DEFAULT 'General',
  thumbnail_url TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  published_at  TIMESTAMPTZ
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

-- WhatsApp message history / campaign log
CREATE TABLE IF NOT EXISTS whatsapp_messages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_type    TEXT NOT NULL CHECK (message_type IN ('article_notification', 'manual_message')),
  paper_id        UUID REFERENCES papers(id) ON DELETE SET NULL,
  message_body    TEXT NOT NULL,
  recipient_count INTEGER DEFAULT 0,
  success_count   INTEGER DEFAULT 0,
  fail_count      INTEGER DEFAULT 0,
  status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'partial', 'failed')),
  error_details   JSONB DEFAULT '[]',
  sent_by         TEXT DEFAULT 'system',
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Per-recipient delivery log (linked to a campaign)
CREATE TABLE IF NOT EXISTS whatsapp_delivery_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id      UUID REFERENCES whatsapp_messages(id) ON DELETE CASCADE,
  doctor_id       UUID REFERENCES doctors(id) ON DELETE SET NULL,
  whatsapp_number TEXT,
  status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'failed')),
  error_message   TEXT,
  sent_at         TIMESTAMPTZ DEFAULT NOW()
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
