import { clamp01, ease } from './anim.js';
import { boxUV } from './geo.js';

const PX = 1 / 16;

// Original BlockReel model and 64x64 texture layout. The wolf faces +Z.
export function buildWolf(THREE, texture, cfg) {
  const root = new THREE.Group();
  const inner = new THREE.Group();
  const trunk = new THREE.Group();
  root.add(inner);
  inner.add(trunk);
  const mat = new THREE.MeshLambertMaterial({ map: texture, alphaTest: 0.5 });
  const box = (parent, size, uv, at) => {
    const mesh = new THREE.Mesh(boxUV(THREE, ...size, ...uv, 64, 64, 0, false), mat);
    mesh.position.set(...at.map((n) => n * PX));
    mesh.castShadow = true;
    parent.add(mesh);
    return mesh;
  };
  const joint = (parent, at) => {
    const group = new THREE.Group();
    group.position.set(...at.map((n) => n * PX));
    parent.add(group);
    return group;
  };
  box(trunk, [6, 6, 12], [0, 13], [0, 1, -1]);
  box(trunk, [8, 8, 6], [36, 12], [0, 2.25, 3.5]);
  if (cfg.parts?.includes('collar')) box(trunk, [8, 8, 1], [39, 43], [0, 2.25, 5]).scale.set(1.019, 1.019, 1);

  const head = joint(trunk, [0, 5, 6.75]);
  box(head, [6, 6, 5], [0, 0], [0, 1, 1.5]);
  box(head, [4, 2, 4], [24, 0], [0, -0.7, 5.5]);
  const jaw = joint(head, [0, -1.65, 3.6]);
  box(jaw, [4, 1, 4], [24, 7], [0, -0.35, 1.85]).scale.set(0.9, 1, 0.925);
  const ears = [-1, 1].map((side) => {
    const ear = joint(head, [side * 2, 3.75, 0.65]);
    box(ear, [2, 3, 1], [42, 0], [0, 1.2, 0]);
    return ear;
  });
  const tail = joint(trunk, [0, 2, -6.25]);
  box(tail, [2, 2, 7], [0, 33], [0, 0, -3.5]);
  const legs = [];
  for (const front of [true, false]) for (const side of [-1, 1]) {
    const height = front ? 7.7 : 7.2;
    const leg = joint(inner, [side * 2.4, height, front ? 4.6 : -5.4]);
    // The atlas has 8 pixels of leg fur. The hind legs use wider haunches.
    const width = front ? 2 : 3;
    const mesh = box(leg, [width, 8, width], front ? [38, 28] : [46, 28], [0, -height / 2, 0]);
    mesh.scale.y = height / 8;
    legs.push({ leg, height, front });
  }

  const scale = (cfg.scale ?? 1) * (cfg.baby ? 0.55 : 1);
  root.scale.setScalar(scale);
  trunk.position.y = 8 * PX;
  tail.rotation.x = 0.35;
  mat.emissiveMap = texture;
  return {
    root, head, headY: 19.45 * PX * scale, eyeY: 15.25 * PX * scale,
    eyeZ: 10.65 * PX * scale, footprint: { width: 0.235, back: -0.39, front: 0.69 },
    mats: [mat], flash: 0,
    update(state, time) {
      const { clip, ct, dur, seg } = state;
      const blend = seg?.blend ?? 0.18;
      const weight = blend > 0 && seg ? ease.smooth(clamp01(ct / blend)) *
        (seg.hold ? 1 : ease.smooth(clamp01((dur - ct) / blend))) : 1;
      const pace = clip === 'run' || clip === 'charge' ? 11 : clip === 'sneak' ? 5 : 7.6;
      const gait = /^(walk|run|charge|sneak)$/.test(clip) ? Math.sin(ct * pace * state.sp) * weight : 0;
      const run = pace === 11;
      const sit = clip === 'sit' ? weight : 0;
      const rest = clip === 'sleep' ? weight : 0;
      const bow = clip === 'play_bow' ? weight : 0;
      const jump = clip === 'jump' ? Math.sin(Math.PI * clamp01(ct / (dur || 0.6))) : 0;
      const bark = /^(bark|talk)$/.test(clip) ? Math.pow(Math.max(0, Math.sin(ct * 18)), 2) * weight : 0;
      const howl = clip === 'howl' ? weight : 0;
      const sniff = clip === 'sniff' ? weight : 0;
      const tilt = /^(head_tilt|curious)$/.test(clip) ? weight : 0;
      const wag = /^(wag|relief|celebrate)$/.test(clip) ? weight : 0;
      const afraid = /^(scared|whimper)$/.test(clip) ? weight : 0;
      const recoil = /^(hit|knockback)$/.test(clip) ? Math.sin(Math.PI * clamp01(ct / (dur || 0.5))) : 0;
      const fallen = /^(die|fall)$/.test(clip) ? ease.smooth(clamp01(ct / 0.5)) : 0;
      trunk.position.y = (8 + Math.abs(gait) * (run ? 0.72 : 0.38) + Math.sin(time * 3) * 0.1 - 2.4 * sit - 5.25 * rest - 1.65 * bow) * PX;
      trunk.rotation.set(-0.21 * sit + 0.32 * bow - 0.2 * jump - 0.23 * recoil, 0, Math.sin(ct * 20) * 0.11 * wag);
      inner.rotation.z = fallen * Math.PI / 2;
      inner.position.y = fallen * 4 * PX;
      for (const [i, { leg, height, front }] of legs.entries()) {
        const stride = (i === 0 || i === 3 ? gait : -gait) * (run ? 0.82 : 0.52);
        leg.position.y = (height - rest * 5.25 - (front ? bow * 3.5 : sit * 3.25)) * PX;
        leg.rotation.x = stride - (front ? 1.03 * bow : 1.13 * sit) + (front ? -0.89 : 0.89) * rest + (front ? -0.6 : 0.43) * jump;
      }
      head.rotation.set(0.03 * Math.sin(time * 2.1) + 0.56 * sniff + 0.08 * Math.sin(ct * 18) * sniff
        - 0.78 * howl - 0.19 * bark + 0.24 * afraid + 0.21 * rest - 0.1 * bow, 0.1 * Math.sin(time * 1.4) * (1 - Math.abs(gait)), 0.42 * tilt);
      jaw.rotation.x = 0.51 * bark + howl * (0.35 + 0.05 * Math.sin(ct * 11));
      for (const [i, ear] of ears.entries()) {
        ear.rotation.x = 0.05 * Math.sin(time * 5.1 + i) - 0.27 * afraid - 0.24 * rest;
        ear.rotation.z = (i === 0 ? 1 : -1) * (0.1 + 0.25 * afraid);
      }
      tail.rotation.set(0.35 + 0.35 * wag + 0.22 * howl - 0.65 * afraid - 0.3 * rest,
        Math.sin(time * 3.4) * 0.14 + Math.sin(ct * 15) * 0.48 * wag + 0.2 * gait, 0);
    },
  };
}
