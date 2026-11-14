# Development Conventions & Coding Standards

| Field | Value |
|---|---|
| SDLC phase | Development |
| Baseline | Blueprint "Naming Conventions", "Coding Standards & Best Practices", "Git Workflow", "IDE Extensions". PHP/Laravel rules are replaced by the TypeScript (Deno) and SQL rules below |

---

## 1. Naming conventions

### 1.1 Database (unchanged from Blueprint)

| Convention | Rule |
|---|---|
| Table names | `snake_case`, plural (`manoks`, `coin_ledger`*, `profile_taris`) |
| Foreign keys | `{table_singular}_id` (`profile_id`, `manok_id`, `breed_id`) |
| Timestamps | Every table has `created_at` and `updated_at` (`timestamptz`) |
| Soft deletes | `deleted_at` on master tables (`profiles`, `manoks`, `breeds`, `skills`, `taris`) |
| Boolean flags | `is_` prefix (`is_active`, `is_verified`, `is_starter`, `is_guest`) |
| Enum types | `snake_case` singular (`match_status`, `result_reason`) |
| Functions | `snake_case` verb-first (`complete_match`, `grant_starter_manok`, `is_admin`) |
| Policies | `"<table>: <role> can <action> <scope>"`, e.g. `"manoks: authenticated can select own"` |
| Migrations | `YYYYMMDDHHMMSS_<snake_case_description>.sql` |

\* `coin_ledger` is a ledger (collective noun), so it is accepted as the plural form.

### 1.2 TypeScript / React (Blueprint)

| Type | Convention | Example |
|---|---|---|
| Components | PascalCase `.tsx` | `MatchHistoryTable.tsx`, `MeterBar.tsx` |
| Hooks | camelCase, `use` prefix | `useMyManoks`, `useSubmitMatch` |
| API files | camelCase | `matches.ts`, `manoks.ts` |
| Types/Interfaces | PascalCase | `Manok`, `MatchResult`, `ApiResponse<T>` |
| Stores | camelCase + `Store` | `authStore.ts`, `settingsStore.ts`, `hudStore.ts` |
| Zod schemas | camelCase + `Schema` | `startMatchSchema`, `renameManokSchema` |
| Constants | `SCREAMING_SNAKE_CASE` | `SIM_VERSION`, `TICK_MS` |

### 1.3 Edge Functions (replaces PHP/Laravel naming)

| Type | Convention | Example |
|---|---|---|
| Function folder | kebab-case domain, plural | `matches/`, `manoks/`, `profiles/` |
| Controller file | camelCase + `Controller` | `matchController.ts` |
| Service file | camelCase + `Service` | `matchService.ts` |
| Repository file | camelCase + `Repository` | `matchRepository.ts` |
| Request schema | Action + Model + `Request` (type) / `Schema` (value) | `StartMatchRequest`, `startMatchSchema` |
| Resource mapper | `to` + Model + `Resource` | `toMatchResource()` |
| Tests | `<file>.test.ts` next to the file | `matchService.test.ts` |

### 1.4 Simulation

- Pure functions or `system(state)` mutators. No classes holding hidden state.
- Units are in names when not obvious: `distanceMm`, `angleBau` (binary angle units), `durationTicks`.

---

## 2. TypeScript standards (Blueprint, applies to frontend, Edge Functions and sim)

- `strict: true`, plus `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`.
- **No `any`** (`@typescript-eslint/no-explicit-any: error`). Use `unknown` + narrowing.
- Functional React components only; no class components (except the error boundary if the chosen library needs one).
- Custom hooks hold data fetching and business logic; components stay presentational where possible.
- Colocate component-specific types with the component.
- Handle loading, error and empty states for every data-driven component.
- Use `React.memo`, `useMemo` and `useCallback` judiciously, mainly around the HUD and tables.
- **Never use `dangerouslySetInnerHTML`** with user data (usernames, display names, manok names).
- `lodash-es` with named imports only. Never inside `_shared/sim`.
- The game loop and Babylon code must not create objects per frame in hot paths. Reuse vectors (`TmpVectors`) and pooled particles.

### Edge Function standards (replaces "PHP / Laravel Standards")

- Controllers are **thin**: get validated input → call the service → return the envelope.
- Services hold all business logic. Multi-step writes call **one** transactional SQL function.
- Repositories are the only place that calls `supabase.from()` / `.rpc()` / `.storage`.
- Never return raw rows. Map through resource mappers.
- Never trust identity from the body. Use the `userId` from the verified JWT.
- Never log secrets, tokens or full input logs. Log the `request_id`, user id and error code.
- Use `Deno.env.get()` only in `_shared/config.ts` (validated with Zod at startup).

