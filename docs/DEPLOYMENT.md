# Guide de Deploiement Gratuit

## Architecture 100% Gratuite

| Service | Plateforme | Limite Gratuite |
|---------|-----------|-----------------|
| Frontend | Vercel | Illimite |
| Backend | Render | 750h/mois |
| Database | Render PostgreSQL | 256MB, 90 jours |
| LLM | Groq | 14,400 req/jour |
| Football API | football-data.org | 10 req/min |

## Etape 1: Creer les Comptes (Gratuit)

1. **Vercel** - https://vercel.com/signup
   - Connecter avec GitHub
   - Plan Hobby (gratuit)

2. **Render** - https://render.com/signup
   - Connecter avec GitHub
   - Plan gratuit

3. **Groq** - https://console.groq.com/
   - Creer un compte
   - Generer une API key (gratuit)

4. **football-data.org** - https://www.football-data.org/client/register
   - Creer un compte
   - Obtenir API key (gratuit)

## Etape 2: Deployer le Backend (Render)

### Option A: Deploy automatique

1. Aller sur https://render.com
2. Cliquer "New" > "Blueprint"
3. Connecter ce repo
4. Render detecte automatiquement `render.yaml`

### Option B: Deploy manuel

1. Aller sur https://render.com
2. Cliquer "New" > "Web Service"
3. Connecter le repo GitHub
4. Configurer:
   - Name: `paris-sportif-api`
   - Environment: `Python 3`
   - Build Command: `pip install -e .`
   - Start Command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`

5. Ajouter les variables d'environnement:
   ```
   FOOTBALL_DATA_API_KEY=votre_cle
   GROQ_API_KEY=votre_cle
   APP_ENV=production
   DEBUG=false
   ```

6. Creer la base de donnees PostgreSQL:
   - "New" > "PostgreSQL"
   - Plan: Free
   - Copier l'URL de connexion

## Etape 3: Deployer le Frontend (Vercel)

1. Aller sur https://vercel.com
2. "Add New" > "Project"
3. Importer le repo GitHub
4. Configurer:
   - Framework: Next.js
   - Root Directory: `frontend`

5. Variables d'environnement:
   ```
   NEXT_PUBLIC_API_URL=https://paris-sportif-api.onrender.com
   ```

6. Cliquer "Deploy"

## Etape 4: Configuration DNS (Optionnel)

Si vous avez un domaine personnalise:

### Vercel (Frontend)
1. Settings > Domains
2. Ajouter votre domaine
3. Configurer les DNS chez votre registrar

### Render (Backend)
1. Settings > Custom Domain
2. Ajouter `api.votre-domaine.com`

## Limites du Plan Gratuit

### Render
- **Web Service**: 750 heures/mois (se met en veille apres 15min d'inactivite)
- **PostgreSQL**: 256MB, supprime apres 90 jours
- Premiere requete peut etre lente (~30s) apres mise en veille

### Vercel
- **Bandwidth**: 100GB/mois
- **Builds**: 6000 minutes/mois
- **Serverless**: 100GB-heures

### Groq
- 30 requetes/minute
- 14,400 requetes/jour
- 1M tokens/heure

### football-data.org
- 10 requetes/minute
- Acces aux 5 grands championnats + coupes europeennes

## Conseils d'Optimisation

### Eviter les Cold Starts Render
Le service gratuit Render se met en veille apres 15min d'inactivite.
Solutions:
1. Utiliser UptimeRobot (gratuit) pour ping toutes les 14 minutes
2. Accepter le delai de ~30s pour la premiere requete

### Gerer les Limites LLM
1. Mettre en cache les analyses (Redis/Upstash)
2. Limiter les appels LLM aux matchs du jour
3. Fallback vers analyse statistique si rate limit

### Base de Donnees Render
La DB gratuite est supprimee apres 90 jours.
Solutions:
1. Migrer vers Supabase (gratuit permanent, 500MB)
2. Exporter les donnees avant expiration
3. Passer au plan payant ($7/mois)

## Commandes Utiles

```bash
# Verifier le statut Render
curl https://paris-sportif-api.onrender.com/health

# Logs Render
render logs paris-sportif-api

# Verifier deploiement Vercel
vercel logs
```

## Variables d'Environnement

### Backend (Render)
```env
DATABASE_URL=postgresql://...  # Auto-configure par Render
FOOTBALL_DATA_API_KEY=xxx
GROQ_API_KEY=xxx
APP_ENV=production
DEBUG=false
REDIS_URL=redis://...  # Optionnel: Upstash
```

### Frontend (Vercel)
```env
NEXT_PUBLIC_API_URL=https://paris-sportif-api.onrender.com
```

## Monitoring

### Gratuit
- **UptimeRobot**: Monitoring uptime (50 moniteurs gratuits)
- **Render Dashboard**: Logs et metriques basiques
- **Vercel Analytics**: Traffic et performance

### Optionnel (Payant)
- Sentry pour error tracking
- Grafana Cloud pour dashboards
