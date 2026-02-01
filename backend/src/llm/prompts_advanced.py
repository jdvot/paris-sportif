"""Advanced LLM prompts for professional football match analysis.

These prompts leverage Groq's Llama 3.3 70B to provide sophisticated analysis
with chain-of-thought reasoning that complements statistical models with
contextual intelligence and expert judgment.
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
    weather_conditions: str = "",
    match_importance: str = "regular",
) -> str:
    """
    Generate a comprehensive match analysis prompt with chain-of-thought reasoning.

    Uses step-by-step analysis to provide professional betting predictions.

    Args:
        home_team: Home team name
        away_team: Away team name
        competition: Competition name
        home_current_form: Recent form summary (e.g., "3 wins, 1 draw, 1 loss")
        away_current_form: Recent form summary
        home_injuries: Injury information
        away_injuries: Injury information
        head_to_head: Historical matchup information
        weather_conditions: Weather/pitch conditions
        match_importance: Match importance level (regular/important/critical)

    Returns:
        Formatted prompt for LLM with chain-of-thought structure
    """
    return f"""You are a professional football analyst with 20+ years of experience in sports betting and match prediction.

MATCH ANALYSIS: {home_team} vs {away_team}
Competition: {competition}
Match Importance: {match_importance}

AVAILABLE DATA:
Recent Form - {home_team}: {home_current_form or "Not available"}
Recent Form - {away_team}: {away_current_form or "Not available"}
Injuries - {home_team}: {home_injuries or "None reported"}
Injuries - {away_team}: {away_injuries or "None reported"}
Head-to-Head: {head_to_head or "No historical data"}
Conditions: {weather_conditions or "Not specified"}

ANALYSIS APPROACH - Use chain-of-thought reasoning:
1. TEAM ASSESSMENT
   - Evaluate current team strength (attack, defense, midfield)
   - Compare recent form and momentum
   - Consider injury impact on available squad depth
   - Account for key player absences

2. CONTEXTUAL FACTORS
   - Head-to-head patterns (historical matchups)
   - Home/away advantage (historical record, travel fatigue)
   - Tactical compatibility (formation and style)
   - Motivation factors (title race, relegation fight, derby)
   - External factors (weather, pitch condition, fixture congestion)

3. PROBABILISTIC REASONING
   - Estimate base probabilities from form and strength
   - Apply injury impact adjustments (-0.3 to 0.0 range)
   - Apply contextual adjustments (head-to-head, motivation)
   - Apply environmental adjustments (weather, crowd)
   - Final probability normalization

4. CONFIDENCE ASSESSMENT
   - Data quality and completeness
   - Historical pattern reliability
   - Recent anomalies or unexpected changes
   - Overall model uncertainty

RESPONSE FORMAT - MANDATORY JSON ONLY (no text before/after):
{{
    "analysis_summary": {{
        "home_team_strength": "weak|below_average|average|above_average|strong",
        "away_team_strength": "weak|below_average|average|above_average|strong",
        "relative_strength": "home_advantage|balanced|away_advantage"
    }},
    "probability_assessment": {{
        "home_win_probability": 0.00,
        "draw_probability": 0.00,
        "away_win_probability": 0.00,
        "confidence_level": "low|medium|high|very_high"
    }},
    "impact_factors": {{
        "injury_impact_home": -0.30 to 0.00,
        "injury_impact_away": -0.30 to 0.00,
        "motivation_impact_home": -0.15 to 0.15,
        "motivation_impact_away": -0.15 to 0.15,
        "weather_impact": -0.10 to 0.10,
        "tactical_edge": -0.05 to 0.05
    }},
    "match_dynamics": {{
        "expected_goals_home": 0.5 to 3.5,
        "expected_goals_away": 0.5 to 3.5,
        "likely_score_range": "e.g., 1-1 to 2-1",
        "match_type": "open_game|defensive_battle|one_sided"
    }},
    "key_factors": [
        "Factor 1 with expected impact",
        "Factor 2 with expected impact",
        "Factor 3 with expected impact",
        "Factor 4 with expected impact"
    ],
    "risk_assessment": {{
        "main_risks": ["Risk 1", "Risk 2"],
        "upset_probability": 0.0 to 0.5,
        "data_quality": "high|medium|low"
    }},
    "recommendation": {{
        "primary_prediction": "home_win|draw|away_win",
        "confidence_percentage": 0 to 100,
        "best_bet": "1|X|2|1X|X2|12|recommended_angle",
        "reasoning": "Concise explanation of primary prediction"
    }}
}}

