---
name: spec-change
description: Change a spec in docs/ before (or together with) a behavior change. Finds affected requirement IDs, design sections, tasks and handoff-contract consumers, edits the spec, and drafts the PR or issue. Use when implementation needs behavior the spec does not describe or contradicts.
argument-hint: <short description of the change>
---

# Spec change: $ARGUMENTS

The specs are the source of truth, and code and specs must not disagree on `main` (conventions §4).

1. **Locate.** Grep `docs/` for every requirement ID, section, table, endpoint and constant affected. List them.
2. **Impact.** Identify:
   - affected tasks in `docs/03-development/tasks.md`;
   - handoff contracts touched (tasks.md "Handoff contracts") and their **consumers**, who must review;
   - whether it changes replay results (needs a `SIM_VERSION` bump and new fixtures), the DB schema (needs a migration) or the API schemas (frontend and Edge Functions both change).
3. **Confirm.** Show the impact list and the proposed wording to the user before editing. Carlo signs off on requirement changes.
4. **Edit.**
   - Keep IDs stable. Add new IDs rather than renumbering.
   - Update every place in `docs/` that states the old behavior, plus the `.claude/rules/*.md` summary if a hard rule changed.
5. **Deliver.** Choose one:
   - same PR as the code (preferred when small);
   - a separate `docs: …` commit or PR first;
   - an issue from `.github/ISSUE_TEMPLATE/spec-change.md` if it needs discussion first. Fill in the template fields from steps 1–2.
6. List the reviewers needed: Ramil, plus the owners of the touched contracts or paths.
