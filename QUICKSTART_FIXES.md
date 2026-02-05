# Quickstart - Actions Immédiates (Phase 1)

**Durée totale:** 2 heures  
**Impact:** Critique (sécurité + performance + résilience)

---

## 1. Ajouter ANTHROPIC_API_KEY (5 minutes)

**Pourquoi:** Actuellement `/health/ready` retourne `"llm_api": false`, ce qui signifie que le système repose uniquement sur Groq. Si Groq rate-limited ou down, les prédictions LLM échouent.

**Actions:**
1. Aller sur https://console.anthropic.com/account/keys
2. Créer une nouvelle API key (ou utiliser existante)
3. Copier la clé (format: `sk-ant-api03-...`)
4. Render Dashboard: https://dashboard.render.com
5. Service `paris-sportif-api` → Environment
6. Add Environment Variable:
   - Key: `ANTHROPIC_API_KEY`
   - Value: `sk-ant-api03-...` (coller la clé)
7. Save → Service redémarrera automatiquement

**Vérification:**
```bash
curl https://paris-sportif-api.onrender.com/health/ready | jq .
# Doit retourner: "llm_api": true
```

---

## 2. Vérifier Backups PostgreSQL (10 minutes)

**Pourquoi:** Sans backups, un incident (corruption DB, suppression accidentelle) = perte totale des données (matchs, users, predictions).

**Actions:**
1. Render Dashboard: https://dashboard.render.com
2. Database `paris-sportif-db` → Backups tab
3. Vérifier:
   - ✅ "Automatic backups" = Enabled
   - ✅ Retention = 7 days (minimum)
   - ✅ Dernier backup < 24h

**Si backups désactivés:**
- Plan actuel probablement "Free" (pas de backups)
- **Upgrade CRITIQUE:** Plan Starter ($7/mois) inclut backups quotidiens
- Settings → Instance Type → Starter
- Confirmer upgrade

**Vérification:**
```bash
# Dashboard → Database → Backups
# Voir liste des backups quotidiens
```

---

## 3. Audit Rotation Secrets (30 minutes)

**Pourquoi:** Secrets mal configurés = risque de sécurité majeur (leak credentials, accès non autorisé).

**Checklist:**

### A. Vérifier Secrets Render
Render Dashboard → Service → Environment:

- [ ] `SUPABASE_JWT_SECRET` 
  - Longueur: 32+ caractères ✅
  - Unique (pas partagé dev/prod) ✅
  - Jamais committé dans Git ✅

- [ ] `STRIPE_SECRET_KEY`
  - Format production: `sk_live_...` (pas `sk_test_`) ✅
  - Voir: https://dashboard.stripe.com/apikeys

- [ ] `STRIPE_WEBHOOK_SECRET`
  - Format: `whsec_...` ✅
  - Correspond à webhook endpoint configuré ✅

- [ ] `HF_TRAINING_API_KEY`
  - Longueur: 32+ caractères ✅
  - Identique sur HuggingFace Space ✅

- [ ] `GROQ_API_KEY` / `ANTHROPIC_API_KEY`
  - Format valide ✅
  - Non expirée (tester via curl) ✅

### B. Vérifier Absence de Secrets dans Code

```bash
cd /Users/admin/paris-sportif

# Rechercher patterns dangereux
grep -r "sk_live_" backend/src/  # Ne doit rien retourner
grep -r "sk_test_" backend/src/  # Ne doit rien retourner
grep -r "GROQ_API_KEY.*=" backend/src/ | grep -v "settings\."  # OK si uniquement via settings
grep -r "password.*=" backend/src/ | grep -v "settings\."  # OK si uniquement via settings

# Vérifier .env non committé
git status | grep ".env"  # Ne doit rien retourner
```

**Si secrets trouvés dans code:**
1. Supprimer immédiatement
2. Regénérer les secrets compromis
3. Commit fix: `git commit -m "security: remove hardcoded secrets"`

---

## 4. Configurer DB Connection Pool (15 minutes)

**Pourquoi:** Pool par défaut SQLAlchemy = 5 connexions. Sous charge (50+ users simultanés), connexions épuisées → erreurs 500.

**Action:**

Modifier `/Users/admin/paris-sportif/backend/src/db/database.py`:

```python
# Trouver la ligne:
engine = create_async_engine(
    settings.database_url,
)

# Remplacer par:
engine = create_async_engine(
    settings.database_url,
    pool_size=20,          # Max connexions actives (5 → 20)
    max_overflow=10,       # Connexions burst temporaires
    pool_pre_ping=True,    # Vérifier connexion avant usage (évite stale)
    pool_recycle=3600,     # Recycler connexions après 1h
    echo_pool=False,       # Désactiver logs pool (performance)
)
```

**Commit & Deploy:**
```bash
cd /Users/admin/paris-sportif
git add backend/src/db/database.py
git commit -m "perf(db): increase connection pool to 20 (was 5)"
git push origin main
# Render auto-deploy en 2-3 minutes
```

**Vérification:**
```bash
# Attendre deploy terminé (Render Dashboard → Deploys)
# Vérifier logs pas d'erreur "connection pool"
curl https://paris-sportif-api.onrender.com/health/ready
# Should return 200 OK
```

---

## 5. Créer render.yaml (1 heure)

**Pourquoi:** Infrastructure as Code = reproductibilité, version control, documentation.

**Actions:**

### A. Fichier déjà créé
Le fichier `/Users/admin/paris-sportif/render.yaml` existe déjà (créé par audit).

### B. Revue & Personnalisation

```bash
cd /Users/admin/paris-sportif
cat render.yaml
```

**Ajustements à faire:**

1. **Region:** Changer `oregon` → `frankfurt` si EU requis
   ```yaml
   region: frankfurt  # oregon → frankfurt
   ```

2. **Auto-sleep (optionnel):** Décommenter si économie prioritaire
   ```yaml
   scaling:
     minInstances: 0  # Décommenter pour auto-sleep
     maxInstances: 1
   ```

3. **Database plan:** Vérifier correspondance avec actuel
   ```yaml
   databases:
     - name: paris-sportif-db
       plan: starter  # Vérifier dans Dashboard actuel
   ```

### C. Commit IaC

```bash
git add render.yaml
git commit -m "infra: add render.yaml for Infrastructure as Code"
git push origin main
```

**Note:** Render ne déploie pas automatiquement depuis `render.yaml` sauf si configuré. Ce fichier sert de:
- Documentation infrastructure
- Template pour nouveaux environnements (staging/prod)
- Référence pour disaster recovery

---

## Vérification Finale (5 minutes)

Après avoir complété les 5 actions ci-dessus:

### 1. Health Check Complet
```bash
curl https://paris-sportif-api.onrender.com/health/ready | jq .
```

**Attendu:**
```json
{
  "status": "ready",
  "database": true,
  "redis": true,
  "football_api": true,
  "llm_api": true  ← Doit être true maintenant
}
```

### 2. Vérifier Logs
Render Dashboard → Logs → Filter "ERROR"
- Pas d'erreurs "connection pool"
- Pas d'erreurs "LLM API"
- Pas d'erreurs "authentication"

### 3. Test Endpoint Critique
```bash
# Test prediction endpoint (nécessite auth)
# Si vous avez un token JWT:
curl -H "Authorization: Bearer $JWT_TOKEN" \
  https://paris-sportif-api.onrender.com/api/v1/predictions?limit=1
```

### 4. Métriques Performance
```bash
# Response time doit rester < 200ms
curl -w "\nTime: %{time_total}s\n" \
  https://paris-sportif-api.onrender.com/health
# Target: < 0.200s (200ms)
```

---

## Checklist Complète

- [ ] ANTHROPIC_API_KEY ajouté (5 min)
- [ ] Backups PostgreSQL vérifiés/activés (10 min)
- [ ] Audit secrets complété (30 min)
- [ ] DB pool configuré & déployé (15 min)
- [ ] render.yaml créé & committé (1h)
- [ ] Vérification finale OK (5 min)

**Total:** ~2h05 minutes

---

## Prochaines Étapes (Phase 2 - Ce Mois)

Après avoir complété Phase 1, voir:
- `/docs/AUDIT_SUMMARY.md` - Résumé exécutif
- `/docs/RENDER_AUDIT_REPORT.md` - Audit complet (60+ pages)
- `/docs/RUNBOOK.md` - Procédures d'incident

**Actions Phase 2 prioritaires:**
1. Activer auto-sleep Render (économie $56/an)
2. Configurer uptime monitoring (UptimeRobot gratuit)
3. Étendre response caching (performance +80%)

---

**Questions?** Consulter `/docs/RUNBOOK.md` section "Contacts & Accès"
