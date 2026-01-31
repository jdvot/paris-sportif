# Exemple d'intégration - Page de détail du match

## Comment ajouter un lien vers la page de détail dans d'autres composants

### Depuis DailyPicks.tsx

```tsx
import Link from 'next/link';

function PickCard({ pick }: { pick: DailyPick }) {
  const { match, prediction } = pick;

  return (
    <Link href={`/match/${match.id}`}>
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden hover:border-dark-600 transition-colors cursor-pointer">
        {/* Contenu existant */}
      </div>
    </Link>
  );
}
```

### Depuis UpcomingMatches.tsx

```tsx
import Link from 'next/link';

function MatchItem({ match }: { match: Match }) {
  return (
    <Link href={`/match/${match.id}`} className="hover:opacity-80 transition-opacity">
      <div className="flex items-center justify-between p-4">
        <div>
          <h3 className="font-semibold text-white">
            {match.homeTeam} vs {match.awayTeam}
          </h3>
        </div>
      </div>
    </Link>
  );
}
```

## Structure de navigation

```
HOME (/)
├── Daily Picks
│   └── → /match/[id]  (Click sur un pick)
├── Upcoming Matches
│   └── → /match/[id]  (Click sur un match)
└── Matches Archive
    └── → /match/[id]  (Click sur un match)

MATCH DETAIL (/match/[id])
├── Match Header
├── Prediction & Probabilities
├── Key Factors
├── Team Form (5 derniers matchs)
├── Head-to-Head (10 derniers matchs)
├── Model Contributions (optionnel)
└── LLM Adjustments (optionnel)
```

## Types de données nécessaires

La page fonctionne avec les types suivants:

```typescript
// Types requis
Match
DetailedPrediction
TeamForm
HeadToHead

// Types optionnels
DetailedPrediction.modelContributions
DetailedPrediction.llmAdjustments
TeamForm.xgForAvg
TeamForm.xgAgainstAvg
DailyPick.riskFactors
```

## Exemple complet d'un lien cliquable

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { fetchDailyPicks } from '@/lib/api';
import type { DailyPick } from '@/lib/types';

export function DailyPicksWithLinks() {
  const { data: picks = [] } = useQuery({
    queryKey: ['dailyPicks'],
    queryFn: () => fetchDailyPicks(),
  });

  return (
    <div className="grid gap-4">
      {picks.map((pick) => (
        <Link
          key={pick.match.id}
          href={`/match/${pick.match.id}`}
          className="block hover:opacity-80 transition-opacity"
        >
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
            <h3 className="font-semibold text-white">
              {pick.match.homeTeam} vs {pick.match.awayTeam}
            </h3>
            <p className="text-dark-400">
              Chance: {Math.round(pick.prediction.confidence * 100)}%
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}
```

## Données retournées par chaque API

### fetchMatch(id)
```typescript
{
  id: number;
  homeTeam: string;
  awayTeam: string;
  competition: string;
  competitionCode: string;
  matchDate: string;  // ISO 8601
  status: "scheduled" | "live" | "finished" | "postponed";
  homeScore?: number;
  awayScore?: number;
  matchday?: number;
}
```

### fetchPrediction(id, includeModelDetails)
```typescript
{
  homeProb: number;           // 0-1
  drawProb: number;           // 0-1
  awayProb: number;           // 0-1
  recommendedBet: "home" | "draw" | "away";
  confidence: number;         // 0-1
  valueScore: number;         // 0-1
  explanation: string;
  keyFactors: string[];
  riskFactors: string[];
  expectedHomeGoals: number;
  expectedAwayGoals: number;
  createdAt: string;
  modelContributions?: {      // Optionnel
    poisson: ModelContribution;
    elo: ModelContribution;
    xg?: ModelContribution;
    xgboost?: ModelContribution;
  };
  llmAdjustments?: {          // Optionnel
    injuryImpactHome: number;
    injuryImpactAway: number;
    sentimentHome: number;
    sentimentAway: number;
    tacticalEdge: number;
    totalAdjustment: number;
    reasoning: string;
  };
}
```

### fetchHeadToHead(id, limit)
```typescript
{
  matches: Match[];
  homeWins: number;
  draws: number;
  awayWins: number;
}
```

### fetchTeamForm(teamId, matchesCount)
```typescript
{
  teamId: number;
  teamName: string;
  lastMatches: Match[];
  formString: string;           // "VVDVD" (V=victoire, D=défaite, N=nul)
  pointsLast5: number;
  goalsScoredAvg: number;
  goalsConcededAvg: number;
  cleanSheets: number;
  xgForAvg?: number;            // Optionnel
  xgAgainstAvg?: number;        // Optionnel
}
```

## Scénarios d'usage

### 1. Afficher un bouton "Voir les détails"

```tsx
<button
  onClick={() => router.push(`/match/${match.id}`)}
  className="px-4 py-2 bg-primary-500 hover:bg-primary-600 rounded-lg text-white"
>
  Voir les détails
</button>
```

### 2. Afficher la prédiction en preview cliquable

```tsx
<Link href={`/match/${match.id}`}>
  <div className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors">
    <div className="flex items-center justify-between">
      <span className="font-semibold">{match.homeTeam} vs {match.awayTeam}</span>
      <span className="text-primary-400">
        {Math.round(prediction.homeProb * 100)}% victoire domicile
      </span>
    </div>
  </div>
</Link>
```

### 3. Breadcrumb navigation

```tsx
<nav className="text-sm text-dark-400">
  <Link href="/" className="hover:text-white">Home</Link>
  <span className="mx-2">/</span>
  <Link href="/matches" className="hover:text-white">Matches</Link>
  <span className="mx-2">/</span>
  <span className="text-white">{match.homeTeam} vs {match.awayTeam}</span>
</nav>
```

## Performance

- La page utilise React Query pour le cache automatique
- Les données sont refetchées à l'intervalle par défaut (5 minutes)
- Les skeletons offrent une bonne perception de performance
- Les images sont lazy-loadées automatiquement par Next.js

## Sécurité

- Les données sont échappées automatiquement par React
- Pas d'injection SQL possible (URLs paramétrées)
- Pas d'XSS possible (contenu utilisateur échappé)
- Validation des types TypeScript au build time

## Débogage

Pour déboguer la page, vous pouvez:

1. **Vérifier les erreurs de fetch**
   ```tsx
   if (matchError) console.log('Match Error:', matchError);
   ```

2. **Vérifier les données retournées**
   ```tsx
   useEffect(() => {
     console.log('Match:', match);
     console.log('Prediction:', prediction);
   }, [match, prediction]);
   ```

3. **Vérifier les requêtes réseau**
   - Ouvrir DevTools > Network
   - Chercher les endpoints `/api/v1/matches/*`

## Tests manuels suggérés

1. Cliquer sur un pick depuis la page d'accueil
2. Vérifier l'affichage du match avec tous les détails
3. Cliquer sur le bouton retour
4. Accéder directement à `/match/1` via l'URL
5. Vérifier le rendu sur mobile (responsive)
6. Vérifier avec données partielles (sans xG, sans LLM adjustments)

## Prochaines étapes

1. Ajouter des tests unitaires
2. Implémenter des partages réseaux sociaux
3. Ajouter un système de notation des prédictions
4. Implémenter un export PDF de la prédiction
5. Ajouter un système de notifications
