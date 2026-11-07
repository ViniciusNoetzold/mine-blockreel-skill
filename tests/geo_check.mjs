// The game-geometry mob builder (core/engine/geo.js) on small synthetic geometries: no network, no cache needed.
import * as THREE from 'three';
import { buildGeoModel } from '../core/engine/geo.js';
import { evaluate, animateEntity } from '../core/engine/molang.js';
let fails = 0; const ok = (c, m) => { if (!c) { fails++; console.error('FAIL', m); } };
const tex = new THREE.Texture();
const box = (g) => { g.root.updateMatrixWorld(true); return new THREE.Box3().setFromObject(g.root); };
// a sheep-like quadruped: the body lies down by bind_pose_rotation, the legs (children) stay upright
const sheep = { tw: 64, th: 32, bones: [
  { name: 'body', pivot: [0, 19, 2], bind_pose_rotation: [90, 0, 0], cubes: [{ origin: [-4, 13, -5], size: [8, 16, 6], uv: [28, 8] }] },
  { name: 'head', pivot: [0, 18, -8], cubes: [{ origin: [-3, 16, -14], size: [6, 6, 8], uv: [0, 0] }] },
  ...[[-3, 7], [3, 7], [-3, -5], [3, -5]].map(([x, z], i) => ({ name: `leg${i}`, parent: 'body', pivot: [x, 12, z], cubes: [{ origin: [x - 2, 0, z - 2], size: [4, 12, 4], uv: [0, 16] }] })),
] };
const m = buildGeoModel(THREE, sheep, tex, { type: 'sheep' }); const b = box(m);
ok(b.max.z - b.min.z > b.max.y - b.min.y - 0.3, 'the body lies down (longer than tall)');
ok(Math.abs(b.min.y) < 0.02, 'the feet stand on y = 0');
ok(b.max.z > 0.5, 'the head points to +z (actors face +z)');
// a cube rotated without a pivot turns about its own centre (pig v3 body)
const pig = { tw: 64, th: 64, bones: [{ name: 'body', pivot: [0, 0, 0], cubes: [{ origin: [-5, 2, -5], size: [10, 16, 8], uv: [28, 8], rotation: [90, 0, 0] }] }] };
const pb = box(buildGeoModel(THREE, pig, tex, {}));
ok(Math.abs((pb.min.y + pb.max.y) / 2 - 10 / 16) < 0.02 && pb.max.z - pb.min.z > 0.9, 'pivot-less cube rotation keeps its centre');
// neverRender hides a bone's own cubes, not its children (zombie waist -> body)
const zb = { tw: 64, th: 32, bones: [{ name: 'waist', pivot: [0, 12, 0], neverRender: true, cubes: [{ origin: [-9, 0, -9], size: [18, 1, 18], uv: [0, 0] }] },
  { name: 'body', parent: 'waist', pivot: [0, 24, 0], cubes: [{ origin: [-4, 12, -2], size: [8, 12, 4], uv: [16, 16] }] }] };
