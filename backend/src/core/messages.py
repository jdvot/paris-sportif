"""Multi-language message templates for predictions.

Centralized location for all user-facing text that needs translation support.
"""

from typing import Literal

Language = Literal["fr", "en", "nl"]


# ============== KEY FACTORS TEMPLATES ==============
# Templates for positive factors about a team
KEY_FACTORS_TEMPLATES: dict[Language, dict[str, list[str]]] = {
    "fr": {
        "home_dominant": [
            "Tres bonne forme domestique",
            "Avantage du terrain significatif",
            "Superiorite en possession statistique",
            "Attaque puissante a domicile",
            "Serie de victoires a domicile",
            "Defense solide sur leur terrain",
        ],
        "away_strong": [
            "Excellente serie en deplacement",
            "Defense tres solide en exterieur",
            "Efficacite offensive elevee",
            "Moral de l'equipe excellent",
            "Bon bilan face a cet adversaire",
            "Equipe en pleine confiance",
        ],
        "balanced": [
            "Matchs equilibres historiquement",
            "Formes similaires actuellement",
            "Qualite defensive comparable",
            "Potentiel de score nul eleve",
            "Confrontations souvent serrees",
            "Peu de buts dans les H2H recents",
        ],
    },
    "en": {
        "home_dominant": [
            "Excellent home form",
            "Significant home advantage",
            "Statistical possession superiority",
            "Powerful home attack",
            "Home winning streak",
            "Solid defense at home",
        ],
        "away_strong": [
            "Excellent away form",
            "Very solid away defense",
            "High offensive efficiency",
            "Excellent team morale",
            "Good record against opponent",
            "Team full of confidence",
        ],
        "balanced": [
            "Historically balanced matches",
            "Similar current form",
            "Comparable defensive quality",
            "High draw potential",
            "Tight encounters historically",
            "Few goals in recent H2H",
        ],
    },
    "nl": {
        "home_dominant": [
            "Uitstekende thuisvorm",
            "Significant thuisvoordeel",
            "Statistisch balbezitvooerdeel",
            "Krachtige thuisaanval",
            "Reeks thuisoverwinningen",
            "Solide verdediging thuis",
        ],
        "away_strong": [
            "Uitstekende uitvorm",
            "Zeer solide uitverdediging",
            "Hoge aanvallende efficientie",
            "Uitstekend teammoraal",
            "Goede resultaten tegen tegenstander",
            "Vol vertrouwen spelend team",
        ],
        "balanced": [
            "Historisch evenwichtige wedstrijden",
            "Vergelijkbare huidige vorm",
            "Vergelijkbare verdedigende kwaliteit",
            "Hoge gelijke kans",
            "Historisch spannende duels",
            "Weinig doelpunten in recente H2H",
        ],
    },
}


# ============== RISK FACTORS TEMPLATES ==============
# Templates for risk warnings
RISK_FACTORS_TEMPLATES: dict[Language, list[str]] = {
    "fr": [
        "Absence de joueurs cles possibles",
        "Fatigue accumulee (calendrier charge)",
        "Conditions meteorologiques defavorables",
        "Historique imprevisible dans ce duel",
        "Equipe en reconstruction",
        "Pression du classement",
        "Match retour de treve internationale",
        "Deplacement lointain recent",
    ],
    "en": [
        "Possible key player absences",
        "Accumulated fatigue (congested schedule)",
        "Unfavorable weather conditions",
        "Unpredictable history in this matchup",
        "Team in rebuilding phase",
        "League position pressure",
        "Return from international break",
        "Recent long-distance travel",
    ],
    "nl": [
        "Mogelijke afwezigheid sleutelspelers",
        "Opgebouwde vermoeidheid (druk schema)",
        "Ongunstige weersomstandigheden",
        "Onvoorspelbare historie in dit duel",
        "Team in wederopbouw",
        "Druk door klassement",
        "Terugkeer na interlandbreak",
        "Recente lange reis",
    ],
}


