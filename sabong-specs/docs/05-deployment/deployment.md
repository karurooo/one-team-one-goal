# Deployment, DevOps, Security & Maintenance

| Field | Value |
|---|---|
| SDLC phases | Deployment, Maintenance |
| Baseline | Blueprint "Infrastructure", "DevOps & Deployment", "Security Implementation", "Production Security Checklist" (Laravel/IIS/Redis parts replaced; frontend hosted on **Vercel**) |
| Status | Draft v0.1 |

---

## 1. Infrastructure

| Category | Blueprint | This project |
|---|---|---|
| Backend hosting | Windows IIS on-premise | **Supabase Cloud** (separate projects for test, staging and production) |
| Database | MySQL | Supabase Postgres (daily backups; PITR on the production plan if the budget allows) |
| Cache / queue | Redis | Not used (Postgres + IndexedDB on the client) |
| Frontend hosting | IIS | **Vercel** (Hobby plan: personal, non-commercial project). Static Vite build, Git-integrated deploys, preview URL per PR (OQ-03 resolved) |
| Repository | GitHub Organization | ✅ GitHub Organization |
| Containerization | Sail (backend), Docker (frontend) | Supabase CLI local stack (Docker under the hood) for the backend. Frontend runs with `npm run dev`; the frontend Dockerfile is optional (local dev only), not used for deploys |
| CI/CD | GitHub Actions | ✅ GitHub Actions for checks + Supabase deploys; Vercel Git integration for frontend deploys |
| Domain & TLS | — | Custom domain on Vercel (optional; `*.vercel.app` works), automatic HTTPS certificates |

---

## 2. Local development quick start (Blueprint "Quick Start" equivalent)

1. Clone the repository and `cd` into the project root.
2. Install: `npm install` (root + workspaces), then install the Supabase CLI and Deno.
3. Start Supabase: `supabase start` (prints the local URL, anon key and Studio URL).
4. Reset & seed the database: `supabase db reset` (runs migrations + `seed.sql`).
5. Serve Edge Functions: `supabase functions serve --env-file supabase/.env.local`.
6. Copy env: `cp frontend/.env.example frontend/.env.local` and paste the local URL/anon key.
7. Start the frontend: `npm run dev -w frontend` (optionally `docker compose up frontend`). To test Vercel-specific behavior (rewrites, headers) locally, use `vercel dev`.
8. Access:
   - App: `http://localhost:5173`
   - Supabase API: `http://127.0.0.1:54321`
   - Edge Functions: `http://127.0.0.1:54321/functions/v1`
   - Studio: `http://127.0.0.1:54323`
   - Emails (Inbucket/Mailpit): `http://127.0.0.1:54324`
   - API docs (OpenAPI viewer, local only): `npm run docs:serve`

### Local services (replaces "Docker Compose Services")

| Service | Provided by | Port |
|---|---|---|
| Postgres | Supabase CLI | 54322 |
| API gateway (PostgREST, Auth, Storage, Functions) | Supabase CLI | 54321 |
| Studio | Supabase CLI | 54323 |
| Email testing | Supabase CLI | 54324 |
| Frontend (Vite) | npm (or the optional `frontend/Dockerfile`, Node 20) | 5173 |

---

## 3. CI/CD

### 3.1 Pull request checks — `ci.yml`
Triggered on PRs to `development`, `staging` and `main`.

| Job | Steps |
|---|---|
| **sim** | Node 20 → `npm ci` → Vitest (sim) with coverage → golden fixtures in Node; Deno → `deno test` golden fixtures |
| **database** | Supabase CLI → `supabase start` → `supabase db reset` → `supabase test db` (pgTAP) → `supabase db lint` → sqlfluff |
| **functions** | (reuses the database stack) → `deno lint` → `deno check` → `deno test --allow-all` → `deno bench` (replay budget) |
| **frontend** | `npm ci` → lint → type-check → Vitest → `npm run build` → bundle size check (≤ 6 MB initial) |
| **types-drift** | `supabase gen types typescript --local` and compare with the committed `database.types.ts` (fail if different) |
| **security** | `gitleaks` secret scan; grep the built bundle for `service_role` |
| **determinism-browsers** | Playwright: golden fixtures in Chromium, Firefox and WebKit (on merges to `development`, and on PRs that touch `_shared/sim`) |

