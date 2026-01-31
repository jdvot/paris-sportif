# Quick Start - Page de Détail du Match

Démarrez en 5 minutes !

## 1. Configuration

```bash
cd frontend
cp .env.local.example .env.local
```

Éditez `.env.local`:
```env
NEXT_PUBLIC_USE_MOCK_DATA=true
```

## 2. Installation et démarrage

```bash
npm install
npm run dev
```

## 3. Accédez à la page

Ouvrez votre navigateur:
```
http://localhost:3000/match/1
```

## Résultat

Vous verrez une page complète avec:
- **En-tête du match**: Manchester United vs Liverpool
- **Prédictions**: Barres visuelles avec probabilités
- **Confiance**: 72% de confiance dans la prédiction
- **Recommandation**: Victoire domicile avec +15% de valeur
- **Facteurs clés**: 5 points forts et 3 risques
- **Forme récente**: 5 derniers matchs de chaque équipe
- **Head-to-Head**: Historique complet entre les équipes
- **Contributions des modèles**: 4 modèles d'IA
- **Ajustements IA**: Impact des blessures, sentiment, tactique

## Documentation

Pour en savoir plus:

| Document | Pour | Lire |
|----------|------|------|
| **GETTING_STARTED_MOCK.md** | Apprendre à utiliser les données mock | `/frontend/GETTING_STARTED_MOCK.md` |
| **src/app/match/README.md** | Comprendre la page en détail | `/frontend/src/app/match/README.md` |
| **MATCH_DETAIL_VISUAL_GUIDE.md** | Voir le design et le layout | `/frontend/MATCH_DETAIL_VISUAL_GUIDE.md` |
| **IMPLEMENTATION_SUMMARY.md** | Vue d'ensemble technique | `/IMPLEMENTATION_SUMMARY.md` |
| **FILES_CREATED.md** | Liste des fichiers modifiés | `/FILES_CREATED.md` |

## Fichiers créés

### Données Mock
- `/frontend/src/lib/mockData.ts` - Données réalistes pour le développement

### Configuration
- `/frontend/.env.local.example` - Template d'environnement

### Documentation
- `/frontend/src/app/match/README.md` - Documentation technique (400+ lignes)
- `/frontend/GETTING_STARTED_MOCK.md` - Guide de démarrage (300+ lignes)
- `/frontend/MATCH_DETAIL_VISUAL_GUIDE.md` - Guide visuel (500+ lignes)
- `/IMPLEMENTATION_SUMMARY.md` - Résumé du projet (400+ lignes)
- `/FILES_CREATED.md` - Liste des changements

### Code modifié
- `/frontend/src/lib/api.ts` - Support des données mock (+50 lignes)

## Contenu de la page

### Section 1: En-tête du Match
```
Premier League • Journée 20     [Status: A venir]

Manchester United    vs    Liverpool
                              24 Jan 2024, 20:00
```

### Section 2: Prédictions
```
Target Prediction    72%

Victoire Domicile:   48%  ████████░░░░░░░
Match Nul:           28%  ██████░░░░░░░░░
Victoire Extérieur:  24%  ██████░░░░░░░░░

✓ Recommandé: Victoire Domicile
Cote Value: +15%

Buts attendus (xG):
Domicile: 2.30
Extérieur: 1.80
```

### Section 3: Facteurs Clés
```
✓ Manchester United inarrêtable domicile avec 4V en 5 matchs
✓ Liverpool en difficulté à l'extérieur: 1V-2D-2L
✓ Historique favorable à United: 3V-2D-2L
✓ Modèle xG avantage United (2.3 vs 1.8)
✓ Forme récente United 4V-1D excellent

⚠ Blessures potentielles de joueurs clés
⚠ Match haut enjeu peut freiner United
⚠ Liverpool a battu des équipes fortes cette saison
```

### Section 4: Forme Récente
```
MANCHESTER UNITED          LIVERPOOL
VVVVV (15 pts)            VDVDV (11 pts)

V V V V V                 V N V N V
Pts: 15                   Pts: 11
Buts: 2.6/match           Buts: 2.2/match
Encaissés: 0.4/match      Encaissés: 0.8/match
Clean sheets: 4           Clean sheets: 1
```

### Section 5: Head-to-Head (Sidebar)
```
Victoires United:    3
Matchs nuls:        2
Victoires Liverpool: 2

Derniers matchs:
• United 2 - Liv 1
• Liv 2 - United 2
• United 1 - Liv 0
• Liv 2 - United 2
• United 3 - Liv 1
```