# ============== EXPLANATION TEMPLATES ==============
# Templates for prediction explanations
EXPLANATIONS_TEMPLATES: dict[Language, dict[str, str]] = {
    "fr": {
        "home_win": (
            "Notre analyse privilegie {home} pour cette rencontre. L'equipe beneficie d'un "
            "fort avantage du terrain combine a une excellente forme actuelle. {away} reste "
            "competitif mais devrait avoir du mal a creer des occasions decisives."
        ),
        "draw": (
            "Un match equilibre ou les deux equipes possedent les atouts pour obtenir un "
            "resultat positif. Les statistiques suggerent un partage des points probable "
            "avec un contexte tactique ferme."
        ),
        "away_win": (
            "Malgre le deplacement, {away} dispose des arguments suffisants pour s'imposer. "
            "La qualite de leur jeu actuel pourrait faire la difference face a {home}."
        ),
    },
    "en": {
        "home_win": (
            "Our analysis favors {home} for this match. The team benefits from a "
            "strong home advantage combined with excellent current form. {away} remains "
            "competitive but may struggle to create decisive chances."
        ),
        "draw": (
            "A balanced match where both teams have the qualities to achieve a "
            "positive result. Statistics suggest a likely draw "
            "in a tight tactical context."
        ),
        "away_win": (
            "Despite the away fixture, {away} has sufficient arguments to win. "
            "Their current quality of play could make the difference against {home}."
        ),
    },
    "nl": {
        "home_win": (
            "Onze analyse geeft de voorkeur aan {home} voor deze wedstrijd. "
            "Het team profiteert van een sterk thuisvoordeel gecombineerd met "
            "een uitstekende huidige vorm. {away} blijft "
            "competitief maar zal moeite hebben om beslissende kansen te creeren."
        ),
        "draw": (
            "Een evenwichtige wedstrijd waarin beide teams de kwaliteiten hebben om een "
            "positief resultaat te behalen. Statistieken suggereren een waarschijnlijk gelijkspel "
            "in een strak tactisch duel."
        ),
        "away_win": (
            "Ondanks de uitwedstrijd heeft {away} voldoende argumenten om te winnen. "
            "Hun huidige kwaliteit van spel kan het verschil maken tegen {home}."
        ),
    },
}


# ============== DYNAMIC FACTOR LABELS ==============
# Labels used in dynamically generated factors
DYNAMIC_LABELS: dict[Language, dict[str, str]] = {
    "fr": {
        "elo_advantage": "Superiorite ELO",
        "good_form": "Bonne forme",
        "poor_form": "Forme difficile",
        "missing_players": "Absences",
        "home_advantage": "Avantage terrain",
        "evenly_matched": "Equipes proches",
        "match_uncertainty": "Incertitude match",
        "physical_advantage": "Avantage physique (plus de repos)",
        "busy_schedule": "Calendrier charge (fatigue potentielle)",
    },
    "en": {
        "elo_advantage": "ELO advantage",
        "good_form": "Good form",
        "poor_form": "Poor form",
        "missing_players": "Missing players",
        "home_advantage": "Home advantage",
        "evenly_matched": "Evenly matched",
        "match_uncertainty": "Match uncertainty",
        "physical_advantage": "Physical advantage (more rest)",
        "busy_schedule": "Busy schedule (potential fatigue)",
    },
    "nl": {
        "elo_advantage": "ELO voordeel",
        "good_form": "Goede vorm",
        "poor_form": "Slechte vorm",
        "missing_players": "Afwezigen",
        "home_advantage": "Thuisvoordeel",
        "evenly_matched": "Gelijkwaardig",
        "match_uncertainty": "Wedstrijd onzekerheid",
        "physical_advantage": "Fysiek voordeel (meer rust)",
        "busy_schedule": "Druk schema (mogelijke vermoeidheid)",
    },
}


