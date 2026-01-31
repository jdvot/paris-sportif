# Paris Sportif Backend

Backend API for Paris Sportif - Football Betting Prediction App.

## Tech Stack
- FastAPI
- PostgreSQL + SQLAlchemy
- Redis (cache)
- XGBoost, scikit-learn (ML models)
- Anthropic Claude (LLM)

## Run locally
```bash
pip install -e .
uvicorn src.api.main:app --reload
```

## API Endpoints
- `GET /health` - Health check
- `GET /api/v1/matches` - List matches
- `GET /api/v1/predictions/daily` - Daily picks