### Section 6: Contributions des Modèles
```
POISSON          ELO              xG               XGBoost
Poids: 25%       Poids: 25%       Poids: 25%       Poids: 25%

Domicile: 50%    Domicile: 48%    Domicile: 46%    Domicile: 49%
Nul: 30%         Nul: 28%         Nul: 26%         Nul: 29%
Extérieur: 20%   Extérieur: 24%   Extérieur: 28%   Extérieur: 22%
```

### Section 7: Ajustements IA
```
Impact              Impact              Sentiment
Blessures           Blessures           Domicile
Domicile            Extérieur
-2.0%               -4.0%               +3.0%

Sentiment           Avantage            Ajustement
Extérieur           Tactique            Total
-2.0%               +4.0%               +5.0%

Raisonnement: La faiblesse tactique de Liverpool à l'extérieur,
combinée avec l'avantage domicile de United et sa récente bonne
forme, offre une valeur. Cependant, les préoccupations de blessures
réduisent légèrement la confiance.
```

## Tester les autres matchs

Des données mock sont disponibles pour 4 matchs:

```
http://localhost:3000/match/1  # Manchester United vs Liverpool (PL)
http://localhost:3000/match/2  # Manchester City vs Arsenal (PL)
http://localhost:3000/match/3  # Real Madrid vs Barcelona (La Liga)
http://localhost:3000/match/4  # Paris Saint-Germain vs Marseille (Ligue 1)
```

## Personnaliser les données

Modifiez `/frontend/src/lib/mockData.ts`:

```typescript
export const mockPrediction: DetailedPrediction = {
  homeProb: 0.48,           // Changer probabilités
  drawProb: 0.28,
  awayProb: 0.24,
  confidence: 0.72,         // Changer confiance
  // ...
};
```

Les changements sont rechargés automatiquement (hot-reload Next.js).

## Passer au backend réel

Quand votre API est prête:

1. Éditer `.env.local`:
```env
NEXT_PUBLIC_USE_MOCK_DATA=false
NEXT_PUBLIC_API_URL=http://localhost:8000
```

2. Redémarrer le serveur:
```bash
npm run dev
```

Le code utilisera automatiquement votre API réelle.

## Dépannage

### "Impossible de charger les détails du match"
→ Vérifier: `NEXT_PUBLIC_USE_MOCK_DATA=true` dans `.env.local`

### Dark theme ne s'affiche pas
→ Redémarrer: `npm run dev`

### Responsive design cassé
→ Actualiser: Ctrl+Shift+R (hard refresh)

## Architecture

```
Frontend → API Client → [Mock Data | Real API]
  ↓           ↓
Browser    useQuery
           React Query
```

- **Mode Mock**: Retourne les données immédiatement (avec délai 300ms)
- **Mode API Réelle**: Appelle votre backend

## Prochaines étapes

1. ✅ Tester avec mock data
2. ✅ Vérifier le responsive design
3. ✅ Ajuster les couleurs/contenu
4. ✅ Connecter le backend réel
5. ✅ Ajouter des fonctionnalités

## Besoin d'aide?

- **Installation**: Voir `/frontend/GETTING_STARTED_MOCK.md`
- **Code**: Voir `/frontend/src/app/match/README.md`
- **Design**: Voir `/frontend/MATCH_DETAIL_VISUAL_GUIDE.md`
- **Technique**: Voir `/IMPLEMENTATION_SUMMARY.md`
- **Fichiers**: Voir `/FILES_CREATED.md`

## Statistiques

| Métrique | Valeur |
|----------|--------|
| Fichiers créés | 7 |
| Fichiers modifiés | 1 |
| Lignes de code | 300+ |
| Lignes de doc | 1600+ |
| Composants React | 9 |
| Données mock | 6 objects |
| Matchs exemple | 4 |

## Stack technologique

- **Frontend**: Next.js 13+, React 18, TypeScript
- **Styles**: Tailwind CSS 3+
- **Icônes**: Lucide React
- **State**: React Query (TanStack Query)
- **Dates**: date-fns
- **API**: Fetch API standard

## Licence et usage

Tous les fichiers sont prêts pour:
- ✅ Développement local
- ✅ Tests et QA
- ✅ Production
- ✅ Intégration backend

---

**Bon développement!**

Pour des questions: Consultez la documentation dans les fichiers README mentionnés ci-dessus.
