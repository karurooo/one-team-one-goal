# Test Plan

| Field | Value |
|---|---|
| SDLC phase | Testing |
| Baseline | Blueprint "Testing Requirements" (Pest → pgTAP + Deno test; Vitest + React Testing Library kept) and SDLC Testing phase (Alpha, Beta, UAT) |
| Status | Draft v0.1 |

---

## 1. Test levels and tools

| Level | Scope | Tool | Location | Runs in CI |
|---|---|---|---|---|
| Sim unit | Math, RNG, systems, frame data, bot | Vitest | `supabase/functions/_shared/sim/**/*.test.ts` | ✅ every PR |
| Determinism | Golden replays across runtimes | Vitest (Node), `deno test`, Playwright (Chromium/Firefox/WebKit) | `sim/__fixtures__/` | ✅ every PR |
| Database | Schema, constraints, RLS, SQL functions | **pgTAP** via `supabase test db` | `supabase/tests/*.test.sql` | ✅ every PR |
| Edge Functions | Middleware, controllers, services (against the local Supabase stack) | `deno test` | `supabase/functions/**/*.test.ts` | ✅ every PR |
| Frontend unit/component | Hooks, stores, forms, components | Vitest + happy-dom + React Testing Library | `frontend/src/**/*.test.ts(x)`, setup in `src/testing/` | ✅ every PR |
| E2E smoke | Critical flows in a real browser | Playwright | `frontend/e2e/` | ✅ on `development`/`staging` merges |
| Performance | FPS, load size, Lighthouse | Manual + Lighthouse CI | — | Lighthouse on staging |
| Playtest | Fun, readability, balance | Humans | Playtest log in `docs/04-testing/playtests/` | — |

---

## 2. Minimum coverage (Blueprint: "All CRUD operations, all movement types, all authorization scenarios")

Adapted to this project:

| Area | Must be covered |
|---|---|
| **All actions** ("movement types") | Every action in game-design §6: exact startup/active/recovery ticks; hit and miss by range, by arc, vs. airborne; buffer; dodge-cancel; anti-air; clash outcomes (early press, late press, nobody presses) |
| **All win conditions** | KO, timeout (each tiebreak step), Talikod survived, Talikod lost, third Talikod, forfeit, draw |
| **All authorization scenarios** | For every table: anon, player (own row), player (someone else's row), deactivated player, admin, service role, for each of select/insert/update/delete. Column grants: update of a forbidden column (`coins`, `role`, `wins`) is denied |
| **All commands** ("CRUD") | Every Edge Function route: success, validation 422, 401, 403 (inactive), 404 (not own), 409, 429 |
| **Economy invariants** | `profiles.coins = sum(coin_ledger.amount)`; one reward per match; daily cap at the Manila day boundary; no negative balances |
| Coverage gate | Sim ≥ 90% lines; Edge Functions ≥ 80%; frontend features ≥ 70% |

---

## 3. Key test cases

### 3.1 Database (pgTAP)

| ID | Case | Expected |
|---|---|---|
| DB-01 | New `auth.users` row | `profiles` row created with `player_` username, `role = player` |
| DB-02 | Player selects another player's `profiles` row | 0 rows |
| DB-03 | Player updates own `coins` | permission denied |
| DB-04 | Player updates own `display_name` | succeeds |
| DB-05 | Player inserts into `matches` / `coin_ledger` | permission denied |
| DB-06 | `grant_starter_manok` called twice | exactly one starter |
| DB-07 | `complete_match` called twice for the same match | second call refused; one ledger row |
| DB-08 | `complete_match` with `is_verified = false` | match saved, no stats/coins change |
| DB-09 | Daily cap at 290 coins earned, Hard win (50 + 50 bonus) | grants 10, cap flag true |
| DB-10 | Deactivated player selects own manoks | 0 rows |
| DB-11 | Breed with a passive skill in `skill_id` | insert rejected |
| DB-12 | Anonymous (`anon`) selects `breeds` | only active rows |

### 3.2 Edge Functions (Deno)

| ID | Case | Expected |
|---|---|---|
| API-01 | `POST /matches` without token | 401 envelope |
| API-02 | `POST /matches` with someone else's `manok_id` | 404 |
| API-03 | Valid start | 201, seed present, match row `in_progress` |
| API-04 | Submit an honest bot match (fixture) | 200, `is_verified = true`, coins granted |
| API-05 | Submit with one changed input frame but the original hash | 422 "Match could not be verified." |
| API-06 | Submit twice | 409 with the same reward data |
| API-07 | Submit after 30 minutes | 422 expired |
| API-08 | Invalid body (bad hash format) | 422 with `errors.final_hash` |
| API-09 | 31 starts in a minute | 31st → 429 with `Retry-After` |
| API-10 | CORS preflight from a non-allowed origin | no `Access-Control-Allow-Origin` |
| API-12 | CORS preflight from a Vercel preview URL | allowed on the test project; **refused** on staging/production |
| API-11 | Unexpected DB error | 500 generic message, no SQL in body, `x-request-id` present |

### 3.3 Frontend

| ID | Case | Expected |
|---|---|---|
| FE-01 | Register with a taken username (422) | error shown under the username field via `setError` |
| FE-02 | Any API 401 | signed out, redirected to `/login` |
| FE-03 | 403 / 429 / 500 | Sonner toast with the right text |
| FE-04 | Form validation timing | error appears on blur, clears on change |
| FE-05 | Submit button | disabled + "Saving…" while submitting |
| FE-06 | Match history | loading skeleton, empty state, error + retry, pagination |
| FE-07 | Submission queue | network off at match end → queued; back online → submitted once |
| FE-08 | HUD store | publishes ≤ 20 times/second during a fight |
| FE-09 | FightView unmount | Babylon engine disposed, no listeners left (no memory growth across 10 fights) |

### 3.4 E2E smoke (Playwright)

1. Register → confirm (local Inbucket) → login → lobby shows the starter manok.
2. Start an Easy bot fight → a scripted input sequence wins by KO → result page shows verified rewards → match appears in history.
3. Forfeit → loss recorded.
4. Settings change persists after reload.
5. Admin-only route redirects a normal player.
6. Deep-link reload on the deployed site (`/roster`, `/matches/<id>`) loads the app, not a 404 (Vercel rewrite).
7. Password-reset email link opened on a Vercel preview lands on `/reset-password` of that preview.

---

## 4. Non-functional tests

| ID | Requirement | Method | Pass |
|---|---|---|---|
| NF-01 | NFR-DET-01 | Golden fixtures in Node, Deno, Chromium, Firefox, WebKit | identical hashes |
| NF-02 | Replay budget | `deno bench` replaying a 7,200-tick match | < 50 ms |
| NF-03 | NFR-PERF-01 | 3-minute bot fight on reference devices, FPS logged by a debug overlay | avg ≥ 60 (laptop, Medium), ≥ 30 (phone, Low); 1% low ≥ 45 / 25 |
| NF-04 | NFR-PERF-03 | High-speed video or `performance` marks: key press → first pose change | ≤ 3 frames |
| NF-05 | NFR-PERF-04/05 | Bundle analyzer + Lighthouse CI on `staging.<domain>` (Vercel) | ≤ 6 MB first load; score ≥ 80 |
| NF-06 | NFR-SEC-* | RLS matrix tests, `gitleaks` in CI, bundle grep for `service_role` | no findings |
| NF-07 | NFR-A11Y-01 | axe-core in Playwright on all menu routes + manual keyboard-only run | no serious/critical issues |

Reference devices: a mid-range laptop with integrated graphics (2020 or newer), a mid-range Android phone (~2022, Chrome), an iPhone (≥ iPhone 12, Safari).

---

## 5. Balance & playtest protocol

- **Automated:** each release, run 2,000 Hard-bot mirror matches per breed pair (headless sim). No breed may win more than **55%** (game-design §11).
- **Human playtests:** 5+ testers, 15 minutes each, recorded. Collect: "Could you tell what the bot was about to do?", "Did any hit feel unfair?", first-win time, quits. Log numeric tuning changes and the new `SIM_VERSION`.

---

## 6. SDLC testing stages (Blueprint)

| Stage | Who | Environment | Entry | Exit |
|---|---|---|---|---|
| Unit & integration | Task owner | Local + CI | Task done | CI green |
| **Alpha** | Carlo, Cliff, Patrick (each tests the other tracks' features); Ramil spot-checks | Test Site | All R1 Must tasks done | No open Critical/High bugs |
| **Beta** | Selected players (10–20) | Test Site | Alpha exit | Feedback triaged; crash-free sessions ≥ 99% (Sentry) |
| **UAT** | Project owner against the acceptance criteria | Staging (`staging.<domain>` on Vercel) | Beta exit | All R1 AC-* pass; **Certificate of Acceptance** signed |

Bug severity: **Critical** (crash, data loss, economy exploit, security), **High** (feature unusable, desync), **Medium** (workaround exists), **Low** (cosmetic).
