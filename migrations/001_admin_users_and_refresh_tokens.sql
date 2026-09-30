-- ============================================================
-- Migration 001: admin_users, refresh_tokens, rate_limits
-- Run this in your Supabase SQL Editor AFTER the base schema.sql
-- This migration is ADDITIVE — it creates new tables only.
-- ============================================================

-- Admin users (replaces shared ADMIN_PASSWORD over time)
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

-- JWT refresh tokens for doctor API auth (rotation pattern)
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

-- Serverless-compatible rate limiting
CREATE TABLE IF NOT EXISTS rate_limits (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key         TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_key_created
  ON rate_limits (key, created_at);

-- Periodic cleanup: delete expired refresh tokens and old rate limit entries.
-- Run this as a cron job or Supabase Edge Function on a schedule.
-- DELETE FROM refresh_tokens WHERE expires_at < NOW();
-- DELETE FROM rate_limits WHERE created_at < NOW() - INTERVAL '1 hour';
