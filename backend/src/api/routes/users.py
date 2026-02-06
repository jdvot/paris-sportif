"""User profile endpoints.

Provides endpoints for user profile management, preferences, and team search.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.auth.supabase_auth import (
    get_user_role_from_profiles,
    sync_role_to_app_metadata,
    update_user_metadata,
)
from src.core.messages import api_msg, detect_language_from_header, ordinal_suffix
from src.db.repositories.unit_of_work import get_uow
from src.db.services.user_service import PreferencesService

logger = logging.getLogger(__name__)

router = APIRouter()


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: str
    email: str | None
    full_name: str | None
    role: str
    created_at: str | None


class UserProfileUpdate(BaseModel):
    """User profile update request."""

    full_name: str | None = None


class UserStatsResponse(BaseModel):
    """User statistics response."""

    total_predictions_viewed: int = 0
    favorite_competition: str | None = None
    member_since_days: int = 0


@router.get("/me", response_model=UserProfileResponse, responses=AUTH_RESPONSES)
async def get_current_profile(user: AuthenticatedUser) -> UserProfileResponse:
    """
    Get current user's profile.

    Returns the authenticated user's profile information.
    Fetches fresh data from Supabase to reflect recent updates.
    """
    from src.auth.supabase_auth import get_user_from_supabase

    user_id = user.get("sub", "")

    # Try to get fresh user data from Supabase
    fresh_user = await get_user_from_supabase(user_id)

    if fresh_user:
        user_metadata = fresh_user.get("user_metadata", {})
        app_metadata = fresh_user.get("app_metadata", {})
        email = fresh_user.get("email")
        created_at = fresh_user.get("created_at")
    else:
        # Fallback to JWT data if Supabase fetch fails
        user_metadata = user.get("user_metadata", {})
        app_metadata = user.get("app_metadata", {})
        email = user.get("email")
        created_at = user.get("created_at")

    # Get role from app_metadata first, then user_metadata
    role = app_metadata.get("role") or user_metadata.get("role")

    # Fallback: check user_profiles table if role not in metadata
    if not role:
        role = await get_user_role_from_profiles(user_id)
        if role:
            # Sync role to app_metadata so future JWT tokens will have it
            await sync_role_to_app_metadata(user_id, role)

    # Default to "free" if no role found anywhere
    role = role or "free"

    return UserProfileResponse(
        id=user_id,
        email=email,
        full_name=user_metadata.get("full_name"),
        role=role,
        created_at=created_at,
    )


@router.patch("/me", response_model=UserProfileResponse, responses=AUTH_RESPONSES)
async def update_profile(
    request: Request,
    user: AuthenticatedUser,
    updates: UserProfileUpdate,
) -> UserProfileResponse:
    """
    Update current user's profile.

    Persists changes to Supabase user metadata.
    """
    user_id = user.get("sub", "")
    user_metadata = user.get("user_metadata", {}).copy()
    app_metadata = user.get("app_metadata", {})

    # Build metadata updates
    metadata_updates: dict[str, str | None] = {}
    if updates.full_name is not None:
        metadata_updates["full_name"] = updates.full_name
        user_metadata["full_name"] = updates.full_name

    # Persist to Supabase if there are updates
    if metadata_updates and user_id:
        result = await update_user_metadata(user_id, metadata_updates)
        if result is None:
            logger.warning(f"Failed to persist profile update for user {user_id}")
            lang = detect_language_from_header(request.headers.get("Accept-Language", ""))
            raise HTTPException(
                status_code=500,
                detail=api_msg("profile_save_error", lang),
            )
        logger.info(f"Profile updated for user {user_id}")

    # Get role from app_metadata first, then user_metadata
    role = app_metadata.get("role") or user_metadata.get("role")

    # Fallback: check user_profiles table if role not in metadata
    if not role:
        role = await get_user_role_from_profiles(user_id)

    # Default to "free" if no role found anywhere
    role = role or "free"

    return UserProfileResponse(
        id=user_id,
        email=user.get("email"),
        full_name=user_metadata.get("full_name"),
        role=role,
        created_at=user.get("created_at"),
    )


@router.get("/me/stats", response_model=UserStatsResponse, responses=AUTH_RESPONSES)
async def get_user_stats(user: AuthenticatedUser) -> UserStatsResponse:
    """
    Get current user's usage statistics.

    Returns statistics about the user's activity on the platform,
    computed from real database data.
    """
    from datetime import datetime

    user_id = user.get("sub", "")

    # Calculate member_since_days from JWT created_at
    member_since_days = 0
    created_at = user.get("created_at")
    if created_at:
        try:
            if isinstance(created_at, str):
                # Parse ISO format, handle both with/without timezone
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created_dt = created_at
            member_since_days = max(0, (datetime.now(created_dt.tzinfo) - created_dt).days)
        except (ValueError, TypeError):
            pass

    # Get favorite competition from user preferences
    favorite_competition = None
    try:
        prefs = await PreferencesService.get_preferences(user_id)
        if prefs and prefs.get("favorite_competitions"):
            favorite_competition = prefs["favorite_competitions"][0]
    except Exception as e:
        logger.warning(f"Failed to get user preferences for {user_id}: {e}")

    # Get total platform predictions (since predictions are system-generated)
    total_predictions_viewed = 0
    try:
        from src.db.services.prediction_service import PredictionService

        stats = await PredictionService.get_statistics(days=365)
        total_predictions_viewed = stats.get("total_predictions", 0)
    except Exception as e:
        logger.warning(f"Failed to get prediction stats: {e}")

    return UserStatsResponse(
        total_predictions_viewed=total_predictions_viewed,
        favorite_competition=favorite_competition,
        member_since_days=member_since_days,
    )


# ============================================================================
# User Preferences Endpoints
# ============================================================================


class FavoriteTeamInfo(BaseModel):
    """Favorite team details."""

    id: int
    name: str
    short_name: str
    logo_url: str | None = None
    country: str | None = None


class UserPreferencesResponse(BaseModel):
    """User preferences response."""

    language: str
    timezone: str
    odds_format: str
    dark_mode: bool
    email_daily_picks: bool
    email_match_results: bool
    push_daily_picks: bool
    push_match_start: bool
    push_bet_results: bool
    default_stake: float
    risk_level: str
    favorite_competitions: list[str]
    favorite_team_id: int | None = None
    favorite_team: FavoriteTeamInfo | None = None


class UserPreferencesUpdate(BaseModel):
    """User preferences update request."""

    language: str | None = None
    timezone: str | None = None
    odds_format: str | None = None
    dark_mode: bool | None = None
    email_daily_picks: bool | None = None
    email_match_results: bool | None = None
    push_daily_picks: bool | None = None
    push_match_start: bool | None = None
    push_bet_results: bool | None = None
    default_stake: float | None = None
    risk_level: str | None = None
    favorite_competitions: list[str] | None = None
    favorite_team_id: int | None = None


@router.get("/me/preferences", response_model=UserPreferencesResponse, responses=AUTH_RESPONSES)
async def get_preferences(user: AuthenticatedUser) -> UserPreferencesResponse:
    """
    Get current user's preferences.

    Returns display, notification, and betting preferences.
    """
    user_id = user.get("sub", "")
    prefs = await PreferencesService.get_preferences(user_id)
    return UserPreferencesResponse(**prefs)


@router.put("/me/preferences", response_model=UserPreferencesResponse, responses=AUTH_RESPONSES)
async def update_preferences(
    user: AuthenticatedUser,
    updates: UserPreferencesUpdate,
) -> UserPreferencesResponse:
    """
    Update current user's preferences.

    Supports partial updates - only provided fields will be changed.
    """
    user_id = user.get("sub", "")

    # Convert to dict, excluding None values
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not update_data:
        # No updates, just return current preferences
        prefs = await PreferencesService.get_preferences(user_id)
        return UserPreferencesResponse(**prefs)

    # Validate favorite_team_id exists if provided
    if "favorite_team_id" in update_data and update_data["favorite_team_id"] is not None:
        async with get_uow() as uow:
            team = await uow.teams.get_by_id(update_data["favorite_team_id"])
            if not team:
                raise HTTPException(
                    status_code=400,
                    detail=f"Team with ID {update_data['favorite_team_id']} not found",
                )

    prefs = await PreferencesService.update_preferences(user_id, **update_data)
    return UserPreferencesResponse(**prefs)


# ============================================================================
# Team Search Endpoints
# ============================================================================


class TeamSearchResult(BaseModel):
    """Team search result."""

    id: int
    name: str
    short_name: str | None = None
    logo_url: str | None = None
    country: str | None = None


class TeamSearchResponse(BaseModel):
    """Team search response."""

    teams: list[TeamSearchResult]
    total: int


@router.get("/teams/search", response_model=TeamSearchResponse, responses=AUTH_RESPONSES)
async def search_teams(
    user: AuthenticatedUser,
    q: str = Query(..., min_length=2, description="Search query (min 2 characters)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
) -> TeamSearchResponse:
    """
    Search for teams by name.

    Returns teams matching the search query for use in autocomplete.
    """
    async with get_uow() as uow:
        teams = await uow.teams.search_by_name(q, limit=limit)

        results = [
            TeamSearchResult(
                id=team.id,
                name=team.name,
                short_name=team.short_name or team.tla,
                logo_url=team.logo_url,
                country=team.country,
            )
            for team in teams
        ]

        return TeamSearchResponse(teams=results, total=len(results))


# ============================================================================
# Favorite Team News & Summary Endpoints
# ============================================================================


class TeamNewsArticle(BaseModel):
    """News article for a team."""

    title: str
    source: str
    url: str | None = None
    published_at: str | None = None


class TeamNewsResponse(BaseModel):
    """Team news response."""

    team_id: int
    team_name: str
    news: list[TeamNewsArticle]
    total: int


class TeamSummaryResponse(BaseModel):
    """Team summary with RAG-generated content."""

    team_id: int
    team_name: str
    summary: str
    form: list[str]  # ["W", "W", "D", "L", "W"]
    position: int | None = None
    points: int | None = None
    competition: str | None = None
    injuries_count: int = 0
    generated_at: str


@router.get("/teams/{team_id}/news", response_model=TeamNewsResponse, responses=AUTH_RESPONSES)
async def get_team_news(
    user: AuthenticatedUser,
    team_id: int,
    limit: int = Query(5, ge=1, le=20),
) -> TeamNewsResponse:
    """
    Get recent news for a specific team.

    Used for the favorite team section on homepage.
    """
    async with get_uow() as uow:
        team = await uow.teams.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        team_name = team.name

    try:
        from src.vector.news_ingestion import get_ingestion_service

        service = get_ingestion_service()
        articles = await service.fetch_team_news_from_api(team_name, max_articles=limit)

        news = [
            TeamNewsArticle(
                title=a.title,
                source=a.source,
                url=a.url,
                published_at=a.published_at.isoformat() if a.published_at else None,
            )
            for a in articles
        ]

        return TeamNewsResponse(
            team_id=team_id,
            team_name=team_name,
            news=news,
            total=len(news),
        )
    except Exception as e:
        logger.warning(f"Failed to fetch news for team {team_id}: {e}")
        return TeamNewsResponse(
            team_id=team_id,
            team_name=team_name,
            news=[],
            total=0,
        )


@router.get(
    "/teams/{team_id}/summary", response_model=TeamSummaryResponse, responses=AUTH_RESPONSES
)
async def get_team_summary(
    request: Request,
    user: AuthenticatedUser,
    team_id: int,
) -> TeamSummaryResponse:
    """
    Get LLM-generated summary for a team's current situation.

    Uses RAG to fetch recent news/articles and generates analysis via LLM.
    """
    from datetime import datetime

    async with get_uow() as uow:
        team = await uow.teams.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        team_name = team.name
        form_string = team.form or ""

        # Get standing info if available (try by team_id first, then by name)
        standing = await uow.standings.get_team_standing(team_id)
        if not standing:
            # Fallback: search by team name (handles ID mismatches between tables)
            standing = await uow.standings.get_by_team_name(team_name)
        position = standing.position if standing else None
        points = standing.points if standing else None
        competition = standing.competition_code if standing else None

    # Generate summary using RAG + LLM
    try:
        from src.llm.client import get_llm_client
        from src.prediction_engine.rag_enrichment import get_rag_enrichment

        rag = get_rag_enrichment()
        llm = get_llm_client()

        # Get team context from RAG (news articles, injuries, form)
        context = await rag.get_team_context(team_name)

        # Extract data from RAG context
        news_articles = context.get("news", [])
        injuries = context.get("injuries", [])
        sentiment = context.get("sentiment", "neutral")

        lang = detect_language_from_header(request.headers.get("Accept-Language", ""))

        # Build news context for LLM
        news_context = ""
        if news_articles:
            news_items = []
            for article in news_articles[:5]:
                title = article.get("title", "")
                if title:
                    news_items.append(f"- {title}")
            if news_items:
                news_context = (
                    api_msg("recent_articles_label", lang) + ":\n" + "\n".join(news_items)
                )

        # Build injuries context
        injuries_context = ""
        if injuries:
            inj_items = []
            for inj in injuries[:3]:
                if isinstance(inj, dict):
                    player = inj.get("player", inj.get("player_name", ""))
                    inj_type = inj.get("type", inj.get("injury_type", "injury"))
                    if player:
                        inj_items.append(f"- {player}: {inj_type}")
            if inj_items:
                injuries_context = api_msg("injuries_label", lang) + ":\n" + "\n".join(inj_items)

        # Build form context
        form_context = ""
        if form_string:
            wins = form_string.count("W")
            draws = form_string.count("D")
            losses = form_string.count("L")
            form_context = api_msg("recent_form", lang, wins=wins, draws=draws, losses=losses)
            if position:
                suffix = ordinal_suffix(position, lang)
                form_context += api_msg("ranking_position", lang, position=position, suffix=suffix)

        # Build LLM prompt (use user's language for the response)
        if lang == "en":
            prompt = f"""\
