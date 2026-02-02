# Authentication Implementation - Quick Start Checklist

## Overview
This checklist guides you through implementing the authentication system for the Paris Sportif app. Follow the steps in order for a smooth implementation.

---

## Pre-Implementation Setup

### 1. Notion Setup (5 minutes)
- [ ] Open your Notion workspace
- [ ] Create or locate "Paris Sportif - Tasks" database
- [ ] Configure database properties (Type, Priority, Effort, Component, Labels, Sprint)
- [ ] Import tickets using one of these methods:
  - **Option A (Fastest)**: Import `auth_tickets.csv` via Notion Import feature
  - **Option B (Manual)**: Copy/paste tickets from `AUTHENTICATION_EPIC_TICKETS.md`
  - **Option C (Automated)**: Use Notion API script (see `NOTION_IMPORT_GUIDE.md`)
- [ ] Create Epic: "Système d'Authentification" and link all 6 tickets
- [ ] Create Board view grouped by Status
- [ ] Create Timeline view grouped by Sprint

### 2. Supabase Project Setup (10 minutes)
- [ ] Go to https://supabase.com and create account (if needed)
- [ ] Create new project: "paris-sportif-[env]" (e.g., paris-sportif-dev)
- [ ] Wait for project provisioning (~2 minutes)
- [ ] Navigate to Settings > API
- [ ] Copy `Project URL` → save as `NEXT_PUBLIC_SUPABASE_URL`
- [ ] Copy `anon/public key` → save as `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] Navigate to Settings > API > JWT Settings
- [ ] Copy `JWT Secret` → save as `SUPABASE_JWT_SECRET` (for backend)

### 3. Environment Variables Setup (5 minutes)

**Frontend** (`/frontend/.env.local`):
```bash
# Create or update .env.local
cd /Users/admin/paris-sportif/frontend
cat >> .env.local << 'EOF'

# Supabase Auth
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
EOF
```

**Backend** (`/backend/.env`):
```bash
# Update .env
cd /Users/admin/paris-sportif/backend
cat >> .env << 'EOF'

# Supabase Auth
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-here
EOF
```

- [ ] Replace placeholder values with actual Supabase credentials
- [ ] Add `.env.local` and `.env` to `.gitignore` (should already be there)
- [ ] Test env vars load correctly: `echo $NEXT_PUBLIC_SUPABASE_URL`

### 4. Database Migrations (10 minutes)
- [ ] Open Supabase Dashboard → SQL Editor
- [ ] Copy content from `database_migrations_auth.sql`
- [ ] Execute migrations sequentially (001 → 010)
- [ ] Verify tables created: Run verification queries at end of file
- [ ] Check RLS policies: Navigate to Authentication > Policies
- [ ] Check Storage bucket: Navigate to Storage → verify "avatars" bucket exists
- [ ] Test trigger: Create test user in Authentication > Users, verify profile auto-created

---

## Sprint 1: Core Authentication (Week 1-2)

### Ticket 1: Setup Supabase Auth (Day 1-2)

**Status**: [ ] Backlog → [ ] In Progress → [ ] Done

#### Step 1.1: Install Dependencies (10 minutes)
```bash
cd /Users/admin/paris-sportif/frontend
npm install @supabase/supabase-js @supabase/ssr
```

- [ ] Verify installation: `npm list @supabase/ssr`
- [ ] Expected version: `@supabase/ssr@0.5.0` or higher

#### Step 1.2: Create Supabase Client Files (30 minutes)

**File 1**: `/frontend/src/lib/supabase/client.ts`
```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

**File 2**: `/frontend/src/lib/supabase/server.ts`
```typescript
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value
        },
        set(name: string, value: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value, ...options })
          } catch (error) {
            // Handle error
          }
        },
        remove(name: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value: '', ...options })
          } catch (error) {
            // Handle error
          }
        },
      },
    }
  )
}
```

- [ ] Files created in correct locations
- [ ] TypeScript errors resolved
- [ ] Test import: Add `import { createClient } from '@/lib/supabase/client'` to a page

