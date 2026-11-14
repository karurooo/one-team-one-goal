# Sabong — fight prototype

> **Reference only — not production code.** This prototype uses floating-point math for quick iteration. The production simulation lives in `supabase/functions/_shared/sim/` and must be integer fixed-point (`docs/02-design/game-engine-design.md` §2.2). Do not copy code from here into the sim.

Single-page prototype: you (Meron, Talisayin) vs. a bot in the ruweda.

- `src/sim.js` — fight simulation, fixed 60 ticks/s, rules from `docs/01-requirements/game-design.md`.
  Floats for speed of iteration; the production sim must be integer fixed-point (game-engine-design §2.2).
- `src/bot.js` — utility AI with reaction delay; Easy / Normal / Hard profiles.
- `src/game.js` — Babylon.js client: arena, two manok instances driven by the sim, camera, input, HUD.
- `src/index.html` — page + HUD markup.
- `build.py` — inlines the scripts and `manok.glb` (base64) into `dist/index.html`.
  Edit the model path at the top if `manok.glb` lives elsewhere.
- `test_sim.js` — headless bot-vs-bot balance run: `node test_sim.js`.

Build: `python3 build.py dist/index.html`, then open `dist/index.html` in a browser.
