// Pure-math checks for core/engine/anim.js. Run: node tests/anim_check.mjs  (exit code 1 on failure)
import { ease, kf, worldTime, actorState, aimAngles, mixPose, evalClip, lookState, mulberry32, noise } from '../core/engine/anim.js';

let fails = 0;
const ok = (c, m) => { if (!c) { fails++; console.error('FAIL', m); } };
const near = (a, b, e = 1e-6) => Math.abs(a - b) <= e;

// easing endpoints and overshoot
for (const [n, f] of Object.entries(ease)) { ok(near(f(0), 0, 1e-3) && near(f(1), 1, 1e-3), `ease ${n} must go 0 -> 1`); }
ok(Math.max(...Array.from({ length: 101 }, (_, i) => ease.outBack(i / 100))) > 1.05, 'outBack overshoots');
ok(Math.min(...Array.from({ length: 101 }, (_, i) => ease.inBack(i / 100))) < -0.05, 'inBack anticipates (goes negative first)');

// keyframes
ok(near(kf(0.5, [[0, 0], [1, 10, 'linear']]), 5), 'kf linear midpoint');
ok(kf(0.5, [[0, [0, 0, 0]], [1, [2, 4, 6], 'linear']]).every((v, i) => near(v, [1, 2, 3][i])), 'kf vectors');

// time remap: identity outside windows, monotonic, net zero shift after the window
const st = { timeRemap: [{ t: 2, dur: 1.5, slow: 0.8 }] };
ok(near(worldTime(st, 1.5), 1.5), 'worldTime before window');
ok(near(worldTime(st, 3.5), 3.5), 'worldTime after window has no shift');
ok(worldTime(st, 2.75) < 2.75 - 0.05 || worldTime(st, 2.4) < 2.4, 'world lags inside the slow half');
let prev = -1; for (let t = 0; t <= 5; t += 0.01) { const w = worldTime(st, t); ok(w >= prev - 1e-9, 'worldTime monotonic'); prev = w; }

// actor timeline
const mk = (cfg, timeline) => ({ story: { timeline }, a: { name: 'a', cfg } });
{
  const { story, a } = mk({ pos: [0, 1, 0], face: 0 }, [{ t: 1, actor: 'a', do: 'walk', to: [4, 1, 0], dur: 2 }, { t: 3, actor: 'a', do: 'wave', dur: 1 }]);
  const s0 = actorState(story, a, 0.5), s1 = actorState(story, a, 2), s2 = actorState(story, a, 3.5);
  ok(near(s0.pos[0], 0), 'before the walk the actor stays put');
  ok(near(s1.pos[0], 2), 'halfway through a linear walk');
  ok(near(s2.pos[0], 4), 'after the walk the actor stays at the destination');
  ok(near(s1.heading, Math.PI / 2, 1e-3), 'walking toward +x sets heading to +90 degrees');
  // blend: no pop at a clip change (pose continuity across t=3)
  const before = actorState(story, a, 3 - 1e-3).pose, at = actorState(story, a, 3 + 1e-3).pose;
  const d = Math.max(...['rArm', 'lArm', 'rLeg', 'lLeg', 'head'].map((k) => Math.max(...before[k].map((v, i) => Math.abs(v - at[k][i])))));
  ok(d < 0.15, `pose must be continuous at a clip change (jump ${d.toFixed(3)})`);
}
{ // shortest-arc turn: from 170 to -170 degrees goes through 180, not through 0
  const { story, a } = mk({ pos: [0, 1, 0], face: 170 }, [{ t: 1, actor: 'a', face: -170, turn: 1 }]);
  const mid = actorState(story, a, 1.5).heading; const deg = ((mid * 180 / Math.PI) % 360 + 360) % 360;
  ok(deg > 175 && deg < 185, `turn takes the short way (got ${deg.toFixed(1)} deg)`);
}
{ // face another actor: uses its actual position at that time
  const ctx = { posOf: () => [5, 1, 0] };
  const { story, a } = mk({ pos: [0, 1, 0], face: 0 }, [{ t: 0, actor: 'a', face: 'b', turn: 0 }]);
  ok(near(actorState(story, a, 1, ctx).heading, Math.PI / 2, 1e-6), 'facing actor b at +x');
}

