"""Advanced LLM prompts for football match analysis.

These prompts leverage Groq's Mixtral 8x7B to provide sophisticated analysis
that complements statistical models with contextual intelligence.
"""


def get_prediction_analysis_prompt(
    home_team: str,
    away_team: str,
    competition: str,
    home_current_form: str = "",
    away_current_form: str = "",
    home_injuries: str = "",
    away_injuries: str = "",
    head_to_head: str = "",
) -> str:
    """
    Generate a comprehensive match analysis prompt.

    Args:
        home_team: Home team name
        away_team: Away team name
        competition: Competition name
        home_current_form: Recent form summary
        away_current_form: Recent form summary
        home_injuries: Injury information
        away_injuries: Injury information
        head_to_head: Historical matchup information

    Returns:
        Formatted prompt for LLM
    """
    return f"""Tu es un expert en analyse de matchs de football avec 15 ans d'expérience.
Analyse ce match en détail et fournis des insights professionnels.

MATCH: {home_team} vs {away_team}
Compétition: {competition}

CONTEXTE ACTUEL:
Forme de {home_team}: {home_current_form or "Non disponible"}
Forme de {away_team}: {away_current_form or "Non disponible"}

SITUATION DES JOUEURS:
Blessures {home_team}: {home_injuries or "Aucune connue"}
Blessures {away_team}: {away_injuries or "Aucune connue"}

HISTORIQUE:
{head_to_head or "Pas de données historiques"}

ANALYSE REQUISE:
1. Évalue la force relative des deux équipes actuellement
2. Identifie les facteurs clés qui influenceront le résultat
3. Estime l'impact des blessures et absences
4. Analyse les tendances tactiques et les forces défensives
5. Fournis une estimation des probabilités de résultat

IMPORTANT - Tu dois répondre UNIQUEMENT avec un JSON valide (pas de texte avant ou après):
{{
    "home_win_probability": 0.00,
    "draw_probability": 0.00,
    "away_win_probability": 0.00,
    "confidence_level": "low|medium|high",
    "key_factors": [
        "Facteur clé 1",
        "Facteur clé 2",
        "Facteur clé 3"
    ],
    "injury_impact_home": -0.15,
    "injury_impact_away": -0.10,
    "tactical_insight": "Explication brève de l'analyse tactique",
    "expected_goals_home": 1.5,
    "expected_goals_away": 1.2,
    "reasoning": "Explication détaillée de l'analyse"
}}

Contraintes:
- Les trois probabilités doivent totaliser 1.0 exactement
- injury_impact doit être entre -0.3 et 0.0
- confidence_level doit être l'une des trois options
- Tous les champs doivent être présents"""


def get_injury_impact_prompt(
    team_name: str,
    absent_players: list[str],
    team_strength: str = "medium",
    competition_importance: str = "regular",
) -> str:
    """
    Generate prompt for analyzing injury impact.

    Args:
        team_name: Team name
        absent_players: List of absent player names
        team_strength: Team strength level (weak/medium/strong)
        competition_importance: Match importance (regular/important/critical)

    Returns:
        Formatted prompt for LLM
    """
    players_str = ", ".join(absent_players) if absent_players else "Aucun"

    return f"""Analyse l'impact des absences sur la performance de {team_name}.

ÉQUIPE: {team_name}
Force générale: {team_strength}
Importance du match: {competition_importance}
Joueurs absents/blessés: {players_str}

Fournis une évaluation numérique de l'impact (de -0.3 à 0.0):
- -0.3: Impact critique (équipe affaiblie considérablement)
- -0.15: Impact modéré (quelques absents importants)
- -0.05: Impact faible (absents mineurs)
- 0.0: Aucun impact (équipe au complet ou absents très mineurs)

Réponds UNIQUEMENT avec un nombre entre -0.3 et 0.0."""


def get_form_sentiment_prompt(
    team_name: str,
    recent_results: list[str],
    media_sentiment: str = "neutral",
    tactical_changes: str = "",
) -> str:
    """
    Generate prompt for analyzing team form and sentiment.

    Args:
        team_name: Team name
        recent_results: List of recent match results
        media_sentiment: Overall media sentiment
        tactical_changes: Recent tactical changes

    Returns:
        Formatted prompt for LLM
    """
    results_str = " -> ".join(recent_results) if recent_results else "Aucun résultat"

    return f"""Analyse la forme et le moral de {team_name}.

ÉQUIPE: {team_name}
Résultats récents: {results_str}
Sentiment médias: {media_sentiment}
Changements tactiques: {tactical_changes or "Aucun"}

Fournis un score de sentiment entre -0.1 et +0.1:
- +0.1: Équipe en très bonne confiance, momentum positif
- +0.05: Équipe en confiance, légèrement optimiste
- 0.0: Équipe neutre, forme équilibrée
- -0.05: Équipe en doute, quelques résultats négatifs
- -0.1: Équipe en crise de confiance, fort pessimisme

Réponds UNIQUEMENT avec un nombre entre -0.1 et +0.1."""


