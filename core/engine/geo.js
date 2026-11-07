// Any mob from the game's own geometry (Bedrock geometry, normalised by tools/vanilla.py mobs): bones with pivots and rotations,
// cubes with box or per-face UVs, inflate and mirror. Animated procedurally by bone names (legs, arms, wings, tail, head...),
// so a cow, a villager, a horse, a bat or the ender dragon all walk, look and react without hand-made rigs.
//
// Frames: Bedrock models face -Z; BlockReel actors face +Z, so every point is turned half a turn around Y: (x, y, z) -> (-x, y, -z).
const PX = 1 / 16;
const S = Math.sin;
const DEG = Math.PI / 180;

export function boxUV(THREE, w, h, d, u, v, TW, TH, grow, mirror) {
  const g = new THREE.BoxGeometry(Math.max(1e-3, (w + grow * 2) * PX), Math.max(1e-3, (h + grow * 2) * PX), Math.max(1e-3, (d + grow * 2) * PX));
  const f = (x, y) => [x / TW, 1 - y / TH];
  const r = (x, y, ww, hh, flip) => (flip ? [f(x + ww, y), f(x, y), f(x + ww, y + hh), f(x, y + hh)] : [f(x, y), f(x + ww, y), f(x, y + hh), f(x + ww, y + hh)]);
  // after the half turn the model's front (bedrock north) is +z: the same layout as the player skin boxes
  let faces = { top: r(u + d, v, w, d), bottom: r(u + d + w, v, w, d), right: r(u, v + d, d, h), front: r(u + d, v + d, w, h), left: r(u + d + w, v + d, d, h), back: r(u + 2 * d + w, v + d, w, h) };
  if (mirror) faces = { top: r(u + d, v, w, d, true), bottom: r(u + d + w, v, w, d, true), right: r(u + d + w, v + d, d, h, true), front: r(u + d, v + d, w, h, true), left: r(u, v + d, d, h, true), back: r(u + 2 * d + w, v + d, w, h, true) };
  const uv = g.attributes.uv; ['left', 'right', 'top', 'bottom', 'front', 'back'].forEach((face, i) => faces[face].forEach((c, j) => uv.setXY(i * 4 + j, c[0], c[1])));
  uv.needsUpdate = true; return g;
}

function faceUV(THREE, w, h, d, uvs, TW, TH, grow) {
  const g = new THREE.BoxGeometry(Math.max(1e-3, (w + grow * 2) * PX), Math.max(1e-3, (h + grow * 2) * PX), Math.max(1e-3, (d + grow * 2) * PX));
  const f = (x, y) => [x / TW, 1 - y / TH];
  const rect = (fc) => { if (!fc || !fc.uv) return null; const [x, y] = fc.uv; const [ww, hh] = fc.uv_size || [0, 0]; return [f(x, y), f(x + ww, y), f(x, y + hh), f(x + ww, y + hh)]; };
  // bedrock face names -> three faces after the half turn: north is the front (+z), east (the model's right) is -x
  const map = { left: uvs.west, right: uvs.east, top: uvs.up, bottom: uvs.down, front: uvs.north, back: uvs.south };
  const uv = g.attributes.uv; const hide = [];
  ['left', 'right', 'top', 'bottom', 'front', 'back'].forEach((face, i) => { const c = rect(map[face]); if (!c) { hide.push(i); for (let j = 0; j < 4; j++) uv.setXY(i * 4 + j, 0, 0); } else c.forEach((cc, j) => uv.setXY(i * 4 + j, cc[0], cc[1])); });
  if (hide.length) { const idx = g.index.array; const keep = []; for (let i = 0; i < 6; i++) if (!hide.includes(i)) for (let k = 0; k < 6; k++) keep.push(idx[i * 6 + k]); g.setIndex(keep); }
  uv.needsUpdate = true; return g;
}

// bedrock rotation [x, y, z] in degrees -> three Euler in our turned frame
const rot = (r) => (r ? [r[0] * DEG, -r[1] * DEG, -r[2] * DEG] : [0, 0, 0]);
const P = (p) => [-(p[0] || 0) * PX, (p[1] || 0) * PX, -(p[2] || 0) * PX];

