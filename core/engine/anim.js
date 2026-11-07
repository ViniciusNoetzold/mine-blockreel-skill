// BlockReel animation core. Pure functions of time (no Three.js): easing, clip library, pose blending,
// timeline evaluation and look-at angles. Every result depends only on (story, actor, t).

const PI = Math.PI;
const S = Math.sin;
export const clamp01 = (u) => Math.max(0, Math.min(1, u));
const mix = (a, b, u) => a + (b - a) * u;
const Z = [0, 0, 0];

// ------------------------------------------------------------------ easing ----
export const ease = {
  linear: (u) => u,
  smooth: (u) => u * u * (3 - 2 * u),
  inOut: (u) => u * u * (3 - 2 * u),
  in: (u) => u * u,
  out: (u) => 1 - (1 - u) * (1 - u),
  inCubic: (u) => u * u * u,
  outCubic: (u) => 1 - Math.pow(1 - u, 3),
  inBack: (u) => 2.70158 * u * u * u - 1.70158 * u * u, // pulls back first (anticipation)
  outBack: (u) => { const v = u - 1; return 1 + 2.70158 * v * v * v + 1.70158 * v * v; }, // overshoots then settles
  inOutBack: (u) => { const c = 1.70158 * 1.525; return u < 0.5 ? (Math.pow(2 * u, 2) * ((c + 1) * 2 * u - c)) / 2 : (Math.pow(2 * u - 2, 2) * ((c + 1) * (u * 2 - 2) + c) + 2) / 2; },
  outElastic: (u) => (u === 0 || u === 1 ? u : Math.pow(2, -10 * u) * S((u * 10 - 0.75) * (2 * PI / 3)) + 1),
  outBounce: (u) => { const n = 7.5625, d = 2.75; if (u < 1 / d) return n * u * u; if (u < 2 / d) { u -= 1.5 / d; return n * u * u + 0.75; } if (u < 2.5 / d) { u -= 2.25 / d; return n * u * u + 0.9375; } u -= 2.625 / d; return n * u * u + 0.984375; },
};
export const getEase = (name) => ease[name] || ease.linear;
export const lerp3 = (a, b, u) => a.map((v, i) => v + (b[i] - v) * u);

// Keyframes: kf(u, [[u0, value, ease?], ...]) with number or array values. The ease belongs to the segment ENDING at that key.
export function kf(u, frames) {
  if (u <= frames[0][0]) return frames[0][1];
  for (let i = 1; i < frames.length; i++) {
    if (u <= frames[i][0]) {
      const [u0, v0] = frames[i - 1]; const [u1, v1, e] = frames[i];
      const k = getEase(e || 'smooth')((u - u0) / (u1 - u0 || 1));
      return Array.isArray(v0) ? v0.map((x, j) => mix(x, v1[j], k)) : mix(v0, v1, k);
    }
  }
  return frames[frames.length - 1][1];
}

