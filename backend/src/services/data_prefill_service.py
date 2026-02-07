"""Data prefill service for automatic data enrichment.

This service runs during sync to ensure all database fields are populated.
It handles:
- Team data: country, form, rest_days, fixture_congestion, xG
- Match data: half-time scores, xG, odds (when available)
- Predictions: pre-generate for upcoming matches
- Cache: pre-warm Redis and DB cache
- News: fetch and store from RSS feeds
- Sync logs: track all operations
"""

import asyncio
import hashlib
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

from src.db import async_session_factory

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_async_session():
    """Context manager for async database sessions."""
    async with async_session_factory() as session:
        yield session


async def log_sync_operation(
    sync_type: str,
    status: str,
    records_synced: int = 0,
    error_message: str | None = None,
    triggered_by: str = "startup",
) -> int:
    """Log a sync operation to the sync_log table."""
    async with get_async_session() as session:
        result = await session.execute(
            text(
                """
                INSERT INTO sync_log (
                    sync_type, status, records_synced,
                    started_at, completed_at,
                    error_message, triggered_by
                )
                VALUES (
                    :sync_type, :status, :records_synced,
                    NOW(), NOW(),
                    :error_message, :triggered_by
                )
                RETURNING id
            """
            ),
            {
                "sync_type": sync_type,
                "status": status,
                "records_synced": records_synced,
                "error_message": error_message,
                "triggered_by": triggered_by,
            },
        )
        await session.commit()
        row = result.fetchone()
        return row[0] if row else 0


async def generate_match_news_summary(
    home_team: str,
    away_team: str,
    home_win_prob: float,
    draw_prob: float,
    away_win_prob: float,
) -> tuple[str, list[dict[str, str]]]:
    """Generate an LLM news summary from recent news_items in DB.

    Queries news_items matching team names (last 7 days, max 20 articles),
    then calls Groq LLM to produce a French-language context summary.

    Returns:
        Tuple of (summary_text, news_sources_list). Returns ("", []) on failure.
    """
    try:
        from src.llm.client import get_llm_client

        # 1. Fetch recent news for both teams
        cutoff = datetime.now() - timedelta(days=7)
        async with get_async_session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT title, source, url, published_at
                    FROM news_items
                    WHERE (title ILIKE :home_pattern OR title ILIKE :away_pattern)
                      AND published_at > :cutoff
                    ORDER BY published_at DESC
                    LIMIT 20
                    """
                ),
                {
                    "home_pattern": f"%{home_team}%",
                    "away_pattern": f"%{away_team}%",
                    "cutoff": cutoff,
                },
            )
            news_rows = result.fetchall()

        if not news_rows:
            return ("", [])

        # 2. Build headlines list and sources
        headlines: list[str] = []
        sources: list[dict[str, str]] = []
        seen_sources: set[str] = set()
        for row in news_rows:
            headlines.append(f"- {row.title[:100]}")
            src = row.source or "Unknown"
            if src not in seen_sources:
                seen_sources.add(src)
                sources.append(
                    {
                        "source": src,
                        "title": row.title[:80],
                        "url": row.url or "",
                    }
                )

        headlines_str = "\n".join(headlines[:20])

        # 3. Call LLM
        prompt = f"""\
Tu es un analyste football expert. Résume le contexte d'actualité \
pour le match {home_team} vs {away_team}.

PROBABILITÉS DU MODÈLE STATISTIQUE:
- Victoire {home_team}: {home_win_prob:.0%}
- Match nul: {draw_prob:.0%}
- Victoire {away_team}: {away_win_prob:.0%}

ACTUALITÉS RÉCENTES (derniers 7 jours):
{headlines_str}

CONSIGNES:
1. Résume en 8-10 lignes max les éléments d'actualité pertinents pour ce match
2. Donne ton avis d'expert sur l'impact de ces actualités sur le pronostic
3. Identifie les facteurs d'influence clés basés sur l'actu (blessures, forme, mercato, etc.)
4. IMPORTANT: Réponds UNIQUEMENT en français, même si les titres sont en anglais
5. Pas de titre, pas de bullet points, juste du texte fluide
6. Sois factuel et concis (max 200 mots)"""

        llm = get_llm_client()
        summary = await llm.complete(
            prompt=prompt,
            max_tokens=400,
            temperature=0.3,
        )
        summary = summary.strip() if summary else ""

        if not summary:
            return ("", [])

        logger.info(
            f"Generated news summary for {home_team} vs {away_team} ({len(news_rows)} news)"
        )
        return (summary, sources[:5])

    except Exception as e:
        logger.warning(f"Failed to generate news summary for {home_team} vs {away_team}: {e}")
        return ("", [])


async def _get_team_injury_news(team_name: str) -> list[dict[str, str]]:
    """Get recent injury news for a team from DB. No LLM call needed."""
    async with get_async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT title, source, published_at
                FROM news_items
                WHERE is_injury_news = TRUE
                  AND title ILIKE :pattern
                  AND published_at > NOW() - INTERVAL '14 days'
                ORDER BY published_at DESC
                LIMIT 5
                """
            ),
            {"pattern": f"%{team_name}%"},
        )
        rows = result.fetchall()
        return [
            {
                "title": r.title[:150],
                "source": r.source or "",
                "date": r.published_at.isoformat() if hasattr(r.published_at, "isoformat") else "",
            }
            for r in rows
        ]


