-- Migration: 001_hotfix_schema.sql
-- Date: 2026-02-04
-- Description: Fix missing columns and timezone issues
-- Run this on production database IMMEDIATELY

-- ============================================================================
-- 1. Add logo_url column to teams table (if not exists)
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'teams' AND column_name = 'logo_url'
    ) THEN
        ALTER TABLE teams ADD COLUMN logo_url TEXT;
        RAISE NOTICE 'Added logo_url column to teams table';
    ELSE
        RAISE NOTICE 'logo_url column already exists';
    END IF;
END $$;

-- ============================================================================
-- 2. Alter cached_data columns to use TIMESTAMP WITH TIME ZONE
-- ============================================================================
ALTER TABLE cached_data
    ALTER COLUMN expires_at TYPE TIMESTAMP WITH TIME ZONE USING expires_at AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';

-- ============================================================================
-- Verification queries (run after migration)
-- ============================================================================
-- Check logo_url column exists
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'teams' AND column_name = 'logo_url';

-- Check cached_data timestamp columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'cached_data' AND column_name IN ('expires_at', 'created_at', 'updated_at');
