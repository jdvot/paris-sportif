# Authentication Epic - Notion Tickets Package

## What's Included

This package contains everything you need to implement authentication in the Paris Sportif application using Supabase Auth. All tickets are ready to be imported into Notion for project management.

---

## Files Overview

### 1. **AUTHENTICATION_EPIC_TICKETS.md** (Primary Document)
**Purpose**: Complete specification of all 6 authentication tickets

**Contents**:
- Epic overview and business context
- 6 detailed tickets with:
  - Title, priority, effort estimates
  - Description and context
  - Technical specifications
  - Acceptance criteria (testable)
  - Testing checklists
  - Dependencies and blockers
  - Resources and documentation links

**When to use**: Reference when implementing each ticket for detailed requirements

---

### 2. **auth_tickets.csv** (Quick Import)
**Purpose**: CSV file for fast Notion import

**Contents**:
- 6 tickets in CSV format
- Core metadata: Title, Type, Priority, Effort, Sprint, Component, Labels, Description

**When to use**: Import directly into Notion via Import → CSV feature

**Limitations**:
- Relations (dependencies) must be added manually after import
- Detailed content (acceptance criteria, testing) not included

---

### 3. **NOTION_IMPORT_GUIDE.md** (Instructions)
**Purpose**: Step-by-step guide for importing tickets into Notion

**Contents**:
- 3 import methods: Manual, CSV, API automation
- Database property configuration
- Ticket relationship setup
- Validation checklist
- Recommended Notion views (Board, Timeline)

**When to use**: First time setting up the tickets in Notion

---

### 4. **AUTH_EPIC_SUMMARY.md** (Executive View)
**Purpose**: High-level overview and planning document

**Contents**:
- Architecture diagram
- Sprint planning (3 sprints, 4-6 weeks)
- Dependency graph between tickets
- Effort vs Impact matrix
- Risk assessment and mitigations
- Success metrics (KPIs)
- Team roles and capacity planning

**When to use**:
- Planning sessions with stakeholders
- Sprint planning meetings
- Risk reviews

---

### 5. **database_migrations_auth.sql** (Database Schema)
**Purpose**: SQL migrations for Supabase database

**Contents**:
- 10 migrations for auth system:
  - `user_profiles` table creation
  - Row Level Security (RLS) policies
  - Auto-create profile trigger
  - Storage bucket for avatars
  - Helper functions
  - OAuth provider tracking
- Rollback scripts
- Verification queries

**When to use**: Execute in Supabase SQL Editor before starting development

---

### 6. **AUTH_IMPLEMENTATION_CHECKLIST.md** (Developer Guide)
**Purpose**: Hands-on, step-by-step implementation guide

**Contents**:
- Pre-implementation setup (Notion, Supabase, env vars)
- Sprint-by-sprint breakdown with daily tasks
- Code snippets and file paths
- Testing instructions for each feature
- Validation checklists per sprint
- Troubleshooting common issues

**When to use**: During active development, day-to-day reference

---

## Quick Start (5-Minute Setup)

### Step 1: Import Tickets to Notion (2 minutes)
1. Open your Notion workspace
2. Go to your "Paris Sportif - Tasks" database
3. Click `⋯` → Import → CSV
4. Upload `auth_tickets.csv`
5. Map columns to properties
6. Done! (Manual linking of dependencies recommended)

### Step 2: Setup Supabase (2 minutes)
1. Go to https://supabase.com
2. Create project: "paris-sportif-dev"
3. Copy Project URL and Anon Key
4. Navigate to SQL Editor
5. Paste and execute `database_migrations_auth.sql`

### Step 3: Configure Environment (1 minute)
```bash
# Frontend
cd /Users/admin/paris-sportif/frontend
echo "NEXT_PUBLIC_SUPABASE_URL=<your-url>" >> .env.local
echo "NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-key>" >> .env.local

# Backend
cd /Users/admin/paris-sportif/backend
echo "SUPABASE_JWT_SECRET=<your-secret>" >> .env
```

