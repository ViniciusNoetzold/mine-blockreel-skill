// Pure checks for the world generator, the mesher (culling, light) and the v0.2 animation additions.
// Run: node tests/world_check.mjs  (exit code 1 on failure)
import { expandWorld, groundHeight, footprint, layoutWarnings } from '../core/engine/worldgen.js';
import { meshWorld, computeLight, resolveDef } from '../core/engine/mesher.js';
import { actorState, evalClip, hurtAt, CLIPS } from '../core/engine/anim.js';

let fails = 0;
const ok = (c, m) => { if (!c) { fails++; console.error('FAIL', m); } };
const defs = { stone: 'stone', glass: { all: 'glass', transparent: true }, leaves: { all: 'leaves', transparent: true }, water: { all: 'water', liquid: true, transparent: true },
  torch: { all: 'torch', shape: 'torch', light: 14 }, tall_grass: { all: 'tall_grass', shape: 'cross' }, glowstone: { all: 'glowstone', emissive: true, light: 15 } };
const defOf = (n) => resolveDef(defs, n);
const quads = (r) => [...r.groups.values()].reduce((a, g) => a + g.builder.n / 4, 0);

// --- mesher: hidden faces are never emitted
{
  const g = new Map(); for (let x = 0; x < 3; x++) for (let y = 0; y < 3; y++) for (let z = 0; z < 3; z++) g.set(`${x},${y},${z}`, 'stone');
  ok(quads(meshWorld(g, defOf)) === 54, `a 3x3x3 stone cube has 54 visible faces (got ${quads(meshWorld(g, defOf))})`);
  const w = new Map([['0,0,0', 'water'], ['1,0,0', 'water']]);
  ok(quads(meshWorld(w, defOf)) === 10 + 2, 'two water blocks share no inner face (10 faces + 2 surface undersides)');
  const lv = new Map([['0,0,0', 'leaves'], ['1,0,0', 'leaves']]);
  ok(quads(meshWorld(lv, defOf)) === 12, 'leaves keep their inner faces (fancy leaves)');
  const gl = new Map([['0,0,0', 'glass'], ['1,0,0', 'glass']]);
  ok(quads(meshWorld(gl, defOf)) === 10, 'glass panes do not show the face between them');
  const dyn = new Map([['0,0,0', 'stone'], ['1,0,0', 'stone']]);
  ok(quads(meshWorld(dyn, defOf, new Set(['1,0,0']))) === 6, 'a block that changes over time never hides a static face');
  const cr = new Map([['0,0,0', 'stone'], ['0,1,0', 'tall_grass']]);
  ok(quads(meshWorld(cr, defOf)) === 6 + 4, 'a plant is two double-sided quads and does not cull the block below');
}
// --- light: sky light from above, block light from a torch, darkness under a roof
{
  const g = new Map(); for (let x = -4; x <= 4; x++) for (let z = -4; z <= 4; z++) { g.set(`${x},0,${z}`, 'stone'); g.set(`${x},4,${z}`, 'stone'); }
  for (let y = 1; y <= 3; y++) for (let x = -4; x <= 4; x++) { g.set(`${x},${y},-4`, 'stone'); g.set(`${x},${y},4`, 'stone'); g.set(`-4,${y},${x}`, 'stone'); g.set(`4,${y},${x}`, 'stone'); }
  let L = computeLight(g, defOf);
  ok(L.at(0, 2, 0)[0] === 0, 'a sealed room has no sky light');
  ok(L.at(0, 6, 0)[0] === 15, 'above the roof there is full sky light');
  g.set('0,1,0', 'torch'); L = computeLight(g, defOf);
  ok(L.at(0, 2, 0)[1] === 13 && L.at(2, 1, 0)[1] === 12, 'torch light falls off by one per block');
}
// --- world generator: deterministic, buildings stand on clear ground, warnings for overlaps
{
  const ops = [{ structure: 'house', pos: [12, null, -6] }, { terrain: { radius: 30, flat: { center: [0, 0], radius: 7, y: 4 }, trees: 0.08, seed: 3 } }, { structure: 'tower', pos: [-14, null, -10] }];
  const a = expandWorld(ops, 3), b = expandWorld(ops, 3);
  ok(a.size === b.size && [...a].every(([k, v]) => b.get(k) === v), 'same ops, same world');
  ok(groundHeight(a, 0, 0) === 5, 'the arena is flat at y=4 (stand at 5)');
  let veg = 0;
  for (const op of ops.filter((o) => o.structure)) { const f = footprint(op); for (const [k, v] of a) { const [x, , z] = k.split(',').map(Number); if (Math.hypot(x - f.x, z - f.z) < f.r && /leaves|tall_grass|flower/.test(v)) veg++; } }
  ok(veg === 0, `no tree or plant grows inside a building site, even when the building is listed before the terrain (found ${veg})`);
  ok(layoutWarnings([{ terrain: { flat: { center: [0, 0], radius: 8 } } }, { structure: 'house', pos: [3, null, 0] }]).length === 1, 'a house in the arena is reported');
  ok(layoutWarnings(ops).length === 0, 'a sensible layout has no warnings');
}
// --- animation: new clips, hops, hurt tint, meta segments keep the clip
{
  for (const c of ['slash', 'overhead', 'thrust', 'guard', 'dodge', 'knockback', 'cast', 'summon', 'levitate', 'kneel', 'fall', 'getup', 'bow', 'celebrate', 'sneak', 'charge'])
    ok(typeof CLIPS[c] === 'function' && evalClip(c, 0.3, 1, 0.6, 0.3).rArm.length === 3, `clip ${c} exists`);
  const story = { timeline: [{ t: 1, actor: 'a', do: 'knockback', dur: 0.8, to: [3, 1, 0], arc: 0.5 }, { t: 2, actor: 'a', do: 'guard', dur: 2, hold: true }, { t: 2.5, actor: 'a', holding: 'iron_sword' }] };
  const a = { name: 'a', cfg: { pos: [0, 1, 0] } };
  ok(Math.abs(actorState(story, a, 1.4).jumpY - 0.5) < 1e-6, 'arc: the hop peaks at mid-move');
  ok(hurtAt(story, a, 1.1) > 0.7 && hurtAt(story, a, 1.6) === 0, 'red hurt tint for half a second after a hit');
  ok(actorState(story, a, 3).clip === 'guard', 'a holding-only entry does not interrupt the running clip');
}
// --- structures turn with "face"; villages keep houses apart; tunnels carve
{
  const base = [{ fill: ['grass', [-30, 0, -30], [30, 0, 30]] }];
  const south = expandWorld([...base, { structure: 'house', pos: [0, 1, 0] }]), east = expandWorld([...base, { structure: 'house', pos: [0, 1, 0], face: 'east' }]);
  ok(south.size === east.size && [...east.values()].some((b) => b === 'oak_stairs:north'), 'a house facing east has its blocks and stair orientations turned');
  const v = expandWorld([...base, { structure: 'village', pos: [0, 1, 0], houses: 6, farms: 2 }], 4);
  ok([...v.values()].filter((b) => b === 'dirt_path').length > 60 && [...v.values()].some((b) => b === 'wheat'), 'a village has paths and farms');
  const t = expandWorld([{ fill: ['stone', [0, 0, -3], [20, 6, 3]] }, { tunnel: [[1, 3, 0], [19, 3, 0]], radius: 1.5, floor: 'gravel', torches: 4 }]);
  ok(!t.has('10,3,0') && [...t.values()].includes('gravel') && [...t.values()].includes('torch'), 'a tunnel is carved, floored and lit');
}
// --- big worlds: a few hundred thousand blocks mesh in well under the old limits
{
  const t0 = Date.now(); const g = expandWorld([{ terrain: { radius: 80, round: false, base: 8, amp: 8, scale: 30, depth: 5, water: 5, trees: 0.01, seed: 2 } }], 2);
  const t1 = Date.now(); const r = meshWorld(g, (n) => resolveDef({ ...defs, grass: { top: 'grass_top', side: 'grass_side', bottom: 'dirt' } }, n)); const t2 = Date.now();
  ok(g.size > 300000, `big world has ${g.size} blocks`);
  ok(t2 - t1 < 6000, `light + mesh of ${g.size} blocks took ${t2 - t1} ms (budget 6 s)`);
  ok(new Set([...r.groups.values()].map((x) => x.chunk)).size > 9, 'the world is split in chunks');
}
if (fails) { console.error(`${fails} world check(s) failed`); process.exit(1); }
console.log('world ok');
