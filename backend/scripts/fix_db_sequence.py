"""
Fix PostgreSQL sequence for matches table.

This script resolves the "null value in column id" error by ensuring
the matches table has a properly configured auto-increment sequence.

Usage:
    python scripts/fix_db_sequence.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.db.database import engine


async def fix_matches_sequence():
    """Fix the matches table auto-increment sequence."""

    sql_commands = [
        # Create sequence if it doesn't exist
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'matches_id_seq') THEN
                CREATE SEQUENCE matches_id_seq;
                RAISE NOTICE 'Created sequence matches_id_seq';
            END IF;
        END $$;
        """,
        # Set sequence to max ID + 1
        """
        SELECT setval('matches_id_seq', COALESCE((SELECT MAX(id) FROM matches), 0) + 1, false);
        """,
        # Set default value
        """
        ALTER TABLE matches ALTER COLUMN id SET DEFAULT nextval('matches_id_seq');
        """,
        # Set sequence owner
        """
        ALTER SEQUENCE matches_id_seq OWNED BY matches.id;
        """,
    ]

    try:
        async with engine.begin() as conn:
            print("🔧 Fixing matches table sequence...")

            for i, sql in enumerate(sql_commands, 1):
                print(f"  Step {i}/4: Executing...")
                await conn.execute(text(sql))
                print(f"  ✅ Step {i} complete")

            # Verify the fix
            result = await conn.execute(
                text(
                    """
                    SELECT column_default
                    FROM information_schema.columns
                    WHERE table_name = 'matches' AND column_name = 'id';
                    """
                )
            )
            default_value = result.scalar()

            print(f"\n✅ Fix completed!")
            print(f"Column default: {default_value}")

            if "nextval" in str(default_value):
                print("✅ Auto-increment is properly configured")
            else:
                print("⚠️  Warning: Auto-increment may not be configured correctly")

            # Get next ID that will be used
            result = await conn.execute(text("SELECT nextval('matches_id_seq');"))
            next_id = result.scalar()
            print(f"Next match ID will be: {next_id}")

            # Rollback the test nextval()
            await conn.execute(text(f"SELECT setval('matches_id_seq', {next_id - 1});"))

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("=== Match Table Sequence Fix ===\n")
    asyncio.run(fix_matches_sequence())
    print("\n✅ You can now insert matches without ID errors")
