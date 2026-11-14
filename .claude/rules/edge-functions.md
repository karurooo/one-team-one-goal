---
paths:
  - "supabase/functions/**"
---

# Edge Function rules (owner: Patrick; `_shared/sim` belongs to Cliff, see sim.md)

Source: [api-design](../../docs/02-design/api-design.md) §3–5 and §8; [conventions §1.3, Edge Function standards](../../docs/03-development/conventions.md); [architecture §3.1](../../docs/02-design/architecture.md).

## Layering (per function folder)
- `index.ts`: Hono app, middleware and routes. No logic.
- `controllers/*Controller.ts`: thin. Take validated input, call the service, return the envelope.
- `services/*Service.ts`: all business logic. A multi-step write calls **one** transactional SQL function via `rpc()`.
- `repositories/*Repository.ts`: the only place that calls `supabase.from()`, `.rpc()` or `.storage`.
- Map rows with `toXResource()` mappers (`_shared/resources/`). Never return raw rows.
- Tests are `<file>.test.ts` next to the file (Deno).

## Every route
- POST, PUT and PATCH need a Zod schema in `_shared/schemas/<domain>.ts`, applied by `validate()`. A failed validation returns **422** `{ data: null, message: "Validation failed", errors: { "dot.path": ["msg"] } }`.
- Schemas trim strings and mirror the DB constraints exactly. The frontend imports the same schemas, so they must run in Vite and Deno: relative imports with `.ts`, and bare specifiers only for packages in `deno.json`.
- Responses use the envelope `{ data, message, errors }` (or `paginated` with `meta`) through `_shared/http/response.ts`, and always carry `x-request-id`.
- Errors never expose SQL errors, stack traces or table names. Unknown errors return `500 "Something went wrong. Please try again."` and are logged with the `request_id`.

## Auth & security
- User identity comes **only** from the verified JWT (`requireAuth`), never from the body. Chain `requireActive`, and add `requireRole` where needed.
- Use a service-role client per request (`_shared/db/admin.ts`). The key comes only from Edge Function secrets.
- Call `Deno.env.get()` only in `_shared/config.ts`, validated with Zod.
- CORS allows exact origins only (`CORS_ALLOWED_ORIGINS`), never `*`.
- Rate limits: `POST /matches` and submit allow 30/min, everything else 60/min. Over the limit returns 429 with `Retry-After`.
- Pass explicit fields to SQL functions (no mass assignment).
- Never log secrets, tokens or full input logs.