// -------------------------------------------------------------------- clips ----
// A clip is (clipTime, speed, segmentDuration) -> partial pose. Rotations are radians [x, y, z].
// Pose keys: head rArm lArm rLeg lLeg body (vec3) and bodyRx bob sink roll spinY (numbers).
export const CLIPS = {
  idle: (t) => ({ head: [S(t * 1.1) * 0.03, 0, 0], rArm: [0, 0, 0.04 + S(t * 1.5) * 0.03], lArm: [0, 0, -0.04 - S(t * 1.5) * 0.03], bodyRx: S(t * 1.6) * 0.012 }),
  walk: (t, sp = 1) => { const a = S(t * 8 * sp) * 0.9; return { rLeg: [a, 0, 0], lLeg: [-a, 0, 0], rArm: [-a, 0, 0], lArm: [a, 0, 0], bob: Math.abs(S(t * 8 * sp)) * 0.03, body: [0, S(t * 8 * sp) * 0.06, 0], head: [0, -S(t * 8 * sp) * 0.03, 0] }; },
  run: (t, sp = 1) => { const a = S(t * 12 * sp) * 1.25; return { rLeg: [a, 0, 0], lLeg: [-a, 0, 0], rArm: [-a * 1.1 - 0.2, 0, 0], lArm: [a * 1.1 - 0.2, 0, 0], bodyRx: 0.2, bob: Math.abs(S(t * 12 * sp)) * 0.08, body: [0, S(t * 12 * sp) * 0.1, 0], head: [-0.16, -S(t * 12 * sp) * 0.05, 0] }; },
  wave: (t) => ({ rArm: [-PI + 0.35, 0, S(t * 9) * 0.45], head: [0, 0, 0.05] }),
  talk: (t) => ({ head: [S(t * 13) * 0.07, S(t * 2.1) * 0.12, 0], rArm: [S(t * 2.1) * 0.05 - 0.08, 0, 0.06], lArm: [S(t * 3.3) * 0.25 - 0.4, 0, -0.1] }), // gestures with the free (left) hand, so a held sword stays low
  mine: (t) => ({ rArm: [-1.1 - Math.abs(S(t * 8)) * 1.0, 0, 0], body: [0, S(t * 8) * 0.08, 0], lArm: [0.1, 0, 0] }),
  punch: (t) => ({ rArm: [-1.55 + S(t * 14) * 0.7, 0, 0], lArm: [0.4, 0, 0.1] }),
  dance: (t) => ({ rArm: [-2.6 + S(t * 9) * 0.5, 0, 0.3], lArm: [-2.6 - S(t * 9) * 0.5, 0, -0.3], rLeg: [S(t * 9) * 0.5, 0, 0], lLeg: [-S(t * 9) * 0.5, 0, 0], head: [0, 0, S(t * 9) * 0.15], bob: Math.abs(S(t * 9)) * 0.12 }),
  sit: () => ({ rLeg: [-1.57, 0, 0], lLeg: [-1.57, 0, 0], rArm: [-0.5, 0, 0.1], lArm: [-0.5, 0, -0.1], sink: 0.62 }),
  look: (t) => ({ head: [0, S(t * 1.3) * 0.9, 0] }),
  scared: (t) => ({ rArm: [-2.2, 0, 0.5 + S(t * 25) * 0.05], lArm: [-2.2, 0, -0.5 - S(t * 25) * 0.05], head: [-0.15, S(t * 18) * 0.1, 0], rLeg: [S(t * 25) * 0.1, 0, 0], lLeg: [-S(t * 25) * 0.1, 0, 0] }),
  die: (t) => ({ roll: Math.min(1, t / 0.5) * PI / 2 }),
  spin: (t) => ({ spinY: t * 6, rArm: [0, 0, 1.2], lArm: [0, 0, -1.2] }),
  jump: () => ({ rArm: [-2.8, 0, 0.2], lArm: [-2.8, 0, -0.2], rLeg: [0.3, 0, 0], lLeg: [-0.3, 0, 0] }),

  // ---- one-shot clips with built-in anticipation, overshoot and follow-through (they stretch to the segment's dur) ----
  swing: (t, sp, dur) => { // wind-up -> fast strike -> overshoot -> settle
    const u = clamp01(t / (dur || 0.7));
    return {
      rArm: kf(u, [[0, [-0.1, 0, 0]], [0.28, [-3.0, 0, 0.1], 'out'], [0.42, [-0.45, 0, 0], 'in'], [0.52, [0.3, 0, 0], 'out'], [1, [-0.1, 0, 0]]]),
      lArm: kf(u, [[0, [0.1, 0, 0]], [0.28, [0.6, 0, 0.2]], [0.5, [-0.3, 0, 0]], [1, [0.1, 0, 0]]]),
      body: kf(u, [[0, Z], [0.28, [0, -0.45, 0], 'out'], [0.42, [0, 0.55, 0], 'in'], [0.62, [0, 0.2, 0]], [1, Z]]),
      bodyRx: kf(u, [[0, 0], [0.28, -0.18], [0.42, 0.28, 'in'], [0.6, 0.1], [1, 0]]),
      head: kf(u, [[0, Z], [0.28, [0, 0.25, 0]], [0.5, [0, -0.18, 0]], [1, Z]]),
    };
  },
  hit: (t, sp, dur) => { // knocked back by an impact: snap, stagger, recover
    const u = clamp01(t / (dur || 0.7));
    return {
      bodyRx: kf(u, [[0, 0], [0.1, 0.5, 'out'], [0.35, 0.3], [1, 0]]),
      head: kf(u, [[0, Z], [0.1, [-0.5, 0.2, 0.1], 'out'], [0.5, [-0.15, 0, 0]], [1, Z]]),
      rArm: kf(u, [[0, [0, 0, 0.05]], [0.1, [-0.7, 0, 0.9], 'out'], [0.6, [-0.2, 0, 0.3]], [1, [0, 0, 0.05]]]),
      lArm: kf(u, [[0, [0, 0, -0.05]], [0.1, [-0.7, 0, -0.9], 'out'], [0.6, [-0.2, 0, -0.3]], [1, [0, 0, -0.05]]]),
      rLeg: kf(u, [[0, Z], [0.1, [0.5, 0, 0]], [1, Z]]), lLeg: kf(u, [[0, Z], [0.1, [-0.3, 0, 0]], [1, Z]]),
      bob: kf(u, [[0, 0], [0.1, 0.05], [1, 0]]),
    };
  },
  stance: (t) => ({ sink: 0.32, bodyRx: 0.3, rLeg: [0, 0, -0.3], lLeg: [0, 0, 0.3], rArm: [-1.1, 0, 0.2], lArm: [-1.1, 0, -0.2], head: [-0.2 + S(t * 2) * 0.02, 0, 0] }),
  lunge: (t, sp, dur) => { // coil back, spring forward, overshoot, recover
    const u = clamp01(t / (dur || 0.8));
    return {
      bodyRx: kf(u, [[0, 0], [0.25, -0.22, 'out'], [0.5, 0.5, 'in'], [0.7, 0.35], [1, 0]]),
      rLeg: kf(u, [[0, Z], [0.25, [0.4, 0, 0]], [0.5, [-0.9, 0, 0]], [1, Z]]),
      lLeg: kf(u, [[0, Z], [0.25, [-0.3, 0, 0]], [0.5, [0.7, 0, 0]], [1, Z]]),
      rArm: kf(u, [[0, Z], [0.25, [0.5, 0, 0.2]], [0.5, [-1.6, 0, 0]], [1, Z]]),
      lArm: kf(u, [[0, Z], [0.25, [0.5, 0, -0.2]], [0.5, [0.3, 0, 0]], [1, Z]]),
      sink: kf(u, [[0, 0], [0.25, 0.2], [0.5, 0.05], [1, 0]]),
    };
  },
  shout: (t) => ({ head: [-0.4 + S(t * 40) * 0.02, S(t * 33) * 0.03, 0], rArm: [0.25, 0, 0.35], lArm: [0.25, 0, -0.35], bodyRx: 0.12 }),
  point: (t) => ({ rArm: [-1.57, 0, 0.05], head: [0, 0.2, 0], bodyRx: -0.04 }),
  raise: (t) => ({ rArm: [-3.0 + S(t * 2) * 0.05, 0, 0.1], lArm: [0.1, 0, -0.1], head: [-0.45, 0, 0], bodyRx: -0.05 }), // arm up (holding a torch aloft)
  // ---- combat and magic (v0.2). Sign conventions: arm x < 0 raises forward/up, rArm z > 0 swings across the body (toward +x),
  //      bodyRx > 0 leans forward, body[1] > 0 twists the chest to the character's left, pitch < 0 tips the whole body backward.
  slash: (t, sp, dur) => { // horizontal cut, right to left: wind back -> fast sweep -> overshoot -> settle
    const u = clamp01(t / (dur || 0.6));
    return {
      rArm: kf(u, [[0, [-1.1, 0, -0.1]], [0.3, [-1.55, 0, -1.35], 'out'], [0.47, [-1.5, 0, 0.95], 'in'], [0.6, [-1.35, 0, 1.2], 'out'], [1, [-0.5, 0, 0.1]]]),
      lArm: kf(u, [[0, Z], [0.3, [-0.7, 0, 0.35]], [0.5, [0.35, 0, -0.25]], [1, Z]]),
      body: kf(u, [[0, Z], [0.3, [0, -0.6, 0], 'out'], [0.47, [0, 0.55, 0], 'in'], [0.62, [0, 0.68, 0]], [1, Z]]),
      head: kf(u, [[0, Z], [0.3, [0, 0.35, 0]], [0.5, [0, -0.3, 0]], [1, Z]]),
      bodyRx: kf(u, [[0, 0], [0.3, -0.06], [0.47, 0.22, 'in'], [1, 0]]),
      rLeg: kf(u, [[0, Z], [0.4, [-0.3, 0, 0]], [1, Z]]), lLeg: kf(u, [[0, Z], [0.4, [0.3, 0, 0]], [1, Z]]),
      wrist: kf(u, [[0, 0], [0.3, 1.2], [0.6, 1.3], [1, 0]]),
    };
  },
  overhead: (t, sp, dur) => { // two-handed chop from above
    const u = clamp01(t / (dur || 0.7));
    return {
      rArm: kf(u, [[0, [-0.3, 0, 0]], [0.32, [-3.05, 0, 0.15], 'out'], [0.48, [-0.55, 0, 0.1], 'in'], [0.58, [-0.25, 0, 0.1], 'out'], [1, [-0.4, 0, 0]]]),
      lArm: kf(u, [[0, Z], [0.32, [-2.7, 0, -0.2], 'out'], [0.48, [-0.75, 0, -0.1], 'in'], [1, Z]]),
      bodyRx: kf(u, [[0, 0], [0.32, -0.28, 'out'], [0.48, 0.42, 'in'], [0.6, 0.32], [1, 0]]),
      head: kf(u, [[0, Z], [0.32, [0.2, 0, 0]], [0.48, [-0.35, 0, 0]], [1, Z]]),
      sink: kf(u, [[0, 0], [0.32, 0], [0.5, 0.16], [1, 0]]),
      rLeg: kf(u, [[0, Z], [0.48, [-0.35, 0, 0]], [1, Z]]), lLeg: kf(u, [[0, Z], [0.48, [0.35, 0, 0]], [1, Z]]),
    };
  },
  thrust: (t, sp, dur) => { // stab: chamber back, drive forward, hold, recover
    const u = clamp01(t / (dur || 0.55));
    return {
      rArm: kf(u, [[0, [-1.1, 0, 0]], [0.35, [-0.9, 0, -0.4], 'out'], [0.5, [-1.62, 0, 0.08], 'in'], [0.66, [-1.66, 0, 0.08]], [1, [-0.6, 0, 0]]]),
      lArm: kf(u, [[0, Z], [0.35, [-0.8, 0, 0.3]], [0.5, [0.45, 0, -0.1]], [1, Z]]),
      body: kf(u, [[0, Z], [0.35, [0, -0.5, 0], 'out'], [0.5, [0, 0.28, 0], 'in'], [1, Z]]),
      bodyRx: kf(u, [[0, 0], [0.35, -0.12], [0.5, 0.38, 'in'], [0.7, 0.3], [1, 0]]),
      head: kf(u, [[0, Z], [0.5, [-0.3, -0.2, 0]], [1, Z]]),
      rLeg: kf(u, [[0, Z], [0.5, [-0.55, 0, 0]], [1, Z]]), lLeg: kf(u, [[0, Z], [0.5, [0.5, 0, 0]], [1, Z]]), sink: kf(u, [[0, 0], [0.5, 0.12], [1, 0]]),
      wrist: kf(u, [[0, 0.3], [0.35, 1.9], [0.7, 2.05], [1, 0.3]]),
    };
  },
  guard: (t) => ({ rArm: [-1.95 + S(t * 3) * 0.04, 0, 0.6], lArm: [-1.25, 0, -0.35], bodyRx: 0.14, sink: 0.12, head: [-0.12, 0, 0], rLeg: [-0.25, 0, -0.12], lLeg: [0.25, 0, 0.12] }),
  block: (t) => CLIPS.guard(t),
  ready: (t) => ({ rArm: [-0.9 + S(t * 2.2) * 0.04, 0, 0.12], lArm: [-0.5, 0, -0.2], bodyRx: 0.12 + S(t * 2.2) * 0.02, sink: 0.08, head: [-0.1, 0, 0], rLeg: [-0.2, 0, -0.1], lLeg: [0.2, 0, 0.1] }),
  dodge: (t, sp, dur) => { // a quick sidestep lean (move the actor sideways with `to`); dir: lean to the actor's left by default
    const u = clamp01(t / (dur || 0.5));
    return { roll: kf(u, [[0, 0], [0.3, 0.32, 'out'], [0.7, 0.24], [1, 0]]), rArm: kf(u, [[0, Z], [0.3, [-0.6, 0, -0.7]], [1, Z]]), lArm: kf(u, [[0, Z], [0.3, [-0.3, 0, 0.6]], [1, Z]]),
      rLeg: kf(u, [[0, Z], [0.3, [0, 0, -0.35]], [1, Z]]), lLeg: kf(u, [[0, Z], [0.3, [0, 0, 0.2]], [1, Z]]), sink: kf(u, [[0, 0], [0.3, 0.12], [1, 0]]) };
  },
  knockback: (t, sp, dur) => { // a big hit that throws the actor back (pair with "to" and "arc")
    const u = clamp01(t / (dur || 0.8));
    return {
      pitch: kf(u, [[0, 0], [0.15, -0.42, 'out'], [0.65, -0.25], [1, 0]]),
      rArm: kf(u, [[0, Z], [0.15, [-1.3, 0, -0.9], 'out'], [0.7, [-0.4, 0, -0.3]], [1, Z]]), lArm: kf(u, [[0, Z], [0.15, [-1.3, 0, 0.9], 'out'], [0.7, [-0.4, 0, 0.3]], [1, Z]]),
      rLeg: kf(u, [[0, Z], [0.15, [-0.7, 0, 0]], [0.8, Z]]), lLeg: kf(u, [[0, Z], [0.15, [-0.2, 0, 0]], [0.8, Z]]),
      head: kf(u, [[0, Z], [0.12, [-0.45, 0.2, 0.1], 'out'], [0.6, [-0.1, 0, 0]], [1, Z]]),
    };
  },
  cast: (t) => ({ rArm: [-1.72 + S(t * 19) * 0.04, 0, 0.22], lArm: [-1.72 - S(t * 21) * 0.04, 0, -0.22], head: [-0.12, 0, 0], bodyRx: -0.08, rLeg: [-0.2, 0, 0], lLeg: [0.2, 0, 0] }),
  summon: (t, sp, dur) => { const u = clamp01(t / (dur || 1.2)); return { rArm: kf(u, [[0, [0, 0, -0.2]], [0.7, [-2.9, 0, -0.35], 'outCubic'], [1, [-2.95, 0, -0.35]]]), lArm: kf(u, [[0, [0, 0, 0.2]], [0.7, [-2.9, 0, 0.35], 'outCubic'], [1, [-2.95, 0, 0.35]]]), head: kf(u, [[0, Z], [0.7, [-0.5, 0, 0]], [1, [-0.55, 0, 0]]]), bodyRx: kf(u, [[0, 0], [0.7, -0.15], [1, -0.16]]) }; },
  levitate: (t) => ({ rArm: [-0.15 + S(t * 1.7) * 0.05, 0, -0.5], lArm: [-0.15 - S(t * 1.7) * 0.05, 0, 0.5], rLeg: [0.12 + S(t * 1.3) * 0.08, 0, -0.04], lLeg: [0.02 - S(t * 1.3) * 0.08, 0, 0.04], bob: 0.08 + S(t * 2.1) * 0.07, head: [0.12, 0, 0] }),
  kneel: () => ({ rLeg: [-1.4, 0, 0], lLeg: [0.55, 0, 0], sink: 0.4, bodyRx: 0.12, head: [-0.12, 0, 0], rArm: [-0.3, 0, 0.05], lArm: [0.1, 0, -0.05] }),
  fall: (t, sp, dur) => { // fall flat on the back (use "hold": true to stay down)
    const u = clamp01(t / (dur || 0.9));
    return { pitch: kf(u, [[0, 0], [0.75, -1.5708, 'in'], [0.86, -1.47, 'out'], [1, -1.5708, 'in']]), sink: kf(u, [[0, 0], [0.75, -0.12], [1, -0.12]]),
      rArm: kf(u, [[0, Z], [0.4, [-2.4, 0, -0.5]], [0.8, [-0.2, 0, -0.3]], [1, [0, 0, -0.25]]]), lArm: kf(u, [[0, Z], [0.4, [-2.4, 0, 0.5]], [0.8, [-0.2, 0, 0.3]], [1, [0, 0, 0.25]]]),
      rLeg: kf(u, [[0, Z], [0.4, [-0.5, 0, 0]], [1, [0, 0, -0.08]]]), lLeg: kf(u, [[0, Z], [0.4, [-0.2, 0, 0]], [1, [0, 0, 0.08]]]), head: kf(u, [[0, Z], [0.5, [0.4, 0, 0]], [1, [0.2, 0.3, 0]]]) };
  },
  getup: (t, sp, dur) => { const u = clamp01(t / (dur || 1.0)); return { pitch: kf(u, [[0, -1.5708], [0.25, -1.4], [0.75, -0.1, 'outCubic'], [1, 0]]), sink: kf(u, [[0, -0.12], [0.5, 0.25], [1, 0]]), rArm: kf(u, [[0, Z], [0.4, [0.6, 0, -0.3]], [1, Z]]), lArm: kf(u, [[0, Z], [0.4, [0.6, 0, 0.3]], [1, Z]]), rLeg: kf(u, [[0, Z], [0.5, [-1.0, 0, 0]], [1, Z]]) }; },
  bow: (t) => ({ rArm: [-1.57, -0.12, 0.08], lArm: [-1.52 + S(t * 25) * 0.015, 0.75, -0.2], head: [0, -0.1, 0], body: [0, 0.15, 0] }),
  throw: (t, sp, dur) => { const u = clamp01(t / (dur || 0.6)); return { rArm: kf(u, [[0, [0, 0, 0]], [0.4, [-2.9, 0, -0.3], 'out'], [0.55, [-1.3, 0, 0], 'in'], [1, [-0.3, 0, 0]]]), body: kf(u, [[0, Z], [0.4, [0, -0.5, 0]], [0.55, [0, 0.4, 0], 'in'], [1, Z]]), bodyRx: kf(u, [[0, 0], [0.4, -0.15], [0.55, 0.25], [1, 0]]), lArm: kf(u, [[0, Z], [0.4, [-1.2, 0, 0.2]], [0.6, [0.3, 0, 0]], [1, Z]]) }; },
  celebrate: (t) => ({ rArm: [-2.85 + S(t * 10) * 0.25, 0, -0.3], lArm: [-2.85 - S(t * 10) * 0.25, 0, 0.3], bob: Math.abs(S(t * 10)) * 0.07, head: [-0.2, 0, 0] }),
  sneak: (t, sp = 1) => { const a = S(t * 6 * sp) * 0.45; return { bodyRx: 0.5, rArm: [-0.4 - a * 0.5, 0, 0], lArm: [-0.4 + a * 0.5, 0, 0], rLeg: [a, 0, 0], lLeg: [-a, 0, 0], sink: 0.18, head: [-0.45, 0, 0] }; },
  crouch: () => ({ bodyRx: 0.5, rArm: [-0.4, 0, 0], lArm: [-0.4, 0, 0], sink: 0.18, head: [-0.45, 0, 0] }),
  charge: (t, sp = 1) => { const a = S(t * 12 * sp) * 1.2; return { rLeg: [a, 0, 0], lLeg: [-a, 0, 0], rArm: [-1.35 + S(t * 12 * sp) * 0.08, 0, 0.12], lArm: [a * 1.1 - 0.4, 0, 0], bodyRx: 0.32, bob: Math.abs(S(t * 12 * sp)) * 0.08, head: [-0.3, 0, 0] }; },
  stagger: (t) => ({ roll: S(t * 5) * 0.08, bodyRx: 0.2 + S(t * 3) * 0.06, head: [0.25, S(t * 4) * 0.2, 0], rArm: [-0.2, 0, -0.25 + S(t * 6) * 0.1], lArm: [-0.2, 0, 0.25 - S(t * 6) * 0.1] }),
  zombie: (t, sp = 1) => { const a = S(t * 6 * sp) * 0.55; return { rArm: [-1.5 + S(t * 3) * 0.06, 0, 0.05], lArm: [-1.5 - S(t * 3) * 0.06, 0, -0.05], rLeg: [a, 0, 0], lLeg: [-a, 0, 0], head: [0.08, S(t * 2) * 0.12, 0], bob: Math.abs(S(t * 6 * sp)) * 0.02 }; },
};