# ============== API ERROR MESSAGES ==============
# User-facing error/warning messages for API responses
API_MESSAGES: dict[str, dict[Language, str]] = {
    # User profile
    "profile_save_error": {
        "fr": "Impossible de sauvegarder les modifications du profil",
        "en": "Failed to save profile changes",
    },
    # Team analysis
    "team_analysis_unavailable": {
        "fr": "Analyse de {team_name} temporairement indisponible.",
        "en": "Analysis of {team_name} temporarily unavailable.",
    },
    "team_analysis_service_error": {
        "fr": (
            "Impossible de générer l'analyse pour {team_name}. "
            "Service temporairement indisponible."
        ),
        "en": "Unable to generate analysis for {team_name}. Service temporarily unavailable.",
    },
    # LLM prompt labels
    "recent_articles_label": {
        "fr": "Articles récents",
        "en": "Recent articles",
    },
    "injuries_label": {
        "fr": "Blessures/Absences",
        "en": "Injuries/Absences",
    },
    "form_unavailable": {
        "fr": "Forme: Non disponible",
        "en": "Form: Not available",
    },
    "news_none": {
        "fr": "Actualités: Aucune actualité récente",
        "en": "News: No recent news",
    },
    "injuries_none": {
        "fr": "Blessures: Aucune blessure signalée",
        "en": "Injuries: No injuries reported",
    },
    "recent_form": {
        "fr": "Forme récente: {wins}V-{draws}N-{losses}D sur les 5 derniers matchs",
        "en": "Recent form: {wins}W-{draws}D-{losses}L in last 5 matches",
    },
    "ranking_position": {
        "fr": ", {position}{suffix} au classement",
        "en": ", {position}{suffix} in standings",
    },
    # Predictions: rate limit / API errors
    "rate_limit_reached": {
        "fr": "[BETA] Limite API externe atteinte (football-data.org: 10 req/min)",
        "en": "[BETA] External API rate limit reached (football-data.org: 10 req/min)",
    },
    "rate_limit_tip": {
        "fr": "Réessayez dans quelques instants ou consultez les picks en cache",
        "en": "Try again shortly or check cached picks",
    },
    "api_error": {
        "fr": "[BETA] Erreur API externe: {detail}",
        "en": "[BETA] External API error: {detail}",
    },
    "api_unavailable_tip": {
        "fr": "L'API football-data.org est temporairement indisponible",
        "en": "football-data.org API is temporarily unavailable",
    },
    "estimated_prediction": {
        "fr": "[BETA] Prédiction estimée - {reason}",
        "en": "[BETA] Estimated prediction - {reason}",
    },
    "fallback_data_warning": {
        "fr": "Données basées sur des modèles statistiques sans contexte temps réel",
        "en": "Data based on statistical models without real-time context",
    },
    "rate_limit_reason": {
        "fr": "Limite API externe atteinte (10 req/min)",
        "en": "External API rate limit reached (10 req/min)",
    },
    "api_error_reason": {
        "fr": "Erreur API externe: {detail}",
        "en": "External API error: {detail}",
    },
    "unexpected_error_reason": {
        "fr": "Erreur inattendue: {detail}",
        "en": "Unexpected error: {detail}",
    },
    "api_error_beta": {
        "fr": "[BETA] Erreur API: {detail}",
        "en": "[BETA] API error: {detail}",
    },
    # Matches: live scores
    "live_scores_rate_limit": {
        "fr": "Limite API externe atteinte",
        "en": "External API rate limit reached",
    },
    "live_scores_unavailable": {
        "fr": "Scores en direct temporairement indisponibles.",
        "en": "Live scores temporarily unavailable.",
    },
    "live_scores_service_unavailable": {
        "fr": "Scores en direct indisponibles",
        "en": "Live scores unavailable",
    },
    "external_api_unavailable": {
        "fr": "API externe indisponible: {detail}",
        "en": "External API unavailable: {detail}",
    },
    # Matches: standings
    "standings_cache_warning": {
        "fr": "[BETA] Classement en cache - API externe indisponible",
        "en": "[BETA] Standings from cache - external API unavailable",
    },
    "error_detail": {
        "fr": "Erreur: {detail}",
        "en": "Error: {detail}",
    },
    # LLM adjustments
    "contextual_data_unavailable": {
        "fr": "Données contextuelles non disponibles.",
        "en": "Contextual data not available.",
    },
    # RAG reasoning strings
    "rag_no_context": {
        "fr": "Aucune information contextuelle significative trouvée dans les news récentes.",
        "en": "No significant contextual information found in recent news.",
    },
    "rag_injuries_reported": {
        "fr": "{team}: {count} blessure(s) signalée(s)",
        "en": "{team}: {count} injury(ies) reported",
    },
    "rag_sentiment": {
        "fr": "{team}: sentiment {sentiment} dans les news",
        "en": "{team}: {sentiment} sentiment in news",
    },
}


def api_msg(key: str, lang: Language = "fr", **kwargs: str | int) -> str:
    """Get a translated API message.

    Args:
        key: Message key from API_MESSAGES dict.
        lang: Language code ("fr", "en", or "nl").
        **kwargs: Format arguments for the message template.

    Returns:
        Formatted message string. Falls back to French if lang not found.
    """
    entry = API_MESSAGES.get(key)
    if not entry:
        return key
    template = entry.get(lang) or entry.get("fr", key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def ordinal_suffix(position: int, lang: Language = "fr") -> str:
    """Get ordinal suffix for a ranking position."""
    if lang == "en":
        if 11 <= position % 100 <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(position % 10, "th")
    return "er" if position == 1 else "e"


def get_key_factors_templates(language: Language = "fr") -> dict[str, list[str]]:
    """Get key factors templates for the specified language."""
    return KEY_FACTORS_TEMPLATES.get(language, KEY_FACTORS_TEMPLATES["fr"])


def get_risk_factors_templates(language: Language = "fr") -> list[str]:
    """Get risk factors templates for the specified language."""
    return RISK_FACTORS_TEMPLATES.get(language, RISK_FACTORS_TEMPLATES["fr"])


def get_explanation_template(bet_type: str, language: Language = "fr") -> str:
    """Get explanation template for the specified bet type and language."""
    templates = EXPLANATIONS_TEMPLATES.get(language, EXPLANATIONS_TEMPLATES["fr"])
    return templates.get(bet_type, templates.get("draw", ""))


def get_label(key: str, language: Language = "fr") -> str:
    """Get a localized label by key."""
    labels = DYNAMIC_LABELS.get(language, DYNAMIC_LABELS["fr"])
    return labels.get(key, key)
