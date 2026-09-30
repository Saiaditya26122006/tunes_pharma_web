-- ============================================================
-- Migration 002: Doctor Platform
-- Run this in your Supabase SQL Editor AFTER migration 001.
--
-- This migration is ADDITIVE and IDEMPOTENT — it uses
-- CREATE TABLE IF NOT EXISTS and ADD COLUMN IF NOT EXISTS
-- throughout. Safe to run multiple times.
--
-- Background: The original production schema (pre-Stage 1) only
-- contained: doctors, papers, notifications, ai_chats,
-- whatsapp_messages, whatsapp_delivery_log, + storage bucket.
--
-- Stage 1 migration 001 added: admin_users, refresh_tokens,
-- rate_limits.
--
-- This migration adds everything else the application code
-- expects: notification preference columns on doctors,
-- notification_campaigns, notification_delivery_logs,
-- push_subscriptions, and bookmarks.
-- ============================================================

-- ── 1. Doctor preference columns ────────────────────────────
-- The notification engine and profile service read these columns.
-- Original doctors table did not have them.

ALTER TABLE doctors
  ADD COLUMN IF NOT EXISTS email_preference BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS push_preference  BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS sms_preference   BOOLEAN DEFAULT FALSE;

-- ── 2. Notification campaigns ───────────────────────────────
-- Multi-channel campaign log used by notification_engine.py
-- and admin notification history routes.
-- (Replaces the legacy whatsapp_messages table for new campaigns.)

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

-- ── 3. Notification delivery logs ───────────────────────────
-- Per-recipient delivery log linked to a campaign.

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

-- ── 4. Push subscriptions ───────────────────────────────────
-- Web push + Expo mobile tokens. Used by notification_engine.py
-- (web push via subscription_json) and push_service.py (Expo
-- tokens via expo_token column).

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

-- ── 5. Bookmarks ────────────────────────────────────────────
-- Doctors can bookmark published articles for later reference.

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

-- ── Rollback notes ──────────────────────────────────────────
-- To reverse this migration:
--   DROP TABLE IF EXISTS bookmarks;
--   DROP TABLE IF EXISTS push_subscriptions;
--   DROP TABLE IF EXISTS notification_delivery_logs;
--   DROP TABLE IF EXISTS notification_campaigns;
--   ALTER TABLE doctors DROP COLUMN IF EXISTS email_preference;
--   ALTER TABLE doctors DROP COLUMN IF EXISTS push_preference;
--   ALTER TABLE doctors DROP COLUMN IF EXISTS sms_preference;
