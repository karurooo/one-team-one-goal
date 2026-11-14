# Implementation Tasks — Release 1 (MVP)

| Field | Value |
|---|---|
| SDLC phase | Development |
| Status | Draft v0.1. Starts after Design sign-off |
| How to use | Each task has an **Owner** (see Team & ownership). Work top to bottom inside your track. Ramil reviews and merges every PR. A task is **done** only when its "Done when" checks pass and CI is green. Tick the box in the same PR. Every PR references task + requirement IDs |

Legend: **Owner** = who builds it · **Support** = who helps or reviews the shared part · **Req** = requirement IDs implemented · **Dep** = tasks that must be done first.

---

## Team & ownership

| Person | Role | Track | Owns (paths) |
|---|---|---|---|
| **Ramil** | Reviewer / approver | — | Approves and merges every PR on GitHub (Blueprint: 1 approval per PR), approves production deploys (GitHub Environment `production`), manages the GitHub org/repo settings, branch protection and secrets |
| **Carlo** | Project owner + developer | **Game client:** 3D rendering, animation, camera, input, VFX, HUD, fight flow, asset pipeline | `frontend/src/game/**`, `tools/blender/**`, `features/match/**`, `features/settings/**`, `frontend/public/models/**`. Also: specs, open questions, design sign-off, UAT (T-QA-05) |
| **Cliff** | Developer | **Gameplay logic, then app screens:** simulation, bot, replay; later auth/profile/roster/history screens | `supabase/functions/_shared/sim/**`, `features/auth/**`, `features/profile/**`, `features/manok/**`, `features/leaderboard/**` |
| **Patrick** | Developer | **Platform:** repo, CI, Vercel, database, Edge Functions, app shell | `supabase/migrations`, `supabase/tests`, `supabase/functions/*` (except `_shared/sim`), `_shared/schemas`, `_shared/http`, `frontend/src/{lib,providers,config,components,app,types,stores}`, `.github/`, `frontend/vercel.json` |

**Workload:** Patrick 23 tasks, Cliff 18, Carlo 15. The counts differ, but the effort is close: Patrick's tasks are many small setup and backend pieces; Cliff's simulation and Carlo's 3D client are the two heaviest areas. Cliff moves to app screens once the simulation is done. Tracks can be swapped between people without changing the plan.

### Parallel plan

| Phase | Cliff | Carlo | Patrick | Sync point |
|---|---|---|---|---|
| 1 | T-SIM-01 → T-SIM-03 (pure TS, Vitest only) | T-ART-01, T-ART-02 (in-place clips, new dodge/skill clips); Babylon spike with the prototype `manok.glb` | T-SETUP-01/02/03/05/06/07: repo, CI, Vercel, Supabase local, CODEOWNERS | **H1:** repo + CI ready → everyone works in the monorepo |
| 2 | T-SETUP-04, T-SIM-04 → T-SIM-08 | T-GAME-01, T-GAME-02, T-GAME-05 against a **stub sim** (simple movement only) | T-DB-01 → T-DB-05, T-API-01, T-FE-01, T-FE-02 | **H2:** Cliff freezes `sim/types.ts` (`SimState`, `MatchConfig`, `MatchResult`, `SimEvent`, input log) → Carlo swaps the stub for the real sim; Patrick writes the match schemas |
| 3 | T-SIM-09, T-SIM-10 (bot, replay, golden fixtures) | T-GAME-03, T-GAME-04, T-GAME-06 (ManokView, camera, VFX/audio) | T-API-02, T-DB-06, T-SETUP-08 | **H3:** `replay()` + fixtures done → Patrick builds T-API-03 |
| 4 | T-FE-03 → T-FE-07 (auth, MFA, guest, profile, roster) | T-GAME-07, T-GAME-09, T-FE-08 (HUD, lobby preview, settings) | T-API-03, T-API-04, T-API-05 | **H4:** `POST /matches` + submit live on the test project → Carlo builds T-GAME-08 |
| 5 | T-FE-09, T-QA-01 (history, tuning) | T-GAME-08, T-GAME-10, T-QA-02 (fight flow, fallbacks, performance) | T-QA-03, T-QA-04 (accessibility, security) | **H5:** full loop on a Vercel preview → Alpha (T-QA-05) |
| 6 | Bug fixes | T-QA-05 (Alpha → Beta → UAT) | T-REL-01 (staging, launch), bug fixes | UAT sign-off → Ramil approves the production deploy |

