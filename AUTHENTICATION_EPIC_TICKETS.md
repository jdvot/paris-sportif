# Epic: Système d'Authentification - Paris Sportif App

## Epic Overview
**Epic Name**: Système d'Authentification avec Supabase Auth
**Priority**: Haute
**Effort Estimate**: XL (2-3 sprints)
**Business Value**: Permettre la personnalisation des prédictions, le tracking des paris, et monétisation future
**Dependencies**: Supabase PostgreSQL déjà en place

---

## Ticket 1: Setup Supabase Auth - Configuration initiale

**Title**: [feat] Setup Supabase Auth - Configuration initiale

**Type**: Feature
**Priority**: Critical
**Effort Estimate**: M (5-8 story points)
**Component**: Frontend, Infrastructure
**Labels**: `feat`, `auth`, `setup`, `supabase`, `frontend`

### Description
Mettre en place la configuration initiale de Supabase Auth dans l'application Next.js. Cette tâche constitue la fondation du système d'authentification et doit être complétée avant les autres tickets d'auth.

### Context
- L'application utilise déjà Supabase pour PostgreSQL
- Next.js 15 avec App Router nécessite l'utilisation de `@supabase/ssr`
- Les clients Supabase doivent être configurés différemment pour browser/server components

### Technical Specifications
**Stack**: Next.js 15, TypeScript, Supabase Auth
**Packages à installer**:
```bash
npm install @supabase/supabase-js @supabase/ssr
```

**Fichiers à créer**:
- `/frontend/src/lib/supabase/client.ts` - Browser client
- `/frontend/src/lib/supabase/server.ts` - Server client
- `/frontend/src/lib/supabase/middleware.ts` - Middleware helper

**Variables d'environnement** (`.env.local`):
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

**Configuration Supabase Dashboard**:
- Auth providers: Email/Password activé
- Email templates: Personnaliser avec branding Paris Sportif
- Site URL: `http://localhost:3000` (dev), production URL
- Redirect URLs: `http://localhost:3000/auth/callback`

### Acceptance Criteria
- [ ] Package `@supabase/ssr` installé (version 0.5.0+)
- [ ] Package `@supabase/supabase-js` installé (version 2.45.0+)
- [ ] Client browser créé avec `createBrowserClient` dans `/lib/supabase/client.ts`
- [ ] Client server créé avec `createServerClient` dans `/lib/supabase/server.ts`
- [ ] Variables d'environnement `NEXT_PUBLIC_SUPABASE_URL` et `NEXT_PUBLIC_SUPABASE_ANON_KEY` configurées
- [ ] Template email de confirmation personnalisé dans Supabase Dashboard
- [ ] Template email de reset password personnalisé
- [ ] Documentation ajoutée dans README pour la configuration locale
- [ ] Types TypeScript générés avec `supabase gen types typescript`

### Testing Checklist
- [ ] Client browser peut être importé sans erreur
- [ ] Client server fonctionne dans Server Components
- [ ] Variables d'environnement sont correctement chargées
- [ ] Email de test envoyé avec succès

### Dependencies
- Aucune

### Blocked By
- Aucun

