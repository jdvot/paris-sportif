# Orval - Génération API Client

Orval génère automatiquement les hooks React Query et types TypeScript à partir du schéma OpenAPI du backend.

## Comment ça marche

```
Backend (FastAPI) → openapi.json → Orval → React Query hooks + Types
```

1. FastAPI expose `/openapi.json` automatiquement
2. On copie ce fichier dans `frontend/openapi.json`
3. Orval génère le code dans `frontend/src/lib/api/`

## Régénérer l'API client

### Étape 1: Récupérer le schéma OpenAPI

```bash
# Backend doit tourner
cd backend && uv run uvicorn src.api.main:app --reload

# Dans un autre terminal, télécharger le schéma
curl http://localhost:8000/openapi.json > frontend/openapi.json
```

### Étape 2: Générer les hooks

```bash
cd frontend
npm run generate:api
```

Cela génère:
- `src/lib/api/endpoints/` - Hooks React Query par tag
- `src/lib/api/models/` - Types TypeScript

## Structure générée

```
frontend/src/lib/api/
├── endpoints/
│   ├── matches/matches.ts    # useGetMatches, useGetMatchById, etc.
│   ├── predictions/predictions.ts
│   ├── bets/bets.ts
│   └── ...
├── models/
│   ├── matchResponse.ts      # Types des réponses
│   ├── predictionResponse.ts
│   └── index.ts              # Export centralisé
├── custom-instance.ts        # Fetch wrapper (auth, errors)
└── index.ts                  # Export principal
```

## Utilisation des hooks

```tsx
import { useGetMatches, useGetPredictionStats } from "@/lib/api";

function MyComponent() {
  // GET request avec React Query
  const { data, isLoading, error } = useGetMatches({
    competition: "PL",
    days: 7
  });

  // Les données sont typées automatiquement
  const matches = data?.data; // MatchResponse[]
}
```

## Configuration Orval

Fichier `frontend/orval.config.ts`:

```typescript
export default defineConfig({
  parisportif: {
    input: {
      target: './openapi.json',  // Schéma source
    },
    output: {
      mode: 'tags-split',        // Un fichier par tag API
      target: 'src/lib/api/endpoints',
      schemas: 'src/lib/api/models',
      client: 'react-query',     // Génère des hooks React Query
      httpClient: 'fetch',
      override: {
        mutator: {
          path: './src/lib/api/custom-instance.ts',
          name: 'customInstance',  // Notre fetch wrapper
        },
      },
    },
  },
});
```

## Custom Instance

Le fichier `custom-instance.ts` gère:
- **Base URL** - Relative en browser, absolue côté serveur
- **Auth** - Ajoute le token Supabase automatiquement
- **Erreurs** - Classe `ApiError` avec status code
- **Params** - Conversion des query params

```typescript
// Exemple d'utilisation interne
const response = await customInstance<MatchResponse[]>('/api/v1/matches', {
  params: { competition: 'PL' }
});
```

## Workflow après modification API

1. **Modifier le backend** (routes, modèles Pydantic)
2. **Redémarrer le backend** pour mettre à jour `/openapi.json`
3. **Télécharger le nouveau schéma**:
   ```bash
   curl http://localhost:8000/openapi.json > frontend/openapi.json
   ```
4. **Régénérer**:
   ```bash
   cd frontend && npm run generate:api
   ```
5. **Vérifier les types** - TypeScript détectera les breaking changes

## Bonnes pratiques

- **Ne jamais modifier** les fichiers dans `endpoints/` ou `models/` - ils seront écrasés
- **Personnaliser** uniquement `custom-instance.ts`
- **Hooks custom** dans `src/hooks/` si besoin de logique spécifique
- **Commit** `openapi.json` pour garder la version du schéma

## Debugging

```bash
# Voir le schéma OpenAPI brut
curl http://localhost:8000/openapi.json | jq .

# Vérifier un endpoint spécifique
curl http://localhost:8000/openapi.json | jq '.paths["/api/v1/matches"]'
```
