---
paths:
  - "supabase/migrations/**"
  - "supabase/tests/**"
  - "supabase/seed.sql"
  - "supabase/seeds/**"
---

# Database & migration rules (owner: Patrick)

Source: [database-design](../../docs/02-design/database-design.md) §1, §6–8 and §11; [conventions §1.1, SQL standards](../../docs/03-development/conventions.md).

## Migrations
- Create migrations with `supabase migration new <snake_case_description>`, named `YYYYMMDDHHMMSS_<description>.sql`. One migration per change.
- **Never edit a migration that has reached `development`.** Add a new one instead.
- A migration that creates a table must, **in the same file**:
  - enable RLS;
  - add policies, or a comment explaining why there are none;
  - add the `set_updated_at` trigger;
  - add explicit `grant`/`revoke`. The default is no access.
- After every migration, run `supabase gen types typescript --local > frontend/src/types/database.types.ts` (`npm run db:types`) and commit the result.

## Security
- RLS is on for every `public` table.
- The client never writes game state. Coins, results, records, ownership and roles change only through one transactional SQL function per operation, called by an Edge Function with the service role. Revoke `EXECUTE` on those functions from `anon` and `authenticated`.
- Every `authenticated` policy also requires `(select public.is_active_user())`. Wrap helper calls in `(select …)`.
- Column-level grants limit client updates (`profiles`: `display_name`, `avatar_path`, `username`; `manoks`: `name`).
- `security definer` functions must `set search_path = ''` and use schema-qualified names.
- No dynamic SQL from input. If unavoidable, use `format()` with `%L`/`%I`.

## Naming and style
- Tables are snake_case plural. Foreign keys are `{singular}_id`. Booleans are `is_*`. Enums are snake_case singular. Functions are verb-first.
- Every table has `created_at` and `updated_at` (`timestamptz`). Master tables also have `deleted_at`.
- Policy names follow `"<table>: <role> can <action> <scope>"`.
- Constraints mirror the Zod schemas in `_shared/schemas` exactly.
- Format with sqlfluff (postgres dialect).

## Tests
- Every RLS rule and SQL function has a pgTAP test in `supabase/tests/*.test.sql`.
- Run them with `supabase test db`.
- Use `rls-reviewer` before opening a PR.
