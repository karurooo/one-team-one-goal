---
name: new-migration
description: Create a Supabase migration that follows database-design §11 (RLS, policies, grants, set_updated_at, naming) with a pgTAP test and regenerated types. Use when adding or changing tables, functions, policies or triggers.
argument-hint: <snake_case_description>
---

# New migration: $ARGUMENTS

Rules: `.claude/rules/database-migrations.md` and `docs/02-design/database-design.md`.

1. Read the database-design sections for the tables or functions involved. If the change is not in the spec, run `/spec-change` first.
2. Run `supabase migration new $ARGUMENTS`. Never edit a migration that has already reached `development`.
3. Write the SQL. For **every new table**, in this same file:
   - [ ] snake_case plural name, `{singular}_id` FKs, `is_*` booleans, `created_at`/`updated_at timestamptz` (`deleted_at` on master tables)
   - [ ] `alter table … enable row level security;`
   - [ ] policies named `"<table>: <role> can <action> <scope>"`, each `authenticated` policy also requiring `(select public.is_active_user())`, or a comment explaining why there are no policies
   - [ ] explicit `revoke`/`grant` (column-level grants for client-updatable columns)
   - [ ] `set_updated_at` trigger
   - [ ] constraints that match the Zod schema in `_shared/schemas` (update the schema in the same PR)
4. For **functions**:
   - `security definer` functions get `set search_path = ''` and schema-qualified names.
   - Game-state writes are one transactional function. Revoke `execute` from `anon` and `authenticated`.
   - No dynamic SQL from input.
5. Add or extend the pgTAP tests in `supabase/tests/<area>.test.sql`, covering every policy (own vs. other user, anon, inactive user) and every function path.
6. Run `supabase db reset`, then `supabase test db`.
7. Run `npm run db:types` (or `supabase gen types typescript --local > frontend/src/types/database.types.ts`) and include the result in the change.
8. Run the `rls-reviewer` agent on the migration and fix what it finds.
9. Suggest the commit `feat: …` (or `fix: …`) and list the task and requirement IDs.
