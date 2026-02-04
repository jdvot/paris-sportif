-- Migration: 002_verify_and_create_all_tables.sql
-- Date: 2026-02-04
-- Description: Ensure all required tables and columns exist in production

-- ============================================================================
-- 1. TEAMS TABLE - Verify all columns
-- ============================================================================
ALTER TABLE teams ADD COLUMN IF NOT EXISTS logo_url TEXT;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS elo_rating NUMERIC(6,1) DEFAULT 1500.0;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS avg_goals_scored_home NUMERIC(4,2);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS avg_goals_scored_away NUMERIC(4,2);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS avg_goals_conceded_home NUMERIC(4,2);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS avg_goals_conceded_away NUMERIC(4,2);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS avg_xg_for NUMERIC(4,2);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS avg_xg_against NUMERIC(4,2);

-- ============================================================================
-- 2. MATCHES TABLE - Verify all columns
-- ============================================================================
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_score_ht INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_score_ht INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_xg NUMERIC(4,2);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_xg NUMERIC(4,2);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS odds_home NUMERIC(5,2);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS odds_draw NUMERIC(5,2);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS odds_away NUMERIC(5,2);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_code VARCHAR(10);

-- Fix match_date type if needed
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
        RAISE NOTICE 'Converted match_date from TEXT to TIMESTAMPTZ';
    ELSIF col_type = 'timestamp without time zone' THEN
        ALTER TABLE matches ALTER COLUMN match_date TYPE TIMESTAMP WITH TIME ZONE
            USING match_date AT TIME ZONE 'UTC';
        RAISE NOTICE 'Converted match_date to TIMESTAMPTZ';
    END IF;
END $$;

-- ============================================================================
-- 3. PREDICTIONS TABLE - Verify all columns
-- ============================================================================
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS home_prob NUMERIC(5,4);
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS draw_prob NUMERIC(5,4);
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS away_prob NUMERIC(5,4);
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS predicted_outcome VARCHAR(10);
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS confidence NUMERIC(5,4);
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS value_score NUMERIC(6,4);
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS is_daily_pick BOOLEAN DEFAULT FALSE;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS pick_rank INTEGER;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS pick_score NUMERIC(6,4);
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS explanation TEXT;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS key_factors TEXT;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS risk_factors TEXT;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS model_details TEXT;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS llm_adjustments TEXT;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

CREATE INDEX IF NOT EXISTS ix_predictions_daily_pick ON predictions(is_daily_pick, created_at);