### Handoff contracts (agree on these before building on them)

| Contract | Producer | Consumers | Defined in |
|---|---|---|---|
| Sim public API + `SimState`/`SimEvent` types | Cliff | Carlo (rendering, fight loop), Patrick (replay in Edge Function) | game-engine-design §2.5 |
| Edge Function request/response schemas (`_shared/schemas`) incl. `MatchConfig` | Patrick | Carlo (fight flow), Cliff (screens) | api-design §6 |
| `ManokPreview3D` component props | Carlo | Cliff (lobby/roster/manok screens) | ui-ux-design §4 |
| App shell, `ProtectedRoute`, `lib/axios`, `lib/supabase`, query keys | Patrick | Cliff, Carlo | architecture §4, ui-ux-design §5 |

Changing a contract means updating the spec in the same PR and getting a review from each consumer.

### Review rules
- **Ramil approves and merges every PR.** No self-merges; branch protection on `development`, `staging` and `main` requires his approval and green CI.
- A PR that touches another developer's owned paths also needs that developer's review (enforced with `CODEOWNERS`; Ramil is listed on `*` so he is requested on every PR).
- Merges to `staging` and `main` are done by Ramil. The production deploy job waits for his approval in the GitHub `production` Environment.

---

## M0 — Foundation & tooling

- [ ] **T-SETUP-01 Monorepo skeleton.** `Owner: Patrick` Create the folder structure from architecture §3, root `package.json`, `.editorconfig`, `.gitignore` (includes `.env*`), README.
  Done when: `npm install` works at root; the structure matches the spec. · Req: C1
- [ ] **T-SETUP-02 Frontend app.** `Owner: Patrick` · Support: Carlo (Babylon deps) (Babylon deps, `@sim` alias) Vite + React + TS (strict flags from conventions §2), Tailwind, shadcn init (components from Blueprint list), react-router-dom, TanStack Query, Zustand, RHF + Zod, Sonner, next-themes, lucide-react, Sentry, vite-plugin-pwa. Path aliases `@/`, `@sim`, `@schemas`.
  Done when: `npm run dev` shows a placeholder lobby; `npm run build` succeeds. · Dep: T-SETUP-01
- [ ] **T-SETUP-03 Supabase project.** `Owner: Patrick` `supabase init`, `config.toml` (auth: min password 8, email confirm on, anonymous sign-ins on, CAPTCHA settings, rate limits), `deno.json` import map (`zod`, `hono`, `@supabase/supabase-js`).
  Done when: `supabase start` runs locally; Studio opens. · Dep: T-SETUP-01
- [ ] **T-SETUP-04 Shared code wiring.** `Owner: Cliff` · Support: Patrick `_shared/sim` and `_shared/schemas` importable from Vite **and** Deno (architecture §3.1).
  Done when: one sample schema and one sample sim function are imported by a frontend test and a Deno test, and both pass. · Dep: T-SETUP-02, T-SETUP-03
- [ ] **T-SETUP-05 Lint/format/hooks.** `Owner: Patrick` CODEOWNERS (Team & ownership paths), ESLint (incl. sim restricted globals), Prettier, deno lint/fmt, sqlfluff, Husky + lint-staged + commitlint.
  Done when: a bad commit message and an `any` are both rejected locally. · Req: NFR-MAINT-01
- [ ] **T-SETUP-06 CI pipeline.** `Owner: Patrick` `.github/workflows/ci.yml` per deployment §3.1 and `deploy.yml` (Supabase backend only, job name `backend-deploy`) per §3.2.
  Done when: a PR runs all jobs and blocks merge on failure. · Dep: T-SETUP-05
