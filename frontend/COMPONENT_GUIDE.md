# Guide des Composants UX/UI Améliorés

Guide complet pour utiliser les nouveaux composants et animations.

---

## 1. PredictionCardPremium

Affichage premium d'une prédiction de match avec tous les indicateurs visuels optimisés.

### Import
```tsx
import { PredictionCardPremium } from "@/components/PredictionCardPremium";
```

### Utilisation Simple
```tsx
<PredictionCardPremium pick={pick} index={0} isTopPick={true} />
```

### Props Détaillées

```typescript
interface PredictionCardPremiumProps {
  pick: DailyPick;        // Objet pick avec match, prediction, factors
  index?: number;         // Index pour animation staggered (0-5)
  isTopPick?: boolean;    // Affiche badge "Top Pick" + glow effect
}
```

### Comportements Visuels

#### Top Pick Badge
```tsx
<PredictionCardPremium pick={pick} isTopPick={true} />
// Affiche:
// - Badge "🔥 Top Pick" en haut à droite
// - Gradient de couleur special
// - Glow effect
```

#### Confidence Tiers
- **>= 0.75 "Très Haut" 🔥**: Primary color (vert)
- **0.65-0.74 "Haut" ⚡**: Blue color
- **0.55-0.64 "Moyen" ⚠️**: Yellow color
- **< 0.55 "Bas" 📊**: Orange/Red color

#### Staggered Animation
```tsx
{picks.map((pick, index) => (
  <PredictionCardPremium
    key={pick.id}
    pick={pick}
    index={index}  // 0, 1, 2, 3, 4...
  />
))}
// Cards entrent progressivement avec délai
```

### CSS Classes Utilisées

```css
.group                /* Hover parent */
.hover-lift          /* Elevation au survol */
.transition-smooth   /* Transitions fluides */
.animate-stagger-in  /* Entrance animation */
.bg-gradient-to-br   /* Gradient backgrounds */
```

---

## 2. LoadingState

Composant polymorphe pour affichage d'états de chargement contextuels.

### Import
```tsx
import { LoadingState } from "@/components/LoadingState";
```

### Variantes

#### Minimal (Léger)
```tsx
<LoadingState
  variant="minimal"
  message="Chargement..."
/>
```
Usage: Petites zones, transitions rapides

#### Picks (Prédictions)
```tsx
<LoadingState
  variant="picks"
  count={5}
  message="Analyse des matchs en cours..."
/>
```
Usage: Page Picks, liste de prédictions

#### Matches (Matchs)
```tsx
<LoadingState
  variant="matches"
  count={5}
  message="Chargement des matchs..."
/>
```
Usage: Page Matchs, upcoming matches

#### Stats (Statistiques)
```tsx
<LoadingState
  variant="stats"
  message="Chargement des statistiques..."
/>
```
Usage: StatsOverview, graphiques

### Props

```typescript
interface LoadingStateProps {
  variant?: "picks" | "matches" | "stats" | "minimal";
  count?: number;          // Nombre de skeletons (default: 5)
  message?: string;        // Message personnalisé
}
```

### Intégration

```tsx
{isLoading && (
  <LoadingState
    variant="picks"
    count={filteredPicks.length || 5}
    message="Analyse des matchs en cours..."
  />
)}

{!isLoading && filteredPicks.length > 0 && (
  <div className="grid gap-4">
    {/* Contenu réel */}
  </div>
)}
```

---

## 3. CompetitionFilter

Filtre interactif pour sélectionner les compétitions.

### Import
```tsx
import { CompetitionFilter } from "@/components/CompetitionFilter";
```

### Utilisation
```tsx
const [selectedCompetitions, setSelectedCompetitions] = useState<string[]>([]);
const [showFilters, setShowFilters] = useState(false);

<CompetitionFilter
  competitions={COMPETITIONS}
  selected={selectedCompetitions}
  onToggle={(id) => toggleCompetition(id)}
  onClear={() => setSelectedCompetitions([])}
  isOpen={showFilters}
  onToggleOpen={() => setShowFilters(!showFilters)}
/>
```

### Props

```typescript
interface CompetitionFilterProps {
  competitions: Competition[];     // Liste des compétitions
  selected: string[];             // IDs sélectionnés
  onToggle: (id: string) => void; // Callback toggle
  onClear: () => void;            // Callback clear
  isOpen: boolean;                // État du filtre
  onToggleOpen: () => void;       // Toggle ouverture
}

interface Competition {
  id: string;    // "PL", "PD", "BL1", etc.
  name: string;  // "Premier League", etc.
}
```

### Compétitions Pré-configurées

```typescript
const COMPETITIONS = [
  { id: "PL", name: "Premier League" },    // Purple
  { id: "PD", name: "La Liga" },           // Orange
  { id: "BL1", name: "Bundesliga" },       // Red
  { id: "SA", name: "Serie A" },           // Blue
  { id: "FL1", name: "Ligue 1" },          // Green
  { id: "CL", name: "Champions League" },  // Indigo
  { id: "EL", name: "Europa League" },     // Amber
];
```

