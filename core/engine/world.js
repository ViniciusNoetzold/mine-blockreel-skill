// Dynamic world: block events (break with cracks, place, explode, tnt with fuse), props (door, chest) and flowing textures.
// Everything is a pure function of time, so renders stay deterministic.
//
// story.changes: [
//   { "t": 3, "break": [x,y,z], "crack": 0.6 }                       // cracks for 0.6 s, then the block pops (debris auto)
//   { "t": 4, "place": [x,y,z], "block": "planks" }                  // block appears with a small pop
//   { "t": 5, "explode": [x,y,z], "radius": 3 }                      // removes nearby blocks, fireball + debris + smoke
//   { "t": 6, "tnt": [x,y,z], "fuse": 1.5, "radius": 3, "also": [[x,y,z]] }  // the TNT block(s) flash, swell, then explode
// ]
// story.props: { "door1": { "type": "door", "pos": [x,y,z], "axis": "x", "hinge": "min", "swing": 1, "block": "planks",
//                           "events": [ { "t": 2, "do": "open" }, { "t": 5, "do": "close" } ] },
//                "chest1": { "type": "chest", "pos": [x,y,z], "face": 180, "events": [ { "t": 3, "do": "open" } ] } }
import { mulberry32, ease, clamp01 } from './anim.js';

const KEEP = new Set(['obsidian', 'water', 'lava']); // blast-resistant by default (story.blastResistant overrides)

export function parseChanges(story, grid) {
  // Each changed block becomes its own instance { pos, block, vis0, evs } so a different block can be placed where another was.
  const insts = []; const dynKeys = new Set(); const fx = []; const cracks = []; const cur = new Map(); const gone = new Set(); // cur: key -> instance occupying it
  const key = (p) => `${p[0]},${p[1]},${p[2]}`;
  const keep = new Set(story.blastResistant || [...KEEP]);
  const rng = mulberry32((story.seed ?? 1) * 977 + 13);
  const ctr = (p) => [p[0] + 0.5, p[1] + 0.5, p[2] + 0.5];
  const occupy = (k) => { // the instance currently at k (creating one from the static grid on first use)
    if (cur.has(k)) return cur.get(k);
    if (!grid.has(k) || gone.has(k)) return null; // never resurrect a block that was already removed
    const pos = k.split(',').map(Number); const it = { pos, block: grid.get(k), vis0: true, evs: [] };
    insts.push(it); dynKeys.add(k); cur.set(k, it); return it;
  };
  const sorted = (story.changes || []).slice().sort((a, b) => a.t - b.t);
  const present = new Map(grid); // what stands where, as the sequence of changes unfolds (for debris colours)
  for (const c of sorted) {
    if (c.break) {
      const k = key(c.break), it = occupy(k); const crack = c.crack ?? 0;
      if (!it) continue;
      it.evs.push({ type: 'break', t: c.t }); cur.delete(k); gone.add(k);
      if (crack > 0) cracks.push({ pos: c.break, t0: c.t - crack, t1: c.t });
      fx.push({ t: c.t, kind: 'break', pos: ctr(c.break), block: present.get(k) || 'stone', seed: Math.round(c.t * 10) });
      present.delete(k);
    } else if (c.place) {
      const k = key(c.place); const blk = c.block || 'stone';
      const it = { pos: [...c.place], block: blk, vis0: false, evs: [{ type: 'place', t: c.t }] };
      insts.push(it); cur.set(k, it); present.set(k, blk); gone.delete(k);
    } else if (c.explode || c.tnt) {
      const o = c.explode || c.tnt; const r = c.radius ?? 3; const te = c.tnt ? c.t + (c.fuse ?? 1.5) : c.t; const sp = c.speed ?? 0.035;
      const ok = key(o); const center = ctr(o); let removed = 0;
      if (c.tnt) for (const q of [c.tnt, ...(c.also || [])]) { const it = occupy(key(q)); if (it) it.evs.push({ type: 'tnt', t: c.t, fuse: c.fuse ?? 1.5 }); } // `also`: more TNT blocks that flash together
      for (const [k, b] of [...present]) {
        const [x, y, z] = k.split(',').map(Number); const d = Math.hypot(x + 0.5 - center[0], y + 0.5 - center[1], z + 0.5 - center[2]);
        const isTnt = c.tnt && (k === ok || (c.also || []).some((q) => key(q) === k));
        if (!isTnt && (d > r * (0.8 + 0.35 * rng()) || keep.has(b))) continue;
        if (!isTnt) { const it = occupy(k); if (!it) continue; it.evs.push({ type: 'explode', t: te, delay: d * sp }); cur.delete(k); gone.add(k); }
        else { cur.delete(k); gone.add(k); }
        present.delete(k); removed++;
        if (removed <= 36 && rng() < 0.55) fx.push({ t: te + d * sp, kind: 'break', pos: [x + 0.5, y + 0.5, z + 0.5], block: b, density: 0.4, seed: removed });
      }
      const below = present.get(key([Math.floor(center[0]), Math.floor(center[1]) - 1, Math.floor(center[2])]));
      fx.push({ t: te, kind: 'explosion', pos: center, scale: Math.max(0.8, r / 2.3), block: below || 'stone', seed: Math.round(te * 10) });
      if (c.smoke !== false) fx.push({ t: te + 0.3, kind: 'smoke', pos: [center[0], center[1] - 0.3, center[2]], dur: c.smoke ?? 3, scale: Math.max(1, r / 3) });
    }
  }
  for (const it of insts) it.evs.sort((a, b) => a.t - b.t);
  return { insts, dynKeys, fx, cracks };
}