- [ ] **T-SETUP-07 Vercel project.** `Owner: Patrick` Import the repo in Vercel (root `frontend`, Vite preset), add `frontend/vercel.json` (deployment §3.3), set env vars per environment and branch, branch domains for `staging`/`development`, Preview protection, required check `backend-deploy` before builds.
  Done when: a PR gets a working preview URL; deep links (e.g. `/roster`) reload without 404; security headers show on the preview. · Req: NFR-SEC-02/03
- [ ] **T-SETUP-08 Optional local Docker.** `Owner: Patrick` `frontend/Dockerfile` (Node 20, Vite dev server) + `docker-compose.yml` for anyone who prefers containers. Not used for deploys.

## M1 — Simulation core (no rendering)

- [ ] **T-SIM-01 Math & RNG.** `Owner: Cliff` Fixed-point helpers, generated trig tables, `isqrt`, `sfc32` + seed splitting.
  Done when: unit tests pass; the trig generator script output matches the committed table. · Req: NFR-DET-01
- [ ] **T-SIM-02 State & input.** `Owner: Cliff` `types.ts`, `createInitialState`, InputFrame bit layout, RLE log encode/decode.
  Done when: round-trip tests encode/decode 10k random frames identically.
- [ ] **T-SIM-03 Movement.** `Owner: Cliff` Facing toward the opponent, acceleration, arena clamp, body push.
  Done when: tests cover the clamp at the arena edge and the push symmetry.
- [ ] **T-SIM-04 Actions & combat.** `Owner: Cliff` Tuka, Sipa, Lipad (arc, strike window), Ilag (i-frames), hitstun, input buffer, dodge-cancel, frame data from `data/actions.ts`.
  Done when: frame-data tests assert exact startup/active/recovery ticks and hit/miss by range and arc. · Req: FR-FIGHT-02
- [ ] **T-SIM-05 Meters.** `Owner: Cliff` Hingal costs/regen/exhausted; Tapang changes/regen. · Req: game-design §7–8
- [ ] **T-SIM-06 Referee.** `Owner: Cliff` Phases, hit-pause, 90 s timer, KO, timeout tiebreaks, Talikod → Sentensya window (max 2 survivals), forfeit. · Req: FR-FIGHT-04, AC-FIGHT-04/04b
- [ ] **T-SIM-07 Clash.** `Owner: Cliff` Detection, prompt window, early "mash" loss, resolution. · Req: game-design §6.2
- [ ] **T-SIM-08 Talisayin skill & passive** `Owner: Cliff` (`banat`, `sigla`).
- [ ] **T-SIM-09 Bot.** `Owner: Cliff` Observation delay buffer, utility scoring, difficulty profiles, clash behavior.
  Done when: in 1,000 headless bot-vs-bot matches there are no exceptions, every match ends ≤ 7,200 ticks, and Hard beats Easy ≥ 75% of the time. · Req: FR-FIGHT-01
- [ ] **T-SIM-10 Hash, replay, golden fixtures, determinism CI.** `Owner: Cliff` `hashState`, `replay`, 10 golden fixtures, a CI job that runs fixtures in Node **and** Deno (plus Chromium/Firefox/WebKit through Playwright).
  Done when: hashes are identical across all runtimes. · Req: FR-MATCH-02, NFR-DET-01

## M2 — Database & backend

- [ ] **T-DB-01 Enums, `profiles`, triggers** `Owner: Patrick` (`handle_new_user`, `set_updated_at`), helpers `is_admin`, `is_active_user`, RLS + column grants. · Req: FR-AUTH-01, FR-PROF-01/02, AC-PROF-02, AC-AUTH-07
- [ ] **T-DB-02 Catalog tables** `Owner: Patrick` `skills`, `breeds`, `taris` + RLS + `check_breed_skill_kinds` + `seed.sql` (R1 rows). · Req: FR-MANOK-03
- [ ] **T-DB-03 `manoks`, `profile_taris`** `Owner: Patrick` + starter unique index + `grant_starter_manok()`. · Req: FR-MANOK-01/02, AC-MANOK-01
- [ ] **T-DB-04 `matches`, `coin_ledger`, `audit_logs`, `rate_limits`** `Owner: Patrick` + `start_match()`, `complete_match()` (reward formula, daily cap, idempotency) + views. · Req: FR-MATCH-01/03/04, AC-MATCH-02b, AC-MATCH-03
- [ ] **T-DB-05 Storage buckets & policies** `Owner: Patrick` (`avatars`, `match-replays`). · Req: FR-PROF-04
- [ ] **T-DB-06 pgTAP suite** `Owner: Patrick` for all RLS rules and SQL functions (test-plan §3).
- [ ] **T-API-01 `_shared/http`.** `Owner: Patrick` Envelope helpers, error mapping, request id, CORS (exact origins + optional Vercel-preview regex on the test project), `requireAuth`, `requireActive`, `requireRole`, `validate`, `rateLimit`, config loader.
  Done when: Deno tests cover each middleware. · Req: api-design §3, §5
