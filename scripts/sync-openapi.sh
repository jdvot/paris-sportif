#!/bin/bash
# sync-openapi.sh
# Synchronise le schéma OpenAPI du backend et regénère les hooks Orval

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
OPENAPI_PATH="$ROOT_DIR/frontend/openapi.json"

echo "🔄 Syncing OpenAPI schema from backend..."

# Check if backend is running
if ! curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo "⚠️  Backend not running at $BACKEND_URL"
    echo "   Starting backend temporarily..."
    
    # Start backend in background
    cd "$ROOT_DIR/backend"
    uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    # Wait for backend to start
    echo "   Waiting for backend to start..."
    sleep 5
    
    # Fetch OpenAPI
    curl -s "$BACKEND_URL/openapi.json" > "$OPENAPI_PATH"
    
    # Stop backend
    kill $BACKEND_PID 2>/dev/null || true
    echo "   Backend stopped"
else
    echo "✅ Backend is running"
    curl -s "$BACKEND_URL/openapi.json" > "$OPENAPI_PATH"
fi

echo "📥 OpenAPI schema saved to frontend/openapi.json"

# Regenerate Orval hooks
echo "🔧 Regenerating Orval hooks..."
cd "$ROOT_DIR/frontend"
npm run generate:api

echo "✅ API sync completed!"
echo ""
echo "Generated files:"
echo "  - frontend/src/lib/api/endpoints/*.ts"
echo "  - frontend/src/lib/api/models/*.ts"
