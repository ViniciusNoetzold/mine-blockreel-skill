// Box-model mobs: creeper-, pig-, spider- and zombie-style rigs driven by a texture YOU provide.
// Layouts follow the standard 64x32 entity-texture convention (see docs/MOBS.md); the zombie uses the player skin layout.
// Use in story.json:  "actors": { "mob1": { "type": "creeper", "texture": "assets/mob.png", "pos": [0,1,0], "scale": 1 } }
const S = Math.sin;

function boxUV(THREE, w, h, d, u, v, TW, TH, grow = 0, px = 1 / 16) {
  const g = new THREE.BoxGeometry((w + grow * 2) * px, (h + grow * 2) * px, (d + grow * 2) * px);
  const f = (x, y) => [x / TW, 1 - y / TH]; const r = (x, y, ww, hh) => [f(x, y), f(x + ww, y), f(x, y + hh), f(x + ww, y + hh)];
  const faces = { top: r(u + d, v, w, d), bottom: r(u + d + w, v, w, d), right: r(u, v + d, d, h), front: r(u + d, v + d, w, h), left: r(u + d + w, v + d, d, h), back: r(u + 2 * d + w, v + d, w, h) };
  const uv = g.attributes.uv;
  ['left', 'right', 'top', 'bottom', 'front', 'back'].forEach((face, i) => faces[face].forEach((c, j) => uv.setXY(i * 4 + j, c[0], c[1])));
  uv.needsUpdate = true; return g;
}

export const MOB_TYPES = ['creeper', 'pig', 'spider'];

export function buildMob(THREE, type, tex, cfg) {
  const PX = 1 / 16; const TW = 64, TH = 32;
  const mat = new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.5 });
  const root = new THREE.Group(); const inner = new THREE.Group(); root.add(inner);
  const part = (parent, w, h, d, u, v, pos, center = [0, 0, 0]) => {
    const g = new THREE.Group(); g.position.set(pos[0] * PX, pos[1] * PX, pos[2] * PX);
    const m = new THREE.Mesh(boxUV(THREE, w, h, d, u, v, TW, TH), mat); m.position.set(center[0] * PX, center[1] * PX, center[2] * PX); m.castShadow = true; g.add(m); parent.add(g); return g;
  };
  const legs = []; let head, eyeY, headY, spiderLegs = null;
  if (type === 'creeper') {
    head = part(inner, 8, 8, 8, 0, 0, [0, 18, 0], [0, 4, 0]);
    part(inner, 8, 12, 4, 16, 16, [0, 12, 0]);
    for (const [x, z] of [[2, 4], [-2, 4], [2, -4], [-2, -4]]) legs.push(part(inner, 4, 6, 4, 0, 16, [x, 6, z], [0, -3, 0]));
    eyeY = 1.4; headY = 1.7;
  } else if (type === 'pig') {
    head = part(inner, 8, 8, 8, 0, 0, [0, 12, 6], [0, 0, 4]);
    const snout = new THREE.Mesh(boxUV(THREE, 4, 3, 1, 16, 16, TW, TH), mat); snout.position.set(0, -1.5 * PX, 8.5 * PX + 4 * PX - 4 * PX + 0.5 * PX); head.add(snout);
    const body = new THREE.Mesh(boxUV(THREE, 10, 16, 8, 28, 8, TW, TH), mat); body.rotation.x = -Math.PI / 2; body.position.set(0, 10 * PX, -1 * PX); body.castShadow = true; inner.add(body);
    for (const [x, z] of [[3, 7], [-3, 7], [3, -5], [-3, -5]]) legs.push(part(inner, 4, 6, 4, 0, 16, [x, 6, z], [0, -3, 0]));
    eyeY = 0.8; headY = 1.0;
  } else if (type === 'spider') {
    part(inner, 6, 6, 6, 0, 0, [0, 9, 0]);
    head = part(inner, 8, 8, 8, 32, 4, [0, 9, 7]);
    part(inner, 10, 8, 12, 0, 12, [0, 9, -9]);
    spiderLegs = [];
    const zs = [3, 1, -1, -3], fan = [0.7, 0.3, -0.3, -0.7];
    for (let i = 0; i < 4; i++) for (const side of [1, -1]) {
      const g = new THREE.Group(); g.position.set(side * 4 * PX, 9 * PX, zs[i] * PX);
      const m = new THREE.Mesh(boxUV(THREE, 16, 2, 2, 18, 0, TW, TH), mat); m.position.set(side * 8 * PX, 0, 0); m.castShadow = true; g.add(m);
      g.rotation.y = side * fan[i]; g.rotation.z = side * -0.75; g.userData = { side, i }; inner.add(g); spiderLegs.push(g);
    }
    eyeY = 0.7; headY = 0.9;
  } else throw new Error('unknown mob type: ' + type);
  const sc = cfg.scale ?? 1; root.scale.setScalar(sc);
  if (cfg.nametag) { /* name tags: use the actor nametag from engine.js */ }
  return {
    root, head, headY: headY * sc, eyeY: eyeY * sc,
    update(st, t) {
      const walking = st.clip === 'walk' || st.clip === 'run'; const sp = (st.sp || 1) * (st.clip === 'run' ? 1.5 : 1); const w = st.ct * 8 * sp;
      legs.forEach((l, i) => { l.rotation.x = walking ? S(w + (i === 0 || i === 3 ? 0 : Math.PI)) * 0.8 : 0; });
      if (spiderLegs) spiderLegs.forEach((g) => { const ph = w + g.userData.i * 0.9 + (g.userData.side > 0 ? 0 : Math.PI); g.rotation.z = g.userData.side * (-0.75 + (walking ? S(ph) * 0.25 : 0)); });
      head.rotation.set(walking ? 0 : S(t * 1.1) * 0.04, walking ? 0 : S(t * 0.7) * 0.15, 0);
      let k = 1, flash = 0; // "swell": the creeper-style pre-explosion inflate with white flashes
      if (st.clip === 'swell') { const u = Math.min(1, st.ct / (st.dur || 1.5)); k = 1 + 0.35 * u * u + 0.03 * S(st.ct * 50); flash = Math.floor(st.ct * (5 + 6 * u)) % 2 === 0 ? 1 : 0; }
      inner.scale.set(k, k, k); mat.color.setScalar(flash ? 2.6 : 1);
      if (st.clip === 'hit') { const u = Math.min(1, st.ct / (st.dur || 0.5)); inner.rotation.x = -0.35 * Math.sin(Math.PI * u); } else inner.rotation.x = 0;
      if (st.clip === 'die') { inner.rotation.z = Math.min(1, st.ct / 0.5) * Math.PI / 2; } else inner.rotation.z = 0;
    },
  };
}