function basePose(idle) {
  return { head: Z, rArm: idle.rArm, lArm: idle.lArm, rLeg: Z, lLeg: Z, body: Z, bodyRx: 0, bob: 0, sink: 0, roll: 0, spinY: 0, pitch: 0, wrist: 0 };
}

export function evalClip(name, ct, sp, dur, tGlobal) {
  const idle = CLIPS.idle(tGlobal);
  const base = basePose(idle);
  if (name === 'idle') return { ...base, head: idle.head, bodyRx: idle.bodyRx };
  const p = (CLIPS[name] || CLIPS.idle)(ct, sp, dur);
  const out = { ...base };
  for (const k of Object.keys(p)) out[k] = p[k];
  return out;
}

export function mixPose(a, b, u) {
  const out = {};
  for (const k of Object.keys(a)) out[k] = Array.isArray(a[k]) ? lerp3(a[k], b[k], u) : mix(a[k], b[k], u);
  return out;
}

// -------------------------------------------------------------- timeline ----
const wrapPI = (a) => ((((a + PI) % (2 * PI)) + 2 * PI) % (2 * PI)) - PI;

function segsOf(story, a) {
  return a._segs || (a._segs = (story.timeline || []).filter((s) => s.actor === a.name).sort((x, y) => x.t - y.t));
}

