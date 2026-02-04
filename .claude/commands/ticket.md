# /ticket - Créer un ticket Linear automatiquement

Crée un ticket Linear structuré à partir d'une description simple.

## Workflow automatique

1. **Analyser** la demande utilisateur
2. **Classifier** le type (feat/fix/chore/docs)
3. **Évaluer** la priorité
4. **Générer** titre et description structurés
5. **Créer** le ticket via MCP Linear
6. **Retourner** l'URL

## Format généré

```markdown
## Description
[Contexte et objectif]

## Tâches
- [ ] Tâche 1
- [ ] Tâche 2

## Critères d'acceptation
- [ ] Critère 1
- [ ] Critère 2

## Fichiers impactés
- `path/to/file.ts`
```

## Argument

Description en langage naturel de ce qu'il faut faire.

## Exemple

```
/ticket Ajouter un bouton de partage sur les prédictions
```

Crée automatiquement:
- Titre: `feat(frontend): add share button to predictions`
- Priority: Medium
- Labels: Feature
