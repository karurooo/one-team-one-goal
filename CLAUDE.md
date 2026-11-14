# CLAUDE.md — Instructions for AI coding agents

This is a **spec-driven** project. Read the relevant spec in `/docs` before writing code, and keep code and specs in agreement.

## Before starting any task
1. Find the task in `docs/03-development/tasks.md` and the requirement IDs it references.
2. Read the design sections for that area (`docs/02-design/*`) and the acceptance criteria (`docs/01-requirements/*`).
3. If the spec is unclear or conflicts with what you find in the code, **stop and ask**. Do not guess, and do not silently change behavior.

## Hard rules
- **Simulation (`supabase/functions/_shared/sim/**`)**: integer/fixed-point math only. No `Math.random`, `Math.sin/cos/atan2/pow/exp`, `Date`, `performance`, DOM, Deno or Node APIs, and no third-party imports. Any change that can change a replay result must bump `SIM_VERSION` and update the golden fixtures in the same PR.
- **Shared code** (`_shared/sim`, `_shared/schemas`) must run in both Vite and Deno: use relative imports with `.ts` extensions, and bare specifiers only for packages in the Deno import map.
- **The client never writes game state.** Coins, results, records, ownership and roles change only in Edge Functions, through one transactional SQL function per operation.
- **Every new table**: in the same migration, enable RLS, add policies and grants, add the `set_updated_at` trigger, and follow the naming conventions. Regenerate `frontend/src/types/database.types.ts` after migrations.
- **Every Edge Function route**: Zod schema from `_shared/schemas`, thin controller, service, repository, Blueprint envelope `{ data, message, errors }`, and no internal details in errors.
- **Frontend**: Blueprint folder layout; atomic tiers (`atoms/molecules/organisms/templates`) inside `features/<domain>/components/`; no `any`; RHF + shared Zod schemas; TanStack Query for server state; Zustand for client state; handle loading/error/empty states.
- **Never** put the service role key or other secrets in frontend code, tests, commits or Vercel environment variables. Only `VITE_`-prefixed public values reach the browser.
- **Hosting is Vercel**: new top-level routes need nothing extra (the SPA rewrite covers them), but new static folders must be added to the rewrite exclusions and cache headers in `frontend/vercel.json`.
- **No real-money mechanics** of any kind.

## Commands
| Purpose | Command |
|---|---|
| Start backend | `supabase start` · `supabase db reset` · `supabase functions serve` |
| Start frontend | `npm run dev -w frontend` |
| All checks (run before finishing a task) | `npm run check` (lint + typecheck + vitest + deno test + `supabase test db`) |
| Regenerate DB types | `npm run db:types` |
| Rebuild manok asset | `npm run assets:build` |

## Finishing a task
- All checks pass locally.
- Tick the task checkbox in `docs/03-development/tasks.md`.
- Commit with the Blueprint format (`feat:`, `fix:`, `docs:` …). In the PR description, list the task and requirement IDs.
- Never merge your own PR: Ramil reviews and merges. Stay inside the paths your task's owner owns (tasks.md "Team & ownership"); if you must touch another track's paths, say so in the PR so CODEOWNERS review applies.
- If you changed behavior, update the spec in the same PR.
