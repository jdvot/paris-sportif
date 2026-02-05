-- Migration: Add favorite_team_id to user_preferences
-- Date: 2026-02-05
-- Description: Adds a foreign key reference to the teams table for user's favorite team

-- Add the column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences'
        AND column_name = 'favorite_team_id'
    ) THEN
        ALTER TABLE user_preferences
        ADD COLUMN favorite_team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL;

        COMMENT ON COLUMN user_preferences.favorite_team_id IS
            'Primary favorite team for homepage personalization';
    END IF;
END $$;

-- Create an index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_preferences_favorite_team
ON user_preferences(favorite_team_id)
WHERE favorite_team_id IS NOT NULL;