def _calculate_match_importance(
    competition: str, home_elo: float, away_elo: float
) -> dict[str, Any]:
    """Calculate match importance from competition and team strength. No LLM call."""
    comp_importance: dict[str, float] = {
        "CL": 1.0,
        "EL": 0.8,
        "ECL": 0.6,
        "PL": 0.9,
        "PD": 0.85,
        "BL1": 0.8,
        "SA": 0.8,
        "FL1": 0.75,
    }
    importance = comp_importance.get(competition, 0.5)
    elo_diff = abs(home_elo - away_elo)
    closeness = max(0.0, 1.0 - elo_diff / 500.0)
    is_top_matchup = home_elo > 1700 and away_elo > 1700

    return {
        "competition_importance": importance,
        "closeness": round(closeness, 2),
        "is_top_matchup": is_top_matchup,
        "overall_importance": round(importance * 0.6 + closeness * 0.4, 2),
    }


def _serialize_model_details(
    pred: Any,
    home_stats: Any,
    away_stats: Any,
    multi_markets_data: Any,
    weather_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Serialize ensemble prediction + enrichments into model_details JSON."""
    from dataclasses import asdict

    details: dict[str, Any] = {
        "model_contributions": [
            {
                "name": mc.name,
                "home_prob": mc.home_prob,
                "draw_prob": mc.draw_prob,
                "away_prob": mc.away_prob,
                "weight": mc.weight,
                "confidence": mc.confidence,
            }
            for mc in (pred.model_contributions or [])
        ],
        "model_agreement": pred.model_agreement,
        "uncertainty": pred.uncertainty,
        "expected_home_goals": pred.expected_home_goals,
        "expected_away_goals": pred.expected_away_goals,
    }

    if multi_markets_data:
        details["multi_markets"] = asdict(multi_markets_data)

    details["fatigue"] = {
        "home": {
            "rest_days": float(home_stats.rest_days or 3),
            "congestion": float(home_stats.fixture_congestion or 0),
        },
        "away": {
            "rest_days": float(away_stats.rest_days or 3),
            "congestion": float(away_stats.fixture_congestion or 0),
        },
    }

    if weather_data and weather_data.get("available"):
        details["weather"] = weather_data

    return details


async def _generate_llm_analysis(
    home_team: str,
    away_team: str,
    competition: str,
    match_date_str: str,
    pred: Any,
    home_elo: float,
    away_elo: float,
    home_form: float,
    away_form: float,
    home_attack: float,
    away_attack: float,
) -> tuple[str | None, list[str] | None, list[str] | None]:
    """Generate LLM analysis via Groq. Returns None on failure (no fallback)."""
    try:
        from src.llm.client import get_llm_client
        from src.llm.prompts import MATCH_EXPLANATION_PROMPT, SYSTEM_FOOTBALL_ANALYST

        key_stats = (
            f"ELO: {home_team} {home_elo:.0f} vs {away_team} {away_elo:.0f}\n"
            f"Expected goals: {pred.expected_home_goals:.1f} - {pred.expected_away_goals:.1f}\n"
            f"Home attack: {home_attack:.2f} g/m | Away attack: {away_attack:.2f} g/m\n"
            f"Model agreement: {pred.model_agreement:.0%} | Uncertainty: {pred.uncertainty:.0%}"
        )

        bet_map = {
            "home": f"Victoire {home_team}",
            "draw": "Match nul",
            "away": f"Victoire {away_team}",
        }

        prompt = MATCH_EXPLANATION_PROMPT.format(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            match_date=match_date_str,
            home_prob=f"{pred.home_win_prob * 100:.1f}",
            draw_prob=f"{pred.draw_prob * 100:.1f}",
            away_prob=f"{pred.away_win_prob * 100:.1f}",
            recommended_bet=bet_map.get(pred.recommended_bet, pred.recommended_bet),
            confidence=f"{pred.confidence * 100:.0f}",
            key_stats=key_stats,
            home_form=f"{home_form:.0%}",
            away_form=f"{away_form:.0%}",
        )

        llm = get_llm_client()
        analysis = await llm.analyze_json(
            prompt=prompt,
            system_prompt=SYSTEM_FOOTBALL_ANALYST,
            temperature=0.4,
        )

        if analysis and isinstance(analysis, dict):
            explanation = str(analysis.get("summary", ""))
            key_factors = analysis.get("key_factors", [])
            risk_factors = analysis.get("risk_factors", [])

            betting_angle = analysis.get("betting_angle", "")
            if betting_angle and explanation:
                explanation = f"{explanation} {betting_angle}"

            if isinstance(key_factors, list) and isinstance(risk_factors, list):
                return explanation, key_factors, risk_factors

    except Exception as e:
        logger.warning(f"LLM analysis failed for {home_team} vs {away_team}: {e}")

    # No fallback — return None (only real LLM data or nothing)
    return None, None, None


class DataPrefillService:
    """Service for automatic data prefilling and enrichment."""

    @staticmethod
    async def fill_all_team_data() -> dict[str, int]:
        """Fill all team data fields. Returns counts of updated fields."""
        results = {
            "country": 0,
            "form": 0,
            "rest_days": 0,
            "avg_goals": 0,
            "elo": 0,
        }

        async with get_async_session() as session:
            # 1. Fill country from competition
            country_result = await session.execute(
                text(
                    """
                WITH team_leagues AS (
                    SELECT team_id, competition_code, SUM(cnt) as total_matches
                    FROM (
                        SELECT home_team_id as team_id, competition_code, COUNT(*) as cnt
                        FROM matches WHERE competition_code IN ('PL', 'PD', 'BL1', 'SA', 'FL1')
                        GROUP BY home_team_id, competition_code
                        UNION ALL
                        SELECT away_team_id as team_id, competition_code, COUNT(*) as cnt
                        FROM matches WHERE competition_code IN ('PL', 'PD', 'BL1', 'SA', 'FL1')
                        GROUP BY away_team_id, competition_code
                    ) m
                    GROUP BY team_id, competition_code
                ),
                primary_league AS (
                    SELECT DISTINCT ON (team_id) team_id, competition_code
                    FROM team_leagues
                    ORDER BY team_id, total_matches DESC
                )
                UPDATE teams t
                SET country = CASE pl.competition_code
                    WHEN 'PL' THEN 'England'
                    WHEN 'PD' THEN 'Spain'
                    WHEN 'BL1' THEN 'Germany'
                    WHEN 'SA' THEN 'Italy'
                    WHEN 'FL1' THEN 'France'
                END,
                updated_at = NOW()
                FROM primary_league pl
                WHERE t.id = pl.team_id AND (t.country IS NULL OR t.country = '')
            """
                )
            )
            results["country"] = country_result.rowcount
            await session.commit()

            # 2. Fill form from last 5 matches
            form_result = await session.execute(
                text(
                    """
                WITH recent_matches AS (
                    SELECT
                        team_id,
                        match_date,
                        CASE
                            WHEN goals_for > goals_against THEN 'W'
                            WHEN goals_for = goals_against THEN 'D'
                            ELSE 'L'
                        END as result,
                        ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY match_date DESC) as rn
                    FROM (
                        SELECT home_team_id as team_id, match_date,
                            home_score as goals_for, away_score as goals_against
                        FROM matches
                        WHERE status = 'FINISHED' AND home_score IS NOT NULL
                        UNION ALL
                        SELECT away_team_id as team_id, match_date,
                            away_score as goals_for, home_score as goals_against
                        FROM matches
                        WHERE status = 'FINISHED' AND away_score IS NOT NULL
                    ) all_matches
                ),
                team_form AS (
                    SELECT team_id, STRING_AGG(result, '' ORDER BY match_date DESC) as form
                    FROM recent_matches
                    WHERE rn <= 5
                    GROUP BY team_id
                )
                UPDATE teams t
                SET
                    form = tf.form,
                    form_score = (
                        (LENGTH(tf.form) - LENGTH(REPLACE(tf.form, 'W', ''))) * 3 +
                        (LENGTH(tf.form) - LENGTH(REPLACE(tf.form, 'D', ''))) * 1
                    ) / 15.0,
                    updated_at = NOW()
                FROM team_form tf
                WHERE t.id = tf.team_id
            """
                )
            )
            results["form"] = form_result.rowcount
            await session.commit()

            # 3. Fill rest_days and fixture_congestion
            rest_result = await session.execute(
                text(
                    """
                WITH last_match AS (
                    SELECT team_id, MAX(match_date) as last_date
                    FROM (
                        SELECT home_team_id as team_id, match_date
                        FROM matches WHERE status = 'FINISHED'
                        UNION ALL
                        SELECT away_team_id as team_id, match_date
                        FROM matches WHERE status = 'FINISHED'
                    ) all_matches
                    GROUP BY team_id
                ),
                congestion AS (
                    SELECT team_id, COUNT(*) as matches_14d
                    FROM (
                        SELECT home_team_id as team_id FROM matches
                        WHERE status = 'FINISHED' AND match_date >= NOW() - INTERVAL '14 days'
                        UNION ALL
                        SELECT away_team_id as team_id FROM matches
                        WHERE status = 'FINISHED' AND match_date >= NOW() - INTERVAL '14 days'
                    ) recent
                    GROUP BY team_id
                )
                UPDATE teams t
                SET
                    last_match_date = lm.last_date,
                    rest_days = COALESCE(EXTRACT(DAY FROM NOW() - lm.last_date)::INTEGER, 7),
                    fixture_congestion = LEAST(1.0, COALESCE(c.matches_14d, 0) / 4.0),
                    updated_at = NOW()
                FROM last_match lm
                LEFT JOIN congestion c ON lm.team_id = c.team_id
                WHERE t.id = lm.team_id
            """
                )
            )
            results["rest_days"] = rest_result.rowcount
            await session.commit()

            # 4. Fill avg_goals from match history
            goals_result = await session.execute(
                text(
                    """
                WITH home_stats AS (
                    SELECT
                        home_team_id as team_id,
                        AVG(home_score) as avg_scored,
                        AVG(away_score) as avg_conceded
                    FROM matches
                    WHERE status = 'FINISHED' AND home_score IS NOT NULL
                    GROUP BY home_team_id
                ),
                away_stats AS (
                    SELECT
                        away_team_id as team_id,
                        AVG(away_score) as avg_scored,
                        AVG(home_score) as avg_conceded
                    FROM matches
                    WHERE status = 'FINISHED' AND away_score IS NOT NULL
                    GROUP BY away_team_id
                )
                UPDATE teams t
                SET
                    avg_goals_scored_home = COALESCE(h.avg_scored, 1.0),
                    avg_goals_conceded_home = COALESCE(h.avg_conceded, 1.0),
                    avg_goals_scored_away = COALESCE(a.avg_scored, 1.0),
                    avg_goals_conceded_away = COALESCE(a.avg_conceded, 1.0),
                    updated_at = NOW()
                FROM home_stats h
                FULL OUTER JOIN away_stats a ON h.team_id = a.team_id
                WHERE t.id = COALESCE(h.team_id, a.team_id)
            """
                )
            )
            results["avg_goals"] = goals_result.rowcount
            await session.commit()

        logger.info(f"Team data prefill complete: {results}")
        return results

    @staticmethod
    async def calculate_elo_ratings() -> int:
        """Calculate proper ELO ratings from match history."""
        from src.prediction_engine.models.elo import ELOSystem

        elo_system = ELOSystem(k_factor=20.0, home_advantage=100.0)
        team_ratings: dict[int, float] = {}

        async with get_async_session() as session:
            # Get all finished matches ordered by date
            result = await session.execute(
                text(
                    """
                SELECT id, home_team_id, away_team_id, home_score, away_score, match_date
                FROM matches
                WHERE status = 'FINISHED'
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                ORDER BY match_date ASC
            """
                )
            )
            matches = result.fetchall()

            logger.info(f"Processing {len(matches)} matches for ELO calculation")

            for match in matches:
                home_id = match.home_team_id
                away_id = match.away_team_id

                # Initialize at 1500 if new
                if home_id not in team_ratings:
                    team_ratings[home_id] = 1500.0
                if away_id not in team_ratings:
                    team_ratings[away_id] = 1500.0

                # Calculate new ratings
                new_home, new_away = elo_system.update_ratings(
                    home_rating=team_ratings[home_id],
                    away_rating=team_ratings[away_id],
                    home_goals=match.home_score,
                    away_goals=match.away_score,
                )

                team_ratings[home_id] = new_home
                team_ratings[away_id] = new_away

            # Update database
            updated = 0
            for team_id, elo in team_ratings.items():
                clamped_elo = max(1000.0, min(2500.0, elo))
                await session.execute(
                    text("UPDATE teams SET elo_rating = :elo, updated_at = NOW() WHERE id = :id"),
                    {"elo": clamped_elo, "id": team_id},
                )
                updated += 1

            await session.commit()
            logger.info(f"Updated ELO for {updated} teams")
            return updated

    @staticmethod
    async def prefill_predictions_for_upcoming() -> int:
        """Pre-generate predictions with full AI enrichment for upcoming matches.

        Pipeline per match:
        1. Run 6-model ensemble predictor
        2. Calculate multi-markets (O/U 1.5/2.5/3.5, BTTS, DC, correct score)
        3. Fetch match-day weather from Open-Meteo
        4. Generate LLM analysis via Groq (None if LLM unavailable)
        5. Generate news context summary via LLM
        6. Persist everything (model_details JSON, explanation, factors)
        7. After all matches: mark top 5 daily picks
        """
        from src.data.data_enrichment import WeatherClient
        from src.db.services.prediction_service import PredictionService
        from src.prediction_engine.ensemble_advanced import advanced_ensemble_predictor
        from src.prediction_engine.multi_markets import get_multi_markets_prediction

        weather_client = WeatherClient()

        async with get_async_session() as session:
            result = await session.execute(
                text(
                    """
                SELECT m.id, m.external_id, m.home_team_id, m.away_team_id,
                       m.competition_code, m.match_date,
                       ht.name as home_team, at.name as away_team
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                LEFT JOIN predictions p ON m.id = p.match_id
                WHERE m.status IN ('SCHEDULED', 'TIMED')
                    AND m.match_date > NOW()
                    AND m.match_date < NOW() + INTERVAL '30 days'
                    AND (
                        p.id IS NULL
                        OR p.value_score IS NULL
                        OR p.key_factors IS NULL
                        OR p.model_details IS NULL
                        OR p.explanation LIKE 'Prédiction pré-calculée%%'
                    )
                ORDER BY m.match_date
            """
                )
            )
            upcoming = result.fetchall()

            logger.info(f"Found {len(upcoming)} upcoming matches needing predictions")

            generated = 0
            prediction_scores: list[dict[str, Any]] = []

            for match in upcoming:
                try:
                    # 1. Get team stats from DB
                    team_result = await session.execute(
                        text(
                            """
                        SELECT t.id, t.elo_rating, t.avg_goals_scored_home,
                               t.avg_goals_scored_away,
                               t.avg_goals_conceded_home, t.avg_goals_conceded_away,
                               t.form_score, t.rest_days, t.fixture_congestion
                        FROM teams t WHERE t.id IN (:home_id, :away_id)
                    """
                        ),
                        {"home_id": match.home_team_id, "away_id": match.away_team_id},
                    )
                    teams = {t.id: t for t in team_result.fetchall()}

                    home = teams.get(match.home_team_id)
                    away = teams.get(match.away_team_id)

                    if not home or not away:
                        continue

                    # 2. Run 6-model ensemble prediction
                    pred = advanced_ensemble_predictor.predict(
                        home_attack=float(home.avg_goals_scored_home or 1.3),
                        home_defense=float(home.avg_goals_conceded_home or 1.3),
                        away_attack=float(away.avg_goals_scored_away or 1.3),
                        away_defense=float(away.avg_goals_conceded_away or 1.3),
                        home_elo=float(home.elo_rating or 1500),
                        away_elo=float(away.elo_rating or 1500),
                        home_team_id=match.home_team_id,
                        away_team_id=match.away_team_id,
                        home_form_score=float(home.form_score or 0.5) * 100,
                        away_form_score=float(away.form_score or 0.5) * 100,
                        home_rest_days=float(home.rest_days or 0.5),
                        away_rest_days=float(away.rest_days or 0.5),
                        home_congestion=float(home.fixture_congestion or 0.5),
                        away_congestion=float(away.fixture_congestion or 0.5),
                    )

                    # 3. Calculate multi-markets (O/U, BTTS, DC, correct score)
                    multi_markets = get_multi_markets_prediction(
                        expected_home_goals=pred.expected_home_goals or 1.3,
                        expected_away_goals=pred.expected_away_goals or 1.0,
                        home_win_prob=pred.home_win_prob,
                        draw_prob=pred.draw_prob,
                        away_win_prob=pred.away_win_prob,
                    )

                    # 4. Fetch weather from Open-Meteo (free, no key needed)
                    weather_data: dict[str, Any] | None = None
                    try:
                        weather_data = await weather_client.get_match_weather(
                            match.home_team, match.match_date
                        )
                    except Exception as we:
                        logger.debug(f"Weather fetch failed for {match.home_team}: {we}")

                    # 5. Serialize model_details (contributions + multi-markets + weather + fatigue)
                    model_details = _serialize_model_details(
                        pred, home, away, multi_markets, weather_data
                    )

                    # 5b. Add injury news and match importance (no LLM, DB/algorithmic)
                    home_elo = float(home.elo_rating or 1500)
                    away_elo = float(away.elo_rating or 1500)
                    try:
                        home_injuries = await _get_team_injury_news(match.home_team)
                        away_injuries = await _get_team_injury_news(match.away_team)
                        if home_injuries or away_injuries:
                            model_details["injuries"] = {
                                "home": home_injuries,
                                "away": away_injuries,
                            }
                    except Exception as ie:
                        logger.debug(f"Injury news fetch failed: {ie}")

                    model_details["importance"] = _calculate_match_importance(
                        match.competition_code or "", home_elo, away_elo
                    )

                    # 6. LLM analysis via Groq (None if unavailable, no fallback)
                    home_form = float(home.form_score or 0.5)
                    away_form = float(away.form_score or 0.5)
                    home_attack = float(home.avg_goals_scored_home or 1.3)
                    away_attack = float(away.avg_goals_scored_away or 1.0)

                    match_date_str = (
                        match.match_date.strftime("%Y-%m-%d %H:%M")
                        if hasattr(match.match_date, "strftime")
                        else str(match.match_date)
                    )

                    explanation, key_factors, risk_factors = await _generate_llm_analysis(
                        home_team=match.home_team,
                        away_team=match.away_team,
                        competition=match.competition_code or "",
                        match_date_str=match_date_str,
                        pred=pred,
                        home_elo=home_elo,
                        away_elo=away_elo,
                        home_form=home_form,
                        away_form=away_form,
                        home_attack=home_attack,
                        away_attack=away_attack,
                    )
                    # Rate limit: Groq 30 req/min
                    await asyncio.sleep(2)

                    # 7. Calculate value_score
                    confidence_val = float(pred.confidence)
                    max_prob = max(pred.home_win_prob, pred.draw_prob, pred.away_win_prob)
                    base_value = max_prob * 0.5 + confidence_val * 0.5
                    value_score = round(base_value + (confidence_val * 0.03), 4)

                    # 8. News context summary via LLM
                    match_context_summary = ""
                    news_sources: list[dict[str, str]] = []
                    try:
                        match_context_summary, news_sources = await generate_match_news_summary(
                            home_team=match.home_team,
                            away_team=match.away_team,
                            home_win_prob=pred.home_win_prob,
                            draw_prob=pred.draw_prob,
                            away_win_prob=pred.away_win_prob,
                        )
                        await asyncio.sleep(2)
                    except Exception as ne:
                        logger.warning(f"News summary failed for match {match.id}: {ne}")

                    # 9. Save prediction with full enrichment
                    await PredictionService.save_prediction_from_api(
                        {
                            "match_id": match.id,
                            "match_external_id": match.external_id,
                            "home_team": match.home_team,
                            "away_team": match.away_team,
                            "competition_code": match.competition_code,
                            "match_date": match.match_date.isoformat(),
                            "home_win_prob": pred.home_win_prob,
                            "draw_prob": pred.draw_prob,
                            "away_win_prob": pred.away_win_prob,
                            "confidence": pred.confidence,
                            "value_score": value_score,
                            "recommendation": pred.recommended_bet,
                            "explanation": explanation,
                            "key_factors": key_factors,
                            "risk_factors": risk_factors,
                            "model_details": model_details,
                            "match_context_summary": match_context_summary or None,
                            "news_sources": news_sources or None,
                        }
                    )

                    prediction_scores.append(
                        {
                            "match_id": match.id,
                            "value_score": value_score,
                            "confidence": confidence_val,
                        }
                    )
                    generated += 1

                except Exception as e:
                    logger.warning(f"Failed to generate prediction for match {match.id}: {e}")

        # 10. Mark daily picks (top 5 by combined score)
        if prediction_scores:
            await DataPrefillService._mark_daily_picks(prediction_scores)

        logger.info(f"Pre-generated {generated} predictions with full AI enrichment")
        return generated

    @staticmethod
    async def _mark_daily_picks(prediction_scores: list[dict[str, Any]]) -> int:
        """Mark top 5 predictions as daily picks by value_score x confidence."""
        from datetime import date as date_type

        async with get_async_session() as session:
            today = date_type.today()
            # Reset existing daily picks for upcoming matches
            await session.execute(
                text(
                    """
                    UPDATE predictions SET
                        is_daily_pick = FALSE, pick_rank = NULL, pick_score = NULL
                    WHERE is_daily_pick = TRUE
                      AND match_id IN (
                          SELECT m.id FROM matches m
                          WHERE m.match_date::date >= :today
                      )
                """
                ),
                {"today": today},
            )

            # Sort by combined score
            scored = sorted(
                prediction_scores,
                key=lambda p: p["value_score"] * p["confidence"],
                reverse=True,
            )

            marked = 0
            for rank, pick in enumerate(scored[:5], start=1):
                combined = round(pick["value_score"] * pick["confidence"], 4)
                await session.execute(
                    text(
                        """
                        UPDATE predictions SET
                            is_daily_pick = TRUE, pick_rank = :rank, pick_score = :score,
                            updated_at = NOW()
                        WHERE match_id = :mid
                    """
                    ),
                    {"rank": rank, "mid": pick["match_id"], "score": combined},
                )
                marked += 1

            await session.commit()
            logger.info(f"Marked {marked} daily picks")
            return marked

    @staticmethod
    async def generate_daily_summary() -> str:
        """Generate an editorial daily picks summary via LLM. Returns '' if LLM unavailable."""
        try:
            from src.llm.client import get_llm_client
            from src.llm.prompts import DAILY_PICKS_SUMMARY_PROMPT, SYSTEM_FOOTBALL_ANALYST

            async with get_async_session() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT p.confidence, p.predicted_outcome, p.explanation,
                               p.pick_rank, p.pick_score, p.value_score,
                               m.competition_code, m.match_date,
                               ht.name as home_team, at.name as away_team
                        FROM predictions p
                        JOIN matches m ON p.match_id = m.id
                        JOIN teams ht ON m.home_team_id = ht.id
                        JOIN teams at ON m.away_team_id = at.id
                        WHERE p.is_daily_pick = TRUE
                          AND m.match_date::date >= CURRENT_DATE
                        ORDER BY p.pick_rank
                        LIMIT 5
                    """
                    )
                )
                picks = result.fetchall()

            if not picks:
                return ""

            picks_text_parts: list[str] = []
            for p in picks:
                bet_map = {
                    "home": f"Victoire {p.home_team}",
                    "draw": "Nul",
                    "away": f"Victoire {p.away_team}",
                }
                bet = bet_map.get(p.predicted_outcome, p.predicted_outcome)
                picks_text_parts.append(
                    f"#{p.pick_rank}: {p.home_team} vs {p.away_team} "
                    f"({p.competition_code})\n"
                    f"  Pronostic: {bet} | Confiance: {float(p.confidence):.0%} | "
                    f"Value: {float(p.value_score or 0):.2f}\n"
                    f"  {p.explanation[:150] if p.explanation else 'Analyse non disponible'}"
                )

            picks_data = "\n\n".join(picks_text_parts)
            prompt = DAILY_PICKS_SUMMARY_PROMPT.format(picks_data=picks_data)

            llm = get_llm_client()
            analysis = await llm.analyze_json(
                prompt=prompt,
                system_prompt=SYSTEM_FOOTBALL_ANALYST,
                temperature=0.5,
            )

            if analysis and isinstance(analysis, dict):
                summary = str(analysis.get("daily_summary", ""))
                logger.info(f"Generated daily summary: {len(summary)} chars")

                # Cache in Redis
                try:
                    from src.core.cache import cache_set

                    await cache_set(
                        "daily_picks_summary",
                        json.dumps(analysis, ensure_ascii=False),
                        ttl=86400,
                    )
                except Exception as ce:
                    logger.warning(f"Failed to cache daily summary: {ce}")

                return summary

        except Exception as e:
            logger.warning(f"Daily summary generation failed: {e}")

        return ""

    @staticmethod
    async def run_post_match_analysis() -> int:
        """Compare predictions with actual results for recently finished matches.

        Updates model_details with post-match data (was_correct, margin, etc.).
        No LLM call — purely algorithmic retrospective.
        """
        count = 0
        async with get_async_session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT p.id as pred_id, p.match_id, p.predicted_outcome,
                           p.home_prob, p.draw_prob, p.away_prob,
                           p.confidence, p.model_details,
                           m.home_score, m.away_score,
                           ht.name as home_team, at.name as away_team,
                           m.competition_code
                    FROM predictions p
                    JOIN matches m ON p.match_id = m.id
                    JOIN teams ht ON m.home_team_id = ht.id
                    JOIN teams at ON m.away_team_id = at.id
                    WHERE m.status IN ('FINISHED', 'finished')
                      AND m.home_score IS NOT NULL
                      AND m.match_date > NOW() - INTERVAL '7 days'
                      AND (
                          p.model_details IS NULL
                          OR p.model_details NOT LIKE '%%post_match%%'
                      )
                    ORDER BY m.match_date DESC
                    LIMIT 50
                    """
                )
            )
            rows = result.fetchall()

            if not rows:
                return 0

            for row in rows:
                try:
                    actual = (
                        "home"
                        if row.home_score > row.away_score
                        else "away" if row.home_score < row.away_score else "draw"
                    )
                    was_correct = actual == row.predicted_outcome

                    # Probability assigned to actual outcome
                    prob_map = {
                        "home": float(row.home_prob),
                        "draw": float(row.draw_prob),
                        "away": float(row.away_prob),
                    }
                    assigned_prob = prob_map.get(actual, 0.33)

                    # Brier score for this prediction (lower is better)
                    brier = (1 - assigned_prob) ** 2

                    post_match = {
                        "actual_outcome": actual,
                        "actual_score": f"{row.home_score}-{row.away_score}",
                        "was_correct": was_correct,
                        "assigned_probability": round(assigned_prob, 4),
                        "brier_score": round(brier, 4),
                        "confidence_was": float(row.confidence),
                    }

                    # Merge into existing model_details
                    existing_details: dict[str, Any] = {}
                    if row.model_details:
                        try:
                            existing_details = json.loads(row.model_details)
                        except (json.JSONDecodeError, TypeError):
                            pass

                    existing_details["post_match"] = post_match

                    await session.execute(
                        text(
                            """
                            UPDATE predictions SET
                                model_details = :details,
                                updated_at = NOW()
                            WHERE id = :pid
                            """
                        ),
                        {
                            "details": json.dumps(existing_details, default=str),
                            "pid": row.pred_id,
                        },
                    )
                    count += 1

                except Exception as e:
                    logger.warning(f"Post-match analysis failed for pred {row.pred_id}: {e}")

            await session.commit()

        logger.info(f"Post-match analysis completed for {count} predictions")
        return count

    @staticmethod
    async def fill_match_odds() -> int:
        """Fetch bookmaker odds for upcoming football matches."""
        from src.data.odds_client import get_match_odds

        count = 0
        async with get_async_session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT m.id, ht.name as home_team, at.name as away_team,
                           m.competition_code
                    FROM matches m
                    JOIN teams ht ON m.home_team_id = ht.id
                    JOIN teams at ON m.away_team_id = at.id
                    WHERE m.status IN ('SCHEDULED', 'TIMED')
                      AND m.match_date > NOW()
                      AND m.match_date < NOW() + INTERVAL '30 days'
                      AND m.odds_home IS NULL
                """
                )
            )
            rows = result.fetchall()
            logger.info(f"Found {len(rows)} matches needing odds")

            for row in rows:
                try:
                    odds = await get_match_odds(row.home_team, row.away_team, row.competition_code)
                    if not odds:
                        continue

                    await session.execute(
                        text(
                            """
                            UPDATE matches SET
                                odds_home = :oh, odds_draw = :od, odds_away = :oa,
                                updated_at = NOW()
                            WHERE id = :mid
                        """
                        ),
                        {
                            "oh": odds["home"],
                            "od": odds["draw"],
                            "oa": odds["away"],
                            "mid": row.id,
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch odds for match {row.id}: {e}")

            await session.commit()

        logger.info(f"Updated odds for {count} football matches")
        return count

    @staticmethod
    async def warm_redis_cache() -> int:
        """Pre-warm Redis cache with predictions and stats."""
        import json

        from src.core.cache import cache_set

        cached = 0
        async with get_async_session() as session:
            # Cache all predictions for upcoming matches
            result = await session.execute(
                text(
                    """
                SELECT p.match_id, p.home_prob, p.draw_prob, p.away_prob,
                       p.predicted_outcome, p.confidence, p.value_score,
                       p.explanation, p.created_at,
                       m.match_date, m.competition_code,
                       ht.name as home_team, at.name as away_team
                FROM predictions p
                JOIN matches m ON p.match_id = m.id
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                WHERE m.match_date > NOW() AND m.match_date < NOW() + INTERVAL '30 days'
            """
                )
            )
            predictions = result.fetchall()

            for pred in predictions:
                # Handle datetime fields that might already be strings
                match_date_str = (
                    pred.match_date.isoformat()
                    if hasattr(pred.match_date, "isoformat")
                    else str(pred.match_date)
                )
                created_at_str = (
                    pred.created_at.isoformat()
                    if hasattr(pred.created_at, "isoformat")
                    else str(pred.created_at)
                )

                cache_data = {
                    "match_id": pred.match_id,
                    "home_team": pred.home_team,
                    "away_team": pred.away_team,
                    "competition": pred.competition_code,
                    "match_date": match_date_str,
                    "probabilities": {
                        "home_win": float(pred.home_prob),
                        "draw": float(pred.draw_prob),
                        "away_win": float(pred.away_prob),
                    },
                    "recommended_bet": pred.predicted_outcome,
                    "confidence": float(pred.confidence),
                    "value_score": float(pred.value_score) if pred.value_score else 0.1,
                    "explanation": pred.explanation,
                    "created_at": created_at_str,
                }

                try:
                    await cache_set(
                        f"prediction:{pred.match_id}",
                        json.dumps(cache_data, default=str),
                        ttl=3600,  # 1 hour
                    )
                    cached += 1
                except Exception as e:
                    logger.warning(f"Failed to cache prediction {pred.match_id}: {e}")

            logger.info(f"Cached {cached} predictions in Redis")
            return cached

    @staticmethod
    async def fill_news_items() -> int:
        """Fetch news from RSS feeds and store in database."""
        from src.vector.news_ingestion import get_ingestion_service

        saved = 0
        try:
            service = get_ingestion_service()

            # Fetch general football news
            general_news = await service.fetch_general_football_news(max_per_source=10)
            logger.info(f"Fetched {len(general_news)} general news articles")

            async with get_async_session() as session:
                for article in general_news:
                    try:
                        # Create unique external_id from URL or title hash
                        external_id = hashlib.md5(
                            (article.url or article.title).encode()
                        ).hexdigest()[:20]

                        # Check if already exists
                        existing = await session.execute(
                            text("SELECT id FROM news_items WHERE external_id = :ext_id"),
                            {"ext_id": external_id},
                        )
                        if existing.fetchone():
                            continue

                        # Determine team_ids from team_name
                        team_ids = None
                        if article.team_id:
                            team_ids = json.dumps([article.team_id])

                        # Convert timezone-aware datetime to naive UTC
                        pub_at = article.published_at
                        if pub_at and pub_at.tzinfo is not None:
                            pub_at = pub_at.astimezone(UTC).replace(tzinfo=None)

                        # Insert news item
                        await session.execute(
                            text(
                                """
                                INSERT INTO news_items (
                                    external_id, title, content, url, source,
                                    team_ids, is_injury_news, published_at, created_at
                                ) VALUES (
                                    :external_id, :title, :content, :url, :source,
                                    :team_ids, :is_injury_news, :published_at, NOW()
                                )
                            """
                            ),
                            {
                                "external_id": external_id,
                                "title": article.title[:500],
                                "content": article.content[:2000] if article.content else None,
                                "url": article.url
                                or f"https://news.google.com/search?q={article.title[:50]}",
                                "source": article.source,
                                "team_ids": team_ids,
                                "is_injury_news": article.article_type == "injury",
                                "published_at": pub_at,
                            },
                        )
                        saved += 1

                    except Exception as e:
                        logger.warning(f"Failed to save news article: {e}")
                        continue

                await session.commit()

            logger.info(f"Saved {saved} news articles to database")
            return saved

        except Exception as e:
            logger.error(f"Error filling news items: {e}")
            return saved

    @staticmethod
    async def run_full_prefill(triggered_by: str = "startup") -> dict[str, Any]:
        """Run complete data prefill pipeline."""
        logger.info("Starting full data prefill...")
        start = datetime.now()
        errors: list[str] = []

        results: dict[str, Any] = {
            "team_data": {},
            "elo_ratings": 0,
            "predictions": 0,
            "match_odds": 0,
            "redis_cache": 0,
            "news_items": 0,
        }

        # 1. Fill team data
        try:
            results["team_data"] = await DataPrefillService.fill_all_team_data()
            total_team_updates = sum(results["team_data"].values())
            await log_sync_operation(
                "team_data", "success", total_team_updates, triggered_by=triggered_by
            )
        except Exception as e:
            logger.error(f"Team data prefill failed: {e}")
            errors.append(f"team_data: {str(e)}")
            await log_sync_operation("team_data", "failed", 0, str(e), triggered_by)

        # 2. Calculate ELO ratings
        try:
            results["elo_ratings"] = await DataPrefillService.calculate_elo_ratings()
            await log_sync_operation(
                "elo_ratings", "success", results["elo_ratings"], triggered_by=triggered_by
            )
        except Exception as e:
            logger.error(f"ELO calculation failed: {e}")
            errors.append(f"elo_ratings: {str(e)}")
            await log_sync_operation("elo_ratings", "failed", 0, str(e), triggered_by)

        # 3. Pre-generate predictions
        try:
            results["predictions"] = await DataPrefillService.prefill_predictions_for_upcoming()
            await log_sync_operation(
                "predictions", "success", results["predictions"], triggered_by=triggered_by
            )
        except Exception as e:
            logger.error(f"Predictions prefill failed: {e}")
            errors.append(f"predictions: {str(e)}")
            await log_sync_operation("predictions", "failed", 0, str(e), triggered_by)

        # 4. Fetch bookmaker odds for upcoming matches
        try:
            results["match_odds"] = await DataPrefillService.fill_match_odds()
            await log_sync_operation(
                "match_odds", "success", results["match_odds"], triggered_by=triggered_by
            )
        except Exception as e:
            logger.error(f"Match odds fetch failed: {e}")
            errors.append(f"match_odds: {str(e)}")
            await log_sync_operation("match_odds", "failed", 0, str(e), triggered_by)

        # 5. Warm Redis cache
        try:
            results["redis_cache"] = await DataPrefillService.warm_redis_cache()
            await log_sync_operation(
                "redis_cache", "success", results["redis_cache"], triggered_by=triggered_by
            )
        except Exception as e:
            logger.error(f"Redis cache warm failed: {e}")
            errors.append(f"redis_cache: {str(e)}")
            await log_sync_operation("redis_cache", "failed", 0, str(e), triggered_by)

        # 6. Fill news items from RSS
        try:
            results["news_items"] = await DataPrefillService.fill_news_items()
            await log_sync_operation(
                "news_items", "success", results["news_items"], triggered_by=triggered_by
            )
        except Exception as e:
            logger.error(f"News items fetch failed: {e}")
            errors.append(f"news_items: {str(e)}")
            await log_sync_operation("news_items", "failed", 0, str(e), triggered_by)

        # 7. Post-match retrospective analysis
        try:
            results["post_match_analysis"] = await DataPrefillService.run_post_match_analysis()
            await log_sync_operation(
                "post_match", "success", results["post_match_analysis"], triggered_by=triggered_by
            )
        except Exception as e:
            logger.error(f"Post-match analysis failed: {e}")
            errors.append(f"post_match: {str(e)}")

        # 8. Generate daily picks editorial summary via LLM
        try:
            summary = await DataPrefillService.generate_daily_summary()
            if summary:
                results["daily_summary"] = summary[:200]
        except Exception as e:
            logger.error(f"Daily summary generation failed: {e}")
            errors.append(f"daily_summary: {str(e)}")

        duration = (datetime.now() - start).total_seconds()
        results["duration_seconds"] = duration
        results["errors"] = errors

        # Log overall prefill operation
        overall_status = "success" if not errors else "partial"
        total_records = (
            sum(results["team_data"].values())
            + results["elo_ratings"]
            + results["predictions"]
            + results["match_odds"]
            + results["redis_cache"]
            + results["news_items"]
            + results.get("post_match_analysis", 0)
        )
        await log_sync_operation(
            "full_prefill",
            overall_status,
            total_records,
            "; ".join(errors) if errors else None,
            triggered_by,
        )

        logger.info(f"Full prefill complete in {duration:.1f}s: {results}")
        return results


# Singleton instance
prefill_service = DataPrefillService()


async def run_prefill() -> dict[str, Any]:
    """Run the full prefill pipeline."""
    return await prefill_service.run_full_prefill()
