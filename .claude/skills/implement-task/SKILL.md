---
name: implement-task
description: Implement one task from docs/03-development/tasks.md end to end (read spec, confirm owner, plan, code + tests, checks, tick checkbox, draft PR). Use when the user says "implement T-XXX-NN" or runs /implement-task <TASK-ID>.
argument-hint: <TASK-ID>
---

# Implement task $ARGUMENTS

Follow these steps in order. Do not skip a step. Stop and ask whenever the spec is unclear or conflicts with the code.

## 1. Read the task
- Find the line starting with `- [ ] **$ARGUMENTS ` in `docs/03-development/tasks.md`. If it is missing or already ticked (`- [x]`), stop and tell the user.
- Record: title, **Owner**, Support, **Req** IDs, **Dep** tasks and the "Done when" criteria.
- Check every Dep task is ticked. If one is not, warn the user and ask whether to continue.

## 2. Read the linked spec
- For each Req ID (FR-…, NFR-…, AC-…), find it in `docs/01-requirements/*.md` and read its acceptance criteria.
- Read the design sections the task names (e.g. "architecture §3", "api-design §6", "engine §5.3"), plus the design doc for the area being touched.
- Note any handoff contract the task touches (tasks.md "Handoff contracts").

## 3. Confirm the owner
- Show the owner and the paths they own (tasks.md "Team & ownership").
- Ask the user: "This task is owned by <Owner>. Are you <Owner>, or is this agreed with them?" Do not proceed without a yes.
- List any files outside the owner's paths that the task will need to touch. These must be called out in the PR.

## 4. Plan
- Present a short plan: files to create or change, tests to write (mapped to the AC and "Done when" items), and any spec changes needed.
- If the implementation needs behavior that differs from the spec, stop and propose a `/spec-change` first.
- Wait for the user's approval.

## 5. Implement with tests
- Follow the path rules in `.claude/rules/`.
- Write the tests alongside the code. Each "Done when" item and AC needs a test that proves it, or a note on how it is verified manually.

## 6. Run the checks
- Run `npm run check`. If it does not exist yet (early M0), run whatever applies: `npm run lint`, `npm run build`, `npx vitest run`, `deno test`, `supabase test db`.
- Fix the failures. Report the final results truthfully, including anything that could not be run.
- For sim changes, run the `sim-determinism-reviewer` agent. For migrations, run `rls-reviewer`. Always run `spec-conformance-reviewer` on the diff.

## 7. Tick the checkbox
- In `docs/03-development/tasks.md`, change `- [ ] **$ARGUMENTS ` to `- [x] **$ARGUMENTS `.

## 8. Commit and draft the PR
- Suggest commits in the Blueprint format (`feat: …`, `fix: …`, `test: …`, `docs: …`, `chore: …`, `refactor: …`, `style: …`). Only commit if the user asks. Never push.
- Draft the PR description from `.github/pull_request_template.md`:

```
## Tasks
Implements $ARGUMENTS (<Req IDs, comma-separated>)

## Summary
<what changed and why, 2–5 bullets>

## Done when
- [x] <each "Done when" item and how it is proven>

## Other tracks touched
<paths outside the owner's area, or "None">

## Checklist
<the template checklist, ticked honestly>
```
