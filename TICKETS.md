# Paris Sportif - Tickets & Roadmap

## Statut Projet - 1er Février 2026

### Infrastructure
| Composant | URL | Statut |
|-----------|-----|--------|
| Frontend | https://paris-sportif.vercel.app | ✅ Live |
| Backend API | https://paris-sportif-api.onrender.com | ✅ Live (Starter $7/mois) |
| Groq LLM | llama-3.3-70b-versatile | ✅ Configuré |
| Football Data | football-data.org (Free tier) | ✅ 10 req/min |

### Base de Données SQLite
| Table | Contenu | Statut |
|-------|---------|--------|
| matches | 67 matchs syncés | ✅ |
| standings | 40 classements | ✅ |
| predictions | Cache prédictions | ✅ Nouveau |
| ml_models | Modèles ML | ✅ Nouveau |
| sync_log | Historique syncs | ✅ |

---

## TICKETS ACTIFS

### [TICKET-001] UI/UX Frontend Improvements
**Priorité:** Haute
**Statut:** 🔄 En cours
**Assigné:** Agent UI/UX Expert

**Description:**
Améliorer l'interface utilisateur du frontend Next.js pour une meilleure expérience.

**Tâches:**
- [ ] Analyser l'état actuel des pages (Picks, Matchs, Classements)
- [ ] Améliorer la page Picks (cards, animations, mobile)
- [ ] Améliorer la page Matchs (filtres, affichage live)
- [ ] Améliorer la page Classements (tableaux, logos)
- [ ] Optimiser le responsive design
- [ ] Ajouter des animations/transitions
- [ ] Améliorer le dark mode
- [ ] Ajouter loading states et skeletons

---

### [TICKET-002] Backend Persistence & Caching
**Priorité:** Haute
**Statut:** ✅ Terminé
**Commit:** 72fd20e

**Description:**
Ajouter la persistence des données en base SQLite pour éviter la perte de cache au restart.

**Tâches:**
- [x] Créer table predictions
- [x] Créer table ml_models
- [x] Fonction save_prediction / get_prediction_from_db
- [x] Fonction save_ml_model / get_ml_model
- [x] Intégrer cache DB dans predictions.py
- [x] Fallback sur DB si API rate limit

---

### [TICKET-003] Rate Limit Protection
**Priorité:** Haute
**Statut:** ✅ Terminé
**Commits:** 87addb8, 6db642f

**Description:**
Protéger contre le rate limit de football-data.org (10 req/min).

**Tâches:**
- [x] Ajouter cache in-memory avec TTL
- [x] Créer endpoint /sync/weekly pour sync proactive
- [x] Fallback sur données mock si rate limit
- [x] Fallback sur database si disponible

---

### [TICKET-004] RAG Enrichment
**Priorité:** Moyenne
**Statut:** ✅ Terminé
**Commit:** 6db642f, pending

**Description:**
Ajouter enrichissement contextuel RAG pour améliorer les prédictions.

**Tâches:**
- [x] Créer module rag_enrichment.py
- [x] Intégrer fetch news/injuries
- [x] Sentiment analysis avec Groq
- [x] Derby detection
- [x] Match importance scoring
- [x] Créer routes API RAG (/rag/status, /rag/enrich, /rag/analyze)

---

### [TICKET-005] ML Training Persistence
**Priorité:** Moyenne
**Statut:** 🔲 À faire

**Description:**
Persister les modèles ML entraînés en database pour éviter re-training à chaque restart.

**Tâches:**
- [ ] Modifier training.py pour sauvegarder en DB
- [ ] Charger modèles depuis DB au startup
- [ ] Endpoint /ml/train pour forcer re-training
- [ ] Endpoint /ml/status pour voir modèles chargés

---

### [TICKET-006] Tennis & NBA Integration
**Priorité:** Basse
**Statut:** 🔲 À faire

**Description:**
Ajouter support pour Tennis et NBA avec APIs gratuites.

**APIs Identifiées:**
- Tennis: API-Tennis (RapidAPI free tier)
- NBA: balldontlie.io (gratuit)

**Tâches:**
- [ ] Créer data source pour Tennis
- [ ] Créer data source pour NBA
- [ ] Adapter modèles de prédiction
- [ ] Ajouter pages frontend

---

## BUGS CONNUS

### [BUG-001] Picks page shows 0 picks for today
**Statut:** Analysé
**Cause:** Matchs du jour déjà terminés (status: "finished")
**Solution:** Afficher matchs programmés des prochains jours

### [BUG-002] curl exit code 56 from VM
**Statut:** Contourné
**Cause:** Configuration réseau VM sandbox
**Solution:** Utiliser navigateur Chrome pour tester API

---

## COMMITS RÉCENTS

| Date | Commit | Description |
|------|--------|-------------|
| 01/02/2026 21:02 | 72fd20e | feat: Add database persistence for predictions and ML models |
| 01/02/2026 20:41 | 6db642f | feat: Integrate RAG enrichment into predictions |
| 01/02/2026 20:38 | 98f4b40 | feat: Add RAG enrichment module (canceled) |
| 01/02/2026 20:38 | 87addb8 | feat: Add caching and database (canceled) |

---

## NOTES TECHNIQUES

### API Keys (configurées sur Render)
- `GROQ_API_KEY`: gsk_njcM...JVQg (56 chars)
- `FOOTBALL_DATA_API_KEY`: aa5a7de7c5024832b6d07c1092d5cd1d

### Compétitions Supportées (Free Tier)
PL, SA, PD, BL1, FL1, DED, ELC, PPL, BSA, CL, WC, EC

### Rate Limits
- football-data.org: 10 requests/minute
- Groq: 30 requests/minute (free tier)

---

*Dernière mise à jour: 1er Février 2026, 21:05*