### Intégration Complète

```tsx
const [selectedCompetitions, setSelectedCompetitions] = useState<string[]>([]);
const [showFilters, setShowFilters] = useState(false);

const toggleCompetition = useCallback((competitionId: string) => {
  setSelectedCompetitions((prev) =>
    prev.includes(competitionId)
      ? prev.filter((c) => c !== competitionId)
      : [...prev, competitionId]
  );
}, []);

// Filtrage
const filteredPicks = picks.filter((pick) => {
  if (selectedCompetitions.length === 0) return true;
  return selectedCompetitions.some(
    (comp) =>
      pick.match.competition.toLowerCase().includes(comp.toLowerCase()) ||
      COMPETITIONS.find(
        (c) => c.id === comp && c.name === pick.match.competition
      )
  );
});

// Rendu
<CompetitionFilter
  competitions={COMPETITIONS}
  selected={selectedCompetitions}
  onToggle={toggleCompetition}
  onClear={() => setSelectedCompetitions([])}
  isOpen={showFilters}
  onToggleOpen={() => setShowFilters(!showFilters)}
/>
```

---

## 4. ConfidenceBadge

Badge affichant le niveau de confiance avec variantes de taille.

### Import
```tsx
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
```

### Tailles

#### Small (Compact)
```tsx
<ConfidenceBadge
  confidence={0.75}
  size="sm"
/>
// Output: "🔥 75%"
```
Usage: Listes, density élevée

#### Medium (Standard)
```tsx
<ConfidenceBadge
  confidence={0.75}
  valueScore={0.12}
  size="md"
  showLabel={true}
/>
```
Usage: Cards, affichage standard

#### Large (Affichage détaillé)
```tsx
<ConfidenceBadge
  confidence={0.75}
  valueScore={0.12}
  size="lg"
  animated={true}
/>
```
Usage: Detail pages, emphasis

### Props

```typescript
interface ConfidenceBadgeProps {
  confidence: number;      // 0-1 (50% = 0.5)
  valueScore?: number;     // Optionnel, 0-1
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;     // Afficher le texte du tier
  animated?: boolean;      // Animations actives
}
```

### Tier Mapping

```
Confidence >= 0.75 → "Très Haut" 🔥 (Primary Green)
Confidence >= 0.65 → "Haut" ⚡ (Blue)
Confidence >= 0.55 → "Moyen" ⚠️ (Yellow)
Confidence < 0.55  → "Bas" 📊 (Orange/Red)
```

### Utilisation dans Cards

```tsx
<div className="flex items-center justify-between">
  <span>Confiance</span>
  <ConfidenceBadge
    confidence={prediction.confidence}
    valueScore={prediction.valueScore}
    size="sm"
  />
</div>
```

---

## 5. Animations Globales

Animations CSS disponibles pour tous les composants.

### Import CSS
```css
/* Automatiquement inclus via globals.css */
@import "app/globals.css";
```

### Classes Disponibles

#### Entrance Animations
```tsx
// Fade + scale
<div className="animate-scale-in">Contenu</div>

// Fade + slide up
<div className="animate-slide-up">Contenu</div>

// Fade in seulement
<div className="animate-fade-in">Contenu</div>
```

#### Stagger Animations
```tsx
{items.map((item, index) => (
  <div key={index} className={`animate-stagger-in animate-stagger-in-${index}`}>
    {item}
  </div>
))}
// Délais: 50ms, 100ms, 150ms, 200ms, 250ms
```

#### Attention Animations
```tsx
// Pulsation subtile (loading indicators)
<div className="animate-pulse-subtle">Indicateur</div>

// Bounce léger (call-to-action)
<div className="animate-bounce-subtle">CTA</div>

// Glow effect (highlights)
<div className="animate-glow border border-primary-500">Important</div>

// Shimmer loading effect
<div className="animate-shimmer bg-gradient-to-r from-dark-700 to-dark-600">
  Placeholder
</div>
```

#### Hover States
```tsx
// Elevation + shadow
<button className="hover-lift">Click me</button>

// Smooth transition
<div className="transition-smooth hover:bg-primary-500">
  Élément
</div>
```

### Keyframes Disponibles

```css
@keyframes fadeIn          /* 0.3s ease-in-out */
@keyframes slideUp         /* 0.3s ease-out */
@keyframes fadeInUp        /* 0.5s ease-out */
@keyframes scaleIn         /* 0.4s cubic-bezier */
@keyframes pulseSubtle     /* 2s infinite */
@keyframes bounceSubtle    /* 2s infinite */
@keyframes glow            /* 2s ease-in-out infinite */
@keyframes shimmer         /* 2s infinite */
```

---

