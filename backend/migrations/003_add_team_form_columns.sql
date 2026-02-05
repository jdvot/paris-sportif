-- Migration 003: Add form and schedule columns to teams table
-- These columns track team form, rest days, and fixture congestion

-- Add form column (e.g., "WWDLW" for last 5 matches)
ALTER TABLE teams ADD COLUMN IF NOT EXISTS form VARCHAR(10);

-- Add form_score column (0-1 normalized score from form string)
ALTER TABLE teams ADD COLUMN IF NOT EXISTS form_score DECIMAL(4,3);

-- Add last_match_date column (when team last played)
ALTER TABLE teams ADD COLUMN IF NOT EXISTS last_match_date TIMESTAMP;

-- Add rest_days column (days since last match)
ALTER TABLE teams ADD COLUMN IF NOT EXISTS rest_days INTEGER;

-- Add fixture_congestion column (matches in last 14 days / 4, capped at 1.0)
ALTER TABLE teams ADD COLUMN IF NOT EXISTS fixture_congestion DECIMAL(4,3);

-- Verify columns were added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'teams'
  AND column_name IN ('form', 'form_score', 'last_match_date', 'rest_days', 'fixture_congestion')
ORDER BY column_name;