### 3.2 Deployment — `deploy.yml`

Deploys are split: **GitHub Actions** deploys the backend (Supabase migrations + Edge Functions). **Vercel's Git integration** deploys the frontend. Vercel's "Ignored Build Step" and branch settings make sure the frontend deploys only after the backend job for the same commit has passed (Vercel waits for the required GitHub check `backend-deploy`).

| Branch | Blueprint site | Backend (GitHub Actions `deploy.yml`) | Frontend (Vercel) |
|---|---|---|---|
| PR branches (`feat/*`, `fix/*`) | — | none (CI only) | **Preview deployment** with Test env vars (points at `sabong-test`) |
| `development` | Test Site | `supabase link --project-ref $TEST_REF` → `supabase db push` → `supabase functions deploy` → Playwright smoke against the Vercel preview URL | Preview deployment, branch alias `dev.<domain>` |
| `staging` | Staging Site | same, with `$STAGING_REF` → Lighthouse CI against `staging.<domain>` | Preview deployment, branch alias `staging.<domain>`, Staging env vars |
| `main` | Production Site | **manual approval by Ramil** (GitHub Environment `production`) → backup check → `supabase db push` → `supabase functions deploy` | **Production deployment** at the production domain; Sentry source maps uploaded during the Vercel build (`SENTRY_AUTH_TOKEN` in Vercel env) → smoke test |

**Rollback:** frontend: Vercel "Instant Rollback" to the previous production deployment. Backend: migrations are forward-only, so ship a fix-forward migration; Edge Functions: redeploy the previous Git tag.

### 3.3 Vercel project configuration

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Framework preset | Vite |
| Build command | `npm run build` |
| Output directory | `dist` |
| Node.js version | 20.x (same as CI) |
| Production branch | `main` |
| Branch domains | `staging` → `staging.<domain>`, `development` → `dev.<domain>` (or the free `*.vercel.app` aliases until a domain is bought) |
| Deployment protection | Vercel Authentication on Preview deployments (only you can open them); off for Production |
| Plan | Hobby (personal, non-commercial). **If the game ever earns money (ads, paid features), move to Pro first** |

`frontend/vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [{ "source": "/((?!assets/|models/|audio/|sw.js|manifest.webmanifest).*)", "destination": "/index.html" }],
  "headers": [
    { "source": "/assets/(.*)", "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }] },
    { "source": "/models/(.*)", "headers": [{ "key": "Cache-Control", "value": "public, max-age=604800, stale-while-revalidate=86400" }] },
    { "source": "/audio/(.*)",  "headers": [{ "key": "Cache-Control", "value": "public, max-age=604800, stale-while-revalidate=86400" }] },
    { "source": "/sw.js",       "headers": [{ "key": "Cache-Control", "value": "no-cache" }] },
    { "source": "/(.*)", "headers": [
      { "key": "Content-Security-Policy", "value": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https://<project-ref>.supabase.co; connect-src 'self' https://<project-ref>.supabase.co wss://<project-ref>.supabase.co https://*.ingest.sentry.io https://challenges.cloudflare.com; frame-src https://challenges.cloudflare.com; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'" },
      { "key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains; preload" },
      { "key": "X-Content-Type-Options", "value": "nosniff" },
      { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
      { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" }
    ]}
  ]
}
```