export function buildGeoModel(THREE, geo, tex, cfg = {}) {
  const TW = geo.tw || 64, TH = geo.th || 64;
  const mat = new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.5, side: THREE.DoubleSide });
  const root = new THREE.Group(); const inner = new THREE.Group(); root.add(inner);
  const bones = new Map(); const byName = (n) => bones.get(String(n).toLowerCase());
  let minY = Infinity, maxY = -Infinity;
  for (const b of geo.bones) { // first pass: groups at their pivots (bones may be listed before their parents)
    const g = new THREE.Group(); g.name = b.name; g.userData = { pivot: P(b.pivot || [0, 0, 0]), rest: rot(b.rotation), bone: b };
    g.rotation.order = 'ZYX'; g.rotation.set(...g.userData.rest);
    bones.set(b.name.toLowerCase(), g);
  }
  for (const b of geo.bones) {
    const g = byName(b.name); const parent = b.parent ? byName(b.parent) : null;
    const pp = parent ? parent.userData.pivot : [0, 0, 0]; const pv = g.userData.pivot;
    g.position.set(pv[0] - pp[0], pv[1] - pp[1], pv[2] - pp[2]);
    (parent || inner).add(g);
    if (b.neverRender) continue; // hides this bone's own cubes only; its children still render
    // equipment the game shows only when equipped (saddle, saddlebags, chest, reins, armour, collar): hidden unless cfg.parts names it
    const optional = /saddle|bag|chest(?!plate)|rein|bridle|harness|armou?r|collar|leash|mouth_?ring|headpiece|noseband/i;
    if (optional.test(b.name) && !(cfg.parts || []).some((x) => new RegExp(x, 'i').test(b.name))) { g.visible = false; continue; }
    // legacy bind_pose_rotation turns the bone's own cubes (a sheep's body lies down), not its children (the legs stay upright)
    let host = g;
    if (b.bind_pose_rotation) { host = new THREE.Group(); host.rotation.order = 'ZYX'; host.rotation.set(...rot(b.bind_pose_rotation)); g.add(host); }
    for (const c of b.cubes || []) {
      const [w, h, d] = c.size; const o = c.origin; const grow = (c.inflate ?? b.inflate ?? 0);
      const mirror = c.mirror ?? b.mirror ?? false;
      const geom = Array.isArray(c.uv) || c.uv === undefined ? boxUV(THREE, w, h, d, (c.uv || [0, 0])[0], (c.uv || [0, 0])[1], TW, TH, grow, mirror) : faceUV(THREE, w, h, d, c.uv, TW, TH, grow);
      const m = new THREE.Mesh(geom, mat); m.castShadow = true;
      // cube centre in the turned frame, relative to the bone pivot
      const cx = -(o[0] + w / 2) * PX, cy = (o[1] + h / 2) * PX, cz = -(o[2] + d / 2) * PX;
      minY = Math.min(minY, o[1] * PX); maxY = Math.max(maxY, (o[1] + h) * PX);
      if (c.rotation) {
        const cp = P(c.pivot || [o[0] + w / 2, o[1] + h / 2, o[2] + d / 2]); const holder = new THREE.Group(); holder.rotation.order = 'ZYX'; // no pivot: the cube turns about its centre
        holder.position.set(cp[0] - pv[0], cp[1] - pv[1], cp[2] - pv[2]); holder.rotation.set(...rot(c.rotation));
        m.position.set(cx - cp[0], cy - cp[1], cz - cp[2]); holder.add(m); host.add(holder);
      } else { m.position.set(cx - pv[0], cy - pv[1], cz - pv[2]); host.add(m); }
    }
  }
  const sc = cfg.scale ?? 1; root.scale.setScalar(sc);
  // bone roles, by name and position (the game names them consistently: leg0..leg7, leftLeg, rightArm, wing0, tail...)
  const all = [...bones.values()].filter((g) => g.parent);
  const named = (re) => all.filter((g) => re.test(g.name));
  const head = byName('head') || named(/head/i)[0] || null;
  const legs = named(/leg/i).filter((g) => !/item/i.test(g.name) && !(g.parent && /leg/i.test(g.parent.name))); // roots only: lower segments follow
  const arms = named(/arm/i).filter((g) => !/armor|item/i.test(g.name));
  const wings = named(/wing/i).filter((g) => !/tip|outer/i.test(g.name));
  const tails = named(/tail/i); const tentacles = named(/tentacle|fin/i);
  const side = (g) => Math.sign(g.userData.pivot[0]) || 1; const front = (g) => g.userData.pivot[2] >= 0 ? 1 : -1;
  const undeadArms = /zombie|husk|drowned|pigman/i.test(cfg.type || '');
  const headY = Math.max(0.5, maxY) * sc, eyeY = (head ? head.userData.pivot[1] + 0.12 : maxY * 0.85) * sc;
  const api = {
    root, head: head || inner, headY, eyeY, mats: [mat], flash: 0, bones,
    update(st, t) {
      const walking = st.clip === 'walk' || st.clip === 'run' || st.clip === 'zombie' || st.clip === 'charge';
      const sp = (st.sp || 1) * (st.clip === 'run' || st.clip === 'charge' ? 1.6 : 1); const w = st.ct * 7 * sp; const amp = walking ? (st.clip === 'run' ? 1.0 : 0.7) : 0;
      for (const g of legs) { // diagonal pairs for four legs and more, alternating for two
        const r = g.userData.rest; const ph = legs.length > 2 ? (side(g) * front(g) > 0 ? 0 : Math.PI) : (side(g) > 0 ? 0 : Math.PI);
        g.rotation.set(r[0] + S(w + ph) * amp, r[1], r[2]);
      }
      for (const g of arms) {
        const r = g.userData.rest; const ph = side(g) > 0 ? Math.PI : 0;
        let x = r[0] + S(w + ph) * amp * 0.8;
        if (undeadArms) x = r[0] - Math.PI / 2 + S(t * 3 + ph) * 0.05;
        if (/swing|slash|overhead|punch|attack|thrust/.test(st.clip) && side(g) < 0) { const u = Math.min(1, st.ct / (st.dur || 0.6)); x = r[0] - Math.sin(u * Math.PI) * 2.2; }
        if (st.clip === 'cast' || st.clip === 'summon') x = r[0] - 2.2 + S(t * 20 + ph) * 0.05;
        g.rotation.set(x, r[1], r[2]);
      }
      for (const g of wings) { const r = g.userData.rest; const fl = walking || st.clip === 'fly' || /bat|parrot|bee|phantom|vex|allay|dragon|ghast/i.test(cfg.type || '') ? 1 : 0.15; g.rotation.set(r[0], r[1], r[2] + side(g) * S(t * 14) * 0.6 * fl); }
      for (const g of tails) { const r = g.userData.rest; g.rotation.set(r[0], r[1] + S(t * (walking ? 9 : 2)) * 0.25, r[2]); }
      tentacles.forEach((g, i) => { const r = g.userData.rest; g.rotation.set(r[0] + S(t * 2.4 + i * 0.8) * 0.25, r[1], r[2]); });
      if (head) { const r = head.userData.rest; head.rotation.set(r[0] + (walking ? 0 : S(t * 1.1) * 0.04), r[1] + (walking ? 0 : S(t * 0.7) * 0.12), r[2]); }
      inner.position.y = walking ? Math.abs(S(w)) * 0.02 : 0;
      let k = 1, flash = 0; // creeper-style swell
      if (st.clip === 'swell') { const u = Math.min(1, st.ct / (st.dur || 1.5)); k = 1 + 0.35 * u * u + 0.03 * S(st.ct * 50); flash = Math.floor(st.ct * (5 + 6 * u)) % 2 === 0 ? 1 : 0; }
      inner.scale.set(k, k, k); api.flash = flash;
      if (st.clip === 'hit' || st.clip === 'knockback') { const u = Math.min(1, st.ct / (st.dur || 0.5)); inner.rotation.x = -0.35 * Math.sin(Math.PI * u); } else inner.rotation.x = 0;
      inner.rotation.z = st.clip === 'die' || st.clip === 'fall' ? Math.min(1, st.ct / 0.5) * Math.PI / 2 : 0; // the game's sideways death fall
    },
  };
  return api;
}
