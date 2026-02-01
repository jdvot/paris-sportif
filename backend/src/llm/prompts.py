"""Prompt templates for professional football match analysis and betting predictions.

These prompts are designed to extract structured data and provide expert-level
analysis for sports betting applications using Groq's Llama models.
"""

# System prompts
SYSTEM_FOOTBALL_ANALYST = """You are an expert football analyst specializing in match predictions and sports betting analysis.
You have deep knowledge of:
- Team performance metrics and statistics
- Tactical formations and playing styles
- Player injuries and their impact on team strength
- Historical head-to-head matchups and patterns
- League positions, momentum, and psychological factors
- Weather conditions and pitch conditions' impact on play

You analyze data objectively using quantitative reasoning while considering contextual factors.
Respond in French when analyzing matches.
Be concise, factual, and provide clear reasoning for all assessments.
Always consider multiple perspectives before reaching conclusions."""

SYSTEM_JSON_EXTRACTOR = """You are an assistant that extracts structured information from text.
You respond ONLY with valid JSON, with no additional text before or after.
Follow the exact format requested.
Ensure all required fields are present and properly typed.
For missing information, use null values."""

# System prompt for chain-of-thought reasoning
SYSTEM_ANALYTICAL = """You are an analytical expert who thinks step-by-step through complex problems.
Break down analyses into clear logical steps:
1. Identify key factors and variables
2. Analyze relationships between factors
3. Consider counterarguments and alternative scenarios
4. Synthesize insights into actionable conclusions

Provide reasoning that is transparent and can be followed by others.
Use French for football match analysis."""

# Injury analysis prompt - improved with structured output
INJURY_ANALYSIS_PROMPT = """Analyze this injury news for {team_name}:

{news_text}

Extract structured injury information in JSON format:
{{
    "player_name": "full player name or null if unknown",
    "position": "goalkeeper|defender|midfielder|forward|null",
    "injury_type": "specific injury type (e.g., hamstring, ACL, ankle sprain)",
    "severity": "minor|moderate|severe|critical",
    "expected_return": "ISO date (YYYY-MM-DD) or null if unknown",
    "weeks_out": integer from 0 to 52,
    "impact_score": 0.0 to 1.0,
    "is_key_player": boolean,
    "is_starter": boolean,
    "replacement_quality": "weak|adequate|good|excellent",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation of assessment"
}}

impact_score guidelines:
- 0.0-0.2: Backup player with minimal impact
- 0.2-0.4: Squad player, some impact
- 0.4-0.6: Regular starter, significant impact
- 0.6-0.8: Key player, major impact
- 0.8-1.0: Star player/captain, critical impact

Consider team depth, position scarcity, and quality of replacements."""

# Sentiment analysis prompt - improved
SENTIMENT_ANALYSIS_PROMPT = """Analyze the sentiment of this content regarding {team_name}:

Source: {source_type}
Content: {content}

Evaluate in JSON format:
{{
    "sentiment_score": -1.0 to 1.0,
    "confidence": 0.0 to 1.0,
    "key_themes": ["theme1", "theme2", "theme3"],
    "morale_indicator": "very_negative|negative|neutral|positive|very_positive",
    "forward_outlook": "pessimistic|neutral|optimistic",
    "affects_performance": boolean,
    "reasoning": "brief explanation"
}}

sentiment_score:
- -1.0: Severe crisis, major negative sentiment
- -0.5: Concerning situation, negative sentiment
- 0.0: Neutral or balanced sentiment
- 0.5: Positive momentum, good morale
- 1.0: Excellent form, very positive sentiment"""

