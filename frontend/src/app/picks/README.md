# Page Picks (/picks)

## Vue d'ensemble
La page `/picks` affiche tous les picks/prédictions de football avec un système de filtrage avancé par date et compétition.

## Fonctionnalités

### 1. Navigation par Date
- **Sélection de date**: Calendrier interactif pour choisir une date spécifique
- **Navigation fluide**: Boutons "Jour précédent" et "Jour suivant"
- **Affichage du jour de la semaine**: Affiche automatiquement le jour français
- **Limitation**: Impossible d'aller au-delà du jour actuel

### 2. Filtrage par Compétition
- **7 compétitions supportées**:
  - Premier League (PL)
  - La Liga (PD)
  - Bundesliga (BL1)
  - Serie A (SA)
  - Ligue 1 (FL1)
  - Champions League (CL)
  - Europa League (EL)
  
- **Interface collapsible**: Cliquez sur le bouton "Filtres par competition" pour déplier/replier
- **Sélection multiple**: Vous pouvez sélectionner plusieurs compétitions en même temps
- **Reinitialisation**: Bouton pour effacer tous les filtres

### 3. Affichage des Picks
Chaque pick affiche:
- **En-tête**: Rang, équipes, compétition, date et heure du match
- **Statistiques de confiance**: Pourcentage de confiance et score de valeur
- **Probabilités**: Barres graphiques pour chaque issue (victoire domicile, nul, victoire extérieur)
- **Recommandation**: Pari recommandé avec code couleur de confiance
- **Explication**: Description détaillée de l'analyse
- **Points positifs**: Facteurs favorables au pari (badges verts)
- **Risques**: Facteurs défavorables (badges orange)

### 4. Design et Couleurs
- **Thème sombre**: Cohérent avec le reste du site
- **Codes couleur de confiance**:
  - >= 70%: Vert primaire (primary-400)
  - 60-69%: Jaune (yellow-400)
  - < 60%: Orange (orange-400)
  
- **Codes couleur par compétition**:
  - Premier League: Violet (purple-500)
  - La Liga: Orange (orange-500)
  - Bundesliga: Rouge (red-500)
  - Serie A: Bleu (blue-500)
  - Ligue 1: Vert (green-500)
  - Champions League: Indigo (indigo-500)
  - Europa League: Ambre (amber-500)

## Architecture Technique

### Composants
1. **PicksPage**: Composant principal avec gestion de l'état
2. **PickCard**: Affichage d'un pick individuel
3. **ProbBar**: Barre de probabilité graphique

### Hooks React
- `useState`: Gestion de la date sélectionnée, compétitions filtrées, visibilité des filtres
- `useCallback`: Fonction optimisée pour basculer la sélection de compétitions
- `useQuery`: Récupération des picks via React Query avec données mock en fallback

### Dépendances
- `@tanstack/react-query`: Gestion du cache et récupération de données
- `date-fns`: Manipulation et formatage des dates
- `lucide-react`: Icônes
- `@/lib/api`: Client API avec fetchDailyPicks()
- `@/lib/utils`: Utilitaire cn() pour Tailwind CSS

## API

### Fonction fetchDailyPicks
```typescript
export async function fetchDailyPicks(date?: string): Promise<DailyPick[]>
```
- **Paramètre**: date optionnelle au format "yyyy-MM-dd"
- **Retour**: Array de DailyPick
- **Endpoint**: GET /api/v1/predictions/daily?date={date}

## Types Utilisés

### DailyPick
```typescript
interface DailyPick {
  rank: number;
  match: Pick<Match, "id" | "homeTeam" | "awayTeam" | "competition" | "matchDate">;
  prediction: Prediction;
  explanation: string;
  keyFactors: string[];
  riskFactors?: string[];
}
```

### Prediction
```typescript
interface Prediction {
  homeProb: number;
  drawProb: number;
  awayProb: number;
  recommendedBet: "home" | "draw" | "away";
  confidence: number;
  valueScore: number;
}
```

## Données Mock
Incluses 5 picks par défaut pour le développement:
1. Manchester City vs Arsenal (Premier League)
2. Real Madrid vs Barcelona (La Liga)
3. Bayern Munich vs Dortmund (Bundesliga)
4. PSG vs Marseille (Ligue 1)
5. Inter Milan vs Juventus (Serie A)

## Déploiement
- Composant client (use client directive)
- Compatible avec Next.js 13+
- Utilise App Router
- Responsive sur mobile, tablette et desktop

## Améliorations Futures
- Pagination pour les résultats
- Exportation en CSV/PDF
- Historique de performance détaillé
- Comparaison de picks entre deux dates
- Statistiques par compétition
- Intégration avec calendriers de paris
