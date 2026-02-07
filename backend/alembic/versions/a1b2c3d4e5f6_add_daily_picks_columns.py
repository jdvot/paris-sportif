"""Add model_details, is_daily_pick, pick_rank to tennis/basketball matches.

Revision ID: a1b2c3d4e5f6
Revises: 530842cf7be0
Create Date: 2026-02-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "530842cf7be0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add daily picks and model_details columns."""
    # Tennis matches
    op.add_column("tennis_matches", sa.Column("model_details", sa.JSON(), nullable=True))
    op.add_column(
        "tennis_matches",
        sa.Column("is_daily_pick", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("tennis_matches", sa.Column("pick_rank", sa.Integer(), nullable=True))

    # Basketball matches
    op.add_column("basketball_matches", sa.Column("model_details", sa.JSON(), nullable=True))
    op.add_column(
        "basketball_matches",
        sa.Column("is_daily_pick", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("basketball_matches", sa.Column("pick_rank", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove daily picks and model_details columns."""
    op.drop_column("basketball_matches", "pick_rank")
    op.drop_column("basketball_matches", "is_daily_pick")
    op.drop_column("basketball_matches", "model_details")
    op.drop_column("tennis_matches", "pick_rank")
    op.drop_column("tennis_matches", "is_daily_pick")
    op.drop_column("tennis_matches", "model_details")
