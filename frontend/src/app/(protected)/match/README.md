# Page de Détail du Match

## Vue d'ensemble

La page de détail du match (`/match/[id]`) affiche les informations complètes d'un match de football avec des prédictions détaillées, une analyse des facteurs clés et les statistiques historiques.

## Architecture

### Structure des fichiers

```
/match
  └── [id]
      └── page.tsx      # Page principale avec tous les composants
```

### Composants principaux

#### 1. **MatchHeader**
Affiche l'en-tête du match avec:
- Équipes (domicile et extérieur)
- Date et heure du match
- Compétition et journée
- Statut du match (à venir, en direct, terminé, reporté)

```tsx
<MatchHeader match={match} />
```

#### 2. **PredictionSection**
Affiche la prédiction principale avec:
- Probabilités en barres visuelles (domicile/nul/extérieur)
- Confiance de la prédiction (%)
- Recommandation de pari avec score de valeur
- Buts attendus (xG) pour chaque équipe
- Explication textuelle de la prédiction

```tsx
<PredictionSection prediction={prediction} />
```

#### 3. **KeyFactorsSection**
Liste les facteurs clés influençant la prédiction:
- Facteurs positifs (points forts)
- Facteurs de risque (points faibles)

```tsx
<KeyFactorsSection prediction={prediction} />
```

#### 4. **TeamFormSection**
Affiche la forme récente des deux équipes:
- 5 derniers matchs avec résultats
- Statistiques sur les 5 derniers matchs
  - Points
  - Buts marqués/encaissés par match
  - Matchs sans encaisser
  - xG (expected goals) si disponibles

```tsx
<TeamFormCard form={homeForm} isHome={true} />
<TeamFormCard form={awayForm} isHome={false} />
```

#### 5. **HeadToHeadSection**
Historique complet entre les deux équipes:
- Nombre de victoires domicile/nul/extérieur
- 5 derniers matchs directs avec résultats
- Barre latérale collante (sticky) pour accès rapide

```tsx
<HeadToHeadSection
  headToHead={headToHead}
  homeTeam={match.homeTeam}
  awayTeam={match.awayTeam}
/>
```

#### 6. **ModelContributionsSection**
Détail des contributions de chaque modèle:
- Poisson (probabilités)
- ELO (rating)
- xG (expected goals)
- XGBoost (machine learning)
- Poids de chaque modèle dans la prédiction finale

```tsx
<ModelContributionsCard
  modelName={modelName}
  contribution={contribution}
/>
```

#### 7. **LLMAdjustmentsSection**
Ajustements appliqués par l'IA:
- Impact des blessures (domicile/extérieur)
- Sentiment des analystes
- Avantage tactique
- Ajustement total
- Explication du raisonnement

```tsx
<AdjustmentCard
  label="Impact Blessures (Domicile)"
  value={adjustments.injuryImpactHome}
  color="orange"
/>
```

#### 8. **ProbabilityBar**
Barre de probabilité visuelle avec:
- Label et pourcentage
- Remplissage proportionnel
- Couleurs différentes par type de pari
- Mise en évidence du pari recommandé

```tsx
<ProbabilityBar
  label="Victoire Domicile"
  probability={prediction.homeProb}
  isRecommended={prediction.recommendedBet === "home"}
  color="primary"
/>
```

## Données et API

### Sources de données

#### Requêtes API
```typescript
// Match details
const match = await fetchMatch(matchId);

// Detailed prediction
const prediction = await fetchPrediction(matchId, true);

// Team form (5 derniers matchs)
const homeForm = await fetchTeamForm(homeTeamId, 5);
const awayForm = await fetchTeamForm(awayTeamId, 5);

// Head-to-head history
const headToHead = await fetchHeadToHead(matchId, 10);
```

### Mode Mock Data

Pour développer sans backend, activez les données mock:

1. **Créer un fichier `.env.local`**:
```bash
NEXT_PUBLIC_USE_MOCK_DATA=true
```

2. **Les données mock incluent**:
- Un match complet: Manchester United vs Liverpool
- Prédiction détaillée avec tous les modèles
- Forme récente pour les 2 équipes
- Historique head-to-head
- Matches à venir

#### Structure des données mock

```typescript
// /lib/mockData.ts

mockMatch: Match
mockPrediction: DetailedPrediction
mockHomeTeamForm: TeamForm
mockAwayTeamForm: TeamForm
mockHeadToHead: HeadToHeadData
mockUpcomingMatches: Match[]
```

## Design et Thème

### Palette de couleurs

- **Primary (Vert)**: Victoires domicile, points positifs
- **Accent (Bleu)**: Victoires extérieur
- **Yellow**: Matchs nuls, attention
- **Orange**: Facteurs de risque
- **Dark**: Fond et textes secondaires

### Composants visuels

#### Classes Tailwind personnalisées

```css
/* Couleurs dark */
bg-dark-800/50        /* Fond semi-transparent */
bg-dark-700/50
border-dark-700

/* Couleurs semantiques */
bg-primary-500/10     /* Fond très transparent */
text-primary-400      /* Texte principal */

/* États */
border-primary-500/30 /* Bordure avec transparence */
animate-pulse         /* Animation pour "EN DIRECT" */
```

### Mise en page

- **Layout principal**: 2 colonnes sur desktop, 1 colonne sur mobile
  - Colonne gauche (2/3): Prédiction, facteurs, forme
  - Colonne droite (1/3): Head-to-head (sticky)

