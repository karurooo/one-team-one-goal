# Game Design Specification (Combat Rules)

| Field | Value |
|---|---|
| SDLC phase | Requirements Gathering |
| Status | Draft v0.1 — all numbers are **starting tuning values**, expected to change in playtests |
| Related | [product-requirements.md](./product-requirements.md) (FR-FIGHT-*, FR-MATCH-*), [../02-design/game-engine-design.md](../02-design/game-engine-design.md) |

All timings are in **ticks** at a fixed **60 ticks/second** (1 tick ≈ 16.7 ms). All distances are in **meters**. The simulation is the single source of truth. Animations only *show* what the simulation decides.

---

## 1. Core loop

1. **Lobby:** pick a manok and a bot difficulty.
2. **Ulutan (R2):** a 3-second face-off mind game.
3. **Fight:** one round, 90 seconds, inside the ruweda.
4. **Result:** KO, Talikod, Timeout or Forfeit → rewards → back to lobby or rematch.

## 2. Glossary (in-game terms)

| Term | Meaning in game |
|---|---|
| Manok | The player's fighter (gamecock) |
| Ruweda | The circular pit (arena) |
| Meron / Wala | The two corners (Player 1 / Player 2). Meron = red, Wala = blue/white |
| Tuka | Peck — fast, weak attack |
| Sipa | Kick — slower, stronger attack using the tari |
| Lipad | Jump — airborne strike, highest damage |
| Ilag | Dodge — short dash with invulnerable frames |
| Hingal | Stamina meter |
| Tapang | Courage meter |
| Talikod | Turning away (loss condition trigger) |
| Sentensyador | Referee — enforces the Talikod rule |
| Tari | Blade attached to the left spur; affects kick/strike damage and reach |
| Llamado / Dehado | Favorite / underdog (PvP, R3) |

## 3. Arena

| Property | Value |
|---|---|
| Shape | Circle on the XZ plane, center (0, 0) |
| Fight radius | **2.0 m** (manok center is clamped inside radius − 0.15 m) |
| Start positions | Meron at (0, −0.8) facing +Z; Wala at (0, +0.8) facing −Z |
| Wall | Soft: a manok pushed into the edge is stopped; no ring-outs |
| Center mark | Visual only (1.2 m circle) |

## 4. Manok state

| Stat | Start | Range | Notes |
|---|---|---|---|
| HP | 100 | 0–100 | 0 → KO |
| Hingal (stamina) | 100 | 0–100 | Spent by actions; regenerates |
| Tapang (courage) | 100 | 0–100 | Falls when hit; 0 → Talikod |
| Body radius | 0.15 | — | Collision circle |
| Facing | angle (rad) | — | Attacks only hit inside their arc |

**Action states:** `idle`, `walk`, `tuka`, `sipa`, `lipad_crouch`, `lipad_air`, `lipad_land`, `ilag`, `hitstun`, `exhausted`, `talikod`, `ko`.

Only one action runs at a time. An action has **startup → active → recovery** phases. Inputs during startup/active/recovery are ignored, except Ilag, which can cancel the last 4 ticks of recovery ("dodge-cancel").

## 5. Movement

| Property | Value |
|---|---|
| Walk speed | 1.2 m/s |
| Turn rate | 540°/s; the manok auto-faces the opponent while walking unless the player holds **Strafe-lock off** (R2 option) |
| Acceleration | Reaches full speed in 6 ticks; stops in 4 ticks |
| Body push | Overlapping manoks push apart equally |

Default facing rule (R1): **the manok always turns toward the opponent**. Movement input is relative to the camera. This keeps the game readable for new players: you circle and space, and attacks point at the opponent.

## 6. Actions (frame data)

| Action | Startup | Active | Recovery | Range (m) | Arc | Damage | Hingal cost | Hitstun on target |
|---|---|---|---|---|---|---|---|---|
| **Tuka** (peck) | 6 | 3 | 10 | 0.40 | 60° | 4 | 5 | 10 |
| **Sipa** (kick) | 12 | 4 | 18 | 0.50 | 90° | 10 × tari | 15 | 18 |
| **Lipad** (jump) | 8 crouch | see §6.1 | 10 land | 0.55 (horizontal) | 120° | 18 × tari | 25 | 24 |
| **Ilag** (dodge) | 0 | 10 (moving), invulnerable ticks 1–6 | 8 | 0.35 dash | — | — | 15 | — |

