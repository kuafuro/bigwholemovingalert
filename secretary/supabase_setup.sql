-- Run this in your Supabase SQL Editor

-- Whale alerts (written by whale.py / form144.py / institutional.py)
CREATE TABLE IF NOT EXISTS whale_alerts (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source      TEXT,
    ticker      TEXT,
    company_name TEXT,
    action      TEXT,
    reporter_name TEXT,
    shares      NUMERIC,
    total_value NUMERIC,
    price       NUMERIC,
    change_pct  NUMERIC,
    sec_link    TEXT UNIQUE,
    extra_data  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whale_alerts_created_at ON whale_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_whale_alerts_ticker     ON whale_alerts(ticker);

-- Creates the secretary_tasks table

CREATE TABLE IF NOT EXISTS secretary_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    chat_id TEXT,                          -- Telegram chat_id for member isolation
    title TEXT NOT NULL,
    due_date DATE,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_tasks_completed ON secretary_tasks(completed);
CREATE INDEX IF NOT EXISTS idx_tasks_chat_id ON secretary_tasks(chat_id);

-- Migration: if table already exists, add chat_id column
-- ALTER TABLE secretary_tasks ADD COLUMN IF NOT EXISTS chat_id TEXT;
-- CREATE INDEX IF NOT EXISTS idx_tasks_chat_id ON secretary_tasks(chat_id);

-- Per-member settings (Google Calendar token, display name, etc.)
CREATE TABLE IF NOT EXISTS member_settings (
    chat_id TEXT PRIMARY KEY,
    display_name TEXT,
    google_token_b64 TEXT,              -- base64 Google Calendar OAuth token
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
