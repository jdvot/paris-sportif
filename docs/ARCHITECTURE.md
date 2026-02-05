# Architecture Paris Sportif

Application de paris sportifs sur le football européen. Prédictions basées sur modèles statistiques (Poisson, ELO, xG) + ML (XGBoost) + LLM (Groq/Claude) pour l'analyse qualitative.

## Table des Matières

- [Stack Technique](#stack-technique)
- [Structure du Projet](#structure-du-projet)
- [Modèles de Prédiction](#modèles-de-prédiction)
- [Flux de Données](#flux-de-données)
- [Documentation Liée](#documentation-liée)

---

## Stack Technique

| Composant | Technologies |
|-----------|-------------|
| **Backend** | Python 3.11+ / FastAPI / SQLAlchemy / Pydantic / uv |
| **Frontend** | Next.js 15 / TypeScript / Tailwind CSS / shadcn/ui / React Query |
| **Database** | PostgreSQL + Redis (cache) |
| **ML** | scikit-learn, XGBoost, NumPy, SciPy |
| **LLM** | Groq (Llama 3.3 70B) production, Claude API dev |
| **Auth** | Supabase (JWT) |
| **API Client** | Orval (génère React Query hooks depuis OpenAPI) |

---

## Structure du Projet

```
paris-sportif/
├── backend/                 # API Python FastAPI
│   ├── src/
│   │   ├── api/routes/      # Endpoints REST
│   │   ├── prediction_engine/  # ML models
│   │   ├── llm/             # Intégration LLM
│   │   ├── data/            # Data fetching
│   │   ├── auth/            # JWT validation
│   │   └── db/              # SQLAlchemy models
│   ├── tests/
│   └── pyproject.toml
│
├── frontend/                # App Next.js
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── components/      # React components
│   │   ├── lib/api/         # Hooks Orval générés
│   │   └── hooks/           # Custom hooks
│   └── package.json
│
├── docs/                    # Documentation
├── scripts/                 # Scripts utilitaires
└── docker-compose.yml       # PostgreSQL + Redis
```

### Backend (`backend/src/`)

| Dossier | Description |
|---------|-------------|
| `api/routes/` | Endpoints FastAPI (matches, predictions, users, admin) |
| `prediction_engine/models/` | Modèles ML (Poisson, ELO, XGBoost, RandomForest) |
| `prediction_engine/ensemble_advanced.py` | Combinaison 6 modèles avec moyenne pondérée |
| `prediction_engine/rag_enrichment.py` | Contexte news/blessures via RAG |
| `llm/client.py` | Client Groq/Anthropic |
| `llm/adjustments.py` | Parse output LLM → ajustements probabilités |
| `llm/prompts.py` | System prompts pour analyses |
| `data/` | Fetching football-data.org, Understat |
| `auth/` | Validation JWT Supabase |
| `db/` | Modèles SQLAlchemy |

### Frontend (`frontend/src/`)

| Dossier | Description |
|---------|-------------|
| `app/(protected)/` | Routes authentifiées (picks, match/[id], profile) |
| `app/auth/` | Login, signup, password reset |
| `components/` | PredictionCard, StatsOverview, etc. |
| `lib/api/endpoints/` | Hooks React Query par tag |
| `lib/api/models/` | Types TypeScript depuis OpenAPI |
| `lib/api/custom-instance.ts` | Fetch wrapper avec auth |
| `lib/constants.ts` | Seuils confidence/value, configs tiers |
| `lib/supabase/` | Client Supabase setup |
| `hooks/` | Custom React hooks |
| `middleware.ts` | Logique redirect auth |

---

## Modèles de Prédiction

L'ensemble avancé (`ensemble_advanced.py`) combine 6 modèles avec moyenne pondérée:

| Modèle | Poids | Description |
|--------|-------|-------------|
| **Dixon-Coles** | 30% | Ratings attaque/défense time-weighted avec correction dépendance |
| **Advanced ELO** | 25% | Force équipe avec forme, avantage domicile, goal difference |
| **XGBoost** | 20% | Gradient boosting classifier sur features match |
| **Poisson** | 10% | Distribution buts (λ = attaque × défense) |
| **Random Forest** | 10% | Ensemble arbres décision pour classification |
| **Basic ELO** | 5% | Rating simple (K=20, avantage domicile +100) |

### Ajustements LLM

Les ajustements LLM sont appliqués via **transformation log-odds**, bornés à **±0.5 max**.

```python
# Exemple: ajustement de +0.05 sur victoire domicile
log_odds = log(p / (1 - p))
adjusted_log_odds = log_odds + adjustment  # max ±0.5
adjusted_p = 1 / (1 + exp(-adjusted_log_odds))
```

---

## Flux de Données

```mermaid
flowchart TD
    subgraph Sources["Sources de Données"]
        FD[football-data.org]
        US[Understat xG]
        NEWS[News/RSS Feeds]
    end

    subgraph Backend["Backend Python"]
        FETCH[Data Fetcher]
        PE[Prediction Engine]
        LLM[LLM Groq/Claude]
        API[FastAPI REST API]
        DB[(PostgreSQL)]
        CACHE[(Redis Cache)]
    end

    subgraph ML["Modèles ML"]
        DC[Dixon-Coles 30%]
        ELO[Advanced ELO 25%]
        XGB[XGBoost 20%]
        POI[Poisson 10%]
        RF[Random Forest 10%]
        BELO[Basic ELO 5%]
    end

    subgraph Frontend["Frontend Next.js"]
        RQ[React Query]
        UI[UI Components]
        AUTH[Supabase Auth]
    end

    FD --> FETCH
    US --> FETCH
    NEWS --> LLM

    FETCH --> DB
    FETCH --> PE

    PE --> DC & ELO & XGB & POI & RF & BELO
    DC & ELO & XGB & POI & RF & BELO --> |Ensemble| PE

    PE --> LLM
    LLM --> |Ajustements ±0.5| API

    API --> CACHE
    CACHE --> RQ
    RQ --> UI
    AUTH --> UI
```

## Architecture Système

```mermaid
graph TB
    subgraph Client["Client Browser"]
        NEXT[Next.js 15 App]
        RQ[React Query]
        SB_CLIENT[Supabase Client]
    end

    subgraph Vercel["Vercel Edge"]
        MW[Middleware Auth]
        SSR[Server Components]
    end

    subgraph Backend["Render / Azure"]
        FAST[FastAPI Server]
        WORKER[Background Workers]
    end

    subgraph Services["Services Externes"]
        SB[Supabase Auth]
        GROQ[Groq LLM API]
        FDATA[football-data.org]
    end

    subgraph Data["Data Layer"]
        PG[(PostgreSQL)]
        REDIS[(Redis)]
    end

    NEXT --> MW
    MW --> SSR
    SSR --> FAST

    RQ --> FAST
    SB_CLIENT --> SB

    FAST --> PG
    FAST --> REDIS
    FAST --> GROQ

    WORKER --> FDATA
    WORKER --> PG
```

## Modèles de Prédiction - Pipeline

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant E as Ensemble Engine
    participant M as ML Models
    participant L as LLM (Groq)
    participant D as Database

    C->>A: GET /predictions/{match_id}
    A->>D: Fetch match data
    D-->>A: Match + Team stats

    A->>E: Calculate predictions

    par Parallel Model Execution
        E->>M: Dixon-Coles (30%)
        E->>M: Advanced ELO (25%)
        E->>M: XGBoost (20%)
        E->>M: Poisson (10%)
        E->>M: Random Forest (10%)
        E->>M: Basic ELO (5%)
    end

    M-->>E: Individual probabilities
    E->>E: Weighted average

    E->>L: Request qualitative analysis
    L-->>E: Adjustments [-0.5, +0.5]

    E->>E: Apply log-odds transformation
    E-->>A: Final probabilities
    A-->>C: Prediction response
```

---

## Variables d'Environnement

### Backend (`.env`)

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/paris_sportif
REDIS_URL=redis://localhost:6379
FOOTBALL_DATA_API_KEY=your_key
GROQ_API_KEY=your_key  # Primary LLM
SUPABASE_JWT_SECRET=your_jwt_secret
```

### Frontend (`.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_key
```

---

## Documentation Liée

| Document | Description |
|----------|-------------|
| [GIT_WORKFLOW.md](./GIT_WORKFLOW.md) | Git flow, branches, worktrees multi-agents |
| [ORVAL_API.md](./ORVAL_API.md) | Génération API client React Query |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Déploiement Vercel + Render |
| [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md) | Plan de récupération |
| [CLAUDE_AGENTS.md](./CLAUDE_AGENTS.md) | Guide création agents spécialisés |

---

## Liens Externes

- [Linear - Paris Sportif](https://linear.app/paris-sportif) - Gestion tickets
- [Vercel](https://vercel.com) - Hébergement frontend
- [Render](https://render.com) - Hébergement backend
- [Supabase](https://supabase.com) - Auth & Database
