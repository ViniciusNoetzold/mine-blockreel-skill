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

// ---------------------------------------------------------------------------------------------- light ----
// Light volume over the grid's bounding box (+1 margin, open sky above). sky/block are 0..15 per cell.
export function computeLight(grid, defOf, dynKeys = new Set()) {
  let x0 = Infinity, y0 = Infinity, z0 = Infinity, x1 = -Infinity, y1 = -Infinity, z1 = -Infinity;
  const cells = [];
  for (const [k, b] of grid) { const [x, y, z] = k.split(',').map(Number); cells.push([x, y, z, b, k]); if (x < x0) x0 = x; if (y < y0) y0 = y; if (z < z0) z0 = z; if (x > x1) x1 = x; if (y > y1) y1 = y; if (z > z1) z1 = z; }
  if (!cells.length) return { at: () => [15, 0], sample: () => [15, 0], opaqueAt: () => false };
  x0 -= 1; y0 -= 1; z0 -= 1; x1 += 1; y1 += 2; z1 += 1;
  const NX = x1 - x0 + 1, NY = y1 - y0 + 1, NZ = z1 - z0 + 1, N = NX * NY * NZ;
  const idx = (x, y, z) => ((y - y0) * NZ + (z - z0)) * NX + (x - x0);
  const block = new Uint8Array(N); // 0 air, 1 opaque, 2 attenuates (leaves, water), 3 passes light (glass, plants)
  const emit = [];
  for (const [x, y, z, b, k] of cells) {
    const d = defOf(b); const i = idx(x, y, z);
    if (dynKeys.has(k)) { block[i] = 3; } // blocks that change over time do not shadow the static world
    else block[i] = d.kind === 'opaque' && d.shape === 'cube' ? 1 : (d.leaves || d.shape === 'liquid') ? 2 : 3;
    if (d.light > 0) emit.push([i, d.light]);
  }
  const sky = new Uint8Array(N), blk = new Uint8Array(N);
  const q = new Int32Array(N * 2); // BFS queue (cells may be re-queued once per improvement)
  const spread = (L, seeds) => {
    let head = 0, tail = 0;
    for (const s of seeds) q[tail++] = s;
    const stride = [1, -1, NX * NZ, -NX * NZ, NX, -NX];
    while (head < tail) {
      const i = q[head++]; const lv = L[i]; if (lv <= 1) continue;
      const x = i % NX, z = Math.floor(i / NX) % NZ, y = Math.floor(i / (NX * NZ));
      for (let d = 0; d < 6; d++) {
        if ((d === 0 && x === NX - 1) || (d === 1 && x === 0) || (d === 2 && y === NY - 1) || (d === 3 && y === 0) || (d === 4 && z === NZ - 1) || (d === 5 && z === 0)) continue;
        const j = i + stride[d]; if (block[j] === 1) continue;
        const nl = lv - (block[j] === 2 ? 2 : 1);
        if (nl > L[j]) { L[j] = nl; if (tail < q.length) q[tail++] = j; }
      }
    }
  };
  const seeds = [];
  for (let x = 0; x < NX; x++) for (let z = 0; z < NZ; z++) {
    let lv = 15;
    for (let y = NY - 1; y >= 0; y--) {
      const i = (y * NZ + z) * NX + x; const b = block[i];
      if (b === 1) break; if (b === 2) lv = Math.max(0, lv - 2);
      sky[i] = lv; if (lv > 1) seeds.push(i);
    }
  }
  spread(sky, seeds);
  const bseeds = [];
  for (const [i, l] of emit) { if (l > blk[i]) blk[i] = l; bseeds.push(i); }
  spread(blk, bseeds);
  const at = (x, y, z) => {
    if (x < x0 || x > x1 || y < y0 || z < z0 || z > z1) return [15, 0];
    if (y > y1) return [15, 0];
    const i = idx(x, y, z); return [sky[i], blk[i]];
  };
  // light in a cell for something standing in it (an actor): max of the cell and the one above, so feet in a slab still read lit
  const sample = (x, y, z) => { const a = at(Math.floor(x), Math.floor(y), Math.floor(z)), b = at(Math.floor(x), Math.floor(y) + 1, Math.floor(z)); return [Math.max(a[0], b[0]), Math.max(a[1], b[1])]; };
  return { at, sample, opaqueAt: (x, y, z) => { if (x < x0 || x > x1 || y < y0 || y > y1 || z < z0 || z > z1) return false; return block[idx(x, y, z)] === 1; } };
}

// ------------------------------------------------------------------------------------------------ mesh ----
// A geometry builder per material key; the engine turns each into a THREE.BufferGeometry + material.
class Builder {
  constructor() { this.pos = []; this.nor = []; this.uv = []; this.col = []; this.lit = []; this.idx = []; this.n = 0; }
  quad(ps, nrm, uvs, cols, lits, flip) {
    for (let i = 0; i < 4; i++) { this.pos.push(...ps[i]); this.nor.push(...nrm); this.uv.push(...uvs[i]); this.col.push(cols[i], cols[i], cols[i]); this.lit.push(lits[i][0] / 15, lits[i][1] / 15); }
    const b = this.n; this.n += 4;
    if (flip) this.idx.push(b + 1, b + 2, b + 3, b + 1, b + 3, b); else this.idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
  }
}

// grid: Map "x,y,z" -> block name (static blocks). dynKeys: positions whose block changes over time (never occlude).
// defOf(name) -> resolveDef result. Returns { groups: Map(key -> { tex, def, kind, builder }), light }.
export function meshWorld(grid, defOf, dynKeys = new Set(), light = null) {
  light = light || computeLight(grid, defOf, dynKeys);
  const groups = new Map();
  const get = (x, y, z) => { const k = `${x},${y},${z}`; if (dynKeys.has(k)) return null; const b = grid.get(k); return b ? defOf(b) : null; };
  const solid = (d) => d && d.shape === 'cube' && d.kind === 'opaque';
  const aoOcc = (x, y, z) => { const d = get(x, y, z); return d && d.shape === 'cube' && (d.kind === 'opaque' || (d.kind === 'cutout' && !d.glassy)) ? 1 : 0; };
  const group = (d, tex) => {
    const key = `${tex}|${d.kind}|${d.flow ? d.flow.join(',') : ''}`;
    if (!groups.has(key)) groups.set(key, { tex, def: d, kind: d.kind, flow: d.flow, builder: new Builder() });
    return groups.get(key).builder;
  };
  const cellLight = (x, y, z) => light.at(x, y, z);

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
      uvs.push([uOf(R), uOf(U)]);
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

  for (const [k, b] of grid) {
    if (dynKeys.has(k)) continue;
    const [x, y, z] = k.split(',').map(Number); const d = defOf(b);
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