// Which clip is playing at time t? { clip, ct, sp, dur, start, seg }. `start` = when this clip state began.
export function clipState(story, a, t) {
  let clip = 'idle', ct = t, sp = 1, dur = 0, start = 0, seg = null;
  for (const s of segsOf(story, a)) {
    if (s.t > t) break;
    if (!('do' in s) && !s.to && s.face === undefined) continue; // meta-only entries (lookAt, holding, hide/show, hurt) keep the current clip
    const d = s.dur ?? 0;
    if (t < s.t + d || s.hold) { clip = s.do || 'idle'; ct = t - s.t; sp = s.speed || 1; dur = d; start = s.t; seg = s; }
    else { clip = 'idle'; ct = t; sp = 1; dur = 0; start = s.t + d; seg = null; }
  }
  return { clip, ct, sp, dur, start, seg };
}

// Full actor state at time t: feet position, heading, jump offset, blended pose.
export function actorState(story, a, t, ctx = {}, depth = 0) {
  let pos = [...(a.cfg.pos || [0, 1, 0])];
  const heads = [{ t: -1e9, h: (a.cfg.face ?? 0) * PI / 180, turn: 0 }]; // heading events
  let jumpY = 0;
  for (const s of segsOf(story, a)) {
    if (s.t > t) break;
    const dur = s.dur ?? 0; const from = [...pos];
    if (s.to) {
      const u = dur > 0 ? Math.min(1, (t - s.t) / dur) : 1;
      pos = lerp3(from, s.to, getEase(s.ease || 'linear')(u));
      const dx = s.to[0] - from[0], dz = s.to[2] - from[2];
      if (s.face === undefined && (dx || dz)) heads.push({ t: s.t, h: Math.atan2(dx, dz), turn: s.turn ?? 0.15 });
    }
    if (s.face !== undefined) {
      let h;
      if (typeof s.face === 'number') h = s.face * PI / 180;
      else {
        let tp;
        if (Array.isArray(s.face)) tp = s.face;
        else if (ctx.posOf && depth < 2) tp = ctx.posOf(s.face, s.t, depth + 1);
        tp = tp || [0, 0, 0];
        h = Math.atan2(tp[0] - pos[0], tp[2] - pos[2]);
      }
      heads.push({ t: s.t, h, turn: s.turn ?? 0.15 });
    }
    if ((t < s.t + dur || s.hold) && s.do === 'jump') { const u = Math.min(1, (t - s.t) / (dur || 0.6)); jumpY = 4 * (s.height ?? 1.0) * u * (1 - u); }
    else if (s.arc && t < s.t + dur) { const u = Math.min(1, (t - s.t) / (dur || 0.6)); jumpY = 4 * s.arc * u * (1 - u); } // a hop along any move (knock-back, leap)
    if (s.to && t >= s.t + dur) pos = [...s.to];
  }
  // smooth turning: shortest arc from the previous heading over `turn` seconds
  let heading = heads[0].h;
  for (let i = 1; i < heads.length; i++) {
    const e = heads[i]; const prev = heading;
    if (t < e.t) break;
    const d = wrapPI(e.h - prev);
    const u = e.turn > 0 ? ease.smooth(clamp01((t - e.t) / e.turn)) : 1;
    heading = u >= 1 ? e.h : prev + d * u;
    if (u < 1) break;
  }
  // pose with a short blend from the previous clip state
  const cur = clipState(story, a, t);
  let pose = evalClip(cur.clip, cur.ct, cur.sp, cur.dur, t);
  const bl = cur.seg ? (cur.seg.blend ?? 0.15) : 0.2;
  if (cur.start > 0 && bl > 0 && t - cur.start < bl) {
    const before = cur.start - 1e-3;
    const prev = clipState(story, a, before);
    const prevPose = evalClip(prev.clip, prev.ct + (t - before), prev.sp, prev.dur, t);
    pose = mixPose(prevPose, pose, ease.smooth(clamp01((t - cur.start) / bl)));
  }
  // hide / show flags: { "t": 5, "actor": "x", "hide": true } removes the actor (e.g. a mob that exploded) until a later "show"
  let hidden = false; for (const s of segsOf(story, a)) { if (s.t > t) break; if (s.hide) hidden = true; if (s.show) hidden = false; if (s.do === 'die' && s.vanish && t >= s.t + (s.dur ?? 1)) hidden = true; }
  return { pos, heading, jumpY, pose, clip: cur.clip, ct: cur.ct, sp: cur.sp, dur: cur.dur, hidden, moving: cur.clip === 'walk' || cur.clip === 'run' };
}

