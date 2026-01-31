"""Prompt templates for LLM tasks."""

# System prompts
SYSTEM_FOOTBALL_ANALYST = """Tu es un analyste de football expert specialise dans la prediction de matchs.
Tu analyses les donnees de maniere objective et quantitative.
Tu dois toujours repondre en francais.
Sois concis et factuel dans tes analyses."""

SYSTEM_JSON_EXTRACTOR = """Tu es un assistant qui extrait des informations structurees.
Tu reponds UNIQUEMENT en JSON valide, sans texte supplementaire.
Respecte exactement le format demande."""

# Injury analysis prompt
INJURY_ANALYSIS_PROMPT = """Analyse cette news de blessure pour l'equipe {team_name}:

{news_text}

Extrait les informations en JSON avec ce format:
{{
    "player_name": "nom du joueur",
    "position": "gardien/defenseur/milieu/attaquant",
    "injury_type": "type de blessure",
    "severity": "minor/moderate/severe",
    "expected_return": "date ou null si inconnue",
    "impact_score": 0.0-1.0,
    "is_key_player": true/false,
    "confidence": 0.0-1.0
}}

impact_score:
- 0.0-0.3: joueur remplacant
- 0.3-0.6: titulaire regulier
- 0.6-0.8: joueur important
- 0.8-1.0: joueur cle/star"""

# Sentiment analysis prompt
SENTIMENT_ANALYSIS_PROMPT = """Analyse le sentiment de ce contenu concernant l'equipe {team_name}:

Source: {source_type}
Contenu: {content}

Evalue en JSON:
{{
    "sentiment_score": -1.0 a 1.0,
    "confidence": 0.0-1.0,
    "key_themes": ["theme1", "theme2"],
    "morale_indicator": "very_negative/negative/neutral/positive/very_positive",
    "forward_outlook": "pessimistic/neutral/optimistic"
}}

sentiment_score:
- -1.0: tres negatif
- 0.0: neutre
- 1.0: tres positif"""

# Match explanation prompt
MATCH_EXPLANATION_PROMPT = """Genere une analyse de match concise en francais.

Match: {home_team} vs {away_team}
Competition: {competition}
Date: {match_date}

Prediction:
- Victoire domicile: {home_prob}%
- Match nul: {draw_prob}%
- Victoire exterieur: {away_prob}%
- Recommandation: {recommended_bet} ({confidence}% confiance)

Statistiques cles:
{key_stats}

Forme recente:
- {home_team}: {home_form}
- {away_team}: {away_form}

Genere en JSON:
{{
    "summary": "Resume en 2-3 phrases (max 150 mots)",
    "key_factors": ["facteur 1", "facteur 2", "facteur 3"],
    "risk_factors": ["risque 1", "risque 2"],
    "betting_angle": "perspective de pari en 1 phrase"
}}"""

# Tactical analysis prompt
TACTICAL_ANALYSIS_PROMPT = """Analyse tactique pour le match {home_team} vs {away_team}.

Formation probable {home_team}: {home_formation}
Formation probable {away_team}: {away_formation}

Historique confrontations:
{h2h_summary}

Style de jeu:
- {home_team}: {home_style}
- {away_team}: {away_style}

Analyse en JSON:
{{
    "tactical_edge": -0.05 a 0.05,
    "edge_for": "home/away/none",
    "key_matchups": ["matchup1", "matchup2"],
    "tactical_insight": "insight en 1-2 phrases",
    "confidence": 0.0-1.0
}}

tactical_edge positif = avantage domicile, negatif = avantage exterieur"""

# Daily picks selection prompt
DAILY_PICKS_SUMMARY_PROMPT = """Resume les 5 picks du jour pour les paris:

{picks_data}

Genere un resume global en JSON:
{{
    "daily_summary": "resume des picks en 2-3 phrases",
    "best_pick": "meilleur pari du jour avec justification courte",
    "total_confidence": "faible/moyenne/haute",
    "risk_level": "faible/modere/eleve",
    "advice": "conseil en 1 phrase"
}}"""
