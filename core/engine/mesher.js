// World mesher: turns the block grid into a few static meshes the way the game itself draws chunks.
//  - hidden faces between solid blocks are never emitted (no z-fighting, no see-through water, far fewer triangles)
//  - per-face shading like the game (top 1.0, north/south 0.8, east/west 0.6, bottom 0.5)
//  - smooth lighting: per-vertex ambient occlusion (3-neighbour rule, quads flipped along the brighter diagonal)
//  - light propagation: sky light (15 from above, -1 per step sideways) and block light from emitters (torches 14, glowstone 15)
//  - shapes: cube, cross (plants), torch, slab, stairs, fence, wall, layer (snow / carpet), liquid (lowered 14/16 top)
// Everything depends only on the grid, so the result is deterministic. Pure geometry here; materials come from the engine.

// face table: normal n, right R, up U (as seen from outside), the game's directional shade, and which texture slot it uses
export const FACES = [
  { n: [1, 0, 0], R: [0, 0, -1], U: [0, 1, 0], shade: 0.6, slot: 'side', name: 'east' },
  { n: [-1, 0, 0], R: [0, 0, 1], U: [0, 1, 0], shade: 0.6, slot: 'side', name: 'west' },
  { n: [0, 1, 0], R: [1, 0, 0], U: [0, 0, -1], shade: 1.0, slot: 'top', name: 'up' },
  { n: [0, -1, 0], R: [1, 0, 0], U: [0, 0, 1], shade: 0.5, slot: 'bottom', name: 'down' },
  { n: [0, 0, 1], R: [1, 0, 0], U: [0, 1, 0], shade: 0.8, slot: 'front', name: 'south' },
  { n: [0, 0, -1], R: [-1, 0, 0], U: [0, 1, 0], shade: 0.8, slot: 'side', name: 'north' },
];
const AO_CURVE = [0.42, 0.62, 0.8, 1.0];

// "oak_stairs:east" -> { base: "oak_stairs", prop: "east" }
export function parseBlock(name) { const i = name.indexOf(':'); return i < 0 ? { base: name, prop: null } : { base: name.slice(0, i), prop: name.slice(i + 1) }; }

// Normalised definition: { shape, kind: opaque|cutout|translucent|emissive, tex: {top,side,bottom,front}, light, liquid, flow, ... }
export function resolveDef(defs, name) {
  const { base, prop } = parseBlock(name);
  let d = defs[base] ?? base; if (typeof d === 'string') d = { all: d };
  const all = d.all ?? base;
  const tex = { top: d.top ?? all, side: d.side ?? all, bottom: d.bottom ?? d.top ?? all, front: d.front ?? d.side ?? all };
  const shape = d.shape || (d.liquid || base === 'water' || base === 'lava' ? 'liquid' : 'cube');
  const translucent = !!(d.translucent || (shape === 'liquid' && !d.emissive) || /(^|_)(ice|stained)/.test(base));
  const kind = d.emissive ? 'emissive' : translucent ? 'translucent' : (d.transparent || shape !== 'cube') ? 'cutout' : 'opaque';
  return { name, base, prop, tex, shape, kind, light: d.light ?? 0, flow: d.flow, height: d.height, emissive: !!d.emissive,
    leaves: d.fancy ?? /leaves/.test(base), glassy: /glass|ice/.test(base), def: d };
}

const hash3 = (x, y, z) => { let h = (x * 374761393 + y * 668265263 + z * 2147483647) | 0; h = (h ^ (h >>> 13)) * 1274126177; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };

// --------------------------------------------------------------------------------------------- volume ----
// The grid as a dense typed volume over its bounding box (+1 margin): neighbour lookups by index arithmetic instead of
// string keys. This is what lets a world of a million and more blocks mesh in a few seconds.
export function buildVolume(grid, dynKeys = new Set()) {
  let x0 = Infinity, y0 = Infinity, z0 = Infinity, x1 = -Infinity, y1 = -Infinity, z1 = -Infinity;
  const xs = new Int32Array(grid.size), ys = new Int32Array(grid.size), zs = new Int32Array(grid.size), names = []; let n = 0;
  const nameId = new Map(); const ids = new Int32Array(grid.size); const dyn = new Uint8Array(grid.size);
  for (const [k, b] of grid) {
    const c1 = k.indexOf(','), c2 = k.indexOf(',', c1 + 1);
    const x = +k.slice(0, c1), y = +k.slice(c1 + 1, c2), z = +k.slice(c2 + 1);
    xs[n] = x; ys[n] = y; zs[n] = z;
    let id = nameId.get(b); if (id === undefined) { names.push(b); id = names.length; nameId.set(b, id); }
    ids[n] = id; dyn[n] = dynKeys.has(k) ? 1 : 0; n++;
    if (x < x0) x0 = x; if (y < y0) y0 = y; if (z < z0) z0 = z; if (x > x1) x1 = x; if (y > y1) y1 = y; if (z > z1) z1 = z;
  }
  if (!n) return null;
  x0 -= 1; y0 -= 1; z0 -= 1; x1 += 1; y1 += 2; z1 += 1;
  const NX = x1 - x0 + 1, NY = y1 - y0 + 1, NZ = z1 - z0 + 1;
  const vol = new Int32Array(NX * NY * NZ); // block id (index into names, 1-based); negative = changes over time (not occluding)
  for (let i = 0; i < n; i++) vol[((ys[i] - y0) * NZ + (zs[i] - z0)) * NX + (xs[i] - x0)] = dyn[i] ? -ids[i] : ids[i];
  return { x0, y0, z0, x1, y1, z1, NX, NY, NZ, vol, names,
    idx: (x, y, z) => ((y - y0) * NZ + (z - z0)) * NX + (x - x0),
    inside: (x, y, z) => x >= x0 && x <= x1 && y >= y0 && y <= y1 && z >= z0 && z <= z1 };
}

// ---------------------------------------------------------------------------------------------- light ----
// Light over the volume: sky light (15 straight down, -1 per step sideways, -2 through leaves and water) and block light
// spread from emitters (torches 14, glowstone 15). sky/block are 0..15 per cell.
export function computeLight(grid, defOf, dynKeys = new Set(), V = null) {
  V = V || buildVolume(grid, dynKeys);
  if (!V) return { at: () => [15, 0], pk: () => 240, sample: () => [15, 0], opaqueAt: () => false, V: null };
  const { x0, y0, z0, x1, y1, z1, NX, NY, NZ, vol, names } = V; const N = vol.length;
  const cls = [0], lightOf = [0];
  for (const nm of names) { const d = defOf(nm); cls.push(d.kind === 'opaque' && d.shape === 'cube' ? 1 : (d.leaves || d.shape === 'liquid') ? 2 : 3); lightOf.push(d.light || 0); }
  const block = new Uint8Array(N); const emitI = []; const emitL = [];
  for (let i = 0; i < N; i++) { const id = vol[i]; if (!id) continue; const a = Math.abs(id); block[i] = id < 0 ? 3 : cls[a]; if (lightOf[a] > 0) { emitI.push(i); emitL.push(lightOf[a]); } }
  const sky = new Uint8Array(N), blk = new Uint8Array(N);
  const q = new Int32Array(N * 2); const SL = NX * NZ;
  const spread = (L, seedCount) => {
    let head = 0, tail = seedCount;
    while (head < tail) {
      const i = q[head++]; const lv = L[i]; if (lv <= 1) continue;
      const x = i % NX, z = ((i / NX) | 0) % NZ, y = (i / SL) | 0;
      for (let d = 0; d < 6; d++) {
        let j;
        if (d === 0) { if (x === NX - 1) continue; j = i + 1; } else if (d === 1) { if (x === 0) continue; j = i - 1; }
        else if (d === 2) { if (y === NY - 1) continue; j = i + SL; } else if (d === 3) { if (y === 0) continue; j = i - SL; }
        else if (d === 4) { if (z === NZ - 1) continue; j = i + NX; } else { if (z === 0) continue; j = i - NX; }
        const bj = block[j]; if (bj === 1) continue;
        const nl = lv - (bj === 2 ? 2 : 1);
        if (nl > L[j]) { L[j] = nl; if (tail < q.length) q[tail++] = j; }
      }
    }
  };
  let sc = 0;
  for (let x = 0; x < NX; x++) for (let z = 0; z < NZ; z++) {
    let lv = 15;
    for (let y = NY - 1; y >= 0; y--) {
      const i = (y * NZ + z) * NX + x; const b = block[i];
      if (b === 1) break; if (b === 2) lv = Math.max(0, lv - 2);
      sky[i] = lv;
      if (lv > 1) q[sc++] = i;
    }
  }
  spread(sky, sc);
  let bc = 0; for (let k = 0; k < emitI.length; k++) { const i = emitI[k]; if (emitL[k] > blk[i]) blk[i] = emitL[k]; q[bc++] = i; }
  spread(blk, bc);
  const pk = (x, y, z) => { // packed sky*16 + block, without allocating
    if (x < x0 || x > x1 || y < y0 || z < z0 || z > z1 || y > y1) return 240;
    const i = ((y - y0) * NZ + (z - z0)) * NX + (x - x0); return sky[i] * 16 + blk[i];
  };
  const at = (x, y, z) => { const v = pk(x, y, z); return [v >> 4, v & 15]; };
  // light in a cell for something standing in it (an actor): max of the cell and the one above, so feet in a slab still read lit
  const sample = (x, y, z) => { const a = at(Math.floor(x), Math.floor(y), Math.floor(z)), b = at(Math.floor(x), Math.floor(y) + 1, Math.floor(z)); return [Math.max(a[0], b[0]), Math.max(a[1], b[1])]; };
  const opaqueAt = (x, y, z) => { if (x < x0 || x > x1 || y < y0 || y > y1 || z < z0 || z > z1) return false; return block[((y - y0) * NZ + (z - z0)) * NX + (x - x0)] === 1; };
  return { at, pk, sample, opaqueAt, V };
}

