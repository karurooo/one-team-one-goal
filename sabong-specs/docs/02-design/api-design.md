# API Design (Supabase Edge Functions + PostgREST)

| Field | Value |
|---|---|
| SDLC phase | Design |
| Status | Draft v0.1 |
| Baseline | Blueprint "Backend API Guidelines", "Backend Validation Standards", "API Integration", "Security Implementation" |
| Related | [database-design.md](./database-design.md), [architecture.md](./architecture.md) |

---

## 1. Two kinds of API

| Kind | Used for | Called with | Envelope |
|---|---|---|---|
| **Commands** (Edge Functions) | Every write that changes game state; anything needing secrets, replay or a transaction | Axios (`src/lib/axios.ts`) | ✅ Blueprint envelope |
| **Queries** (PostgREST through supabase-js) | Reading own data and public catalogs, under RLS | `supabase.from(...)` in `features/<domain>/api/` | Normalized by the frontend API layer (see §7) |

Cosmetic writes that RLS fully protects (`profiles.display_name/username/avatar_path`, `manoks.name`) may use PostgREST directly, through column-level grants (see database-design §6).

---

## 2. Versioning and base paths

Supabase serves functions at `https://<project-ref>.supabase.co/functions/v1/<function-name>`. The `/functions/v1/` prefix is Supabase's own platform version. **Our API version is carried by the function name**: functions without a suffix are v1. A breaking change ships as a new function `<name>-v2`, and the old one is kept until clients are updated.

| Domain | Base path (Blueprint "API Versioning" equivalent) |
|---|---|
| Matches | `/functions/v1/matches` |
| Manoks | `/functions/v1/manoks` |
| Profiles | `/functions/v1/profiles` |
| Taris (R2) | `/functions/v1/taris` |
| Admin (R2) | `/functions/v1/admin` |

Each function is one Hono app with `basePath('/<function-name>')`.

---

## 3. Response envelope (mandatory)

All Edge Function responses use the Blueprint envelope through the helpers in `_shared/http/response.ts` (equivalent of the Laravel `ApiResponse` trait):

| Response type | Structure | HTTP codes |
|---|---|---|
| Success | `{ data: T, message: string, errors: null }` | 200, 201 |
| Error | `{ data: null, message: string, errors: Record<string, string[]> \| null }` | 400, 401, 403, 404, 409, 422, 429, 500 |
| Paginated | `{ data: T[], meta: { current_page, last_page, per_page, total }, message, errors: null }` | 200 |

```ts
// _shared/http/response.ts
export const ok = <T>(c: Context, data: T, message = 'OK', status: 200 | 201 = 200) =>
  c.json({ data, message, errors: null }, status);
export const fail = (c: Context, status: ErrorStatus, message: string, errors: FieldErrors | null = null) =>
  c.json({ data: null, message, errors }, status);
export const paginated = <T>(c: Context, rows: T[], meta: PageMeta, message = 'OK') =>
  c.json({ data: rows, meta, message, errors: null }, 200);
```

Rules:
- Never return raw DB rows. Each service returns a **resource mapper** output (`toMatchResource(row)`), the equivalent of a Laravel API Resource.
- Never expose SQL errors, stack traces or table names. Unknown errors → `500 "Something went wrong. Please try again."`, and the details go to the log with the `request_id`.
- Every response includes the header `x-request-id`.

---

## 4. Function internal structure (Laravel layering → Hono)

```
supabase/functions/matches/
├── index.ts              # Hono app: middleware + routes (no logic)
├── controllers/
│   └── matchController.ts   # thin: parse validated input → call service → return envelope
├── services/
│   └── matchService.ts      # business logic: seeds, replay, reward calls
├── repositories/
│   └── matchRepository.ts   # all Supabase queries/rpc for this domain
└── matchController.test.ts  # Deno tests
```

