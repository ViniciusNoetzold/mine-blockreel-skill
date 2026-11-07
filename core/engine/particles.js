// Deterministic particles. Every particle is generated once at load from a seeded PRNG and evaluated in closed form
// from time (gravity + linear drag + a floor), so renderAt(t) stays a pure function of t. Particles are cubes.
import { mulberry32, clamp01 } from './anim.js';

const hex = (h) => [(h >> 16 & 255) / 255, (h >> 8 & 255) / 255, (h & 255) / 255];
const ramp = (...hs) => hs.map(hex);

// Layer spec: n, life[a,b], delay[a,b], speed[a,b], dir ('sphere'|'up'|'ring'), cone (rad), g (gravity, negative rises),
// k (drag), s0[a,b] start size, s1[a,b] end size, colors (array of [r,g,b]) | 'block', ramp (colour over life), glow, spin, radius, floor
const FIRE = ramp(0xffffff, 0xffe27a, 0xff9a2e, 0xc2391a, 0x3a1208);
const SMOKE = ramp(0x6a6a6a, 0x4a4a4a, 0x2e2e2e);
const KINDS = {
  break: () => [{ n: 18, life: [0.7, 1.2], speed: [1.6, 3.4], dir: 'up', cone: 1.1, g: 14, k: 0.3, s0: [0.07, 0.16], s1: [0.05, 0.1], colors: 'block', spin: 8, radius: 0.35 }],
  explosion: () => [
    { n: 1, life: [0.28, 0.28], speed: [0, 0], dir: 'sphere', s0: [0.4, 0.4], s1: [3.2, 3.2], ramp: ramp(0xffffff, 0xffd27a, 0xff8a2a), glow: true, shrinkEnd: true },
    { n: 46, life: [0.35, 0.8], speed: [2.5, 7], dir: 'sphere', g: -1, k: 3.2, s0: [0.45, 0.8], s1: [0.1, 0.25], ramp: FIRE, glow: true, spin: 4, radius: 0.3 },
    { n: 34, life: [1.0, 1.7], speed: [4, 9], dir: 'up', cone: 1.2, g: 18, k: 0.2, s0: [0.1, 0.25], s1: [0.08, 0.18], colors: 'block', spin: 10, radius: 0.5 },
    { n: 44, delay: [0.1, 0.6], life: [1.4, 2.8], speed: [0.8, 2.2], dir: 'up', cone: 0.9, g: -1.1, k: 1.0, s0: [0.22, 0.4], s1: [0.6, 1.0], ramp: SMOKE, spin: 1.5, radius: 0.8 },
  ],
  smoke: () => [{ n: 1, rate: 16, life: [1.6, 2.8], speed: [0.7, 1.4], dir: 'up', cone: 0.45, g: -1.0, k: 0.7, s0: [0.16, 0.28], s1: [0.5, 0.85], ramp: SMOKE, spin: 1, radius: 0.25 }],
  fire: () => [{ n: 1, rate: 26, life: [0.45, 0.9], speed: [0.4, 1.2], dir: 'up', cone: 0.35, g: -1.5, k: 0.6, s0: [0.22, 0.38], s1: [0.04, 0.1], ramp: FIRE, glow: true, spin: 3, radius: 0.35 }],
  sparks: () => [{ n: 44, life: [0.5, 1.1], speed: [1.5, 4.2], dir: 'sphere', g: 9, k: 0.5, s0: [0.08, 0.14], s1: [0.02, 0.05], ramp: ramp(0xfff2a8, 0xffc233, 0xff7a1a), glow: true, radius: 0.1 }],
  dust: () => [{ n: 8, life: [0.45, 0.8], speed: [0.4, 1.1], dir: 'ring', g: -0.4, k: 2.4, s0: [0.1, 0.16], s1: [0.3, 0.5], ramp: ramp(0xcdbd9a, 0xa89a7c, 0x8a7e66), radius: 0.15 }],
  blood: () => [{ n: 14, life: [0.6, 1.1], speed: [1.5, 4], dir: 'up', cone: 1.2, g: 14, k: 0.3, s0: [0.05, 0.1], s1: [0.04, 0.08], colors: [hex(0xb01010), hex(0x7a0808), hex(0xd02020)], spin: 6, radius: 0.12 }],
  // combat and magic (the game's crit stars, death poof, portal swirl, sweep arc, torch flame, enchant glyph-dust)
  crit: () => [{ n: 22, life: [0.35, 0.7], speed: [2.5, 5.5], dir: 'sphere', g: 7, k: 1.4, s0: [0.07, 0.11], s1: [0.03, 0.05], ramp: ramp(0xffffff, 0xd8c8a8, 0x8a7a60), glow: true, radius: 0.25 }],
  magiccrit: () => [{ n: 24, life: [0.4, 0.8], speed: [2.5, 5], dir: 'sphere', g: 5, k: 1.4, s0: [0.07, 0.11], s1: [0.03, 0.05], ramp: ramp(0xe0fbff, 0x5ff0ff, 0x2a7aa8), glow: true, radius: 0.25 }],
  poof: () => [{ n: 20, life: [0.5, 0.9], speed: [0.4, 1.4], dir: 'sphere', g: -0.6, k: 2.2, s0: [0.18, 0.3], s1: [0.05, 0.12], ramp: ramp(0xffffff, 0xd8d8d8, 0x9a9a9a), radius: 0.45 }],
  portal: () => [{ n: 1, rate: 40, life: [0.5, 1.1], speed: [0.6, 1.6], dir: 'sphere', g: -0.8, k: 1.8, s0: [0.06, 0.1], s1: [0.02, 0.04], ramp: ramp(0xf0b8ff, 0xb040ff, 0x40107a), glow: true, radius: 0.7 }],
  sweep: () => [{ n: 26, life: [0.18, 0.28], speed: [1.5, 2.5], dir: 'arc', arc: 2.4, g: 0, k: 3, s0: [0.16, 0.22], s1: [0.04, 0.08], ramp: ramp(0xffffff, 0xe8e8f0, 0xa8a8b8), glow: true, radius: 1.3 }],
  flame: () => [{ n: 1, rate: 8, life: [0.3, 0.6], speed: [0.1, 0.35], dir: 'up', cone: 0.2, g: -0.6, k: 1.0, s0: [0.05, 0.08], s1: [0.01, 0.03], ramp: ramp(0xffffff, 0xffd24a, 0xff7a1a), glow: true, radius: 0.04 },
                 { n: 1, rate: 3, life: [0.8, 1.4], speed: [0.2, 0.5], dir: 'up', cone: 0.3, g: -0.6, k: 0.8, s0: [0.05, 0.07], s1: [0.08, 0.12], ramp: SMOKE, radius: 0.05 }],
  enchant: () => [{ n: 1, rate: 30, life: [0.8, 1.4], speed: [0.3, 0.8], dir: 'sphere', g: -0.4, k: 0.8, s0: [0.05, 0.08], s1: [0.02, 0.04], ramp: ramp(0xffffff, 0xc8b0ff, 0x6a50d0), glow: true, radius: 0.9 }],
  aura: () => [{ n: 1, rate: 24, life: [0.7, 1.3], speed: [0.2, 0.6], dir: 'up', cone: 0.6, g: -0.9, k: 1.0, s0: [0.07, 0.11], s1: [0.02, 0.04], ramp: ramp(0xffffff, 0xd8e8ff, 0x8090c0), glow: true, radius: 0.5 }],
  confetti: () => [{ n: 50, life: [1.2, 2.2], speed: [2, 6], dir: 'up', cone: 0.9, g: 6, k: 1.2, s0: [0.07, 0.11], s1: [0.07, 0.11], colors: [hex(0xff4d4d), hex(0x4dd2ff), hex(0xffd84a), hex(0x7dff6a), hex(0xd36aff)], spin: 9, radius: 0.2 }],
};

