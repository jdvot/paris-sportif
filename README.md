# Paris Sportif - Football Betting Prediction App

Application intelligente de prediction de paris sportifs sur le football europeen. Combine des modeles statistiques, du machine learning et des LLMs pour proposer les 5 meilleurs matchs a jouer chaque jour.

## Features

- **5 Daily Picks** - Selection automatique des meilleurs paris du jour
- **Analyse Multi-Modeles** - Poisson, ELO, xG, XGBoost combines
- **Explications LLM** - Analyses detaillees generees par Claude
- **5 Grands Championnats** - Premier League, La Liga, Bundesliga, Serie A, Ligue 1
- **Coupes Europeennes** - Champions League, Europa League
- **Tracking Performance** - Suivi des predictions vs resultats reels

## Tech Stack (100% Gratuit)

| Layer | Technology | Hebergement |
|-------|------------|-------------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS | **Vercel** (gratuit) |
| Backend | Python 3.11+, FastAPI, SQLAlchemy | **Render** (gratuit) |
| Database | PostgreSQL | **Render** (gratuit) |
| LLM | **Groq** (Llama 3.3 70B) | Gratuit (14K req/jour) |
| Data | football-data.org API | Gratuit (10 req/min) |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                              │
│                    Next.js 15 + shadcn/ui                     │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                         BACKEND                               │
│                      FastAPI + Python                         │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   Poisson   │  │   XGBoost   │  │   LLM Adjustments   │   │
│  │    (25%)    │  │    (35%)    │  │   (News, Injuries)  │   │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘   │
│         │                │                    │               │
│  ┌──────┴──────┐  ┌──────┴──────┐            │               │
│  │   xG Model  │  │     ELO     │            │               │
│  │    (25%)    │  │    (15%)    │            │               │
│  └──────┬──────┘  └──────┬──────┘            │               │
│         └────────────────┴───────────────────┘               │
│                          │                                    │
│              ┌───────────▼───────────┐                       │
│              │   Ensemble + Value    │                       │
│              │      Selection        │                       │
│              └───────────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

## Deploiement Gratuit

### Services Gratuits Requis
1. **Groq** (LLM gratuit) - https://console.groq.com/
2. **football-data.org** - https://www.football-data.org/client/register
3. **Vercel** (frontend) - https://vercel.com
4. **Render** (backend + DB) - https://render.com

Voir [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) pour le guide complet.

## Quick Start (Local)

### Prerequisites
- Python 3.11+ avec [uv](https://docs.astral.sh/uv/)
- Node.js 22+
- Docker & Docker Compose
- Groq API key (gratuit)
- football-data.org API key (gratuit)

### Installation

```bash
# 1. Clone
git clone <repo>
cd paris-sportif

# 2. Configuration
cp .env.example .env
# Éditer .env avec vos clés API

# 3. Installer les dépendances
make install

# 4. Démarrer les services Docker
docker-compose up -d

# 5. Lancer en développement
make dev
```

**Accès:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Commandes Makefile

| Commande | Description |
|----------|-------------|
| `make dev` | Lance backend + frontend en parallèle |
| `make test` | Exécute tous les tests |
| `make lint` | Vérifie le code (ruff, mypy, eslint) |
| `make format` | Formate le code (black, prettier) |
| `make install` | Installe toutes les dépendances |
| `make sync-api` | Sync OpenAPI et regénère Orval |
| `make build` | Build frontend pour production |
| `make clean` | Nettoie les fichiers temporaires |

### Commandes individuelles

```bash
make dev-backend   # Lance uniquement le backend (port 8000)
make dev-frontend  # Lance uniquement le frontend (port 3000)
make test-backend  # Tests backend uniquement
make test-frontend # Tests frontend uniquement
```

## Prediction Models

### Poisson Distribution (25%)
Modele statistique classique pour predire la distribution des buts.
- Lambda home = avg_goals_scored_home × avg_goals_conceded_away
- Lambda away = avg_goals_scored_away × avg_goals_conceded_home

### XGBoost Classifier (35%)
Gradient boosting pour classification 3 classes (1/X/2).
- Features: forme, H2H, xG, stats defensives/offensives
- Calibration Platt pour probabilites

### Expected Goals Model (25%)
Base sur la qualite des occasions creees/concedees.
- xG for/against moyennes sur 10 matchs
- Meilleur predicteur que buts reels

### ELO Rating (15%)
Systeme de classement adapte au football.
- Rating initial: 1500
- K-factor: 20
- Home advantage: +100

### LLM Adjustments (Groq - Llama 3.3 70B)
Llama analyse les news et blessures pour ajuster les predictions.
- Impact blessures: -0.3 a 0
- Sentiment: -0.1 a +0.1
- **Borne max: +/-0.5** pour eviter les derives

## Daily Picks Selection

```python
# Selection des 5 meilleurs matchs
value_score = (our_probability - bookmaker_probability) / bookmaker_probability
final_score = value_score × confidence

# Criteres:
# - Minimum 5% de value
# - Diversite des championnats
# - Confiance > 60%
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/matches` | Liste des matchs a venir |
| GET | `/api/v1/matches/{id}` | Details d'un match |
| GET | `/api/v1/predictions/daily` | 5 picks du jour |
| GET | `/api/v1/predictions/{match_id}` | Prediction detaillee |
| GET | `/api/v1/teams/{id}/form` | Forme recente d'une equipe |

### Example Response

```json
{
  "match_id": 12345,
  "home_team": "Manchester City",
  "away_team": "Liverpool",
  "predictions": {
    "home_win": 0.45,
    "draw": 0.28,
    "away_win": 0.27
  },
  "recommended_bet": "home_win",
  "confidence": 0.72,
  "value_score": 0.08,
  "explanation": "City en grande forme...",
  "key_factors": [
    "5 victoires consecutives a domicile",
    "Liverpool sans Salah (blesse)"
  ]
}
```

## Project Structure

```
paris-sportif/
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI routes
│   │   ├── prediction_engine/
│   │   │   ├── models/       # Poisson, ELO, XGBoost
│   │   │   ├── features/     # Feature engineering
│   │   │   └── ensemble.py   # Model combination
│   │   ├── llm/              # Claude integration
│   │   ├── data/             # Data sources
│   │   └── db/               # Database models
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages
│   │   ├── components/       # React components
│   │   └── lib/              # Utils, types
│   └── public/
├── docs/
├── docker-compose.yml
└── README.md
```

## Development

### Running Tests
```bash
# Tous les tests
make test

# Par projet
make test-backend
make test-frontend
```

### Code Quality
```bash
# Linting complet
make lint

# Formatting
make format

# API Sync (OpenAPI → Orval)
make sync-api
```

## Performance Tracking

L'application suit automatiquement la performance des predictions:
- Taux de reussite global
- ROI simule (sans mise reelle)
- Performance par championnat
- Performance par type de pari

## License

MIT License - Projet educatif, pas de conseils financiers.

## Disclaimer

Cette application est a but educatif. Les paris sportifs comportent des risques. Ne pariez jamais plus que ce que vous pouvez vous permettre de perdre.