#### Step 1.3: Configure Email Templates (15 minutes)
- [ ] Open Supabase Dashboard → Authentication > Email Templates
- [ ] Customize "Confirm Signup" template:
  - Subject: "Bienvenue sur Paris Sportif - Confirmez votre email"
  - Add branding/logo
- [ ] Customize "Reset Password" template:
  - Subject: "Réinitialisation de votre mot de passe - Paris Sportif"
- [ ] Test email delivery: Create test user, check spam folder

#### Step 1.4: Testing (15 minutes)
```bash
cd /Users/admin/paris-sportif/frontend
npm run dev
```

- [ ] No TypeScript errors
- [ ] No console errors in browser
- [ ] Supabase client imports successfully

**Mark Ticket 1 as DONE**: [ ]

---

### Ticket 2: Login/Signup Pages (Day 3-5)

**Status**: [ ] Backlog → [ ] In Progress → [ ] Done

#### Step 2.1: Install Form Dependencies (5 minutes)
```bash
cd /Users/admin/paris-sportif/frontend
npm install react-hook-form @hookform/resolvers zod
```

- [ ] Verify installation: `npm list react-hook-form zod`

#### Step 2.2: Create Auth Layout (30 minutes)

**File**: `/frontend/src/app/auth/layout.tsx`
```typescript
import { ReactNode } from 'react'

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md p-8">
        {/* Add logo here */}
        <h1 className="text-2xl font-bold text-center mb-8">Paris Sportif</h1>
        {children}
      </div>
    </div>
  )
}
```

- [ ] Layout file created
- [ ] Styles applied correctly
- [ ] Logo visible (if added)

#### Step 2.3: Create Login Page (2 hours)

**File**: `/frontend/src/app/auth/login/page.tsx`

Key features to implement:
- [ ] Form with email and password fields
- [ ] Zod validation schema
- [ ] React Hook Form integration
- [ ] Supabase signInWithPassword
- [ ] Error handling (display errors from Supabase)
- [ ] Loading state (disable button, show spinner)
- [ ] Redirect to `/` after successful login
- [ ] Link to `/auth/signup` ("Pas encore de compte ?")
- [ ] Link to `/auth/forgot-password` ("Mot de passe oublié ?")

Testing:
- [ ] Valid login redirects to homepage
- [ ] Invalid credentials show error message
- [ ] Form validation prevents empty fields
- [ ] Loading spinner appears during login

#### Step 2.4: Create Signup Page (2 hours)

**File**: `/frontend/src/app/auth/signup/page.tsx`

Key features:
- [ ] Form with email, password, confirm password
- [ ] Password strength validation (min 8 chars, 1 number, 1 special char)
- [ ] Passwords match validation
- [ ] Supabase signUp
- [ ] Success message: "Vérifiez votre email pour confirmer votre compte"
- [ ] Link to `/auth/login` ("Déjà un compte ?")

Testing:
- [ ] Signup creates user in Supabase
- [ ] Confirmation email sent
- [ ] Duplicate email shows error
- [ ] Password mismatch shows error

#### Step 2.5: Create Forgot Password Page (1 hour)

**File**: `/frontend/src/app/auth/forgot-password/page.tsx`

Key features:
- [ ] Form with email field only
- [ ] Supabase resetPasswordForEmail
- [ ] Success message: "Email envoyé ! Vérifiez votre boîte de réception."
- [ ] Link back to `/auth/login`

Testing:
- [ ] Reset email sent successfully
- [ ] Email contains reset link

#### Step 2.6: Create Auth Callback Route (30 minutes)

**File**: `/frontend/src/app/auth/callback/route.ts`

Key features:
- [ ] Handle OAuth callback
- [ ] Exchange code for session
- [ ] Redirect to homepage

Testing:
- [ ] Callback processes correctly (test later with OAuth)

**Mark Ticket 2 as DONE**: [ ]

---

### Ticket 3: Middleware Protection (Day 6)

**Status**: [ ] Backlog → [ ] In Progress → [ ] Done

#### Step 3.1: Create Middleware (1 hour)

**File**: `/frontend/src/middleware.ts`

