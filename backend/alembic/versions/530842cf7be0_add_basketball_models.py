"""add_basketball_models

Revision ID: 530842cf7be0
Revises: 438d0fd7a51a
Create Date: 2026-02-06 13:31:04.827748

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "530842cf7be0"
down_revision: str | Sequence[str] | None = "438d0fd7a51a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Tennis tables
    op.create_table(
        "tennis_players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("country", sa.String(50), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("atp_ranking", sa.Integer(), nullable=True),
        sa.Column("wta_ranking", sa.Integer(), nullable=True),
        sa.Column("circuit", sa.String(10), server_default="ATP"),
        sa.Column("elo_hard", sa.Numeric(6, 1), server_default="1500.0"),
        sa.Column("elo_clay", sa.Numeric(6, 1), server_default="1500.0"),
        sa.Column("elo_grass", sa.Numeric(6, 1), server_default="1500.0"),
        sa.Column("elo_indoor", sa.Numeric(6, 1), server_default="1500.0"),
        sa.Column("win_rate_ytd", sa.Numeric(5, 2), nullable=True),
        sa.Column("matches_played_ytd", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_tennis_players_external_id", "tennis_players", ["external_id"], unique=True)

    op.create_table(
        "tennis_tournaments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("surface", sa.String(20), nullable=False),
        sa.Column("country", sa.String(50), nullable=True),
        sa.Column("circuit", sa.String(10), server_default="ATP"),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_tennis_tournaments_external_id", "tennis_tournaments", ["external_id"], unique=True
    )

    op.create_table(
        "tennis_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("player1_id", sa.Integer(), sa.ForeignKey("tennis_players.id"), nullable=False),
        sa.Column("player2_id", sa.Integer(), sa.ForeignKey("tennis_players.id"), nullable=False),
        sa.Column(
            "tournament_id", sa.Integer(), sa.ForeignKey("tennis_tournaments.id"), nullable=False
        ),
        sa.Column("round", sa.String(30), nullable=True),
        sa.Column("match_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("surface", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="scheduled"),
        sa.Column("winner_id", sa.Integer(), nullable=True),
        sa.Column("score", sa.String(50), nullable=True),
        sa.Column("sets_player1", sa.Integer(), nullable=True),
        sa.Column("sets_player2", sa.Integer(), nullable=True),
        sa.Column("odds_player1", sa.Numeric(5, 2), nullable=True),
        sa.Column("odds_player2", sa.Numeric(5, 2), nullable=True),
        sa.Column("pred_player1_prob", sa.Numeric(5, 4), nullable=True),
        sa.Column("pred_player2_prob", sa.Numeric(5, 4), nullable=True),
        sa.Column("pred_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("pred_explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_tennis_matches_external_id", "tennis_matches", ["external_id"], unique=True)
    op.create_index("ix_tennis_matches_match_date", "tennis_matches", ["match_date"])
    op.create_index("ix_tennis_matches_date_status", "tennis_matches", ["match_date", "status"])
    op.create_index(
        "ix_tennis_matches_tournament", "tennis_matches", ["tournament_id", "match_date"]
    )

    # Basketball tables
    op.create_table(
        "basketball_teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("short_name", sa.String(10), nullable=True),
        sa.Column("country", sa.String(50), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("league", sa.String(20), server_default="NBA"),
        sa.Column("conference", sa.String(20), nullable=True),
        sa.Column("division", sa.String(30), nullable=True),
        sa.Column("elo_rating", sa.Numeric(6, 1), server_default="1500.0"),
        sa.Column("offensive_rating", sa.Numeric(5, 1), nullable=True),
        sa.Column("defensive_rating", sa.Numeric(5, 1), nullable=True),
        sa.Column("pace", sa.Numeric(5, 1), nullable=True),
        sa.Column("wins", sa.Integer(), server_default="0"),
        sa.Column("losses", sa.Integer(), server_default="0"),
        sa.Column("win_rate_ytd", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_points_scored", sa.Numeric(5, 1), nullable=True),
        sa.Column("avg_points_allowed", sa.Numeric(5, 1), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_basketball_teams_external_id", "basketball_teams", ["external_id"], unique=True
    )

    op.create_table(
        "basketball_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column(
            "home_team_id", sa.Integer(), sa.ForeignKey("basketball_teams.id"), nullable=False
        ),
        sa.Column(
            "away_team_id", sa.Integer(), sa.ForeignKey("basketball_teams.id"), nullable=False
        ),
        sa.Column("league", sa.String(20), nullable=False),
        sa.Column("season", sa.String(20), nullable=True),
        sa.Column("match_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="scheduled"),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("home_q1", sa.Integer(), nullable=True),
        sa.Column("away_q1", sa.Integer(), nullable=True),
        sa.Column("home_q2", sa.Integer(), nullable=True),
        sa.Column("away_q2", sa.Integer(), nullable=True),
        sa.Column("home_q3", sa.Integer(), nullable=True),
        sa.Column("away_q3", sa.Integer(), nullable=True),
        sa.Column("home_q4", sa.Integer(), nullable=True),
        sa.Column("away_q4", sa.Integer(), nullable=True),
        sa.Column("home_ot", sa.Integer(), nullable=True),
        sa.Column("away_ot", sa.Integer(), nullable=True),
        sa.Column("odds_home", sa.Numeric(5, 2), nullable=True),
        sa.Column("odds_away", sa.Numeric(5, 2), nullable=True),
        sa.Column("spread", sa.Numeric(5, 1), nullable=True),
        sa.Column("over_under", sa.Numeric(5, 1), nullable=True),
        sa.Column("is_back_to_back_home", sa.Boolean(), server_default="false"),
        sa.Column("is_back_to_back_away", sa.Boolean(), server_default="false"),
        sa.Column("pred_home_prob", sa.Numeric(5, 4), nullable=True),
        sa.Column("pred_away_prob", sa.Numeric(5, 4), nullable=True),
        sa.Column("pred_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("pred_explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_basketball_matches_external_id", "basketball_matches", ["external_id"], unique=True
    )
    op.create_index("ix_basketball_matches_match_date", "basketball_matches", ["match_date"])
    op.create_index(
        "ix_basketball_matches_date_status", "basketball_matches", ["match_date", "status"]
    )
    op.create_index("ix_basketball_matches_league", "basketball_matches", ["league", "match_date"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_basketball_matches_league", table_name="basketball_matches")
    op.drop_index("ix_basketball_matches_date_status", table_name="basketball_matches")
    op.drop_index("ix_basketball_matches_match_date", table_name="basketball_matches")
    op.drop_index("ix_basketball_matches_external_id", table_name="basketball_matches")
    op.drop_table("basketball_matches")

    op.drop_index("ix_basketball_teams_external_id", table_name="basketball_teams")
    op.drop_table("basketball_teams")

    op.drop_index("ix_tennis_matches_tournament", table_name="tennis_matches")
    op.drop_index("ix_tennis_matches_date_status", table_name="tennis_matches")
    op.drop_index("ix_tennis_matches_match_date", table_name="tennis_matches")
    op.drop_index("ix_tennis_matches_external_id", table_name="tennis_matches")
    op.drop_table("tennis_matches")

    op.drop_index("ix_tennis_tournaments_external_id", table_name="tennis_tournaments")
    op.drop_table("tennis_tournaments")

    op.drop_index("ix_tennis_players_external_id", table_name="tennis_players")
    op.drop_table("tennis_players")