CRITICAL CONSTRAINTS:
- Probabilities must sum to exactly 1.0
- confidence_level must be one of the 4 specified options
- All numerical fields must be within specified ranges
- Provide only JSON, no additional text
- injury_impact values must be between -0.3 and 0.0
- All required fields must be present"""


def get_injury_impact_analysis_prompt(
    team_name: str,
    absent_players: list[str],
    team_strength: str = "medium",
    competition_importance: str = "regular",
    replacement_options: str = "",
) -> str:
    """
    Generate prompt for detailed injury impact analysis.

    Args:
        team_name: Team name
        absent_players: List of absent player names with positions
        team_strength: Team strength level (weak/medium/strong)
        competition_importance: Match importance (regular/important/critical)
        replacement_options: Available replacement players

    Returns:
        Formatted prompt for chain-of-thought injury analysis
    """
    players_str = ", ".join(absent_players) if absent_players else "None"

    return f"""Analyze the competitive impact of player absences on {team_name}.

TEAM CONTEXT:
Team: {team_name}
Overall Strength: {team_strength}
Match Importance: {competition_importance}

ABSENT PLAYERS:
{players_str}

REPLACEMENT OPTIONS:
{replacement_options or "Standard squad rotation"}

ANALYSIS FRAMEWORK:
1. PLAYER IMPACT ASSESSMENT
   - Evaluate each player's typical minutes and contribution
   - Consider position-specific scarcity
   - Assess replacement quality/depth

2. TACTICAL IMPACT
   - Formation flexibility with absences
   - Defensive stability changes
   - Attacking potency reduction
   - Midfield control impact

3. CUMULATIVE EFFECT
   - Multiple absences compound effect
   - Team chemistry disruption
   - Confidence/momentum impact
   - Training continuity effects

4. COMPETITIVE DISADVANTAGE
   - Quantify as adjustment factor
   - Consider match importance (critical matches: larger impact)
   - Account for team's squad depth

IMPACT SCORING:
- 0.0: No impact (minor players absent)
- -0.05: Small impact (1-2 squad players)
- -0.10: Moderate impact (key regular absent)
- -0.15: Significant impact (multiple starters/one star)
- -0.25: Major impact (several key players)
- -0.30: Critical impact (star player + multiple starters)

RESPONSE FORMAT - JSON ONLY:
{{
    "impact_assessment": {{
        "injury_impact_factor": -0.30 to 0.00,
        "severity_level": "minimal|light|moderate|significant|major|critical",
        "primary_concern": "player_name or position impacted",
        "replacement_quality": "weak|adequate|good|excellent"
    }},
    "player_analysis": [
        {{
            "player": "name",
            "position": "position",
            "importance": "backup|regular|key|star",
            "expected_minutes_lost": 0 to 100,
            "impact_rating": 0.0 to 1.0
        }}
    ],
    "tactical_implications": {{
        "formation_flexibility": "low|medium|high",
        "defense_vulnerability": "low|medium|high",
        "attack_reduction": 0.0 to 0.3,
        "midfield_control_loss": 0.0 to 0.3
    }},
    "confidence": 0.0 to 1.0,
    "reasoning": "Explanation of impact assessment"
}}"""


def get_form_analysis_prompt(
    team_name: str,
    recent_results: list[str],
    media_sentiment: str = "neutral",
    tactical_changes: str = "",
    key_player_form: str = "",
) -> str:
    """
    Generate prompt for team form and sentiment analysis with trends.

    Args:
        team_name: Team name
        recent_results: List of recent match results (e.g., ['W', 'W', 'D', 'L'])
        media_sentiment: Overall media sentiment (very_negative/negative/neutral/positive/very_positive)
        tactical_changes: Recent tactical changes
        key_player_form: Form of key players

    Returns:
        Formatted prompt for form analysis
    """
    results_str = " → ".join(recent_results) if recent_results else "No data"

    return f"""Analyze team form, momentum, and psychological state for {team_name}.