| Laravel concept | Here |
|---|---|
| Route (`routes/api.php`) | `index.ts` Hono routes |
| Middleware (auth, role) | `_shared/http/middleware.ts`: `requestId`, `cors`, `requireAuth`, `requireActive`, `requireRole('admin')`, `rateLimit` |
| Form Request | Zod schema in `_shared/schemas/<domain>.ts` + `validate('json', schema)` middleware (422 on failure) |
| Controller | `controllers/*.ts` (thin) |
| Service | `services/*.ts` |
| Repository | `repositories/*.ts` (only place with `supabase.from/rpc`) |
| Policy | RLS + ownership checks inside SQL functions |
| `DB::transaction()` | A single SQL function per multi-step write (database-design §7) |
| API Resource | `toXResource()` mappers in `_shared/resources/` |

---

## 5. Authentication, authorization, CORS, rate limits

- **Auth:** `requireAuth` reads `Authorization: Bearer <jwt>` and calls `supabase.auth.getUser(jwt)` (or verifies the JWT against the project's JWKS). It puts `userId` in the context. Missing/invalid → `401 "Unauthenticated."`.
- **Active check:** `requireActive` loads `profiles.is_active`; inactive → `403 "Your account is deactivated."`.
- **Roles:** `requireRole('admin')` → `403 "Access denied."`.
- **DB access:** functions use a **service-role client created per request** (`_shared/db/admin.ts`). The service key comes only from Edge Function secrets. User identity always comes from the verified JWT, **never from the request body**.
- **CORS:** `Access-Control-Allow-Origin` is restricted to `CORS_ALLOWED_ORIGINS` (dev: `http://localhost:5173`; prod: the deployed frontend URL). No wildcard.
- **Rate limits:**
  - Auth endpoints: Supabase Auth rate limits (configured in `config.toml` / dashboard) + CAPTCHA (Cloudflare Turnstile or hCaptcha), targeting the Blueprint's **5 attempts per 5 minutes**.
  - Edge Functions: per-user fixed window held in Postgres (`rate_limits` table, function `hit_rate_limit(key, limit, window)`): `POST /matches` 30/min, `POST /matches/{id}/submit` 30/min, others 60/min. Over the limit → `429` with `Retry-After`.

- **Input security (Blueprint "Input Security"):**
  - *SQL injection:* only the supabase-js query builder, PostgREST and parameterized `rpc()` calls. SQL functions never build dynamic SQL from input; if they ever must, they use `format()` with `%L`/`%I`.
  - *XSS:* functions return JSON only. The frontend renders user text through React escaping and never uses `dangerouslySetInnerHTML`.
  - *Mass assignment:* services pass explicit fields to SQL functions, never the raw body. On the client side, column-level grants (database-design §6) are the equivalent of `$fillable`/`$guarded`.

---

## 6. Endpoints (R1 unless marked)

### 6.1 Matches — `/functions/v1/matches`

#### `POST /matches` — start a match (FR-FIGHT-01)

Request (`StartMatchRequest`):
| Field | Rule |
|---|---|
| `mode` | `'bot'` (R1) |
| `manok_id` | uuid, must be the caller's active manok |
| `difficulty` | `'easy' \| 'normal' \| 'hard'` |

Response `201`:
```json
{
  "data": {
    "match_id": "uuid",
    "seed": 8812736512,
    "sim_version": "1.0.0",
    "config": {
      "meron": { "breed_code": "talisayin", "tari_code": "standard", "is_bot": false },
      "wala":  { "breed_code": "talisayin", "tari_code": "standard", "is_bot": true, "difficulty": "normal" },
      "round_ticks": 5400
    }
  },
  "message": "Match started.",
  "errors": null
}
```
Errors: 404 manok not found/not yours; 422 validation; 429 rate limit.

The seed is generated server-side with `crypto.getRandomValues` (53-bit safe integer).

#### `POST /matches/{match_id}/submit` — finish a match (FR-MATCH-01/02/03)

Request (`SubmitMatchRequest`):
| Field | Rule |
|---|---|
| `input_log` | string: base64 of the binary input log (sim spec §6), ≤ 64 KB decoded |
| `final_hash` | 64-char hex |
| `claimed_winner_side` | `'meron' \| 'wala' \| 'draw'` |
| `claimed_reason` | `'ko' \| 'talikod' \| 'timeout' \| 'forfeit'` |
| `duration_ticks` | integer 0–7200 |

Service steps:
1. Load the match (must be the caller's, `in_progress`, created < 30 minutes ago).
2. **Replay** with `_shared/sim` at `match.sim_version`, `match.seed`, the snapshot config and the input log. If `sim_version` is not the current one, use the version kept in `_shared/sim/versions/` (old versions stay available until no in-progress match uses them).
3. Compare the replayed `{winner, reason, duration, hash}` with the claim.
4. Upload the input log to `match-replays/{profile_id}/{match_id}.bin`.
5. Call `complete_match(...)` with `is_verified`.

Response `200`:
```json
{
  "data": {
    "match": { "id": "uuid", "winner_side": "meron", "result_reason": "ko", "duration_ticks": 2710, "is_verified": true },
    "rewards": { "coins": 75, "breakdown": [{"reason":"match_reward","amount":25},{"reason":"daily_bonus","amount":50}], "daily_cap_reached": false },
    "profile": { "coins": 1240, "wins": 12, "losses": 7, "draws": 1 }
  },
  "message": "Match saved.",
  "errors": null
}
```
Errors: 404; 409 `"Match already submitted."` (the same rewards are returned in `data` so retries stay idempotent); 422 `"Match could not be verified."` (AC-MATCH-02); 422 validation.

Replay budget: a full 90-second match is ≤ 7,200 ticks. The target is < 50 ms CPU in the Edge runtime; this is checked by a benchmark test (test-plan §4).

#### `POST /matches/{match_id}/forfeit`
Marks the match `completed`, winner = opponent, reason `forfeit`, verified by rule (no replay needed for a loss). `200`.

#### `GET /matches/health`
Public, no auth. It returns `200 { data: { status: "ok", sim_version }, … }` for uptime checks (deployment §7).

#### `GET /matches/{match_id}/replay` (R2)
Returns `{ signed_url, expires_in: 300 }` for the caller's own replay.

### 6.2 Manoks — `/functions/v1/manoks`

| Method & path | Purpose | Request | Response |
|---|---|---|---|
| `POST /manoks/starter` | Grant starter if missing (idempotent, called on first lobby load) | — | `200` manok resource (existing or new) |
| `POST /manoks/purchase` (R2) | Buy a breed | `{ breed_code, name }` | `201` manok + new coin balance; `422 "Not enough coins."` |
| `PATCH /manoks/{id}/tari` (R2) | Equip an owned tari | `{ tari_code }` | `200` |
| `DELETE /manoks/{id}` (R2) | Retire (soft delete) | — | `200`; `422 "You need at least one manok."` |

Rename (`name`) goes through PostgREST directly (column grant), validated client-side by the same Zod schema and server-side by the `check` constraint.

### 6.3 Profiles — `/functions/v1/profiles`

| Method & path | Purpose |
|---|---|
| `POST /profiles/convert-guest` | After a guest links email/password (`supabase.auth.updateUser`), clears `is_guest` and lets the user set a username. `409` if the username is taken |

Username/display name/avatar edits use PostgREST + Storage directly (RLS column grants).

### 6.4 Admin — `/functions/v1/admin` (R2, role `admin`)

| Method & path | Purpose |
|---|---|
| `GET /admin/profiles?search=&page=&per_page=` | Paginated list (envelope `meta`) |
| `PATCH /admin/profiles/{id}` | `{ is_active }` → `admin_set_profile_active` + audit |
| `POST /admin/breeds`, `PATCH /admin/breeds/{code}` | Catalog edits (name, description, price, `is_active`). Gameplay numbers are **not** editable here |
| `POST /admin/taris`, `PATCH /admin/taris/{code}` | Same for taris |

---

## 7. Queries through PostgREST (frontend `features/<domain>/api/`)

| Feature | Query | Hook |
|---|---|---|
| profile | `profiles` select own | `useMyProfile()` |
| profile | `public_profiles` by username | `usePublicProfile(username)` |
| manok | `manoks` own, joined with `breeds(code,name,archetype,model_path, skill:skills!skill_id(*), passive:skills!passive_id(*))` | `useMyManoks()` |
| manok | `breeds` active catalog | `useBreeds()` |
| match | `my_match_history` paginated with `range()` and `count: 'exact'` | `useMatchHistory(page, perPage)` |
| match | `matches` by id (own) | `useMatch(id)` |
| leaderboard | `leaderboard_bot` (R2) | `useLeaderboard()` |

Each query function returns typed data from `database.types.ts`. On error it throws an `ApiError { status, message, errors }`, so components handle Edge Function errors and PostgREST errors the same way. Paginated queries return `{ data, meta }` in the envelope's `meta` shape, so `DataTable` gets one input format.

---

## 8. Validation standards (Blueprint "Backend Validation Standards", adapted)

1. Every POST/PUT/PATCH Edge Function route **MUST** have a Zod schema in `_shared/schemas/<domain>.ts`, applied by `validate()` before the controller runs. Controllers and services never validate input themselves.
2. Schemas **MUST** mirror DB constraints (`varchar(24)` → `.max(24)`, `check` regexes → `.regex()`).
3. Strings are trimmed (`z.string().trim()`).
4. Validation failure → **422** `{ data: null, message: "Validation failed", errors: { field: ["message"] } }`. Nested keys use dot notation (`config.meron.breed_code`).
5. The frontend imports the **same schemas** (path alias `@schemas`) for React Hook Form, so client and server rules cannot drift.

| Data type | Zod rule (shared) | DB constraint |
|---|---|---|
| Username | `z.string().trim().toLowerCase().regex(/^[a-z0-9_]{3,20}$/, 'Use 3–20 letters, numbers or _')` | `citext` + check |
| Display name | `z.string().trim().min(1, 'Display name is required').max(40)` | `varchar(40)` + check |
| Manok name | `z.string().trim().min(1, 'Name is required').max(24)` | `varchar(24)` + check |
| Email | `z.string().trim().email('Enter a valid email')` | Supabase Auth |
| Password | `z.string().min(8, 'Minimum 8 characters').max(72)` | Supabase Auth (min length set to 8) |
| UUID | `z.string().uuid()` | `uuid` |
| Enum | `z.enum([...])` built from `database.types.ts` enums | enum type |
| Hash | `z.string().regex(/^[0-9a-f]{64}$/)` | `varchar(64)` |
| Avatar file | custom refine: `size ≤ 2 MB`, type in `jpeg/png/webp` | bucket limits |

---

## 9. Frontend HTTP client (Blueprint "API Integration")

`src/lib/axios.ts`, the only Axios instance:
- `baseURL = ${VITE_SUPABASE_URL}/functions/v1`.
- Request interceptor: adds `Authorization: Bearer <access_token>` from `supabase.auth.getSession()` and `apikey: <anon key>`.
- `withCredentials: false` (token-based auth).
- Response interceptor (global handling):
  - **401** → `supabase.auth.signOut()`, clear stores, redirect to `/login`.
  - **403** → toast "Access denied".
  - **422** → reject with `ApiError` so forms map `errors` to fields with `setError` (dot keys → RHF paths; unknown keys → `setError('root', …)`).
  - **429** → toast "Too many requests. Try again in N seconds."
  - **500/network** → toast "Server error. Please try again." (match submissions are queued instead; see NFR-REL-01).

---

## 10. OpenAPI

`supabase/openapi.yaml` documents every Edge Function route with request/response schemas (generated from the Zod schemas with `zod-to-openapi` in a script, `npm run docs:openapi`). It replaces Laravel Scramble. It is not served publicly in production (Blueprint: "Scramble docs disabled or auth-gated in production").