Key features to implement:
- [ ] Check for Supabase session in cookies
- [ ] Refresh expired tokens
- [ ] Protected routes: `/picks`, `/profile`
- [ ] Redirect to `/auth/login` if no session on protected routes
- [ ] Redirect to `/` if session exists on `/auth/login`
- [ ] Update cookies with refreshed session

**Middleware config**:
```typescript
export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
}
```

- [ ] Middleware file created at root of `/src`
- [ ] Matcher excludes static files
- [ ] TypeScript compiles without errors

#### Step 3.2: Testing Middleware (30 minutes)

Test scenarios:
- [ ] **Test 1**: Not logged in → try to access `/picks` → redirected to `/auth/login`
- [ ] **Test 2**: Logged in → try to access `/auth/login` → redirected to `/`
- [ ] **Test 3**: Logged in → access `/picks` → page loads successfully
- [ ] **Test 4**: Homepage `/` accessible without auth
- [ ] **Test 5**: Token expires → automatically refreshed on next request

**Mark Ticket 3 as DONE**: [ ]

---

## Sprint 1 Validation (End of Week 2)

### Sprint 1 Demo Checklist
- [ ] User can sign up with email/password
- [ ] User receives confirmation email
- [ ] User can log in with credentials
- [ ] Invalid credentials show error message
- [ ] Routes `/picks` and `/profile` are protected
- [ ] Middleware redirects work correctly
- [ ] User can reset password via email

### Sprint 1 Metrics
- [ ] All 3 tickets marked as DONE in Notion
- [ ] Zero critical bugs
- [ ] Code reviewed and merged to main
- [ ] Frontend tests pass (if written)
- [ ] Deployed to staging environment

---

## Sprint 2: Profile & Backend (Week 3-4)

### Ticket 4: User Profile (Day 7-10)

**Status**: [ ] Backlog → [ ] In Progress → [ ] Done

#### Step 4.1: Verify Database (10 minutes)
- [ ] Check Supabase Dashboard → Database → Tables → `user_profiles` exists
- [ ] Check RLS policies are enabled
- [ ] Test: Create user via signup, verify profile auto-created

#### Step 4.2: Create Profile Page (3 hours)

**File**: `/frontend/src/app/profile/page.tsx`

Key features:
- [ ] Fetch user profile from Supabase
- [ ] Display: username, full_name, email, bio, favorite_team, avatar
- [ ] Edit mode toggle
- [ ] Form to update profile fields
- [ ] Avatar upload component
- [ ] Save button (updates Supabase)
- [ ] Loading states

Testing:
- [ ] Profile data loads correctly
- [ ] Updates save successfully
- [ ] Avatar upload works
- [ ] RLS prevents accessing other users' profiles

#### Step 4.3: Avatar Upload Component (2 hours)

**File**: `/frontend/src/components/profile/AvatarUpload.tsx`

Key features:
- [ ] File input (accept: image/jpeg, image/png, image/webp)
- [ ] Preview before upload
- [ ] Upload to Supabase Storage (`avatars` bucket)
- [ ] File size validation (max 2MB)
- [ ] Update `avatar_url` in `user_profiles`
- [ ] Display current avatar or placeholder

Testing:
- [ ] Upload JPG, PNG, WEBP works
- [ ] Upload >2MB blocked
- [ ] Avatar displays after upload

#### Step 4.4: User Menu in Navbar (1 hour)

**File**: `/frontend/src/components/layout/UserMenu.tsx`

Key features:
- [ ] Avatar + username in navbar (top-right)
- [ ] Dropdown menu on click
- [ ] Menu items: "Profil", "Paramètres", "Déconnexion"
- [ ] Logout button calls `supabase.auth.signOut()`
- [ ] Redirect to `/auth/login` after logout

Testing:
- [ ] Menu appears when logged in
- [ ] Menu hidden when logged out
- [ ] Logout works and redirects

**Mark Ticket 4 as DONE**: [ ]

---

### Ticket 5: Backend FastAPI Auth (Day 11-13)

**Status**: [ ] Backlog → [ ] In Progress → [ ] Done

#### Step 5.1: Install Python Dependencies (5 minutes)
```bash
cd /Users/admin/paris-sportif/backend
uv add pyjwt httpx python-jose[cryptography]
```