Notes:
- The rewrite sends every app route (`/roster`, `/fight/bot` …) to `index.html` so React Router handles it; static folders are excluded so a missing model returns a real 404.
- Vite puts hashed bundles in `/assets/`, which is why that folder is cached as `immutable`. Models and audio are not hashed, so they use a 7-day cache; change a model's filename when its content changes (e.g. `manok_talisayin.v2.glb`).
- `<project-ref>` differs per environment. Since `vercel.json` is static, the CSP lists the production ref, and Preview builds use a `vercel.json` override generated at build time by `scripts/write-vercel-csp.mjs` from `VITE_SUPABASE_URL` (or, simpler: allow `https://*.supabase.co wss://*.supabase.co` on Preview only).
- `'unsafe-inline'` for styles is needed by some UI libraries (Sonner, Radix positioning). Scripts stay strict.

Migrations must be backward compatible with the frontend currently live (expand → deploy → contract), because the database deploys before the frontend, and older Vercel deployments (previews, Instant Rollback targets) may still call it.

---

## 4. Environment variables & secrets

### Frontend (build-time, public) — set in **Vercel → Project → Environment Variables**
See [conventions.md](../03-development/conventions.md) §5. **Only the anon key** is ever exposed.

| Variable | Production | Preview (`staging` branch) | Preview (all other branches) | Development (`vercel env pull`) |
|---|---|---|---|---|
| `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` | `sabong-prod` | `sabong-staging` | `sabong-test` | local (`127.0.0.1:54321`) |
| `VITE_SENTRY_DSN` | ✅ | ✅ | ✅ | optional |
| `VITE_CAPTCHA_SITE_KEY` | prod key | test key | test key | Turnstile test key |
| `SENTRY_AUTH_TOKEN` (build-only, **not** `VITE_`-prefixed) | ✅ | ✅ | — | — |

Vercel lets a Preview variable be scoped to one branch: that is how `staging` gets its own Supabase project. Never add `SUPABASE_SERVICE_ROLE_KEY` to Vercel: the frontend never needs it.

### Edge Functions (secrets, set with `supabase secrets set`)

