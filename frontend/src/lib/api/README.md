# API Client Généré avec Orval

Ce dossier contient le client TypeScript généré automatiquement par Orval à partir de l'API FastAPI.

## Structure

- `custom-instance.ts` - Configurateur HTTP personnalisé pour les requêtes
- `endpoints/` - Hooks React Query pour chaque endpoint de l'API
  - `bets/` - Opérations de paris
  - `matches/` - Opérations de matchs
- `models/` - Types TypeScript générés automatiquement

## Utilisation

### Hooks React Query

Les hooks sont générés automatiquement et incluent la gestion du caching et la réactivité.

#### Récupérer une liste de paris

```typescript
import { useListBets } from '@/lib/api';

export function BetsList() {
  const { data, isLoading, error } = useListBets();

  if (isLoading) return <div>Chargement...</div>;
  if (error) return <div>Erreur: {error.message}</div>;

  return (
    <ul>
      {data?.data.map(bet => (
        <li key={bet.id}>{bet.id}</li>
      ))}
    </ul>
  );
}
```

#### Récupérer un pari spécifique

```typescript
import { useGetBet } from '@/lib/api';

export function BetDetail({ betId }: { betId: string }) {
  const { data, isLoading } = useGetBet(betId);

  if (isLoading) return <div>Chargement...</div>;

  return <div>{data?.data.prediction}</div>;
}
```

#### Créer un nouveau pari

```typescript
import { useCreateBet } from '@/lib/api';
import type { BetCreate } from '@/lib/api';

export function CreateBetForm() {
  const { mutate, isPending } = useCreateBet();

  const handleSubmit = (betData: BetCreate) => {
    mutate({ data: betData });
  };

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      handleSubmit({
        match_id: 'match-123',
        prediction: 'home_win',
        amount: 50,
      });
    }}>
      {/* Formulaire */}
      <button disabled={isPending}>
        {isPending ? 'Création...' : 'Créer un pari'}
      </button>
    </form>
  );
}
```

## Types TypeScript

Tous les types sont disponibles via:

```typescript
import type {
  Match,
  Bet,
  BetCreate,
  Odds,
  MatchStatus,
  BetStatus,
} from '@/lib/api';
```

## Régénération du Client

Pour régénérer le client après une mise à jour de l'API:

```bash
npm run generate:api
```

## Configuration

La configuration Orval se trouve dans `orval.config.ts` à la racine du projet.

La requête HTTP utilise le `customInstance` défini dans `custom-instance.ts` qui:
- Ajoute l'URL de base de l'API
- Configure les en-têtes par défaut
- Gère les erreurs

Vous pouvez configurer l'URL de base via la variable d'environnement:

```
NEXT_PUBLIC_API_URL=https://paris-sportif-api.onrender.com
```
