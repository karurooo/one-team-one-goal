# Product Requirements Specification

| Field | Value |
|---|---|
| Project | **Sabong** — 3D web sabong fighting game |
| SDLC phase | Requirements Gathering (Waterfall, per ICT Blueprint 2026) |
| Status | Draft v0.1 — for review |
| Owner | Carlo S. Gaballo · Developers: Carlo, Cliff, Patrick · Reviewer/approver: Ramil |
| Related | [game-design.md](./game-design.md), [../02-design/architecture.md](../02-design/architecture.md) |

---

## 1. Vision

A competitive, skill-based 3D fighting game played in the browser. Each player picks a **manok** (gamecock) with its own skill and passive and fights inside a circular **ruweda** (pit). Players control the manok directly: they move, peck, kick, jump and dodge. Timing and spacing win fights, not stats or luck.

The game uses real sabong culture for flavor (ulutan, sentensyador, llamado/dehado, meron/wala, tari, derby) as a **stylized arcade fighter**. It is **not** a gambling product.

## 2. Goals and non-goals

### Goals
- G1. A fight that is fun and readable against a bot within the first release (MVP).
- G2. Skill expression: attack telegraphs, spacing, stamina management, jump timing.
- G3. Built on the ICT Blueprint 2026 conventions, with **Supabase** replacing the Laravel backend.
- G4. An architecture that can grow into online PvP without a rewrite (deterministic simulation).