- **Breakpoints**:
  - Mobile: < 768px (md)
  - Tablet: >= 768px et < 1024px
  - Desktop: >= 1024px (lg)

## États de chargement

### LoadingState
Affiche des skeletons animés pendant le chargement:
- En-tête du match
- 3 sections principales
- Sidebar head-to-head

```tsx
function LoadingState() {
  return <div className="animate-pulse">...</div>;
}
```

## Gestion des erreurs

### Cas d'erreur
- Match non trouvé
- API indisponible
- Données manquantes

```tsx
if (matchError || !match) {
  return (
    <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30">
      <AlertTriangle className="w-5 h-5 text-red-400" />
      <p className="text-red-300">Impossible de charger les details du match.</p>
    </div>
  );
}
```

## Icônes

Utilise la bibliothèque **Lucide React**:
- `Target`: Prédiction
- `BarChart3`: Statistiques
- `TrendingUp`: Forme récente
- `Users`: Head-to-head
- `Trophy`: Compétition
- `Clock`: Date/heure
- `CheckCircle`: Recommandation
- `AlertTriangle`: Erreurs/risques

## Types TypeScript

### Match
```typescript
interface Match {
  id: number;
  homeTeam: string;
  awayTeam: string;
  competition: string;
  competitionCode: string;
  matchDate: string;
  status: "scheduled" | "live" | "finished" | "postponed";
  homeScore?: number;
  awayScore?: number;
  matchday?: number;
}
```

### DetailedPrediction
```typescript
interface DetailedPrediction {
  homeProb: number;
  drawProb: number;
  awayProb: number;
  recommendedBet: "home" | "draw" | "away";
  confidence: number;
  valueScore: number;
  explanation: string;
  keyFactors: string[];
  riskFactors: string[];
  modelContributions?: {...};
  llmAdjustments?: {...};
  expectedHomeGoals: number;
  expectedAwayGoals: number;
  createdAt: string;
}
```

### TeamForm
```typescript
interface TeamForm {
  teamId: number;
  teamName: string;
  lastMatches: Match[];
  formString: string;      // Ex: "VDVVD" (V=victoire, D=défaite, N=nul)
  pointsLast5: number;
  goalsScoredAvg: number;
  goalsConcededAvg: number;
  cleanSheets: number;
  xgForAvg?: number;
  xgAgainstAvg?: number;
}
```

## Fonctionnalités principales

### 1. Prédictions visuelles
- Barres de probabilité proportionnelles
- Confiance en pourcentage
- Score de valeur du pari

### 2. Analyse approfondie
- Facteurs clés positifs et négatifs
- Contributions de 4 modèles différents
- Ajustements IA avec raisonnement

### 3. Contexte historique
- Forme récente (5 derniers matchs)
- Statistiques détaillées par équipe
- Head-to-head sur plusieurs saisons

### 4. Responsive design
- Optimisé pour tous les appareils
- Sticky sidebar sur desktop
- Layout adaptable sur mobile

## Développement

### Ajouter un nouvel élément de prédiction

1. Ajouter le champ à `DetailedPrediction` dans `/lib/types.ts`
2. Ajouter aux données mock dans `/lib/mockData.ts`
3. Créer une nouvelle section composant:

```tsx
function NewFactorSection({ prediction }: { prediction: DetailedPrediction }) {
  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
      <h3 className="text-xl font-bold text-white">
        Nouveau Facteur
      </h3>
      {/* Contenu */}
    </div>
  );
}
```

4. Ajouter au rendu principal dans `MatchDetailPage`

### Tester avec mock data

```bash
# .env.local
NEXT_PUBLIC_USE_MOCK_DATA=true
npm run dev
```

Puis naviguer à `/match/1`

### Passer à l'API réelle

1. S'assurer que le backend est en cours d'exécution
2. Dans `.env.local`:
```
NEXT_PUBLIC_USE_MOCK_DATA=false
NEXT_PUBLIC_API_URL=http://localhost:8000
```
3. Redémarrer le serveur de développement

## Performance

### Optimisations
- Lazy loading des requêtes en utilisant `enabled` dans React Query
- Génération de Team IDs avec hash (équipe domicile/extérieur séparées)
- Sticky sidebar pour meilleure navigation
- Skeletons pendant le chargement

### Temps de chargement

- Match: ~300ms (mock)
- Prédiction: ~300ms (mock)
- Forme équipe: ~300ms par équipe (mock)
- Head-to-head: ~300ms (mock)

## Dépannage

### Le match n'apparaît pas
- Vérifier l'ID du match dans l'URL
- Vérifier que l'API retourne le match
- Vérifier les logs dans la console

### Les prédictions sont nulles
- Vérifier que `fetchPrediction` retourne les données
- Vérifier le format de `DetailedPrediction`
- En mock mode: vérifier `NEXT_PUBLIC_USE_MOCK_DATA=true`

### Layout cassé
- Vérifier que Tailwind est compilé
- Vérifier les classes Tailwind dans `tailwind.config.ts`
- Vérifier la configuration dark theme

## Liens utiles

- [Fichier principal](/frontend/src/app/match/[id]/page.tsx)
- [Types TypeScript](/frontend/src/lib/types.ts)
- [Mock Data](/frontend/src/lib/mockData.ts)
- [API Client](/frontend/src/lib/api.ts)
- [Configuration Tailwind](/frontend/tailwind.config.ts)
