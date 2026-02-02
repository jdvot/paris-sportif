# Tickets Authentification & Rôles - Paris Sportif

## Vue d'ensemble

**Stack recommandée** : Supabase Auth (gratuit, déjà intégré)
**Coût estimé** : 0€ (jusqu'à 50,000 MAU)

---

## Epic: Système d'Authentification avec Rôles

### Architecture des rôles

```
┌─────────────────────────────────────────────────────────────┐
│                     RÔLES UTILISATEURS                       │
├─────────────────────────────────────────────────────────────┤
│  FREE (Gratuit)      │  PREMIUM           │  ADMIN          │
│  ─────────────────   │  ─────────────────  │  ────────────── │
│  • 3 picks/jour      │  • Tous les picks   │  • Tout accès   │
│  • Matchs publics    │  • Analyses RAG     │  • Dashboard    │
│  • Stats basiques    │  • Historique       │  • Gestion users│
│                      │  • Alertes          │  • Sync manuel  │
└─────────────────────────────────────────────────────────────┘
```

---

## Ticket 1: Setup Supabase Auth - Configuration initiale

**Priorité**: Haute | **Effort**: M | **Sprint**: 1

### Description
Configurer Supabase Auth dans le projet Next.js en utilisant le package officiel `@supabase/ssr` (recommandé pour Next.js 15 App Router).

### Tâches
- [ ] Installer les packages : `npm install @supabase/supabase-js @supabase/ssr`
- [ ] Créer `/lib/supabase/client.ts` (browser client)
- [ ] Créer `/lib/supabase/server.ts` (server client)
- [ ] Créer `/lib/supabase/middleware.ts` (pour middleware)
- [ ] Configurer `.env.local` avec les clés Supabase
- [ ] Configurer les templates email dans Supabase Dashboard

### Code - Client Browser
```typescript
// lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

### Code - Client Server
```typescript
// lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {}
        },
      },
    }
  )
}
```

### Variables d'environnement
```env
# .env.local (Frontend)
NEXT_PUBLIC_SUPABASE_URL=https://tbzbwxbhuonnglvqfdjr.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG...

# .env (Backend - déjà configuré)
DATABASE_URL=postgresql://...
```

### Coût: GRATUIT
- Supabase Auth: 0€ jusqu'à 50,000 MAU
- Pas de service supplémentaire requis

---

## Ticket 2: Pages Login/Signup avec Design

**Priorité**: Haute | **Effort**: L | **Sprint**: 1

### Description
Créer les pages d'authentification avec le design dark theme cohérent avec l'app.

### Pages à créer
- [ ] `/app/auth/login/page.tsx` - Connexion
- [ ] `/app/auth/signup/page.tsx` - Inscription
- [ ] `/app/auth/forgot-password/page.tsx` - Mot de passe oublié
- [ ] `/app/auth/callback/route.ts` - Callback OAuth
- [ ] `/app/auth/confirm/route.ts` - Confirmation email

### Fonctionnalités
- [ ] Formulaire email/password avec validation
- [ ] Messages d'erreur clairs
- [ ] Loading states
- [ ] Redirection après connexion
- [ ] Lien "Mot de passe oublié"
- [ ] Design responsive (mobile-first)

### UI Components à utiliser
- Input fields avec icônes (Mail, Lock)
- Boutons primaires (gradient vert)
- Alert messages pour erreurs
- Spinner pour loading

---

## Ticket 3: Système de Rôles (RBAC)

**Priorité**: Haute | **Effort**: M | **Sprint**: 1

### Description
Implémenter un système de rôles basé sur une table Supabase avec Row Level Security.

### Schéma Base de Données
```sql
-- Table des profils utilisateurs avec rôle
CREATE TABLE public.user_profiles (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  email TEXT NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  role TEXT NOT NULL DEFAULT 'free' CHECK (role IN ('free', 'premium', 'admin')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger pour créer automatiquement le profil à l'inscription
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, role)
  VALUES (NEW.id, NEW.email, 'free');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- RLS Policies
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile
CREATE POLICY "Users can view own profile"
  ON public.user_profiles FOR SELECT
  USING (auth.uid() = id);

-- Users can update their own profile (except role)
CREATE POLICY "Users can update own profile"
  ON public.user_profiles FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Only admins can change roles
CREATE POLICY "Admins can update any profile"
  ON public.user_profiles FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );
```

### Permissions par Rôle

| Fonctionnalité | Free | Premium | Admin |
|----------------|------|---------|-------|
| Voir matchs | ✅ | ✅ | ✅ |
| 3 picks/jour | ✅ | ✅ | ✅ |
| Tous les picks | ❌ | ✅ | ✅ |
| Analyses RAG | ❌ | ✅ | ✅ |
| Historique complet | ❌ | ✅ | ✅ |
| Alertes personnalisées | ❌ | ✅ | ✅ |
| Dashboard admin | ❌ | ❌ | ✅ |
| Sync manuel | ❌ | ❌ | ✅ |
| Gestion utilisateurs | ❌ | ❌ | ✅ |

### Hook React pour vérifier le rôle
```typescript
// hooks/useUserRole.ts
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

type Role = 'free' | 'premium' | 'admin'

