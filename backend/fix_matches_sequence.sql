-- Fix matches table auto-increment sequence
-- This resolves the "null value in column id" error

-- 1. Check if sequence exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'matches_id_seq') THEN
        -- Create the sequence if it doesn't exist
        CREATE SEQUENCE matches_id_seq;
        RAISE NOTICE 'Created sequence matches_id_seq';
    END IF;
END $$;

-- 2. Set the sequence to the max existing ID + 1
SELECT setval('matches_id_seq', COALESCE((SELECT MAX(id) FROM matches), 0) + 1, false);

-- 3. Alter the table to use the sequence as default
ALTER TABLE matches ALTER COLUMN id SET DEFAULT nextval('matches_id_seq');

-- 4. Set the sequence owner to the column
ALTER SEQUENCE matches_id_seq OWNED BY matches.id;

-- 5. Verify the fix
SELECT
    'matches' as table_name,
    column_name,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'matches' AND column_name = 'id';

-- 6. Test: Get next value (don't commit this)
SELECT nextval('matches_id_seq') as next_id;
SELECT setval('matches_id_seq', currval('matches_id_seq') - 1); -- Rollback test

-- Expected output: column_default should be "nextval('matches_id_seq'::regclass)"
