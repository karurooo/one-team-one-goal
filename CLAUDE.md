# CLAUDE.md — Instructions for AI coding agents

This is a **spec-driven** project. The specs in `/docs` are the source of truth. Read the relevant spec before writing code, and keep code and specs in agreement.

## Project overview

Sabong: a competitive, skill-based 3D web sabong (cockfighting) game. React + TypeScript + Vite frontend with Babylon.js for 3D; Supabase (Postgres + RLS, Auth, Edge Functions, Storage) backend. Full detail: [product-requirements.md](docs/01-requirements/product-requirements.md), [architecture.md](docs/02-design/architecture.md).

## Repository structure

- `frontend/` — Vite + React app (owners per path: see `.claude/rules/frontend.md`).
- `supabase/` — `migrations/`, `tests/` (pgTAP), `seeds/`, `functions/` (Edge Functions + `_shared/{sim,schemas,http,db}`).
- `docs/` — specs (`01-requirements` → `05-deployment`), including `03-development/tasks.md` (task list and ownership) and `conventions.md` (naming, Git workflow, standards).
- `prototype/` — reference-only PoC, never import from it.
- `.github/CODEOWNERS` and `pull_request_template.md` — review routing and PR checklist.
- `.claude/agents/` — read-only reviewers (`rls-reviewer`, `sim-determinism-reviewer`, `spec-conformance-reviewer`); run the relevant one before opening a PR.

## Before starting any task
1. Find the task in `docs/03-development/tasks.md` and the requirement IDs it references (or use `/implement-task <TASK-ID>`).
2. Read the design sections for that area (`docs/02-design/*`) and the acceptance criteria (`docs/01-requirements/*`).
3. If the spec is unclear or conflicts with the code, **stop and ask**. Do not guess, and do not silently change behavior.

## Path-specific rules (loaded automatically for matching files)
| Paths | Rules |
|---|---|
| `supabase/functions/_shared/sim/**` | [.claude/rules/sim.md](.claude/rules/sim.md) |
| `supabase/migrations/**`, `supabase/tests/**` | [.claude/rules/database-migrations.md](.claude/rules/database-migrations.md) |
| `supabase/functions/**` | [.claude/rules/edge-functions.md](.claude/rules/edge-functions.md) |
| `frontend/**` | [.claude/rules/frontend.md](.claude/rules/frontend.md) |

## Rules that apply everywhere
- **The client never writes game state.** Coins, results, records, ownership and roles change only in Edge Functions, through one transactional SQL function per operation.
- **Never** put the service role key or other secrets in frontend code, tests, commits or Vercel env vars. Do not read `.env*` files.
- **No real-money mechanics** of any kind.
- `prototype/` is reference only (float math). Never copy it into production code.
- Never push to production or remote Supabase (`supabase db push`, `link` and `functions deploy` and `vercel --prod` are denied). Use the local stack only.

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
- Commit in the Blueprint format (`feat:`, `fix:`, `style:`, `refactor:`, `chore:`, `docs:`, `test:`). In the PR description, list the task and requirement IDs (e.g. `Implements T-SIM-04 (FR-FIGHT-02, NFR-DET-01)`).
- Never merge your own PR: Ramil reviews and merges. Stay inside the task owner's paths (tasks.md "Team & ownership"). If you touch another track's paths, say so in the PR.
- If behavior changed, update the spec in the same PR (`/spec-change`).
