/* Sabong fight prototype — bot (utility AI with reaction delay). game-design.md §10 */
(function (root) {
  'use strict';
  const Sim = (typeof module !== 'undefined' && module.exports) ? require('./sim.js') : root.SabongSim;
  const A = Sim.A;

  const PROFILES = {
    easy:   { react: 27, mistake: 0.30, antiAir: 0.0,  dodgeCancel: false, manage: 0.0, noise: 0.55, aggression: 0.8 },
    normal: { react: 17, mistake: 0.15, antiAir: 0.45, dodgeCancel: false, manage: 0.5, noise: 0.35, aggression: 1.0 },
    hard:   { react: 10, mistake: 0.05, antiAir: 0.85, dodgeCancel: true,  manage: 1.0, noise: 0.18, aggression: 1.15 },
  };

  function phaseOf(act, t) {
    if (act === 'tuka') return t < A.tuka.startup ? 'startup' : t < A.tuka.startup + A.tuka.active ? 'active' : 'recovery';
    if (act === 'sipa') return t < A.sipa.startup ? 'startup' : t < A.sipa.startup + A.sipa.active ? 'active' : 'recovery';
    if (act === 'banat') return t < 22 ? 'active' : 'recovery';
    if (act === 'lipad') {
      const at = t - A.lipad.crouch;
      if (at < 0) return 'startup';
      if (at < 26) return 'air';
      if (at < A.lipad.air) return 'air_desc';
      return 'recovery';
    }
    if (act === 'ilag') return t < A.ilag.move ? 'active' : 'recovery';
    if (act === 'hitstun' || act === 'exhausted') return 'recovery';
    return 'free';
  }

  function makeBot(difficulty, seed, sideIndex) {
    const P = PROFILES[difficulty] || PROFILES.normal;
    let a = (seed >>> 0) || 7;
    const rng = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const hist = [];
    let plan = { mx: 0, mz: 0 }, press = null, nextDecide = 0, circleSign = 1, clashPressAt = -1, clashMash = false;

    function observe(s) {
      const o = s.m[1 - sideIndex];
      hist.push({ x: o.x, z: o.z, h: o.h, act: o.act, t: o.t, hingal: o.hingal });
      if (hist.length > 64) hist.shift();
    }

    function think(s) {
      observe(s);
      const me = s.m[sideIndex];
      const inp = { mx: 0, mz: 0, tuka: false, sipa: false, lipad: false, ilag: false, skill: false };
      if (s.phase === 'clash') {
        if (s.clash.t === 1) {
          clashMash = rng() < P.mistake / 2;
          clashPressAt = clashMash ? 1 : Math.max(4, P.react + Math.floor((rng() - 0.5) * 8));
        }
        if (s.clash.t === clashPressAt) inp.sipa = true;
        return inp;
      }
      if (s.phase !== 'fight') return inp;
      const obs = hist[Math.max(0, hist.length - 1 - P.react)];
      if (!obs) return inp;

      const dx = obs.x - me.x, dz = obs.z - me.z, d = Math.hypot(dx, dz) || 1e-6;
      const ux = dx / d, uz = dz / d;
      const oph = phaseOf(obs.act, obs.t);
      const oppAttacking = (oph === 'startup' || oph === 'active') && obs.act !== 'ilag';
      const oppRange = obs.act === 'sipa' ? A.sipa.range : obs.act === 'lipad' ? A.lipad.range + 0.3 : A.tuka.range;
      const free = me.act === 'idle' || me.act === 'walk';

      // dodge-cancel (hard)
      if (P.dodgeCancel && !free && oppAttacking && d < oppRange + 0.3 && me.hingal >= A.ilag.cost && rng() > P.mistake) {
        const L = Sim.actLength(me); if (L && me.t >= L - 6 && me.act !== 'hitstun') { inp.ilag = true; }
      }

      if (s.tick >= nextDecide || (free && press === 'done')) {
        nextDecide = s.tick + 4; press = null;
        const exhausted = me.exh > 0;
        const lowH = me.hingal < 30;
        const opts = [];
        const add = (k, v) => opts.push({ k, v: v + rng() * P.noise });
        add('approach', d > 0.7 ? 1.0 * P.aggression : d > 0.5 ? 0.25 : 0.05);
        add('retreat', (oppAttacking && d < oppRange + 0.25 ? 0.7 : 0.05) + (lowH ? 0.5 * P.manage : 0));
        add('circle', 0.3 + (d > 0.45 && d < 0.9 ? 0.25 : 0));
        if (free) {
          if (d < 0.48 && me.hingal >= A.tuka.cost) add('tuka', (0.55 + (oph === 'recovery' ? 0.4 : 0)) * P.aggression);
          if (!exhausted && d < 0.58 && me.hingal >= A.sipa.cost) {
            let v = (0.4 + (oph === 'recovery' ? 0.6 : 0)) * P.aggression;
            if (lowH) v -= 0.3 * P.manage;
            add('sipa', v);
          }
          if (!exhausted && obs.act === 'lipad' && oph === 'air_desc' && d < 0.75 && me.hingal >= A.sipa.cost && rng() < P.antiAir) add('sipa', 1.6);
          if (!exhausted && d > 0.5 && d < 1.1 && me.hingal >= A.lipad.cost) add('lipad', (0.32 + (oph === 'recovery' ? 0.3 : 0)) * P.aggression - (lowH ? 0.4 * P.manage : 0));
          if (!exhausted && oppAttacking && d < oppRange + 0.3 && me.hingal >= A.ilag.cost) add('ilag', 0.9 * (1 - P.mistake));
          if (me.cd === 0 && d < 0.45 && me.hingal >= A.banat.cost) add('skill', 0.5 * P.aggression);
        }
        add('wait', 0.12 + (lowH ? 0.5 * P.manage : 0));
        opts.sort((p, q) => q.v - p.v);
        let pick = opts[0];
        if (opts.length > 1 && rng() < P.mistake) pick = opts[1];
        if (rng() < 0.08) circleSign = -circleSign;
        switch (pick.k) {
          case 'approach': plan = { mx: ux, mz: uz }; break;
          case 'retreat': plan = { mx: -ux, mz: -uz }; break;
          case 'circle': plan = { mx: -uz * circleSign + ux * 0.25, mz: ux * circleSign + uz * 0.25 }; break;
          case 'wait': plan = { mx: 0, mz: 0 }; break;
          case 'ilag': plan = { mx: -uz * circleSign - ux * 0.5, mz: ux * circleSign - uz * 0.5 }; press = 'ilag'; break;
          default: plan = { mx: 0, mz: 0 }; press = pick.k;
        }
        // stay off the wall
        const r = Math.hypot(me.x, me.z);
        if (r > 1.6) { plan.mx -= me.x / r * 0.8; plan.mz -= me.z / r * 0.8; }
        const L = Math.hypot(plan.mx, plan.mz); if (L > 1) { plan.mx /= L; plan.mz /= L; }
      }
      inp.mx = plan.mx; inp.mz = plan.mz;
      if (press && press !== 'done') { inp[press] = true; press = 'done'; }
      return inp;
    }
    return { think, profile: P };
  }

  const api = { makeBot, PROFILES };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.SabongBot = api;
})(typeof window !== 'undefined' ? window : globalThis);