TEAM: {team_name}
Recent Results (last 5-10): {results_str}
Media Sentiment: {media_sentiment}
Tactical Changes: {tactical_changes or "None"}
Key Players Form: {key_player_form or "Not specified"}

FORM ANALYSIS FRAMEWORK:
1. PERFORMANCE TRENDS
   - Win/draw/loss pattern analysis
   - Goal scoring/conceding trends
   - Performance consistency
   - Recent trajectory (improving/declining/stable)

2. PSYCHOLOGICAL FACTORS
   - Team confidence level
   - Motivation indicators
   - Pressure/stress signs
   - Cohesion indicators

3. MOMENTUM ASSESSMENT
   - Winning streak or losing streak
   - Clean sheet consistency
   - High-pressure game responses
   - Recent comeback ability

4. EXTERNAL SIGNALS
   - Media perception and criticism
   - Coach comments and decisions
   - Player interviews/statements
   - Transfer/tactical changes

SENTIMENT ADJUSTMENT SCALE:
- +0.15: Exceptional form, very strong confidence, media very positive
- +0.10: Good form, confident team, media positive
- +0.05: Slight positive momentum, minor confidence boost
- 0.00: Neutral, balanced form, realistic expectations
- -0.05: Slight negative trend, minor doubt creeping in
- -0.10: Poor form, confidence dented, media concerned
- -0.15: Crisis mode, severe confidence loss, intense scrutiny

RESPONSE FORMAT - JSON ONLY:
{{
    "form_assessment": {{
        "recent_performance": "very_poor|poor|below_average|average|above_average|good|excellent",
        "trend": "deteriorating|stable|improving",
        "confidence_level": "very_low|low|medium|high|very_high"
    }},
    "momentum_analysis": {{
        "momentum_indicator": -0.15 to 0.15,
        "win_streak_status": "active|broken|none",
        "defensive_solidity": "weak|average|strong",
        "attack_effectiveness": "weak|average|strong"
    }},
    "sentiment_adjustment": -0.15 to 0.15,
    "key_observations": [
        "observation1",
        "observation2",
        "observation3"
    ],
    "confidence": 0.0 to 1.0,
    "reasoning": "Summary of form assessment"
}}"""


def get_tactical_matchup_prompt(
    home_team: str,
    away_team: str,
    home_formation: str = "",
    away_formation: str = "",
    home_style: str = "",
    away_style: str = "",
    head_to_head_tactics: str = "",
) -> str:
    """
    Generate prompt for detailed tactical analysis and matchup.

    Args:
        home_team: Home team name
        away_team: Away team name
        home_formation: Home team formation (e.g., "4-2-3-1")
        away_formation: Away team formation
        home_style: Home team's typical playing style
        away_style: Away team's typical playing style
        head_to_head_tactics: Historical tactical patterns

    Returns:
        Formatted prompt for tactical analysis
    """
    return f"""Analyze the tactical matchup and formation compatibility for {home_team} vs {away_team}.

FORMATIONS AND STYLES:
{home_team}: {home_formation or "Not specified"} - {home_style or "Not specified"}
{away_team}: {away_formation or "Not specified"} - {away_style or "Not specified"}

HISTORICAL TACTICS:
{head_to_head_tactics or "No specific patterns"}

TACTICAL ANALYSIS FRAMEWORK:
1. FORMATION MATCHUP
   - Numerical advantage in key areas (midfield, defense)
   - Line of symmetry advantages
   - Defensive coverage and vulnerabilities
   - Offensive width and penetration options

2. STYLE COMPATIBILITY
   - How does {home_team}'s style suit their formation?
   - How does {away_team} adapt away from home?
   - What tactical adjustments might occur?
   - Which team has tactical flexibility?