### SQL standards

- Lowercase keywords are fine, but be consistent. Format with **sqlfluff** (dialect `postgres`).
- `security definer` functions **must** `set search_path = ''` and use schema-qualified names.
- Use explicit `grant`/`revoke` for every function and table. The default is no access.
- Wrap RLS helper calls in `(select …)` for performance.
- Avoid N+1 queries: use embedded selects in PostgREST queries and views for lists.

---

## 3. Lint, format, hooks (Blueprint "IDE Extensions" / "Git Hooks")

| Tool | Scope | Config |
|---|---|---|
| ESLint (flat config) | `frontend/`, `supabase/functions/` | `typescript-eslint` strict, `react-hooks`, `jsx-a11y`, import order; **sim restricted-globals rule** |
| Prettier | All TS/TSX/JSON/MD | 2 spaces, single quotes, trailing commas, 100 cols |
| `deno lint` + `deno check` | `supabase/functions/` | `deno.json` |
| sqlfluff | `supabase/migrations`, `supabase/tests` | `.sqlfluff` |
| `supabase db lint` | Database | Run in CI |
| Husky + lint-staged | Repo root | see below |
| commitlint | Commit messages | Conventional types from the Blueprint |

Recommended VS Code extensions: ESLint, Prettier, Deno (enabled only for `supabase/functions`), Tailwind CSS IntelliSense, sqlfluff, Babylon.js (optional).

**Husky hooks** (Blueprint: pre-commit, post-commit, commit message):

| Hook | Runs |
|---|---|
| `pre-commit` | `lint-staged` (eslint --fix, prettier, sqlfluff on staged files); `deno fmt --check` on staged function files |
| `commit-msg` | `commitlint` (type must be one of `feat`, `fix`, `style`, `refactor`, `chore`, `docs`, `test`) |
| `post-commit` | Reminder if `supabase/migrations` changed but `frontend/src/types/database.types.ts` did not |
| `pre-push` | `npm run typecheck && npm run test:sim` (fast checks) |

---

## 4. Git workflow (Blueprint, unchanged)

- **Flow:** feature branch → `development` (testing) → `staging` (pre-production) → `main` (production).
- **Code review:** every PR needs **Ramil's approval** (Blueprint: at least one approval), and Ramil merges. PRs that touch another developer's owned paths also need that developer's review (`CODEOWNERS`, see tasks.md "Team & ownership"). CI must pass. No self-merges.
- **Branch naming:** `feat/name-of-feature`, `fix/name-of-fix` (also allowed: `docs/…`, `chore/…`, `refactor/…`, `test/…`).
- **Commit message format:**

```
feat: describe what is the feature to be created
fix: describe fix no.1; describe fix no.2;
style: describing the change of style
refactor: rewrite/restructure code, however does not change any behavior
chore: miscellaneous commit, does not belong above
docs: describe document related commits
test: describe test scenarios created
```

- **Spec traceability:** PR descriptions list the task and requirement IDs they implement (e.g. `Implements T-SIM-04 (FR-FIGHT-02, NFR-DET-01)`).
- **Spec changes first:** if implementation needs behavior that differs from a spec, update the spec in the same PR (or an earlier `docs:` PR). Code and specs must not disagree on `main`.

---

## 5. Environment variables (frontend)

Validated at startup with Zod in `src/config/env.ts`. The app refuses to start with a clear error if any are missing.

| Variable | Example | Notes |
|---|---|---|
| `VITE_SUPABASE_URL` | `http://127.0.0.1:54321` | Public |
| `VITE_SUPABASE_ANON_KEY` | `eyJ…` | Public (anon key only; **never** the service role key) |
| `VITE_FUNCTIONS_URL` | `${VITE_SUPABASE_URL}/functions/v1` | Axios base URL |
| `VITE_SENTRY_DSN` | — | Optional in dev |
| `VITE_CAPTCHA_SITE_KEY` | — | Turnstile/hCaptcha site key |
| `VITE_APP_VERSION` | `VERCEL_GIT_COMMIT_SHA` (set in `vite.config.ts` from Vercel's system env) | Sent to Sentry |

Values per environment live in **Vercel → Environment Variables** (deployment §4). Locally, `vercel env pull frontend/.env.local` downloads the Development set, or copy `.env.example`.

Backend secrets: see [deployment.md](../05-deployment/deployment.md) §4.