**You're ready to start Sprint 1!**

---

## Ticket Summary

| # | Title | Priority | Effort | Sprint | Dependencies |
|---|-------|----------|--------|--------|--------------|
| 1 | Setup Supabase Auth | Critical | M | Sprint 1 | None |
| 2 | Login/Signup Pages | Critical | L | Sprint 1 | Ticket 1 |
| 3 | Middleware Protection | Critical | M | Sprint 1 | Ticket 1 |
| 4 | User Profile | High | L | Sprint 2 | Tickets 1, 2 |
| 5 | Backend FastAPI Auth | High | M | Sprint 2 | Ticket 1 |
| 6 | OAuth Providers | Medium | M | Sprint 3 | Tickets 1, 2, 4 |

**Total Effort**: 38-53 story points
**Timeline**: 4-6 weeks (3 sprints)

---

## Sprint Breakdown

### Sprint 1 (Weeks 1-2): Core Authentication
**Goal**: Users can sign up, log in, and access protected routes

**Deliverables**:
- ✅ Supabase Auth configured
- ✅ Login, Signup, Forgot Password pages
- ✅ Middleware protecting `/picks` and `/profile`

**Success Criteria**: New user can create account, log in, and be redirected from protected routes if not authenticated.

---

### Sprint 2 (Weeks 3-4): Profile & Backend
**Goal**: User profiles and secure backend

**Deliverables**:
- ✅ User profile page with avatar upload
- ✅ Backend JWT verification
- ✅ Protected API endpoints

**Success Criteria**: User can edit profile, upload avatar, and backend rejects unauthorized requests.

---

### Sprint 3 (Weeks 5-6): OAuth & Polish
**Goal**: Social login for better UX

**Deliverables**:
- ✅ Google OAuth
- ✅ GitHub OAuth
- ✅ OAuth buttons on login/signup

**Success Criteria**: User can sign up/login with Google or GitHub, profile auto-created with provider data.

---

## Epic Acceptance Criteria

**Definition of Done for entire epic**:
- [ ] Users can create accounts with email/password
- [ ] Users can log in with email/password
- [ ] Users can log in with Google or GitHub (OAuth)
- [ ] Protected routes redirect to login if not authenticated
- [ ] User profiles are viewable and editable
- [ ] Avatars can be uploaded and displayed
- [ ] Backend verifies JWT and protects sensitive endpoints
- [ ] RLS policies prevent unauthorized data access
- [ ] All tests passing (unit, integration, E2E)
- [ ] Zero critical security vulnerabilities
- [ ] Documentation complete and up-to-date

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                     FRONTEND                            │
│  Next.js 15 + TypeScript + Tailwind + shadcn/ui       │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Login      │  │   Signup     │  │   Profile   │ │
│  │   Page       │  │   Page       │  │   Page      │ │
│  └──────────────┘  └──────────────┘  └─────────────┘ │
│           │                │                │          │
│           └────────────────┴────────────────┘          │
│                          │                             │
│                   Supabase Auth Client                 │
│                          │                             │
│                   Middleware (JWT)                     │
└─────────────────────────┼──────────────────────────────┘
                          │ JWT Token
┌─────────────────────────┼──────────────────────────────┐
│                     BACKEND                             │
│        FastAPI + Python 3.11 + PyJWT                   │
│                          │                             │
│         Auth Middleware (verify JWT)                   │
│                          │                             │
│              Protected Endpoints                       │
└─────────────────────────┼──────────────────────────────┘
                          │
┌─────────────────────────┼──────────────────────────────┐
│                    SUPABASE                             │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ auth.users   │  │user_profiles │  │   Storage   │ │
│  │  (Managed)   │  │   (Custom)   │  │  (Avatars)  │ │
│  └──────────────┘  └──────────────┘  └─────────────┘ │
│                                                         │
│         Row Level Security (RLS) Enabled               │
└─────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **Forms**: React Hook Form + Zod
- **Auth Client**: @supabase/ssr, @supabase/supabase-js

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Auth**: PyJWT, python-jose
- **HTTP Client**: httpx

