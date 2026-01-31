# Guide de Démarrage Rapide - Mode Mock Data

Ce guide explique comment utiliser la page de détail du match avec les données mock, sans avoir besoin de backend.

## Installation rapide

### 1. Configuration d'environnement

Créez un fichier `.env.local` à la racine du dossier `frontend`:

```bash
cd /sessions/laughing-sharp-hawking/mnt/paris-sportif/frontend
cp .env.local.example .env.local
```

Editez le fichier `.env.local`:

```env
# Backend API URL (non utilisée en mode mock)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Activer les données mock pour le développement
NEXT_PUBLIC_USE_MOCK_DATA=true
```

### 2. Installation des dépendances

```bash
npm install
```

### 3. Lancer le serveur de développement

```bash
npm run dev
```

### 4. Accéder à la page

Ouvrez votre navigateur et allez à:

```
http://localhost:3000/match/1
```

## Données mock disponibles

### Match principal
- **ID**: 1
- **Équipes**: Manchester United vs Liverpool
- **Compétition**: Premier League (Journée 20)
- **Date**: Demain à 20:00
- **Statut**: A venir

### Prédiction complète
- **Probabilités**: Home 48%, Draw 28%, Away 24%
- **Confiance**: 72%
- **Recommandation**: Victoire domicile
- **Score de valeur**: +15%
- **xG attendus**: Home 2.30, Away 1.80
- **Modèles**: Poisson, ELO, xG, XGBoost
- **Ajustements IA**: Blessures, sentiment, tactique

### Forme récente
- **Manchester United**: VVVVV (15 pts sur 5 matchs)
  - Buts marqués: 2.6/match
  - Buts encaissés: 0.4/match
  - Clean sheets: 4
  - xG pour: 2.45, contre: 0.85

- **Liverpool**: VDVDV (11 pts sur 5 matchs)
  - Buts marqués: 2.2/match
  - Buts encaissés: 0.8/match
  - Clean sheets: 1
  - xG pour: 2.15, contre: 1.20

### Head-to-Head
- 5 derniers matchs directs
- Statistiques historiques
  - Victoires United: 3
  - Matchs nuls: 2
  - Victoires Liverpool: 2

### Autres matchs
Disponibles via `/match/2`, `/match/3`, `/match/4`:
- Manchester City vs Arsenal (PL)
- Real Madrid vs Barcelona (La Liga)
- Paris Saint-Germain vs Marseille (Ligue 1)

## Utilisation en développement

### Visualiser la page

```bash
# Terminal 1: Lancer le serveur
npm run dev

# Terminal 2: Ouvrir le navigateur
open http://localhost:3000/match/1
```

### Éditer les données mock

Modifiez `/lib/mockData.ts` pour changer les données:

```typescript
// Exemple: Changer la confiance de la prédiction
export const mockPrediction: DetailedPrediction = {
  // ...
  confidence: 0.85,  // Augmenter de 72% à 85%
  // ...
};
```

Les changements seront rechargés automatiquement grâce au hot-reload Next.js.

### Tester différents IDs de match

Essayez d'accéder à différents IDs:

```
http://localhost:3000/match/1    # Manchester United vs Liverpool
http://localhost:3000/match/2    # Manchester City vs Arsenal
http://localhost:3000/match/3    # Real Madrid vs Barcelona
http://localhost:3000/match/4    # PSG vs Marseille
http://localhost:3000/match/100  # ID inexistant (utilise Manchester United)
```

## Structure des données mock

### Fichier principal: `/lib/mockData.ts`

```typescript
// Match
mockMatch: Match

// Prédiction avec tous les détails
mockPrediction: DetailedPrediction

// Forme des équipes
mockHomeTeamForm: TeamForm
mockAwayTeamForm: TeamForm

// Historique entre équipes
mockHeadToHead: {
  matches: Match[]
  homeWins: number
  draws: number
  awayWins: number
}

// Liste de matchs à venir
mockUpcomingMatches: Match[]

// Fonctions d'accès
getMockMatchById(id: number): Match
useMockData(): boolean
```

### Modifier les prédictions

```typescript
// /lib/mockData.ts

export const mockPrediction: DetailedPrediction = {
  homeProb: 0.48,           // Probabilité victoire domicile
  drawProb: 0.28,           // Probabilité nul
  awayProb: 0.24,           // Probabilité victoire extérieur
  recommendedBet: "home",   // "home" | "draw" | "away"
  confidence: 0.72,         // 0-1 (0-100%)
  valueScore: 0.15,         // Valeur du pari +15%

  explanation: "...",       // Texte d'explication
  keyFactors: [...],        // Liste des facteurs positifs
  riskFactors: [...],       // Liste des risques

  expectedHomeGoals: 2.3,   // xG domicile
  expectedAwayGoals: 1.8,   // xG extérieur

  modelContributions: {
    poisson: { ... },       // Contribution Poisson
    elo: { ... },           // Contribution ELO
    xg: { ... },            // Contribution xG
    xgboost: { ... },       // Contribution XGBoost
  },

  llmAdjustments: {
    injuryImpactHome: -0.02,
    injuryImpactAway: -0.04,
    sentimentHome: 0.03,
    sentimentAway: -0.02,
    tacticalEdge: 0.04,
    totalAdjustment: 0.05,
    reasoning: "...",
  },

  createdAt: new Date().toISOString(),
};
```

### Ajouter un nouveau match

