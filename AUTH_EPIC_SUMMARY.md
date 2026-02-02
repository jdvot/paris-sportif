# Epic d'Authentification - Vue d'ensemble

## Résumé Exécutif

**Epic**: Système d'Authentification Supabase pour Paris Sportif App
**Objectif**: Permettre aux utilisateurs de créer des comptes, se connecter, et accéder à des fonctionnalités personnalisées
**Timeline**: 4-6 semaines (3 sprints)
**Effort Total**: 38-53 story points

---

## Architecture d'Authentification

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js 15)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Login     │  │   Signup     │  │   Profile    │       │
│  │   Page      │  │   Page       │  │   Page       │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│         │                │                   │               │
│         └────────────────┴───────────────────┘               │
│                          │                                   │
│                  ┌───────▼────────┐                         │
│                  │  Supabase Auth  │                         │
│                  │    Client       │                         │
│                  └───────┬────────┘                         │
│                          │                                   │
│                  ┌───────▼────────┐                         │
│                  │   Middleware    │◄─── Protected Routes   │
│                  │  (JWT Verify)   │     (/picks, /profile) │
│                  └───────┬────────┘                         │
└──────────────────────────┼──────────────────────────────────┘
                           │ JWT Token
                           │ (Authorization Header)
┌──────────────────────────▼──────────────────────────────────┐
│                   BACKEND (FastAPI)                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────┐     ┌──────────────────┐           │
│  │  Auth Middleware   │────►│  Protected       │           │
│  │  (verify JWT)      │     │  Endpoints       │           │
│  └────────────────────┘     └──────────────────┘           │
│           │                                                  │
│           │                                                  │
└───────────┼──────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────┐
│                    SUPABASE                                   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  auth.users │  │user_profiles │  │   Storage    │       │
│  │  (Supabase) │  │   (Custom)   │  │  (Avatars)   │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
│  ┌─────────────────────────────────────────────────┐        │
│  │          Row Level Security (RLS)               │        │
│  │  - Users can only read/update their own profile │        │
│  └─────────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

---

## Planning des Sprints

### Sprint 1: Authentification de Base (Semaines 1-2)
**Objectif**: MVP fonctionnel - les utilisateurs peuvent créer un compte et se connecter

| Ticket | Titre | Effort | Owner | Status |
|--------|-------|--------|-------|--------|
| 1 | Setup Supabase Auth | M (5-8 pts) | TBD | Backlog |
| 2 | Pages Login/Signup | L (8-13 pts) | TBD | Backlog |
| 3 | Middleware Protection | M (5-8 pts) | TBD | Backlog |

**Deliverables Sprint 1**:
- [ ] Configuration Supabase Auth complète
- [ ] Pages login, signup, forgot-password fonctionnelles
- [ ] Routes `/picks` et `/profile` protégées
- [ ] Middleware redirections correctes

**Definition of Done Sprint 1**:
Un utilisateur peut créer un compte, recevoir un email de confirmation, se connecter, accéder à `/picks` (protégé), et être redirigé vers login s'il n'est pas authentifié.

---

### Sprint 2: Profil et Backend (Semaines 3-4)
**Objectif**: Personnalisation et sécurisation backend

| Ticket | Titre | Effort | Owner | Status |
|--------|-------|--------|-------|--------|
| 4 | Profil Utilisateur | L (8-13 pts) | TBD | Backlog |
| 5 | Backend FastAPI Auth | M (5-8 pts) | TBD | Backlog |

**Deliverables Sprint 2**:
- [ ] Table `user_profiles` avec RLS
- [ ] Page `/profile` fonctionnelle
- [ ] Upload avatar via Supabase Storage
- [ ] Backend FastAPI vérifie JWT
- [ ] Endpoints protégés côté API

**Definition of Done Sprint 2**:
Un utilisateur peut éditer son profil, uploader un avatar, se déconnecter. Le backend rejette les requêtes sans token valide sur les endpoints protégés.

---

### Sprint 3: OAuth et Polish (Semaines 5-6)
**Objectif**: Amélioration UX avec OAuth social login

| Ticket | Titre | Effort | Owner | Status |
|--------|-------|--------|-------|--------|
| 6 | OAuth Google/GitHub | M (5-8 pts) | TBD | Backlog |

**Deliverables Sprint 3**:
- [ ] Google OAuth configuré
- [ ] GitHub OAuth configuré
- [ ] Boutons social login visibles
- [ ] Tests E2E complets

**Definition of Done Sprint 3**:
Un utilisateur peut se connecter avec Google ou GitHub, son profil est auto-créé, et l'avatar est récupéré depuis le provider OAuth.

---

## Dépendances entre Tickets

```
┌─────────────────────┐
│   Ticket 1          │
│   Setup Supabase    │
│   Auth              │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼────┐   ┌───▼────┐
│Ticket 2│   │Ticket 3│
│Pages   │   │Middleware
│Auth    │   │         │
└───┬────┘   └────────┘
    │
    │
┌───▼────────────────┐
│   Ticket 4         │
│   Profil           │
│   Utilisateur      │
└───┬────────────────┘
    │
┌───▼────────────────┐
│   Ticket 6         │
│   OAuth            │
│   Providers        │
└────────────────────┘

┌─────────────────────┐
│   Ticket 5          │
│   Backend Auth      │
│   (Parallèle)       │
└─────────────────────┘
```

**Chemin Critique**: Ticket 1 → Ticket 2 → Ticket 3 → Ticket 4 → Ticket 6

**Parallélisation**: Ticket 5 (Backend Auth) peut être développé en parallèle après Ticket 1

---

## Matrice Effort vs Impact

