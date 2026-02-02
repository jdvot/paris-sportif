# RAG `/enrich` Endpoint Fix

## Summary
Fixed the `/enrich` endpoint in `/backend/src/api/routes/rag.py` to properly extract data from the nested structure returned by `enrich_match_prediction()`.

## Problem

The endpoint was attempting to extract fields from the top-level of the enrichment response:
```python
enrichment.get("home_news", [])
enrichment.get("home_injuries", [])
enrichment.get("home_sentiment", 0.0)
```

However, the actual response from `enrich_match_prediction()` has a nested structure:
```python
{
    "home_context": {
        "news": [...],
        "injuries": [...],
        "sentiment": "positive",  # STRING, not float
        ...
    },
    "away_context": {
        "news": [...],
        "injuries": [...],
        "sentiment": "negative",
        ...
    },
    "match_context": {
        "is_derby": bool,
        "importance": str,
        ...
    }
}
```

## Solution

### 1. Extract Nested Contexts
Updated the code to properly extract the three nested context objects:
```python
home_ctx = enrichment.get("home_context", {})
away_ctx = enrichment.get("away_context", {})
match_ctx = enrichment.get("match_context", {})
```

### 2. Convert Sentiment String to Float
Added sentiment mapping to convert string values to float scores:
```python
sentiment_map = {"positive": 0.8, "negative": 0.2, "neutral": 0.5}
home_sentiment_str = home_ctx.get("sentiment", "neutral")
home_sentiment_score = sentiment_map.get(home_sentiment_str, 0.5)
```

### 3. Use Correct Field Names
Updated all field extractions to use the correct nested field names:
```python
home_context=TeamContext(
    team_name=home_team,
    recent_news=home_ctx.get("news", []),        # was: enrichment.get("home_news")
    injuries=home_ctx.get("injuries", []),        # was: enrichment.get("home_injuries")
    sentiment_score=home_sentiment_score,         # converted from string
    sentiment_label=home_sentiment_str,           # now string as expected
)
```

## Changes Made

**File**: `/backend/src/api/routes/rag.py`

**Lines modified**: 98-143

### Before
```python
# Build response
return MatchContext(
    home_team=home_team,
    away_team=away_team,
    competition=competition,
    match_date=parsed_date,
    home_context=TeamContext(
        team_name=home_team,
        recent_news=enrichment.get("home_news", []),  # WRONG
        injuries=enrichment.get("home_injuries", []),  # WRONG
        sentiment_score=enrichment.get("home_sentiment", 0.0),  # WRONG
        sentiment_label=_get_sentiment_label(enrichment.get("home_sentiment", 0.0)),
    ),
    # ... similar issues for away_context
    is_derby=enrichment.get("is_derby", False),  # WRONG
    match_importance=enrichment.get("importance", "normal"),  # WRONG
)
```

### After
```python
# Extract nested contexts
home_ctx = enrichment.get("home_context", {})
away_ctx = enrichment.get("away_context", {})
match_ctx = enrichment.get("match_context", {})

# Convert sentiment string to float score
sentiment_map = {"positive": 0.8, "negative": 0.2, "neutral": 0.5}
home_sentiment_str = home_ctx.get("sentiment", "neutral")
home_sentiment_score = sentiment_map.get(home_sentiment_str, 0.5)
away_sentiment_str = away_ctx.get("sentiment", "neutral")
away_sentiment_score = sentiment_map.get(away_sentiment_str, 0.5)

# Build response
return MatchContext(
    home_team=home_team,
    away_team=away_team,
    competition=competition,
    match_date=parsed_date,
    home_context=TeamContext(
        team_name=home_team,
        recent_news=home_ctx.get("news", []),      # CORRECT
        injuries=home_ctx.get("injuries", []),      # CORRECT
        sentiment_score=home_sentiment_score,       # CORRECT
        sentiment_label=home_sentiment_str,         # CORRECT
    ),
    away_context=TeamContext(
        team_name=away_team,
        recent_news=away_ctx.get("news", []),      # CORRECT
        injuries=away_ctx.get("injuries", []),      # CORRECT
        sentiment_score=away_sentiment_score,       # CORRECT
        sentiment_label=away_sentiment_str,         # CORRECT
    ),
    is_derby=match_ctx.get("is_derby", False),     # CORRECT
    match_importance=match_ctx.get("importance", "normal"),  # CORRECT
    combined_analysis=None,
    enriched_at=datetime.now(),
    sources_used=["groq_llm", "public_data"],
)
```

## Testing

### Manual Testing
The endpoint can be tested with:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/enrich?home_team=Arsenal&away_team=Chelsea&competition=PL"
```

Expected response structure:
```json
{
  "home_team": "Arsenal",
  "away_team": "Chelsea",
  "competition": "PL",
  "match_date": "2025-02-01T...",
  "home_context": {
    "team_name": "Arsenal",
    "recent_news": [],
    "injuries": [],
    "sentiment_score": 0.5,
    "sentiment_label": "neutral"
  },
  "away_context": {
    "team_name": "Chelsea",
    "recent_news": [],
    "injuries": [],
    "sentiment_score": 0.5,
    "sentiment_label": "neutral"
  },
  "is_derby": true,
  "match_importance": "normal",
  "combined_analysis": null,
  "enriched_at": "2025-02-01T...",
  "sources_used": ["groq_llm", "public_data"]
}
```

## Impact

- **Fixed**: Data extraction from nested `enrich_match_prediction()` response
- **Fixed**: Sentiment type conversion (string → float)
- **Fixed**: Field name mappings (home_news → news in home_context)
- **Improved**: Code clarity with explicit context extraction
- **Maintained**: All existing API contract (response models unchanged)

## Additional Notes

1. The `combined_analysis` field is set to `None` in the base enrichment because it's not generated until the `/analyze` endpoint is called with `generate_enriched_analysis()`.

2. The `_get_sentiment_label()` function was updated to reflect the new score ranges (0.0-1.0 instead of -1.0 to 1.0) but is no longer used in the main flow since sentiment is now received as a string.

3. The sentiment mapping values are:
   - "positive" → 0.8
   - "negative" → 0.2
   - "neutral" → 0.5

## Validation

Syntax validation passed:
```bash
cd /Users/admin/paris-sportif/backend
python3 -m py_compile src/api/routes/rag.py
# ✓ No errors
```