3. KEY MATCHUPS
   - Midfield battle (numerical/positional)
   - Wing play and fullback battles
   - Attacking structure vs defensive shape
   - Set-piece advantages/disadvantages

4. STRATEGIC IMPLICATIONS
   - Expected game flow and tempo
   - Which team controls the match?
   - Likely game situations (open game vs defensive)
   - Potential tactical pivots

TACTICAL EDGE SCALE:
- +0.05: Clear tactical advantage for {home_team}
- +0.03: Slight tactical advantage for {home_team}
- +0.01: Minor tactical advantage for {home_team}
- 0.00: Tactical balance, equally matched
- -0.01: Minor tactical advantage for {away_team}
- -0.03: Slight tactical advantage for {away_team}
- -0.05: Clear tactical advantage for {away_team}

RESPONSE FORMAT - JSON ONLY:
{{
    "formation_analysis": {{
        "home_formation": "{home_formation or 'Not specified'}",
        "away_formation": "{away_formation or 'Not specified'}",
        "formation_compatibility": "home_advantage|balanced|away_advantage"
    }},
    "tactical_edge": -0.05 to 0.05,
    "edge_reason": "Explanation of tactical advantage",
    "key_matchups": [
        "matchup1 with expected result",
        "matchup2 with expected result",
        "matchup3 with expected result"
    ],
    "vulnerable_areas": {{
        "home_team_weakness": "specific tactical vulnerability",
        "away_team_opportunity": "how away team can exploit"
    }},
    "game_dynamics": {{
        "expected_tempo": "slow|moderate|fast",
        "expected_intensity": "low|moderate|high",
        "likely_game_type": "open|balanced|defensive|one_sided"
    }},
    "confidence": 0.0 to 1.0,
    "reasoning": "Summary of tactical analysis"
}}"""


def get_head_to_head_analysis_prompt(
    home_team: str,
    away_team: str,
    h2h_history: str,
    recent_h2h: str = "",
) -> str:
    """
    Generate prompt for historical head-to-head analysis.

    Args:
        home_team: Home team name
        away_team: Away team name
        h2h_history: Overall head-to-head record
        recent_h2h: Recent head-to-head results

    Returns:
        Formatted prompt for H2H analysis
    """
    return f"""Analyze historical patterns in matches between {home_team} and {away_team}.

TEAMS: {home_team} vs {away_team}
Overall H2H Record: {h2h_history}
Recent H2H (last 5): {recent_h2h or "Not available"}