## 6. Intégration Complète - Exemple Page Picks

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import { format, subDays, addDays, parseISO } from "date-fns";
import { fr } from "date-fns/locale";
import { AlertTriangle, Calendar } from "lucide-react";
import { PredictionCardPremium } from "@/components/PredictionCardPremium";
import { LoadingState } from "@/components/LoadingState";
import { CompetitionFilter } from "@/components/CompetitionFilter";
import { fetchDailyPicks } from "@/lib/api";
import type { DailyPick } from "@/lib/types";

const COMPETITIONS = [
  { id: "PL", name: "Premier League" },
  { id: "PD", name: "La Liga" },
  { id: "BL1", name: "Bundesliga" },
  { id: "SA", name: "Serie A" },
  { id: "FL1", name: "Ligue 1" },
  { id: "CL", name: "Champions League" },
  { id: "EL", name: "Europa League" },
];

export default function PicksPage() {
  const [selectedDate, setSelectedDate] = useState<string>(
    format(new Date(), "yyyy-MM-dd")
  );
  const [selectedCompetitions, setSelectedCompetitions] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  const { data: picks = [], isLoading, error } = useQuery({
    queryKey: ["dailyPicks", selectedDate],
    queryFn: () => fetchDailyPicks(selectedDate),
  });

  const filteredPicks = picks.filter((pick) => {
    if (selectedCompetitions.length === 0) return true;
    return selectedCompetitions.some(
      (comp) =>
        pick.match.competition.toLowerCase().includes(comp.toLowerCase())
    );
  });

  const toggleCompetition = useCallback((competitionId: string) => {
    setSelectedCompetitions((prev) =>
      prev.includes(competitionId)
        ? prev.filter((c) => c !== competitionId)
        : [...prev, competitionId]
    );
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="text-center py-8">
        <h1 className="text-4xl font-bold text-white mb-4">
          Tous les Picks
        </h1>
        <p className="text-dark-300">
          Consultez notre analyse complète et suivez les performances
        </p>
      </section>

      {/* Filters */}
      <section className="px-4 sm:px-0">
        <CompetitionFilter
          competitions={COMPETITIONS}
          selected={selectedCompetitions}
          onToggle={toggleCompetition}
          onClear={() => setSelectedCompetitions([])}
          isOpen={showFilters}
          onToggleOpen={() => setShowFilters(!showFilters)}
        />
      </section>

      {/* Loading */}
      {isLoading && (
        <LoadingState
          variant="picks"
          count={5}
          message="Analyse des matchs en cours..."
        />
      )}

      {/* Error */}
      {!isLoading && error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">
            Erreur de chargement
          </h3>
          <p className="text-dark-400">Impossible de charger les picks</p>
        </div>
      )}

      {/* Results */}
      {!isLoading && filteredPicks.length > 0 && (
        <div className="grid gap-4 px-4 sm:px-0">
          {filteredPicks.map((pick, index) => (
            <PredictionCardPremium
              key={pick.rank}
              pick={pick}
              index={index}
              isTopPick={index === 0}
            />
          ))}
        </div>
      )}

      {/* No results */}
      {!isLoading && filteredPicks.length === 0 && (
        <div className="text-center py-12 text-dark-400">
          <p className="text-lg">Aucun pick disponible</p>
        </div>
      )}
    </div>
  );
}
```

---

## 7. Checklist d'Implémentation

Pour ajouter les améliorations UX à d'autres pages:

- [ ] Importer `PredictionCardPremium` pour prédictions
- [ ] Importer `LoadingState` pour états de chargement
- [ ] Importer `CompetitionFilter` pour filtres
- [ ] Importer `ConfidenceBadge` si affichage de confiance
- [ ] Ajouter animations via `animate-*` classes
- [ ] Tester responsive sur mobile (< 640px)
- [ ] Tester dark mode (par défaut)
- [ ] Vérifier performance (Lighthouse)
- [ ] Tester interactions (hover, click, focus)
- [ ] Valider avec utilisateurs

---

## 8. Performance Notes

- Toutes les animations utilisent **CSS natives** (pas JS)
- **Zero dépendances** externes ajoutées
- **Mobile-optimized**: SVG pour badges, media queries pour layout
- **Accessibility**: Focus states, color contrast OK
- **Bundle impact**: +15KB (CSS animations seulement)

---

## Support et Debugging

### Animation non visible
```css
/* Vérifier que la classe est appliquée */
.animate-scale-in {
  animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

### Stagger delays ne marchent pas
```tsx
// Doit avoir index 0-5 pour les classes animate-stagger-in-{1-5}
{items.map((item, index) => (
  <div key={index} className={`animate-stagger-in animate-stagger-in-${Math.min(index, 5)}`}>
    {item}
  </div>
))}
```

### Badge color pas correcte
```tsx
// Vérifier la valeur de confidence (0-1, pas 0-100)
<ConfidenceBadge confidence={0.75} /> ✓
<ConfidenceBadge confidence={75} />   ✗
```
