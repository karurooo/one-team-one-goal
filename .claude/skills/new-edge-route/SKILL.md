---
name: new-edge-route
description: Add an Edge Function route following api-design §3–5 and §8 (Zod schema in _shared/schemas, thin controller, service, repository, envelope, Deno tests). Use when adding or changing an endpoint under supabase/functions/.
argument-hint: <METHOD /domain/path>
---

# New Edge Function route: $ARGUMENTS

Rules: `.claude/rules/edge-functions.md` and `docs/02-design/api-design.md`.

1. Find the endpoint in api-design §6: request, response, errors, rate limit, requirement IDs. If it is not there, run `/spec-change` first.
2. **Schema**: add `<action><Model>Schema` and the `<Action><Model>Request` type to `supabase/functions/_shared/schemas/<domain>.ts`.
   - Trim strings and mirror the DB constraints.
   - Relative imports use `.ts`, and `zod` is the bare specifier from `deno.json`.
   - Schemas are shared with the frontend and are a handoff contract: changes need review from the consumers.
3. **Route** in `supabase/functions/<domain>/index.ts`. Chain the middleware: `requestId`, `cors`, `requireAuth`, `requireActive`, (`requireRole`), `rateLimit`, then `validate('json', schema)`. No logic in this file.
4. **Controller** `controllers/<domain>Controller.ts` is thin: take the validated input and `userId` from the context, call the service, and return `ok`/`fail`/`paginated`.
5. **Service** `services/<domain>Service.ts` holds the business logic. A multi-step write is **one** `rpc()` to a transactional SQL function (use `/new-migration` if it does not exist). Map the result with `toXResource()`.
6. **Repository** `repositories/<domain>Repository.ts` is the only place that calls `supabase.from`, `rpc` or `storage`. Pass explicit fields.
7. **Errors**: use the envelope `{ data, message, errors }`. 422 errors use dot-path keys. Unknown errors return the generic 500 and are logged with `request_id`. No internal details.
8. **Tests** go in `<file>.test.ts` (Deno). Cover the happy path, 401, 403 (inactive or role), 404 (other user's resource), 422, 409 or 429 where relevant, and every error listed in the spec.
9. Run `deno lint`, `deno check` and `deno test` for `supabase/functions`, and `supabase functions serve` for a manual check.
10. Run `spec-conformance-reviewer` on the diff. Suggest a `feat: …` commit with the task and requirement IDs.
