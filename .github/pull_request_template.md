## Tasks
<!-- One line per task, e.g. "Implements T-SIM-04 (FR-FIGHT-02, NFR-DET-01)" -->
Implements T-

## Requirement IDs
<!-- FR-/NFR-/AC- IDs covered by this PR -->
-

## Summary
-

## Done when
<!-- Copy the task's "Done when" items from docs/03-development/tasks.md and say how each is proven -->
- [ ]

## Other tracks touched
<!-- Paths outside the task owner's area (tasks.md "Team & ownership"), or "None" -->
None

## Checklist
- [ ] `npm run check` passes locally (lint, typecheck, vitest, deno test, `supabase test db`)
- [ ] Tests cover the acceptance criteria / "Done when" items
- [ ] Task checkbox ticked in `docs/03-development/tasks.md`
- [ ] Spec updated in this PR if behavior changed (or N/A)
- [ ] Handoff contract changed? Consumers requested as reviewers (or N/A)
- [ ] Migrations: RLS, policies, grants, `set_updated_at` in the same file; `database.types.ts` regenerated (or N/A)
- [ ] Sim: replay-affecting change bumps `SIM_VERSION` and updates golden fixtures (or N/A)
- [ ] No secrets, service role key or `.env` values in code, tests or commits
- [ ] Commits use the Blueprint format (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `style:`, `test:`)