- Damage only lands during **active** ticks, if the target's center is within *range + target radius* and inside the attack's facing arc, and the target is not invulnerable.
- One attack hits a target at most once.
- **Telegraphs:** every startup has a distinct readable pose (see engine spec). Sipa has the longest wind-up on purpose: it is strong but punishable.

### 6.1 Lipad (jump)

| Phase | Ticks | Detail |
|---|---|---|
| Crouch | 8 | Can be seen and punished |
| Airborne | 36 | Height follows a parabola, apex **0.35 m** at tick 18. The manok drifts toward its input direction at 0.8 m/s |
| Strike window | air ticks 12–24 | Hits targets on the ground or below its own height |
| Land | 10 | Vulnerable recovery |

- A grounded **Tuka** cannot hit an airborne manok above 0.15 m height.
- **Anti-air:** a grounded **Sipa** whose active frames overlap an opponent's air ticks 26–36 (descending) deals **1.3×** damage. This counters predictable jumps.

### 6.2 Clash (both airborne)

WHEN both manoks are airborne and both strike windows overlap within 0.55 m, a **Clash** starts:
1. The simulation freezes the motion for up to 30 ticks and shows a "CLASH!" prompt.
2. Each side must press **Sipa** inside the window. The **earlier valid press wins**. A press before the prompt appears (tick 0–3) counts as a "mash" and **loses**.
3. Winner deals the strike damage × 1.2; loser takes it and enters hitstun 30. If neither presses, both take half damage.
4. The bot "presses" after its reaction time (§10) with its mistake rate applied.

## 7. Hingal (stamina)

| Rule | Value |
|---|---|
| Regen | 12 per second while not attacking/dodging; ×1.5 while walking slowly or idle for > 1 s |
| Action blocked | An action that costs more than the current Hingal cannot start (the input is ignored, and a short "out of breath" puff plays) |
| Exhausted | When Hingal hits 0 → `exhausted` state for **90 ticks**: walk speed ×0.5, no Sipa/Lipad/Ilag, then Hingal resets to 30 |

## 8. Tapang (courage)

| Event | Effect |
|---|---|
| Take a hit | Tapang −(damage × 0.6) |
| Land a hit | Tapang +3 |
| Land a Lipad strike | Tapang +6 |
| Win a Clash | Tapang +10, loser −10 |
| Idle regen | +2 per second if no hit taken for 3 s (max 100) |

Tapang is shown on the HUD **and** on the model: hackle (neck feather) flare scales with Tapang (100 = fully flared, below 25 = drooping). This gives players an in-world read without looking at bars.

## 9. Win conditions and the Sentensyador rule

| Condition | Result reason | Rule |
|---|---|---|
| HP reaches 0 | `ko` | Immediate win for the other side |
| Talikod not answered | `talikod` | See below |
| Timer reaches 0 (90 s) | `timeout` | Higher HP % wins; tie → higher Tapang; tie → `draw` |
| Player quits | `forfeit` | Quitting side loses |

**Talikod / Sentensyador rule**
1. WHEN a manok's Tapang reaches 0, it enters `talikod`: it turns away for 30 ticks.
2. The **sentensyador** steps in: the fight pauses, both manoks are reset to start positions ("ulutan reset"), and the turned manok's Tapang is set to 25.
3. A **5-second (300-tick) "Sentensya" window** starts. The turned manok **must land any hit (even a Tuka)** in that window.
4. If it does → the fight continues normally. If it does not → it loses with reason `talikod`.
5. Each manok can survive the Sentensya at most **twice** per fight; the third Talikod is an immediate loss.

This makes Tapang a second "health bar" that rewards pressure and gives a dramatic comeback moment.

## 10. Bot (AI opponent)

The bot reads only the same information a human sees (positions, current action and phase, meters) **through the simulation API**, with a reaction delay. It produces the same input format as a human, and it runs inside the simulation with the match seed. The server can therefore replay bot behavior exactly.

