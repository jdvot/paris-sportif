# Guide des Agents Claude Code

Ce guide explique comment utiliser et créer des agents spécialisés pour Claude Code dans le projet Paris Sportif.

## Table des Matières

- [Qu'est-ce qu'un Agent Spécialisé?](#quest-ce-quun-agent-spécialisé)
- [Agents Disponibles](#agents-disponibles)
- [Utilisation des Agents](#utilisation-des-agents)
- [Créer un Nouvel Agent](#créer-un-nouvel-agent)
- [Configuration MCP](#configuration-mcp)
- [Bonnes Pratiques](#bonnes-pratiques)
- [Workflows Multi-Agents](#workflows-multi-agents)

---

## Qu'est-ce qu'un Agent Spécialisé?

Un agent spécialisé est une configuration Claude Code optimisée pour un type de tâche spécifique. Il combine:

- **Contexte spécifique** - System prompt adapté au domaine
- **Outils dédiés** - Sélection minimale d'outils pertinents
- **Instructions claires** - Comportement attendu bien défini
- **Exemples de déclenchement** - Quand l'agent doit être utilisé

### Avantages vs Prompts Génériques

| Aspect | Agent Spécialisé | Prompt Générique |
|--------|------------------|------------------|
| Précision | Haute (contexte ciblé) | Variable |
| Autonomie | Peut travailler en background | Interaction requise |
| Cohérence | Comportement prévisible | Dépend du contexte |
| Performance | Optimisé pour la tâche | Overhead possible |

---

## Agents Disponibles

### Agents Système (Built-in)

| Agent | Description | Usage |
|-------|-------------|-------|
| `Explore` | Explorer codebase rapidement | Recherche fichiers, patterns, structure |
| `Plan` | Planifier implémentation | Conception, architecture, trade-offs |
| `Bash` | Exécution commandes shell | Git, npm, docker, scripts |
| `general-purpose` | Tâches multi-étapes | Recherche complexe, refactoring |

### Agents MCP (Model Context Protocol)

| Agent | MCP Server | Usage |
|-------|------------|-------|
| `linear-mcp-expert` | Linear | Créer/gérer tickets, sprints |
| `notion-ticket-creator` | Notion | Créer pages documentation |

---

## Utilisation des Agents

### Via le Task Tool

```
Utilise l'agent Explore pour trouver tous les fichiers qui gèrent l'authentification.
```

Claude lancera automatiquement l'agent approprié.

### Déclenchement Automatique

Les agents peuvent être déclenchés automatiquement selon le contexte:

- **Question sur le code** → Agent Explore
- **Planification feature** → Agent Plan
- **Création ticket Linear** → Agent linear-mcp-expert
- **Documentation Notion** → Agent notion-ticket-creator

### Exécution en Background

```
Lance un agent en background pour analyser tous les endpoints API.
```

L'agent travaille de manière asynchrone et notifie à la fin.

---

## Créer un Nouvel Agent

### 1. Définir le Contexte

Questions à se poser:
- Quel domaine spécifique?
- Quelles tâches récurrentes?
- Quels outils nécessaires?
- Quand doit-il être déclenché?

### 2. Structure de Configuration

Fichier: `.claude/settings.local.json`

```json
{
  "customAgents": [
    {
      "name": "backend-python-expert",
      "description": "Expert Python/FastAPI pour le backend Paris Sportif. Utiliser pour: création endpoints, modèles SQLAlchemy, intégration ML, tests pytest.",
      "systemPrompt": "Tu es un expert Python senior spécialisé en:\n- FastAPI et async Python\n- SQLAlchemy ORM\n- Pydantic validation\n- Tests pytest\n\nContexte projet:\n- Backend dans backend/src/\n- Utilise uv comme package manager\n- Black + isort + ruff pour formatting\n- mypy pour type checking\n\nRègles:\n1. Toujours typer les fonctions\n2. Docstrings Google style\n3. Tests pour chaque nouvelle fonction\n4. Pas de print(), utiliser logging",
      "tools": ["Bash", "Read", "Edit", "Write", "Grep", "Glob"]
    }
  ]
}
```

### 3. Éléments du System Prompt

| Section | Contenu |
|---------|---------|
| **Rôle** | Qui est l'agent, son expertise |
| **Contexte** | Structure projet, conventions |
| **Règles** | Comportements obligatoires/interdits |
| **Format** | Style de réponse attendu |
| **Exemples** | Cas d'usage concrets |

### 4. Sélection des Outils

Principe: **minimum nécessaire**

| Outil | Usage |
|-------|-------|
| `Read` | Lire fichiers |
| `Edit` | Modifier fichiers existants |
| `Write` | Créer nouveaux fichiers |
| `Bash` | Commandes shell |
| `Grep` | Recherche contenu |
| `Glob` | Recherche fichiers par pattern |
| `WebFetch` | Requêtes HTTP |
| `WebSearch` | Recherche web |

### 5. Exemples de Déclenchement

Dans la description de l'agent:

```
"description": "Expert frontend Next.js. Utiliser quand l'utilisateur demande de: créer un composant React, modifier une page, ajouter du styling Tailwind, intégrer un hook React Query."
```

---

## Configuration MCP

### Qu'est-ce que MCP?

MCP (Model Context Protocol) permet à Claude d'interagir avec des services externes (Linear, Notion, GitHub, etc.).

### Configuration (`.claude/settings.local.json`)

```json
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "@anthropic/linear-mcp-server"],
      "env": {
        "LINEAR_API_KEY": "lin_api_xxx"
      }
    },
    "notion": {
      "command": "npx",
      "args": ["-y", "@anthropic/notion-mcp-server"],
      "env": {
        "NOTION_API_KEY": "secret_xxx"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic/github-mcp-server"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx"
      }
    }
  }
}
```

### MCP Servers Utiles

| Server | Usage | Outils fournis |
|--------|-------|----------------|
| **linear** | Gestion projet | create_issue, list_issues, update_issue |
| **notion** | Documentation | create_page, search, update_page |
| **github** | Code review | create_pr, list_prs, add_comment |
| **postgres** | Requêtes DB | query, execute |

---

## Bonnes Pratiques

### DO ✅

- **Un agent = un domaine** - Spécialisation maximale
- **Instructions claires** - Pas d'ambiguïté
- **Outils minimaux** - Éviter le bloat
- **Exemples concrets** - Facilite déclenchement auto
- **Tester** - Valider sur plusieurs cas

### DON'T ❌

- **Agent trop générique** - Perd en efficacité
- **Trop d'outils** - Confusion, lenteur
- **Instructions vagues** - Comportement imprévisible
- **Pas d'exemples** - Déclenchement aléatoire

### Patterns Recommandés

```json
{
  "name": "nom-court-descriptif",
  "description": "Une phrase. Utiliser quand: cas1, cas2, cas3.",
  "systemPrompt": "Rôle en 1 ligne.\n\nContexte:\n- Point 1\n- Point 2\n\nRègles:\n1. Règle 1\n2. Règle 2",
  "tools": ["Read", "Edit"]  // Minimum
}
```

---

## Workflows Multi-Agents

### Feature Development

```
1. Agent Plan     → Analyse et crée ticket Linear
2. Agent Explore  → Identifie fichiers à modifier
3. Agent Backend  → Implémente API
4. Agent Frontend → Implémente UI
5. Agent Bash     → Commit et push
```

### Bug Triage

```
1. Agent Explore  → Analyse l'erreur, trouve root cause
2. Agent Linear   → Crée issue avec contexte
3. Agent Backend  → Propose et implémente fix
4. Agent Bash     → Tests + commit
```

### Documentation

```
1. Agent Explore  → Analyse code à documenter
2. Agent Notion   → Crée page documentation
3. Agent Backend  → Ajoute docstrings au code
```

---

## Liens

- [Architecture du Projet](./ARCHITECTURE.md)
- [Git Workflow](./GIT_WORKFLOW.md)
- [Déploiement](./DEPLOYMENT.md)
- [Linear - Paris Sportif](https://linear.app/paris-sportif)