// ------------------------------------------------------------- look-at ----
// "lookAt" entries on timeline segments: a target (actor name, [x,y,z], "camera") or null to release.
export function lookEntries(story, a) {
  return a._look || (a._look = (story.timeline || []).filter((s) => s.actor === a.name && 'lookAt' in s).sort((x, y) => x.t - y.t));
}
export function lookState(story, a, t) {
  const es = lookEntries(story, a); let i = -1;
  for (let k = 0; k < es.length; k++) if (es[k].t <= t) i = k;
  if (i < 0) return null;
  const e = es[i]; const prev = i > 0 ? es[i - 1].lookAt : null;
  return { target: e.lookAt, prev, w: ease.smooth(clamp01((t - e.t) / (e.blend ?? 0.3))), limit: e.limit };
}
// yaw/pitch (radians) a head must turn to face `target` given feet pos, heading and eye height
export function aimAngles(feet, heading, eyeY, target, limit = 1.2) {
  const dx = target[0] - feet[0], dz = target[2] - feet[2], dy = target[1] - (feet[1] + eyeY);
  const yaw = wrapPI(Math.atan2(dx, dz) - heading); const pitch = -Math.atan2(dy, Math.hypot(dx, dz));
  const c = (v, l) => Math.max(-l, Math.min(l, v));
  return [c(pitch, 0.7), c(yaw, limit)];
}

