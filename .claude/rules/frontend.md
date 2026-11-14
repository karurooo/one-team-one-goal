---
paths:
  - "frontend/**"
---

# Frontend rules

Owners (tasks.md): Carlo owns `src/game/**`, `features/match/**`, `features/settings/**` and `public/models/**`. Cliff owns `features/{auth,profile,manok,leaderboard}/**`. Patrick owns `src/{lib,providers,config,components,app,types,stores}` and `vercel.json`. Flag any change outside the task owner's paths in the PR.

Source: [architecture §4](../../docs/02-design/architecture.md), [ui-ux-design §4–8](../../docs/02-design/ui-ux-design.md), [api-design §8–9](../../docs/02-design/api-design.md), [conventions §1.2, §2, §5](../../docs/03-development/conventions.md), [game-engine-design §4–8](../../docs/02-design/game-engine-design.md).

## Structure
- Use the Blueprint layout from architecture §4. Features live in `src/features/<domain>/` with `components/{atoms,molecules,organisms,templates}`, `api/`, `hooks/`, `stores/` and so on, and export public pieces from `index.ts`.
- shadcn primitives live only in `src/components/ui/`.
- `src/game/` is the Babylon engine, not a feature. React talks to it only through `src/game/bridge` and the `match` organisms (`FightView`, `Hud`).
- The sim and schemas are imported via the `@sim` and `@schemas` aliases. Never copy them, and never import from `prototype/`.

## Code
- TS strict with `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` and `noImplicitOverride`. **No `any`**: use `unknown` and narrow.
- Functional components only. Data fetching and logic go in custom hooks.
- Server state uses TanStack Query (keys per ui-ux §5). Client state uses Zustand (`authStore` is not persisted; `settingsStore` persists under `sabong.settings.v1`).
- Forms use React Hook Form with `zodResolver` and the shared `@schemas`, `mode: 'onBlur'`. Map 422s with `mapServerErrors`.
- Every data-driven component handles loading (skeleton), error (message and retry) and empty states.
- Never use `dangerouslySetInnerHTML` with user data.
- Accessibility: keyboard navigation, focus rings, labelled inputs, `aria-invalid`/`aria-describedby`, and contrast ≥ 4.5:1.
- Game and Babylon hot paths allocate nothing per frame: reuse `TmpVectors` and pooled particles. Respect "reduce motion".

## Security & state
- **The client never writes game state.** Coins, results and records change only via Edge Functions (`lib/axios.ts`).
- Only `VITE_`-prefixed public values, validated in `src/config/env.ts`. Never the service role key or other secrets.
- Run `npm run db:types` after migrations. Never hand-edit `src/types/database.types.ts`.
- New static folders must be added to the rewrite exclusions and cache headers in `frontend/vercel.json`.
