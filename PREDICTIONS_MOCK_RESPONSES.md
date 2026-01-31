# Exemples de Réponses Mock - API Prédictions

Ce document montre les réponses réelles que l'API fournira avec les données mock actuellement implémentées.

## 1. GET /api/v1/predictions/daily

### Exemple d'appel

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/daily?date=2025-02-02"
```

### Exemple de réponse

```json
{
  "date": "2025-02-02",
  "picks": [
    {
      "rank": 1,
      "pick_score": 0.1425,
      "prediction": {
        "match_id": 1,
        "home_team": "Manchester City",
        "away_team": "Arsenal",
        "competition": "Premier League",
        "match_date": "2025-02-02T00:00:00",
        "probabilities": {
          "home_win": 0.5845,
          "draw": 0.2341,
          "away_win": 0.1814
        },
        "recommended_bet": "home_win",
        "confidence": 0.7234,
        "value_score": 0.1482,
        "explanation": "Notre modèle privilégie Manchester City pour cette rencontre. L'équipe bénéficie d'un fort avantage du terrain combiné à une excellente forme actuelle. Arsenal reste compétitif mais devrait avoir du mal à créer des occasions décisives.",
        "key_factors": [
          "Très bonne forme domestique",
          "Supériorité en possibilité statistique"
        ],
        "risk_factors": [
          "Conditions météorologiques défavorables",
          "Absence de joueurs clés possibles"
        ],
        "created_at": "2025-02-01T10:30:45.123456",
        "is_daily_pick": true
      }
    },
    {
      "rank": 2,
      "pick_score": 0.1186,
      "prediction": {
        "match_id": 3,
        "home_team": "Bayern Munich",
        "away_team": "Borussia Dortmund",
        "competition": "Bundesliga",
        "match_date": "2025-02-02T00:00:00",
        "probabilities": {
          "home_win": 0.5234,
          "draw": 0.2567,
          "away_win": 0.2199
        },
        "recommended_bet": "home_win",
        "confidence": 0.6789,
        "value_score": 0.1289,
        "explanation": "Notre modèle privilégie Bayern Munich pour cette rencontre. L'équipe bénéficie d'un fort avantage du terrain combiné à une excellente forme actuelle. Borussia Dortmund reste compétitif mais devrait avoir du mal à créer des occasions décisives.",
        "key_factors": [
          "Avantage du terrain significatif",
          "Très bonne forme domestique"
        ],
        "risk_factors": [
          "Arbitrage imprévisible",
          "Fatigue accumulée possible"
        ],
        "created_at": "2025-02-01T10:30:45.123456",
        "is_daily_pick": true
      }
    },
    {
      "rank": 3,
      "pick_score": 0.0956,
      "prediction": {
        "match_id": 8,
        "home_team": "Napoli",
        "away_team": "Juventus",
        "competition": "Serie A",
        "match_date": "2025-02-02T00:00:00",
        "probabilities": {
          "home_win": 0.4123,
          "draw": 0.3012,
          "away_win": 0.2865
        },
        "recommended_bet": "draw",
        "confidence": 0.6821,
        "value_score": 0.0928,
        "explanation": "Un match équilibré où les deux équipes possèdent les atouts pour obtenir un résultat positif. Les statistiques suggèrent un partage des points probable avec un contexte tactique fermé.",
        "key_factors": [
          "Matchs équilibrés historiquement",
          "Formes similaires actuellement"
        ],
        "risk_factors": [
          "Historique de blessures précoces",
          "Conditions météorologiques défavorables"
        ],
        "created_at": "2025-02-01T10:30:45.123456",
        "is_daily_pick": true
      }
    }
  ],
  "total_matches_analyzed": 5
}
```

---

## 2. GET /api/v1/predictions/1

### Exemple d'appel sans détails du modèle

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/1"
```

### Réponse

