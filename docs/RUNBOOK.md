# Runbook Opérationnel - Paris Sportif Backend

**Version:** 1.0  
**Dernière mise à jour:** 5 février 2026  
**Mainteneur:** DevOps Team

---

## Table des Matières

1. [Contacts & Accès](#contacts--accès)
2. [Procédures Standard](#procédures-standard)
3. [Scénarios d'Incident](#scénarios-dincident)
4. [Maintenance Planifiée](#maintenance-planifiée)
5. [Checklists](#checklists)

---

## Contacts & Accès

### Équipe
- **On-Call Primary:** DevOps Team
- **On-Call Secondary:** Backend Team
- **Escalation:** CTO

### Dashboards
- **Render Dashboard:** https://dashboard.render.com/web/srv-xxx
- **Upstash Redis:** https://console.upstash.com/redis/xxx
- **Qdrant Cloud:** https://cloud.qdrant.io/
- **Sentry:** https://sentry.io/organizations/paris-sportif/
- **Uptime Robot:** https://uptimerobot.com/dashboard (à configurer)

### Endpoints de Monitoring
- **Production API:** https://paris-sportif-api.onrender.com
- **Health Check:** https://paris-sportif-api.onrender.com/health
- **Dependencies Check:** https://paris-sportif-api.onrender.com/health/ready
- **OpenAPI Docs:** https://paris-sportif-api.onrender.com/docs

---

## Procédures Standard

### 1. Vérifier l'État du Système

```bash
# Health check basique
curl https://paris-sportif-api.onrender.com/health

# Vérifier toutes les dépendances
curl https://paris-sportif-api.onrender.com/health/ready | jq .

# Exemple de réponse saine:
# {
#   "status": "ready",
#   "database": true,
#   "redis": true,
#   "football_api": true,
#   "llm_api": true  # Doit être true si ANTHROPIC_API_KEY configuré
# }
```

### 2. Consulter les Logs

**Via Render Dashboard:**
1. Go to https://dashboard.render.com
2. Select `paris-sportif-api` service
3. Click "Logs" tab
4. Filter by level: `ERROR`, `WARNING`, `INFO`

**Patterns de Logs Communs:**
```bash
# Erreurs de connexion DB
grep "connection pool" logs.txt

# Erreurs Redis
grep "Redis" logs.txt | grep "ERROR"

# Rate limits API Football
grep "RateLimitError" logs.txt

# Erreurs LLM
grep "GROQ\|Anthropic" logs.txt | grep "ERROR"
```

### 3. Déploiement & Rollback

**Déployer Manuellement:**
```bash
# Trigger deploy via Git push
git push origin main

# Ou via Render Deploy Hook (curl)
curl -X POST "$RENDER_DEPLOY_HOOK_URL"
```

**Rollback en Cas d'Erreur:**
1. Render Dashboard → Service → "Deploys" tab
2. Find last working deploy (status: "Live")
3. Click "..." → "Redeploy"
4. Confirm rollback
5. Monitor logs for 5 minutes

**Temps estimé:** 5-10 minutes

---

## Scénarios d'Incident

### Incident 1: API Complètement Down (HTTP 503)

**Symptômes:**
- `/health` retourne 503 Service Unavailable
- Frontend affiche "Service temporairement indisponible"
- Render Dashboard: Service status "Unhealthy"

**Causes Possibles:**
1. Deploy en cours (normal, 30-60s downtime)
2. Service crashé (OOM, exception non catchée)
3. Database unreachable
4. Code error au startup (migration failed)

**Diagnostic:**
```bash
# 1. Vérifier status Render
# Dashboard → Status indicator (rouge = down)

# 2. Vérifier logs startup
# Dashboard → Logs → Filter "ERROR" or "CRITICAL"

# 3. Vérifier DB connectivity
curl https://paris-sportif-api.onrender.com/health/ready
# Si "database": false → DB issue
```

**Actions:**
1. **Si deploy en cours:** Attendre 2 minutes, service devrait redémarrer
2. **Si service crashé:**
   ```bash
   # Restart manual
   # Dashboard → Settings → "Manual Deploy"
   # Ou rollback au dernier deploy stable
   ```
3. **Si DB unreachable:**
   - Vérifier Render PostgreSQL status
   - Dashboard → Database → Metrics
   - Si DB down: Contacter Render Support
4. **Si code error:**
   - Rollback au dernier commit stable
   - Fix bug en urgence sur branche `hotfix/xxx`
   - Deploy fix

**Temps de Résolution:** 5-15 minutes  
**Priorité:** 🔴 P0 (Critical)

---

### Incident 2: API Lente (Response Time > 2s)

**Symptômes:**
- Health check OK mais lent (>500ms)
- Frontend timeouts sur certaines requêtes
- Utilisateurs se plaignent de lenteur

**Causes Possibles:**
1. DB query lente (missing index, full table scan)
2. Cache Redis miss (pas de hit)
3. API externe timeout (Football Data, Groq)
4. CPU/Memory exhaustion
5. Connection pool exhaustion

**Diagnostic:**
```bash
# 1. Identifier endpoints lents via Sentry APM
# Sentry → Performance → Transactions → Sort by "p95"

# 2. Vérifier métriques serveur
# Render Dashboard → Metrics
# - CPU > 80% ? → Scale up needed
# - Memory > 400MB ? → Memory leak or load spike

# 3. Tester requête problématique
curl -w "\nTime: %{time_total}s\n" \
  https://paris-sportif-api.onrender.com/api/v1/predictions?limit=10
```

**Actions:**
1. **Query DB lente:**
   ```sql
   -- Identifier queries lentes (PostgreSQL)
   SELECT query, calls, mean_exec_time, max_exec_time
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```
   - Ajouter index manquant
   - Optimiser query (EXPLAIN ANALYZE)

2. **Cache miss:**
   ```python
   # Vérifier hit rate Redis
   # Upstash Dashboard → Metrics → Hit Rate
   # Si < 50% → augmenter TTL cache
   ```

3. **API externe timeout:**
   - Vérifier status page API externe
   - Augmenter timeout si nécessaire
   - Implémenter retry avec backoff

4. **CPU/Memory exhaustion:**
   ```bash
   # Scale up temporairement
   # Render Dashboard → Settings → Instance Type
   # Standard → Pro (plus de CPU/RAM)
   ```

5. **Connection pool exhaustion:**
   ```python
   # Fix: Augmenter pool size dans src/db/database.py
   engine = create_async_engine(
       settings.database_url,
       pool_size=20,  # 5 → 20
       max_overflow=10,
   )
   ```

**Temps de Résolution:** 15-60 minutes  
**Priorité:** 🟠 P1 (High)

---

### Incident 3: Rate Limit Exceeded (Football Data API)

**Symptômes:**
- Logs: `RateLimitError: API rate limit exceeded`
- Scheduler job `auto_sync_and_verify` failed
- Matches data pas à jour

**Causes:**
- Dépassement du plan Free (10 req/min)
- Trop de syncs simultanés
- Spike de traffic utilisateur

**Diagnostic:**
```bash
# Vérifier logs scheduler
# Render Dashboard → Logs → Search "RateLimitError"

# Vérifier plan API
# https://www.football-data.org/client/home
# → Usage → Requests today
```

**Actions:**
1. **Réduire fréquence sync:**
   ```python
   # src/api/main.py - Ligne 193
   scheduler.add_job(
       auto_sync_and_verify,
       trigger=IntervalTrigger(hours=12),  # 6h → 12h
   )
   # Deploy fix
   ```

2. **Upgrade plan API (si nécessaire):**
   - Free: 10 req/min
   - Tier One: €15/mois, 600 req/min
   - Tier Two: €50/mois, 10 req/sec

3. **Implémenter rate limiting interne:**
   ```python
   # Ajouter dans src/data/sources/football_data.py
   import asyncio
   
   async def _request(self, method, endpoint):
       await asyncio.sleep(0.5)  # 120 req/min max
       # ... existing code
   ```

**Temps de Résolution:** 5 minutes (fix code) ou immédiat (upgrade plan)  
**Priorité:** 🟡 P2 (Medium)

---

### Incident 4: Redis Unreachable

**Symptômes:**
- `/health/ready` retourne `"redis": false`
- Logs: `RedisError: Connection refused`
- API fonctionne mais très lente (no cache)

**Causes:**
- Upstash maintenance
- Réseau Render → Upstash bloqué
- Quota Free tier dépassé
- Mauvaise config `REDIS_URL`

**Diagnostic:**
```bash
# 1. Vérifier status Upstash
# https://status.upstash.com/

# 2. Tester connexion Redis
redis-cli -u $REDIS_URL PING
# Should return "PONG"

# 3. Vérifier quota
# Upstash Dashboard → Database → Metrics
# Daily Requests < 10,000 (Free tier)
```

**Actions:**
1. **Upstash maintenance:** Attendre fin maintenance (check status page)
2. **Réseau bloqué:** Redémarrer service Render (restart manual)
3. **Quota dépassé:**
   - Upgrade plan Pay-As-You-Go ($0.002/10k req)
   - Ou réduire cache usage (augmenter TTL)
4. **Mauvaise config:**
   ```bash
   # Render Dashboard → Environment Variables
   # Vérifier REDIS_URL format:
   # rediss://default:PASSWORD@HOST:6379
   ```

**Temps de Résolution:** 5-30 minutes  
**Priorité:** 🟡 P2 (Medium) - API degraded mais fonctionne

---

### Incident 5: Database Connection Exhausted

**Symptômes:**
- Logs: `OperationalError: FATAL: remaining connection slots reserved`
- Certaines requêtes retournent 500
- `/health/ready` intermittent

**Causes:**
- Pool size trop petit (default: 5 connexions)
- Connexions non fermées (leak)
- Traffic spike

**Diagnostic:**
```bash
# 1. Vérifier connexions actives PostgreSQL
# Render Dashboard → Database → Metrics → Active Connections
# Si proche de max_connections (default: 97) → problème

# 2. Identifier queries longues
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
```

**Actions:**
1. **Augmenter pool size (fix permanent):**
   ```python
   # backend/src/db/database.py
   engine = create_async_engine(
       settings.database_url,
       pool_size=20,  # 5 → 20
       max_overflow=10,
       pool_pre_ping=True,
       pool_recycle=3600,
   )
   ```

2. **Tuer connexions bloquées (fix temporaire):**
   ```sql
   -- Identifier PID de la query
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'active' AND now() - query_start > interval '5 minutes';
   ```

3. **Scale up DB plan:**
   - Starter: 97 connexions max
   - Standard: 200 connexions max

**Temps de Résolution:** 5 minutes (kill) ou 15 minutes (deploy fix)  
**Priorité:** 🔴 P0 (Critical si prod, P1 si staging)

---

### Incident 6: LLM API Errors (Groq/Anthropic)

**Symptômes:**
- Logs: `GroqException: Rate limit exceeded` ou `AnthropicException`
- Predictions générées sans ajustements LLM
- `/health/ready` retourne `"llm_api": false`

**Causes:**
- Rate limit Groq (gratuit: 30 req/min)
- API key invalide/expirée
- API externe down (status.groq.com)

**Diagnostic:**
```bash
# 1. Vérifier status API
# Groq: https://status.groq.com/
# Anthropic: https://status.anthropic.com/

# 2. Tester API key
curl -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "test"}]}'
```

**Actions:**
1. **Rate limit dépassé:**
   - Réduire fréquence d'appel LLM
   - Implémenter cache LLM (TTL 1h)
   - Utiliser fallback: Groq → Anthropic

2. **API key invalide:**
   ```bash
   # Render Dashboard → Environment Variables
   # Regénérer clé sur console.groq.com
   # Mettre à jour GROQ_API_KEY
   ```

3. **API down:**
   - Activer fallback Anthropic
   - Ou désactiver ajustements LLM temporairement:
     ```python
     # Ajouter dans src/llm/client.py
     USE_LLM = False  # Emergency fallback
     ```

**Temps de Résolution:** 5-15 minutes  
**Priorité:** 🟡 P2 (Medium) - Predictions fonctionnent sans LLM

---

## Maintenance Planifiée

### Mise à Jour de Dépendances Python

**Fréquence:** Mensuel  
**Fenêtre:** Samedi 02:00-04:00 UTC (faible trafic)

**Procédure:**
```bash
# 1. Créer branche
git checkout -b chore/update-dependencies

# 2. Mettre à jour uv.lock
cd backend
uv sync --upgrade

# 3. Tester localement
uv run pytest tests/ -v

# 4. Deploy sur staging (si disponible)
# 5. Vérifier logs pendant 24h
# 6. Merge et deploy prod
```

---

### Nettoyage Base de Données

**Fréquence:** Trimestriel  
**Objectif:** Supprimer vieux matchs, prédictions expirées

**Procédure:**
```sql
-- Supprimer matchs > 1 an et status FINISHED
DELETE FROM matches
WHERE status = 'FINISHED'
  AND match_date < NOW() - INTERVAL '1 year';

-- Supprimer prédictions > 6 mois
DELETE FROM predictions
WHERE created_at < NOW() - INTERVAL '6 months';

-- Vacuum pour récupérer espace
VACUUM FULL ANALYZE;
```

**Temps estimé:** 30 minutes  
**Downtime:** Aucun (VACUUM peut être lent)

---

### Nettoyage Vectors Qdrant

**Fréquence:** Mensuel  
**Objectif:** Rester dans Free tier (1GB)

**Procédure:**
```python
# Script: backend/scripts/cleanup_vectors.py
from datetime import datetime, timedelta
from src.vector.client import get_qdrant_client

async def cleanup_old_news():
    client = await get_qdrant_client()
    cutoff = datetime.now() - timedelta(days=90)
    
    # Delete vectors older than 90 days
    client.delete(
        collection_name="news",
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="created_at",
                        range=Range(lt=cutoff.timestamp())
                    )
                ]
            )
        )
    )
    print(f"Deleted vectors older than {cutoff}")

# Run
asyncio.run(cleanup_old_news())
```

---

## Checklists

### Checklist Pre-Deploy

- [ ] Tests passés localement (`uv run pytest`)
- [ ] Linting OK (`uv run ruff check`, `uv run black --check`)
- [ ] Migrations testées (`uv run alembic upgrade head`)
- [ ] Variables d'env vérifiées (pas de secret en clair)
- [ ] Changelog mis à jour
- [ ] Equipe notifiée (#deployments Slack)

### Checklist Post-Deploy

- [ ] Health check OK (`/health/ready` retourne 200)
- [ ] Logs vérifiés (no ERROR dans les 5 premières minutes)
- [ ] Endpoints critiques testés (matches, predictions, auth)
- [ ] Performance stable (response time < 200ms)
- [ ] Sentry: aucune nouvelle erreur
- [ ] Monitor pendant 30 minutes

### Checklist Post-Incident

- [ ] Root cause identifiée et documentée
- [ ] Fix permanent déployé (pas juste workaround)
- [ ] Post-mortem rédigé (template GitHub Issues)
- [ ] Monitoring ajouté pour détecter recurrence
- [ ] Runbook mis à jour avec nouvelle procédure
- [ ] Equipe formée sur nouveau process

---

## Annexes

### A. Commandes Utiles

```bash
# Tester endpoint avec timing
curl -w "\nStatus: %{http_code}\nTime: %{time_total}s\n" \
  https://paris-sportif-api.onrender.com/health

# Dump database (backup manuel)
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore database
psql $DATABASE_URL < backup_20260205.sql

# Test Redis connection
redis-cli -u $REDIS_URL INFO

# Test Qdrant connection
curl https://2aa5655c-xxx.gcp.cloud.qdrant.io:6333/collections \
  -H "api-key: $QDRANT_API_KEY"
```

---

### B. Contacts Escalation

| Service | Contact | Priorité |
|---------|---------|----------|
| Render Support | support@render.com | P0/P1 |
| Upstash Support | support@upstash.com | P2 |
| Groq Support | support@groq.com | P2 |
| Football Data API | support@football-data.org | P3 |

---

**Dernière révision:** 5 février 2026  
**Prochaine révision:** 5 mai 2026 (trimestriel)
