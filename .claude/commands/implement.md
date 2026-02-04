# /implement - Implémenter un ticket

Workflow complet pour implémenter un ticket Linear.

## Instructions

1. **Récupérer le ticket** via `mcp__linear__get_issue`
2. **Mettre en "In Progress"** via `mcp__linear__update_issue`
3. **Créer un worktree** avec la branche appropriée:
   ```bash
   git worktree add /Users/admin/paris-sportif-worktrees/par-XXX -b feat/par-XXX-description main
   ```
4. **Analyser les requirements** du ticket
5. **Implémenter** le code nécessaire
6. **Tester** avec les commandes appropriées:
   - Backend: `uv run pytest`
   - Frontend: `npm run test && npm run type-check`
7. **Commit** avec message conventionnel
8. **Push** la branche
9. **Créer la PR** via `gh pr create`
10. **Mettre à jour le ticket** en "In Review"

## Convention de branches

- `feat/par-XXX-description` - Nouvelles features
- `fix/par-XXX-description` - Bug fixes
- `chore/par-XXX-description` - Maintenance
- `docs/par-XXX-description` - Documentation

## Argument

Le numéro du ticket (ex: `PAR-132` ou juste `132`)