- [ ] Packages installed: `uv pip list | grep -i jwt`

#### Step 5.2: Create Auth Middleware (2 hours)

**File**: `/backend/src/api/auth/middleware.py`

Key features:
- [ ] Function `verify_supabase_jwt(token: str)`
- [ ] Decode JWT with PyJWT
- [ ] Verify signature using `SUPABASE_JWT_SECRET`
- [ ] Check expiration
- [ ] Return user payload (user_id, email)

**File**: `/backend/src/api/auth/dependencies.py`

Key features:
- [ ] FastAPI dependency `get_current_user`
- [ ] Extract token from `Authorization: Bearer <token>` header
- [ ] Call `verify_supabase_jwt`
- [ ] Raise `HTTPException` if invalid/expired

Testing:
- [ ] Unit test: Valid JWT → returns user_id
- [ ] Unit test: Invalid JWT → raises exception
- [ ] Unit test: Expired JWT → raises exception

#### Step 5.3: Protect Endpoints (1 hour)

Update existing endpoints:
```python
from fastapi import Depends
from api.auth.dependencies import get_current_user

@app.post("/api/v1/predictions/track")
async def track_prediction(
    data: PredictionTrack,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]  # User ID from JWT
    # ... rest of logic
```

Endpoints to protect:
- [ ] `POST /api/v1/predictions/track`
- [ ] `GET /api/v1/predictions/user/{user_id}` (verify user_id matches JWT)

Testing:
- [ ] Request without token → 401 Unauthorized
- [ ] Request with invalid token → 401 Unauthorized
- [ ] Request with valid token → 200 OK

#### Step 5.4: Integration Testing (1 hour)

**File**: `/backend/tests/test_auth_integration.py`

Test scenarios:
- [ ] Signup on frontend → receive JWT → call protected endpoint → success
- [ ] Call protected endpoint without token → 401
- [ ] Call protected endpoint with expired token → 401

**Mark Ticket 5 as DONE**: [ ]

---

## Sprint 2 Validation (End of Week 4)

### Sprint 2 Demo Checklist
- [ ] User can view and edit profile
- [ ] User can upload avatar
- [ ] Avatar displays in navbar
- [ ] Logout works from navbar
- [ ] Backend rejects requests without valid JWT
- [ ] Backend accepts requests with valid JWT

### Sprint 2 Metrics
- [ ] Tickets 4 & 5 marked as DONE in Notion
- [ ] All tests passing (frontend + backend)
- [ ] Code coverage >80%
- [ ] No security vulnerabilities (run `npm audit`, `pip-audit`)

---

## Sprint 3: OAuth & Polish (Week 5-6)

### Ticket 6: OAuth Providers (Day 14-16)

**Status**: [ ] Backlog → [ ] In Progress → [ ] Done

#### Step 6.1: Google OAuth Setup (1 hour)
- [ ] Go to https://console.cloud.google.com
- [ ] Create project: "Paris Sportif"
- [ ] Enable Google+ API
- [ ] Create OAuth 2.0 credentials (Web application)
- [ ] Authorized redirect URI: `https://<your-project>.supabase.co/auth/v1/callback`
- [ ] Copy Client ID and Client Secret
- [ ] Paste in Supabase Dashboard → Authentication > Providers > Google

#### Step 6.2: GitHub OAuth Setup (30 minutes)
- [ ] Go to https://github.com/settings/developers
- [ ] New OAuth App
- [ ] Homepage URL: `http://localhost:3000` (dev)
- [ ] Callback URL: `https://<your-project>.supabase.co/auth/v1/callback`
- [ ] Copy Client ID and Client Secret
- [ ] Paste in Supabase Dashboard → Authentication > Providers > GitHub

#### Step 6.3: Add OAuth Buttons (2 hours)

**File**: `/frontend/src/components/auth/OAuthButtons.tsx`

Key features:
- [ ] Button "Continue with Google" (with Google icon)
- [ ] Button "Continue with GitHub" (with GitHub icon)
- [ ] Call `supabase.auth.signInWithOAuth({ provider: 'google' })`
- [ ] Handle errors (permissions denied)