| Variable | Dev value | Production notes |
|---|---|---|
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Injected by the platform | Never copied into the repo or the frontend |
| `APP_ENV` | `local` | `production` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated exact origins. Test: `https://dev.<domain>` plus the preview pattern below. Staging: `https://staging.<domain>`. Production: the production domain **only** |
| `CORS_ALLOWED_ORIGIN_PATTERN` | — | **Test project only:** `^https://sabong-[a-z0-9-]+-<vercel-team-slug>\.vercel\.app$` (matches Vercel preview URLs). Unset on staging/production |
| `LOG_LEVEL` | `debug` | `info` (debug detail off: Blueprint's `APP_DEBUG=false`) |
| `MATCH_SUBMIT_MAX_AGE_MIN` | `30` | `30` |
| `DAILY_COIN_CAP` | `300` | tune per OQ-04 |

### Supabase project settings (dashboard / `config.toml`)

| Setting | Value |
|---|---|
| Auth: minimum password length | 8 |
| Auth: email confirmation | On |
| Auth: custom SMTP | Office 365 or Gmail SMTP (Blueprint email service) |
| Auth: MFA | TOTP enabled |
| Auth: anonymous sign-ins | On only if OQ-02 = yes |
| Auth: CAPTCHA | Turnstile or hCaptcha, on sign-up, sign-in and password reset |
| Auth: rate limits | Sign-in/verify attempts set to ~5 per 5 minutes per IP (closest supported setting) |
| Auth: JWT expiry | 3600 s (access); refresh token rotation on |
| Auth: Site URL / redirect URLs | Production: the production domain only. Staging: `https://staging.<domain>/**`. Test: `https://dev.<domain>/**` **and** `https://sabong-*-<vercel-team-slug>.vercel.app/**` so email confirmation and password-reset links work on Vercel previews |
| API: exposed schemas | `public` only |
| Database: SSL enforcement | On |
| Network restrictions (prod) | Restrict direct DB access to the CI runner and admin IPs |

---

## 5. Deployment phase activities (Blueprint SDLC)

| Activity | Output |
|---|---|
| Prepare the staging environment and deploy for final verification | `staging.<domain>` (Vercel) + `sabong-staging` (Supabase) live; UAT sign-off |
| User training and documentation | Short player guide (controls, rules, FAQ) in the app's Help page; admin guide for the catalog tools |
| Launch and rollout | Ramil merges to `main` and approves the deploy → production deploy on Vercel; custom domain + HTTPS verified; announcement; monitor the first 72 hours (Vercel deployment logs, Sentry, Supabase) |
| Initial technical support | Bug intake form → GitHub Issues; Sentry alerts to the developer |

---

## 6. Production security checklist (Blueprint, adapted)

- [ ] `APP_ENV=production`, `LOG_LEVEL=info` in Edge Function secrets (no debug detail in responses).
- [ ] Service role key, JWT secret and DB password exist **only** in Supabase/GitHub secrets. Never in Git, never in the frontend bundle (CI grep passes).
- [ ] `.env*` files are in `.gitignore`; `gitleaks` passes.
- [ ] **RLS enabled on every `public` table**; Supabase Security Advisor shows no errors.
- [ ] Every Edge Function route except health checks requires `requireAuth` (the equivalent of `auth:sanctum` on all routes except login/forgot-password).
- [ ] `security definer` functions have `set search_path = ''`, and `EXECUTE` is revoked from `anon`/`authenticated` where they are service-only.
- [ ] Token expiry configured (1 h access, rotating refresh). Blueprint's 24 h Sanctum token is replaced by short JWTs + refresh.
- [ ] Rate limiting active on sign-in, password reset (Supabase Auth + CAPTCHA) and Edge Functions.
- [ ] CORS restricted to the production frontend domain; the Vercel preview pattern exists **only** on the test project.
- [ ] Vercel Preview deployments are protected (Vercel Authentication), so unfinished builds are not public.
- [ ] No server-side secrets in Vercel env vars except build-only ones (`SENTRY_AUTH_TOKEN`); no `VITE_` variable holds a secret.
- [ ] HTTPS enforced (Supabase is HTTPS-only; Vercel serves HTTPS with automatic certificates, and `vercel.json` sets HSTS).
- [ ] Storage: `match-replays` private; avatar policies scoped to the owner's folder; size/MIME limits set; random UUID filenames.
- [ ] Audit logging active on catalog tables and admin actions.
- [ ] OpenAPI docs not publicly served.
- [ ] Security headers from `vercel.json` (§3.3) present on production (check with `curl -I` or securityheaders.com): CSP with scripts from self only, `connect-src` limited to the Supabase project, Sentry and the CAPTCHA provider.
- [ ] No real-money features exist (NFR-LEGAL-01).

**Data protection note:** the game stores only email, username, display name, avatar and gameplay data. No government IDs are collected, so the Blueprint's "encrypted cast for government identifiers" rule does not apply. If personal data beyond this is ever added, encrypt it at rest (pgsodium/Vault) and update this document. A privacy notice that follows the Philippine Data Privacy Act of 2012 is shown at registration.

---

## 7. Maintenance (Blueprint SDLC "Maintenance")

| Activity | How |
|---|---|
| Monitor performance & availability | Supabase dashboard (API/DB metrics), Sentry (frontend errors, release health), Vercel deployment logs, optional Vercel Speed Insights (real-user Web Vitals), uptime check on the frontend URL and `GET /functions/v1/matches/health` |
| Technical support | GitHub Issues with severity labels; Critical fixed within 24 h |
| Updates & patches | Monthly dependency updates (Dependabot); Supabase CLI/platform updates; Babylon minor versions after a determinism + FPS check |
| Enhancements | New requirement IDs in the specs first → tasks → PRs (spec-driven loop) |
| Backups | Supabase daily backups; a monthly restore drill on the test project |
| Sim version hygiene | Delete old `sim/versions/*` once no `in_progress` match uses them |