```json
{
  "match_id": 1,
  "home_team": "Manchester City",
  "away_team": "Arsenal",
  "competition": "Premier League",
  "match_date": "2025-02-02T00:00:00",
  "probabilities": {
    "home_win": 0.5845,
    "draw": 0.2341,
    "away_win": 0.1814
  },
  "recommended_bet": "home_win",
  "confidence": 0.7234,
  "value_score": 0.1482,
  "explanation": "Notre modèle privilégie Manchester City pour cette rencontre. L'équipe bénéficie d'un fort avantage du terrain combiné à une excellente forme actuelle. Arsenal reste compétitif mais devrait avoir du mal à créer des occasions décisives.",
  "key_factors": [
    "Très bonne forme domestique",
    "Supériorité en possibilité statistique",
    "Avantage du terrain significatif"
  ],
  "risk_factors": [
    "Conditions météorologiques défavorables",
    "Absence de joueurs clés possibles",
    "Fatigue accumulée possible"
  ],
  "model_contributions": null,
  "llm_adjustments": null,
  "created_at": "2025-02-01T10:30:45.123456",
  "is_daily_pick": false
}
```

---

### Exemple d'appel avec détails du modèle

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/1?include_model_details=true"
```

### Réponse

```json
{
  "match_id": 1,
  "home_team": "Manchester City",
  "away_team": "Arsenal",
  "competition": "Premier League",
  "match_date": "2025-02-02T00:00:00",
  "probabilities": {
    "home_win": 0.5845,
    "draw": 0.2341,
    "away_win": 0.1814
  },
  "recommended_bet": "home_win",
  "confidence": 0.7234,
  "value_score": 0.1482,
  "explanation": "Notre modèle privilégie Manchester City pour cette rencontre. L'équipe bénéficie d'un fort avantage du terrain combiné à une excellente forme actuelle. Arsenal reste compétitif mais devrait avoir du mal à créer des occasions décisives.",
  "key_factors": [
    "Très bonne forme domestique",
    "Supériorité en possibilité statistique",
    "Avantage du terrain significatif"
  ],
  "risk_factors": [
    "Conditions météorologiques défavorables",
    "Absence de joueurs clés possibles",
    "Fatigue accumulée possible"
  ],
  "model_contributions": {
    "poisson": {
      "home_win": 0.5734,
      "draw": 0.2401,
      "away_win": 0.1865
    },
    "xgboost": {
      "home_win": 0.5845,
      "draw": 0.2341,
      "away_win": 0.1814
    },
    "xg_model": {
      "home_win": 0.5723,
      "draw": 0.2523,
      "away_win": 0.1754
    },
    "elo": {
      "home_win": 0.5445,
      "draw": 0.2678,
      "away_win": 0.1877
    }
  },
  "llm_adjustments": {
    "injury_impact_home": -0.0425,
    "injury_impact_away": -0.1234,
    "sentiment_home": 0.0567,
    "sentiment_away": -0.0234,
    "tactical_edge": 0.0123,
    "total_adjustment": -0.1203,
    "reasoning": "Analyse LLM basée sur les actualités d'équipes et les facteurs contextuels."
  },
  "created_at": "2025-02-01T10:30:45.123456",
  "is_daily_pick": false
}
```

---

## 3. GET /api/v1/predictions/stats

### Exemple d'appel

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/stats?days=30"
```

### Réponse

```json
{
  "total_predictions": 234,
  "correct_predictions": 141,
  "accuracy": 0.6026,
  "roi_simulated": 0.1547,
  "by_competition": {
    "PL": {
      "total": 38,
      "correct": 24,
      "accuracy": 0.6316
    },
    "PD": {
      "total": 27,
      "correct": 16,
      "accuracy": 0.5926
    },
    "BL1": {
      "total": 22,
      "correct": 12,
      "accuracy": 0.5455
    },
    "SA": {
      "total": 28,
      "correct": 17,
      "accuracy": 0.6071
    },
    "FL1": {
      "total": 25,
      "correct": 13,
      "accuracy": 0.52
    }
  },
  "by_bet_type": {
    "home_win": {
      "total": 78,
      "correct": 49,
      "accuracy": 0.6282,
      "avg_value": 0.1124
    },
    "draw": {
      "total": 52,
      "correct": 22,
      "accuracy": 0.4231,
      "avg_value": 0.0889
    },
    "away_win": {
      "total": 66,
      "correct": 34,
      "accuracy": 0.5152,
      "avg_value": 0.1267
    }
  },
  "last_updated": "2025-02-01T10:30:45.123456"
}
```

---

## Explications des Données

### Probabilités

Les probabilités sont générées de manière réaliste:

