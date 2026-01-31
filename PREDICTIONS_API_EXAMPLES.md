# API Prédictions - Exemples d'Utilisation

## Vue d'ensemble

L'API Prédictions fournit des prédictions réalistes et basées sur des données pour les matchs de football européens. Les prédictions incluent des probabilités, des scores de confiance et de valeur, ainsi que des explications détaillées en français.

## Endpoints Implémentés

### 1. GET /api/v1/predictions/daily

Retourne les 5 meilleures prédictions du jour.

**Paramètres:**
- `date` (optionnel): Date au format YYYY-MM-DD. Par défaut: date d'aujourd'hui

**Critères de sélection:**
- Valeur minimale de 5% vs les cotes des bookmakers
- Confiance minimale de 60%
- Diversifiés entre les compétitions

**Exemple de réponse:**

```json
{
  "date": "2025-02-01",
  "picks": [
    {
      "rank": 1,
      "pick_score": 0.1248,
      "prediction": {
        "match_id": 1,
        "home_team": "Manchester City",
        "away_team": "Arsenal",
        "competition": "Premier League",
        "match_date": "2025-02-02T15:30:00",
        "probabilities": {
          "home_win": 0.5234,
          "draw": 0.2456,
          "away_win": 0.2310
        },
        "recommended_bet": "home_win",
        "confidence": 0.72,
        "value_score": 0.1352,
        "explanation": "Notre modèle privilégie Manchester City pour cette rencontre. L'équipe bénéficie d'un fort avantage du terrain combiné à une excellente forme actuelle. Arsenal reste compétitif mais devrait avoir du mal à créer des occasions décisives.",
        "key_factors": [
          "Très bonne forme domestique",
          "Avantage du terrain significatif"
        ],
        "risk_factors": [
          "Absence de joueurs clés possibles",
          "Fatigue accumulée possible"
        ],
        "created_at": "2025-02-01T14:23:45",
        "is_daily_pick": true
      }
    }
  ],
  "total_matches_analyzed": 8
}
```

---

### 2. GET /api/v1/predictions/{match_id}

Retourne une prédiction détaillée pour un match spécifique.

**Paramètres:**
- `match_id` (requis): ID du match
- `include_model_details` (optionnel, défaut: false): Inclure les contributions individuelles des modèles

**Exemple d'appel:**

```bash
curl "http://localhost:8000/api/v1/predictions/1?include_model_details=true"
```

**Exemple de réponse (avec détails du modèle):**

```json
{
  "match_id": 1,
  "home_team": "Manchester City",
  "away_team": "Arsenal",
  "competition": "Premier League",
  "match_date": "2025-02-02T15:30:00",
  "probabilities": {
    "home_win": 0.5234,
    "draw": 0.2456,
    "away_win": 0.2310
  },
  "recommended_bet": "home_win",
  "confidence": 0.72,
  "value_score": 0.1352,
  "explanation": "Notre modèle privilégie Manchester City pour cette rencontre. L'équipe bénéficie d'un fort avantage du terrain combiné à une excellente forme actuelle. Arsenal reste compétitif mais devrait avoir du mal à créer des occasions décisives.",
  "key_factors": [
    "Très bonne forme domestique",
    "Avantage du terrain significatif",
    "Supériorité en possibilité statistique"
  ],
  "risk_factors": [
    "Absence de joueurs clés possibles",
    "Fatigue accumulée possible",
    "Conditions météorologiques défavorables"
  ],
  "model_contributions": {
    "poisson": {
      "home_win": 0.5123,
      "draw": 0.2534,
      "away_win": 0.2343
    },
    "xgboost": {
      "home_win": 0.5234,
      "draw": 0.2456,
      "away_win": 0.2310
    },
    "xg_model": {
      "home_win": 0.5167,
      "draw": 0.2523,
      "away_win": 0.2310
    },
    "elo": {
      "home_win": 0.5034,
      "draw": 0.2678,
      "away_win": 0.2288
    }
  },
  "llm_adjustments": {
    "injury_impact_home": -0.075,
    "injury_impact_away": -0.025,
    "sentiment_home": 0.032,
    "sentiment_away": -0.018,
    "tactical_edge": 0.012,
    "total_adjustment": -0.074,
    "reasoning": "Analyse LLM basée sur les actualités d'équipes et les facteurs contextuels."
  },
  "created_at": "2025-02-01T14:23:45",
  "is_daily_pick": false
}
```

