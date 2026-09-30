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
  email_preference    BOOLEAN DEFAULT TRUE,
  push_preference     BOOLEAN DEFAULT TRUE,
  sms_preference      BOOLEAN DEFAULT FALSE,
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

-- Push subscriptions (web push + Expo mobile tokens)
CREATE TABLE IF NOT EXISTS push_subscriptions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doctor_id         UUID REFERENCES doctors(id) ON DELETE CASCADE,
  subscription_json JSONB NOT NULL,
  expo_token        TEXT,
  platform          TEXT CHECK (platform IN ('ios', 'android', 'web')),
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(doctor_id, subscription_json)
);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_doctor
  ON push_subscriptions (doctor_id);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_expo_token
  ON push_subscriptions (expo_token) WHERE expo_token IS NOT NULL;

-- Notification message history / campaign log (formerly whatsapp_messages)
CREATE TABLE IF NOT EXISTS notification_campaigns (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_type    TEXT NOT NULL CHECK (message_type IN ('article_notification', 'manual_message')),
  channel         TEXT NOT NULL CHECK (channel IN ('email', 'push', 'sms', 'whatsapp', 'multi')),
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
CREATE TABLE IF NOT EXISTS notification_delivery_logs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id     UUID REFERENCES notification_campaigns(id) ON DELETE CASCADE,
  doctor_id       UUID REFERENCES doctors(id) ON DELETE SET NULL,
  channel         TEXT NOT NULL,
  contact_info    TEXT,
  status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'failed')),
  error_message   TEXT,
  sent_at         TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Doctor bookmarks
-- ============================================================
CREATE TABLE IF NOT EXISTS bookmarks (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doctor_id   UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
  paper_id    UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(doctor_id, paper_id)
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_doctor
  ON bookmarks (doctor_id);

CREATE INDEX IF NOT EXISTS idx_bookmarks_paper
  ON bookmarks (paper_id);

-- ============================================================
-- Admin users (replaces shared ADMIN_PASSWORD over time)
-- ============================================================
CREATE TABLE IF NOT EXISTS admin_users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT UNIQUE NOT NULL,
  password_hash   TEXT NOT NULL,
  name            TEXT NOT NULL,
  role            TEXT DEFAULT 'admin' CHECK (role IN ('admin', 'super_admin')),
  is_active       BOOLEAN DEFAULT TRUE,
  last_login_at   TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- JWT refresh tokens for doctor API auth (rotation pattern)
-- ============================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doctor_id   UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
  jti         TEXT UNIQUE NOT NULL,
  revoked     BOOLEAN DEFAULT FALSE,
  expires_at  TIMESTAMPTZ NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_doctor_jti
  ON refresh_tokens (doctor_id, jti) WHERE revoked = FALSE;

-- ============================================================
-- Serverless-compatible rate limiting
-- ============================================================
CREATE TABLE IF NOT EXISTS rate_limits (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key         TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_key_created
  ON rate_limits (key, created_at);

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
