# /fix-suggestions - Appliquer les suggestions de review

Récupère et applique automatiquement les suggestions du bot claude-review sur une PR.

## Instructions

1. **Récupérer les commentaires** de la PR via `gh api repos/jdvot/paris-sportif/pulls/{PR}/comments`
2. **Filtrer les suggestions** du bot claude-review
3. **Analyser chaque suggestion**:
   - Identifier le fichier et la ligne concernés
   - Comprendre la correction demandée
   - Évaluer si la suggestion est pertinente
4. **Appliquer les corrections** automatiquement
5. **Commit et push** les changements
6. **Répondre aux commentaires** si nécessaire

## Types de suggestions gérées

- ✅ Erreurs de lint/format
- ✅ Types manquants
- ✅ Imports inutilisés
- ✅ Nommage incorrect
- ✅ Code dupliqué
- ✅ Améliorations de performance
- ⚠️ Changements d'architecture (demander confirmation)

## Argument

Numéro de la PR: `9` ou URL complète