// ------------------------------------------------------------------------------------------------ mesh ----
// A geometry builder per chunk and material; the engine turns each into a THREE.BufferGeometry + material.
class Builder {
  constructor() { this.pos = []; this.nor = []; this.uv = []; this.col = []; this.lit = []; this.idx = []; this.n = 0; }
  quad(ps, nrm, uvs, cols, lits, flip) {
    const P = this.pos, Nn = this.nor, Uv = this.uv, C = this.col, L = this.lit;
    for (let i = 0; i < 4; i++) {
      const p = ps[i], u = uvs[i], c = cols[i], l = lits[i];
      P.push(p[0], p[1], p[2]); Nn.push(nrm[0], nrm[1], nrm[2]); Uv.push(u[0], u[1]); C.push(c, c, c); L.push(l[0] / 15, l[1] / 15);
    }
    const b = this.n; this.n += 4;
    if (flip) this.idx.push(b + 1, b + 2, b + 3, b + 1, b + 3, b); else this.idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
  }
}
export const CHUNK = 32; // meshes are split into 32x32 columns so the camera skips what is outside the frame

// grid: Map "x,y,z" -> block name (static blocks). dynKeys: positions whose block changes over time (never occlude).
// defOf(name) -> resolveDef result. Returns { groups: Map(key -> { tex, def, kind, flow, chunk, builder }), light }.
export function meshWorld(grid, defOf, dynKeys = new Set(), light = null) {
  const V0 = light && light.V ? light.V : buildVolume(grid, dynKeys);
  light = light || computeLight(grid, defOf, dynKeys, V0);
  const groups = new Map();
  if (!V0) return { groups, light };
  const { x0, y0, z0, x1, y1, z1, NX, NZ, vol, names } = V0;
  const defs = [null, ...names.map((nm) => defOf(nm))];
  const get = (x, y, z) => { if (x < x0 || x > x1 || y < y0 || y > y1 || z < z0 || z > z1) return null; const id = vol[((y - y0) * NZ + (z - z0)) * NX + (x - x0)]; return id > 0 ? defs[id] : null; };
  const solid = (d) => d && d.shape === 'cube' && d.kind === 'opaque';
  const aoOcc = (x, y, z) => { const d = get(x, y, z); return d && d.shape === 'cube' && (d.kind === 'opaque' || (d.kind === 'cutout' && !d.glassy)) ? 1 : 0; };
  let curChunk = '';
  const group = (d, tex) => {
    const key = `${curChunk}|${tex}|${d.kind}|${d.flow ? d.flow.join(',') : ''}`;
    let g = groups.get(key);
    if (!g) { g = { tex, def: d, kind: d.kind, flow: d.flow, chunk: curChunk, builder: new Builder() }; groups.set(key, g); }
    return g.builder;
  };
  const cellLight = (x, y, z) => { const v = light.pk(x, y, z); return [v >> 4, v & 15]; };

  // emit an axis-aligned box face. box in block-local units [0..1]. onBoundary: face lies on the block boundary (AO + culling apply)
  const boxFace = (x, y, z, d, f, box, opts = {}) => {
    const [bx0, by0, bz0, bx1, by1, bz1] = box; const { n, R, U } = f;
    const tex = opts.tex ?? d.tex[f.slot];
    const onB = (n[0] === 1 && bx1 === 1) || (n[0] === -1 && bx0 === 0) || (n[1] === 1 && by1 === 1) || (n[1] === -1 && by0 === 0) || (n[2] === 1 && bz1 === 1) || (n[2] === -1 && bz0 === 0);
    if (onB && !opts.noCull) {
      const nb = get(x + n[0], y + n[1], z + n[2]);
      if (solid(nb)) return;
      if (nb && nb.base === d.base && d.shape === 'cube' && !d.leaves) return; // glass-glass, ice-ice (leaves keep inner faces: the game's fancy leaves)
      if (nb && d.shape === 'liquid' && nb.shape === 'liquid' && nb.base === d.base) return;
    }
    // face plane coordinate and corner points
    const corners = [];
    for (const [sr, su] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      const p = [0, 0, 0];
      for (let a = 0; a < 3; a++) {
        if (n[a] !== 0) p[a] = n[a] > 0 ? box[a + 3] : box[a];
        else { const s = R[a] !== 0 ? sr * Math.sign(R[a]) : su * Math.sign(U[a]); p[a] = s > 0 ? box[a + 3] : box[a]; }
      }
      corners.push({ p, sr, su });
    }
    const ps = [], uvs = [], cols = [], lits = []; const aoS = [];
    for (const c of corners) {
      const p = c.p; ps.push([x + p[0], y + p[1], z + p[2]]);
      const uOf = (V) => (V[0] > 0 ? p[0] : V[0] < 0 ? 1 - p[0] : V[1] > 0 ? p[1] : V[1] < 0 ? 1 - p[1] : V[2] > 0 ? p[2] : 1 - p[2]);
      { let uu = uOf(R), vv = uOf(U); for (let r = 0; r < (opts.uvRot || 0); r++) { const t0 = uu; uu = vv; vv = 1 - t0; } uvs.push([uu, vv]); }
      let ao = 3, L = cellLight(x + n[0], y + n[1], z + n[2]);
      if (onB) {
        const s1 = R.map((v) => v * c.sr), s2 = U.map((v) => v * c.su); const ax = x + n[0], ay = y + n[1], az = z + n[2];
        const a1 = aoOcc(ax + s1[0], ay + s1[1], az + s1[2]), a2 = aoOcc(ax + s2[0], ay + s2[1], az + s2[2]);
        const a3 = aoOcc(ax + s1[0] + s2[0], ay + s1[1] + s2[1], az + s1[2] + s2[2]);
        ao = a1 && a2 ? 0 : 3 - (a1 + a2 + a3);
        // smooth light: average the 4 cells touching this corner in front of the face (skip opaque ones)
        let ss = 0, sb = 0, cnt = 0;
        const cellsL = [[0, 0, 0], s1, s2]; if (!(a1 && a2)) cellsL.push([s1[0] + s2[0], s1[1] + s2[1], s1[2] + s2[2]]);
        for (const o of cellsL) { if (light.opaqueAt(ax + o[0], ay + o[1], az + o[2])) continue; const l = cellLight(ax + o[0], ay + o[1], az + o[2]); ss += l[0]; sb += l[1]; cnt++; }
        if (cnt) L = [ss / cnt, sb / cnt];
      } else L = cellLight(x, y, z);
      if (opts.flat) ao = 3;
      aoS.push(AO_CURVE[ao]);
      cols.push(AO_CURVE[ao] * (opts.flat ? 1 : f.shade)); lits.push(L);
    }
    const br = (i) => aoS[i] * (0.2 + lits[i][0] / 15 + lits[i][1] / 20);
    const flip = br(0) + br(2) < br(1) + br(3);
    group(d, tex).quad(ps, n, uvs, cols, lits, flip);
  };
  const box6 = (x, y, z, d, box, opts) => { for (const f of FACES) boxFace(x, y, z, d, f, box, opts); };

  const SL = NX * NZ;
  for (let i = 0; i < vol.length; i++) {
    const id = vol[i]; if (id <= 0) continue;
    const x = (i % NX) + x0, z = (((i / NX) | 0) % NZ) + z0, y = ((i / SL) | 0) + y0; const d = defs[id];
    curChunk = `${Math.floor(x / CHUNK)},${Math.floor(z / CHUNK)}`;
    switch (d.shape) {
      case 'cube': {
        if (d.prop === 'x' || d.prop === 'z') { // logs on their side: the end grain faces the axis
          for (const f of FACES) { const alongAxis = (d.prop === 'x' && f.n[0] !== 0) || (d.prop === 'z' && f.n[2] !== 0); boxFace(x, y, z, d, f, [0, 0, 0, 1, 1, 1], { tex: alongAxis ? d.tex.top : d.tex.side }); }
        } else box6(x, y, z, d, [0, 0, 0, 1, 1, 1]);
        break;
      }
      case 'liquid': {
        const above = get(x, y + 1, z); const h = above && above.base === d.base ? 1 : 14 / 16;
        box6(x, y, z, d, [0, 0, 0, 1, h, 1], { flat: false });
        if (h < 1) { const f = FACES[3]; const nb = get(x, y + 1, z); if (!solid(nb)) boxFace(x, y, z, d, { ...f, n: [0, -1, 0] }, [0, h, 0, 1, h, 1], { noCull: true }); } // underside of the surface, seen from below water
        break;
      }
      case 'slab': { const top = d.prop === 'top' || d.def.half === 'top'; box6(x, y, z, d, top ? [0, 0.5, 0, 1, 1, 1] : [0, 0, 0, 1, 0.5, 1]); break; }
      case 'layer': { const h = (d.height ?? 2) / 16; box6(x, y, z, d, [0, 0, 0, 1, h, 1]); break; }
      case 'stairs': { // bottom half + the upper half on the side the stairs climb toward (prop: north|south|east|west, default north)
        box6(x, y, z, d, [0, 0, 0, 1, 0.5, 1]);
        const dir = d.prop || d.def.facing || 'north';
        const up = { north: [0, 0.5, 0, 1, 1, 0.5], south: [0, 0.5, 0.5, 1, 1, 1], east: [0.5, 0.5, 0, 1, 1, 1], west: [0, 0.5, 0, 0.5, 1, 1] }[dir] || [0, 0.5, 0, 1, 1, 0.5];
        box6(x, y, z, d, up); break;
      }
      case 'fence': case 'wall': {
        const isW = d.shape === 'wall'; const p0 = isW ? 4 / 16 : 6 / 16, p1 = 1 - p0;
        box6(x, y, z, d, [p0, 0, p0, p1, 1, p1], { flat: false });
        const conn = (dx, dz) => { const nb = get(x + dx, y, z + dz); return nb && (nb.shape === d.shape || solid(nb)); };
        const bars = isW ? [[0, 14 / 16]] : [[6 / 16, 9 / 16], [12 / 16, 15 / 16]]; const w0 = isW ? 5 / 16 : 7 / 16, w1 = 1 - w0;
        for (const [ya, yb] of bars) {
          if (conn(1, 0)) box6(x, y, z, d, [p1, ya, w0, 1, yb, w1]);
          if (conn(-1, 0)) box6(x, y, z, d, [0, ya, w0, p0, yb, w1]);
          if (conn(0, 1)) box6(x, y, z, d, [w0, ya, p1, w1, yb, 1]);
          if (conn(0, -1)) box6(x, y, z, d, [w0, ya, 0, w1, yb, p0]);
        }
        break;
      }
      case 'cross': { // two diagonal quads, both sides, with the game's small random offset per position
        const h = hash3(x, y, z), ox = (h - 0.5) * 0.36, oz = (hash3(z, x, y) - 0.5) * 0.36, L = cellLight(x, y, z);
        const s = 0.5 - 0.5 * 0.9; const a = s, c = 1 - s; const bl = group(d, d.tex.side);
        const P = (u, yy, w) => [x + u + ox, y + yy, z + w + oz];
        const lits = [L, L, L, L], cols = [1, 1, 1, 1];
        for (const [p, q] of [[[a, a], [c, c]], [[a, c], [c, a]]]) {
          const quad = [P(p[0], 0, p[1]), P(q[0], 0, q[1]), P(q[0], 1, q[1]), P(p[0], 1, p[1])]; const uv = [[0, 0], [1, 0], [1, 1], [0, 1]];
          bl.quad(quad, [0, 1, 0], uv, cols, lits, false); bl.quad([quad[1], quad[0], quad[3], quad[2]], [0, 1, 0], [[1, 0], [0, 0], [0, 1], [1, 1]], cols, lits, false);
        }
        break;
      }
      case 'torch': { // the block-model torch: a 2x10 px stick (texture cols 7-8, rows 6-15) with its tip as the flame
        const P = 1 / 16; const bx = [7 * P, 0, 7 * P, 9 * P, 10 * P, 9 * P]; const bl = group({ ...d, kind: 'emissive' }, d.tex.side);
        for (const f of FACES) {
          if (f.n[1] === -1) continue;
          const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sr, su]) => {
            const p = [0, 0, 0];
            for (let a2 = 0; a2 < 3; a2++) { if (f.n[a2] !== 0) p[a2] = f.n[a2] > 0 ? bx[a2 + 3] : bx[a2]; else { const sg = f.R[a2] !== 0 ? sr * Math.sign(f.R[a2]) : su * Math.sign(f.U[a2]); p[a2] = sg > 0 ? bx[a2 + 3] : bx[a2]; } }
            return { p, sr, su };
          });
          const uv = corners.map((c) => f.n[1] === 1 ? [(c.sr > 0 ? 9 : 7) / 16, (c.su > 0 ? 10 : 8) / 16] : [(c.sr > 0 ? 9 : 7) / 16, c.su > 0 ? 10 / 16 : 0]);
          bl.quad(corners.map((c) => [x + c.p[0], y + c.p[1], z + c.p[2]]), f.n, uv, [1, 1, 1, 1], [[15, 15], [15, 15], [15, 15], [15, 15]], false);
        }
        break;
      }

      // ---- v0.3 shapes. Orientation suffix: "oak_door:south", "oak_door:south:open", "ladder:north", "rail:x", "bed_head:east"
      case 'door': { // two halves 3 px thick on the `facing` side; open = swung against the side wall
        const parts = (d.prop || 'south').split(':'); const fc = parts[0]; const open = parts.includes('open'); const T = 3 / 16;
        const slab = { south: [0, 0, 1 - T, 1, 1, 1], north: [0, 0, 0, 1, 1, T], east: [1 - T, 0, 0, 1, 1, 1], west: [0, 0, 0, T, 1, 1] };
        const swing = { south: 'east', north: 'west', east: 'north', west: 'south' };
        const bx = slab[open ? swing[fc] : fc] || slab.south;
        box6(x, y, z, d, bx, { noCull: true, tex: d.tex.side }); box6(x, y + 1, z, d, bx, { noCull: true, tex: d.tex.top });
        break;
      }
      case 'trapdoor': { const parts = (d.prop || 'south').split(':'); const T = 3 / 16;
        const bx = parts.includes('open') ? ({ south: [0, 0, 1 - T, 1, 1, 1], north: [0, 0, 0, 1, 1, T], east: [1 - T, 0, 0, 1, 1, 1], west: [0, 0, 0, T, 1, 1] }[parts[0]] || [0, 0, 0, 1, 1, T])
          : parts.includes('top') ? [0, 1 - T, 0, 1, 1, 1] : [0, 0, 0, 1, T, 1];
        box6(x, y, z, d, bx, { noCull: true }); break; }
      case 'ladder': case 'vine': { // a flat cutout panel against the wall it hangs on
        const fc = d.prop || 'north'; const T = 0.8 / 16;
        const bx = { north: [0, 0, 0, 1, 1, T], south: [0, 0, 1 - T, 1, 1, 1], east: [1 - T, 0, 0, 1, 1, 1], west: [0, 0, 0, T, 1, 1] }[fc] || [0, 0, 0, 1, 1, T];
        box6(x, y, z, d, bx, { noCull: true, flat: true }); break; }
      case 'rail': box6(x, y, z, d, [0, 0, 0, 1, 1 / 16, 1], { noCull: true, flat: true, uvRot: d.prop === 'x' || d.prop === 'east' || d.prop === 'west' ? 1 : 0 }); break;
      case 'pane': { // glass panes and iron bars: a thin post that reaches toward panes and solid blocks around it
        const a = 7 / 16, b = 9 / 16; box6(x, y, z, d, [a, 0, a, b, 1, b], { noCull: true });
        const conn = (dx, dz) => { const nb = get(x + dx, y, z + dz); return nb && (nb.shape === 'pane' || solid(nb)); };
        if (conn(1, 0)) box6(x, y, z, d, [b, 0, a, 1, 1, b], { noCull: true }); if (conn(-1, 0)) box6(x, y, z, d, [0, 0, a, a, 1, b], { noCull: true });
        if (conn(0, 1)) box6(x, y, z, d, [a, 0, b, b, 1, 1], { noCull: true }); if (conn(0, -1)) box6(x, y, z, d, [a, 0, 0, b, 1, a], { noCull: true });
        break; }
      case 'crop': { // the game's crop model: four upright planes in a # pattern
        const L = cellLight(x, y, z), bl = group(d, d.tex.side); const lits = [L, L, L, L], cols = [1, 1, 1, 1];
        for (const k of [4 / 16, 12 / 16]) {
          for (const [q, n] of [[[[x + k, y, z], [x + k, y, z + 1], [x + k, y + 1, z + 1], [x + k, y + 1, z]], [1, 0, 0]], [[[x, y, z + k], [x + 1, y, z + k], [x + 1, y + 1, z + k], [x, y + 1, z + k]], [0, 0, 1]]]) {
            bl.quad(q, [0, 1, 0], [[0, 0], [1, 0], [1, 1], [0, 1]], cols, lits, false); bl.quad([q[1], q[0], q[3], q[2]], [0, 1, 0], [[1, 0], [0, 0], [0, 1], [1, 1]], cols, lits, false); void n;
          }
        }
        break; }
      case 'cactus': box6(x, y, z, d, [1 / 16, 0, 1 / 16, 15 / 16, 1, 15 / 16]); break;
      case 'bed': { // 9 px tall; the top turns with the facing (head toward the facing side)
        const fc = d.prop || 'south'; const rotTop = { south: 0, west: 1, north: 2, east: 3 }[fc] ?? 0;
        for (const f of FACES) boxFace(x, y, z, d, f, [0, 0, 0, 1, 9 / 16, 1], f.n[1] === 1 ? { uvRot: rotTop } : {});
        break; }
      default: box6(x, y, z, d, [0, 0, 0, 1, 1, 1]);
    }
  }
  return { groups, light };
}

