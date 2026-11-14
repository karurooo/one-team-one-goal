# UI/UX Design (Screens, Routes, Components, State)

| Field | Value |
|---|---|
| SDLC phase | Design |
| Status | Draft v0.1. Figma wireframes are to be produced and linked here before Design sign-off (Blueprint output: "UI/UX Designs (Figma)") |
| Baseline | Blueprint "Frontend Guidelines", "Component Architecture (Atomic Design)", "Routing & Access Control", "Form Standards", "Frontend Validation Standards" |
| Related | [game-engine-design.md](./game-engine-design.md) §8, [api-design.md](./api-design.md) §7, §9 |

---

## 1. Visual direction

- **Style:** "Fiesta Arcade": bold flat shapes, thick outlines, warm palette. Accents come from banderitas, jeepney-art lettering and banig weave patterns (used as backgrounds and dividers, never behind body text).
- **Tokens (Tailwind / shadcn CSS variables):**

| Token | Light | Dark | Use |
|---|---|---|---|
| `--primary` | `#C2410C` (fiesta orange) | `#F97316` | Main actions |
| `--meron` | `#B91C1C` | `#EF4444` | Meron corner, P1 |
| `--wala` | `#1D4ED8` | `#60A5FA` | Wala corner, bot/P2 |
| `--gold` | `#B45309` | `#FBBF24` | Coins, rewards |
| `--background` | `#FFF8EE` | `#1B1410` | App background |
| `--card` | `#FFFFFF` | `#2A1F18` | Panels |

- **Fonts:** a display face with jeepney-sign character for titles/banners (e.g. "Bungee", Google Fonts), and Inter/system UI for body text.
- **Theme:** next-themes, light/dark for menus. The fight screen always uses its own fixed palette.
- Every meter uses an **icon + color + number**, so color is never the only signal (NFR-A11Y-01). HP = heart, Hingal = lungs/wind, Tapang = flame/feather.

---

## 2. Routes and access (Blueprint "Routing & Access Control")

All routes except the public ones are wrapped in `ProtectedRoute` (`isAuthenticated`). Role-restricted routes pass `roles`.

| Route | Page component | Access | Requirement |
|---|---|---|---|
| `/login` | `LoginPage` | Public | FR-AUTH-02 |
| `/register` | `RegisterPage` | Public | FR-AUTH-01 |
| `/forgot-password` | `ForgotPasswordPage` | Public | FR-AUTH-03 |
| `/reset-password` | `ResetPasswordPage` | Public (recovery link) | FR-AUTH-03 |
| `/play-as-guest` | `GuestStartPage` | Public | FR-AUTH-06 (C) |
| `/` | `LobbyPage` | All authenticated (incl. guest) | FR-FIGHT-01, FR-MANOK-04 |
| `/roster` | `RosterPage` | Authenticated | FR-MANOK-01..03 |
| `/roster/:manokId` | `ManokDetailPage` | Authenticated (own; RLS) | FR-MANOK-02/03/06 |
| `/fight/bot` | `BotFightPage` | Authenticated | FR-FIGHT-01..06 |
| `/fight/:matchId/result` | `MatchResultPage` | Authenticated (own) | FR-FIGHT-04, FR-MATCH-01..03 |
| `/matches` | `MatchHistoryPage` | Authenticated | FR-MATCH-04 |
| `/matches/:matchId` | `MatchDetailPage` | Authenticated (own) | FR-MATCH-04/05 |
| `/leaderboard` | `LeaderboardPage` | Authenticated | FR-LEAD-01 (R2) |
| `/profile` | `MyProfilePage` | Authenticated | FR-PROF-01..04 |
| `/u/:username` | `PublicProfilePage` | Authenticated | FR-PROF-01 |
| `/settings` | `SettingsPage` | Authenticated | FR-SET-01..04, FR-AUTH-04 |
| `/admin/profiles` | `AdminProfilesPage` | `admin` | FR-ADMIN-02 (R2) |
| `/admin/catalog` | `AdminCatalogPage` | `admin` | FR-ADMIN-01 (R2) |
| `*` | `NotFoundPage` | Public | — |

