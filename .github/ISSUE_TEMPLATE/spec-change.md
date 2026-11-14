---
name: Spec change
about: Propose a change to the specs in docs/ (behavior must change in the spec first)
title: "docs: "
labels: spec-change
---

## Proposed change

## Why

## Affected spec sections
<!-- e.g. game-design §6.2, api-design §6.1, database-design §4.7 -->
-

## Affected requirement IDs
<!-- Keep IDs stable; add new IDs instead of renumbering -->
-

## Affected tasks
<!-- T-xxx from docs/03-development/tasks.md -->
-

## Impact
- [ ] Changes replay results (needs a `SIM_VERSION` bump and new golden fixtures)
- [ ] Needs a database migration
- [ ] Changes `_shared/schemas` (frontend and Edge Functions)
- [ ] Changes a handoff contract. Consumers who must review:
- [ ] None of the above

## Sign-off
Requirement changes: Carlo. Every PR: Ramil.
