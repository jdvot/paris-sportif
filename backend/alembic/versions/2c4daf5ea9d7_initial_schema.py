"""initial_schema

Revision ID: 2c4daf5ea9d7
Revises:
Create Date: 2026-02-06 13:09:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2c4daf5ea9d7"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for the Paris Sportif application."""
    # --- teams ---
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("short_name", sa.String(length=10), nullable=True),
        sa.Column("tla", sa.String(length=5), nullable=True),
        sa.Column("country", sa.String(length=50), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("elo_rating", sa.Numeric(precision=6, scale=1), nullable=False),
        sa.Column("avg_goals_scored_home", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("avg_goals_scored_away", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("avg_goals_conceded_home", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("avg_goals_conceded_away", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("avg_xg_for", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("avg_xg_against", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("form", sa.String(length=10), nullable=True),
        sa.Column("form_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("last_match_date", sa.DateTime(), nullable=True),
        sa.Column("rest_days", sa.Integer(), nullable=True),
        sa.Column("fixture_congestion", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_teams_external_id"), "teams", ["external_id"], unique=True)

    # --- competitions ---
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("country", sa.String(length=50), nullable=True),
        sa.Column("emblem_url", sa.Text(), nullable=True),
        sa.Column("current_season", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(
        op.f("ix_competitions_external_id"), "competitions", ["external_id"], unique=True
    )

    # --- matches ---
    op.create_table(
        "matches",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            server_default=sa.text("nextval('matches_id_seq')"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=50), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("competition_code", sa.String(length=10), nullable=False),
        sa.Column("match_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("matchday", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("home_score_ht", sa.Integer(), nullable=True),
        sa.Column("away_score_ht", sa.Integer(), nullable=True),
        sa.Column("home_xg", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("away_xg", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("odds_home", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("odds_draw", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("odds_away", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_matches_external_id"), "matches", ["external_id"], unique=True)
    op.create_index(op.f("ix_matches_competition_code"), "matches", ["competition_code"])
    op.create_index(op.f("ix_matches_match_date"), "matches", ["match_date"])
    op.create_index("ix_matches_status", "matches", ["status"])
    op.create_index("ix_matches_date_status", "matches", ["match_date", "status"])
    op.create_index("ix_matches_competition_date", "matches", ["competition_code", "match_date"])

    # --- predictions ---
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("home_prob", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("draw_prob", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("away_prob", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("predicted_outcome", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("value_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("is_daily_pick", sa.Boolean(), nullable=False),
        sa.Column("pick_rank", sa.Integer(), nullable=True),
        sa.Column("pick_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("key_factors", sa.Text(), nullable=True),
        sa.Column("risk_factors", sa.Text(), nullable=True),
        sa.Column("model_details", sa.Text(), nullable=True),
        sa.Column("llm_adjustments", sa.Text(), nullable=True),
        sa.Column("match_context_summary", sa.Text(), nullable=True),
        sa.Column("news_sources", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id"),
    )
    op.create_index("ix_predictions_daily_pick", "predictions", ["is_daily_pick", "created_at"])

    # --- prediction_results ---
    op.create_table(
        "prediction_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("actual_outcome", sa.String(length=10), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("value_captured", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("assigned_probability", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prediction_id"),
    )

    # --- news_items ---
    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("team_ids", sa.Text(), nullable=True),
        sa.Column("player_names", sa.Text(), nullable=True),
        sa.Column("is_injury_news", sa.Boolean(), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("impact_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("llm_analysis", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_news_published", "news_items", ["published_at"])
    op.create_index("ix_news_injury", "news_items", ["is_injury_news", "published_at"])

    # --- push_subscriptions ---
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh_key", sa.Text(), nullable=False),
        sa.Column("auth_key", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=True),
        sa.Column("daily_picks", sa.Boolean(), nullable=False),
        sa.Column("match_start", sa.Boolean(), nullable=False),
        sa.Column("result_updates", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    op.create_index(op.f("ix_push_subscriptions_user_id"), "push_subscriptions", ["user_id"])

    # --- cached_data ---
    op.create_table(
        "cached_data",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cache_key", sa.String(length=100), nullable=False),
        sa.Column("cache_type", sa.String(length=50), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index(op.f("ix_cached_data_cache_key"), "cached_data", ["cache_key"], unique=True)
    op.create_index(op.f("ix_cached_data_cache_type"), "cached_data", ["cache_type"])
    op.create_index(op.f("ix_cached_data_expires_at"), "cached_data", ["expires_at"])

    # --- standings ---
    op.create_table(
        "standings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competition_code", sa.String(length=10), nullable=False),
        sa.Column("season", sa.String(length=20), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("team_logo", sa.Text(), nullable=True),
        sa.Column("played_games", sa.Integer(), nullable=False),
        sa.Column("won", sa.Integer(), nullable=False),
        sa.Column("drawn", sa.Integer(), nullable=False),
        sa.Column("lost", sa.Integer(), nullable=False),
        sa.Column("goals_for", sa.Integer(), nullable=False),
        sa.Column("goals_against", sa.Integer(), nullable=False),
        sa.Column("goal_difference", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("form", sa.String(length=10), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_standings_competition", "standings", ["competition_code"])
    op.create_index(op.f("ix_standings_competition_code"), "standings", ["competition_code"])
    op.create_index("ix_standings_position", "standings", ["competition_code", "position"])
    op.create_index(
        "uq_standings_comp_team", "standings", ["competition_code", "team_id"], unique=True
    )

    # --- sync_log ---
    op.create_table(
        "sync_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sync_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("records_synced", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sync_log_sync_type"), "sync_log", ["sync_type"])
    op.create_index("ix_sync_log_type_date", "sync_log", ["sync_type", "started_at"])

    # --- ml_models ---
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_type", sa.String(length=50), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("accuracy", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("precision", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("recall", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("f1_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("training_samples", sa.Integer(), nullable=False),
        sa.Column("feature_columns", sa.Text(), nullable=True),
        sa.Column("hyperparameters", sa.Text(), nullable=True),
        sa.Column("model_binary", sa.LargeBinary(), nullable=True),
        sa.Column("scaler_binary", sa.LargeBinary(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("trained_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_name"),
    )
    op.create_index(op.f("ix_ml_models_model_name"), "ml_models", ["model_name"], unique=True)

    # --- notification_logs ---
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=True),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["push_subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_logs_notification_type"),
        "notification_logs",
        ["notification_type"],
    )
    op.create_index(op.f("ix_notification_logs_user_id"), "notification_logs", ["user_id"])
    op.create_index(
        "ix_notification_logs_type_date",
        "notification_logs",
        ["notification_type", "created_at"],
    )

    # --- user_bets ---
    op.create_table(
        "user_bets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("bet_type", sa.String(length=20), nullable=False),
        sa.Column("stake", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("odds", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("potential_return", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("actual_return", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.Column("followed_prediction", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_bets_user_id"), "user_bets", ["user_id"])
    op.create_index("ix_user_bets_user_status", "user_bets", ["user_id", "status"])
    op.create_index("ix_user_bets_user_date", "user_bets", ["user_id", "created_at"])

    # --- user_bankrolls ---
    op.create_table(
        "user_bankrolls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("bet_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["bet_id"], ["user_bets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_bankrolls_user_id"), "user_bankrolls", ["user_id"])
    op.create_index("ix_user_bankrolls_user_date", "user_bankrolls", ["user_id", "created_at"])

    # --- user_stats ---
    op.create_table(
        "user_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("total_bets", sa.Integer(), nullable=False),
        sa.Column("won_bets", sa.Integer(), nullable=False),
        sa.Column("lost_bets", sa.Integer(), nullable=False),
        sa.Column("pending_bets", sa.Integer(), nullable=False),
        sa.Column("void_bets", sa.Integer(), nullable=False),
        sa.Column("total_staked", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_returns", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("profit_loss", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("roi_percentage", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("win_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("avg_odds", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("best_streak", sa.Integer(), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=False),
        sa.Column("followed_predictions", sa.Integer(), nullable=False),
        sa.Column("followed_wins", sa.Integer(), nullable=False),
        sa.Column("followed_win_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("stats_by_bet_type", sa.Text(), nullable=True),
        sa.Column("stats_by_competition", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_stats_user_id"), "user_stats", ["user_id"], unique=True)

    # --- user_favorites ---
    op.create_table(
        "user_favorites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("favorite_type", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("notify_before_match", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_favorites_user", "user_favorites", ["user_id"])
    op.create_index(op.f("ix_user_favorites_user_id"), "user_favorites", ["user_id"])
    op.create_index("ix_user_favorites_type", "user_favorites", ["user_id", "favorite_type"])
    op.create_index(
        "uq_user_favorites_user_match",
        "user_favorites",
        ["user_id", "match_id"],
        unique=True,
    )

    # --- testimonials ---
    op.create_table(
        "testimonials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("author_name", sa.String(length=100), nullable=False),
        sa.Column("author_role", sa.String(length=100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- user_preferences ---
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("odds_format", sa.String(length=20), nullable=False),
        sa.Column("dark_mode", sa.Boolean(), nullable=False),
        sa.Column("email_daily_picks", sa.Boolean(), nullable=False),
        sa.Column("email_match_results", sa.Boolean(), nullable=False),
        sa.Column("push_daily_picks", sa.Boolean(), nullable=False),
        sa.Column("push_match_start", sa.Boolean(), nullable=False),
        sa.Column("push_bet_results", sa.Boolean(), nullable=False),
        sa.Column("default_stake", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("bankroll", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("favorite_competitions", sa.Text(), nullable=True),
        sa.Column("favorite_teams", sa.Text(), nullable=True),
        sa.Column("favorite_team_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["favorite_team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_user_preferences_user_id"), "user_preferences", ["user_id"], unique=True
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("user_preferences")
    op.drop_table("testimonials")
    op.drop_table("user_favorites")
    op.drop_table("user_stats")
    op.drop_table("user_bankrolls")
    op.drop_table("user_bets")
    op.drop_table("notification_logs")
    op.drop_table("ml_models")
    op.drop_table("sync_log")
    op.drop_table("standings")
    op.drop_table("cached_data")
    op.drop_table("push_subscriptions")
    op.drop_table("news_items")
    op.drop_table("prediction_results")
    op.drop_table("predictions")
    op.drop_table("matches")
    op.drop_table("competitions")
    op.drop_table("teams")
