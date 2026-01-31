# CLAUDE.md - Paris Sportif App

## Project Overview
Application de paris sportifs sur le football europeen. Predictions basees sur modeles statistiques (Poisson, ELO, xG) + ML (XGBoost) + LLM (Claude) pour l'analyse qualitative.

## Tech Stack
- **Backend**: Python 3.11+ / FastAPI / SQLAlchemy / Pydantic
- **Frontend**: Next.js 15 / TypeScript / Tailwind CSS / shadcn/ui
- **Database**: PostgreSQL + Redis (cache)
- **ML**: scikit-learn, XGBoost, NumPy, SciPy
- **LLM**: Claude API (Anthropic)
- **Vector DB**: Qdrant (RAG)

## Project Structure
```
/paris-sportif
├── backend/src/
│   ├── api/           # FastAPI routes
│   ├── prediction_engine/  # ML models (Poisson, ELO, XGBoost)
│   ├── llm/           # Claude integration
│   ├── data/          # Data sources (football-data.org)
│   └── db/            # SQLAlchemy models
├── frontend/src/
│   ├── app/           # Next.js App Router
│   ├── components/    # React components
│   └── lib/           # Utils, API client
└── docs/              # Documentation
```

## Key Commands
```bash
# Backend
cd backend && uv run uvicorn src.api.main:app --reload
cd backend && uv run pytest

# Frontend
cd frontend && npm run dev
cd frontend && npm run build

# Docker
docker-compose up -d  # Start all services
```

## API Endpoints
- `GET /api/v1/matches` - Liste des matchs
- `GET /api/v1/predictions/daily` - 5 picks du jour
- `GET /api/v1/predictions/{match_id}` - Prediction detaillee

## Environment Variables
```
# Backend (.env)
DATABASE_URL=postgresql://user:pass@localhost:5432/paris_sportif
REDIS_URL=redis://localhost:6379
FOOTBALL_DATA_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Prediction Models
1. **Poisson (25%)** - Distribution des buts
2. **XGBoost (35%)** - Classification match outcome
3. **xG Model (25%)** - Expected Goals based
4. **ELO (15%)** - Team strength rating

## LLM Usage
- Analyse news/blessures (Claude Haiku)
- Generation explications (Claude Sonnet)
- Ajustements bornes a +/-0.5 max

## Code Style
- Python: Black, isort, mypy
- TypeScript: ESLint, Prettier
- Commits: Conventional commits (feat:, fix:, docs:)

## Data Sources
- football-data.org (principal, gratuit)
- Understat (xG scraping)
- News RSS (Sky Sports, BBC, L'Equipe)