You are an expert football analyst. \
Generate a concise analysis of {team_name}'s current situation.

AVAILABLE DATA:
{form_context if form_context else api_msg("form_unavailable", lang)}

{news_context if news_context else api_msg("news_none", lang)}

{injuries_context if injuries_context else api_msg("injuries_none", lang)}

Media sentiment: {sentiment}

INSTRUCTIONS:
- Write 2-3 sentences of synthetic analysis
- Mention current form if available
- Highlight important injuries
- Give an overall impression of the team's dynamic
- Be factual and concise (max 100 words)
- Reply only with the analysis, no title or formatting"""
        else:
            prompt = f"""\
Tu es un analyste football expert. \
Génère une analyse concise de la situation actuelle de {team_name}.

DONNÉES DISPONIBLES:
{form_context if form_context else api_msg("form_unavailable", lang)}

{news_context if news_context else api_msg("news_none", lang)}

{injuries_context if injuries_context else api_msg("injuries_none", lang)}

Sentiment médiatique: {sentiment}

INSTRUCTIONS:
- Écris 2-3 phrases d'analyse synthétique
- Mentionne la forme actuelle si disponible
- Signale les blessures importantes
- Donne une impression générale de la dynamique de l'équipe
- Sois factuel et concis (max 100 mots)
- Réponds uniquement avec l'analyse, sans titre ni formatage"""

        # Call LLM for analysis
        summary = await llm.complete(
            prompt=prompt,
            max_tokens=200,
            temperature=0.3,
        )

        # Clean up response
        summary = summary.strip()
        if not summary:
            summary = api_msg("team_analysis_unavailable", lang, team_name=team_name)

        # Count injuries from context
        injuries_count = len(injuries) if injuries else 0

        return TeamSummaryResponse(
            team_id=team_id,
            team_name=team_name,
            summary=summary,
            form=list(form_string) if form_string else [],
            position=position,
            points=points,
            competition=competition,
            injuries_count=injuries_count,
            generated_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to generate LLM summary for team {team_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=api_msg("team_analysis_service_error", lang, team_name=team_name),
        )