// anticipation and overshoot are really in the swing clip
{
  const arm = (u) => evalClip('swing', u * 0.8, 1, 0.8, 0).rArm[0];
  ok(arm(0.28) < -2.5, 'swing winds up (arm goes back/up)');
  ok(arm(0.42) > arm(0.28) + 2, 'swing strikes fast after the wind-up');
  ok(arm(0.52) > 0.1, 'swing overshoots past the rest pose');
  ok(Math.abs(arm(1) - -0.1) < 0.05, 'swing settles');
}

// Expressive clips move, settle, and are safe to sample out of order.
{
  const keys = ['head', 'rArm', 'lArm', 'rLeg', 'lLeg', 'body'];
  const delta = (a, b) => Math.max(...keys.flatMap((key) => a[key].map((v, i) => Math.abs(v - b[key][i]))));
  for (const name of ['nod', 'shake_head', 'shrug', 'flinch', 'relief', 'salute', 'laugh', 'inspect']) {
    const at = (t) => evalClip(name, t, 1, 1, 0);
    const rest = at(0);
    const middle = at(0.3);
    ok(Math.max(...[0.2, 0.4, 0.6].map((t) => delta(rest, at(t)))) > 0.12, name + ' has a readable pose');
    ok(delta(rest, at(1)) < 1e-6, name + ' settles');
    ok(delta(middle, at(0.3)) === 0, name + ' evaluates deterministically');
  }
  const { story, a } = mk({}, [
    { t: 0, actor: 'a', do: 'walk', dur: 1 },
    { t: 1, actor: 'a', do: 'wave', dur: 0.05, blend: 0.4 },
    { t: 1.05, actor: 'a', do: 'flinch', dur: 0.8, blend: 0.3 },
  ]);
  const before = actorState(story, a, 1.05 - 1e-4).pose;
  const after = actorState(story, a, 1.05 + 1e-4).pose;
  ok(delta(before, after) < 0.005, 'interrupting a crossfade preserves the visible pose');
  const idle = evalClip('idle', 0, 1, 0, 0);
  ok(idle.rArm[2] < 0 && idle.lArm[2] > 0, 'resting arms angle outward from the torso');
}

// look-at angles
{
  const [pitch, yaw] = aimAngles([0, 1, 0], 0, 1.6, [5, 2.6, 0]); // target at +x while facing +z => turn right
  ok(near(yaw, Math.PI / 2, 1e-6) || near(yaw, 1.2, 1e-6), 'look-at yaw toward +x');
  const [pu] = aimAngles([0, 1, 0], 0, 1.6, [0, 6, 3]); ok(pu < 0, 'looking up gives a negative pitch');
  const [pd] = aimAngles([0, 1, 0], 0, 1.6, [0, 0, 3]); ok(pd > 0, 'looking down gives a positive pitch');
  const story = { timeline: [{ t: 1, actor: 'a', lookAt: 'b' }, { t: 3, actor: 'a', lookAt: null }] };
  const a = { name: 'a' };
  ok(lookState(story, a, 0.5) === null, 'no look-at before the first entry');
  ok(lookState(story, a, 1.2).target === 'b' && lookState(story, a, 4).target === null, 'look-at can be released with null');
}

// determinism
{ const r1 = mulberry32(42), r2 = mulberry32(42); ok(r1() === r2() && r1() === r2(), 'seeded PRNG is repeatable');
  ok(noise(1.234, 3) === noise(1.234, 3) && Math.abs(noise(9, 1)) <= 1, 'noise is pure and bounded'); }
ok(mixPose({ a: [0, 0, 0], b: 0 }, { a: [2, 2, 2], b: 4 }, 0.5).b === 2, 'mixPose blends numbers and vectors');

if (fails) { console.error(`${fails} failure(s)`); process.exit(1); }
console.log('anim ok');
