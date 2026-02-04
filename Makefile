# Paris Sportif - Monorepo Makefile
# Commandes unifiées pour backend (Python/uv) et frontend (Node/npm)

.PHONY: help dev dev-backend dev-frontend test test-backend test-frontend lint lint-backend lint-frontend format format-backend format-frontend install install-backend install-frontend clean sync-api build

# Default target
help:
	@echo "Paris Sportif - Commandes disponibles:"
	@echo ""
	@echo "  make dev          - Lance backend + frontend en parallèle"
	@echo "  make test         - Exécute tous les tests"
	@echo "  make lint         - Vérifie le code (ruff + eslint)"
	@echo "  make format       - Formate le code (black + prettier)"
	@echo "  make install      - Installe les dépendances"
	@echo "  make sync-api     - Sync OpenAPI et regénère les hooks Orval"
	@echo "  make build        - Build frontend pour production"
	@echo "  make clean        - Nettoie les fichiers temporaires"
	@echo ""
	@echo "Commandes individuelles:"
	@echo "  make dev-backend  - Lance uniquement le backend (port 8000)"
	@echo "  make dev-frontend - Lance uniquement le frontend (port 3000)"

# ============================================================================
# DEVELOPMENT
# ============================================================================

dev:
	@echo "🚀 Lancement backend (8000) + frontend (3000)..."
	@make -j2 dev-backend dev-frontend

dev-backend:
	@echo "🐍 Backend starting on http://localhost:8000"
	cd backend && uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "⚛️  Frontend starting on http://localhost:3000"
	cd frontend && npm run dev

# ============================================================================
# TESTING
# ============================================================================

test: test-backend test-frontend
	@echo "✅ All tests completed"

test-backend:
	@echo "🧪 Running backend tests..."
	cd backend && uv run pytest tests/ -v --tb=short

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd frontend && npm run test:run

# ============================================================================
# LINTING
# ============================================================================

lint: lint-backend lint-frontend
	@echo "✅ Linting completed"

lint-backend:
	@echo "🔍 Linting backend (ruff + mypy)..."
	cd backend && uv run ruff check src/ tests/
	cd backend && uv run mypy src/ --ignore-missing-imports

lint-frontend:
	@echo "🔍 Linting frontend (eslint + tsc)..."
	cd frontend && npm run lint
	cd frontend && npm run type-check

# ============================================================================
# FORMATTING
# ============================================================================

format: format-backend format-frontend
	@echo "✅ Formatting completed"

format-backend:
	@echo "🎨 Formatting backend (black + isort)..."
	cd backend && uv run black src/ tests/
	cd backend && uv run isort src/ tests/

format-frontend:
	@echo "🎨 Formatting frontend (prettier)..."
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,json,css,md}"

# ============================================================================
# INSTALLATION
# ============================================================================

install: install-backend install-frontend
	@echo "✅ All dependencies installed"

install-backend:
	@echo "📦 Installing backend dependencies..."
	cd backend && uv sync --all-extras

install-frontend:
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install

# ============================================================================
# API SYNC
# ============================================================================

sync-api:
	@echo "🔄 Syncing OpenAPI spec and regenerating Orval hooks..."
	@./scripts/sync-openapi.sh

# ============================================================================
# BUILD
# ============================================================================

build:
	@echo "🏗️  Building frontend for production..."
	cd frontend && npm run build

# ============================================================================
# CLEANUP
# ============================================================================

clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules/.cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed"
