"""Generate match explanations using LLM."""

from dataclasses import dataclass
from typing import Optional

from src.llm.client import get_llm_client, GroqClient
from src.llm.prompts import SYSTEM_FOOTBALL_ANALYST, MATCH_EXPLANATION_PROMPT
from src.prediction_engine.ensemble import EnsemblePrediction


@dataclass
class MatchExplanation:
    """Generated match explanation."""

    summary: str
    key_factors: list[str]
    risk_factors: list[str]
    betting_angle: str


async def generate_match_explanation(
    home_team: str,
    away_team: str,
    competition: str,
    match_date: str,
    prediction: EnsemblePrediction,
    home_form: str = "N/A",
    away_form: str = "N/A",
    key_stats: Optional[str] = None,
) -> MatchExplanation:
    """
    Generate human-readable match explanation.

    Args:
        home_team: Home team name
        away_team: Away team name
        competition: Competition name
        match_date: Match date string
        prediction: Ensemble prediction result
        home_form: Home team recent form (e.g., "WWDLW")
        away_form: Away team recent form
        key_stats: Additional stats to include

    Returns:
        MatchExplanation with summary and factors
    """
    client = get_llm_client()

    # Format prediction data
    recommended_map = {
        "home": f"Victoire {home_team}",
        "draw": "Match nul",
        "away": f"Victoire {away_team}",
    }

    prompt = MATCH_EXPLANATION_PROMPT.format(
        home_team=home_team,
        away_team=away_team,
        competition=competition,
        match_date=match_date,
        home_prob=round(prediction.home_win_prob * 100, 1),
        draw_prob=round(prediction.draw_prob * 100, 1),
        away_prob=round(prediction.away_win_prob * 100, 1),
        recommended_bet=recommended_map.get(prediction.recommended_bet, prediction.recommended_bet),
        confidence=round(prediction.confidence * 100, 1),
        key_stats=key_stats or "Non disponibles",
        home_form=home_form,
        away_form=away_form,
    )

    try:
        result = await client.analyze_json(
            prompt=prompt,
            system_prompt=SYSTEM_FOOTBALL_ANALYST,
        )

        return MatchExplanation(
            summary=result.get("summary", "Analyse non disponible"),
            key_factors=result.get("key_factors", []),
            risk_factors=result.get("risk_factors", []),
            betting_angle=result.get("betting_angle", ""),
        )

    except Exception as e:
        # Fallback if LLM fails
        return MatchExplanation(
            summary=f"Match entre {home_team} et {away_team}. Prediction: {recommended_map.get(prediction.recommended_bet)} avec {round(prediction.confidence * 100)}% de confiance.",
            key_factors=[
                f"Probabilite victoire domicile: {round(prediction.home_win_prob * 100)}%",
                f"Probabilite match nul: {round(prediction.draw_prob * 100)}%",
                f"Probabilite victoire exterieur: {round(prediction.away_win_prob * 100)}%",
            ],
            risk_factors=["Analyse LLM non disponible"],
            betting_angle="Suivre la prediction du modele statistique",
        )


async def generate_quick_summary(
    home_team: str,
    away_team: str,
    prediction: EnsemblePrediction,
) -> str:
    """
    Generate a quick one-line summary without LLM.

    Useful when LLM is rate-limited or for performance.
    """
    outcome_map = {
        "home": f"victoire de {home_team}",
        "draw": "match nul",
        "away": f"victoire de {away_team}",
    }

    outcome = outcome_map.get(prediction.recommended_bet, prediction.recommended_bet)
    confidence = round(prediction.confidence * 100)

    return f"Prediction: {outcome} ({confidence}% confiance)"