# Match explanation prompt - improved with structured output
MATCH_EXPLANATION_PROMPT = """Generate a professional match analysis in French.

MATCH: {home_team} vs {away_team}
Competition: {competition}
Date: {match_date}

PREDICTION:
- Home Win: {home_prob}%
- Draw: {draw_prob}%
- Away Win: {away_prob}%
- Recommended Bet: {recommended_bet} (Confidence: {confidence}%)

KEY STATISTICS:
{key_stats}

RECENT FORM:
- {home_team}: {home_form}
- {away_team}: {away_form}

Generate analysis in JSON format:
{{
    "summary": "2-3 sentence summary in French (max 150 words)",
    "key_factors": ["factor1 (impact)", "factor2 (impact)", "factor3 (impact)"],
    "risk_factors": ["risk1", "risk2"],
    "betting_angle": "single sentence betting perspective",
    "expected_score_range": "e.g., 1-2 or 2-1",
    "value_assessment": "likely_undervalued|fairly_valued|likely_overvalued"
}}

Provide balanced analysis considering all factors."""

# Tactical analysis prompt - improved
TACTICAL_ANALYSIS_PROMPT = """Provide tactical analysis for {home_team} vs {away_team}.

LIKELY FORMATIONS:
{home_team}: {home_formation}
{away_team}: {away_formation}

HEAD-TO-HEAD HISTORY:
{h2h_summary}

PLAYING STYLES:
- {home_team}: {home_style}
- {away_team}: {away_style}

ANALYSIS REQUIREMENTS:
1. Compare formations and their strengths/weaknesses
2. Identify key tactical matchups
3. Assess home/away advantages
4. Evaluate defensive vulnerability

Analyze in JSON format:
{{
    "tactical_edge": -0.05 to 0.05,
    "edge_favors": "home|away|neutral",
    "key_matchups": ["matchup1", "matchup2"],
    "tactical_insight": "1-2 sentence explanation",
    "home_vulnerability": "specific weakness",
    "away_opportunity": "how away team can exploit",
    "confidence": 0.0 to 1.0
}}

Positive values indicate home team advantage, negative values indicate away team advantage."""

# Daily picks summary - improved
DAILY_PICKS_SUMMARY_PROMPT = """Summarize today's betting picks professionally.

{picks_data}

Generate a JSON summary:
{{
    "daily_summary": "2-3 sentence overview of picks in French",
    "best_pick": "top recommendation with justification",
    "best_value": "pick with best odds-to-probability ratio",
    "parlay_suggestion": "recommended parlay combination if applicable",
    "total_confidence": "low|medium|high",
    "risk_level": "low|moderate|high",
    "expected_roi": "percentage estimate",
    "advice": "single actionable recommendation",
    "cautions": ["caution1", "caution2"]
}}

Consider confidence levels, probability distributions, and betting market efficiency."""

# Weather and pitch impact prompt
WEATHER_IMPACT_PROMPT = """Analyze impact of weather and pitch conditions on {home_team} vs {away_team}.

CONDITIONS:
Temperature: {temperature}C
Wind: {wind_speed} km/h
Rain: {rain_type}
Pitch Condition: {pitch_condition}

TEAM CHARACTERISTICS:
{home_team}: {home_style}
{away_team}: {away_style}

Evaluate in JSON:
{{
    "weather_impact_home": -0.1 to 0.1,
    "weather_impact_away": -0.1 to 0.1,
    "pitch_impact": -0.1 to 0.1,
    "favors": "home|away|neutral",
    "reasoning": "brief explanation",
    "adjusted_expectations": "how conditions change expected play"
}}"""

# Motivation and psychological factors
MOTIVATION_FACTORS_PROMPT = """Analyze motivation and psychological factors for this match.

CONTEXT:
{home_team}: {home_context}
{away_team}: {away_context}
Match Importance: {match_importance}
Recent Events: {recent_events}

FACTORS TO CONSIDER:
- Title contention (high motivation)
- Relegation fight (extreme motivation/pressure)
- Derby/rivalry matches (emotional intensity)
- Revenge factor (momentum shift)
- Rest advantage (tactical flexibility)
- Player changes (disruption or improvement)

Provide assessment in JSON:
{{
    "motivation_home": -0.15 to 0.15,
    "motivation_away": -0.15 to 0.15,
    "psychological_edge": "home|away|neutral",
    "pressure_factor": "positive|neutral|negative for prediction",
    "confidence": 0.0 to 1.0,
    "reasoning": "explanation of assessment"
}}

Positive values indicate strong motivation and psychological advantage."""