**Explications des champs:**

- **probabilities**: Probabilités pour chaque issue (somme = 1.0)
  - `home_win`: Probabilité de victoire à domicile
  - `draw`: Probabilité de match nul
  - `away_win`: Probabilité de victoire à l'extérieur

- **recommended_bet**: L'issue avec la meilleure probabilité
  - `home_win`, `draw`, ou `away_win`

- **confidence**: Score de confiance (60-85%)
  - Indique la fiabilité de la prédiction
  - Plus élevé = plus fiable

- **value_score**: Score de valeur (5-18%)
  - Représente l'avantage par rapport aux cotes des bookmakers
  - Plus élevé = meilleure valeur

- **key_factors**: Facteurs clés en français
  - Les raisons principales soutenant la prédiction

- **risk_factors**: Facteurs de risque en français
  - Les éléments d'incertitude à considérer

- **model_contributions** (optionnel):
  - Contributions individuelles de 4 modèles:
    - Poisson: Modèle basé sur la distribution de Poisson
    - XGBoost: Modèle de gradient boosting
    - XG Model: Modèle basé sur expected goals
    - Elo: Évaluation du classement Elo

- **llm_adjustments** (optionnel):
  - Ajustements basés sur l'analyse LLM:
    - `injury_impact_*`: Impact des blessures (-0.3 à 0.0)
    - `sentiment_*`: Sentiment de l'équipe (-0.1 à 0.1)
    - `tactical_edge`: Avantage tactique (-0.05 à 0.05)
    - `total_adjustment`: Ajustement total

---

### 3. GET /api/v1/predictions/stats

Retourne les statistiques de performance des prédictions.

**Paramètres:**
- `days` (optionnel, défaut: 30): Nombre de jours à analyser (7-365)

**Exemple de réponse:**

```json
{
  "total_predictions": 187,
  "correct_predictions": 115,
  "accuracy": 0.6151,
  "roi_simulated": 0.1842,
  "by_competition": {
    "PL": {
      "total": 35,
      "correct": 22,
      "accuracy": 0.6286
    },
    "PD": {
      "total": 28,
      "correct": 17,
      "accuracy": 0.6071
    },
    "BL1": {
      "total": 24,
      "correct": 14,
      "accuracy": 0.5833
    },
    "SA": {
      "total": 25,
      "correct": 15,
      "accuracy": 0.6000
    },
    "FL1": {
      "total": 22,
      "correct": 12,
      "accuracy": 0.5455
    }
  },
  "by_bet_type": {
    "home_win": {
      "total": 67,
      "correct": 42,
      "accuracy": 0.6269,
      "avg_value": 0.1124
    },
    "draw": {
      "total": 45,
      "correct": 21,
      "accuracy": 0.4667,
      "avg_value": 0.0891
    },
    "away_win": {
      "total": 60,
      "correct": 33,
      "accuracy": 0.5500,
      "avg_value": 0.1234
    }
  },
  "last_updated": "2025-02-01T14:23:45"
}
```

**Explications des champs:**

- **total_predictions**: Nombre total de prédictions analysées
- **correct_predictions**: Nombre de prédictions correctes
- **accuracy**: Pourcentage de prédictions correctes (61.51%)
- **roi_simulated**: ROI simulé basé sur les cotes (18.42%)
- **by_competition**: Statistiques par compétition
  - PL: Premier League
  - PD: La Liga
  - BL1: Bundesliga
  - SA: Serie A
  - FL1: Ligue 1