const zbb = box(buildGeoModel(THREE, zb, tex, {}));
ok(zbb.max.x - zbb.min.x < 0.6 && zbb.max.y > 1.4, 'children of a neverRender bone still render, its own cubes do not');
// optional equipment (saddle) is hidden unless asked for
const horse = { tw: 64, th: 64, bones: [{ name: 'body', pivot: [0, 0, 0], cubes: [{ origin: [-5, 0, -5], size: [10, 10, 10], uv: [0, 0] }] }, { name: 'saddle', parent: 'body', pivot: [0, 0, 0], cubes: [{ origin: [-6, 10, -6], size: [12, 2, 12], uv: [0, 0] }] }] };
ok(box(buildGeoModel(THREE, horse, tex, {})).max.y < 0.7 && box(buildGeoModel(THREE, horse, tex, { parts: ['saddle'] })).max.y > 0.7, 'saddle hidden by default, shown with parts');
// walking swings diagonal leg pairs
const walk = buildGeoModel(THREE, sheep, tex, {}); walk.update({ clip: 'walk', ct: 0.2, sp: 1 }, 0.2);
const l = (n) => walk.bones.get(n).rotation.x;
ok(Math.abs(l('leg0') - l('leg3')) < 1e-9 && Math.abs(l('leg0') + l('leg1')) < 1e-6 && Math.abs(l('leg0')) > 0.1, 'diagonal legs move together, sides opposite');
// Molang: the game's expression language (trigonometry in degrees, short aliases, ternaries, assignments, unknowns read 0)
const near = (a, b) => Math.abs(a - b) < 1e-6;
ok(near(evaluate('math.cos(query.anim_time * 38.17) * 80.0', { query: { anim_time: 0 } }), 80), 'molang cos in degrees');
ok(near(evaluate('q.is_baby ? 2 : 1', { query: { is_baby: 1 } }), 2) && near(evaluate('q.unknown_thing + 3', { query: {} }), 3), 'molang aliases, ternary, unknown queries');
const env = { query: { x: 2 }, variable: {}, temp: {}, context: {} }; evaluate('v.a = q.x * 3; v.b = v.a + 1;', env);
ok(near(env.variable.b, 7) && near(evaluate('math.clamp(v.b, 0, 5) ?? 1', env), 5), 'molang assignments, statements, math.clamp');
const gait = { anims: { walk: { anim_time_update: 'query.modified_distance_moved', loop: true, bones: { leg0: { rotation: ['math.cos(query.anim_time * 38.17) * 80.0', 0, 0] } } },
  setup: { bones: { body: { rotation: ['90 - this', 0, 0] } } }, sitting: { bones: { body: { position: [0, -5, 0] } } } }, animate: ['setup', 'walk', 'sitting'] };
const still = animateEntity(gait, { life_time: 1, modified_move_speed: 0, modified_distance_moved: 3 });
ok(near(still.get('leg0')?.rot[0] ?? 0, 0), 'a distance-driven gait fades out when the mob stands still');
const moving = animateEntity(gait, { life_time: 1, modified_move_speed: 0.5, modified_distance_moved: 0 });
ok(near(moving.get('leg0').rot[0], 40), 'the gait plays weighted by the move speed');
ok(near(moving.get('body').rot[0], 90) && near(moving.get('body').pos[1], 0), '`this` is what earlier animations added; situational ones (sitting) stay off');
ok(near(animateEntity(gait, { life_time: 1, is_sitting: 1 }).get('body').pos[1], -5), 'situational animations play when the clip asks');
const spikes = { absPos: true, bones: [{ name: 'spike', pivot: [0, 24, 0] }], anims: { s: { bones: { spike: { position: ['-this', '16 - this', '8 - this'] } } } }, animate: ['s'] };
ok(animateEntity(spikes, { life_time: 1 }).get('spike').pos.every((v, j) => near(v, [0, -8, 8][j])), 'legacy rigs: absolute pivots (guardian spikes)');
const kid = { anims: { baby_transform: { bones: { head: { scale: 2 } } }, baby_sit: { bones: { body: { position: [0, -3, 0] } } }, baby_walk: { bones: { leg0: { rotation: [10, 0, 0] } } } }, animate: ['baby_transform', 'baby_sit', 'baby_walk'] };
const kq = animateEntity(kid, { life_time: 1, is_baby: 1 });
ok(kq.get('head')?.scale === 2 && kq.get('leg0') && !kq.get('body'), 'babies play baby animations, but not baby_sit unless sitting');
ok(!animateEntity({ ...kid, nativeBaby: true }, { life_time: 1, is_baby: 1 }).get('head'), "the game's own baby model is not shrunk again");
ok(!animateEntity(kid, { life_time: 1 }).get('leg0'), 'adults skip baby animations');
if (fails) { console.error(`${fails} geo check(s) failed`); process.exit(1); }
console.log('geo ok');
