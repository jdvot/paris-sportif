"""User profile endpoints.

Provides endpoints for user profile management, preferences, and team search.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.auth.supabase_auth import (
    get_user_role_from_profiles,
    sync_role_to_app_metadata,
    update_user_metadata,
)
from src.db.services.user_service import PreferencesService
from src.db.repositories.unit_of_work import get_uow

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
    role_from_db = False

    # Fallback: check user_profiles table if role not in metadata
    if not role:
        role = await get_user_role_from_profiles(user_id)
        if role:
            role_from_db = True
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
            raise HTTPException(
                status_code=500,
                detail="Impossible de sauvegarder les modifications du profil",
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

    Returns statistics about the user's activity on the platform.
    """
    # In a real implementation, this would fetch from database
    # For now, return placeholder data
    return UserStatsResponse(
        total_predictions_viewed=0,
        favorite_competition=None,
        member_since_days=0,
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
    competition: str | None = None
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


@router.get("/teams/{team_id}/summary", response_model=TeamSummaryResponse, responses=AUTH_RESPONSES)
async def get_team_summary(
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

        # Get standing info if available
        standing = await uow.standings.get_team_standing(team_id)
        position = standing.position if standing else None
        competition = standing.competition_code if standing else None

    # Generate summary using RAG + LLM
    try:
        from src.prediction_engine.rag_enrichment import get_rag_enrichment
        from src.llm.client import get_llm_client

        rag = get_rag_enrichment()
        llm = get_llm_client()

        # Get team context from RAG (news articles, injuries, form)
        context = await rag.get_team_context(team_name)

        # Extract data from RAG context
        news_articles = context.get("news", [])
        injuries = context.get("injuries", [])
        key_info = context.get("key_info", [])
        sentiment = context.get("sentiment", "neutral")
        recent_form = context.get("recent_form", [])

        # Build news context for LLM
        news_context = ""
        if news_articles:
            news_items = []
            for article in news_articles[:5]:
                title = article.get("title", "")
                if title:
                    news_items.append(f"- {title}")
            if news_items:
                news_context = "Articles récents:\n" + "\n".join(news_items)

        # Build injuries context
        injuries_context = ""
        if injuries:
            inj_items = []
            for inj in injuries[:3]:
                if isinstance(inj, dict):
                    player = inj.get("player", inj.get("player_name", ""))
                    inj_type = inj.get("type", inj.get("injury_type", "blessure"))
                    if player:
                        inj_items.append(f"- {player}: {inj_type}")
            if inj_items:
                injuries_context = "Blessures/Absences:\n" + "\n".join(inj_items)

        # Build form context
        form_context = ""
        if form_string:
            wins = form_string.count("W")
            draws = form_string.count("D")
            losses = form_string.count("L")
            form_context = f"Forme récente: {wins}V-{draws}N-{losses}D sur les 5 derniers matchs"
            if position:
                form_context += f", {position}{'er' if position == 1 else 'e'} au classement"

        # Build LLM prompt
        prompt = f"""Tu es un analyste football expert. Génère une analyse concise de la situation actuelle de {team_name}.

DONNÉES DISPONIBLES:
{form_context if form_context else "Forme: Non disponible"}

{news_context if news_context else "Actualités: Aucune actualité récente"}

{injuries_context if injuries_context else "Blessures: Aucune blessure signalée"}

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
            summary = f"Analyse de {team_name} temporairement indisponible."

        return TeamSummaryResponse(
            team_id=team_id,
            team_name=team_name,
            summary=summary,
            form=list(form_string) if form_string else [],
            position=position,
            competition=competition,
            generated_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.warning(f"Failed to generate LLM summary for team {team_id}: {e}")
        # Fallback to basic template if LLM fails
        fallback_parts = []
        if form_string:
            wins = form_string.count("W")
            draws = form_string.count("D")
            losses = form_string.count("L")
            fallback_parts.append(f"{team_name}: {wins}V-{draws}N-{losses}D récemment")
        if position:
            fallback_parts.append(f"{position}{'er' if position == 1 else 'e'} au classement")

        fallback = ". ".join(fallback_parts) if fallback_parts else f"Informations sur {team_name} temporairement indisponibles."

        return TeamSummaryResponse(
            team_id=team_id,
            team_name=team_name,
            summary=fallback,
            form=list(form_string) if form_string else [],
            position=position,
            competition=competition,
            generated_at=datetime.utcnow().isoformat(),
        )