| Parameter | Easy | Normal | Hard |
|---|---|---|---|
| Reaction time | 450 ms (27 ticks) | 280 ms (17 ticks) | 160 ms (10 ticks) |
| Mistake rate (wrong or late choice) | 30% | 15% | 5% |
| Uses anti-air Sipa | Never | Sometimes | Often |
| Dodge-cancels | No | No | Yes |
| Manages Hingal (avoids exhaustion) | No | Partly | Yes |
| Preferred spacing | Random | Mid-range | Just outside player's Tuka range |

**Behavior loop (utility-based):** each decision tick the bot scores the options (approach, retreat, circle, Tuka, Sipa, Lipad, Ilag, wait) from the current situation, adds seeded noise by difficulty, and picks the highest score. It must never read the player's *future* input.

## 11. Manok breeds (R1 has one; R2 adds more)

Each breed = **base stat modifiers + one active skill + one passive**. The active skill uses a dedicated button (**L**) with a cooldown.

| Breed | Archetype | Modifiers | Skill (button L) | Passive | Release |
|---|---|---|---|---|---|
| **Talisayin** | All-rounder | none | *Banat* — a 3-hit Tuka string (startup 5, 3×2 dmg + 6 finisher), CD 6 s | *Sigla*: Tapang idle regen ×1.5 | R1 |
| Kelso | Counter-fighter | HP 95 | *Basa* — 30-tick counter stance; if hit, auto-dodge and punish with Sipa, CD 8 s | Sees opponent Hingal on HUD | R2 |
| Hatch | Tank | HP 115, walk 1.05 | *Tibay* — next hit taken deals 50% damage, CD 10 s | Hitstun taken −20% | R2 |
| Roundhead | Evasive | HP 90, walk 1.35 | *Ikot* — fast circle-step behind the opponent, CD 7 s | Ilag recovery −4 ticks | R2 |
| Sweater | Rushdown | — | *Sunod-sunod* — Sipa can chain into a 2nd Sipa, CD 8 s | +10% damage while Hingal > 70 | R2 |
| Asil | Ground fighter | HP 110, walk 1.0 | *Kapit* — grab + 3 pecks, CD 10 s | Sipa damage ×1.15; Lipad costs +10 Hingal | R2 |

Balance rule: no breed may have a win rate above **55%** vs. the others in Hard-bot mirror testing before a release.

## 12. Tari (R2)

| Tari | Damage multiplier (Sipa/Lipad) | Reach bonus | Sipa startup | Price |
|---|---|---|---|---|
| Standard (default) | 1.0 | 0 | 0 | Free |
| Short blade | 0.9 | −0.03 m | −2 ticks | 400 coins |
| Long blade | 1.1 | +0.05 m | +2 ticks | 600 coins |

## 13. Ulutan (pre-fight, R2)

A 3-second face-off. Each side secretly picks **Flare**, **Feint** or **Steady**:
- Flare beats Steady → winner Tapang +10, loser −10.
- Steady beats Feint → winner gets first move: +10 Hingal.
- Feint beats Flare → winner's first hit deals +4 damage.
- Same choice → no effect.

The bot chooses with weighted randomness from the match seed.

## 14. Economy (soft currency only)

| Source | Coins |
|---|---|
| Bot win — Easy / Normal / Hard | 10 / 25 / 50 |
| Bot loss (verified, ≥ 30 s fought) | 2 |
| First win of the day | +50 bonus |
| Daily cap from bot fights | 300 (see OQ-04) |

**Coins have no monetary value and can never be bought, sold or withdrawn.** All coin changes happen server-side and are recorded in `coin_ledger`.

## 15. Camera, feel and feedback (requirements for the engine)

- Fixed high 3/4 camera that tracks the midpoint of both manoks and zooms between 2.2 m and 3.5 m distance as they separate. No free orbit during fights.
- **Hit-pause:** 4 ticks on Tuka hits, 6 on Sipa, 8 on Lipad/Clash (the simulation freezes; the render keeps drawing).
- Feather-burst particles on hits; dust ring on landing; screen shake on Lipad hits (disabled by "reduce motion").
- Every attack's startup pose must be distinguishable in under 100 ms of viewing. This is validated in playtests.
