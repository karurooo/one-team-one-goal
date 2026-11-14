---
paths:
  - "supabase/functions/_shared/sim/**"
---

# Simulation rules (owner: Cliff)

Source: [game-engine-design §2](../../docs/02-design/game-engine-design.md), [conventions §1.4](../../docs/03-development/conventions.md), [architecture §3.1](../../docs/02-design/architecture.md). The sim runs in Vite **and** Deno, and the server replays every match, so any non-determinism is a bug.

## Determinism (NFR-DET-01)
- Integer / fixed-point math only. Positions are integer mm (arena radius 2000), velocities are mm/tick, and angles are binary angle units 0–4095.
- Trig comes only from the committed `math/trig.ts` lookup tables (scaled 2¹⁴). Square roots use integer `isqrt`.
- Truncate every mul/div with `Math.trunc` and keep values within ±2³¹.
- **Forbidden:** `Math.random`, `Math.sin/cos/tan/atan2/pow/exp/sqrt`, `Date`, `performance`, any DOM, `Deno.*` or Node API, third-party imports, float accumulation, and logic that depends on `Map`/`Set`/object-key iteration order.
- RNG is `sfc32` seeded from the server seed, with separate streams (`rng.bot[side]`, `rng.ulutan`).
- Each tick processes Meron then Wala, in the system order of §2.4.
- `SimState` is plain, structured-clone-safe data: plain objects, arrays and typed arrays. No classes holding hidden state; use pure functions or `system(state)` mutators.

## Shared-code wiring
- Relative imports include the `.ts` extension. Bare specifiers are not allowed in the sim (no third-party imports at all).
- The public API is only what `index.ts` re-exports (§2.5). It is a handoff contract (tasks.md): changing it means updating the spec and getting review from Carlo and Patrick.

## Versioning
- Any change that can alter a replay outcome (numbers, logic, bot) bumps `SIM_VERSION` (at least minor) **and** updates the golden fixtures in `__fixtures__/` in the same PR.
- Copy the previous version into `versions/<x.y.z>/` on a bump.
- Gameplay numbers live in `data/`, never in the database.

## Tests
- Vitest next to the code. Frame-data tests assert exact ticks.
- Golden fixtures must hash identically in Node and Deno.
- Use `sim-determinism-reviewer` before opening a PR.
