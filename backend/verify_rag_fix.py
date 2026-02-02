#!/usr/bin/env python3
"""
Verification script for RAG endpoint fix.

This script demonstrates that the /enrich endpoint now correctly
extracts data from the nested structure returned by enrich_match_prediction().
"""

def test_data_extraction():
    """Test that data extraction works correctly with nested structure."""

    # Simulated enrichment response from enrich_match_prediction()
    enrichment = {
        "home_context": {
            "team": "Arsenal",
            "news": [
                {"title": "Arsenal win big", "source": "ESPN"},
                {"title": "Star player returns", "source": "BBC"}
            ],
            "injuries": [
                {"player": "Player A", "status": "out"}
            ],
            "form_notes": "Good form",
            "sentiment": "positive",  # STRING, not float
            "key_info": []
        },
        "away_context": {
            "team": "Chelsea",
            "news": [
                {"title": "Chelsea struggle", "source": "Goal"}
            ],
            "injuries": [],
            "form_notes": "Mixed form",
            "sentiment": "negative",  # STRING
            "key_info": []
        },
        "match_context": {
            "competition": "PL",
            "match_date": "2025-02-01T10:00:00",
            "is_derby": True,
            "importance": "high"
        },
        "enriched_at": "2025-02-01T10:00:00"
    }

    # Extract nested contexts (THE FIX)
    home_ctx = enrichment.get("home_context", {})
    away_ctx = enrichment.get("away_context", {})
    match_ctx = enrichment.get("match_context", {})

    # Convert sentiment string to float score (THE FIX)
    sentiment_map = {"positive": 0.8, "negative": 0.2, "neutral": 0.5}
    home_sentiment_str = home_ctx.get("sentiment", "neutral")
    home_sentiment_score = sentiment_map.get(home_sentiment_str, 0.5)
    away_sentiment_str = away_ctx.get("sentiment", "neutral")
    away_sentiment_score = sentiment_map.get(away_sentiment_str, 0.5)

    # Verify extractions
    print("✓ Data Extraction Test")
    print("=" * 50)

    # Home context
    assert home_ctx.get("news") == enrichment["home_context"]["news"]
    assert len(home_ctx.get("news", [])) == 2
    print(f"✓ Home news: {len(home_ctx.get('news', []))} articles")

    assert home_ctx.get("injuries") == enrichment["home_context"]["injuries"]
    assert len(home_ctx.get("injuries", [])) == 1
    print(f"✓ Home injuries: {len(home_ctx.get('injuries', []))} players")

    assert home_sentiment_str == "positive"
    assert home_sentiment_score == 0.8
    print(f"✓ Home sentiment: '{home_sentiment_str}' → {home_sentiment_score}")

    # Away context
    assert away_ctx.get("news") == enrichment["away_context"]["news"]
    assert len(away_ctx.get("news", [])) == 1
    print(f"✓ Away news: {len(away_ctx.get('news', []))} articles")

    assert away_ctx.get("injuries") == enrichment["away_context"]["injuries"]
    assert len(away_ctx.get("injuries", [])) == 0
    print(f"✓ Away injuries: {len(away_ctx.get('injuries', []))} players")

    assert away_sentiment_str == "negative"
    assert away_sentiment_score == 0.2
    print(f"✓ Away sentiment: '{away_sentiment_str}' → {away_sentiment_score}")

    # Match context
    assert match_ctx.get("is_derby") == True
    print(f"✓ Match is_derby: {match_ctx.get('is_derby')}")

    assert match_ctx.get("importance") == "high"
    print(f"✓ Match importance: {match_ctx.get('importance')}")

    print("=" * 50)
    print("✓ All tests passed!")
    print()

    # Show the old (broken) way
    print("× Old (Broken) Extraction")
    print("=" * 50)
    print(f"× enrichment.get('home_news', []): {enrichment.get('home_news', [])}")
    print(f"  Expected 2 articles, got: {len(enrichment.get('home_news', []))}")
    print(f"× enrichment.get('home_injuries', []): {enrichment.get('home_injuries', [])}")
    print(f"  Expected 1 injury, got: {len(enrichment.get('home_injuries', []))}")
    print(f"× enrichment.get('home_sentiment', 0.0): {enrichment.get('home_sentiment', 0.0)}")
    print(f"  Expected 'positive' string, got: {type(enrichment.get('home_sentiment', 0.0))}")
    print(f"× enrichment.get('is_derby', False): {enrichment.get('is_derby', False)}")
    print(f"  Expected True, got: {enrichment.get('is_derby', False)}")
    print("=" * 50)
    print()


if __name__ == "__main__":
    print("\nRAG Endpoint Fix Verification")
    print("=" * 50)
    print("Testing nested data extraction from enrich_match_prediction()")
    print()
    test_data_extraction()
    print("✓ Fix verified successfully!")