-- ============================================================================
-- 4. PREDICTION_RESULTS TABLE - Create if not exists
-- ============================================================================
CREATE TABLE IF NOT EXISTS prediction_results (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER NOT NULL UNIQUE REFERENCES predictions(id),
    actual_outcome VARCHAR(10) NOT NULL,
    was_correct BOOLEAN NOT NULL,
    value_captured NUMERIC(6,2),
    assigned_probability NUMERIC(5,4) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 5. STANDINGS TABLE - Create if not exists
-- ============================================================================
CREATE TABLE IF NOT EXISTS standings (
    id SERIAL PRIMARY KEY,
    competition_code VARCHAR(10) NOT NULL,
    season VARCHAR(20),
    position INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    team_logo TEXT,
    played_games INTEGER DEFAULT 0,
    won INTEGER DEFAULT 0,
    drawn INTEGER DEFAULT 0,
    lost INTEGER DEFAULT 0,
    goals_for INTEGER DEFAULT 0,
    goals_against INTEGER DEFAULT 0,
    goal_difference INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    form VARCHAR(10),
    synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_standings_competition ON standings(competition_code);
CREATE INDEX IF NOT EXISTS ix_standings_position ON standings(competition_code, position);
CREATE UNIQUE INDEX IF NOT EXISTS uq_standings_comp_team ON standings(competition_code, team_id);

-- ============================================================================
-- 6. SYNC_LOG TABLE - Create if not exists
-- ============================================================================
CREATE TABLE IF NOT EXISTS sync_log (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_synced INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT,
    error_details TEXT,
    triggered_by VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS ix_sync_log_type_date ON sync_log(sync_type, started_at);

-- ============================================================================
-- 7. CACHED_DATA TABLE - Verify columns with timezone
-- ============================================================================
DO $$
BEGIN
    -- Check if expires_at needs timezone
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'cached_data'
        AND column_name = 'expires_at'
        AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE cached_data
            ALTER COLUMN expires_at TYPE TIMESTAMP WITH TIME ZONE USING expires_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- ============================================================================
-- 8. NEWS_ITEMS TABLE - Create if not exists
-- ============================================================================
CREATE TABLE IF NOT EXISTS news_items (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(100) UNIQUE,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    url TEXT NOT NULL,
    source VARCHAR(100) NOT NULL,
    team_ids TEXT,
    player_names TEXT,
    is_injury_news BOOLEAN DEFAULT FALSE,
    sentiment_score NUMERIC(4,3),
    impact_score NUMERIC(4,3),
    llm_analysis TEXT,
    published_at TIMESTAMP NOT NULL,
    analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_news_published ON news_items(published_at);
CREATE INDEX IF NOT EXISTS ix_news_injury ON news_items(is_injury_news, published_at);

-- ============================================================================
-- 9. ML_MODELS TABLE - Create if not exists
-- ============================================================================
CREATE TABLE IF NOT EXISTS ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) UNIQUE NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    accuracy NUMERIC(5,4),
    precision NUMERIC(5,4),
    recall NUMERIC(5,4),
    f1_score NUMERIC(5,4),
    training_samples INTEGER DEFAULT 0,
    feature_columns TEXT,
    hyperparameters TEXT,
    model_binary BYTEA,
    scaler_binary BYTEA,
    is_active BOOLEAN DEFAULT FALSE,
    trained_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 10. PUSH_SUBSCRIPTIONS TABLE - Create if not exists
-- ============================================================================
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id SERIAL PRIMARY KEY,
    endpoint TEXT UNIQUE NOT NULL,
    p256dh_key TEXT NOT NULL,
    auth_key TEXT NOT NULL,
    user_id VARCHAR(100),
    daily_picks BOOLEAN DEFAULT TRUE,
    match_start BOOLEAN DEFAULT FALSE,
    result_updates BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    failed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_push_subscriptions_user ON push_subscriptions(user_id);

-- ============================================================================
-- 11. NOTIFICATION_LOGS TABLE - Create if not exists
-- ============================================================================
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    user_id VARCHAR(100),
    subscription_id INTEGER REFERENCES push_subscriptions(id),
    title VARCHAR(200) NOT NULL,
    body TEXT,
    payload TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_notification_logs_type_date ON notification_logs(notification_type, created_at);

-- ============================================================================
-- 12. USER TABLES - Create if not exist
-- ============================================================================

-- user_bets
CREATE TABLE IF NOT EXISTS user_bets (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    prediction_id INTEGER REFERENCES predictions(id),
    bet_type VARCHAR(20) NOT NULL,
    stake NUMERIC(10,2) NOT NULL,
    odds NUMERIC(5,2) NOT NULL,
    potential_return NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    actual_return NUMERIC(10,2),
    settled_at TIMESTAMP,
    followed_prediction BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_bets_user_status ON user_bets(user_id, status);
CREATE INDEX IF NOT EXISTS ix_user_bets_user_date ON user_bets(user_id, created_at);

-- user_bankrolls
CREATE TABLE IF NOT EXISTS user_bankrolls (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    balance_after NUMERIC(12,2) NOT NULL,
    bet_id INTEGER REFERENCES user_bets(id),
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_bankrolls_user_date ON user_bankrolls(user_id, created_at);

-- user_stats
CREATE TABLE IF NOT EXISTS user_stats (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    total_bets INTEGER DEFAULT 0,
    won_bets INTEGER DEFAULT 0,
    lost_bets INTEGER DEFAULT 0,
    pending_bets INTEGER DEFAULT 0,
    void_bets INTEGER DEFAULT 0,
    total_staked NUMERIC(12,2) DEFAULT 0,
    total_returns NUMERIC(12,2) DEFAULT 0,
    profit_loss NUMERIC(12,2) DEFAULT 0,
    roi_percentage NUMERIC(6,2) DEFAULT 0,
    win_rate NUMERIC(5,2) DEFAULT 0,
    avg_odds NUMERIC(5,2) DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    followed_predictions INTEGER DEFAULT 0,
    followed_wins INTEGER DEFAULT 0,
    followed_win_rate NUMERIC(5,2) DEFAULT 0,
    stats_by_bet_type TEXT,
    stats_by_competition TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- user_favorites
CREATE TABLE IF NOT EXISTS user_favorites (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    prediction_id INTEGER REFERENCES predictions(id),
    favorite_type VARCHAR(20) DEFAULT 'pick',
    note VARCHAR(500),
    notify_before_match BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_favorites_user ON user_favorites(user_id);
CREATE INDEX IF NOT EXISTS ix_user_favorites_type ON user_favorites(user_id, favorite_type);
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_favorites_user_match ON user_favorites(user_id, match_id);

-- user_preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    language VARCHAR(5) DEFAULT 'fr',
    timezone VARCHAR(50) DEFAULT 'Europe/Paris',
    odds_format VARCHAR(20) DEFAULT 'decimal',
    dark_mode BOOLEAN DEFAULT TRUE,
    email_daily_picks BOOLEAN DEFAULT TRUE,
    email_match_results BOOLEAN DEFAULT FALSE,
    push_daily_picks BOOLEAN DEFAULT TRUE,
    push_match_start BOOLEAN DEFAULT FALSE,
    push_bet_results BOOLEAN DEFAULT TRUE,
    default_stake NUMERIC(10,2) DEFAULT 10.0,
    bankroll NUMERIC(12,2),
    risk_level VARCHAR(20) DEFAULT 'medium',
    favorite_competitions TEXT,
    favorite_teams TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- VERIFICATION QUERY - Run this to check all tables exist
-- ============================================================================
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns c WHERE c.table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
AND table_name IN (
    'teams', 'competitions', 'matches', 'predictions', 'prediction_results',
    'standings', 'sync_log', 'cached_data', 'news_items', 'ml_models',
    'push_subscriptions', 'notification_logs', 'user_bets', 'user_bankrolls',
    'user_stats', 'user_favorites', 'user_preferences'
)
ORDER BY table_name;