- **by_bet_type**: Statistiques par type de pari
  - Inclut la valeur moyenne pour chaque type

---

## Matchs Disponibles en Mock Data

Les prédictions utilisent les données mock suivantes:

| ID  | Match                              | Compétition | Date |
|-----|-----------------------------------|------------|------|
| 1   | Manchester City vs Arsenal        | PL         | +1j  |
| 2   | Real Madrid vs Barcelona          | PD         | +2j  |
| 3   | Bayern Munich vs Borussia Dortmund | BL1        | +1j  |
| 4   | PSG vs Olympique Marseille        | FL1        | +3j  |
| 5   | Inter Milan vs AC Milan           | SA         | +2j  |
| 6   | Liverpool vs Manchester United    | PL         | +4j  |
| 7   | Atletico Madrid vs Real Sociedad  | PD         | +3j  |
| 8   | Napoli vs Juventus                | SA         | +1j  |
| 9   | Tottenham vs Chelsea              | PL         | +2j  |
| 10  | Bayer Leverkusen vs RB Leipzig    | BL1        | +2j  |

---

## Caractéristiques des Prédictions

### Probabilités Réalistes
Les probabilités sont générées de manière réaliste basée sur:
- La force relative supposée des équipes
- L'avantage du terrain (plus favorable pour les équipes à domicile)
- Des variations aléatoires pour simuler l'incertitude

### Confidence Score (60-85%)
- Indique la fiabilité de la prédiction
- Basé sur le consensus des modèles
- Les valeurs plus élevées indiquent une plus grande certitude

### Value Score (5-18%)
- Représente l'avantage de valeur par rapport aux cotes des bookmakers
- Plus élevé = meilleure opportunité de pari
- Utilisé pour les sélections des "picks du jour"

### Key Factors en Français
Exemples:
- "Très bonne forme domestique"
- "Avantage du terrain significatif"
- "Supériorité en possibilité statistique"
- "Excellente série loin du domicile"
- "Défense très solide en déplacements"

### Risk Factors en Français
Exemples:
- "Absence de joueurs clés possibles"
- "Fatigue accumulée possible"
- "Conditions météorologiques défavorables"
- "Arbitrage imprévisible"
- "Historique de blessures précoces"

### Explanations en Français
Explications générées automatiquement basées sur:
- L'issue prédite (victoire domicile, match nul, victoire extérieur)
- Les forces respectives des équipes
- Les facteurs clés identifiés

---

## Exemples de Requêtes cURL

### Obtenir les picks du jour

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/daily"
```

### Obtenir les picks pour une date spécifique

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/daily?date=2025-02-02"
```

### Obtenir une prédiction détaillée

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/1"
```

### Obtenir une prédiction avec les détails du modèle

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/1?include_model_details=true"
```

### Obtenir les statistiques de performance

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/stats"
```

### Obtenir les statistiques sur 60 jours

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/stats?days=60"
```

---

## Notes d'Implémentation

### Data Source
Les prédictions utilisent actuellement des données mock réalistes. Dans une implémentation en production:
- Les données seraient stockées dans une base de données PostgreSQL
- Les probabilités seraient calculées par des modèles ML réels (Poisson, XGBoost, XG)
- Les ajustements LLM seraient générés en temps réel par Claude/Groq
- Les explications seraient générées dynamiquement

### Performance
Les prédictions sont générées à la demande et peuvent être cachées via Redis pour:
- Le endpoint `/daily` (TTL: 30 minutes)
- Le endpoint `/{match_id}` (TTL: 30 minutes)
- Le endpoint `/stats` (TTL: 1 heure)

### Extensibilité
L'API est conçue pour être facilement étendue avec:
- Support pour d'autres types de compétitions
- Métriques supplémentaires (head-to-head, forme des équipes)
- Intégration avec des données de bookmakers réelles
- Support pour les paris en direct (live betting)

