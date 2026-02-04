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
-- 3. Fix matches.match_date column type (TEXT -> TIMESTAMP WITH TIME ZONE)
-- ============================================================================
DO $$
DECLARE
    col_type TEXT;
BEGIN
    SELECT data_type INTO col_type
    FROM information_schema.columns
    WHERE table_name = 'matches' AND column_name = 'match_date';

    IF col_type = 'text' OR col_type = 'character varying' THEN
        ALTER TABLE matches ALTER COLUMN match_date TYPE TIMESTAMP WITH TIME ZONE
            USING match_date::TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Converted match_date from % to TIMESTAMP WITH TIME ZONE', col_type;
    ELSIF col_type = 'timestamp without time zone' THEN
        ALTER TABLE matches ALTER COLUMN match_date TYPE TIMESTAMP WITH TIME ZONE
            USING match_date AT TIME ZONE 'UTC';
        RAISE NOTICE 'Converted match_date to TIMESTAMP WITH TIME ZONE';
    ELSE
        RAISE NOTICE 'match_date column type is already: %', col_type;
    END IF;
END $$;

-- ============================================================================
-- 4. Add missing columns to predictions table
-- ============================================================================
DO $$
BEGIN
    -- home_prob
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'home_prob') THEN
        ALTER TABLE predictions ADD COLUMN home_prob NUMERIC(5,4);
        RAISE NOTICE 'Added home_prob column';
    END IF;

    -- draw_prob
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'draw_prob') THEN
        ALTER TABLE predictions ADD COLUMN draw_prob NUMERIC(5,4);
        RAISE NOTICE 'Added draw_prob column';
    END IF;

    -- away_prob
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'away_prob') THEN
        ALTER TABLE predictions ADD COLUMN away_prob NUMERIC(5,4);
        RAISE NOTICE 'Added away_prob column';
    END IF;

    -- predicted_outcome
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'predicted_outcome') THEN
        ALTER TABLE predictions ADD COLUMN predicted_outcome VARCHAR(10);
        RAISE NOTICE 'Added predicted_outcome column';
    END IF;

    -- confidence
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'confidence') THEN
        ALTER TABLE predictions ADD COLUMN confidence NUMERIC(5,4);
        RAISE NOTICE 'Added confidence column';
    END IF;

    -- value_score
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'value_score') THEN
        ALTER TABLE predictions ADD COLUMN value_score NUMERIC(6,4);
        RAISE NOTICE 'Added value_score column';
    END IF;

    -- is_daily_pick
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'is_daily_pick') THEN
        ALTER TABLE predictions ADD COLUMN is_daily_pick BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_daily_pick column';
    END IF;

    -- pick_rank
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'pick_rank') THEN
        ALTER TABLE predictions ADD COLUMN pick_rank INTEGER;
        RAISE NOTICE 'Added pick_rank column';
    END IF;

    -- pick_score
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'pick_score') THEN
        ALTER TABLE predictions ADD COLUMN pick_score NUMERIC(6,4);
        RAISE NOTICE 'Added pick_score column';
    END IF;

    -- explanation
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'explanation') THEN
        ALTER TABLE predictions ADD COLUMN explanation TEXT;
        RAISE NOTICE 'Added explanation column';
    END IF;

    -- key_factors
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'key_factors') THEN
        ALTER TABLE predictions ADD COLUMN key_factors TEXT;
        RAISE NOTICE 'Added key_factors column';
    END IF;

    -- risk_factors
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'risk_factors') THEN
        ALTER TABLE predictions ADD COLUMN risk_factors TEXT;
        RAISE NOTICE 'Added risk_factors column';
    END IF;

    -- model_details
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'model_details') THEN
        ALTER TABLE predictions ADD COLUMN model_details TEXT;
        RAISE NOTICE 'Added model_details column';
    END IF;

    -- llm_adjustments
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'llm_adjustments') THEN
        ALTER TABLE predictions ADD COLUMN llm_adjustments TEXT;
        RAISE NOTICE 'Added llm_adjustments column';
    END IF;

    -- created_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'created_at') THEN
        ALTER TABLE predictions ADD COLUMN created_at TIMESTAMP DEFAULT NOW();
        RAISE NOTICE 'Added created_at column';
    END IF;

    -- updated_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'predictions' AND column_name = 'updated_at') THEN
        ALTER TABLE predictions ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
        RAISE NOTICE 'Added updated_at column';
    END IF;
END $$;

-- ============================================================================
-- 5. Create index for daily picks if not exists
-- ============================================================================
CREATE INDEX IF NOT EXISTS ix_predictions_daily_pick ON predictions(is_daily_pick, created_at);

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

-- Check matches.match_date type
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'matches' AND column_name = 'match_date';

-- Check predictions columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'predictions'
ORDER BY ordinal_position;