def get_tactical_matchup_prompt(
    home_team: str,
    away_team: str,
    home_style: str = "",
    away_style: str = "",
) -> str:
    """
    Generate prompt for tactical analysis.

    Args:
        home_team: Home team name
        away_team: Away team name
        home_style: Home team's typical style
        away_style: Away team's typical style

    Returns:
        Formatted prompt for LLM
    """
    return f"""Analyse le matchup tactique entre {home_team} et {away_team}.

MATCHUP TACTIQUE:
Style de {home_team}: {home_style or "Non spécifié"}
Style de {away_team}: {away_style or "Non spécifié"}

Considère:
1. Comment {home_team} joue-t-il généralement?
2. Comment {away_team} s'adapte-t-il en déplacement?
3. Quels sont les avantages/désavantages de chaque approche?
4. Y a-t-il une équipe mieux adaptée tactiquement?

Fournis un avantage tactique entre -0.05 et +0.05:
- +0.05: Avantage tactique clair pour {home_team}
- +0.02: Léger avantage tactique pour {home_team}
- 0.0: Équilibre tactique
- -0.02: Léger avantage tactique pour {away_team}
- -0.05: Avantage tactique clair pour {away_team}

Réponds UNIQUEMENT avec un nombre entre -0.05 et +0.05."""


def get_expected_goals_prompt(
    home_team: str,
    away_team: str,
    home_attack_quality: str = "medium",
    away_attack_quality: str = "medium",
    home_defense_quality: str = "medium",
    away_defense_quality: str = "medium",
) -> str:
    """
    Generate prompt for expected goals estimation.

    Args:
        home_team: Home team name
        away_team: Away team name
        home_attack_quality: Quality of home team's attack
        away_attack_quality: Quality of away team's attack
        home_defense_quality: Quality of home team's defense
        away_defense_quality: Quality of away team's defense

    Returns:
        Formatted prompt for LLM
    """
    return f"""Estime les buts attendus (xG) pour ce match.

ÉQUIPES:
{home_team}: Attaque {home_attack_quality}, Défense {home_defense_quality}
{away_team}: Attaque {away_attack_quality}, Défense {away_defense_quality}

Basé sur la qualité des attaques et défenses:
- Équipes avec très bonne attaque créent généralement 2.0-2.5 xG
- Équipes avec bonne attaque créent 1.5-2.0 xG
- Équipes avec attaque moyenne créent 1.2-1.5 xG
- Équipes avec faible attaque créent 0.8-1.2 xG
- Excellente défense réduit le xG concédé
- Faible défense augmente le xG concédé

Fournis les xG estimées en JSON:
{{
    "home_xg": 1.5,
    "away_xg": 1.3
}}

Les valeurs doivent être entre 0.5 et 3.5."""


def get_motivation_prompt(
    home_team: str,
    away_team: str,
    league_position_home: str = "",
    league_position_away: str = "",
    stakes: str = "regular",
) -> str:
    """
    Generate prompt for motivation/pressure analysis.

    Args:
        home_team: Home team name
        away_team: Away team name
        league_position_home: Home team's league position
        league_position_away: Away team's league position
        stakes: Match stakes (regular/important/critical)

    Returns:
        Formatted prompt for LLM
    """
    return f"""Analyse la motivation et la pression pour ce match.

CONTEXTE:
{home_team}: Position au classement: {league_position_home or "Non spécifié"}
{away_team}: Position au classement: {league_position_away or "Non spécifié"}
Enjeux du match: {stakes}

Facteurs à considérer:
- Équipe en lutte pour le titre (+0.10 à +0.15)
- Équipe en lutte contre la relégation (-0.15 à -0.10)
- Match de derby ou très important (+0.10)
- Équipe en revanchard (+0.05)
- Équipe ayant peu à perdre (-0.05)

Fournis un facteur de motivation entre -0.15 et +0.15:
Positif = équipe fortement motivée
Négatif = équipe peu motivée/sous pression negative

Réponds UNIQUEMENT avec un nombre entre -0.15 et +0.15."""


def get_probability_adjustment_prompt(
    home_win_prob: float,
    draw_prob: float,
    away_win_prob: float,
    model_confidence: float,
    additional_context: str = "",
) -> str:
    """
    Generate prompt for final probability adjustments.

    Args:
        home_win_prob: Home win probability from models
        draw_prob: Draw probability from models
        away_win_prob: Away win probability from models
        model_confidence: Overall model confidence
        additional_context: Any additional context

    Returns:
        Formatted prompt for LLM
    """
    return f"""Révise ces probabilités de prédiction en fonction de contexte humain.

PROBABILITÉS MODÈLES:
Victoire {home_win_prob:.1%} | Match nul {draw_prob:.1%} | Victoire adverse {away_win_prob:.1%}
Confiance du modèle: {model_confidence:.0%}

CONTEXTE ADDITIONNEL:
{additional_context or "Aucun contexte particulier"}

Considère si ces probabilités semblent justes ou si des ajustements sont nécessaires
basés sur des facteurs que les modèles statistiques ne capturent pas:
- Dynamique de groupe et moral
- Expérience en grandes compétitions
- Facteurs psychologiques
- Événements récents non quantifiables

Les probabilités révisées doivent:
1. Totaliser exactement 1.0
2. Être raisonnablement proches des estimations du modèle
3. Refléter le contexte humain

Réponds UNIQUEMENT avec le JSON:
{{
    "home_win": 0.00,
    "draw": 0.00,
    "away_win": 0.00,
    "adjustment_reason": "Explication brève"
}}"""
