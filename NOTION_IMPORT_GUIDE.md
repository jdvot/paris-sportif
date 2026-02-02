# Guide: Importer les tickets d'authentification dans Notion

## Option 1: Import Manuel (Recommandé)

### Prérequis
Créer ou identifier votre database Notion avec les propriétés suivantes:

**Propriétés de la Database**:
- **Title** (Text) - Titre du ticket
- **Type** (Select) - Options: Feature, Bug, Refactor, Docs, Test
- **Status** (Select) - Options: Backlog, Todo, In Progress, Done
- **Priority** (Select) - Options: Critical, High, Medium, Low
- **Effort** (Select) - Options: XS, S, M, L, XL (ou story points 1-13)
- **Component** (Multi-select) - Options: Frontend, Backend, Database, Infrastructure, Security, Auth
- **Labels** (Multi-select) - Options: feat, fix, refactor, docs, test, auth, oauth, etc.
- **Assignee** (Person) - À assigner
- **Dependencies** (Relation) - Liens vers autres tickets
- **Blocked By** (Relation) - Tickets bloquants
- **Sprint** (Select) - Sprint 1, Sprint 2, Sprint 3

### Steps d'import

1. **Créer l'Epic**:
   - Créer un ticket parent: "Epic: Système d'Authentification"
   - Type: Epic
   - Priority: Critical
   - Effort: XL

2. **Créer les 6 tickets**:
   Pour chaque ticket dans `AUTHENTICATION_EPIC_TICKETS.md`:

   **Ticket 1**: Setup Supabase Auth
   - Title: `[feat] Setup Supabase Auth - Configuration initiale`
   - Type: Feature
   - Priority: Critical
   - Effort: M
   - Component: Frontend, Infrastructure
   - Labels: feat, auth, setup, supabase, frontend
   - Dependencies: None
   - Sprint: Sprint 1

   **Ticket 2**: Pages d'authentification
   - Title: `[feat] Créer pages Login, Signup et Forgot Password`
   - Type: Feature
   - Priority: Critical
   - Effort: L
   - Component: Frontend, Auth
   - Labels: feat, auth, ui, forms, frontend
   - Dependencies: Ticket 1
   - Blocked By: Ticket 1
   - Sprint: Sprint 1

   **Ticket 3**: Middleware et protection des routes
   - Title: `[feat] Implémenter middleware d'authentification et protection des routes`
   - Type: Feature
   - Priority: Critical
   - Effort: M
   - Component: Frontend, Security
   - Labels: feat, auth, middleware, security, frontend
   - Dependencies: Ticket 1
   - Blocked By: Ticket 1
   - Sprint: Sprint 1

   **Ticket 4**: Profil utilisateur
   - Title: `[feat] Page profil utilisateur avec upload avatar et gestion compte`
   - Type: Feature
   - Priority: High
   - Effort: L
   - Component: Frontend, Backend, Database
   - Labels: feat, profile, storage, database, frontend
   - Dependencies: Ticket 1, Ticket 2
   - Blocked By: Ticket 1, Ticket 2
   - Sprint: Sprint 2

   **Ticket 5**: Backend FastAPI Auth
   - Title: `[feat] Vérification JWT Supabase et protection endpoints FastAPI`
   - Type: Feature
   - Priority: High
   - Effort: M
   - Component: Backend, Security
   - Labels: feat, auth, backend, api, security
   - Dependencies: Ticket 1
   - Blocked By: Ticket 1
   - Sprint: Sprint 2

   **Ticket 6**: OAuth Providers
   - Title: `[feat] Ajouter authentification OAuth Google et GitHub`
   - Type: Feature
   - Priority: Medium
   - Effort: M
   - Component: Frontend, Auth
   - Labels: feat, auth, oauth, enhancement, frontend
   - Dependencies: Ticket 1, Ticket 2, Ticket 4
   - Blocked By: Ticket 1, Ticket 2, Ticket 4
   - Sprint: Sprint 3

3. **Lier les tickets à l'Epic**:
   - Utiliser la propriété "Parent" ou "Epic" pour lier tous les tickets à l'Epic

4. **Copier le contenu détaillé**:
   - Pour chaque ticket, copier/coller le contenu depuis `AUTHENTICATION_EPIC_TICKETS.md`
   - Sections à inclure: Description, Context, Technical Specifications, Acceptance Criteria, Testing Checklist, Resources

---

## Option 2: Import CSV (Plus rapide)

### Créer le fichier CSV

Créer un fichier `auth_tickets.csv` avec ce format:

```csv
Title,Type,Priority,Effort,Component,Labels,Dependencies,Description
"[feat] Setup Supabase Auth - Configuration initiale",Feature,Critical,M,"Frontend,Infrastructure","feat,auth,setup",None,"Mettre en place la configuration initiale de Supabase Auth..."
"[feat] Créer pages Login, Signup et Forgot Password",Feature,Critical,L,"Frontend,Auth","feat,auth,ui",Ticket 1,"Créer les interfaces utilisateur pour l'authentification..."
```