- [ ] **T-API-02 `manoks` function:** `Owner: Patrick` `POST /manoks/starter`. · Req: AC-MANOK-01
- [ ] **T-API-03 `matches` function:** `Owner: Patrick` · Support: Cliff (replay) (replay) `POST /matches`, `POST /matches/{id}/submit` (replay verify, replay upload, `complete_match`), `POST /matches/{id}/forfeit`.
  Done when: Deno tests cover happy path, tampered log → 422, double submit → 409 with same rewards, expired match, other user's match → 404; replay benchmark < 50 ms. · Req: FR-MATCH-01/02/03, AC-FIGHT-05
- [ ] **T-API-04 `profiles` function:** `Owner: Patrick` `POST /profiles/convert-guest`. · Req: FR-AUTH-06
- [ ] **T-API-05 OpenAPI generation** `Owner: Patrick` (`npm run docs:openapi`).

## M3 — Frontend foundation & menus

- [ ] **T-FE-01 Core libs:** `Owner: Patrick` `lib/supabase.ts`, `lib/axios.ts` (interceptors per api-design §9), `config/env.ts`, `types/api.ts` (`ApiResponse<T>`, `ApiError`), generated `database.types.ts`, providers (Query, Theme, Sentry, PWA). · Req: AC-AUTH-SESSION
- [ ] **T-FE-02 App shell & routing:** `Owner: Patrick` AppShell, `ProtectedRoute`, `RoleGate`, all R1 routes as stubs, NotFound, error boundary. · Req: ui-ux §2
- [ ] **T-FE-03 Auth feature:** `Owner: Cliff` login, register, forgot/reset password, CAPTCHA, logout, inactive-account handling, server-error mapping. · Req: FR-AUTH-01/02/03/05/07
- [ ] **T-FE-04 MFA (TOTP):** `Owner: Cliff` enroll, verify, challenge at login. · Req: FR-AUTH-04
- [ ] **T-FE-05 Guest play & conversion.** `Owner: Cliff` · Req: FR-AUTH-06 (Could)
- [ ] **T-FE-06 Profile feature:** `Owner: Cliff` view/edit, avatar upload (2 MB, preview, UUID filename). · Req: FR-PROF-01..04
- [ ] **T-FE-07 Manok feature:** `Owner: Cliff` · Support: Carlo (`ManokPreview3D`) (3D preview hook-up) roster, detail, rename, starter grant on first lobby load. · Req: FR-MANOK-01..04
- [ ] **T-FE-08 Settings feature:** `Owner: Carlo` audio, quality, reduce motion, theme, key bindings (persisted `settingsStore`). · Req: FR-SET-01..04, NFR-A11Y-02
- [ ] **T-FE-09 Match history:** `Owner: Cliff` TanStack Table with server pagination; match detail page. · Req: FR-MATCH-04

## M4 — Game client

