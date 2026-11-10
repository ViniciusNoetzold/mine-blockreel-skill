// World ops -> block grid (Map "x,y,z" -> block). Pure and seeded: the same ops always give the same world.
//
//   { "fill":   ["stone", [x0,y0,z0], [x1,y1,z1]] }                 solid box ("air" removes)
//   { "set":    ["gold", [x,y,z]] }                                  one block
//   { "hollow": ["planks", [x0,y0,z0], [x1,y1,z1]] }                 box shell (floor and roof included)
//   { "tree":   [x,y,z], "kind": "oak|birch|spruce|dead", "height": 5 }   y may be null: on the ground
//   { "sphere": ["glass", [cx,cy,cz], r], "hollow": false, "half": false }
//   { "cylinder": ["cobblestone", [cx,y0,cz], r, h], "hollow": false }
//   { "terrain": { "radius": 40, "center": [0,0], "base": 4, "amp": 3, "scale": 16, "seed": 1, "top": "grass", "soil": "dirt",
//                  "stone": "stone", "water": 3, "flat": { "center": [0,0], "radius": 8, "y": 4 },
//                  "trees": 0.015, "treeKinds": ["oak","birch"], "plants": 0.12, "flowers": 0.02, "biome": "plains" } }
//   { "scatter": ["tall_grass", [x0,z0], [x1,z1]], "density": 0.2, "seed": 3, "on": ["grass"] }   on top of the ground
//   { "structure": "house|tower|ruins|shrine|pillar|campfire", "pos": [x,y,z], "face": "south", "block": "...", "seed": 1 }

