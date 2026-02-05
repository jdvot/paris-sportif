# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Application de paris sportifs sur le football europeen. Predictions basees sur modeles statistiques (Poisson, ELO, xG) + ML (XGBoost) + LLM (Groq/Claude) pour l'analyse qualitative.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / SQLAlchemy / Pydantic / uv
- **Frontend**: Next.js 15 / TypeScript / Tailwind CSS / shadcn/ui / React Query
- **Database**: PostgreSQL + Redis (cache)
- **ML**: scikit-learn, XGBoost, NumPy, SciPy
- **LLM**: Groq (Llama 3.3 70B) for production, Claude API for dev
- **Auth**: Supabase (JWT)
- **API Client**: Orval (generates React Query hooks from OpenAPI)

## Key Commands

```bash
# Backend
cd backend && uv run uvicorn src.api.main:app --reload  # Dev server (port 8000)
cd backend && uv run pytest                              # Run all tests
cd backend && uv run pytest tests/test_file.py -k "test_name"  # Single test
cd backend && uv run alembic upgrade head               # Run migrations
cd backend && uv run black src/ && uv run isort src/   # Format code

# Frontend
cd frontend && npm run dev        # Dev server (port 3000)
cd frontend && npm run build      # Production build
cd frontend && npm run lint       # ESLint
cd frontend && npm run type-check # TypeScript check
cd frontend && npm run generate:api  # Regenerate API hooks from OpenAPI

# Docker
docker-compose up -d  # Start PostgreSQL + Redis
```

## Architecture

### Backend Structure

```
backend/src/
├── api/routes/          # FastAPI endpoints (matches, predictions, users, admin)
├── prediction_engine/   # Core ML models
│   ├── models/          # Poisson, ELO, XGBoost, RandomForest
│   ├── ensemble_advanced.py  # Combines 6 models with weighted average
│   └── rag_enrichment.py # News/injury context via RAG
├── llm/                 # LLM integration
│   ├── client.py        # Groq/Anthropic client
│   ├── adjustments.py   # Parse LLM output to probability adjustments
│   └── prompts.py       # System prompts for analysis
├── data/                # Data fetching (football-data.org, Understat)
├── auth/                # Supabase JWT validation
└── db/                  # SQLAlchemy models
```

### Frontend Structure

```
frontend/src/
├── app/                 # Next.js App Router pages
│   ├── (protected)/     # Auth-required routes (picks, match/[id], profile)
│   └── auth/            # Login, signup, password reset
├── components/          # React components (PredictionCard, StatsOverview, etc.)
├── lib/
│   ├── api/             # Orval-generated hooks and types
│   │   ├── endpoints/   # React Query hooks by tag
│   │   ├── models/      # TypeScript types from OpenAPI
│   │   └── custom-instance.ts  # Fetch wrapper with auth
│   ├── constants.ts     # Confidence/value thresholds and tier configs
│   └── supabase/        # Supabase client setup
├── hooks/               # Custom React hooks
└── middleware.ts        # Auth redirect logic
```

### Prediction Models

The advanced ensemble predictor (`ensemble_advanced.py`) combines 6 models with weighted average:

| Model | Weight | Description |
|-------|--------|-------------|
| Dixon-Coles | 30% | Time-weighted attack/defense ratings with dependency correction |
| Advanced ELO | 25% | Team strength with form, home advantage, goal difference |
| XGBoost | 20% | Gradient boosting classifier on match features |
| Poisson | 10% | Goal distribution (lambda = attack × defense) |
| Random Forest | 10% | Ensemble of decision trees for classification |
| Basic ELO | 5% | Simple rating system (K=20, home advantage +100) |

LLM adjustments are applied via log-odds transformation, bounded to ±0.5 max.

### API Client Generation

Frontend uses **Orval** to generate React Query hooks from the backend OpenAPI spec:

1. Backend exposes `/openapi.json`
2. Run `npm run generate:api` to regenerate `src/lib/api/`
3. Generated hooks use `customInstance` for auth and error handling

## Key Files

- `backend/src/prediction_engine/ensemble_advanced.py` - Advanced ensemble (6 models)
- `frontend/src/lib/constants.ts` - Confidence/value thresholds and colors
- `frontend/src/lib/api/custom-instance.ts` - API fetch wrapper with Supabase auth
- `frontend/orval.config.ts` - API generation config

## Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql://user:pass@localhost:5432/paris_sportif
REDIS_URL=redis://localhost:6379
FOOTBALL_DATA_API_KEY=your_key
GROQ_API_KEY=your_key  # Primary LLM
SUPABASE_JWT_SECRET=your_jwt_secret

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_key
```

## Code Style

- Python: Black (line-length=100), isort, mypy strict
- TypeScript: ESLint, Prettier
- Commits: Conventional commits (feat:, fix:, docs:)
- Dark mode: Use `dark:` Tailwind classes with `slate-*` colors for consistency

## Recherche de Documentation

**IMPORTANT**: Avant toute recherche de documentation externe (Supabase, Next.js, etc.):

1. Toujours vérifier la date actuelle avec `date` avant d'utiliser WebSearch
2. Inclure l'année courante dans les requêtes de recherche (ex: "Supabase SSR Next.js 2026")
3. Privilégier les sources officielles et les exemples GitHub récents
4. Vérifier la compatibilité des versions (Next.js 15, @supabase/ssr, etc.)

## Data Flow

1. **football-data.org** → Backend fetches matches/stats
2. **Prediction Engine** → Ensemble model generates probabilities
3. **LLM (Groq)** → Analyzes news/injuries, adjusts probabilities ±0.5 max
4. **Daily Picks** → Top 5 matches by `value_score × confidence`
5. **Frontend** → React Query hooks fetch and cache data

## MCP & Agents

Le projet utilise MCP (Model Context Protocol) pour l'intégration avec des outils externes:

| Server | Usage |
|--------|-------|
| **Linear** | Gestion des tickets (create, update, list) |
| **Notion** | Documentation et specs |

### Workflows Multi-Agents

1. **Feature Development**: Plan → Ticket Linear → Dev → PR → Doc Notion
2. **Bug Triage**: Explore → Ticket Linear → Fix → PR + Tests

Voir [docs/MCP_AGENTS.md](docs/MCP_AGENTS.md) pour la documentation complète.

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) | Git flow, branches, worktrees multi-agents |
| [docs/ORVAL_API.md](docs/ORVAL_API.md) | Génération API client React Query |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Déploiement Vercel + Render |
| [docs/MCP_AGENTS.md](docs/MCP_AGENTS.md) | Configuration MCP et agents spécialisés |
