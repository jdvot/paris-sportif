#!/usr/bin/env python3
"""Script to train ML models on HuggingFace using match data from Supabase."""

import json
import os
import sys

import httpx

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tbzbwxbhuonnglvqfdjr.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
HF_SPACE_URL = os.getenv("HF_SPACE_URL", "https://jdevot244-paris-sportif.hf.space")


def fetch_training_data() -> list[dict]:
    """Fetch training data from Supabase."""
    print(f"Fetching training data from Supabase...")

    # Use REST API to fetch matches with team stats
    url = f"{SUPABASE_URL}/rest/v1/rpc/get_training_matches"

    # Alternative: direct query
    url = f"{SUPABASE_URL}/rest/v1/matches"
    params = {
        "select": "home_score,away_score,home_team:teams!matches_home_team_id_fkey(avg_goals_scored_home,avg_goals_conceded_home,elo_rating),away_team:teams!matches_away_team_id_fkey(avg_goals_scored_away,avg_goals_conceded_away,elo_rating)",
        "status": "eq.FINISHED",
        "home_score": "not.is.null",
        "order": "match_date.desc",
        "limit": "1200"
    }

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

    response = httpx.get(url, params=params, headers=headers, timeout=60.0)
    response.raise_for_status()

    rows = response.json()
    print(f"Fetched {len(rows)} matches")

    # Transform to training format
    training_data = []
    for row in rows:
        home_team = row.get("home_team") or {}
        away_team = row.get("away_team") or {}

        training_data.append({
            "home_attack": float(home_team.get("avg_goals_scored_home") or 1.0),
            "home_defense": float(home_team.get("avg_goals_conceded_home") or 1.0),
            "away_attack": float(away_team.get("avg_goals_scored_away") or 1.0),
            "away_defense": float(away_team.get("avg_goals_conceded_away") or 1.0),
            "home_elo": float(home_team.get("elo_rating") or 1500),
            "away_elo": float(away_team.get("elo_rating") or 1500),
            "home_form": 0.5,
            "away_form": 0.5,
            "home_rest_days": 7.0,
            "away_rest_days": 7.0,
            "home_fixture_congestion": 0.0,
            "away_fixture_congestion": 0.0,
            "home_score": row.get("home_score"),
            "away_score": row.get("away_score"),
        })

    return training_data


def train_models(training_data: list[dict]) -> dict:
    """Send training data to HuggingFace for training."""
    print(f"Sending {len(training_data)} matches to HuggingFace for training...")

    response = httpx.post(
        f"{HF_SPACE_URL}/train",
        json={"matches": training_data},
        timeout=300.0,  # 5 min timeout
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Training successful!")
        print(f"   Samples: {result.get('training_samples')}")
        print(f"   XGBoost accuracy: {result.get('accuracy_xgboost'):.4f}")
        print(f"   Random Forest accuracy: {result.get('accuracy_random_forest'):.4f}")
        return result
    else:
        print(f"❌ Training failed: {response.status_code}")
        print(response.text)
        sys.exit(1)


def main():
    """Main function."""
    # Load training data from stdin or file if provided
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            training_data = json.load(f)
    else:
        # Try to fetch from Supabase (requires SUPABASE_SERVICE_KEY)
        if not SUPABASE_KEY:
            print("Error: SUPABASE_SERVICE_KEY not set")
            print("Usage: python train_ml_models.py <training_data.json>")
            print("   or: SUPABASE_SERVICE_KEY=xxx python train_ml_models.py")
            sys.exit(1)
        training_data = fetch_training_data()

    if len(training_data) < 50:
        print(f"Error: Not enough training data ({len(training_data)} matches)")
        sys.exit(1)

    train_models(training_data)


if __name__ == "__main__":
    main()
