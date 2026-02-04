# /review-and-fix - Review une PR et applique les fixes

Analyse une PR, identifie les problèmes et les corrige automatiquement.

## Workflow

1. **Checkout la branche** de la PR
2. **Analyser le diff** complet
3. **Lancer les checks**:
   - Ruff (Python linting)
   - Black (Python formatting)
   - Mypy (Python types)
   - ESLint (JS/TS linting)
   - TypeScript (type checking)
4. **Corriger automatiquement** ce qui peut l'être
5. **Lister les problèmes** qui nécessitent intervention manuelle
6. **Commit et push** les corrections

## Auto-fix activé pour

```bash
# Backend
uv run ruff check src/ --fix
uv run black src/
uv run isort src/

# Frontend  
npm run lint -- --fix
npx prettier --write "src/**/*.{ts,tsx}"
```

## Argument

Numéro de la PR ou branche