- [ ] **T-ART-01 Asset pipeline:** `Owner: Carlo` move `build_manok.py` into `tools/blender/`; strip root translation from clips (in-place); `npm run assets:build` with gltf-transform meshopt. · Req: NFR-PERF-04
- [ ] **T-ART-02 Missing clips:** `Owner: Carlo` `Ilag_Dodge`, `Banat_Combo`; align the key poses listed in engine §5.3.
- [ ] **T-GAME-01 Engine & loop:** `Owner: Carlo` Babylon engine/scene lifecycle, fixed-step loop, pause on hidden tab, dispose on unmount. · Req: NFR-PERF-02
- [ ] **T-GAME-02 Arena & lighting:** `Owner: Carlo` ruweda, quality tiers, blob shadows, toon material + outline. · Req: FR-SET-02, NFR-PERF-01
- [ ] **T-GAME-03 ManokView:** `Owner: Carlo` · Support: Cliff (sim state fields) sim-driven animation sync, in-place root, procedural hackles/head/jiggle, interpolation.
- [ ] **T-GAME-04 Camera:** `Owner: Carlo` midpoint tracking, zoom by separation, shake (respects reduce motion).
- [ ] **T-GAME-05 Input:** `Owner: Carlo` keyboard, gamepad, edge-triggered sampling, world-space direction conversion, rebinding support. · Req: FR-FIGHT-06
- [ ] **T-GAME-06 VFX & audio:** `Owner: Carlo` pooled particles, hit-pause visuals, KO slow-motion, sound events. · Req: game-design §15
- [ ] **T-GAME-07 Bridge & HUD:** `Owner: Carlo` `hudStore` at 20 Hz, event emitter, HUD organisms, prompts (Clash, Sentensya, KO). · Req: FR-FIGHT-03
- [ ] **T-GAME-08 Fight flow:** `Owner: Carlo` · Support: Patrick (API), Cliff (result screen) (fight events) difficulty picker → `POST /matches` → fight → submission queue (IndexedDB, retry) → result page; pause menu & forfeit. · Req: FR-FIGHT-01/04/05, FR-MATCH-01, NFR-REL-01
- [ ] **T-GAME-09 Lobby 3D preview.** `Owner: Carlo` · Req: ui-ux §3.1
- [ ] **T-GAME-10 WebGL capability check & fallbacks.** `Owner: Carlo` · Req: NFR-COMP-01

## M5 — Quality, security, release

- [ ] **T-QA-01 Playtest & tuning pass** `Owner: Cliff` · Support: Carlo (game feel) (game-design numbers; record changes and bump `SIM_VERSION`).
- [ ] **T-QA-02 Performance pass** `Owner: Carlo` against NFR-PERF-01..05 on the reference devices (test-plan §6).
- [ ] **T-QA-03 Accessibility pass** `Owner: Patrick` (axe in Playwright + manual keyboard run). · Req: NFR-A11Y-01
- [ ] **T-QA-04 Security checklist** `Owner: Patrick` (deployment §6), including RLS review and secret scan. · Req: NFR-SEC-01..03
- [ ] **T-QA-05 Alpha → Beta → UAT** `Owner: Carlo` · Support: Cliff, Patrick (bug fixes) Patrick (bug fixes) per test-plan §7.
- [ ] **T-REL-01 Staging deploy, user guide, launch** `Owner: Patrick` · Support: Ramil (production approval) per deployment §5: `staging.<domain>` on Vercel for UAT; production domain connected on Vercel; Instant Rollback tested once before launch.

---

## Traceability check (R1 "Must" requirements → tasks)

| Requirement | Tasks |
|---|---|
| FR-AUTH-01/02/03/05/07 | T-DB-01, T-FE-03 |
| FR-PROF-01/02/03 | T-DB-01, T-FE-06 |
| FR-MANOK-01..04 | T-DB-02, T-DB-03, T-API-02, T-FE-07 |
| FR-FIGHT-01..05 | T-SIM-*, T-GAME-*, T-API-03 |
| FR-FIGHT-06 (keyboard) | T-GAME-05 |
| FR-MATCH-01..04 | T-DB-04, T-API-03, T-GAME-08, T-FE-09 |
| FR-SET-01/02 | T-FE-08, T-GAME-02 |
| NFR-DET-01 | T-SIM-01, T-SIM-10 |
| NFR-SEC-01..03 | T-DB-*, T-API-01, T-QA-04 |
| NFR-PERF-01..05 | T-GAME-01/02, T-ART-01, T-QA-02 |
| NFR-REL-01 | T-GAME-08 |
| NFR-MAINT-01 | T-SETUP-05/06 |