Update login/signup pages:
- [ ] Add `<OAuthButtons />` component to `/auth/login`
- [ ] Add `<OAuthButtons />` component to `/auth/signup`
- [ ] Add divider: "ou" between OAuth and email forms

Testing:
- [ ] Click "Continue with Google" → Google consent screen
- [ ] After consent → redirected to app with session
- [ ] Profile auto-created with Google data (name, avatar)
- [ ] Same tests for GitHub

#### Step 6.4: Update Database Trigger (30 minutes)
- [ ] Verify trigger captures OAuth provider (already in migration 009)
- [ ] Test: Sign up with Google → check `auth_provider` column = 'google'
- [ ] Test: Avatar from Google populated in `avatar_url`

**Mark Ticket 6 as DONE**: [ ]

---

## Sprint 3 Validation (End of Week 6)

### Sprint 3 Demo Checklist
- [ ] User can sign up with Google
- [ ] User can sign up with GitHub
- [ ] OAuth auto-creates profile with provider data
- [ ] Avatar pulled from OAuth provider
- [ ] User can log in with email OR OAuth interchangeably

### Sprint 3 Metrics
- [ ] Ticket 6 marked as DONE in Notion
- [ ] OAuth adoption rate tracked (via analytics)
- [ ] Zero auth-related bugs in production

---

## Post-Epic Validation

### Security Audit Checklist
- [ ] RLS policies tested (user cannot access other users' data)
- [ ] JWT signature verified server-side
- [ ] No credentials in frontend code
- [ ] Environment variables not committed to git
- [ ] HTTPS enforced in production
- [ ] CORS configured correctly
- [ ] Rate limiting planned (future)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (React escapes by default)

### Performance Checklist
- [ ] Middleware overhead <50ms (measure with Lighthouse)
- [ ] Login flow <2 seconds (p95)
- [ ] Database queries optimized (indexes on frequently queried columns)
- [ ] Avatar images optimized (WebP, max 200KB)
- [ ] Caching strategy for profile data (React Query or SWR)

### Documentation Checklist
- [ ] Update `/docs/AUTHENTICATION.md` with architecture overview
- [ ] Update `/README.md` with auth setup instructions
- [ ] Create `/docs/TROUBLESHOOTING_AUTH.md` for common issues
- [ ] Document environment variables in `.env.example`
- [ ] Add code comments for complex auth logic

### Monitoring Setup
- [ ] Sentry configured for error tracking
- [ ] Google Analytics tracking signup funnel
- [ ] Supabase Dashboard monitoring auth metrics
- [ ] Alerts for auth failures >5% (future)

---

## Common Issues & Solutions

### Issue 1: "Invalid JWT" error
**Solution**: Check `SUPABASE_JWT_SECRET` matches in Supabase Dashboard → Settings > API

### Issue 2: Middleware infinite redirect
**Solution**: Ensure middleware doesn't protect `/auth/*` routes

### Issue 3: Avatar upload fails
**Solution**: Check Storage policies allow user's UUID as folder name

### Issue 4: Profile not auto-created on signup
**Solution**: Check trigger `on_auth_user_created` is enabled

### Issue 5: OAuth callback fails
**Solution**: Verify redirect URL matches exactly in OAuth provider settings

---

## Next Steps (Post-Epic)

### Phase 2 Planning
- [ ] Schedule retro: What went well? What to improve?
- [ ] Gather user feedback on auth flow
- [ ] Plan Phase 2 features (2FA, magic links, etc.)
- [ ] Update roadmap in Notion

### Technical Debt
- [ ] Refactor duplicated auth code
- [ ] Add E2E tests with Playwright
- [ ] Improve error messages (i18n)
- [ ] Add loading skeletons for better UX

---

## Resources

- **Project files**: `/Users/admin/paris-sportif/`
- **Detailed tickets**: `AUTHENTICATION_EPIC_TICKETS.md`
- **Database migrations**: `database_migrations_auth.sql`
- **Notion import guide**: `NOTION_IMPORT_GUIDE.md`
- **Epic summary**: `AUTH_EPIC_SUMMARY.md`

---

**Questions?** Refer to the detailed ticket specifications or consult the team.

**Good luck with the implementation!** 🚀