// state of one block instance at time t: { vis, scale, flash }
export function blockState(evs, vis0, t) {
  let vis = vis0, scale = 1, flash = 0;
  for (const ev of evs) {
    if (t < ev.t) break;
    if (ev.type === 'place') { vis = true; const a = t - ev.t; scale = a < 0.3 ? 0.5 + 0.5 * ease.outBack(a / 0.3) : 1; }
    else if (ev.type === 'break') { vis = false; scale = 1; }
    else if (ev.type === 'explode') { if (t >= ev.t + ev.delay) { vis = false; scale = 1; } }
    else if (ev.type === 'tnt') {
      const a = t - ev.t;
      if (a >= ev.fuse) { vis = false; scale = 1; }
      else { flash = Math.floor(a * (4 + a * 3)) % 2 === 0 ? 1 : 0; scale = 1 + 0.14 * Math.pow(a / ev.fuse, 2) * 1.5 + 0.02 * Math.sin(a * 40); }
    }
  }
  return { vis, scale, flash };
}

// ---------------------------------------------------------------- cracks ----
export function crackTextures(THREE) {
  const out = []; const rng = mulberry32(4242); const pts = [];
  let x = 8, y = 8; const marks = [];
  for (let i = 0; i < 70; i++) { // a random walk that grows outward, shared by all stages so cracks extend rather than change
    const a = rng() * Math.PI * 2; x = Math.max(0, Math.min(15, x + Math.round(Math.cos(a) * 1.6))); y = Math.max(0, Math.min(15, y + Math.round(Math.sin(a) * 1.6)));
    marks.push([x, y]); if (i % 9 === 8) { x = 8 + Math.round((rng() - 0.5) * 6); y = 8 + Math.round((rng() - 0.5) * 6); }
  }
  for (let s = 0; s < 10; s++) {
    const c = document.createElement('canvas'); c.width = c.height = 16; const g = c.getContext('2d');
    g.fillStyle = 'rgba(20,14,10,.78)'; const n = Math.round(((s + 1) / 10) * marks.length);
    for (let i = 0; i < n; i++) g.fillRect(marks[i][0], marks[i][1], 1, 1);
    const t = new THREE.CanvasTexture(c); t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; out.push(t);
  }
  return out;
}

// ----------------------------------------------------------------- props ----
export async function buildProps(THREE, scene, props, getMaterials) {
  const items = [];
  for (const [name, p] of Object.entries(props || {})) {
    const evs = (p.events || []).slice().sort((a, b) => a.t - b.t);
    const angleAt = (t, open, dur) => { // eased, overshooting open/close driven by events
      let from = 0;
      for (const ev of evs) {
        if (t < ev.t) return from;
        const to = ev.do === 'open' ? open : 0; const u = clamp01((t - ev.t) / (ev.dur ?? dur));
        if (u < 1) return from + (to - from) * ease.outBack(u);
        from = to;
      }
      return from;
    };
    if (p.type === 'door') {
      const mats = await getMaterials(p.block || 'planks'); const axis = p.axis || 'x'; const [x, y, z] = p.pos; const th = 3 / 16;
      const geo = new THREE.BoxGeometry(axis === 'x' ? 1 : th, 2, axis === 'x' ? th : 1);
      const mesh = new THREE.Mesh(geo, mats); mesh.castShadow = true;
      const g = new THREE.Group(); const hingeMax = p.hinge === 'max'; const sgn = hingeMax ? -1 : 1;
      mesh.position.set(axis === 'x' ? sgn * 0.5 : 0, 1, axis === 'x' ? 0 : sgn * 0.5); g.add(mesh);
      g.position.set(axis === 'x' ? x + (hingeMax ? 1 : 0) : x + th / 2, y, axis === 'x' ? z + th / 2 : z + (hingeMax ? 1 : 0));
      scene.add(g);
      const sw = p.swing ?? 1;
      items.push({ update: (t) => { g.rotation.y = sw * angleAt(t, Math.PI / 2, 0.38) * (axis === 'x' ? 1 : -1); } });
    } else if (p.type === 'chest') {
      const mats = await getMaterials(p.block || 'chest'); const [x, y, z] = p.pos; const PX = 1 / 16;
      const root = new THREE.Group(); root.position.set(x + 0.5, y, z + 0.5); root.rotation.y = (p.face ?? 0) * Math.PI / 180;
      const body = new THREE.Mesh(new THREE.BoxGeometry(14 * PX, 10 * PX, 14 * PX), mats); body.position.y = 5 * PX; body.castShadow = true; root.add(body);
      const hinge = new THREE.Group(); hinge.position.set(0, 10 * PX, -7 * PX); root.add(hinge);
      const lid = new THREE.Mesh(new THREE.BoxGeometry(14 * PX, 5 * PX, 14 * PX), mats); lid.position.set(0, 2.5 * PX, 7 * PX); lid.castShadow = true; hinge.add(lid);
      const latch = new THREE.Mesh(new THREE.BoxGeometry(2 * PX, 4 * PX, 1 * PX), new THREE.MeshLambertMaterial({ color: 0xc8c8d0 })); latch.position.set(0, -0.5 * PX, 14.3 * PX); hinge.add(latch);
      scene.add(root);
      // as in the game: the lid swings to 90 degrees in about 0.5 s (10 ticks) with a cubic ease-out, no bounce
      const lidAt = (t) => { let from = 0; for (const ev of evs) { if (t < ev.t) return from; const to = ev.do === 'open' ? Math.PI / 2 : 0; const u = clamp01((t - ev.t) / (ev.dur ?? 0.5)); if (u < 1) return from + (to - from) * (1 - (1 - u) ** 3); from = to; } return from; };
      items.push({ update: (t) => { hinge.rotation.x = -lidAt(t); } });
    }
  }
  return { update: (t) => items.forEach((i) => i.update(t)) };
}