export function mulberry(a) { return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const h2 = (x, z, s) => { let h = (x * 374761393 + z * 668265263 + s * 982451653) | 0; h = (h ^ (h >>> 13)) * 1274126177; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
const smooth = (u) => u * u * (3 - 2 * u);
function vnoise(x, z, s) { const xi = Math.floor(x), zi = Math.floor(z), xf = smooth(x - xi), zf = smooth(z - zi);
  const a = h2(xi, zi, s), b = h2(xi + 1, zi, s), c = h2(xi, zi + 1, s), d = h2(xi + 1, zi + 1, s);
  return (a + (b - a) * xf) + ((c + (d - c) * xf) - (a + (b - a) * xf)) * zf; }
export function fbm(x, z, s) { return vnoise(x, z, s) * 0.62 + vnoise(x * 2.1, z * 2.1, s + 17) * 0.26 + vnoise(x * 4.3, z * 4.3, s + 31) * 0.12; }

const BIOMES = {
  plains: { top: 'grass', soil: 'dirt', stone: 'stone', shore: 'sand', treeKinds: ['oak', 'oak', 'birch'], plants: ['tall_grass'], flowers: ['flower_red', 'flower_yellow'] },
  forest: { top: 'grass', soil: 'dirt', stone: 'stone', shore: 'sand', treeKinds: ['oak', 'birch', 'birch'], plants: ['tall_grass'], flowers: ['flower_red'], trees: 0.05 },
  taiga: { top: 'grass', soil: 'dirt', stone: 'stone', shore: 'gravel', treeKinds: ['spruce'], plants: ['tall_grass'], flowers: [], trees: 0.04 },
  desert: { top: 'sand', soil: 'sand', stone: 'sandstone', shore: 'sand', treeKinds: [], plants: ['dead_bush'], flowers: [], trees: 0, plantsDensity: 0.015 },
  snowy: { top: 'snow', soil: 'dirt', stone: 'stone', shore: 'gravel', treeKinds: ['spruce'], plants: [], flowers: [], trees: 0.02 },
  nether: { top: 'netherrack', soil: 'netherrack', stone: 'netherrack', shore: 'soul_sand', treeKinds: [], plants: ['fire'], flowers: [], trees: 0, plantsDensity: 0.01, liquid: 'lava' },
  wasteland: { top: 'gravel', soil: 'dirt', stone: 'stone', shore: 'gravel', treeKinds: ['dead'], plants: ['dead_bush'], flowers: [], trees: 0.01, plantsDensity: 0.03 },
};

// Ground plan of a structure: centre and radius (blocks) it needs, plus the height it occupies. Used to keep trees and plants
// out of building sites, to clear the site, and to warn when two buildings (or a building and the arena) overlap.
export function footprint(op) {
  const [x, , z] = op.pos || [0, null, 0]; const k = op.structure;
  const r = k === 'house' ? Math.max(op.w ?? 7, op.d ?? 6) / 2 + 1.5 : k === 'tower' ? (op.r ?? 3) + 1 : k === 'ruins' ? Math.max(op.w ?? 9, op.d ?? 7) / 2 + 0.5
    : k === 'shrine' ? 3 : k === 'campfire' ? 2 : k === 'well' ? 3 : k === 'farm' ? Math.max(op.w ?? 7, op.d ?? 5) / 2 + 1.5 : k === 'village' ? (op.size ?? 16) + 8 : k === 'lamp' ? 1 : 1;
  const h = k === 'house' ? 9 : k === 'tower' ? (op.h ?? 12) + 3 : k === 'pillar' ? (op.h ?? 5) + 2 : 5;
  return { x, z, r, h, kind: k };
}
export function layoutWarnings(ops) {
  const out = []; const fps = (ops || []).filter((o) => o.structure).map(footprint);
  const flat = (ops || []).map((o) => o.terrain?.flat).find(Boolean);
  for (let i = 0; i < fps.length; i++) {
    for (let j = i + 1; j < fps.length; j++) { const a = fps[i], b = fps[j]; if (Math.hypot(a.x - b.x, a.z - b.z) < a.r + b.r) out.push(`${a.kind} at ${a.x},${a.z} overlaps ${b.kind} at ${b.x},${b.z}`); }
    if (flat && fps[i].kind !== 'shrine' && fps[i].kind !== 'campfire' && Math.hypot(fps[i].x - flat.center[0], fps[i].z - flat.center[1]) < fps[i].r + flat.radius) out.push(`${fps[i].kind} at ${fps[i].x},${fps[i].z} cuts into the arena`);
  }
  return out;
}

export function expandWorld(ops, seed0 = 1) {
  // terrain first, then everything else in the given order: buildings always stand on the finished ground
  ops = [...(ops || []).filter((o) => o.terrain), ...(ops || []).filter((o) => !o.terrain)];
  const sites = ops.filter((o) => o.structure).map(footprint);
  const grid = new Map(); const K = (x, y, z) => `${x},${y},${z}`;
  const set = (b, x, y, z) => { const k = K(x, y, z); if (b === 'air') grid.delete(k); else grid.set(k, b); };
  const setIfAir = (b, x, y, z) => { if (!grid.has(K(x, y, z))) set(b, x, y, z); };
  const range = (a, b) => { const lo = Math.min(a, b), hi = Math.max(a, b); const r = []; for (let i = lo; i <= hi; i++) r.push(i); return r; };
  const ground = (x, z, from = 160) => { for (let y = from; y > -64; y--) { const b = grid.get(K(x, y, z)); if (b && !/tall_grass|flower|dead_bush|fire|torch|mushroom|sapling|snow_layer|wheat|carrots|potatoes|beetroots|rail|ladder|vine|door|lamp/.test(b)) return y + 1; } return 1; };

  const tree = (x, y, z, kind = 'oak', h, rng = Math.random) => {
    if (y === null || y === undefined) y = ground(x, z);
    if (kind === 'spruce') {
      h = h ?? 6 + Math.floor(rng() * 3);
      for (let i = 0; i < h; i++) set('spruce_log', x, y + i, z);
      for (let i = 2; i <= h; i++) { const r = Math.max(0, Math.min(2, Math.floor((h - i) / 1.6) % 3)) + ((h - i) % 2 === 0 ? 0 : -1); const rr = Math.max(0, r);
        for (let dx = -rr; dx <= rr; dx++) for (let dz = -rr; dz <= rr; dz++) if (!(Math.abs(dx) === rr && Math.abs(dz) === rr && rr > 0) && (dx || dz)) setIfAir('spruce_leaves', x + dx, y + i, z + dz); }
      set('spruce_leaves', x, y + h, z); set('spruce_leaves', x, y + h + 1, z); return;
    }
    if (kind === 'dead') { h = h ?? 3 + Math.floor(rng() * 2); for (let i = 0; i < h; i++) set('log', x, y + i, z); set('log:x', x + 1, y + h - 1, z); set('log:z', x, y + h - 2, z - 1); return; }
    const log = kind === 'birch' ? 'birch_log' : 'log', leaves = kind === 'birch' ? 'birch_leaves' : 'leaves';
    h = h ?? (kind === 'birch' ? 5 + Math.floor(rng() * 2) : 4 + Math.floor(rng() * 2));
    for (let i = 0; i < h; i++) set(log, x, y + i, z);
    for (let dx = -2; dx <= 2; dx++) for (let dz = -2; dz <= 2; dz++) for (let dy = h - 2; dy <= h; dy++) {
      const corner = Math.abs(dx) === 2 && Math.abs(dz) === 2;
      if (corner && (dy === h || rng() < 0.6)) continue;
      if (dy === h && (Math.abs(dx) === 2 || Math.abs(dz) === 2)) continue;
      if (!(dx === 0 && dz === 0 && dy < h)) setIfAir(leaves, x + dx, y + dy, z + dz);
    }
    setIfAir(leaves, x, y + h + 1, z); for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) setIfAir(leaves, x + dx, y + h + 1, z + dz);
  };


  // carve a tube of air along a polyline (tunnels, cave worms); the floor below becomes `floor` when given
  const carve = (pts, R, floor, rngT) => {
    for (let i = 1; i < pts.length; i++) {
      const [a, b] = [pts[i - 1], pts[i]]; const L = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]); const n = Math.max(1, Math.ceil(L / 0.5));
      for (let k = 0; k <= n; k++) {
        const u = k / n, cx = a[0] + (b[0] - a[0]) * u, cy = a[1] + (b[1] - a[1]) * u, cz = a[2] + (b[2] - a[2]) * u; const r = R * (0.85 + (rngT ? rngT() * 0.3 : 0.15));
        for (let dx = -Math.ceil(r); dx <= Math.ceil(r); dx++) for (let dy = -Math.ceil(r); dy <= Math.ceil(r); dy++) for (let dz = -Math.ceil(r); dz <= Math.ceil(r); dz++) {
          if (Math.hypot(dx, dy * 1.15, dz) > r) continue; const X = Math.round(cx) + dx, Y = Math.round(cy) + dy, Z = Math.round(cz) + dz;
          if (grid.get(K(X, Y, Z)) === 'bedrock') continue; grid.delete(K(X, Y, Z));
          if (floor && dy === -Math.ceil(r) + 1 && grid.has(K(X, Y - 1, Z))) set(floor, X, Y - 1, Z);
        }
      }
    }
  };

  const structure = (op) => {
    const rng = mulberry((op.seed ?? 1) * 7919 + seed0);
    let [x, y, z] = op.pos || [0, null, 0]; if (y === null || y === undefined) y = ground(x, z);
    const kind = op.structure;
    { // clear the site: no tree, leaf or plant may stand where the building goes (incl. canopies that hang over it)
      const f = footprint({ ...op, pos: [x, y, z] }); const R = Math.ceil(f.r);
      for (let dx = -R; dx <= R; dx++) for (let dz = -R; dz <= R; dz++) {
        if (Math.hypot(dx, dz) > f.r + 0.5) continue;
        for (let yy = y; yy < y + f.h; yy++) { const k = K(x + dx, yy, z + dz); const c = grid.get(k); if (c && /log|leaves|tall_grass|flower|dead_bush|mushroom|sapling|poppy|dandelion/.test(c)) grid.delete(k); }
      }
    }
    // facing: build in local coordinates (door on the south side) and turn the result around the centre; orientation suffixes turn too
    const turns = { south: 0, west: 1, north: 2, east: 3 }[op.face || 'south'] ?? 0;
    const TR = (X, Z) => { let dx = X - x, dz = Z - z; for (let i = 0; i < turns; i++) [dx, dz] = [-dz, dx]; return [x + dx, z + dz]; };
    const DIRS = ['south', 'west', 'north', 'east'];
    const rotName = (bl) => { if (!turns || !bl.includes(':')) return bl; const [base, ...ps] = bl.split(':');
      return [base, ...ps.map((q) => (DIRS.includes(q) ? DIRS[(DIRS.indexOf(q) + turns) % 4] : (q === 'x' || q === 'z') && turns % 2 ? (q === 'x' ? 'z' : 'x') : q))].join(':'); };
    const setR = (bl, X, Y, Z) => { const [a2, c2] = TR(X, Z); set(rotName(bl), a2, Y, c2); };
    const KR = (X, Y, Z) => { const [a2, c2] = TR(X, Z); return K(a2, Y, c2); };
    const found = (x0, x1, z0, z1, top, b) => { // foundation: fill each column under the footprint down to the terrain
      if (op.foundation === false) return;
      for (const xx of range(x0, x1)) for (const zz of range(z0, z1)) for (let yy = top; yy > top - 24; yy--) { const k = KR(xx, yy, zz); const c = grid.get(k); if (c && !/tall_grass|flower|dead_bush|fire|torch|leaves|water/.test(c)) break; setR(b, xx, yy, zz); }
    };
    if (kind === 'house') { // 7x6 oak cabin: cobble base, plank walls, log corners, glass windows, door gap on the south side, stair-free pitched roof
      const W = op.w ?? 7, D = op.d ?? 6, H = 4; const x0 = x - (W >> 1), z0 = z - (D >> 1), x1 = x0 + W - 1, z1 = z0 + D - 1;
      found(x0, x1, z0, z1, y - 2, 'cobblestone');
      for (const xx of range(x0, x1)) for (const zz of range(z0, z1)) { setR('cobblestone', xx, y - 1, zz); for (let yy = y; yy < y + H + 4; yy++) setR('air', xx, yy, zz); }
      for (const xx of range(x0, x1)) for (const zz of range(z0, z1)) for (let yy = y; yy < y + H; yy++) {
        const edge = xx === x0 || xx === x1 || zz === z0 || zz === z1; if (!edge) continue;
        const corner = (xx === x0 || xx === x1) && (zz === z0 || zz === z1);
        setR(corner ? 'log' : (yy === y ? 'cobblestone' : op.block ?? 'planks'), xx, yy, zz);
      }
      const dx = x0 + (W >> 1); setR('air', dx, y, z1); setR('air', dx, y + 1, z1); // door gap (south)
      for (const wx of [x0 + 1, x1 - 1]) setR('glass', wx, y + 1, z1); for (const wz of [z0 + 2]) { setR('glass', x0, y + 1, wz); setR('glass', x1, y + 1, wz); }
      for (let i = 0; i <= (W >> 1) + 1; i++) for (const zz of range(z0 - 1, z1 + 1)) { // roof
        const yy = y + H + i - 1; if (x0 - 1 + i > x1 + 1 - i) break;
        const ridge = x0 - 1 + i >= x1 + 1 - i - 1; // roof of stairs climbing to a plank ridge, slab eaves
        setR(i === 0 ? 'oak_slab' : ridge ? 'dark_oak_planks' : 'oak_stairs:east', x0 - 1 + i, yy, zz); setR(i === 0 ? 'oak_slab' : ridge ? 'dark_oak_planks' : 'oak_stairs:west', x1 + 1 - i, yy, zz);
      }
      for (const xx of range(x0 + 1, x1 - 1)) for (const zz of range(z0 + 1, z1 - 1)) setR('planks', xx, y - 1, zz);
      setR('torch', x0 + 1, y, z0 + 1); setR('torch', x1 - 1, y, z0 + 1); setR('crafting_table', x1 - 1, y, z0 + 2);
    } else if (kind === 'tower') {
      const r = op.r ?? 3, h = op.h ?? 12; const b = op.block ?? 'stonebrick';
      found(x - r, x + r, z - r, z + r, y - 2, b);
      for (let yy = y - 1; yy < y + h; yy++) for (let dx = -r; dx <= r; dx++) for (let dz = -r; dz <= r; dz++) {
        const d = Math.hypot(dx, dz); if (d > r + 0.4) continue; const wall = d > r - 0.6;
        if (yy === y - 1 || (wall && !(yy > y && yy % 4 === 2 && (dx === 0 || dz === 0)))) setR(rng() < 0.15 ? 'stonebrick_mossy' : b, x + dx, yy, z + dz); else setR('air', x + dx, yy, z + dz);
      }
      setR('air', x, y, z + r); setR('air', x, y + 1, z + r);
      for (let dx = -r; dx <= r; dx++) for (let dz = -r; dz <= r; dz++) { const d = Math.hypot(dx, dz); if (d <= r + 0.4) setR(b, x + dx, y + h, z + dz); if (d > r - 0.6 && d <= r + 0.4 && (dx + dz) % 2 === 0) setR(b, x + dx, y + h + 1, z + dz); }
      setR('torch', x, y + h + 1, z); setR('torch', x + 1, y, z);
    } else if (kind === 'ruins') {
      const W = op.w ?? 9, D = op.d ?? 7; const x0 = x - (W >> 1), z0 = z - (D >> 1), x1 = x0 + W - 1, z1 = z0 + D - 1;
      for (const xx of range(x0, x1)) for (const zz of range(z0, z1)) {
        const edge = xx === x0 || xx === x1 || zz === z0 || zz === z1; if (!edge) { if (rng() < 0.5) setR(rng() < 0.4 ? 'mossy_cobblestone' : 'cobblestone', xx, y - 1, zz); continue; }
        const hh = Math.floor(rng() * 4.2); for (let yy = y; yy < y + hh; yy++) setR(rng() < 0.35 ? 'mossy_cobblestone' : rng() < 0.2 ? 'stonebrick_cracked' : 'cobblestone', xx, yy, zz);
      }
    } else if (kind === 'shrine') { // the fan-lore summoning altar: gold base, netherrack + fire on top, redstone torches around
      found(x - 2, x + 2, z - 2, z + 2, y - 1, 'mossy_cobblestone');
      for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) setR('gold', x + dx, y, z + dz);
      setR('mossy_cobblestone', x, y + 1, z); setR('netherrack', x, y + 2, z); setR('fire', x, y + 3, z);
      for (const [dx, dz] of [[2, 0], [-2, 0], [0, 2], [0, -2]]) setR('redstone_torch', x + dx, y + 1, z + dz);
      for (const [dx, dz] of [[2, 1], [2, -1], [-2, 1], [-2, -1], [1, 2], [-1, 2], [1, -2], [-1, -2], [2, 2], [-2, 2], [2, -2], [-2, -2]]) setR('mossy_cobblestone', x + dx, y, z + dz);
    } else if (kind === 'pillar') { const h = op.h ?? 5; for (let yy = y; yy < y + h; yy++) setR(op.block ?? 'quartz', x, yy, z); if (op.top !== false) setR(op.top ?? 'torch', x, y + h, z); }
    else if (kind === 'well') { found(x - 2, x + 2, z - 2, z + 2, y - 2, 'cobblestone');
      for (let dx = -2; dx <= 2; dx++) for (let dz = -2; dz <= 2; dz++) { const edge = Math.abs(dx) === 2 || Math.abs(dz) === 2; setR('cobblestone', x + dx, y - 1, z + dz); if (edge) setR('cobblestone', x + dx, y, z + dz); else { setR('water', x + dx, y - 1, z + dz); setR('water', x + dx, y - 2, z + dz); } }
      for (const [dx, dz] of [[-2, -2], [2, -2], [-2, 2], [2, 2]]) for (let yy = y + 1; yy < y + 3; yy++) setR('oak_fence', x + dx, yy, z + dz);
      for (let dx = -2; dx <= 2; dx++) for (let dz = -2; dz <= 2; dz++) setR('cobblestone_slab', x + dx, y + 3, z + dz);
    } else if (kind === 'farm') { const W = op.w ?? 7, D = op.d ?? 5; found(x - (W >> 1), x + (W >> 1), z - (D >> 1), z + (D >> 1), y - 2, 'dirt');
      for (let dx = -(W >> 1) - 1; dx <= (W >> 1) + 1; dx++) for (let dz = -(D >> 1) - 1; dz <= (D >> 1) + 1; dz++) {
        const edge = Math.abs(dx) === (W >> 1) + 1 || Math.abs(dz) === (D >> 1) + 1; for (let yy = y; yy < y + 3; yy++) setR('air', x + dx, yy, z + dz);
        if (edge) { setR('log:x', x + dx, y - 1, z + dz); continue; }
        if (dz === 0) { setR('water', x + dx, y - 1, z + dz); continue; }
        setR('farmland', x + dx, y - 1, z + dz); setR(op.crop ?? (rng() < 0.8 ? 'wheat' : 'carrots'), x + dx, y, z + dz);
      }
    } else if (kind === 'lamp') { for (let yy = y; yy < y + 3; yy++) setR('oak_fence', x, yy, z); setR('planks', x, y + 3, z); setR('torch', x, y + 4, z); }
    else if (kind === 'village') { // a well, dirt paths in four directions, houses facing the paths, farms, lamp posts
      const n = op.houses ?? 6, L = op.size ?? 18;
      { // level the village ground: flat within the village, blending back into the natural terrain over 6 blocks
        const R0 = L + 7, top = grid.get(K(x, y - 1, z)) || 'grass';
        for (let dx = -R0 - 6; dx <= R0 + 6; dx++) for (let dz = -R0 - 6; dz <= R0 + 6; dz++) {
          const dist = Math.max(Math.abs(dx), Math.abs(dz)); if (dist > R0 + 6) continue;
          const X = x + dx, Z = z + dz; const g = ground(X, Z, y + 40); const k = Math.min(1, Math.max(0, (dist - R0) / 6)); const target = Math.round(y + (g - y) * k * k * (3 - 2 * k));
          if (g === target) continue;
          for (let yy = Math.min(g, target) - 1; yy < Math.max(g, target) + 8; yy++) { const b = grid.get(K(X, yy, Z)); if (b && /log|leaves|planks|cobble|glass|door|stairs|slab/.test(b)) continue; if (yy >= target) set('air', X, yy, Z); else if (yy === target - 1) set(top === 'dirt_path' ? 'grass' : top, X, yy, Z); else set('dirt', X, yy, Z); }
        }
      }
      structure({ structure: 'well', pos: [x, y, z], foundation: op.foundation });
      for (const [ux, uz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) for (let i = 3; i <= L; i++) for (const w of [-1, 0, 1]) {
        const X = x + ux * i + (uz ? w : 0), Z = z + uz * i + (ux ? w : 0); const g = ground(X, Z); const top = grid.get(K(X, g - 1, Z));
        if (top && !/water|log|planks|cobble/.test(top)) { set('dirt', X, g - 1, Z); set('dirt_path', X, g - 1, Z); }
      }
      const spots = []; for (const [ux, uz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) for (const along of [7, 16]) for (const sd of [1, -1]) spots.push([ux, uz, along, sd]); // 9 apart: a 7-wide house plus a gap
      let built = 0; const rv = mulberry((op.seed ?? 1) * 31 + 7);
      for (const [ux, uz, along, sd] of spots.sort(() => rv() - 0.5)) {
        if (built >= n + (op.farms ?? 2)) break;
        const off = 6; const X = x + ux * along + (uz ? sd * off : 0), Z = z + uz * along + (ux ? sd * off : 0);
        // the door faces the path: the path is on the -sd side across the street
        const face = ux ? (sd > 0 ? 'north' : 'south') : (sd > 0 ? 'west' : 'east');
        if (built < n) structure({ structure: 'house', pos: [X, null, Z], face, seed: built, foundation: op.foundation });
        else structure({ structure: 'farm', pos: [X, null, Z], face, seed: built });
        built++;
      }
      for (const [ux, uz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) structure({ structure: 'lamp', pos: [x + ux * 4 + (uz ? 2 : 0), null, z + uz * 4 + (ux ? 2 : 0)] });
    }
    else if (kind === 'campfire') { for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) setR('cobblestone_slab', x + dx, y, z + dz); setR('log:x', x, y, z); setR('fire', x, y + 1, z); }
  };

  for (const op of ops || []) {
    if (op.fill) { const [b, p, r] = op.fill; for (const x of range(p[0], r[0])) for (const y of range(p[1], r[1])) for (const z of range(p[2], r[2])) set(b, x, y, z); }
    else if (op.set) { const [b, p] = op.set; set(b, p[0], p[1] ?? ground(p[0], p[2]), p[2]); }
    else if (op.hollow) { const [b, p, r] = op.hollow; const [x0, x1, y0, y1, z0, z1] = [Math.min(p[0], r[0]), Math.max(p[0], r[0]), Math.min(p[1], r[1]), Math.max(p[1], r[1]), Math.min(p[2], r[2]), Math.max(p[2], r[2])];
      for (const x of range(x0, x1)) for (const y of range(y0, y1)) for (const z of range(z0, z1)) if (x === x0 || x === x1 || y === y0 || y === y1 || z === z0 || z === z1) set(b, x, y, z); }
    else if (op.tree) { const [x, y, z] = op.tree; tree(x, y, z, op.kind || 'oak', op.height, mulberry(x * 31 + z * 17 + seed0)); }
    else if (op.sphere) { const [b, c, r] = op.sphere; const R = Math.ceil(r);
      for (let dx = -R; dx <= R; dx++) for (let dy = -R; dy <= R; dy++) for (let dz = -R; dz <= R; dz++) { const d = Math.hypot(dx, dy, dz); if (d > r + 0.5) continue; if (op.half && dy < 0) continue; if (op.hollow && d < r - 0.5) continue; set(b, c[0] + dx, c[1] + dy, c[2] + dz); } }
    else if (op.cylinder) { const [b, c, r, h] = op.cylinder; const R = Math.ceil(r);
      for (let dx = -R; dx <= R; dx++) for (let dz = -R; dz <= R; dz++) { const d = Math.hypot(dx, dz); if (d > r + 0.5 || (op.hollow && d < r - 0.5)) continue; for (let yy = 0; yy < h; yy++) set(b, c[0] + dx, c[1] + yy, c[2] + dz); } }
    else if (op.terrain) {
      const T = op.terrain; const B = { ...BIOMES[T.biome || 'plains'], ...T }; const s = T.seed ?? seed0;
      const [cx, cz] = T.center || [0, 0]; const R = T.radius ?? 40; const base = T.base ?? 4, amp = T.amp ?? 3, sc = T.scale ?? 16; const wl = T.water ?? null;
      const flat = T.flat; const depth = T.depth ?? 3; const bottom = Math.floor(T.bottom ?? Math.min(base - amp - depth - 1, (flat?.y ?? base) - depth - 2));
      const H = new Map();
      for (let x = cx - R; x <= cx + R; x++) for (let z = cz - R; z <= cz + R; z++) {
        if (T.round !== false && Math.hypot(x - cx, z - cz) > R + 0.5) continue;
        let h = base + (fbm(x / sc, z / sc, s) - 0.5) * 2 * amp;
        if (flat) { const d = Math.hypot(x - flat.center[0], z - flat.center[1]); const k = smooth(Math.min(1, Math.max(0, (d - flat.radius) / (flat.blend ?? 5)))); h = flat.y + (h - flat.y) * k; }
        h = Math.round(h); H.set(`${x},${z}`, h);
        const shore = wl !== null && h <= wl; const top = shore ? B.shore : B.top;
        for (let y = bottom; y <= h; y++) set(y === h ? top : y >= h - depth ? (shore ? B.shore : B.soil) : B.stone, x, y, z);
        if (wl !== null) for (let y = h + 1; y <= wl; y++) set(B.liquid || 'water', x, y, z);
      }
      const rng = mulberry(s * 4049 + 7); const trees = []; const td = T.trees ?? B.trees ?? 0.015;
      const inFlat = (x, z, m = 0) => flat && Math.hypot(x - flat.center[0], z - flat.center[1]) < flat.radius + m;
      const keep = T.clear || []; // [[x,z,r], ...] areas kept free of trees and plants (paths, sets)
      const kept = (x, z, m = 0) => keep.some(([kx, kz, kr]) => Math.hypot(x - kx, z - kz) < kr + m) || sites.some((f) => Math.hypot(x - f.x, z - f.z) < f.r + m);
      for (const [k, h] of H) {
        const [x, z] = k.split(',').map(Number); const top = grid.get(K(x, h, z)); if (top !== B.top || (wl !== null && h <= wl)) continue;
        const r = rng();
        if ((B.treeKinds || []).length && r < td && !inFlat(x, z, 3) && !kept(x, z, 3) && Math.hypot(x - cx, z - cz) < R - 2 && !trees.some(([a, b]) => Math.hypot(a - x, b - z) < 4)) {
          trees.push([x, z]); tree(x, h + 1, z, B.treeKinds[Math.floor(rng() * B.treeKinds.length)], undefined, rng); continue;
        }
        if (inFlat(x, z, 1) && !T.arenaPlants) continue; if (kept(x, z)) continue; // the arena stays clear unless asked
        const pr = rng();
        if ((B.flowers || []).length && pr < (T.flowers ?? 0.02)) setIfAir(B.flowers[Math.floor(rng() * B.flowers.length)], x, h + 1, z);
        else if ((B.plants || []).length && pr < (T.flowers ?? 0.02) + (T.plants ?? B.plantsDensity ?? 0.07)) setIfAir(B.plants[Math.floor(rng() * B.plants.length)], x, h + 1, z);
      }
      if (T.ores) { // ores in the stone layer, rarer and deeper like the game (visible in caves, tunnels and craters)
        for (const [k, b0] of [...grid]) { if (b0 !== B.stone || B.stone !== 'stone') continue; const [x, y, z] = k.split(',').map(Number); const r = rng(); const depth = (H.get(`${x},${z}`) ?? y) - y;
          if (r < 0.015) set('coal_ore', x, y, z); else if (r < 0.023) set('iron_ore', x, y, z); else if (r < 0.025 && depth > 6) set('gold_ore', x, y, z); else if (r < 0.026 && depth > 9) set('diamond_ore', x, y, z); }
      }
      for (let c = 0; c < (T.caves ?? 0); c++) { // cave worms: winding tubes under the surface, some breaking out to daylight
        let px = cx + (rng() - 0.5) * R * 1.4, pz = cz + (rng() - 0.5) * R * 1.4; if (flat && Math.hypot(px - flat.center[0], pz - flat.center[1]) < flat.radius + 4) continue;
        let py = (H.get(`${Math.round(px)},${Math.round(pz)}`) ?? base) - 2 - rng() * 4; let yaw = rng() * Math.PI * 2, pitch = (rng() - 0.6) * 0.5; const pts = [[px, py, pz]];
        for (let i = 0; i < 16 + rng() * 20; i++) { yaw += (rng() - 0.5) * 0.9; pitch = Math.max(-0.5, Math.min(0.4, pitch + (rng() - 0.5) * 0.3)); px += Math.cos(yaw) * 1.6; pz += Math.sin(yaw) * 1.6; py = Math.max(bottom + 2, py + pitch); pts.push([px, py, pz]); }
        carve(pts, 1.3 + rng() * 1.0, null, rng);
      }
    }
    else if (op.tunnel) { // { "tunnel": [[x,y,z], ...], "radius": 1.6, "floor": "gravel", "torches": 6 }
      const pts = op.tunnel; carve(pts, op.radius ?? 1.6, op.floor, null);
      if (op.torches) { let acc = 0; for (let i = 1; i < pts.length; i++) { const [a, b] = [pts[i - 1], pts[i]]; const L = Math.hypot(b[0] - a[0], b[2] - a[2]);
        for (let d = 0; d < L; d += 1) { if ((acc++) % op.torches) continue; const u = d / L; const X = Math.round(a[0] + (b[0] - a[0]) * u), Z = Math.round(a[2] + (b[2] - a[2]) * u); const g = ground(X, Z, Math.round(a[1] + (b[1] - a[1]) * u) + 1);
          if (!grid.has(K(X, g, Z))) set('torch', X, g, Z); } } }
    }
    else if (op.scatter) { const [b, p, q] = op.scatter; const rng = mulberry((op.seed ?? 3) * 131 + seed0); const on = op.on;
      for (const x of range(p[0], q[0])) for (const z of range(p[1], q[1])) { if (rng() >= (op.density ?? 0.15)) continue; const g = ground(x, z); const under = grid.get(K(x, g - 1, z)); if (on && !on.includes(under)) continue; setIfAir(b, x, g, z); } }
    else if (op.structure) structure(op);
  }
  return grid;
}

// top of the highest collidable block in a column (feet height for something standing there)
export function groundHeight(grid, x, z, from = 160, passable = (b) => /tall_grass|flower|dead_bush|^fire|torch|mushroom|sapling|lantern|snow_layer|carpet|water|lava|poppy|dandelion|wheat|carrots|potatoes|beetroots|rail|ladder|vine|door/.test(b)) {
  const ix = Math.floor(x), iz = Math.floor(z);
  for (let y = from; y > -64; y--) { const b = grid.get(`${ix},${y},${iz}`); if (b && !passable(b)) return y + 1; }
  return 1;
}