// Alpha-aware mipmaps for pixel-art textures: colour = average of the opaque texels, alpha = coverage >= 40 %.
// Without them distant blocks shimmer ("flicker") while the camera moves; with plain mipmaps leaves and plants vanish.
export function pixelMipmaps(img, cutout) {
  const out = []; let w = img.width, h = img.height;
  const c0 = document.createElement('canvas'); c0.width = w; c0.height = h; const g0 = c0.getContext('2d'); g0.drawImage(img, 0, 0); out.push(c0);
  let src = g0.getImageData(0, 0, w, h);
  while (w > 1 || h > 1) {
    const nw = Math.max(1, w >> 1), nh = Math.max(1, h >> 1); const c = document.createElement('canvas'); c.width = nw; c.height = nh;
    const g = c.getContext('2d'); const dst = g.createImageData(nw, nh);
    for (let y = 0; y < nh; y++) for (let x = 0; x < nw; x++) {
      let r = 0, gg = 0, b = 0, a = 0, cov = 0, n = 0;
      for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) {
        const sx = Math.min(w - 1, x * 2 + dx), sy = Math.min(h - 1, y * 2 + dy); const i = (sy * w + sx) * 4; const al = src.data[i + 3];
        n++; a += al; if (al > 0) { r += src.data[i] * al; gg += src.data[i + 1] * al; b += src.data[i + 2] * al; cov += al; }
      }
      const o = (y * nw + x) * 4;
      if (cov > 0) { dst.data[o] = r / cov; dst.data[o + 1] = gg / cov; dst.data[o + 2] = b / cov; }
      dst.data[o + 3] = cutout ? (a / n >= 0.4 * 255 ? 255 : 0) : a / n;
    }
    g.putImageData(dst, 0, 0); out.push(c); src = dst; w = nw; h = nh;
  }
  return out;
}