Page components live in `src/app/routes/<domain>/`. They compose templates/organisms and own data fetching. They **must not** contain atom- or molecule-level markup inline (Blueprint rule).

---

## 3. Screens

### 3.1 Lobby (`/`)
- **3D preview** of the selected manok idling on a small pedestal (a light Babylon scene that reuses `src/game/render/ManokView`, Low quality).
- Manok selector (carousel of owned manoks), breed name, skill/passive chips.
- **"Laban!" (Fight)** primary button → difficulty dialog (Easy/Normal/Hard, with a short description of each) → `/fight/bot`.
- Coins, daily reward progress (e.g. "120 / 300 coins today"), record W-L-D.
- Nav: Roster, Matches, Leaderboard (R2), Profile, Settings.

### 3.2 Fight (`/fight/bot`)
- Full-screen canvas. The AppShell is hidden.
- **HUD (React overlay):**
  - Top: Meron banner (left), timer (center), Wala banner (right).
  - Under each banner: HP bar (large), Hingal bar (thin), Tapang bar (thin, with a flame icon). The skill cooldown ring sits near the player's bars.
  - Center prompts: "ULUTAN", "LABAN!", "CLASH! – press K", "SENTENSYA! 5…", "KO!".
- **Pause menu** (Esc): Resume, Controls, Settings (audio/quality), Forfeit (confirm dialog).
- **Loading state:** model/scene loading progress; "Requesting match…" while `POST /matches` runs.
- **Error state:** WebGL unsupported → explanation + link to supported browsers; network error on start → retry button.

### 3.3 Match result (`/fight/:matchId/result`)
- Big result banner (PANALO / TALO / TABLA = Win / Loss / Draw) and reason (KO, Talikod, Timeout, Forfeit).
- Stats: damage dealt, hits landed by type, clashes won, time.
- Rewards panel: coin breakdown, "daily cap reached" note, new balance. A "Saving…" state appears while the submission is pending. If verification fails: "This match could not be verified. No rewards were given."
- Buttons: Rematch (same settings), Change manok, Lobby.

### 3.4 Roster, manok detail, matches, profile, settings
Standard shadcn layouts: cards for manoks; a **TanStack Table** for match history (columns: date, manok, opponent, result, reason, duration, coins; server-side pagination); forms for profile and settings.

---

## 4. Component architecture (Atomic Design, mandatory)

Global primitives: `src/components/ui/` (shadcn: button, input, label, card, table, badge, dialog, form, select, tabs, slider, switch, tooltip, progress, sonner).

| Feature | Atoms | Molecules | Organisms | Templates |
|---|---|---|---|---|
| `auth` | `AuthLogo`, `PasswordStrengthHint` | `LoginForm`, `RegisterForm`, `ForgotPasswordForm`, `ResetPasswordForm`, `MfaChallengeForm`, `CaptchaField` | `AuthCard` | `AuthLayout` |
| `profile` | `CoinBadge`, `RecordBadge`, `AvatarImage` | `ProfileForm`, `AvatarUploader`, `MfaSetupPanel` | `ProfileOverview`, `PublicProfileView` | — |
| `manok` | `BreedChip`, `SkillChip`, `ArchetypeIcon` | `ManokCard`, `RenameManokForm`, `TariSelect` (R2) | `ManokCarousel`, `ManokPreview3D`, `RosterGrid`, `ManokDetailView` | — |
| `match` | `MeterBar`, `TimerDisplay`, `CornerBanner`, `ResultBanner`, `CooldownRing` | `PlayerHudPanel`, `DifficultyPicker`, `RewardBreakdown`, `PauseMenu`, `FightPrompt` | `FightView` (Babylon mount), `Hud`, `MatchResultView`, `MatchHistoryTable`, `MatchDetailView` | `FightLayout` |
| `leaderboard` (R2) | `RankCell` | `LeaderboardRow` | `LeaderboardTable` | — |
| `settings` | `KeyCap` | `AudioSettingsForm`, `GraphicsSettingsForm`, `KeyBindingRow` | `SettingsPanel` | — |
| `admin` (R2) | — | `BreedForm`, `TariForm` | `AdminProfilesTable`, `CatalogEditor` | `AdminLayout` |

