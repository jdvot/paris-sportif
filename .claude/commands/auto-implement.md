# /auto-implement - Workflow automatisé complet

Implémente un ticket de A à Z automatiquement:
1. Récupère le ticket → 2. Crée worktree → 3. Implémente → 4. Tests → 5. PR → 6. Vérifie suggestions → 7. Applique fixes → 8. Merge → 9. Cleanup

## Workflow Automatique

### Phase 1: Setup
- Récupérer le ticket Linear complet
- Passer le ticket en "In Progress"
- Créer worktree avec branche conventionnelle
- Pull main pour être à jour

### Phase 2: Implémentation
- Analyser les requirements du ticket
- Implémenter le code nécessaire
- Respecter les conventions du projet (CLAUDE.md)
- Ajouter tests si nécessaire

### Phase 3: Validation locale
- Backend: `uv run ruff check src/ --fix && uv run black src/ && uv run pytest`
- Frontend: `npm run lint -- --fix && npm run type-check && npm run build`
- Commit avec message conventionnel

### Phase 4: PR & Review
- Push la branche
- Créer la PR avec description complète
- **Attendre les CI checks** (5 min max)
- **Récupérer les suggestions** du claude-review bot
- **Appliquer automatiquement** les suggestions pertinentes
- Push les corrections
- Re-vérifier les CI

### Phase 5: Finalisation
- Merger la PR (squash)
- Passer le ticket en "Done"
- Supprimer le worktree
- Confirmer la completion

## Argument

Numéro du ticket: `PAR-XXX` ou `XXX`

## Exemple

```
/auto-implement PAR-132
```

Résultat attendu:
- ✅ Ticket implémenté
- ✅ PR mergée
- ✅ Suggestions appliquées
- ✅ Ticket Done
- ✅ Worktree nettoyé