### Database & Auth
- **Platform**: Supabase
- **Database**: PostgreSQL (with RLS)
- **Storage**: Supabase Storage (avatars)
- **Auth**: Supabase Auth (email, Google, GitHub)

---

## Success Metrics (KPIs)

### Technical Metrics
- **Uptime**: >99.9%
- **Login Latency**: <2 seconds (p95)
- **Middleware Overhead**: <50ms
- **Test Coverage**: >85%

### Business Metrics
- **Signup Conversion**: >70%
- **OAuth Adoption**: >40%
- **7-Day Retention**: >50%
- **Login Error Rate**: <5%

---

## Risk Management

### Top Risks
1. **Configuration errors** (Mitigation: Detailed checklists, test in staging)
2. **RLS policy vulnerabilities** (Mitigation: Security audit, peer review)
3. **OAuth setup complexity** (Mitigation: Do last, comprehensive docs)
4. **JWT expiration issues** (Mitigation: Auto-refresh, thorough testing)

---

## Team Requirements

**Recommended team**:
- 1 Frontend Developer (full-time, 4-6 weeks)
- 1 Backend Developer (part-time, 2-3 weeks)
- 1 QA Engineer (testing throughout)
- 1 DevOps (setup support, 1 week)

**Skills needed**:
- Next.js 15 + TypeScript
- FastAPI + Python
- Supabase (Auth, Storage, RLS)
- OAuth 2.0 understanding
- Security best practices

---

## Next Steps

1. **Import tickets to Notion** using `auth_tickets.csv` or `NOTION_IMPORT_GUIDE.md`
2. **Setup Supabase** and run `database_migrations_auth.sql`
3. **Configure environment variables** in `.env.local` and `.env`
4. **Start Sprint 1** following `AUTH_IMPLEMENTATION_CHECKLIST.md`
5. **Daily standups** to track progress and blockers

---

## Documentation Links

- **Supabase Auth Docs**: https://supabase.com/docs/guides/auth
- **Next.js Auth**: https://nextjs.org/docs/app/building-your-application/authentication
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
- **OAuth 2.0**: https://oauth.net/2/

---

## Support

**Questions about tickets?**
→ See detailed specs in `AUTHENTICATION_EPIC_TICKETS.md`

**Stuck during implementation?**
→ Check `AUTH_IMPLEMENTATION_CHECKLIST.md` troubleshooting section

**Need to plan sprints?**
→ Refer to `AUTH_EPIC_SUMMARY.md` for roadmap

**Database issues?**
→ Verification queries at end of `database_migrations_auth.sql`

---

## Files Checklist

Verify you have all these files in `/Users/admin/paris-sportif/`:

- [x] `AUTHENTICATION_EPIC_TICKETS.md` (41 KB, 1000+ lines)
- [x] `auth_tickets.csv` (2 KB, 7 rows)
- [x] `NOTION_IMPORT_GUIDE.md` (18 KB, 350+ lines)
- [x] `AUTH_EPIC_SUMMARY.md` (25 KB, 550+ lines)
- [x] `database_migrations_auth.sql` (20 KB, 500+ lines)
- [x] `AUTH_IMPLEMENTATION_CHECKLIST.md` (30 KB, 650+ lines)
- [x] `README_AUTH_TICKETS.md` (this file)

**Total package size**: ~136 KB, 3000+ lines of documentation

---

## Version History

- **v1.0** (2026-02-02): Initial creation with 6 tickets, 3 sprints, complete documentation

---

**Ready to build!** 🚀

Start with Sprint 1, Ticket 1: Setup Supabase Auth. Good luck!