Each feature exports its public pieces from `src/features/<domain>/index.ts`.

---

## 5. State management (Blueprint "State Management", adapted)

| State | Tool | Store / hook | Purpose | Persistence |
|---|---|---|---|---|
| Session & user | supabase-js + Zustand | `authStore` | `session`, `user`, `profile`, `isAuthenticated`, `role`, `isGuest` (mirror only) | supabase-js persists the session itself; `authStore` is **not** persisted (no duplicate token storage) |
| Server data | TanStack Query | `useMyProfile`, `useMyManoks`, `useBreeds`, `useMatchHistory`… | Cached reads, invalidated after mutations | None (refetched) |
| Mutations | TanStack Query `useMutation` | `useStartMatch`, `useSubmitMatch`, `useRenameManok`… | Commands; on success invalidate `['profile']`, `['manoks']`, `['matches']` | — |
| UI | Zustand | `uiStore` | Dialogs, pause menu open, loading overlays | None |
| Settings | Zustand + `persist` | `settingsStore` | Volumes, quality, key bindings, reduce motion, theme | localStorage (versioned key `sabong.settings.v1`, try/catch) |
| Live fight HUD | Zustand vanilla store | `hudStore` (in `src/game/bridge`) | 20 Hz HUD snapshot | None |
| Lobby selection | Zustand | `features/match/stores/fightSetupStore` | Selected manok + difficulty | sessionStorage |
| Pending submissions | IndexedDB | `features/match/lib/submissionQueue` | NFR-REL-01 | IndexedDB |

Query keys: `['profile', 'me']`, `['profile', username]`, `['manoks', 'me']`, `['breeds']`, `['matches', { page, perPage }]`, `['match', id]`, `['leaderboard']`.

---

## 6. Forms (Blueprint "Form Standards" / "Frontend Validation Standards")

- React Hook Form + Zod via `@hookform/resolvers/zod`. Schemas come from `@schemas` (shared with Edge Functions).
- `useForm({ mode: 'onBlur', reValidateMode: 'onChange' })`.
- Errors show inline under the field in red, with `aria-invalid` and `aria-describedby`.
- 422 responses → `mapServerErrors(errors, setError)` (dot keys → RHF paths; unknown keys → `root`).
- Submit buttons are disabled while `isSubmitting` and show "Saving…".
- On success: Sonner toast, then navigate or close.
- No multi-step forms in R1 (guest conversion is a single step).

| Form | Fields | Schema |
|---|---|---|
| Register | email, password, confirm password, display name, CAPTCHA | `registerSchema` |
| Login | email, password, CAPTCHA | `loginSchema` |
| Forgot / Reset password | email / new password + confirm | `forgotPasswordSchema`, `resetPasswordSchema` |
| Profile | username, display name | `updateProfileSchema` |
| Avatar | file (≤ 2 MB, jpg/png/webp) with preview | `avatarFileSchema` |
| Rename manok | name | `renameManokSchema` |
| Difficulty picker | difficulty | `startMatchSchema` (partial) |
| Settings | volumes, quality, reduce motion, bindings | `settingsSchema` (client-only) |

---

## 7. Feedback, loading, empty, error states

Every data-driven component handles **loading** (skeleton), **error** (message + retry), and **empty** (friendly message + action, e.g. "No matches yet. Start your first fight!"). Toasts (Sonner) are used for non-field results: 403, 429, 500, "Settings saved", "Rewards received".

---

## 8. Accessibility & responsiveness

- Menus: full keyboard navigation, visible focus rings, contrast ≥ 4.5:1, labelled inputs, screen-reader text for meters ("Hingal 45 of 100").
- Fight: "Reduce motion" turns off shake, flashes and slow-motion. Prompts are shown as text **and** played as sound.
- Layout: menus are responsive from 360 px wide. The fight needs landscape on phones; in portrait the player sees a "Rotate your device" overlay.
- PWA install prompt (`components/pwa`) appears after the first completed match, not on first visit.
