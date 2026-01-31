# Guide Visuel - Page de Détail du Match

## Vue d'ensemble du layout

```
┌─────────────────────────────────────────────────────────────────┐
│                          HEADER                                  │
│         Paris Sportif - Predictions Football                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    MATCH HEADER SECTION                          │
│                                                                   │
│  Trophy Premier League • Journee 20     [Status: A venir]       │
│                                                                   │
│        Manchester United    vs    Liverpool                       │
│                                              24 Jan 2024, 20:00  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────┬──────────────────────────────┐
│   MAIN CONTENT (66%)              │  SIDEBAR (33%)               │
│                                   │                              │
│  ┌────────────────────────────┐   │  ┌──────────────────────┐   │
│  │   PREDICTION SECTION       │   │  │  HEAD-TO-HEAD        │   │
│  │                            │   │  │  (sticky)            │   │
│  │  Target Prediction   72%   │   │  │                      │   │
│  │                            │   │  │  Victoires United: 3 │   │
│  │  Victoire Domicile   48%   │   │  │  Matchs nuls:     2  │   │
│  │  ████████░░░░░░░░░░░░░     │   │  │  Victoires Liverpool:│   │
│  │                            │   │  │                 2    │   │
│  │  Match Nul           28%   │   │  │  ────────────────    │   │
│  │  ██████░░░░░░░░░░░░░░░     │   │  │  Derniers matchs:    │   │
│  │                            │   │  │  • United 2 - Liv 1  │   │
│  │  Victoire Exterieur  24%   │   │  │  • Liv 2 - United 2  │   │
│  │  ██████░░░░░░░░░░░░░░░     │   │  │  • United 1 - Liv 0  │   │
│  │                            │   │  │  • Liv 2 - United 2  │   │
│  │  ✓ Victoire Domicile       │   │  │  • United 3 - Liv 1  │   │
│  │  Cote Value: +15%          │   │  │                      │   │
│  │                            │   │  └──────────────────────┘   │
│  │  Buts attendus:            │   │                              │
│  │  Domicile: 2.30            │   │                              │
│  │  Exterieur: 1.80           │   │                              │
│  │                            │   │                              │
│  │  Analyse: Manchester       │   │                              │
│  │  United montre une bonne   │   │                              │
│  │  forme domicile avec 4     │   │                              │
│  │  victoires en 5 derniers   │   │                              │
│  │  matchs...                 │   │                              │
│  │                            │   │                              │
│  └────────────────────────────┘   │                              │
│                                   │                              │
│  ┌────────────────────────────┐   │                              │
│  │   KEY FACTORS SECTION      │   │                              │
│  │                            │   │                              │
│  │  ✓ Manchester United       │   │                              │
│  │    inarretable domicile    │   │                              │
│  │    avec 4V en 5 matchs     │   │                              │
│  │                            │   │                              │
│  │  ✓ Liverpool en difficulte │   │                              │
│  │    a l'exterieur: 1V-2N-2D │   │                              │
│  │                            │   │                              │
│  │  ✓ Historique favorable    │   │                              │
│  │    a United: 3V-2N-2D      │   │                              │
│  │                            │   │                              │
│  │  ✓ Modele xG avantage      │   │                              │
│  │    United (2.3 vs 1.8)     │   │                              │
│  │                            │   │                              │
│  │  ✓ Forme recente United    │   │                              │
│  │    4V-1D excellent         │   │                              │
│  │                            │   │                              │
│  │  ⚠ Blessures potentielles │   │                              │
│  │    joueurs cles United     │   │                              │
│  │                            │   │                              │
│  │  ⚠ Match haut enjeu peut  │   │                              │
│  │    freiner United          │   │                              │
│  │                            │   │                              │
│  │  ⚠ Liverpool a battu des  │   │                              │
│  │    equipes fortes cette    │   │                              │
│  │    saison                  │   │                              │
│  │                            │   │                              │
│  └────────────────────────────┘   │                              │
│                                   │                              │
│  ┌────────────────────────────┐   │                              │
│  │   TEAM FORM SECTION        │   │                              │
│  │                            │   │                              │
│  │  ┌──────────┬──────────┐   │   │                              │
│  │  │Manchester│ Liverpool │   │   │                              │
│  │  │ United   │          │   │   │                              │
│  │  ├──────────┼──────────┤   │   │                              │
│  │  │VVVVV     │ VDVDV    │   │   │                              │
│  │  │          │          │   │   │                              │
│  │  │ V V V V V│ V N V N V│   │   │                              │
│  │  │          │          │   │   │                              │
│  │  │ Pts (5): 15│ Pts (5): 11│ │                              │
│  │  │                    │   │   │                              │
│  │  │ Buts marques: 2.6  │   │   │                              │
│  │  │ Buts encaisses: 0.4│   │   │                              │
│  │  │ Clean sheets: 4    │   │   │                              │
│  │  │                    │   │   │                              │
│  │  │ xG pour: 2.45      │   │   │                              │
│  │  │ xG contre: 0.85    │   │   │                              │
│  │  └──────────┴──────────┘   │   │                              │
│  │                            │   │                              │
│  └────────────────────────────┘   │                              │
│                                   │                              │
└──────────────────────────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              MODEL CONTRIBUTIONS SECTION                         │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Poisson  │  │   ELO    │  │   xG     │  │ XGBoost  │         │
│  │ Poids: 25│  │ Poids: 25│  │ Poids: 25│  │ Poids: 25│         │
│  │          │  │          │  │          │  │          │         │
│  │ Domicile:│  │ Domicile:│  │ Domicile:│  │ Domicile:│         │
│  │ 50%      │  │ 48%      │  │ 46%      │  │ 49%      │         │
│  │          │  │          │  │          │  │          │         │
│  │ Nul:     │  │ Nul:     │  │ Nul:     │  │ Nul:     │         │
│  │ 30%      │  │ 28%      │  │ 26%      │  │ 29%      │         │
│  │          │  │          │  │          │  │          │         │
│  │ Exterieur│  │ Exterieur│  │ Exterieur│  │ Exterieur│         │
│  │ 20%      │  │ 24%      │  │ 28%      │  │ 22%      │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              LLM ADJUSTMENTS SECTION                             │
│                                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐     │
│  │ Impact         │  │ Impact         │  │ Sentiment      │     │
│  │ Blessures      │  │ Blessures      │  │ Domicile       │     │
│  │ Domicile       │  │ Exterieur      │  │                │     │
│  │ -2.0%          │  │ -4.0%          │  │ +3.0%          │     │
│  └────────────────┘  └────────────────┘  └────────────────┘     │
│                                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐     │
│  │ Sentiment      │  │ Avantage       │  │ Ajustement     │     │
│  │ Exterieur      │  │ Tactique       │  │ Total          │     │
│  │ -2.0%          │  │ +4.0%          │  │ +5.0%          │     │
│  └────────────────┘  └────────────────┘  └────────────────┘     │
│                                                                   │
│  Raisonnement:                                                   │
│  La faiblesse tactique de Liverpool a l'exterieur, combinee      │
│  avec l'avantage domicile de United et sa recente bonne forme,   │
│  offre une valeur. Cependant, les preoccupations de blessures    │
│  pour les deux equipes reduisent legerement la confiance.        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          FOOTER                                  │
│              Paris Sportif - Predictions basees sur IA            │
│          Avertissement: Les paris comportent des risques.         │
│                     Jouez responsablement.                        │
└─────────────────────────────────────────────────────────────────┘
```