### Resources
- [Supabase Auth with Next.js App Router](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [Supabase SSR Package](https://supabase.com/docs/guides/auth/server-side/creating-a-client)

---

## Ticket 2: Pages d'authentification - Login/Signup

**Title**: [feat] Créer pages Login, Signup et Forgot Password

**Type**: Feature
**Priority**: Critical
**Effort Estimate**: L (8-13 story points)
**Component**: Frontend, Auth
**Labels**: `feat`, `auth`, `ui`, `forms`, `frontend`

### Description
Créer les interfaces utilisateur pour l'authentification: pages de login, inscription et récupération de mot de passe. Design cohérent avec le thème dark existant de l'application.

### Context
- L'application utilise déjà shadcn/ui pour les composants
- Thème dark par défaut
- Besoin de validation robuste des formulaires
- UX fluide avec gestion des erreurs claire

### Technical Specifications
**Stack**: Next.js 15, TypeScript, shadcn/ui, Tailwind CSS, React Hook Form, Zod

**Packages additionnels**:
```bash
npm install react-hook-form @hookform/resolvers zod
```

**Pages à créer**:
- `/frontend/src/app/auth/login/page.tsx`
- `/frontend/src/app/auth/signup/page.tsx`
- `/frontend/src/app/auth/forgot-password/page.tsx`
- `/frontend/src/app/auth/callback/route.ts` (API route pour OAuth)

**Composants à créer**:
- `/frontend/src/components/auth/LoginForm.tsx`
- `/frontend/src/components/auth/SignupForm.tsx`
- `/frontend/src/components/auth/ForgotPasswordForm.tsx`
- `/frontend/src/components/auth/AuthLayout.tsx` (layout partagé)

**Fonctionnalités**:
- Login: Email + Password avec lien "Forgot password"
- Signup: Email + Password + Confirm Password + Terms acceptance
- Forgot Password: Email pour reset link
- Validation côté client avec Zod schemas
- Messages d'erreur Supabase traduits en français
- Loading states pendant les requêtes
- Redirection automatique après succès

**Design Requirements**:
- Thème dark cohérent avec l'app
- Formulaires centrés sur la page
- Logo Paris Sportif en header
- Responsive (mobile-first)
- Animations subtiles (shadcn/ui defaults)

### Acceptance Criteria
- [ ] Page `/auth/login` créée et accessible
- [ ] Page `/auth/signup` créée et accessible
- [ ] Page `/auth/forgot-password` créée et accessible
- [ ] Formulaire login fonctionnel avec Supabase Auth
- [ ] Formulaire signup fonctionnel avec création de compte
- [ ] Formulaire forgot password envoie l'email de reset
- [ ] Validation des champs avec Zod (email format, password strength)
- [ ] Messages d'erreur clairs en français (email déjà utilisé, credentials invalides, etc.)
- [ ] Redirection vers `/` après login réussi
- [ ] Redirection vers `/auth/login` après signup avec message "Vérifiez votre email"
- [ ] Design responsive (mobile, tablet, desktop)
- [ ] Loading spinners pendant les requêtes async
- [ ] Lien "Pas encore de compte ?" sur login vers signup
- [ ] Lien "Déjà un compte ?" sur signup vers login

### Testing Checklist
- [ ] Login avec credentials valides réussit
- [ ] Login avec credentials invalides affiche erreur
- [ ] Signup crée un nouveau compte
- [ ] Signup avec email existant affiche erreur
- [ ] Forgot password envoie l'email
- [ ] Validation empêche soumission de formulaire invalide
- [ ] Redirection post-auth fonctionne
- [ ] UI responsive sur mobile

### Dependencies
- Ticket 1: Setup Supabase Auth

### Blocked By
- Ticket 1 doit être complété

### Design Mockups
- Wireframes disponibles dans `/docs/design/auth-pages.png` (à créer)

### Resources
- [shadcn/ui Form component](https://ui.shadcn.com/docs/components/form)
- [React Hook Form](https://react-hook-form.com/)
- [Zod validation](https://zod.dev/)

---

## Ticket 3: Middleware et protection des routes

**Title**: [feat] Implémenter middleware d'authentification et protection des routes

**Type**: Feature
**Priority**: Critical
**Effort Estimate**: M (5-8 story points)
**Component**: Frontend, Security
**Labels**: `feat`, `auth`, `middleware`, `security`, `frontend`

### Description
Créer le middleware Next.js pour vérifier l'authentification sur les routes protégées et gérer les redirections automatiques. Ce middleware garantit que seuls les utilisateurs authentifiés peuvent accéder aux pages sensibles.

### Context
- Next.js 15 middleware s'exécute sur Edge Runtime
- Nécessite vérification JWT Supabase côté serveur
- Routes publiques: `/`, `/auth/*`, `/api/health`
- Routes protégées: `/picks`, `/profile`, `/predictions/*` (détails)

### Technical Specifications
**Stack**: Next.js 15 Middleware, Supabase Auth

**Fichier principal**:
- `/frontend/src/middleware.ts`

**Configuration**:
```typescript
export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
}
```

**Logique du middleware**:
1. Vérifier la présence de session Supabase dans cookies
2. Rafraîchir le token si expiré
3. Si route protégée + pas de session → redirect `/auth/login`
4. Si route `/auth/*` + session active → redirect `/`
5. Mettre à jour les cookies avec nouveau token

**Routes à protéger**:
- `/picks` - Page des 5 picks quotidiens
- `/profile` - Profil utilisateur
- `/predictions/[id]` - Détails prédictions (futures feature)

**Routes publiques**:
- `/` - Homepage
- `/auth/login`, `/auth/signup`, `/auth/forgot-password`
- `/api/*` - API routes (gestion auth interne)

### Acceptance Criteria
- [ ] Fichier `middleware.ts` créé à la racine de `/src`
- [ ] Session Supabase vérifiée via cookies
- [ ] Token JWT rafraîchi automatiquement si expiré
- [ ] Redirection vers `/auth/login` si accès route protégée sans auth
- [ ] Redirection vers `/` si accès `/auth/login` avec session active
- [ ] Cookies mis à jour avec nouveau token après refresh
- [ ] Matcher configuré pour exclure `_next/static`, `_next/image`, etc.
- [ ] Variable `matcher` exclut les fichiers publics
- [ ] Performance: middleware rapide (<50ms overhead)

### Testing Checklist
- [ ] Utilisateur non-auth accédant `/picks` est redirigé vers login
- [ ] Utilisateur auth accédant `/auth/login` est redirigé vers `/`
- [ ] Token expiré est rafraîchi automatiquement
- [ ] Routes publiques accessibles sans auth
- [ ] Session persiste après refresh page
- [ ] Logout invalide la session et redirige

### Dependencies
- Ticket 1: Setup Supabase Auth

### Blocked By
- Ticket 1 doit être complété

### Security Considerations
- Vérifier JWT signature côté serveur
- Ne jamais faire confiance aux données côté client uniquement
- Logs des tentatives d'accès non autorisés (future)

### Resources
- [Next.js Middleware](https://nextjs.org/docs/app/building-your-application/routing/middleware)
- [Supabase Auth Middleware](https://supabase.com/docs/guides/auth/server-side/nextjs)

---

## Ticket 4: Profil utilisateur et gestion de compte

**Title**: [feat] Page profil utilisateur avec upload avatar et gestion compte

**Type**: Feature
**Priority**: High
**Effort Estimate**: L (8-13 story points)
**Component**: Frontend, Backend, Database
**Labels**: `feat`, `profile`, `storage`, `database`, `frontend`

### Description
Créer la page de profil utilisateur permettant de voir/éditer les informations du compte, uploader un avatar, et se déconnecter. Inclut la création de la table `user_profiles` dans Supabase avec Row Level Security.

### Context
- Les données d'auth (email) sont dans `auth.users` (géré par Supabase)
- Données de profil additionnelles dans table custom `user_profiles`
- Avatar stocké dans Supabase Storage avec bucket public
- RLS pour garantir que chaque user ne peut modifier que son profil

### Technical Specifications
**Stack**: Next.js 15, TypeScript, Supabase Storage, PostgreSQL

**Database Schema** (`user_profiles`):
```sql
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE,
  full_name TEXT,
  avatar_url TEXT,
  bio TEXT,
  favorite_team TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policies
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile"
  ON user_profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
  ON user_profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Users can insert their own profile"
  ON user_profiles FOR INSERT
  WITH CHECK (auth.uid() = id);
```

**Supabase Storage**:
- Bucket: `avatars` (public)
- Max file size: 2MB
- Allowed formats: JPG, PNG, WEBP
- Naming: `{user_id}/avatar.{ext}`

**Pages/Composants**:
- `/frontend/src/app/profile/page.tsx`
- `/frontend/src/components/profile/ProfileForm.tsx`
- `/frontend/src/components/profile/AvatarUpload.tsx`
- `/frontend/src/components/layout/UserMenu.tsx` (dropdown navbar)

**Fonctionnalités**:
- Affichage infos profil (email, username, full_name, bio)
- Édition profil avec formulaire
- Upload avatar avec preview
- Bouton "Déconnexion" dans navbar (dropdown menu)
- Trigger auto-création profil lors du signup (via Supabase trigger)

**Database Trigger** (auto-create profile):
```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.user_profiles (id, username, full_name)
  VALUES (new.id, new.email, new.raw_user_meta_data->>'full_name');
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### Acceptance Criteria
- [ ] Table `user_profiles` créée dans Supabase avec colonnes spécifiées
- [ ] RLS policies configurées (SELECT, UPDATE, INSERT)
- [ ] Bucket `avatars` créé dans Supabase Storage (public)
- [ ] Trigger auto-création profil lors signup configuré
- [ ] Page `/profile` accessible et affiche les données utilisateur
- [ ] Formulaire édition profil fonctionnel (username, full_name, bio, favorite_team)
- [ ] Upload avatar fonctionnel avec preview avant upload
- [ ] Avatar affiché dans navbar (dropdown menu)
- [ ] Bouton "Déconnexion" dans navbar dropdown
- [ ] Logout fonctionne et redirige vers `/auth/login`
- [ ] Validation: username unique, avatar max 2MB
- [ ] Messages de succès/erreur pour update profil

### Testing Checklist
- [ ] Profil auto-créé lors du signup
- [ ] Édition profil sauvegarde correctement
- [ ] Upload avatar fonctionne (JPG, PNG, WEBP)
- [ ] Upload avatar >2MB bloqué avec message erreur
- [ ] RLS empêche user A de modifier profil user B
- [ ] Logout invalide session et redirige
- [ ] Avatar affiché dans navbar après upload

### Dependencies
- Ticket 1: Setup Supabase Auth
- Ticket 2: Pages d'authentification

### Blocked By
- Tickets 1 et 2 doivent être complétés

### Database Migration
- Créer migration SQL dans `/backend/migrations/003_user_profiles.sql`

### Resources
- [Supabase Storage](https://supabase.com/docs/guides/storage)
- [Supabase RLS](https://supabase.com/docs/guides/auth/row-level-security)

---

## Ticket 5: Intégration Auth avec Backend FastAPI

**Title**: [feat] Vérification JWT Supabase et protection endpoints FastAPI

**Type**: Feature
**Priority**: High
**Effort Estimate**: M (5-8 story points)
**Component**: Backend, Security
**Labels**: `feat`, `auth`, `backend`, `api`, `security`

### Description
Ajouter la vérification des JWT Supabase dans le backend FastAPI pour protéger les endpoints sensibles et lier les prédictions aux utilisateurs authentifiés.

### Context
- Frontend envoie JWT Supabase dans header `Authorization: Bearer <token>`
- Backend doit vérifier signature JWT avec Supabase JWT secret
- Endpoints publics: `GET /matches`, `GET /health`
- Endpoints protégés: `POST /predictions/track`, `GET /predictions/user/{user_id}`

### Technical Specifications
**Stack**: FastAPI, Python 3.11+, PyJWT, httpx

**Packages à ajouter**:
```bash
uv add pyjwt httpx python-jose[cryptography]
```

**Fichiers à créer**:
- `/backend/src/api/auth/middleware.py` - Middleware JWT verification
- `/backend/src/api/auth/dependencies.py` - FastAPI dependencies
- `/backend/src/api/auth/models.py` - User Pydantic models

**Middleware JWT**:
```python
# Pseudo-code
async def verify_supabase_jwt(token: str) -> dict:
    # 1. Fetch Supabase JWT secret from env
    # 2. Decode JWT avec PyJWT
    # 3. Vérifier signature et expiration
    # 4. Retourner payload (user_id, email, etc.)
```

**FastAPI Dependency**:
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    payload = await verify_supabase_jwt(token.credentials)
    return payload
```

**Endpoints à protéger**:
- `POST /api/v1/predictions/track` - Tracker un pari utilisateur
- `GET /api/v1/predictions/user/{user_id}` - Historique paris utilisateur
- Future: endpoints admin

**Variables d'environnement** (`.env`):
```
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_URL=https://your-project.supabase.co
```

### Acceptance Criteria
- [ ] Package `pyjwt` et `python-jose` installés
- [ ] Middleware `verify_supabase_jwt` créé et teste
- [ ] Dependency `get_current_user` créée pour FastAPI
- [ ] Variable `SUPABASE_JWT_SECRET` configurée dans `.env`
- [ ] Endpoints protégés utilisent `Depends(get_current_user)`
- [ ] Requête sans token retourne `401 Unauthorized`
- [ ] Requête avec token invalide retourne `401 Unauthorized`
- [ ] Requête avec token valide retourne `user_id` dans payload
- [ ] User ID disponible dans les handlers des endpoints protégés
- [ ] Tests unitaires pour `verify_supabase_jwt`
- [ ] Tests d'intégration pour endpoints protégés

### Testing Checklist
- [ ] Test: Endpoint protégé sans token → 401
- [ ] Test: Endpoint protégé avec token invalide → 401
- [ ] Test: Endpoint protégé avec token valide → 200
- [ ] Test: `get_current_user` retourne correct user_id
- [ ] Test: Token expiré → 401
- [ ] Integration test: Frontend → Backend auth flow

### Dependencies
- Ticket 1: Setup Supabase Auth

### Blocked By
- Ticket 1 doit être complété

### Security Considerations
- Ne jamais logger les tokens JWT
- Vérifier signature avec secret côté serveur
- Valider expiration du token
- Rate limiting sur endpoints auth (future)

### Resources
- [Supabase JWT Verification](https://supabase.com/docs/guides/auth/server-side/verifying-jwts)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)

---

## Ticket 6: OAuth Providers (Google, GitHub)

**Title**: [feat] Ajouter authentification OAuth Google et GitHub

**Type**: Feature
**Priority**: Medium
**Effort Estimate**: M (5-8 story points)
**Component**: Frontend, Auth
**Labels**: `feat`, `auth`, `oauth`, `enhancement`, `frontend`

### Description
Ajouter l'authentification sociale via Google et GitHub pour offrir une expérience de connexion plus fluide aux utilisateurs. Boutons "Continue with Google/GitHub" sur les pages login et signup.

### Context
- OAuth améliore le taux de conversion (moins de friction)
- Supabase supporte nativement Google et GitHub OAuth
- Pas besoin de gérer les passwords pour ces utilisateurs
- Configuration requise dans Google Cloud Console et GitHub OAuth Apps

### Technical Specifications
**Stack**: Next.js 15, Supabase Auth, OAuth 2.0

**Configuration Supabase**:
1. **Google OAuth**:
   - Créer projet dans Google Cloud Console
   - Activer Google+ API
   - Créer OAuth 2.0 credentials (Web application)
   - Redirect URI: `https://<project-ref>.supabase.co/auth/v1/callback`
   - Copier Client ID et Client Secret dans Supabase Dashboard

2. **GitHub OAuth**:
   - Créer OAuth App dans GitHub Settings > Developer settings
   - Homepage URL: `https://paris-sportif.app` (production)
   - Callback URL: `https://<project-ref>.supabase.co/auth/v1/callback`
   - Copier Client ID et Client Secret dans Supabase Dashboard

**Composants à modifier**:
- `/frontend/src/components/auth/LoginForm.tsx`
- `/frontend/src/components/auth/SignupForm.tsx`
- Ajouter `/frontend/src/components/auth/OAuthButtons.tsx`

**Fonctionnalités**:
- Boutons "Continue with Google" et "Continue with GitHub"
- Icons des providers (utiliser `lucide-react`)
- Gestion des erreurs OAuth
- Auto-création profil lors du premier login OAuth (via trigger DB)

**Code Example**:
```typescript
const handleGoogleLogin = async () => {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  })
  if (error) {
    toast.error(error.message)
  }
}
```

### Acceptance Criteria
- [ ] Google OAuth configuré dans Google Cloud Console
- [ ] GitHub OAuth configuré dans GitHub Developer Settings
- [ ] Client ID et Secret ajoutés dans Supabase Dashboard (Google + GitHub)
- [ ] Composant `OAuthButtons.tsx` créé avec boutons Google et GitHub
- [ ] Boutons OAuth ajoutés sur page `/auth/login`
- [ ] Boutons OAuth ajoutés sur page `/auth/signup`
- [ ] Click sur "Continue with Google" initie OAuth flow
- [ ] Click sur "Continue with GitHub" initie OAuth flow
- [ ] Callback OAuth redirige vers `/` après succès
- [ ] Profil auto-créé lors du premier login OAuth
- [ ] Messages d'erreur si OAuth échoue (permissions refusées, etc.)
- [ ] Icons providers visibles (Google colors, GitHub logo)

### Testing Checklist
- [ ] Login Google réussit et crée session
- [ ] Login GitHub réussit et crée session
- [ ] Profil créé automatiquement après premier OAuth login
- [ ] Erreur si permissions OAuth refusées
- [ ] Redirection vers `/` après succès
- [ ] Avatar récupéré depuis Google/GitHub (si disponible)

### Dependencies
- Ticket 1: Setup Supabase Auth
- Ticket 2: Pages d'authentification
- Ticket 4: Profil utilisateur (pour auto-création)

### Blocked By
- Tickets 1, 2, et 4 doivent être complétés

### Configuration Steps
1. Google Cloud Console: Créer projet + OAuth credentials
2. GitHub: Créer OAuth App
3. Supabase Dashboard: Ajouter credentials dans Auth > Providers
4. Tester OAuth flow en local et production

### Resources
- [Supabase OAuth Guide](https://supabase.com/docs/guides/auth/social-login)
- [Google OAuth Setup](https://console.cloud.google.com/)
- [GitHub OAuth Apps](https://github.com/settings/developers)

---

## Epic Summary

**Total Effort**: XL (38-53 story points across 6 tickets)
**Estimated Timeline**: 2-3 sprints (4-6 weeks)
**Critical Path**: Ticket 1 → Ticket 2 → Ticket 3 (bloquer pour MVP)
**Nice-to-have**: Ticket 6 (OAuth) peut être fait en dernier

**Priority Order**:
1. **Sprint 1**: Tickets 1, 2, 3 (auth de base fonctionnel)
2. **Sprint 2**: Tickets 4, 5 (profil et backend)
3. **Sprint 3**: Ticket 6 (OAuth - enhancement)

**Success Metrics**:
- [ ] Utilisateurs peuvent créer un compte et se connecter
- [ ] Routes sensibles protégées par middleware
- [ ] Backend vérifie JWT Supabase
- [ ] Taux de completion signup >80%
- [ ] Temps de login <2 secondes
- [ ] Zero failles de sécurité auth

**Risks & Mitigations**:
- **Risk**: Configuration Supabase incorrecte → **Mitigation**: Tester en local avant prod
- **Risk**: OAuth setup complexe → **Mitigation**: Faire OAuth en dernier (Ticket 6)
- **Risk**: RLS policies mal configurées → **Mitigation**: Tests exhaustifs des policies

**Post-Epic Tasks** (Future):
- Email verification obligatoire
- Two-factor authentication (2FA)
- Social login avec Apple, Microsoft
- Magic link authentication
- Rate limiting sur endpoints auth
- Audit logs des connexions

---

## Notes pour les développeurs

### Setup Local
1. Créer projet Supabase sur https://supabase.com
2. Copier `SUPABASE_URL` et `ANON_KEY` dans `.env.local`
3. Exécuter migrations SQL dans Supabase SQL Editor
4. Configurer email templates (optionnel pour dev)

### Conventions de code
- Noms de fonctions: `camelCase`
- Composants React: `PascalCase`
- Fichiers API routes: `kebab-case`
- Commits: `feat(auth): description` selon Conventional Commits

### Testing Strategy
- **Unit tests**: Fonctions de validation, helpers
- **Integration tests**: API endpoints avec mock JWT
- **E2E tests**: Flow complet signup → login → protected page (Playwright)

### Documentation à mettre à jour
- `/docs/AUTHENTICATION.md` - Guide détaillé auth
- `/README.md` - Section "Getting Started" avec setup Supabase
- `/frontend/README.md` - Variables d'environnement requises

---

**Questions? Contacts**:
- Tech Lead: [À définir]
- Product Owner: [À définir]
- Design: [À définir]

**Dernière mise à jour**: 2026-02-02