export function useUserRole() {
  const [role, setRole] = useState<Role>('free')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const supabase = createClient()

    async function fetchRole() {
      const { data: { user } } = await supabase.auth.getUser()
      if (user) {
        const { data } = await supabase
          .from('user_profiles')
          .select('role')
          .eq('id', user.id)
          .single()

        if (data) setRole(data.role as Role)
      }
      setLoading(false)
    }

    fetchRole()
  }, [])

  return { role, loading, isPremium: role === 'premium' || role === 'admin', isAdmin: role === 'admin' }
}
```

---

## Ticket 4: Middleware Protection des Routes

**Priorité**: Haute | **Effort**: M | **Sprint**: 1

### Description
Créer un middleware Next.js pour protéger les routes selon le rôle.

### Code Middleware
```typescript
// middleware.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

// Routes protégées par rôle
const PROTECTED_ROUTES = {
  premium: ['/picks/all', '/analysis', '/history'],
  admin: ['/admin', '/sync'],
}

const PUBLIC_ROUTES = ['/', '/auth/login', '/auth/signup', '/matches']

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()
  const pathname = request.nextUrl.pathname

  // Redirect to login if not authenticated and accessing protected route
  if (!user && !PUBLIC_ROUTES.some(r => pathname.startsWith(r))) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  // Check role-based access
  if (user) {
    const { data: profile } = await supabase
      .from('user_profiles')
      .select('role')
      .eq('id', user.id)
      .single()

    const role = profile?.role || 'free'

    // Check premium routes
    if (PROTECTED_ROUTES.premium.some(r => pathname.startsWith(r))) {
      if (role === 'free') {
        return NextResponse.redirect(new URL('/upgrade', request.url))
      }
    }

    // Check admin routes
    if (PROTECTED_ROUTES.admin.some(r => pathname.startsWith(r))) {
      if (role !== 'admin') {
        return NextResponse.redirect(new URL('/', request.url))
      }
    }
  }

  return supabaseResponse
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
}
```

---

## Ticket 5: Intégration Backend FastAPI

**Priorité**: Moyenne | **Effort**: M | **Sprint**: 2

### Description
Ajouter la vérification JWT Supabase dans le backend FastAPI.

### Code Backend
```python
# src/core/auth.py
from fastapi import HTTPException, Depends, Header
from jose import jwt, JWTError
import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

async def get_current_user(authorization: str = Header(...)):
    """Verify Supabase JWT and return user info."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("user_metadata", {}).get("role", "free")
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(required_role: str):
    """Decorator to require specific role."""
    async def role_checker(user = Depends(get_current_user)):
        role_hierarchy = {"free": 0, "premium": 1, "admin": 2}
        if role_hierarchy.get(user["role"], 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

# Usage in routes
@router.get("/picks/all")
async def get_all_picks(user = Depends(require_role("premium"))):
    """Premium-only endpoint."""
    pass

@router.post("/sync/manual")
async def manual_sync(user = Depends(require_role("admin"))):
    """Admin-only endpoint."""
    pass
```

### Variables d'environnement Backend
```env
# Ajouter dans .env sur Render
SUPABASE_URL=https://tbzbwxbhuonnglvqfdjr.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-dashboard
```

---

## Ticket 6: Page Profil Utilisateur

**Priorité**: Moyenne | **Effort**: M | **Sprint**: 2

### Description
Page pour voir et modifier son profil, avec badge de rôle.

### Fonctionnalités
- [ ] Afficher email, nom, avatar
- [ ] Badge du rôle (Free/Premium/Admin)
- [ ] Modifier nom et avatar
- [ ] Upload avatar vers Supabase Storage
- [ ] Bouton déconnexion
- [ ] Historique des prédictions (premium)

---

## Ticket 7: OAuth Social Login (Optionnel)

**Priorité**: Basse | **Effort**: M | **Sprint**: 3

### Description
Ajouter connexion via Google et GitHub.

### Configuration Supabase Dashboard
1. Aller dans Authentication > Providers
2. Activer Google OAuth (API Console credentials)
3. Activer GitHub OAuth (Developer settings)
4. Configurer les redirect URLs

### Coût: GRATUIT
OAuth via Supabase est inclus dans le plan gratuit.

---

## Récapitulatif des Coûts

| Service | Coût | Limite gratuite |
|---------|------|-----------------|
| Supabase Auth | 0€ | 50,000 MAU |
| Supabase Database | 0€ | 500 MB |
| Supabase Storage | 0€ | 1 GB |
| **Total** | **0€** | |

---

## Planning Sprints

### Sprint 1 (Semaines 1-2) - Critique
- Ticket 1: Setup Auth ✅
- Ticket 2: Pages Login/Signup
- Ticket 3: Système de Rôles
- Ticket 4: Middleware Protection

### Sprint 2 (Semaines 3-4) - Important
- Ticket 5: Backend FastAPI Auth
- Ticket 6: Page Profil

### Sprint 3 (Semaine 5) - Nice-to-have
- Ticket 7: OAuth Social Login

---

## Ressources

- [Supabase Auth Next.js Docs](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [Next.js 15 Middleware](https://nextjs.org/docs/app/building-your-application/routing/middleware)