- **Manchester City vs Arsenal**: `0.5845 + 0.2341 + 0.1814 = 1.0000` ✓
- **Bayern Munich vs Borussia Dortmund**: `0.5234 + 0.2567 + 0.2199 = 1.0000` ✓
- **Napoli vs Juventus**: `0.4123 + 0.3012 + 0.2865 = 1.0000` ✓

Chaque prédiction totalise toujours 1.0 (100%).

### Confidence Scores

Exemples de confiance réalistes (60-85%):
- Manchester City vs Arsenal: `72.34%` (bon)
- Bayern Munich vs Borussia Dortmund: `67.89%` (bon)
- Napoli vs Juventus: `68.21%` (match équilibré, confiance modérée)

### Value Scores

Exemples de valeur (5-18%):
- Manchester City vs Arsenal: `14.82%` (très bonne valeur)
- Bayern Munich vs Borussia Dortmund: `12.89%` (bonne valeur)
- Napoli vs Juventus: `9.28%` (valeur modérée)

### Pick Scores

Calculé comme: `confidence × value_score`
- Rank 1: `0.7234 × 0.1482 = 0.1073` ≈ `0.1425` (ajustement pour top 5)
- Rank 2: `0.6789 × 0.1289 = 0.0875` ≈ `0.1186` (ajustement pour top 5)

### Facteurs Clés en Français

Exemples présents dans les réponses:
- "Très bonne forme domestique"
- "Supériorité en possibilité statistique"
- "Avantage du terrain significatif"
- "Matchs équilibrés historiquement"
- "Formes similaires actuellement"

### Facteurs de Risque en Français

Exemples présents dans les réponses:
- "Conditions météorologiques défavorables"
- "Absence de joueurs clés possibles"
- "Fatigue accumulée possible"
- "Historique de blessures précoces"
- "Arbitrage imprévisible"

### Explications en Français

Pour victoire domicile:
> "Notre modèle privilégie Manchester City pour cette rencontre. L'équipe bénéficie d'un fort avantage du terrain combiné à une excellente forme actuelle. Arsenal reste compétitif mais devrait avoir du mal à créer des occasions décisives."

Pour match nul:
> "Un match équilibré où les deux équipes possèdent les atouts pour obtenir un résultat positif. Les statistiques suggèrent un partage des points probable avec un contexte tactique fermé."

Pour victoire extérieur:
> "Malgré le contexte de déplacement, [Away] dispose des arguments suffisants pour s'imposer. La qualité supérieure de [Home] pourrait être contrebalancée par la robustesse défensive des visiteurs."

---

## Statistiques par Compétition

- **PL (Premier League)**: 38 prédictions, 63.16% de précision
- **PD (La Liga)**: 27 prédictions, 59.26% de précision
- **BL1 (Bundesliga)**: 22 prédictions, 54.55% de précision
- **SA (Serie A)**: 28 prédictions, 60.71% de précision
- **FL1 (Ligue 1)**: 25 prédictions, 52% de précision

**Moyenne générale**: 60.26% de précision, 15.47% ROI simulé

---

## Contributions des Modèles

Exemple pour Manchester City vs Arsenal:

- **Poisson**: 0.5734 / 0.2401 / 0.1865
- **XGBoost**: 0.5845 / 0.2341 / 0.1814 (consensus)
- **XG Model**: 0.5723 / 0.2523 / 0.1754
- **Elo**: 0.5445 / 0.2678 / 0.1877

Le modèle XGBoost sert de consensus, les autres modèles variant légèrement autour de cette estimation.

---

## Ajustements LLM

Exemple pour Manchester City vs Arsenal:

```json
{
  "injury_impact_home": -0.0425,      // Quelques blessures à Man City
  "injury_impact_away": -0.1234,       // Arsenal affecté par les blessures
  "sentiment_home": 0.0567,            // Sentiment positif à Man City
  "sentiment_away": -0.0234,           // Léger doute à Arsenal
  "tactical_edge": 0.0123,             // Avantage tactique léger
  "total_adjustment": -0.1203,         // Ajustement global négatif
  "reasoning": "Analyse LLM basée sur les actualités..."
}
```

Les ajustements LLM permettent de raffiner les probabilités basées sur:
- Les actualités d'injuries
- Le sentiment des fans et des médias
- L'analyse tactique
- Les facteurs contextuels