### Importer dans Notion

1. Dans votre database Notion, cliquer sur `⋯` (menu)
2. Sélectionner "Import" → "CSV"
3. Uploader `auth_tickets.csv`
4. Mapper les colonnes CSV aux propriétés Notion
5. Valider l'import

**Limites CSV**:
- Les relations (Dependencies, Blocked By) doivent être créées manuellement après import
- Le contenu détaillé (Acceptance Criteria, etc.) doit être ajouté manuellement

---

## Option 3: API Notion (Automatisation)

### Prérequis
- Créer une Notion Integration: https://www.notion.so/my-integrations
- Récupérer le `NOTION_API_KEY`
- Partager la database avec l'integration

### Script Python

Créer `/backend/scripts/import_tickets_to_notion.py`:

```python
import os
from notion_client import Client

notion = Client(auth=os.environ["NOTION_API_KEY"])
database_id = os.environ["NOTION_DATABASE_ID"]

tickets = [
    {
        "title": "[feat] Setup Supabase Auth - Configuration initiale",
        "type": "Feature",
        "priority": "Critical",
        "effort": "M",
        "components": ["Frontend", "Infrastructure"],
        "labels": ["feat", "auth", "setup", "supabase"],
        "description": "Mettre en place la configuration initiale...",
    },
    # ... autres tickets
]

for ticket in tickets:
    notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "Title": {"title": [{"text": {"content": ticket["title"]}}]},
            "Type": {"select": {"name": ticket["type"]}},
            "Priority": {"select": {"name": ticket["priority"]}},
            "Effort": {"select": {"name": ticket["effort"]}},
            "Component": {"multi_select": [{"name": c} for c in ticket["components"]]},
            "Labels": {"multi_select": [{"name": l} for l in ticket["labels"]]},
        },
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": ticket["description"]}}]
                },
            }
        ],
    )
    print(f"✅ Created: {ticket['title']}")
```

### Exécution
```bash
export NOTION_API_KEY="secret_xxx"
export NOTION_DATABASE_ID="xxx"
cd backend
uv run python scripts/import_tickets_to_notion.py
```

---

## Validation Post-Import

### Checklist
- [ ] Les 6 tickets sont créés dans Notion
- [ ] L'Epic parent existe et lie les 6 tickets
- [ ] Les propriétés sont correctement remplies (Type, Priority, Effort)
- [ ] Les relations "Dependencies" et "Blocked By" sont configurées
- [ ] Le contenu détaillé est présent (Description, Acceptance Criteria, etc.)
- [ ] Les labels sont cohérents
- [ ] Les sprints sont assignés (Sprint 1, 2, 3)

### Vue recommandée (Board)
Créer une vue Kanban dans Notion:
- **Group by**: Status (Backlog, Todo, In Progress, Done)
- **Filter**: Epic = "Système d'Authentification"
- **Sort**: Priority (Critical → Low)

### Vue Timeline
Créer une vue Timeline:
- **Start Date**: Date de début du sprint
- **End Date**: Date estimée de fin
- **Group by**: Sprint

---

## Structure Database Notion recommandée

```
📊 Paris Sportif - Tasks Database
│
├── 🎯 Epics
│   └── Epic: Système d'Authentification
│
├── 📋 Sprint 1 (Semaine 1-2)
│   ├── [feat] Setup Supabase Auth
│   ├── [feat] Pages Login/Signup
│   └── [feat] Middleware protection
│
├── 📋 Sprint 2 (Semaine 3-4)
│   ├── [feat] Profil utilisateur
│   └── [feat] Backend FastAPI Auth
│
└── 📋 Sprint 3 (Semaine 5-6)
    └── [feat] OAuth Providers
```

---

## Templates de propriétés Notion

### Type (Select)
- Epic
- Feature
- Bug
- Refactor
- Docs
- Test
- Chore

### Priority (Select)
- Critical 🔴
- High 🟠
- Medium 🟡
- Low 🟢

### Status (Select)
- Backlog
- Todo
- In Progress
- In Review
- Done
- Blocked

### Effort (Select)
- XS (1-2 pts)
- S (3-5 pts)
- M (5-8 pts)
- L (8-13 pts)
- XL (13+ pts)

### Component (Multi-select)
- Frontend
- Backend
- Database
- Infrastructure
- Security
- Auth
- UI/UX
- API
- Storage

### Labels (Multi-select)
- feat
- fix
- refactor
- docs
- test
- auth
- oauth
- api
- security
- database
- storage
- middleware

---

## Ressources

- **Document source**: `/paris-sportif/AUTHENTICATION_EPIC_TICKETS.md`
- **Notion API Docs**: https://developers.notion.com/
- **Notion CSV Import**: https://www.notion.so/help/import-data-into-notion

---

**Dernière mise à jour**: 2026-02-02