### Non-goals (explicitly out of scope)
- NG1. **Real-money betting, cash-in or cash-out of any kind.** Any in-game currency is soft currency with no monetary value. (Online sabong/e-sabong is banned in the Philippines; app stores also restrict real-money gaming.)
- NG2. Realistic blood/gore or realistic depictions of animal injury. Damage is shown with stylized effects (feathers, flashes, "KO").
- NG3. Native mobile apps (the Blueprint's React Native stack is **not** used). Mobile browsers are supported through the PWA.
- NG4. Online real-time PvP in the MVP (planned for a later release, see §7).

## 3. Users and roles

| Role | Description | How assigned |
|---|---|---|
| Guest | Plays vs. bot without an account; progress is local only (Could-have, see FR-AUTH-06) | Supabase anonymous sign-in |
| Player | Registered user; owns manoks, earns coins, has match history | Default on sign-up |
| Admin | Manages reference data (breeds, skills, taris), moderates profiles | Set only by database migration/SQL; never from the client |

## 4. Release plan

| Release | Content |
|---|---|
| **MVP (R1)** | Accounts, one breed (Talisayin), bot fights (3 difficulties), HUD, match results saved and verified server-side, coins, roster, match history, settings |
| R2 | 3–5 breeds with skills and passives, tari loadouts, ulutan pre-fight phase, leaderboard (bot ladder) |
| R3 | Online PvP (ranked/unranked), llamado/dehado matchmaking labels |
| R4 | Derby mode (multi-manok rosters), Pintakasi timed events, Gamefarm (raising/breeding) |

Priority is given per requirement with **MoSCoW** (M = Must, S = Should, C = Could, W = Won't in this release).

---

## 5. Functional requirements

Acceptance criteria use the **EARS** pattern ("WHEN … THE SYSTEM SHALL …"). Every requirement has an ID; tasks and tests must reference these IDs.

### 5.1 Authentication and accounts (AUTH)

| ID | Requirement | Pri | Release |
|---|---|---|---|
| FR-AUTH-01 | Users can register with email and password. | M | R1 |
| FR-AUTH-02 | Users can log in and log out. | M | R1 |
| FR-AUTH-03 | Users can reset a forgotten password by email. | M | R1 |
| FR-AUTH-04 | Users can enable multi-factor authentication (TOTP). | S | R1 |
| FR-AUTH-05 | Login and password reset are rate-limited and protected by CAPTCHA. | M | R1 |
| FR-AUTH-06 | Guests can play vs. bot without registering and later convert to a full account, keeping progress. | C | R1 |
| FR-AUTH-07 | Deactivated accounts (`is_active = false`) cannot use the game. | M | R1 |

**Acceptance criteria**
- AC-AUTH-01: WHEN a user submits a valid, unused email and a password of 8+ characters, THE SYSTEM SHALL create the account, create a `profiles` row, and grant one starter manok.
- AC-AUTH-02: WHEN a user submits wrong credentials, THE SYSTEM SHALL show a generic "Invalid email or password" message and SHALL NOT reveal whether the email exists.
- AC-AUTH-05: WHEN login attempts from one client exceed the configured limit (target: 5 attempts per 5 minutes, per Blueprint), THE SYSTEM SHALL reject further attempts with HTTP 429 and show a "Too many attempts, try again later" toast.
- AC-AUTH-07: WHEN a user whose profile has `is_active = false` signs in, THE SYSTEM SHALL sign them out and show "Your account is deactivated."
- AC-AUTH-SESSION: WHEN any request returns 401, THE SYSTEM SHALL clear the session and redirect to `/login`.

### 5.2 Profile (PROF)

| ID | Requirement | Pri | Release |
|---|---|---|---|
| FR-PROF-01 | Each player has a public profile: unique username, display name, avatar. | M | R1 |
| FR-PROF-02 | Players can edit display name and avatar. | M | R1 |
| FR-PROF-03 | Profile shows win/loss record and coins. | M | R1 |
| FR-PROF-04 | Avatar upload accepts JPG/PNG/WebP up to 2 MB. | S | R1 |

- AC-PROF-01: WHEN a user picks a username that is taken (case-insensitive), THE SYSTEM SHALL show "Username already taken" under the field.
- AC-PROF-02: THE SYSTEM SHALL NOT allow a player to change `coins`, `role`, win/loss counts or `is_active` from the client.

### 5.3 Manok roster (MANOK)

| ID | Requirement | Pri | Release |
|---|---|---|---|
| FR-MANOK-01 | Each player owns one or more manoks. New players receive one starter Talisayin. | M | R1 |
| FR-MANOK-02 | Players can rename a manok (1–24 chars). | M | R1 |
| FR-MANOK-03 | Players can view each manok's breed, skill, passive and record. | M | R1 |
| FR-MANOK-04 | Players can pick which manok to fight with. | M | R1 |
| FR-MANOK-05 | Players can buy additional breeds with coins. | S | R2 |
| FR-MANOK-06 | Players can equip a tari (blade) per manok. | S | R2 |
| FR-MANOK-07 | Players can retire (soft delete) a manok, except their last one. | C | R2 |

- AC-MANOK-01: WHEN a profile is created, THE SYSTEM SHALL create exactly one starter manok (idempotent: retries never create a second one).
- AC-MANOK-07: WHEN a player tries to retire their only active manok, THE SYSTEM SHALL refuse with HTTP 422 and the message "You need at least one manok."

### 5.4 Bot fights (FIGHT)

| ID | Requirement | Pri | Release |
|---|---|---|---|
| FR-FIGHT-01 | Players can start a fight vs. a bot, choosing difficulty Easy, Normal or Hard. | M | R1 |
| FR-FIGHT-02 | The player controls the manok in real time (move, Tuka, Sipa, Lipad, Ilag) per the [Game Design](./game-design.md). | M | R1 |
| FR-FIGHT-03 | The HUD shows HP, Hingal (stamina), Tapang (courage), timer, Meron/Wala corners. | M | R1 |
| FR-FIGHT-04 | Fights end by KO, Talikod (sentensyador rule) or timeout, and show a result screen. | M | R1 |
| FR-FIGHT-05 | Players can pause a bot fight and forfeit. | M | R1 |
| FR-FIGHT-06 | Keyboard controls work; gamepad is supported; controls can be rebound. | M / S / C | R1 |
| FR-FIGHT-07 | Touch controls on mobile browsers. | C | R2 |
| FR-FIGHT-08 | Ulutan pre-fight phase. | S | R2 |

- AC-FIGHT-01: WHEN the player starts a bot fight, THE SYSTEM SHALL request a match from the server, receive a `match_id` and `seed`, and start the fight within 3 seconds on a broadband connection (assets cached).
- AC-FIGHT-04: WHEN a manok's HP reaches 0, THE SYSTEM SHALL end the fight with result reason `ko`.
- AC-FIGHT-04b: WHEN the 90-second round timer reaches 0, THE SYSTEM SHALL decide the winner by remaining HP %, then Tapang, then draw.
- AC-FIGHT-05: WHEN the player forfeits, THE SYSTEM SHALL record the match as a loss with reason `forfeit`.

### 5.5 Match results and rewards (MATCH)

| ID | Requirement | Pri | Release |
|---|---|---|---|
| FR-MATCH-01 | Every finished fight is submitted to the server and saved. | M | R1 |
| FR-MATCH-02 | The server verifies the result by replaying the fight from the seed and the input log before granting rewards. | M | R1 |
| FR-MATCH-03 | Wins grant coins by difficulty; a daily cap limits bot-farming. | M | R1 |
| FR-MATCH-04 | Players can view their match history (paginated) and details of each match. | M | R1 |
| FR-MATCH-05 | Players can watch a replay of a past match. | C | R2 |

- AC-MATCH-02: WHEN the replayed final-state hash does not equal the submitted hash, THE SYSTEM SHALL save the match with `is_verified = false`, grant no rewards, and respond 422 "Match could not be verified."
- AC-MATCH-02b: WHEN a match is submitted twice, THE SYSTEM SHALL grant rewards at most once (idempotent by `match_id`).
- AC-MATCH-03: WHEN a player has reached the daily coin cap, THE SYSTEM SHALL still save verified wins but SHALL grant 0 coins and say so on the result screen.

### 5.6 Leaderboard (LEAD)

| ID | Requirement | Pri | Release |
|---|---|---|---|
| FR-LEAD-01 | Public leaderboard of verified bot-ladder points (R2) and ranked rating (R3). | S | R2 |

### 5.7 Settings (SET)

| ID | Requirement | Pri | Release |
|---|---|---|---|
| FR-SET-01 | Audio volume (master, music, effects). | M | R1 |
| FR-SET-02 | Graphics quality (Low / Medium / High) and a frame-rate limit. | M | R1 |
| FR-SET-03 | Light/dark theme for menus. | S | R1 |
| FR-SET-04 | Key rebinding. | C | R1 |

Settings are stored per device (localStorage); they need not sync between devices.

### 5.8 Administration (ADMIN)

| ID | Requirement | Pri | Release |
|---|---|---|---|
| FR-ADMIN-01 | Admins can create/edit breeds, skills, passives and taris (reference data). | S | R2 |
| FR-ADMIN-02 | Admins can deactivate a player profile. | S | R2 |
| FR-ADMIN-03 | All admin changes are written to the audit log. | M | R2 |

### 5.9 Online PvP (PVP) — future

| ID | Requirement | Pri | Release |
|---|---|---|---|
| FR-PVP-01 | Matchmaking for 1v1 fights by rating. | M | R3 |
| FR-PVP-02 | Real-time online fight with input delay/rollback netcode. | M | R3 |
| FR-PVP-03 | Llamado/Dehado labels by rating difference; Dehado wins grant bonus rewards. | S | R3 |

PvP will get its own requirements and design document before R3 starts.

---

## 6. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-PERF-01 | Performance | The fight renders at **60 FPS** on a mid-range laptop (integrated GPU, 2020+) at Medium quality; at least **30 FPS** on a mid-range phone at Low quality. |
| NFR-PERF-02 | Performance | The game simulation runs at a fixed **60 ticks/second**, independent of render frame rate. |
| NFR-PERF-03 | Performance | Input-to-visible-response latency ≤ **3 frames** (~50 ms) locally. |
| NFR-PERF-04 | Load | First load (cold cache) ≤ **6 MB** transferred before the lobby is usable; a manok model ≤ 1 MB. |
| NFR-PERF-05 | Load | Lighthouse Performance score ≥ 80 on the lobby page. |
| NFR-DET-01 | Determinism | Given the same seed, manok setup and input log, the simulation produces the **same final-state hash** in every supported browser and in the Supabase Edge Function runtime. |
| NFR-SEC-01 | Security | All tables have Row Level Security enabled; the client can never write coins, results, roles or ratings directly. |
| NFR-SEC-02 | Security | All security items in the Blueprint's Production Security Checklist (adapted in [deployment.md](../05-deployment/deployment.md)) are met before launch. |
| NFR-SEC-03 | Security | No secrets (service-role key, JWT secret, DB password) in the frontend bundle, in Git, or in Vercel environment variables. |
| NFR-COMP-01 | Compatibility | Latest two versions of Chrome, Edge, Firefox, Safari (desktop) and Chrome Android / Safari iOS. WebGL2 required; WebGPU optional. |
| NFR-A11Y-01 | Accessibility | Menus meet WCAG 2.1 AA (contrast, keyboard navigation, focus states, `aria-*` on form errors). In-fight: color is never the only signal (shapes/icons on HUD bars and telegraphs). |
| NFR-A11Y-02 | Accessibility | A "reduce motion" setting turns off camera shake and flashes. |
| NFR-REL-01 | Reliability | If match submission fails, the client retries with backoff and keeps the pending result in IndexedDB until it succeeds (no lost wins). |
| NFR-OBS-01 | Observability | Frontend errors are reported to Sentry with release version; Edge Function errors are logged with a request ID. |
| NFR-MAINT-01 | Maintainability | Strict TypeScript, no `any`; CI blocks merges on lint, type-check, test or build failure. |
| NFR-I18N-01 | Localization | UI text is in English with Filipino game terms; text is kept in a single strings module so a Filipino/Cebuano translation can be added later. |
| NFR-LEGAL-01 | Legal/Content | No real-money mechanics; no loot boxes with paid currency; content rated for teens (stylized violence). The project stays non-commercial while hosted on Vercel Hobby. |

---

## 7. Assumptions, constraints, open questions

### Assumptions
- A1. Supabase Cloud is the backend for all environments; the frontend is hosted on **Vercel** (Hobby plan). This is a **personal, non-commercial hobby project**, so the ICT Blueprint is followed voluntarily as the house standard.
- A2. The prototype manok asset and rig (39 bones, 9 animations) from `tools/blender/build_manok.py` are the R1 placeholder art.
- A3. Three developers build R1: **Carlo** (project owner; game client), **Cliff** (simulation and bot, then app screens) and **Patrick** (platform: database, Edge Functions, CI, Vercel). **Ramil** reviews and approves every PR. Claude Code assists. QA is done by the team and a small beta group. Ownership is in [tasks.md](../03-development/tasks.md#team--ownership).

### Constraints
- C1. Follow the ICT Information System Blueprint 2026 for the frontend, conventions, Git workflow, testing and SDLC. Laravel is replaced by Supabase (mapping in [architecture.md](../02-design/architecture.md) §2).
- C2. Web only (React + TypeScript + Vite).
- C3. Bot fights run on the client; the server can only verify them by replay (FR-MATCH-02).

### Open questions (to resolve before Design sign-off)

| ID | Question | Proposed default |
|---|---|---|
| ~~OQ-01~~ | ~~Final game title?~~ | **Resolved 2026-11-14: "Sabong"** (repo `sabong`) |
| OQ-02 | Allow guest play (FR-AUTH-06) in R1? | Yes — lowers friction for first fight |
| ~~OQ-03~~ | ~~Production hosting for the frontend?~~ | **Resolved 2026-11-14: Vercel** (Hobby plan). Move to Pro before any monetization |
| OQ-04 | Daily coin cap value | 300 coins/day from bot wins |
| OQ-05 | PvP netcode approach (R3): WebRTC P2P rollback vs. authoritative relay | Decide in a PvP design spike before R3 |
| OQ-06 | Audio library | Babylon.js built-in audio first; revisit if limits appear |