// ------------------------------------------------------------ time remap ----
// story.timeRemap: [{ t, dur, slow }]  A speed ramp: the world slows down then catches up inside the window, so the
// world time is unchanged outside every window (no authoring shift). v(u) = 1 - slow*sin(2*pi*u), slow in [0, 0.95].
export function worldTime(story, t) {
  let w = t;
  for (const r of story.timeRemap || []) {
    if (t <= r.t) continue;
    const dur = r.dur ?? 1, A = clamp01((r.slow ?? 0.7) / 0.95) * 0.95;
    const u = clamp01((t - r.t) / dur);
    w += dur * (-(A / (2 * PI)) * (1 - Math.cos(2 * PI * u)));
  }
  return w;
}

// ---------------------------------------------------------------- noise ----
// Deterministic smooth noise in [-1, 1] (sum of incommensurate sines), for handheld camera and secondary motion.
export function noise(t, seed = 0) {
  return (S(t * 1.31 + seed * 12.9) + S(t * 2.77 + seed * 78.2) * 0.6 + S(t * 5.13 + seed * 37.7) * 0.35) / 1.95;
}
export function mulberry32(a) {
  return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// ------------------------------------------------------------------- hurt ----
// Red damage tint like the game (about 0.5 s after a hit), held while dying. 0..1
export function hurtAt(story, a, t) {
  let h = 0;
  for (const s of segsOf(story, a)) {
    if (s.t > t) break;
    const k = t - s.t;
    if (s.do === 'hit' || s.do === 'knockback' || s.hurt) { if (k < 0.5) h = Math.max(h, 1 - k / 0.5); }
    if (s.do === 'die' && (k < (s.dur ?? 1) || s.hold)) h = Math.max(h, k < 1.0 ? 0.9 : Math.max(0, 0.9 - (k - 1.0)));
  }
  return h;
}
