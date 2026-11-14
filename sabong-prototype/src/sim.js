/* Sabong fight prototype — simulation (fixed 60 ticks/s).
 * Follows docs/01-requirements/game-design.md. PROTOTYPE NOTE: uses floats for speed of iteration;
 * the production sim must use integer fixed-point math (game-engine-design §2.2).
 */
(function (root) {
  'use strict';
  const TPS = 60;
  const TAPANG_LOSS = 1.8;   // tuned in prototype (spec v0.1 had 0.6, which made Talikod unreachable)
  const ARENA_R = 2.0, BODY_R = 0.15;
  const ROUND_TICKS = 90 * TPS;
  const DEG = Math.PI / 180;

  const A = {
    tuka:  { startup: 6, active: 3, recovery: 10, range: 0.40, arc: 60, dmg: 4, cost: 5, stun: 10, pause: 4 },
    sipa:  { startup: 12, active: 4, recovery: 18, range: 0.50, arc: 90, dmg: 10, cost: 15, stun: 18, pause: 6 },
    lipad: { crouch: 8, air: 36, land: 10, range: 0.55, arc: 120, dmg: 18, cost: 25, stun: 24, pause: 8,
             winStart: 12, winEnd: 24, apex: 0.35, drift: 0.8 / TPS },
    ilag:  { move: 10, inv: 6, recovery: 8, dist: 0.35, cost: 15 },
    banat: { hits: [5, 13, 21], dmgs: [2, 2, 6], activeLen: 2, total: 32, range: 0.42, arc: 70, cost: 10, cd: 6 * TPS, stun: 8, pause: 4 },
  };
  const WALK = 1.2 / TPS;
  const BUFFER = 6;

  function rngFrom(seed) {             // mulberry32
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function makeManok(side) {
    const meron = side === 'meron';
    return {
      side, x: 0, z: meron ? -0.8 : 0.8, vx: 0, vz: 0, face: meron ? 0 : Math.PI, h: 0,
      hp: 100, hingal: 100, tapang: 100,
      act: 'idle', t: 0, hitDone: false, banatHits: 0, buf: null, bufT: 0,
      cd: 0, exh: 0, sinceHit: 999, idleT: 0, talikodCount: 0, stunLen: 0,
      dirx: 0, dirz: 0, stats: { dmg: 0, tuka: 0, sipa: 0, lipad: 0, skill: 0, clash: 0 },
    };
  }

  function create(seed) {
    return {
      tick: 0, phase: 'ready', phaseT: 0, timer: ROUND_TICKS, hitpause: 0,
      m: [makeManok('meron'), makeManok('wala')],
      clash: null, talikod: null, sentensya: null, result: null, rng: rngFrom(seed || 1),
    };
  }

  // ---------------------------------------------------------------- helpers
  const dist = (a, b) => Math.hypot(b.x - a.x, b.z - a.z);
  function angleTo(a, b) { return Math.atan2(b.x - a.x, b.z - a.z); }   // forward = (sin, cos)
  function wrap(a) { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; }
  function turnToward(m, target, maxStep) {
    const d = wrap(target - m.face);
    m.face = wrap(m.face + Math.max(-maxStep, Math.min(maxStep, d)));
  }
  function isFree(m) { return m.act === 'idle' || m.act === 'walk'; }
  function airT(m) { return m.act === 'lipad' ? m.t - A.lipad.crouch : -1; }
  function isAirborne(m) { const at = airT(m); return at >= 0 && at < A.lipad.air; }
  function actLength(m) {
    switch (m.act) {
      case 'tuka': return A.tuka.startup + A.tuka.active + A.tuka.recovery;
      case 'sipa': return A.sipa.startup + A.sipa.active + A.sipa.recovery;
      case 'lipad': return A.lipad.crouch + A.lipad.air + A.lipad.land;
      case 'ilag': return A.ilag.move + A.ilag.recovery;
      case 'banat': return A.banat.total;
      case 'hitstun': return m.stunLen;
      default: return 0;
    }
  }
  function inRecoveryTail(m) { const L = actLength(m); return L > 0 && m.t >= L - BUFFER; }

  function canStart(m, action) {
    if (m.exh > 0 && (action === 'sipa' || action === 'lipad' || action === 'ilag')) return false;
    const cost = action === 'skill' ? A.banat.cost : A[action].cost;
    if (m.hingal < cost) return false;
    if (action === 'skill' && m.cd > 0) return false;
    return true;
  }

  function startAction(s, m, action, inp, ev) {
    const cost = action === 'skill' ? A.banat.cost : A[action].cost;
    m.hingal -= cost;
    m.act = action === 'skill' ? 'banat' : action;
    m.t = 0; m.hitDone = false; m.banatHits = 0; m.idleT = 0;
    if (action === 'skill') m.cd = A.banat.cd;
    if (action === 'ilag') {
      let dx = inp.mx, dz = inp.mz;
      if (!dx && !dz) { const o = s.m[m.side === 'meron' ? 1 : 0]; const a = angleTo(o, m); dx = Math.sin(a); dz = Math.cos(a); }
      const L = Math.hypot(dx, dz) || 1; m.dirx = dx / L; m.dirz = dz / L;
    }
    ev.push({ type: 'action', side: m.side, action: m.act });
    if (m.hingal <= 0) { m.hingal = 0; m.exh = 90; ev.push({ type: 'exhausted', side: m.side }); }
  }

  // ---------------------------------------------------------------- hits
  function canHit(a, b, range, arc) {
    if (b.act === 'ko' || b.act === 'talikod') return false;
    if (b.act === 'ilag' && b.t < A.ilag.inv) return false;
    if (dist(a, b) > range + BODY_R) return false;
    const d = Math.abs(wrap(angleTo(a, b) - a.face));
    return d <= (arc / 2) * DEG;
  }

  function applyHit(s, a, b, dmg, stun, pause, kind, ev) {
    b.hp = Math.max(0, b.hp - dmg);
    b.tapang = Math.max(0, b.tapang - dmg * TAPANG_LOSS);
    a.tapang = Math.min(100, a.tapang + (kind === 'lipad' ? 6 : 3));
    a.stats.dmg += dmg; a.stats[kind] = (a.stats[kind] || 0) + 1;
    b.sinceHit = 0;
    const wasAir = b.h > 0.02;
    b.act = 'hitstun'; b.t = 0; b.stunLen = stun; b.buf = null;
    const ang = angleTo(a, b); b.vx = Math.sin(ang) * 0.02; b.vz = Math.cos(ang) * 0.02;
    if (wasAir) b.airFall = true;
    s.hitpause = pause;
    ev.push({ type: 'hit', side: a.side, target: b.side, kind, dmg, x: b.x, z: b.z, h: b.h });
    if (s.sentensya && s.sentensya.side === a.side) {
      ev.push({ type: 'sentensya_ok', side: a.side });
      s.sentensya = null;
    }
  }

  // ---------------------------------------------------------------- step
  function step(s, inputs) {
    const ev = [];
    s.tick++;
    if (s.phase === 'ended') { for (const m of s.m) m.t++; return ev; }

    // buffer presses even while frozen
    for (let i = 0; i < 2; i++) bufferPress(s.m[i], inputs[i]);

    if (s.phase === 'ready') {
      s.phaseT++;
      if (s.phaseT === 1) ev.push({ type: 'prompt', text: 'ready' });
      if (s.phaseT >= 75) { s.phase = 'fight'; s.phaseT = 0; ev.push({ type: 'prompt', text: 'laban' }); }
      animateIdle(s); return ev;
    }
    if (s.hitpause > 0) { s.hitpause--; return ev; }

    if (s.phase === 'clash') { stepClash(s, inputs, ev); return ev; }
    if (s.phase === 'talikod') { stepTalikod(s, ev); return ev; }

    // ---- fight
    const [M, W] = s.m;
    const order = (s.tick & 1) ? [1, 0] : [0, 1];          // alternate who goes first (fairness)
    for (const i of order) stepActor(s, s.m[i], s.m[1 - i], inputs[i], ev);
    // clash check (both in strike window)
    if (inWindow(M) && inWindow(W) && dist(M, W) <= A.lipad.range + BODY_R && !M.hitDone && !W.hitDone) {
      s.phase = 'clash'; s.clash = { t: 0, winner: null, mash: [false, false] };
      ev.push({ type: 'clash_started' });
      return ev;
    }
    for (const i of order) resolveAttacks(s, s.m[i], s.m[1 - i], ev);
    pushApart(M, W);
    for (const m of s.m) meters(s, m, ev);

    // sentensya window
    if (s.sentensya) {
      s.sentensya.left--;
      if (s.sentensya.left <= 0) {
        const loser = s.m[s.sentensya.side === 'meron' ? 0 : 1];
        end(s, loser.side === 'meron' ? 'wala' : 'meron', 'talikod', ev);
        return ev;
      }
    }
    // win checks
    for (const m of s.m) if (m.hp <= 0) { m.act = 'ko'; m.t = 0; end(s, m.side === 'meron' ? 'wala' : 'meron', 'ko', ev); return ev; }
    for (const m of s.m) if (m.tapang <= 0 && m.act !== 'talikod') { startTalikod(s, m, ev); return ev; }
    s.timer--;
    if (s.timer <= 0) {
      let w = 'draw';
      if (M.hp !== W.hp) w = M.hp > W.hp ? 'meron' : 'wala';
      else if (Math.round(M.tapang) !== Math.round(W.tapang)) w = M.tapang > W.tapang ? 'meron' : 'wala';
      end(s, w, 'timeout', ev);
    }
    return ev;
  }

  function bufferPress(m, inp) {
    if (!inp) return;
    const order = ['skill', 'lipad', 'sipa', 'tuka', 'ilag'];
    for (const k of order) if (inp[k]) { m.buf = k; m.bufT = BUFFER; break; }
  }

  function animateIdle(s) { for (const m of s.m) m.t++; }

  function stepActor(s, m, o, inp, ev) {
    m.t++;
    if (m.cd > 0) m.cd--;
    if (m.exh > 0) { m.exh--; if (m.exh === 0) { m.hingal = Math.max(m.hingal, 30); ev.push({ type: 'recovered', side: m.side }); } }
    m.sinceHit++;
    if (m.bufT > 0) m.bufT--; else m.buf = null;

    // finish actions
    const L = actLength(m);
    if (L > 0 && m.t >= L) { m.act = 'idle'; m.t = 0; m.airFall = false; }
    if (m.act === 'hitstun' && m.airFall) { m.h = Math.max(0, m.h - 0.03); }

    // start new action (from free state, or dodge-cancel / buffer at end of recovery)
    if (isFree(m) && m.buf && canStart(m, m.buf)) {
      startAction(s, m, m.buf, inp, ev); m.buf = null; m.bufT = 0;
    } else if (m.buf === 'ilag' && inRecoveryTail(m) && m.act !== 'hitstun' && m.act !== 'lipad' && m.act !== 'ilag' && canStart(m, 'ilag')) {
      startAction(s, m, 'ilag', inp, ev); m.buf = null; m.bufT = 0;      // dodge-cancel
    }

    // movement
    const free = isFree(m);
    if (free) {
      const speed = WALK * (m.exh > 0 ? 0.5 : 1);
      let tx = inp.mx * speed, tz = inp.mz * speed;
      const k = (inp.mx || inp.mz) ? 1 / 6 : 1 / 4;
      m.vx += (tx - m.vx) * k; m.vz += (tz - m.vz) * k;
      m.act = Math.hypot(m.vx, m.vz) > 0.0025 ? 'walk' : 'idle';
      if (m.act === 'idle') m.idleT++; else m.idleT = 0;
    } else if (m.act === 'ilag') {
      if (m.t < A.ilag.move) { const v = A.ilag.dist / A.ilag.move; m.vx = m.dirx * v; m.vz = m.dirz * v; }
      else { m.vx *= 0.5; m.vz *= 0.5; }
    } else if (m.act === 'lipad') {
      const at = airT(m);
      if (at === 0) {
        let dx = inp.mx, dz = inp.mz;
        if (!dx && !dz) { const a = angleTo(m, o); dx = Math.sin(a); dz = Math.cos(a); }
        const Ln = Math.hypot(dx, dz) || 1; m.dirx = dx / Ln; m.dirz = dz / Ln;
        ev.push({ type: 'takeoff', side: m.side });
      }
      if (at >= 0 && at < A.lipad.air) {
        const u = (at + 1) / A.lipad.air;
        m.h = 4 * A.lipad.apex * u * (1 - u);
        m.vx = m.dirx * A.lipad.drift; m.vz = m.dirz * A.lipad.drift;
        if (at === A.lipad.air - 1) { m.h = 0; ev.push({ type: 'land', side: m.side, x: m.x, z: m.z }); }
      } else { m.vx *= 0.6; m.vz *= 0.6; if (at >= A.lipad.air) m.h = 0; }
    } else {
      m.vx *= 0.7; m.vz *= 0.7;
    }
    m.x += m.vx; m.z += m.vz;
    const r = Math.hypot(m.x, m.z), maxR = ARENA_R - BODY_R;
    if (r > maxR) { m.x *= maxR / r; m.z *= maxR / r; }

    // facing
    const tracking = free || m.act === 'hitstun' || m.act === 'exhausted' ||
      (m.act === 'tuka' && m.t < A.tuka.startup) || (m.act === 'sipa' && m.t < A.sipa.startup) ||
      (m.act === 'lipad' && m.t < A.lipad.crouch + 6) || (m.act === 'banat' && m.t < 4);
    if (tracking) turnToward(m, angleTo(m, o), 9 * DEG);
  }

  function inWindow(m) { const at = airT(m); return at >= A.lipad.winStart && at <= A.lipad.winEnd; }

  function resolveAttacks(s, a, b, ev) {
    if (a.act === 'tuka' && !a.hitDone) {
      const st = A.tuka;
      if (a.t >= st.startup && a.t < st.startup + st.active && b.h <= 0.15 && canHit(a, b, st.range, st.arc)) {
        a.hitDone = true; applyHit(s, a, b, st.dmg, st.stun, st.pause, 'tuka', ev);
      }
    } else if (a.act === 'sipa' && !a.hitDone) {
      const st = A.sipa;
      if (a.t >= st.startup && a.t < st.startup + st.active) {
        const bat = airT(b);
        const antiAir = bat >= 26 && bat < A.lipad.air;
        if ((b.h <= 0.15 || antiAir) && canHit(a, b, st.range, st.arc)) {
          a.hitDone = true; applyHit(s, a, b, Math.round(st.dmg * (antiAir ? 1.3 : 1)), st.stun, st.pause, 'sipa', ev);
          if (antiAir) ev.push({ type: 'anti_air', side: a.side });
        }
      }
    } else if (a.act === 'lipad' && !a.hitDone && inWindow(a)) {
      const st = A.lipad;
      if (b.h <= a.h + 0.01 && canHit(a, b, st.range, st.arc)) {
        a.hitDone = true; applyHit(s, a, b, st.dmg, st.stun, st.pause, 'lipad', ev);
      }
    } else if (a.act === 'banat') {
      const st = A.banat;
      const idx = st.hits.findIndex((h) => a.t >= h && a.t < h + st.activeLen);
      if (idx >= 0 && a.banatHits <= idx && b.h <= 0.15 && canHit(a, b, st.range, st.arc)) {
        a.banatHits = idx + 1; applyHit(s, a, b, st.dmgs[idx], st.stun, st.pause, 'skill', ev);
      }
    }
  }

  function pushApart(a, b) {
    if (Math.abs(a.h - b.h) > 0.2) return;
    const d = dist(a, b), min = 2 * BODY_R;
    if (d < min && d > 1e-6) {
      const push = (min - d) / 2, nx = (b.x - a.x) / d, nz = (b.z - a.z) / d;
      a.x -= nx * push; a.z -= nz * push; b.x += nx * push; b.z += nz * push;
    } else if (d <= 1e-6) { a.x -= 0.01; b.x += 0.01; }
  }

  function meters(s, m, ev) {
    const attacking = !(m.act === 'idle' || m.act === 'walk' || m.act === 'hitstun');
    if (!attacking && m.exh === 0) {
      let r = 12 / TPS;
      if (m.idleT > 60 || (m.act === 'walk' && Math.hypot(m.vx, m.vz) < WALK * 0.5)) r *= 1.5;
      m.hingal = Math.min(100, m.hingal + r);
    }
    if (m.sinceHit > 180) m.tapang = Math.min(100, m.tapang + 2 / TPS * (1.5)); // Talisayin passive "Sigla": x1.5
  }

  // ---------------------------------------------------------------- clash
  function stepClash(s, inputs, ev) {
    const c = s.clash; c.t++;
    for (let i = 0; i < 2; i++) {
      if (inputs[i] && inputs[i].sipa && c.winner === null) {
        if (c.t <= 3) c.mash[i] = true;
        else if (!c.mash[i]) c.winner = i;
      }
    }
    const bothMash = c.mash[0] && c.mash[1];
    if (c.winner === null && c.mash[0] !== c.mash[1] && c.t > 3) c.winner = c.mash[0] ? 1 : 0;
    if (c.winner !== null || c.t >= 30 || bothMash) {
      const [M, W] = s.m, st = A.lipad;
      if (c.winner !== null) {
        const a = s.m[c.winner], b = s.m[1 - c.winner];
        a.hitDone = true; b.hitDone = true;
        a.stats.clash++;
        applyHit(s, a, b, Math.round(st.dmg * 1.2), 30, 8, 'lipad', ev);
        a.tapang = Math.min(100, a.tapang + 10); b.tapang = Math.max(0, b.tapang - 10);
        ev.push({ type: 'clash_resolved', winner: a.side });
      } else {
        const half = Math.round(st.dmg / 2);
        for (const m of [M, W]) { m.hp = Math.max(0, m.hp - half); m.tapang = Math.max(0, m.tapang - half * TAPANG_LOSS); m.act = 'hitstun'; m.t = 0; m.stunLen = 20; m.airFall = true; m.hitDone = true; }
        s.hitpause = 8;
        ev.push({ type: 'clash_resolved', winner: null });
      }
      s.clash = null; s.phase = 'fight';
    }
  }

  // ---------------------------------------------------------------- talikod / sentensya
  function startTalikod(s, m, ev) {
    m.talikodCount++;
    if (m.talikodCount >= 3) { m.act = 'talikod'; m.t = 0; end(s, m.side === 'meron' ? 'wala' : 'meron', 'talikod', ev); return; }
    m.act = 'talikod'; m.t = 0; m.h = 0; m.vx = m.vz = 0;
    const o = s.m[m.side === 'meron' ? 1 : 0]; o.act = 'idle'; o.t = 0; o.vx = o.vz = 0;
    s.sentensya = null;
    s.phase = 'talikod'; s.talikod = { side: m.side, t: 0 };
    ev.push({ type: 'talikod', side: m.side, count: m.talikodCount });
  }

  function stepTalikod(s, ev) {
    const tk = s.talikod; tk.t++;
    for (const m of s.m) m.t++;
    if (tk.t === 60) {
      // sentensyador resets the fighters (ulutan reset)
      const [M, W] = s.m;
      Object.assign(M, { x: 0, z: -0.8, face: 0, vx: 0, vz: 0, h: 0, act: 'idle', t: 0, buf: null });
      Object.assign(W, { x: 0, z: 0.8, face: Math.PI, vx: 0, vz: 0, h: 0, act: 'idle', t: 0, buf: null });
      const turned = s.m[tk.side === 'meron' ? 0 : 1];
      turned.tapang = 25; turned.sinceHit = 0;
      s.sentensya = { side: tk.side, left: 300 };
      s.phase = 'fight'; s.talikod = null;
      ev.push({ type: 'sentensya_started', side: tk.side });
    }
  }

  function end(s, winner, reason, ev) {
    s.phase = 'ended';
    s.result = { winner, reason, ticks: ROUND_TICKS - s.timer };
    for (const m of s.m) if (m.act !== 'ko' && m.act !== 'talikod') {
      if (m.side !== winner && reason === 'talikod') { m.act = 'talikod'; m.t = 0; }
      else if (m.act !== 'idle') { m.act = 'idle'; m.t = 0; }
    }
    ev.push({ type: 'match_ended', winner, reason });
  }

  function forfeit(s, side) {
    if (s.phase === 'ended') return [];
    const ev = []; end(s, side === 'meron' ? 'wala' : 'meron', 'forfeit', ev); return ev;
  }

  const api = { TPS, ARENA_R, BODY_R, ROUND_TICKS, A, create, step, forfeit, dist, angleTo, airT, actLength, wrap };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.SabongSim = api;
})(typeof window !== 'undefined' ? window : globalThis);