## Détail des sections

### 1. Match Header
**Éléments:**
- Logo/icône compétition
- Nom compétition et journée
- Badge statut avec couleur adaptée
- Noms des équipes en gros
- Score (si terminé)
- Date/heure du match

**Couleurs:**
- Background: `from-dark-800/50 to-dark-900/50`
- Border: `border-dark-700`
- Texte: blanc pour équipes, `accent-400` pour compétition
- Status badge: couleur variant par statut

### 2. Prediction Section
**Éléments:**
- Titre avec icône Target
- Pourcentage de confiance (haut droit)
- 3 barres de probabilité
- Zone recommandation de pari
- 2 cartes xG (expected goals)
- Explication textuelle

**Couleurs:**
- Victoire domicile: `primary-400` (vert)
- Match nul: `yellow-400`
- Victoire extérieur: `accent-400` (bleu)
- Recommandation: `bg-primary-500/10 border-primary-500/30`

### 3. Key Factors Section
**Éléments:**
- Titre avec icône BarChart3
- Liste des facteurs positifs (CheckCircle, vert)
- Séparateur ligne
- Liste des facteurs de risque (AlertTriangle, orange)

**Couleurs:**
- Facteurs positifs: `text-primary-400`
- Facteurs risque: `bg-yellow-500/10 border-yellow-500/20`

### 4. Team Form Section
**Sous-sections pour chaque équipe:**
- Nom équipe
- Form string (VVVVV, VDVDV, etc.)
- 5 cartes avec résultats derniers matchs
  - V (Victoire) = vert `bg-primary-500`
  - N (Nul) = gris `bg-gray-500`
  - D (Défaite) = rouge `bg-red-500`
- Grille 2×2 avec statistiques
- Ligne de séparation + xG stats (optionnel)

### 5. Head-to-Head Section
**Sticky sidebar (top: 2rem):**
- Titre avec icône Users
- 3 cartes avec wins/draws/losses
- Séparateur ligne
- "Derniers matchs" titre
- Scroll container max-h-64 avec 5 matches
  - Nom match
  - Score (si terminé) ou date (si à venir)

**Couleurs:**
- Victoires home: `bg-primary-500/10 border-primary-500/20`
- Nuls: `bg-gray-500/10 border-gray-500/20`
- Victoires away: `bg-accent-500/10 border-accent-500/20`