```
Haute │
Impact│  [T3]         [T2] [T4]
      │  Middleware   Pages  Profil
      │
      │  [T5]         [T1]
      │  Backend      Setup
      │
Basse │              [T6]
Impact│              OAuth
      │
      └─────────────────────────────
         Faible        Moyen    Élevé
                    Effort
```

**Insights**:
- **Quick Wins**: Ticket 1 (Setup) - effort moyen, impact moyen, bloqueur critique
- **Big Bets**: Ticket 2 (Pages) et Ticket 4 (Profil) - effort élevé, impact élevé
- **Nice-to-Have**: Ticket 6 (OAuth) - effort moyen, impact faible (amélioration UX)

---

## Checklist de Qualité (Definition of Done)

### Pour chaque ticket:
- [ ] Code review effectué par 1+ développeur
- [ ] Tests unitaires passent (couverture >80%)
- [ ] Tests d'intégration passent
- [ ] Documentation mise à jour (README, AUTHENTICATION.md)
- [ ] Pas de vulnérabilités de sécurité (Snyk, npm audit)
- [ ] Performance acceptable (<2s login, <50ms middleware)
- [ ] Accessible (WCAG AA minimum)
- [ ] Responsive (mobile, tablet, desktop)
- [ ] Commits suivent Conventional Commits

### Pour l'Epic complet:
- [ ] Tests E2E Playwright (flow signup → login → protected page)
- [ ] Audit de sécurité auth (JWT, RLS, CORS)
- [ ] Load testing (100 users simultanés)
- [ ] Documentation complète pour onboarding nouveaux devs
- [ ] Rollback plan en cas d'incident production

---

## Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Configuration Supabase incorrecte | Moyenne | Élevé | Tester en local avant prod, checklist validation |
| OAuth setup complexe (Google/GitHub) | Moyenne | Moyen | Faire en dernier (Sprint 3), documentation détaillée |
| RLS policies mal configurées (fuite data) | Faible | Critique | Tests exhaustifs, peer review SQL, audit sécurité |
| JWT expiration mal gérée | Moyenne | Moyen | Refresh token automatique, tests expiration |
| Performance middleware (latence) | Faible | Moyen | Cache JWT validation, monitoring latence |
| Email delivery issues (spam) | Moyenne | Moyen | Configurer DKIM/SPF, tester avec Gmail/Outlook |

---

## Métriques de Succès (KPIs)

### Technique
- **Uptime Auth**: >99.9%
- **Latence Login**: <2 secondes (p95)
- **Latence Middleware**: <50ms overhead
- **Test Coverage**: >85%
- **Sécurité**: Zero vulnérabilités critiques (Snyk)

### Business
- **Taux de Conversion Signup**: >70% (visitors → accounts)
- **Taux de Completion Signup**: >80% (started → completed)
- **Taux d'Adoption OAuth**: >40% (vs email/password)
- **Retention J7**: >50% (retour après 7 jours)
- **Taux d'Erreur Login**: <5%

### Monitoring
- Mettre en place Sentry pour errors tracking
- Google Analytics pour funnel signup
- Supabase Dashboard pour auth metrics

---

## Équipe et Rôles

### Recommandation

| Rôle | Responsabilités | Tickets |
|------|-----------------|---------|
| **Frontend Lead** | Pages auth, middleware, profil | T1, T2, T3, T4, T6 |
| **Backend Dev** | FastAPI auth, JWT verification | T5 |
| **DevOps** | Supabase config, env vars, déploiement | T1 (support) |
| **QA** | Tests E2E, security audit | Tous |
| **Product Owner** | Acceptance criteria, priorités | - |

**Capacité requise**: 2 devs full-time pendant 4-6 semaines

---

## Roadmap Post-Epic (Futures Améliorations)

### Phase 2 (Q2 2026)
- [ ] Email verification obligatoire (currently optional)
- [ ] Two-Factor Authentication (2FA) avec TOTP
- [ ] Social login Apple, Microsoft, Twitter
- [ ] Magic link authentication (passwordless)

### Phase 3 (Q3 2026)
- [ ] Rate limiting sur endpoints auth
- [ ] Audit logs des connexions (RGPD compliance)
- [ ] Password strength meter sur signup
- [ ] Account recovery via SMS
- [ ] Session management (voir toutes les sessions actives)

### Phase 4 (Q4 2026)
- [ ] Single Sign-On (SSO) pour entreprises
- [ ] Biometric authentication (WebAuthn)
- [ ] Delegated authentication (login for friends)

---

## Ressources et Documentation

### Documentation à créer
1. `/docs/AUTHENTICATION.md` - Guide complet du système d'auth
2. `/docs/SUPABASE_SETUP.md` - Setup Supabase étape par étape
3. `/docs/SECURITY.md` - Best practices sécurité
4. `/docs/TROUBLESHOOTING_AUTH.md` - Dépannage auth

### Liens utiles
- [Supabase Auth Docs](https://supabase.com/docs/guides/auth)
- [Next.js 15 Auth](https://nextjs.org/docs/app/building-your-application/authentication)
- [OAuth 2.0 Spec](https://oauth.net/2/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

### Formations recommandées
- Supabase Auth Deep Dive (YouTube, 2h)
- OAuth 2.0 Explained (Udemy, 3h)
- Next.js Authentication Patterns (Frontend Masters, 4h)

---

## Contact et Support

**Questions techniques**: [Slack #auth-epic]
**Blockers**: Signaler immédiatement dans Notion (property "Blocked")
**Daily standup**: 10h00 (15min) - focus sur tickets auth

**Product Owner**: [À définir]
**Tech Lead**: [À définir]
**Scrum Master**: [À définir]

---

**Version**: 1.0
**Dernière mise à jour**: 2026-02-02
**Statut**: Prêt pour planification Sprint 1