function pick(rng, [a, b]) { return a + (b - a) * rng(); }
function sphereDir(rng) { const z = rng() * 2 - 1, a = rng() * Math.PI * 2, r = Math.sqrt(1 - z * z); return [r * Math.cos(a), z, r * Math.sin(a)]; }
function coneDir(rng, cone) { const c = Math.cos(cone), z = c + (1 - c) * rng(), a = rng() * Math.PI * 2, r = Math.sqrt(1 - z * z); return [r * Math.cos(a), z, r * Math.sin(a)]; }
function ringDir(rng) { const a = rng() * Math.PI * 2; return [Math.cos(a), 0.12 + rng() * 0.2, Math.sin(a)]; }

export async function buildParticles(THREE, scene, story, ctx) {
  const entries = [...(story.fx || [])];
  // auto footstep dust for actors with "dust": true
  for (const [name, cfg] of Object.entries(story.actors || {})) {
    if (!cfg.dust) continue;
    for (const s of story.timeline || []) {
      if (s.actor !== name || (s.do !== 'walk' && s.do !== 'run')) continue;
      const period = (s.do === 'run' ? Math.PI / 12 : Math.PI / 8) / (s.speed || 1);
      for (let tt = s.t + period * 0.5; tt < s.t + (s.dur ?? 0); tt += period) entries.push({ t: tt, kind: 'dust', pos: { actor: name, at: tt }, scale: 0.6, seed: Math.round(tt * 100) });
    }
  }
  // the game's death poof: an actor whose "die" segment has "vanish": true disappears in white smoke when the fall ends
  for (const s of story.timeline || []) if (s.do === 'die' && s.vanish) entries.push({ t: s.t + (s.dur ?? 1), kind: 'poof', pos: { actor: s.actor, at: s.t + (s.dur ?? 1), offset: [0, 0.5, 0] }, scale: 1.3, seed: 7 });
  const seed0 = story.seed ?? 1; const lit = []; const glow = [];
  let idx = 0;
  for (const e of entries) {
    idx++;
    const layersFn = KINDS[e.kind]; if (!layersFn) { console.warn('unknown fx kind:', e.kind); continue; }
    const rng = mulberry32(seed0 * 7919 + idx * 104729 + (e.seed ?? 0) * 31);
    const sc = e.scale ?? 1;
    let p = e.pos;
    if (typeof p === 'string') p = { actor: p };
    if (p && p.actor) { const base = ctx.posOf(p.actor, p.at ?? e.t); const o = p.offset || [0, 0, 0]; p = [base[0] + o[0], base[1] + o[1], base[2] + o[2]]; }
    p = p || [0, 1, 0];
    const floor = e.floor ?? ctx.groundAt(p[0], p[1], p[2]) ?? -Infinity;
    const palette = e.kind === 'dust' && !e.block ? null : (e.block ? await ctx.palette(e.block) : await ctx.palette(ctx.blockUnder(p) || 'stone'));
    const dur = e.dur ?? 0;
    for (const L of layersFn()) {
      let n = Math.max(1, Math.round(L.n * (e.density ?? 1) * Math.max(1, sc ** 1.3)));
      if (L.rate) n = Math.max(1, Math.round(L.rate * (dur || 1) * (e.density ?? 1)));
      for (let i = 0; i < n; i++) {
        const life = pick(rng, L.life);
        const birth = e.t + (L.rate ? rng() * dur : 0) + (L.delay ? pick(rng, L.delay) : 0);
        let d = L.dir === 'up' ? coneDir(rng, L.cone ?? 0.8) : L.dir === 'ring' ? ringDir(rng) : sphereDir(rng);
        let arcOff = null;
        if (L.dir === 'arc') { // sweep: particles along a horizontal arc in front of `face` (degrees), moving outward
          const h = ((e.face ?? 0) * Math.PI) / 180 + (rng() - 0.5) * (L.arc ?? 2.2); const r = (L.radius ?? 1) * sc;
          arcOff = [Math.sin(h) * r, (rng() - 0.5) * 0.15, Math.cos(h) * r]; d = [Math.sin(h), 0, Math.cos(h)];
        }
        const sp = pick(rng, L.speed) * sc;
        const rad = (L.radius ?? 0) * sc;
        const jit = sphereDir(rng);
        let col = null; let rmp = null;
        if (L.ramp) rmp = L.ramp.map((c) => new THREE.Color(c[0], c[1], c[2]));
        else if (L.colors === 'block') { const c = (palette || [[0.5, 0.5, 0.5]])[Math.floor(rng() * (palette || [1]).length)]; col = new THREE.Color(c[0], c[1], c[2]); }
        else if (L.colors) { const c = L.colors[Math.floor(rng() * L.colors.length)]; col = new THREE.Color(c[0], c[1], c[2]); }
        else col = new THREE.Color(1, 1, 1);
        const ax = sphereDir(rng);
        (L.glow ? glow : lit).push({
          b: birth, life,
          x: p[0] + (arcOff ? arcOff[0] : jit[0] * rad * rng()), y: p[1] + (arcOff ? arcOff[1] : Math.abs(jit[1]) * rad * 0.5), z: p[2] + (arcOff ? arcOff[2] : jit[2] * rad * rng()),
          vx: d[0] * sp, vy: d[1] * sp, vz: d[2] * sp, g: L.g ?? 0, k: Math.max(L.k ?? 0, 0), floor,
          s0: pick(rng, L.s0) * sc, s1: pick(rng, L.s1) * sc, col, rmp, spin: (L.spin ?? 0) * (rng() * 2 - 1), ax, rest: !!(L.g > 0), shrinkEnd: !!L.shrinkEnd,
        });
      }
    }
  }
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const mk = (list, material) => {
    if (!list.length) return null;
    const m = new THREE.InstancedMesh(geo, material, list.length);
    m.instanceMatrix.setUsage(THREE.DynamicDrawUsage); m.frustumCulled = false; m.castShadow = false; m.receiveShadow = false;
    const white = new THREE.Color(1, 1, 1); for (let i = 0; i < list.length; i++) m.setColorAt(i, white);
    scene.add(m); return m;
  };
  const litMesh = mk(lit, new THREE.MeshLambertMaterial({ color: 0xffffff }));
  const glowMesh = mk(glow, new THREE.MeshBasicMaterial({ color: 0xffffff }));
  const dummy = new THREE.Object3D(); const tmp = new THREE.Color();

  const evalList = (list, mesh, t) => {
    if (!mesh) return;
    for (let i = 0; i < list.length; i++) {
      const p = list[i]; const a = t - p.b;
      if (a < 0 || a > p.life) { dummy.scale.setScalar(0); dummy.position.set(0, -999, 0); dummy.updateMatrix(); mesh.setMatrixAt(i, dummy.matrix); continue; }
      const k = p.k; let F, y;
      if (k < 1e-3) { F = a; y = p.y + p.vy * a - 0.5 * p.g * a * a; }
      else { const e = 1 - Math.exp(-k * a); F = e / k; y = p.y + (p.vy + p.g / k) * F - (p.g * a) / k; }
      const x = p.x + p.vx * F, z = p.z + p.vz * F;
      const u = a / p.life; let s = p.s0 + (p.s1 - p.s0) * u; if (p.shrinkEnd) s *= 1 - u * u * u;
      else s *= u > 0.85 ? Math.max(0, (1 - u) / 0.15) : 1;
      if (p.rest && p.floor > -1e8 && y < p.floor + s * 0.5) y = p.floor + s * 0.5;
      dummy.position.set(x, y, z); dummy.scale.setScalar(Math.max(s, 0));
      dummy.quaternion.setFromAxisAngle(new THREE.Vector3(p.ax[0], p.ax[1], p.ax[2]).normalize(), p.spin * a);
      dummy.updateMatrix(); mesh.setMatrixAt(i, dummy.matrix);
      if (p.rmp) {
        const f = clamp01(u) * (p.rmp.length - 1); const i0 = Math.floor(f), i1 = Math.min(p.rmp.length - 1, i0 + 1);
        tmp.copy(p.rmp[i0]).lerp(p.rmp[i1], f - i0); mesh.setColorAt(i, tmp);
      } else mesh.setColorAt(i, p.col);
    }
    mesh.instanceMatrix.needsUpdate = true; if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  };
  return { count: lit.length + glow.length, update(t) { evalList(lit, litMesh, t); evalList(glow, glowMesh, t); } };
}
