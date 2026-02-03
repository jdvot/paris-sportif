# Git Workflow

Flux de travail Git simple pour développeur solo.

## Workflow Principal

```
main ←── feature-branch ←── commits
```

### 1. Créer une branche feature

```bash
git checkout main
git pull origin main
git checkout -b feature/nom-feature
```

### 2. Développer et commiter

```bash
# Commits atomiques avec conventional commits
git add <fichiers>
git commit -m "feat: description courte"
```

**Prefixes commits:**
- `feat:` - Nouvelle fonctionnalité
- `fix:` - Correction de bug
- `docs:` - Documentation
- `style:` - Formatting, pas de changement de code
- `refactor:` - Refactoring sans changement de comportement
- `test:` - Ajout/modification de tests
- `chore:` - Maintenance, dépendances

### 3. Push et créer PR

```bash
git push -u origin feature/nom-feature
```

Puis créer la PR via GitHub ou CLI:

```bash
gh pr create --title "feat: description" --body "## Summary
- Point 1
- Point 2

## Test plan
- [ ] Tests passent
- [ ] Build OK"
```

### 4. Merge dans main

```bash
# Via GitHub UI: "Squash and merge" (recommandé)
# Ou via CLI:
gh pr merge --squash
```

### 5. Nettoyer

```bash
git checkout main
git pull origin main
git branch -d feature/nom-feature
```

## Commits directs sur main

Pour les petits fixes rapides (typos, hotfixes urgents):

```bash
git checkout main
git add <fichiers>
git commit -m "fix: correction rapide"
git push origin main
```

## Commandes utiles

```bash
# Voir l'état
git status
git log --oneline -10

# Annuler dernier commit (pas pushé)
git reset --soft HEAD~1

# Stash temporaire
git stash
git stash pop

# Sync avec remote
git fetch origin
git pull origin main --rebase
```

## Structure des branches

| Branche | Usage |
|---------|-------|
| `main` | Production, toujours stable |
| `feature/*` | Nouvelles fonctionnalités |
| `fix/*` | Corrections de bugs |
| `hotfix/*` | Fixes urgents production |

## Git Worktrees (Multi-agents)

Les worktrees permettent de travailler sur plusieurs branches en parallèle dans des dossiers séparés. Utile pour lancer plusieurs agents Claude sur différentes features.

### Structure recommandée

```
~/projects/
├── paris-sportif/           # Repo principal (main)
├── paris-sportif-feature-a/ # Worktree branche feature-a
└── paris-sportif-feature-b/ # Worktree branche feature-b
```

### Créer un worktree

```bash
# Depuis le repo principal
cd ~/projects/paris-sportif

# Créer une nouvelle branche + worktree
git worktree add ../paris-sportif-feature-auth feature/auth

# Ou pour une branche existante
git worktree add ../paris-sportif-feature-ui feature/ui
```

### Lancer un agent par worktree

```bash
# Terminal 1 - Agent sur feature/auth
cd ~/projects/paris-sportif-feature-auth
claude

# Terminal 2 - Agent sur feature/ui
cd ~/projects/paris-sportif-feature-ui
claude

# Terminal 3 - Agent sur main (hotfixes)
cd ~/projects/paris-sportif
claude
```

### Lister les worktrees

```bash
git worktree list
# /Users/admin/paris-sportif              abc1234 [main]
# /Users/admin/paris-sportif-feature-auth def5678 [feature/auth]
# /Users/admin/paris-sportif-feature-ui   ghi9012 [feature/ui]
```

### Supprimer un worktree

```bash
# Après merge de la branche
git worktree remove ../paris-sportif-feature-auth

# Ou forcer si modifications non commitées
git worktree remove --force ../paris-sportif-feature-auth

# Nettoyer les références obsolètes
git worktree prune
```

### Workflow multi-agents

1. **Créer les worktrees** pour chaque feature
   ```bash
   git worktree add ../ps-backend feature/backend-api
   git worktree add ../ps-frontend feature/frontend-ui
   ```

2. **Lancer un agent Claude** dans chaque dossier
   - Chaque agent travaille sur sa branche isolée
   - Pas de conflits de fichiers entre agents

3. **Merger les branches** une par une
   ```bash
   cd ~/projects/paris-sportif
   git merge feature/backend-api
   git merge feature/frontend-ui
   ```

4. **Nettoyer**
   ```bash
   git worktree remove ../ps-backend
   git worktree remove ../ps-frontend
   git branch -d feature/backend-api feature/frontend-ui
   ```

### Avantages worktrees vs branches classiques

| Aspect | Branches classiques | Worktrees |
|--------|---------------------|-----------|
| Changement de contexte | `git checkout` (perd état) | Dossier séparé |
| Agents parallèles | Impossible | ✅ Un agent par dossier |
| node_modules | Partagé | Séparé (peut diverger) |
| Conflits fichiers | Possibles | Isolés |