```typescript
// /lib/mockData.ts

export const mockNewMatch: Match = {
  id: 5,
  homeTeam: "Bayern Munich",
  awayTeam: "Borussia Dortmund",
  competition: "Bundesliga",
  competitionCode: "BL",
  matchDate: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
  status: "scheduled",
  matchday: 18,
};

// Puis modifiez getMockMatchById:
export function getMockMatchById(id: number): Match {
  const matches = [mockMatch, mockNewMatch, ...mockUpcomingMatches];
  return matches.find((m) => m.id === id) || mockMatch;
}
```

## Passage au backend réel

Quand vous êtes prêt à passer au backend:

### 1. Arrêter le serveur
```bash
Ctrl + C
```

### 2. Modifier `.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK_DATA=false
```

### 3. Démarrer le backend
```bash
# Dans un autre terminal
cd backend
python -m uvicorn main:app --reload
```

### 4. Relancer Next.js
```bash
npm run dev
```

## Dépannage

### Le page affiche "Impossible de charger les détails du match"

**Cause**: Les données mock ne sont pas activées ou chargement API échoue

**Solution**:
```env
NEXT_PUBLIC_USE_MOCK_DATA=true
```

### Le styling du dark theme ne s'applique pas

**Cause**: Tailwind CSS n'a pas recompilé

**Solution**:
```bash
# Redémarrer le serveur
npm run dev
```

### Les icônes ne s'affichent pas

**Cause**: Lucide React n'est pas installé

**Solution**:
```bash
npm install lucide-react
```

### Le layout est cassé sur mobile

**Cause**: Tailwind responsive classes non compilées

**Solution**:
```bash
# Vérifier tailwind.config.ts
npm install -D tailwindcss
npm run dev
```

## Exemples de personnalisation

### Changer les couleurs du thème

Modifiez `tailwind.config.ts`:

```typescript
const config: Config = {
  theme: {
    extend: {
      colors: {
        primary: {
          400: "#ff6b6b",  // Changer de vert à rouge
          500: "#ee5a52",
          // ...
        },
        // ...
      },
    },
  },
};
```

### Ajouter plus d'informations à la prédiction

```typescript
// /lib/types.ts

export interface DetailedPrediction extends Prediction {
  // ... existing fields
  injuryNews?: string;           // Nouvelles blessures
  weatherConditions?: string;    // Conditions météo
  refereeName?: string;          // Arbitre du match
  // ...
}
```

Puis ajouter aux mock data:

```typescript
// /lib/mockData.ts

export const mockPrediction: DetailedPrediction = {
  // ... existing
  injuryNews: "Rashford out for 2 weeks",
  weatherConditions: "Clear, 15°C",
  refereeName: "Paul Tierney",
};
```

Et afficher dans la page:

```typescript
// /match/[id]/page.tsx

function PredictionSection({ prediction }: { prediction: DetailedPrediction }) {
  return (
    <div className="...">
      {/* existing sections */}

      {prediction.injuryNews && (
        <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
          <p className="text-yellow-300">{prediction.injuryNews}</p>
        </div>
      )}
    </div>
  );
}
```

## Performance en mode mock

Les données mock simulent une latence réseau de 300ms pour plus de réalisme:

```typescript
export async function fetchMatch(matchId: number): Promise<Match> {
  if (USE_MOCK_DATA) {
    return new Promise((resolve) =>
      setTimeout(() => resolve(getMockMatchById(matchId)), 300)  // 300ms delay
    );
  }
  // ...
}
```

Pour développer plus vite, vous pouvez réduire le délai:

```typescript
setTimeout(() => resolve(getMockMatchById(matchId)), 50)  // 50ms delay
```

## Fichiers importants

```
frontend/
├── src/
│   ├── app/
│   │   ├── match/
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx          # Page principale
│   │   │   └── README.md             # Documentation détaillée
│   │   └── layout.tsx
│   ├── lib/
│   │   ├── mockData.ts               # Données mock
│   │   ├── api.ts                    # Client API (mock + réel)
│   │   └── types.ts                  # Types TypeScript
│   └── components/
│       └── Header.tsx
├── tailwind.config.ts                 # Thème Tailwind
├── .env.local.example                 # Template d'env
├── GETTING_STARTED_MOCK.md           # Ce fichier
├── MATCH_DETAIL_VISUAL_GUIDE.md      # Guide visuel
└── next.config.ts
```

## Prochaines étapes

1. **Explorez les données**: Modifiez les mock data et observez les changements
2. **Testez le responsive**: Redimensionnez le navigateur pour voir l'adaptation mobile
3. **Ajoutez des sections**: Créez de nouveaux composants basés sur le pattern existant
4. **Connectez au backend**: Passez de `NEXT_PUBLIC_USE_MOCK_DATA=true` à `false`
5. **Déployez**: Buildez et déployez sur Vercel ou votre plateforme

## Liens utiles

- [Documentation complète](/frontend/src/app/match/README.md)
- [Guide visuel](/frontend/MATCH_DETAIL_VISUAL_GUIDE.md)
- [Types TypeScript](/frontend/src/lib/types.ts)
- [Mock Data](/frontend/src/lib/mockData.ts)
- [API Client](/frontend/src/lib/api.ts)

## Support

Pour des questions ou problèmes:

1. Vérifiez la console du navigateur (F12)
2. Vérifiez les logs du serveur terminal
3. Consultez les fichiers README
4. Vérifiez que `.env.local` est correct

Bon développement! 🚀