### 6. Model Contributions
**Grid 4 colonnes (responsive):**
- Nom du modèle
- Pourcentage de poids
- 3 probabilités (domicile/nul/extérieur)

**Couleurs:**
- Domicile: `text-primary-400`
- Nul: `text-yellow-400`
- Extérieur: `text-accent-400`

### 7. LLM Adjustments
**Grid 3 colonnes (responsive):**
6 cartes d'ajustement:
- Label en bas
- Pourcentage en gros/gras
- Couleur selon type (orange pour blessures, bleu pour sentiment, vert pour tactique)

**Sous la grille:**
- Zone explication en `bg-dark-700/50`
- Texte en `text-dark-300`

## États et animations

### Loading State
```
┌─────────────────────────────────────────────────────────────┐
│  [████░░░░░░░░░░░░] Header skeleton animate-pulse          │
└─────────────────────────────────────────────────────────────┘

┌───────────────────────────┬─────────────────────────────────┐
│ [████░░░░░░░░░░░░░] Left  │ [████░░░░░░░░] Right skeleton  │
├───────────────────────────┤                                 │
│ [████░░░░░░░░░░░░░]       │                                 │
│ [████░░░░░░░░░░░░░]       │                                 │
│ [████░░░░░░░░░░░░░]       │                                 │
└───────────────────────────┴─────────────────────────────────┘
```

### Status Animations
- **EN DIRECT**: `animate-pulse` rouge
- **A venir**: bleu statique
- **Termine**: gris statique
- **Reporte**: jaune statique

## Responsive Behavior

### Desktop (lg ≥ 1024px)
- 2 colonnes: 66% + 33%
- Sidebar sticky
- Grid 2 colonnes pour form
- Grid 4 colonnes pour models
- Grid 3 colonnes pour ajustements

### Tablet (md ≥ 768px, lg < 1024px)
- 1 colonne full width
- Sidebar non-sticky (s'écoule naturellement)
- Grid 2 colonnes pour form
- Grid 2 colonnes pour models
- Grid 3 colonnes pour ajustements

### Mobile (< 768px)
- 1 colonne full width
- Tous les grids: 1 colonne
- Padding réduit
- Font sizes adaptés

## Accessibility

### ARIA Labels
```tsx
<div className="flex items-center gap-3" role="alert">
  <AlertTriangle className="w-5 h-5" aria-hidden="true" />
  <p>Erreur de chargement</p>
</div>
```

### Keyboard Navigation
- Tabs traversent tous les éléments interactifs
- Barres de probabilité non-interactives (info visuelle)
- Sticky sidebar reste accessible au scroll

### Couleurs & Contraste
- Tous les textes respectent WCAG AA (minimum 4.5:1)
- Pas de dépendance unique à la couleur
- Symboles en plus des couleurs (V/N/D pour form)

## Dark Theme

### Palette appliquée
```css
--color-dark-800: #1e293b  /* Backgrounds principaux */
--color-dark-700: #334155  /* Borders, séparateurs */
--color-dark-400: #94a3b8  /* Texte secondaire */
--color-dark-300: #cbd5e1  /* Texte tertiaire */
--color-dark-200: #e2e8f0  /* Texte clair */
--color-dark-100: #f1f5f9  /* Texte très clair */
--color-primary: #22c55e   /* Vert - victoires home */
--color-accent: #3b82f6    /* Bleu - victoires away */
```

### Overlays semi-transparents
```css
bg-dark-800/50    /* 50% opacity */
bg-primary-500/10 /* 10% opacity pour backgrounds */
border-primary-500/30 /* 30% opacity pour borders */
```

## Exemple d'intégration HTML

```html
<div class="space-y-6">
  <!-- Match Header -->
  <div class="bg-gradient-to-r from-dark-800/50 to-dark-900/50 border border-dark-700 rounded-xl p-8">
    <!-- Header content -->
  </div>

  <!-- Main Grid -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Left Column -->
    <div class="lg:col-span-2 space-y-6">
      <!-- Prediction -->
      <div class="bg-dark-800/50 border border-dark-700 rounded-xl p-6"></div>
      <!-- Key Factors -->
      <div class="bg-dark-800/50 border border-dark-700 rounded-xl p-6"></div>
      <!-- Team Form -->
      <div class="bg-dark-800/50 border border-dark-700 rounded-xl p-6"></div>
    </div>

    <!-- Right Column -->
    <div class="sticky top-8">
      <!-- Head-to-Head -->
      <div class="bg-dark-800/50 border border-dark-700 rounded-xl p-6"></div>
    </div>
  </div>

  <!-- Model Contributions -->
  <div class="bg-dark-800/50 border border-dark-700 rounded-xl p-6"></div>

  <!-- LLM Adjustments -->
  <div class="bg-dark-800/50 border border-dark-700 rounded-xl p-6"></div>
</div>
```