HEAD-TO-HEAD ANALYSIS:
1. HISTORICAL DOMINANCE
   - Overall win/loss/draw record
   - Home/away splits
   - Recent trend (who's winning now)
   - Statistical probability adjustments

2. PATTERN IDENTIFICATION
   - Typical match outcomes
   - Score ranges
   - Defensive patterns
   - Emotional/rivalry factors

3. RECENT FORM vs H2H
   - Has dominance changed?
   - Are patterns evolving?
   - Tactical adjustments visible?
   - Individual matchup changes

RESPONSE FORMAT - JSON ONLY:
{{
    "h2h_dominance": {{
        "overall_record": "X-Y-Z (wins-draws-losses for home)",
        "home_advantage": -0.1 to 0.1,
        "trend": "home_improving|balanced|away_improving",
        "reliability": "strong|moderate|weak"
    }},
    "pattern_analysis": {{
        "most_common_result": "1|X|2",
        "average_goals": 0.0 to 5.0,
        "pattern_strength": "strong|moderate|weak",
        "pattern_description": "description of typical matchup"
    }},
    "h2h_adjustment": -0.05 to 0.05,
    "confidence": 0.0 to 1.0,
    "reasoning": "Summary of H2H insights"
}}"""


def get_probability_refinement_prompt(
    home_win_prob: float,
    draw_prob: float,
    away_win_prob: float,
    model_confidence: float,
    analysis_summary: str = "",
) -> str:
    """
    Generate prompt for final probability refinement with expert adjustment.

    Args:
        home_win_prob: Initial home win probability
        draw_prob: Initial draw probability
        away_win_prob: Initial away win probability
        model_confidence: Model's confidence level
        analysis_summary: Summary of key findings

    Returns:
        Formatted prompt for probability adjustment
    """
    return f"""Refine these match probabilities using expert judgment and contextual factors.

INITIAL MODEL PROBABILITIES:
Home Win: {home_win_prob:.1%}
Draw: {draw_prob:.1%}
Away Win: {away_win_prob:.1%}
Model Confidence: {model_confidence:.0%}

KEY FINDINGS SUMMARY:
{analysis_summary or "Use model probabilities as baseline"}

REFINEMENT FRAMEWORK:
1. VALIDATE PROBABILITIES
   - Do they align with expert assessment?
   - Are there anomalies or surprises?
   - Is model confidence justified?

2. CONSIDER HUMAN FACTORS
   - Team dynamics and cohesion
   - Psychological readiness
   - Leadership and experience
   - Recent unexpected performances

3. MARKET INEFFICIENCY
   - Are odds justified?
   - Is there value (undervalued outcomes)?
   - Does the market misjudge either team?

4. FINAL ADJUSTMENT
   - Adjustments should be conservative
   - Probabilities must sum to 1.0
   - Changes should be justified
   - Confidence must be realistic

RESPONSE FORMAT - JSON ONLY:
{{
    "refined_probabilities": {{
        "home_win": 0.00 to 1.00,
        "draw": 0.00 to 1.00,
        "away_win": 0.00 to 1.00,
        "total": "must equal 1.00"
    }},
    "adjustment_justification": {{
        "major_adjustments": ["adjustment1", "adjustment2"],
        "reason": "Why probabilities changed from model",
        "confidence_in_adjustment": 0.0 to 1.0
    }},
    "betting_implication": {{
        "value_outcome": "1|X|2|none",
        "expected_odds_alignment": "undervalued|fairly_valued|overvalued"
    }},
    "final_recommendation": {{
        "primary_prediction": "1|X|2",
        "confidence": 0 to 100,
        "supporting_factors": ["factor1", "factor2"]
    }},
    "reasoning": "Concise summary of refinement"
}}"""


def get_weather_impact_prompt(
    home_team: str,
    away_team: str,
    temperature: str = "",
    wind: str = "",
    rain: str = "",
    pitch_condition: str = "",
) -> str:
    """
    Generate prompt for weather and environmental impact analysis.

    Args:
        home_team: Home team name
        away_team: Away team name
        temperature: Temperature information
        wind: Wind speed and direction
        rain: Rain/precipitation forecast
        pitch_condition: Pitch condition description

    Returns:
        Formatted prompt for weather analysis
    """
    return f"""Analyze how weather and pitch conditions affect {home_team} vs {away_team}.

ENVIRONMENTAL CONDITIONS:
Temperature: {temperature or "Not specified"}
Wind: {wind or "Not specified"}
Rain: {rain or "Not specified"}
Pitch Condition: {pitch_condition or "Normal"}

TEAM CHARACTERISTICS:
{home_team}: Typical play style, adaptation history
{away_team}: Typical play style, adaptation history

WEATHER IMPACT ANALYSIS:
1. DIRECT EFFECTS
   - Movement and ball control
   - Passing accuracy
   - Shooting power and accuracy
   - Defensive solidity

2. STYLE ADAPTATION
   - Which team plays better in conditions?
   - Formation adjustments needed
   - Tactical flexibility
   - Set-piece vulnerability

3. HOME ADVANTAGE
   - Familiarity with pitch/conditions
   - Mental advantage in adversity
   - Playing style suitability

RESPONSE FORMAT - JSON ONLY:
{{
    "weather_impact": {{
        "home_team_impact": -0.10 to 0.10,
        "away_team_impact": -0.10 to 0.10,
        "overall_impact": "neutral|favors_home|favors_away"
    }},
    "tactical_implications": {{
        "expected_style_change": "description of how game might change",
        "set_piece_vulnerability": "increased|unchanged|decreased",
        "possession_changes": "expected adjustment in possession patterns"
    }},
    "confidence": 0.0 to 1.0,
    "reasoning": "Summary of weather impact"
}}"""
