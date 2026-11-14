/* Sabong fight prototype — Babylon.js client: arena, manok views, camera, input, HUD, loop. */
(function () {
  'use strict';
  const Sim = window.SabongSim, Bot = window.SabongBot;
  const $ = (id) => document.getElementById(id);
  const TICK_MS = 1000 / 60;

  // ------------------------------------------------------------------ engine & scene
  const canvas = $('c');
  const engine = new BABYLON.Engine(canvas, true, { stencil: true, preserveDrawingBuffer: false }, true);
  engine.setHardwareScalingLevel(1 / Math.min(window.devicePixelRatio || 1, 1.5));
  const scene = new BABYLON.Scene(engine);
  scene.clearColor = new BABYLON.Color4(0.11, 0.075, 0.055, 1);
  scene.fogMode = BABYLON.Scene.FOGMODE_EXP2; scene.fogDensity = 0.045; scene.fogColor = new BABYLON.Color3(0.11, 0.075, 0.055);

  const cam = new BABYLON.ArcRotateCamera('cam', -Math.PI / 2 - 0.55, 0.98, 2.8, new BABYLON.Vector3(0, 0.3, 0), scene);
  cam.minZ = 0.05; cam.fov = 0.9;

  const hemi = new BABYLON.HemisphericLight('h', new BABYLON.Vector3(0.2, 1, -0.1), scene);
  hemi.intensity = 0.55; hemi.groundColor = new BABYLON.Color3(0.35, 0.24, 0.16);
  const sun = new BABYLON.DirectionalLight('sun', new BABYLON.Vector3(-0.45, -1, 0.35), scene);
  sun.position = new BABYLON.Vector3(3, 6, -3); sun.intensity = 0.95;
  const shadows = new BABYLON.ShadowGenerator(1024, sun);
  shadows.useBlurExponentialShadowMap = true; shadows.blurKernel = 12; shadows.darkness = 0.35;

  function mat(name, r, g, b, emissive) {
    const m = new BABYLON.StandardMaterial(name, scene);
    m.diffuseColor = new BABYLON.Color3(r, g, b); m.specularColor = new BABYLON.Color3(0.05, 0.05, 0.05);
    if (emissive) m.emissiveColor = new BABYLON.Color3(r * emissive, g * emissive, b * emissive);
    return m;
  }

  // ------------------------------------------------------------------ the ruweda (arena)
  (function buildArena() {
    const ground = BABYLON.MeshBuilder.CreateGround('ground', { width: 30, height: 30 }, scene);
    ground.material = mat('groundM', 0.2, 0.15, 0.11); ground.position.y = -0.01;
    const sand = BABYLON.MeshBuilder.CreateDisc('sand', { radius: 2.35, tessellation: 72 }, scene);
    sand.rotation.x = Math.PI / 2; sand.position.y = 0.001; sand.receiveShadows = true;
    sand.material = mat('sandM', 0.56, 0.42, 0.28);
    const mark = BABYLON.MeshBuilder.CreateTorus('mark', { diameter: 1.2, thickness: 0.012, tessellation: 64 }, scene);
    mark.position.y = 0.003; mark.material = mat('markM', 0.5, 0.36, 0.23);
    // plank wall
    const plank = BABYLON.MeshBuilder.CreateBox('plank', { width: 0.3, height: 0.36, depth: 0.05 }, scene);
    plank.material = mat('plankM', 0.42, 0.26, 0.13); plank.isVisible = false;
    const N = 52;
    for (let i = 0; i < N; i++) {
      const a = (i / N) * Math.PI * 2, inst = plank.createInstance('p' + i);
      inst.position.set(Math.sin(a) * 2.42, 0.18, Math.cos(a) * 2.42); inst.rotation.y = a;
      inst.scaling.y = 0.92 + ((i * 37) % 10) / 60;
    }
    const rail = BABYLON.MeshBuilder.CreateTorus('rail', { diameter: 4.86, thickness: 0.06, tessellation: 72 }, scene);
    rail.position.y = 0.37; rail.material = mat('railM', 0.3, 0.18, 0.09);
    // poles + banderitas (bunting)
    const poleM = mat('poleM', 0.32, 0.22, 0.12);
    const colors = [[0.84, 0.2, 0.17], [0.96, 0.71, 0.18], [0.18, 0.44, 0.85], [0.95, 0.93, 0.88], [0.2, 0.62, 0.32]];
    const flagSrc = colors.map((c, i) => {
      const f = BABYLON.MeshBuilder.CreateDisc('flag' + i, { radius: 0.09, tessellation: 3, sideOrientation: BABYLON.Mesh.DOUBLESIDE }, scene);
      f.material = mat('flagM' + i, c[0], c[1], c[2], 0.25); f.isVisible = false; return f;
    });
    const poles = 6, R = 2.75;
    for (let p = 0; p < poles; p++) {
      const a = (p / poles) * Math.PI * 2 + 0.3;
      const pole = BABYLON.MeshBuilder.CreateCylinder('pole' + p, { height: 2.6, diameter: 0.07 }, scene);
      pole.position.set(Math.sin(a) * R, 1.3, Math.cos(a) * R); pole.material = poleM;
    }
    let k = 0;
    for (let p = 0; p < poles; p++) {
      const a0 = (p / poles) * Math.PI * 2 + 0.3, a1 = ((p + 1) / poles) * Math.PI * 2 + 0.3;
      const x0 = Math.sin(a0) * R, z0 = Math.cos(a0) * R, x1 = Math.sin(a1) * R, z1 = Math.cos(a1) * R;
      for (let j = 1; j < 12; j++) {
        const u = j / 12, x = x0 + (x1 - x0) * u, z = z0 + (z1 - z0) * u, y = 2.45 - Math.sin(u * Math.PI) * 0.35;
        const f = flagSrc[k++ % flagSrc.length].createInstance('f' + p + '_' + j);
        f.position.set(x, y, z); f.rotation.y = Math.atan2(x1 - x0, z1 - z0) + Math.PI / 2; f.rotation.z = Math.PI / 2 + Math.PI / 6;
      }
    }
    // crowd silhouettes
    const crowdM = mat('crowdM', 0.17, 0.12, 0.09);
    const body = BABYLON.MeshBuilder.CreateCapsule('crowdB', { height: 0.62, radius: 0.16 }, scene);
    const head = BABYLON.MeshBuilder.CreateSphere('crowdH', { diameter: 0.2, segments: 8 }, scene); head.position.y = 0.42;
    const person = BABYLON.Mesh.MergeMeshes([body, head], true); person.material = crowdM; person.isVisible = false;
    for (let row = 0; row < 3; row++) {
      const n = 46 + row * 8, r = 3.0 + row * 0.55;
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2 + row * 0.07, c = person.createInstance('c' + row + '_' + i);
        c.position.set(Math.sin(a) * r, 0.31 + row * 0.28, Math.cos(a) * r);
        c.scaling.setAll(0.9 + ((i * 13 + row * 5) % 7) / 30);
      }
    }
    // stepped bleachers under the crowd
    for (let row = 0; row < 3; row++) {
      const step = BABYLON.MeshBuilder.CreateTorus('bleach' + row, { diameter: 2 * (3.0 + row * 0.55), thickness: 0.5, tessellation: 64 }, scene);
      step.scaling.y = 0.2 + row * 0.55; step.position.y = 0.0; step.material = mat('bleachM' + row, 0.24 - row * 0.03, 0.17 - row * 0.02, 0.11 - row * 0.015);
    }
  })();

  // blob shadows (jump readability)
  function blob() {
    const d = BABYLON.MeshBuilder.CreateDisc('blob', { radius: 0.17, tessellation: 24 }, scene);
    d.rotation.x = Math.PI / 2; d.position.y = 0.004;
    const m = new BABYLON.StandardMaterial('blobM', scene);
    m.diffuseColor = BABYLON.Color3.Black(); m.specularColor = BABYLON.Color3.Black(); m.alpha = 0.38; m.disableLighting = true;
    d.material = m; return d;
  }

  // particles
  function featherTex() {
    const t = new BABYLON.DynamicTexture('ft', { width: 64, height: 64 }, scene, false);
    const ctx = t.getContext(); ctx.clearRect(0, 0, 64, 64);
    const g = ctx.createRadialGradient(32, 32, 2, 32, 32, 30); g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(32, 32, 30, 12, 0.6, 0, Math.PI * 2); ctx.fill(); t.hasAlpha = true; t.update(); return t;
  }
  const FT = featherTex();
  function makePS(name, c1, c2, gravity) {
    const ps = new BABYLON.ParticleSystem(name, 300, scene);
    ps.particleTexture = FT; ps.emitter = new BABYLON.Vector3(0, 0.3, 0);
    ps.minEmitBox = new BABYLON.Vector3(-0.05, -0.05, -0.05); ps.maxEmitBox = new BABYLON.Vector3(0.05, 0.05, 0.05);
    ps.color1 = c1; ps.color2 = c2; ps.colorDead = new BABYLON.Color4(c2.r, c2.g, c2.b, 0);
    ps.minSize = 0.03; ps.maxSize = 0.07; ps.minLifeTime = 0.45; ps.maxLifeTime = 1.1;
    ps.emitRate = 0; ps.manualEmitCount = 0; ps.gravity = new BABYLON.Vector3(0, gravity, 0);
    ps.direction1 = new BABYLON.Vector3(-1, 0.4, -1); ps.direction2 = new BABYLON.Vector3(1, 1.4, 1);
    ps.minEmitPower = 0.5; ps.maxEmitPower = 1.6; ps.minAngularSpeed = -6; ps.maxAngularSpeed = 6;
    ps.blendMode = BABYLON.ParticleSystem.BLENDMODE_STANDARD; ps.updateSpeed = 1 / 60; ps.start();
    return ps;
  }
  const featherPS = {
    meron: makePS('fm', new BABYLON.Color4(0.75, 0.15, 0.08, 1), new BABYLON.Color4(0.95, 0.6, 0.15, 1), -1.4),
    wala: makePS('fw', new BABYLON.Color4(0.95, 0.95, 0.92, 1), new BABYLON.Color4(0.75, 0.75, 0.72, 1), -1.4),
  };
  const dustPS = makePS('dust', new BABYLON.Color4(0.7, 0.55, 0.38, 0.8), new BABYLON.Color4(0.55, 0.42, 0.3, 0.5), -0.2);
  dustPS.direction1 = new BABYLON.Vector3(-1, 0.05, -1); dustPS.direction2 = new BABYLON.Vector3(1, 0.25, 1); dustPS.minSize = 0.06; dustPS.maxSize = 0.14;
  function burst(ps, x, y, z, n) { ps.emitter.set(x, y, z); ps.manualEmitCount = (ps.manualEmitCount > 0 ? ps.manualEmitCount : 0) + n; }

  // ------------------------------------------------------------------ manok views
  const CLIP_LEN = { Idle: 61, Walk: 25, Tuka_Peck: 19, Sipa_Kick: 25, Lipad_Jump: 41, Hit_React: 16, Hingal_Exhausted: 17, Talikod_TurnAway: 30, KO: 40 };
  function pw(keys, t) {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const [t1, f1] = keys[i];
      if (t <= t1) { const [t0, f0] = keys[i - 1]; return f0 + (f1 - f0) * ((t - t0) / Math.max(1e-6, t1 - t0)); }
    }
    return keys[keys.length - 1][1];
  }
  const K_TUKA = [[0, 1], [6, 9], [9, 12], [19, 19]];
  const K_SIPA = [[0, 1], [12, 11], [16, 15], [34, 25]];
  const K_LIPAD = [[0, 1], [8, 8], [14, 14], [26, 20], [38, 26], [44, 33], [54, 41]];
  const K_BANAT_SEG = [[0, 4], [5, 9], [7, 11], [8, 12]];

  class ManokView {
    constructor(side, entries) {
      this.side = side;
      this.holder = new BABYLON.TransformNode(side + '_holder', scene);
      entries.rootNodes.forEach((n) => { n.parent = this.holder; });
      this.groups = {};
      for (const g of entries.animationGroups) {
        g.stop();
        const key = Object.keys(CLIP_LEN).find((k) => g.name === k || g.name.endsWith('_' + k) || g.name.endsWith(k));
        if (!key) continue;
        // in-place: the simulation owns position, so drop root-bone translation from every clip
        for (let i = g.targetedAnimations.length - 1; i >= 0; i--) {
          const ta = g.targetedAnimations[i], nm = (ta.target && ta.target.name) || '';
          if ((nm === 'root' || nm.endsWith('_root')) && ta.animation.targetProperty === 'position') g.targetedAnimations.splice(i, 1);
        }
        this.groups[key] = g;
      }
      this.cur = null; this.walkPhase = 0;
      this.hackles = [];
      for (const n of this.holder.getChildTransformNodes(false)) {
        if (/hackle_(C|L|R)$/.test(n.name)) this.hackles.push(n);
      }
      this.meshes = this.holder.getChildMeshes(false);
      this.meshes.forEach((m) => { shadows.addShadowCaster(m); m.isPickable = false; });
      this.blob = blob();
      this.tapang = 100;
    }
    pose(clip, bf) {
      const g = this.groups[clip]; if (!g) return;
      if (this.cur !== clip) {
        if (this.cur && this.groups[this.cur]) this.groups[this.cur].stop();
        g.start(false, 1, g.from, g.to); g.pause(); this.cur = clip;
      }
      const f = g.from + (bf - 1) * 2;
      g.goToFrame(Math.max(g.from, Math.min(g.to, f)));
    }
    tint(map) {
      for (const m of this.meshes) {
        const ms = m.material && m.material.subMaterials ? m.material.subMaterials : [m.material];
        for (const mt of ms) {
          if (!mt) continue;
          for (const key in map) if (mt.name.indexOf(key) >= 0 && mt.albedoColor) mt.albedoColor = map[key];
        }
      }
    }
  }

  function poseFor(view, m, s, timeSec) {
    const act = m.act, t = m.t;
    if (act === 'ko') return view.pose('KO', Math.min(40, 1 + t * (39 / 40)));
    if (act === 'talikod') return view.pose('Talikod_TurnAway', Math.min(30, 1 + t));
    if (act === 'hitstun') return view.pose('Hit_React', 1 + Math.min(15, (t / Math.max(1, m.stunLen)) * 15));
    if (act === 'tuka') return view.pose('Tuka_Peck', pw(K_TUKA, t));
    if (act === 'sipa') return view.pose('Sipa_Kick', pw(K_SIPA, t));
    if (act === 'lipad') return view.pose('Lipad_Jump', pw(K_LIPAD, t));
    if (act === 'banat') { const seg = Math.floor(t / 8); return view.pose('Tuka_Peck', seg < 3 ? pw(K_BANAT_SEG, t % 8) : 12 + (t - 24) * (7 / 8)); }
    if (act === 'ilag') return view.pose('Walk', 1 + ((t * 2.4) % 24));
    if (m.exh > 0) return view.pose('Hingal_Exhausted', 1 + ((timeSec * 30) % 16));
    if (act === 'walk') return view.pose('Walk', 1 + (view.walkPhase % 24));
    return view.pose('Idle', 1 + ((timeSec * 30) % 60));
  }

  // ------------------------------------------------------------------ input
  const held = new Set(); let pressed = {};
  const KEYMAP = { KeyJ: 'tuka', KeyK: 'sipa', Space: 'lipad', ShiftLeft: 'ilag', ShiftRight: 'ilag', KeyL: 'skill' };
  const MOVE = { KeyW: [0, 1], ArrowUp: [0, 1], KeyS: [0, -1], ArrowDown: [0, -1], KeyA: [-1, 0], ArrowLeft: [-1, 0], KeyD: [1, 0], ArrowRight: [1, 0] };
  window.addEventListener('keydown', (e) => {
    if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
    if (e.code === 'Escape' || e.code === 'KeyP') { if (!e.repeat) togglePause(); return; }
    if (e.repeat) return;
    held.add(e.code);
    if (KEYMAP[e.code]) pressed[KEYMAP[e.code]] = true;
  });
  window.addEventListener('keyup', (e) => held.delete(e.code));
  window.addEventListener('blur', () => held.clear());

  let padPrev = {};
  function sampleInput() {
    let fx = 0, fy = 0;
    for (const code of held) if (MOVE[code]) { fx += MOVE[code][0]; fy += MOVE[code][1]; }
    const inp = { mx: 0, mz: 0, tuka: !!pressed.tuka, sipa: !!pressed.sipa, lipad: !!pressed.lipad, ilag: !!pressed.ilag, skill: !!pressed.skill };
    pressed = {};
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    const pad = pads && Array.from(pads).find((p) => p);
    if (pad) {
      const ax = pad.axes[0] || 0, ay = pad.axes[1] || 0;
      if (Math.hypot(ax, ay) > 0.25) { fx += ax; fy -= ay; }
      const b = (i) => !!(pad.buttons[i] && pad.buttons[i].pressed);
      const edge = (i, name) => { const v = b(i); if (v && !padPrev[i]) inp[name] = true; padPrev[i] = v; };
      edge(0, 'tuka'); edge(2, 'sipa'); edge(1, 'lipad'); edge(5, 'ilag'); edge(3, 'skill');
      if (b(12)) fy += 1; if (b(13)) fy -= 1; if (b(14)) fx -= 1; if (b(15)) fx += 1;
      const st = b(9); if (st && !padPrev[9]) togglePause(); padPrev[9] = st;
    }
    if (fx || fy) {
      // camera-relative → world-space direction
      const fwd = cam.target.subtract(cam.position); fwd.y = 0; fwd.normalize();
      const right = new BABYLON.Vector3(fwd.z, 0, -fwd.x);
      let wx = fwd.x * fy + right.x * fx, wz = fwd.z * fy + right.z * fx;
      const L = Math.hypot(wx, wz) || 1; inp.mx = wx / L; inp.mz = wz / L;
    }
    return inp;
  }

  // ------------------------------------------------------------------ HUD
  const hudEls = {};
  for (const side of ['m', 'w']) for (const k of ['hp', 'hingal', 'tapang']) {
    const el = $(side + '-' + k); hudEls[side + k] = { el, fill: el.querySelector('.fill'), num: el.querySelector('.num') };
  }
  function setBar(key, v, cls) {
    const b = hudEls[key]; const val = Math.max(0, Math.round(v));
    b.fill.style.width = val + '%'; b.num.textContent = val;
    if (cls) for (const c in cls) b.el.classList.toggle(c, cls[c]);
  }
  let promptTimer = null;
  function prompt(big, sub, ms) {
    const p = $('prompt'); p.querySelector('.big').textContent = big || '';
    const s = p.querySelector('.sub'); s.textContent = sub || ''; s.classList.toggle('hidden', !sub);
    p.classList.remove('pop'); void p.offsetWidth; p.classList.add('pop');
    clearTimeout(promptTimer);
    if (ms) promptTimer = setTimeout(() => { p.querySelector('.big').textContent = ''; s.classList.add('hidden'); }, ms);
  }
  function updateHud(s) {
    const [M, W] = s.m;
    setBar('mhp', M.hp, { low: M.hp < 30 }); setBar('whp', W.hp, { low: W.hp < 30 });
    setBar('mhingal', M.hingal, { exh: M.exh > 0 }); setBar('whingal', W.hingal, { exh: W.exh > 0 });
    setBar('mtapang', M.tapang, { low: M.tapang < 30 }); setBar('wtapang', W.tapang, { low: W.tapang < 30 });
    $('timer').firstChild.nodeValue = String(Math.ceil(s.timer / 60));
    const cdPct = M.cd > 0 ? 100 - (M.cd / Sim.A.banat.cd) * 100 : 100;
    $('ring').style.setProperty('--p', cdPct + '%');
    $('skillTxt').textContent = M.cd > 0 ? Math.ceil(M.cd / 60) + ' s' : 'Ready';
    const sent = $('sent');
    if (s.sentensya) {
      const secs = Math.ceil(s.sentensya.left / 60);
      sent.style.display = 'block';
      sent.textContent = s.sentensya.side === 'meron' ? `SENTENSYA: land a hit in ${secs}…` : `SENTENSYA: Wala must land a hit (${secs})`;
      sent.style.background = s.sentensya.side === 'meron' ? 'var(--meron)' : 'var(--wala)';
    } else sent.style.display = 'none';
  }

  // ------------------------------------------------------------------ game state
  let views = null, state = null, bot = null, difficulty = 'normal';
  let started = false, paused = false, acc = 0, last = performance.now(), simTime = 0;
  let prev = null, shakeT = 0, reduceMotion = false, resultShown = false, ended = false;

  function snapshot(s) { return s.m.map((m) => ({ x: m.x, z: m.z, h: m.h, face: m.face })); }

  function newMatch() {
    const seed = (Math.random() * 2 ** 31) >>> 0;
    state = Sim.create(seed); bot = Bot.makeBot(difficulty, seed ^ 0x5bd1e995, 1);
    prev = snapshot(state); acc = 0; simTime = 0; resultShown = false; ended = false;
    $('botLabel').textContent = 'Bot · ' + difficulty[0].toUpperCase() + difficulty.slice(1);
    cam.target.set(0, 0.3, 0);
    updateHud(state);
  }

  function onEvents(ev) {
    for (const e of ev) {
      switch (e.type) {
        case 'prompt': if (e.text === 'ready') prompt('MERON vs WALA', null, 1100); else prompt('LABAN!', null, 900); break;
        case 'hit': {
          const target = state.m[e.target === 'meron' ? 0 : 1];
          burst(featherPS[e.target], target.x, 0.32 + target.h, target.z, e.kind === 'lipad' ? 40 : e.kind === 'sipa' ? 26 : 12);
          if (!reduceMotion) shakeT = e.kind === 'lipad' ? 14 : e.kind === 'sipa' ? 8 : 3;
          if (e.kind === 'lipad' && e.side === 'meron') prompt('', 'Lipad hit!', 600);
          break;
        }
        case 'anti_air': if (e.side === 'meron') prompt('', 'Anti-air!', 700); break;
        case 'land': burst(dustPS, e.x, 0.02, e.z, 18); break;
        case 'exhausted': if (e.side === 'meron') prompt('', 'Hingal! Out of breath', 900); break;
        case 'clash_started': prompt('CLASH!', 'Press K (Sipa) first! Too early loses', 0); break;
        case 'clash_resolved': prompt(e.winner ? (e.winner === 'meron' ? 'CLASH WON' : 'CLASH LOST') : 'TABLA', null, 900); break;
        case 'talikod': prompt('TALIKOD!', e.side === 'meron' ? 'Your manok turned away' : 'The bot turned away', 1100); break;
        case 'sentensya_started': prompt('SENTENSYA!', e.side === 'meron' ? 'Land any hit in 5 seconds or you lose' : 'The bot must land a hit in 5 seconds', 1600); break;
        case 'sentensya_ok': prompt('', e.side === 'meron' ? 'Sentensya answered!' : 'The bot answered the Sentensya', 900); break;
        case 'match_ended': {
          ended = true;
          const big = e.reason === 'ko' ? 'KO!' : e.reason === 'talikod' ? 'TALIKOD' : e.reason === 'timeout' ? 'TIME!' : 'FORFEIT';
          prompt(big, null, 0);
          setTimeout(showResult, e.reason === 'forfeit' ? 300 : 1800);
          break;
        }
      }
    }
  }

  function showResult() {
    if (resultShown) return; resultShown = true;
    const r = state.result, M = state.m[0];
    const win = r.winner === 'meron', draw = r.winner === 'draw';
    $('res-title').textContent = draw ? 'TABLA' : win ? 'PANALO' : 'TALO';
    $('res-title').style.color = draw ? '#6b5848' : win ? '#1f7a2e' : '#b3261e';
    const reason = { ko: 'by KO', talikod: 'by Talikod (Sentensya not answered)', timeout: 'on time (HP, then Tapang)', forfeit: 'by forfeit' }[r.reason];
    $('res-sub').textContent = `${draw ? 'Draw' : win ? 'You win' : 'You lose'} ${reason} · vs Bot (${difficulty}) · ${(r.ticks / 60).toFixed(1)} s`;
    const st = M.stats;
    $('res-stats').innerHTML = '';
    const items = [['Damage dealt', Math.round(st.dmg)], ['Hits: Tuka / Sipa / Lipad / Banat', `${st.tuka || 0} / ${st.sipa || 0} / ${st.lipad || 0} / ${st.skill || 0}`], ['Clashes won', st.clash], ['HP left', Math.round(M.hp)]];
    for (const [k, v] of items) { const d = document.createElement('div'); d.className = 'stat'; const s1 = document.createElement('small'); s1.textContent = k; const s2 = document.createElement('div'); s2.textContent = v; d.append(s1, s2); $('res-stats').appendChild(d); }
    $('result').classList.remove('hidden');
    $('rematch').focus();
  }

  function togglePause(force) {
    if (!started || resultShown) return;
    paused = force !== undefined ? force : !paused;
    $('pause').classList.toggle('hidden', !paused);
    if (paused) $('resume').focus(); else { last = performance.now(); canvas.focus(); }
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden && started && !ended) togglePause(true); });

  // ------------------------------------------------------------------ UI wiring
  document.querySelectorAll('.diff').forEach((b) => b.addEventListener('click', () => {
    difficulty = b.dataset.d; document.querySelectorAll('.diff').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
  }));
  $('go').addEventListener('click', () => { $('start').classList.add('hidden'); newMatch(); started = true; paused = false; canvas.focus(); });
  $('resume').addEventListener('click', () => togglePause(false));
  $('forfeit').addEventListener('click', () => { togglePause(false); onEvents(Sim.forfeit(state, 'meron')); });
  $('reduce').addEventListener('click', (e) => { reduceMotion = !reduceMotion; e.currentTarget.setAttribute('aria-pressed', String(reduceMotion)); e.currentTarget.textContent = 'Reduce motion: ' + (reduceMotion ? 'on' : 'off'); });
  $('rematch').addEventListener('click', () => { $('result').classList.add('hidden'); prompt('', null, 1); newMatch(); started = true; canvas.focus(); });
  $('change').addEventListener('click', () => { $('result').classList.add('hidden'); prompt('', null, 1); started = false; newMatch(); $('start').classList.remove('hidden'); });
  canvas.tabIndex = 0;

  // ------------------------------------------------------------------ camera
  let camAlpha = cam.alpha;
  function updateCamera(pos, dtFrames) {
    const [a, b] = pos;
    const mx = (a.x + b.x) / 2, mz = (a.z + b.z) / 2, sep = Math.hypot(b.x - a.x, b.z - a.z);
    const k = 1 - Math.pow(1 - 0.08, dtFrames);
    cam.target.x += (mx - cam.target.x) * k; cam.target.z += (mz - cam.target.z) * k;
    cam.target.y += (0.3 + Math.max(a.h, b.h) * 0.4 - cam.target.y) * k;
    const radius = Math.max(2.2, Math.min(3.5, 2.2 + 0.6 * sep));
    cam.radius += (radius - cam.radius) * k;
    // side-on view, slightly behind Meron (the player)
    let dx = b.x - a.x, dz = b.z - a.z; const L = Math.hypot(dx, dz) || 1; dx /= L; dz /= L;
    const cands = [[-dz, dx], [dz, -dx]].map(([px, pz]) => { const vx = px * 0.82 - dx * 0.57, vz = pz * 0.82 - dz * 0.57; return Math.atan2(vz, vx); });
    const diff = (t) => Math.abs(Sim.wrap(t - camAlpha));
    const want = diff(cands[0]) <= diff(cands[1]) ? cands[0] : cands[1];
    camAlpha += Sim.wrap(want - camAlpha) * (1 - Math.pow(1 - 0.03, dtFrames));
    cam.alpha = camAlpha; cam.beta = 0.98;
    if (shakeT > 0) { const m = shakeT / 14 * 0.025; cam.target.x += (Math.random() - 0.5) * m; cam.target.y += (Math.random() - 0.5) * m; shakeT -= dtFrames; }
  }

  // ------------------------------------------------------------------ render
  function lerpAngle(a, b, t) { return a + Sim.wrap(b - a) * t; }
  function render(alpha, dtFrames) {
    if (!views || !state) return;
    const pos = state.m.map((m, i) => {
      const p = prev[i];
      return { x: p.x + (m.x - p.x) * alpha, z: p.z + (m.z - p.z) * alpha, h: p.h + (m.h - p.h) * alpha, face: lerpAngle(p.face, m.face, alpha) };
    });
    state.m.forEach((m, i) => {
      const v = views[i], p = pos[i];
      v.holder.position.set(p.x, p.h, p.z); v.holder.rotation.y = p.face;
      poseFor(v, m, state, simTime);
      v.blob.position.x = p.x; v.blob.position.z = p.z;
      const sc = 1 - Math.min(0.5, p.h * 1.2); v.blob.scaling.set(sc, sc, sc); v.blob.material.alpha = 0.38 * sc;
      v.tapang += (m.tapang - v.tapang) * 0.2;
    });
    updateCamera(pos, dtFrames);
  }

  // hackle flare from Tapang (procedural, after animation)
  scene.onAfterAnimationsObservable.add(() => {
    if (!views) return;
    for (const v of views) {
      const flare = ((v.tapang - 50) / 50) * 0.35;
      for (const n of v.hackles) {
        if (!n.rotationQuaternion) continue;
        n.rotationQuaternion.multiplyInPlace(BABYLON.Quaternion.RotationAxis(BABYLON.Axis.X, -flare));
      }
    }
  });

  // ------------------------------------------------------------------ loop
  let hudAcc = 0, fpsAcc = 0;
  engine.runRenderLoop(() => {
    const now = performance.now();
    let dt = Math.min(now - last, 250); last = now;
    const dtFrames = dt / (1000 / 60);
    if (started && !paused && state) {
      acc += dt; let steps = 0;
      while (acc >= TICK_MS && steps < 5) {
        prev = snapshot(state);
        const pin = (state.phase === 'ended') ? { mx: 0, mz: 0 } : sampleInput();
        const bin = bot.think(state);
        const ev = Sim.step(state, [pin, bin]);
        if (state.phase !== 'ended') simTime += 1 / 60;
        const me = state.m;
        views.forEach((v, i) => { if (me[i].act === 'walk') v.walkPhase += (Math.hypot(me[i].vx, me[i].vz) / (1.2 / 60)) * 0.55; });
        onEvents(ev);
        acc -= TICK_MS; steps++;
      }
      if (steps === 5) acc = 0;
      hudAcc += dt; if (hudAcc > 50) { hudAcc = 0; updateHud(state); }
    } else if (state) { simTime += dt / 1000; }
    render(started && !paused ? Math.min(1, acc / TICK_MS) : 1, dtFrames);
    scene.render();
    fpsAcc += dt; if (fpsAcc > 500) { fpsAcc = 0; $('fps').textContent = Math.round(engine.getFps()) + ' fps'; }
  });
  window.addEventListener('resize', () => engine.resize());

  // ------------------------------------------------------------------ load model
  $('loading').classList.remove('hidden');
  BABYLON.SceneLoader.LoadAssetContainerAsync('', window.MANOK_GLB, scene, null, '.glb').then((container) => {
    const make = (side) => {
      const entries = container.instantiateModelsToScene((n) => side + '_' + n, true);
      return new ManokView(side, entries);
    };
    views = [make('meron'), make('wala')];
    // Wala: white / silver plumage (Meron keeps the red & gold Talisayin colors)
    views[1].tint({ Body_DeepRed: new BABYLON.Color3(0.86, 0.85, 0.82), Hackle_Gold: new BABYLON.Color3(0.96, 0.95, 0.9), WingTip_Green: new BABYLON.Color3(0.25, 0.27, 0.3) });
    newMatch();
    $('loading').classList.add('hidden');
    $('go').focus();
    window.__proto = { get state() { return state; }, views, scene, Sim };
  }).catch((e) => { $('loadTxt').textContent = 'Could not load the manok model: ' + e.message; });
})();
