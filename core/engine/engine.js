// BlockReel engine: deterministic Three.js scene player.  window.renderAt(t) draws the frame for time t (seconds).
import * as THREE from 'three';
import { ease, getEase, clamp01, actorState, lookState, aimAngles, worldTime, noise } from './anim.js';
import { buildParticles } from './particles.js';
import { makeFace, faceStateAt } from './face.js';
import { skyTexture, lightingAt, createWeather } from './env.js';
import { createPost, usesPost } from './post.js';
import { buildMob } from './mobs.js';
import { parseChanges, blockState, crackTextures, buildProps } from './world.js';

const q = new URLSearchParams(location.search);
const PROJECT = q.get('project') || '/project/story.json';
const BASE = PROJECT.slice(0, PROJECT.lastIndexOf('/') + 1);
const RES = parseFloat(q.get('res') || '1') || 1; // internal render scale (render.py --scale)
const PX = 1 / 16; // one skin pixel in world units; a player is 2 blocks tall

const loader = new THREE.TextureLoader();
// HEAD with retries: a transient socket error must not turn a texture into the magenta "missing" checker
const exists = async (u) => {
  for (let i = 0; i < 4; i++) {
    try { const r = await fetch(u, { method: 'HEAD' }); if (r.ok) return true; if (r.status === 404) return false; } catch { /* retry */ }
    await new Promise((res) => setTimeout(res, 150 * (i + 1)));
  }
  return false;
};
window.__missing = []; // names of block textures that could not be found (tools/render.py refuses to render with these)
const getJSON = async (u) => (await fetch(u)).json();
const loadImg = (u) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('cannot load ' + u)); i.src = u; });
const resolve = (p) => (p.startsWith('/') || p.startsWith('http') ? p : BASE + p);

function pixelTex(url) {
  return new Promise((res, rej) => loader.load(url, (t) => {
    t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
    t.colorSpace = THREE.SRGBColorSpace; res(t);
  }, undefined, () => rej(new Error('cannot load ' + url))));
}

let story, style, renderer, scene, camera, sun;
const actors = {};
const clouds = [];
let blockDefs = {}; let projBlocksDir = null;
let grid = new Map(); let particles = null; let lastQA = null; let dyn = [], cracks = [], flowTex = [], props = null, worldFx = []; let post = null, weather = null, ambientL = null, skyTex = null, bgBase = null;
const texCache = new Map();

// ------------------------------------------------------------ textures ----
async function blockTexture(name) {
  if (texCache.has(name)) return texCache.get(name);
  const cands = [];
  if (projBlocksDir) cands.push(`${BASE}${projBlocksDir}/${name}.png`);
  cands.push(`/core/builtin/blocks/${name}.png`);
  let p = null;
  for (const u of cands) { if (await exists(u)) { p = pixelTex(u); break; } }
  if (!p) { // classic missing-texture checker
    const c = document.createElement('canvas'); c.width = c.height = 16; const g = c.getContext('2d');
    g.fillStyle = '#000'; g.fillRect(0, 0, 16, 16); g.fillStyle = '#f0f'; g.fillRect(0, 0, 8, 8); g.fillRect(8, 8, 8, 8);
    const t = new THREE.CanvasTexture(c); t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.colorSpace = THREE.SRGBColorSpace;
    console.warn('missing block texture:', name); window.__missing.push(name); p = Promise.resolve(t);
  }
  texCache.set(name, p); return p;
}

async function blockMaterials(block) {
  let def = blockDefs[block] ?? block;
  if (typeof def === 'string') def = { all: def };
  const top = def.top ?? def.all ?? block, side = def.side ?? def.all ?? block, bottom = def.bottom ?? def.all ?? block;
  const mk = async (n) => {
    const map = await blockTexture(n);
    if (def.flow) { map.wrapS = map.wrapT = THREE.RepeatWrapping; if (!flowTex.some((f) => f.map === map)) flowTex.push({ map, flow: def.flow }); } // flowing water / lava
    const o = { map, transparent: !!def.transparent, alphaTest: 0.1, side: def.transparent ? THREE.DoubleSide : THREE.FrontSide };
    return def.emissive ? new THREE.MeshBasicMaterial(o) : new THREE.MeshLambertMaterial(o);
  };
  const [t, s, b] = [await mk(top), await mk(side), await mk(bottom)];
  return [s, s, t, b, s, s]; // +x -x +y -y +z -z
}

// --------------------------------------------------------------- world ----
function expandWorld(ops) {
  const grid = new Map(); // "x,y,z" -> block
  const set = (b, x, y, z) => { const k = `${x},${y},${z}`; if (b === 'air') grid.delete(k); else grid.set(k, b); };
  const range = (a, b) => { const lo = Math.min(a, b), hi = Math.max(a, b); const r = []; for (let i = lo; i <= hi; i++) r.push(i); return r; };
  for (const op of ops || []) {
    if (op.fill) { const [b, p, r] = op.fill; for (const x of range(p[0], r[0])) for (const y of range(p[1], r[1])) for (const z of range(p[2], r[2])) set(b, x, y, z); }
    else if (op.set) { const [b, p] = op.set; set(b, p[0], p[1], p[2]); }
    else if (op.hollow) { const [b, p, r] = op.hollow; const [x0, x1, y0, y1, z0, z1] = [Math.min(p[0], r[0]), Math.max(p[0], r[0]), Math.min(p[1], r[1]), Math.max(p[1], r[1]), Math.min(p[2], r[2]), Math.max(p[2], r[2])];
      for (const x of range(x0, x1)) for (const y of range(y0, y1)) for (const z of range(z0, z1)) if (x === x0 || x === x1 || y === y0 || y === y1 || z === z0 || z === z1) set(b, x, y, z); }
    else if (op.tree) { const [x, y, z] = op.tree; const h = op.height ?? 4;
      for (let i = 0; i < h; i++) set('log', x, y + i, z);
      for (let dx = -2; dx <= 2; dx++) for (let dz = -2; dz <= 2; dz++) for (let dy = h - 2; dy <= h; dy++) {
        const far = Math.abs(dx) === 2 && Math.abs(dz) === 2; if (!(far && dy === h - 2) && !(dx === 0 && dz === 0 && dy < h)) set('leaves', x + dx, y + dy, z + dz); }
      set('leaves', x, y + h + 1, z); }
  }
  return grid;
}

async function buildWorld() {
  grid = expandWorld(story.world);
  const ch = parseChanges(story, grid); worldFx = ch.fx;
  const by = {};
  for (const [k, b] of grid) if (!ch.dynKeys.has(k)) (by[b] ||= []).push(k.split(',').map(Number));
  const geo = new THREE.BoxGeometry(1, 1, 1); const m = new THREE.Matrix4();
  for (const [b, list] of Object.entries(by)) {
    const mesh = new THREE.InstancedMesh(geo, await blockMaterials(b), list.length);
    list.forEach(([x, y, z], i) => { m.setPosition(x + 0.5, y + 0.5, z + 0.5); mesh.setMatrixAt(i, m); });
    mesh.castShadow = mesh.receiveShadow = true; scene.add(mesh);
  }
  // blocks that change over time (story.changes): one instanced mesh per block type, updated each frame
  const dby = {}; for (const it of ch.insts) (dby[it.block] ||= []).push(it);
  const white = new THREE.Color(1, 1, 1);
  for (const [b, list] of Object.entries(dby)) {
    const mesh = new THREE.InstancedMesh(geo, await blockMaterials(b), list.length);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage); mesh.castShadow = mesh.receiveShadow = true; mesh.frustumCulled = false;
    list.forEach((it, i) => { mesh.setColorAt(i, white); dyn.push({ mesh, i, it }); });
    scene.add(mesh);
  }
  if (ch.cracks.length) {
    const tex = crackTextures(THREE);
    for (const c of ch.cracks) {
      const mat = new THREE.MeshBasicMaterial({ map: tex[0], transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 });
      const m2 = new THREE.Mesh(new THREE.BoxGeometry(1.004, 1.004, 1.004), mat); m2.position.set(c.pos[0] + 0.5, c.pos[1] + 0.5, c.pos[2] + 0.5); m2.visible = false; scene.add(m2);
      cracks.push({ mesh: m2, mat, tex, c });
    }
  }
  props = await buildProps(THREE, scene, story.props, blockMaterials);
}

const _m4 = new THREE.Matrix4(), _col = new THREE.Color();
function updateWorld(t) {
  for (const f of flowTex) { const st = Math.floor(t * f.flow[1] * 16) / 16, sx = Math.floor(t * f.flow[0] * 16) / 16; f.map.offset.set(sx % 1, -st % 1); }
  const touched = new Set();
  for (const d of dyn) {
    const st = blockState(d.it.evs, d.it.vis0, t); const sc = st.vis ? st.scale : 0;
    _m4.makeScale(sc, sc, sc); _m4.setPosition(d.it.pos[0] + 0.5, d.it.pos[1] + 0.5, d.it.pos[2] + 0.5);
    d.mesh.setMatrixAt(d.i, _m4); d.mesh.setColorAt(d.i, st.flash ? _col.setRGB(3, 3, 3) : _col.setRGB(1, 1, 1)); touched.add(d.mesh);
  }
  for (const m of touched) { m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true; }
  for (const c of cracks) { const on = t >= c.c.t0 && t < c.c.t1; c.mesh.visible = on; if (on) c.mat.map = c.tex[Math.min(9, Math.floor(((t - c.c.t0) / (c.c.t1 - c.c.t0)) * 10))]; }
  props && props.update(t);
}

// -------------------------------------------------------------- player ----
function uvRect(x, y, w, h) { // skin pixels (origin top-left) -> [TL, TR, BL, BR] uv corners
  const f = (px, py) => [px / 64, 1 - py / 64];
  return [f(x, y), f(x + w, y), f(x, y + h), f(x + w, y + h)];
}
function boxGeo(w, h, d, u, v, grow = 0) {
  const g = new THREE.BoxGeometry((w + grow * 2) * PX, (h + grow * 2) * PX, (d + grow * 2) * PX);
  const r = {
    top: uvRect(u + d, v, w, d), bottom: uvRect(u + d + w, v, w, d), right: uvRect(u, v + d, d, h),
    front: uvRect(u + d, v + d, w, h), left: uvRect(u + d + w, v + d, d, h), back: uvRect(u + 2 * d + w, v + d, w, h),
  };
  const order = ['left', 'right', 'top', 'bottom', 'front', 'back']; // three: +x -x +y -y +z -z (character faces +z)
  const uv = g.attributes.uv;
  order.forEach((face, i) => r[face].forEach((c, j) => uv.setXY(i * 4 + j, c[0], c[1])));
  uv.needsUpdate = true; return g;
}

function detectSlim(img) {
  const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  const s = img.width / 64; const col = (x, y0, y1) => { const d = g.getImageData(x * s, y0 * s, 1, (y1 - y0) * s).data; for (let i = 3; i < d.length; i += 4) if (d[i]) return false; return true; };
  return col(55, 20, 32) && (img.height === 32 * s || col(47, 52, 64));
}

async function makeMob(name, cfg) {
  const tex = await pixelTex(resolve(cfg.texture));
  const m = buildMob(THREE, cfg.type, tex, cfg);
  m.root.position.set(...(cfg.pos || [0, 1, 0])); scene.add(m.root);
  if (cfg.nametag) {
    const c = document.createElement('canvas'); c.width = 256; c.height = 40; const g = c.getContext('2d');
    g.fillStyle = 'rgba(0,0,0,.45)'; g.fillRect(0, 0, 256, 40); g.fillStyle = '#fff'; g.font = 'bold 26px monospace'; g.textAlign = 'center'; g.fillText(cfg.nametag, 128, 29);
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false, transparent: true }));
    sp.scale.set(1.2, 0.19, 1); sp.position.set(0, m.headY + 0.6, 0); m.root.add(sp);
  }
  m.head.rotation.order = 'YXZ';
  return { name, cfg, mob: m, root: m.root, head: m.head, face: { update() {} }, headY: m.headY, eyeY: m.eyeY, _pos: [...(cfg.pos || [0, 1, 0])], _heading: 0, _headPose: [0, 0, 0] };
}

async function makePlayer(name, cfg) {
  const url = resolve(cfg.skin);
  const img = await loadImg(url);
  const tex = await pixelTex(url);
  let slim = cfg.model === 'slim' || ((cfg.model ?? 'auto') === 'auto' && detectSlim(img));
  const legacy = img.height === img.width / 2;
  const aw = slim ? 3 : 4;
  const base = new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.5, transparent: false });
  const over = new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.5, transparent: true });
  const root = new THREE.Group(); const inner = new THREE.Group(); root.add(inner);
  const upper = new THREE.Group(); upper.position.set(0, 12 * PX, 0); inner.add(upper); // hip pivot: torso, head and arms lean together
  const limb = (parent, w, h, d, u, v, ou, ov, pivot, dy = 0, rise = 0) => { // rise: how far the box extends ABOVE its pivot (arms: 2 px, so the shoulder is flush with the top of the torso)
    const g = new THREE.Group(); g.position.set(pivot[0] * PX, (pivot[1] - dy) * PX, pivot[2] * PX);
    const a = new THREE.Mesh(boxGeo(w, h, d, u, v), base); a.position.y = (-h / 2 + rise) * PX; a.castShadow = true; g.add(a);
    const b = new THREE.Mesh(boxGeo(w, h, d, ou, ov, 0.5), over); b.position.y = (-h / 2 + rise) * PX; g.add(b);
    parent.add(g); return g;
  };
  const head = new THREE.Group(); head.position.set(0, 12 * PX, 0);
  const face = makeFace(THREE, img, head, PX, (t) => { t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; t.colorSpace = THREE.SRGBColorSpace; });
  const hm = new THREE.Mesh(boxGeo(8, 8, 8, 0, 0), face.material); hm.position.y = 4 * PX; hm.castShadow = true; head.add(hm);
  const hat = new THREE.Mesh(boxGeo(8, 8, 8, 32, 0, 0.5), over); hat.position.y = 4 * PX; head.add(hat); upper.add(head);
  const body = new THREE.Group(); body.position.set(0, 6 * PX, 0);
  const bm = new THREE.Mesh(boxGeo(8, 12, 4, 16, 16), base); bm.castShadow = true; body.add(bm);
  const jm = new THREE.Mesh(boxGeo(8, 12, 4, 16, 32, 0.5), over); body.add(jm); upper.add(body);
  const ax = slim ? 5.5 : 6;
  const rArm = limb(upper, aw, 12, 4, 40, 16, 40, 32, [-ax, 22, 0], 12, 2);
  // legacy 64x32 skins have no left limbs: mirror the right ones
  const lArm = legacy ? limb(upper, aw, 12, 4, 40, 16, 40, 16, [ax, 22, 0], 12, 2) : limb(upper, aw, 12, 4, 32, 48, 48, 48, [ax, 22, 0], 12, 2);
  const rLeg = limb(inner, 4, 12, 4, 0, 16, 0, 32, [-2, 12, 0]);
  const lLeg = legacy ? limb(inner, 4, 12, 4, 0, 16, 0, 16, [2, 12, 0]) : limb(inner, 4, 12, 4, 16, 48, 0, 48, [2, 12, 0]);
  if (legacy) { lArm.scale.x = -1; lLeg.scale.x = -1; }
  // optional held block
  let held = null;
  if (cfg.holding) {
    const mats = await blockMaterials(cfg.holding);
    held = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.34, 0.34), mats); held.position.set(0, -10.5 * PX, 5 * PX); rArm.add(held);
  }
  // name tag
  if (cfg.nametag) {
    const c = document.createElement('canvas'); c.width = 256; c.height = 40; const g = c.getContext('2d');
    g.fillStyle = 'rgba(0,0,0,.45)'; g.fillRect(0, 0, 256, 40); g.fillStyle = '#fff'; g.font = 'bold 26px monospace'; g.textAlign = 'center'; g.fillText(cfg.nametag, 128, 29);
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false, transparent: true }));
    sp.scale.set(1.2, 0.19, 1); sp.position.set(0, 2.45, 0); root.add(sp);
  }
  const sc = cfg.scale ?? 1; root.scale.setScalar(sc);
  head.rotation.order = 'YXZ'; upper.rotation.order = 'YXZ';
  scene.add(root);
  return { name, cfg, root, inner, upper, head, body, rArm, lArm, rLeg, lLeg, face, headY: 1.9 * sc, eyeY: 1.62 * sc, _pos: [...(cfg.pos || [0, 1, 0])], _heading: 0 };
}

// ----------------------------------------------------- actors (see anim.js) ----
const actorCtx = { posOf: (n, tt, depth) => (actors[n] ? actorState(story, actors[n], tt, actorCtx, depth).pos : [0, 0, 0]) };

function applyActor(a, t) {
  const st = actorState(story, a, t, actorCtx);
  a.root.visible = !st.hidden;
  if (a.mob) { // mobs: position + heading here, limbs in mobs.js
    a.mob.update(st, t); a.root.position.set(st.pos[0], st.pos[1] - (st.clip === 'swell' ? 0 : 0), st.pos[2]); a.root.rotation.set(0, st.heading, 0);
    a._pos = st.pos; a._heading = st.heading; a._headPose = [a.head.rotation.x, a.head.rotation.y, 0]; return;
  }
  const p = st.pose;
  a._headPose = p.head;
  a.head.rotation.set(p.head[0], p.head[1], p.head[2]);
  a.rArm.rotation.set(p.rArm[0], p.rArm[1], p.rArm[2]); a.lArm.rotation.set(p.lArm[0], p.lArm[1], p.lArm[2]);
  a.rLeg.rotation.set(p.rLeg[0], p.rLeg[1], p.rLeg[2]); a.lLeg.rotation.set(p.lLeg[0], p.lLeg[1], p.lLeg[2]);
  a.upper.rotation.set(p.bodyRx + p.body[0], p.body[1], p.body[2]);
  a.root.position.set(st.pos[0], st.pos[1] + p.bob + st.jumpY - p.sink, st.pos[2]);
  a.root.rotation.set(0, st.heading + p.spinY, p.roll); a.root.rotation.order = 'YXZ';
  a._pos = st.pos; a._heading = st.heading;
}

// head follows a look-at target (actor, [x,y,z] or "camera"); camPos is null until the camera is placed
function targetPoint(tg, camPos) {
  if (tg === 'camera') return camPos ? [camPos.x, camPos.y, camPos.z] : null;
  if (Array.isArray(tg)) return tg;
  const o = actors[tg]; return o ? [o._pos[0], o._pos[1] + o.eyeY, o._pos[2]] : null;
}
function applyLook(a, t, camPos) {
  const ls = lookState(story, a, t); const hp = a._headPose || [0, 0, 0];
  let dyaw = 0, dpitch = 0;
  if (ls) {
    const aim = (tg) => { if (tg === null || tg === undefined) return [0, 0]; const pt = targetPoint(tg, camPos); return pt ? aimAngles(a._pos, a._heading, a.eyeY, pt, ls.limit) : [0, 0]; };
    const [p1, y1] = aim(ls.target), [p0, y0] = aim(ls.prev);
    dpitch = p0 + (p1 - p0) * ls.w; dyaw = y0 + (y1 - y0) * ls.w;
  }
  a.head.rotation.set(hp[0] + dpitch, hp[1] + dyaw, hp[2]);
}

// ------------------------------------------------------------- camera ----
function vec(v) {
  if (Array.isArray(v)) return new THREE.Vector3(...v);
  if (typeof v === 'string') { const a = actors[v]; return a ? new THREE.Vector3(a._pos[0], a._pos[1] + a.headY * 0.8, a._pos[2]) : new THREE.Vector3(); }
  if (v && v.actor) { const a = actors[v.actor]; const o = v.offset || [0, 0, 0]; return new THREE.Vector3(a._pos[0] + o[0], a._pos[1] + o[1], a._pos[2] + o[2]); }
  return new THREE.Vector3();
}

function currentShot(t) {
  const shots = (story.camera || []).slice().sort((a, b) => a.t - b.t);
  let shot = shots[0]; for (const s of shots) if (s.t <= t) shot = s;
  return shot;
}

function applyCamera(t, wt) {
  const shot = currentShot(t);
  for (const a of Object.values(actors)) a.head.visible = true;
  if (!shot) { camera.position.set(8, 5, 10); camera.lookAt(0, 1.5, 0); return camera.position; }
  const dur = shot.dur ?? 3; const u = clamp01((wt - worldTime(story, shot.t)) / dur); const e = getEase(shot.ease || 'smooth')(u);
  let pos, look; let roll = (shot.dutch ?? 0) + ((shot.dutchTo ?? shot.dutch ?? 0) - (shot.dutch ?? 0)) * e;
  if (shot.first) { // first-person: camera at the actor's eyes, looking where the head looks
    const a = actors[shot.first.actor ?? shot.first]; const fwd = new THREE.Vector3(0, 0, 1);
    fwd.applyEuler(new THREE.Euler(a.head.rotation.x, a._heading + a.head.rotation.y, 0, 'YXZ'));
    pos = new THREE.Vector3(a._pos[0], a._pos[1] + a.eyeY, a._pos[2]).addScaledVector(fwd, 0.14); look = pos.clone().add(fwd);
    a.head.visible = false; // hide the own head (arms stay in view)
  } else if (shot.orbit) {
    const o = shot.orbit; const c = vec(o.center); const ang = (o.from + (o.to - o.from) * e) * Math.PI / 180;
    pos = new THREE.Vector3(c.x + Math.sin(ang) * o.radius, c.y + (o.height ?? 2), c.z + Math.cos(ang) * o.radius); look = c;
  } else {
    const p0 = vec(shot.pos), p1 = shot.to ? vec(shot.to) : p0; pos = p0.clone().lerp(p1, e);
    const l0 = vec(shot.look), l1 = shot.lookTo ? vec(shot.lookTo) : l0; look = l0.clone().lerp(l1, e);
  }
  const sh = shot.shake ?? 0; if (sh) { pos.x += Math.sin(t * 61) * sh; pos.y += Math.sin(t * 53 + 1) * sh; pos.z += Math.sin(t * 47 + 2) * sh; }
  const hh = shot.handheld ?? 0; // slow organic drift: position, aim and a touch of roll
  if (hh) {
    pos.x += noise(t, 1) * hh * 0.08; pos.y += noise(t, 2) * hh * 0.06; pos.z += noise(t, 3) * hh * 0.08;
    look.x += noise(t, 4) * hh * 0.1; look.y += noise(t, 5) * hh * 0.08; look.z += noise(t, 6) * hh * 0.1; roll += noise(t, 7) * hh * 1.2;
  }
  camera.position.copy(pos); camera.up.set(0, 1, 0); camera.lookAt(look);
  if (roll) camera.rotateZ(roll * Math.PI / 180);
  const f0 = shot.fov ?? style.fov ?? 60; const fov = shot.fovTo !== undefined ? f0 + (shot.fovTo - f0) * e : f0;
  if (camera.fov !== fov) { camera.fov = fov; camera.updateProjectionMatrix(); }
  return camera.position;
}

// ------------------------------------------------------------ overlays ----
function applyOverlays(t) {
  const sub = document.getElementById('sub'); const title = document.getElementById('title');
  const s = (story.subtitles || []).find((x) => t >= x.t && t < x.t + (x.dur ?? 2));
  sub.innerHTML = s ? `<span>${s.who ? `<b>&lt;${s.who}&gt;</b> ` : ''}${s.text.replace(/</g, '&lt;')}</span>` : '';
  const ti = (story.titles || []).find((x) => t >= x.t && t < x.t + (x.dur ?? 2));
  if (ti) { const k = (t - ti.t); const fade = Math.min(1, k / 0.3, (ti.dur ?? 2) - k > 0.3 ? 1 : ((ti.dur ?? 2) - k) / 0.3); title.style.opacity = fade; title.style.color = ti.color || '#fff'; title.style.fontSize = (ti.size || 64) + 'px'; title.textContent = ti.text; }
  else title.textContent = '';
}

// transitions: { t, type: "flash" | "fade" | "whip", dur, ... } on the output timeline
function applyTransitions(t) {
  const flash = document.getElementById('flash'), fade = document.getElementById('fade'), cv = document.getElementById('c'), blur = document.getElementById('hbBlur');
  let fa = 0, fc = '#fff', da = 0, dc = '#000', wh = 0, wdir = 1;
  for (const x of story.transitions || []) {
    const d = x.dur ?? 0.3; const u = (t - x.t) / d;
    if (x.type === 'flash') { if (u >= 0 && u <= 1) { const env = u < 0.2 ? u / 0.2 : Math.pow(1 - (u - 0.2) / 0.8, 2); const v = env * (x.peak ?? 1); if (v > fa) { fa = v; fc = x.color || '#fff'; } } }
    else if (x.type === 'fade') { // dir "out": clear -> color over dur and stays; "in": color -> clear
      const out = (x.dir ?? 'out') === 'out'; const v = out ? clamp01(u) : 1 - clamp01(u);
      if ((out && u >= 0) || (!out && u <= 1 && t >= x.t - 1e-9) ) { if (v > da) { da = v; dc = x.color || '#000'; } }
      if (!out && t < x.t && x.hold) { da = Math.max(da, 1); dc = x.color || '#000'; }
    } else if (x.type === 'whip') { if (u >= 0 && u <= 1) { const v = Math.sin(Math.PI * u); if (v > wh) { wh = v * (x.strength ?? 36); wdir = x.dir === 'left' ? -1 : 1; } } }
  }
  flash.style.background = fc; flash.style.opacity = fa;
  fade.style.background = dc; fade.style.opacity = da;
  if (wh > 0.5) { blur.setAttribute('stdDeviation', `${wh} 0`); cv.style.filter = 'url(#hb)'; cv.style.transform = `translateX(${wdir * wh * 0.6}px) scale(1.04)`; }
  else { cv.style.filter = ''; cv.style.transform = ''; }
}

// ---------------------------------------------------------- particle ctx ----
async function blockPalette(name) {
  let def = blockDefs[name] ?? name; if (typeof def === 'string') def = { all: def };
  const tn = def.side ?? def.all ?? name; const cands = [];
  if (projBlocksDir) cands.push(`${BASE}${projBlocksDir}/${tn}.png`);
  cands.push(`/core/builtin/blocks/${tn}.png`);
  for (const u of cands) {
    if (!(await exists(u))) continue;
    const img = await loadImg(u); const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    const g = c.getContext('2d'); g.drawImage(img, 0, 0); const d = g.getImageData(0, 0, c.width, c.height).data; const out = []; const seen = new Set();
    for (let i = 0; i < d.length; i += 4) { if (d[i + 3] < 200) continue; const k = (d[i] >> 3) + ',' + (d[i + 1] >> 3) + ',' + (d[i + 2] >> 3); if (seen.has(k)) continue; seen.add(k); out.push([d[i] / 255, d[i + 1] / 255, d[i + 2] / 255]); if (out.length >= 48) break; }
    if (out.length) return out;
  }
  return [[0.5, 0.5, 0.5]];
}
const palCache = new Map();
const particleCtx = {
  posOf: (n, tt) => actorCtx.posOf(n, tt, 0),
  groundAt: (x, y, z) => { const ix = Math.floor(x), iz = Math.floor(z); for (let yy = Math.floor(y + 0.6); yy > Math.floor(y) - 40; yy--) if (grid.has(`${ix},${yy},${iz}`)) return yy + 1; return null; },
  blockUnder: (p) => { const ix = Math.floor(p[0]), iz = Math.floor(p[2]); for (let yy = Math.floor(p[1] + 0.6); yy > Math.floor(p[1]) - 40; yy--) { const b = grid.get(`${ix},${yy},${iz}`); if (b) return b; } return null; },
  palette: (n) => { if (!palCache.has(n)) palCache.set(n, blockPalette(n)); return palCache.get(n); },
};

// --------------------------------------------------------------- setup ----
async function init() {
  story = await getJSON(PROJECT);
  const styleName = story.style || 'classic-2012';
  style = await getJSON(`/styles/${styleName}/style.json`); Object.assign(style, story.styleOverride || {});
  const W = story.size?.[0] ?? 1280, H = story.size?.[1] ?? 720;
  const stage = document.getElementById('stage'); stage.style.width = W + 'px'; stage.style.height = H + 'px';
  stage.style.background = `linear-gradient(${style.sky.top}, ${style.sky.bottom})`;
  const lb = style.letterbox; // true = 11% bars; a number = target aspect ratio (e.g. 2.37)
  const barPct = typeof lb === 'number' ? Math.max(0, (1 - (W / lb) / H) / 2 * 100) : 11;
  document.querySelectorAll('#bars .bar').forEach((b) => { b.style.height = barPct + '%'; });
  document.getElementById('bars').style.display = lb ? 'block' : 'none';
  document.getElementById('vig').style.display = style.vignette ? 'block' : 'none';
  const k = style.pixelate || 1;
  renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('c'), antialias: k === 1, alpha: true, preserveDrawingBuffer: true });
  renderer.setSize(W * RES / k, H * RES / k, false); renderer.setPixelRatio(1);
  renderer.shadowMap.enabled = !!style.shadows; renderer.shadowMap.type = THREE.PCFShadowMap;
  scene = new THREE.Scene();
  skyTex = skyTexture(THREE, style.sky.top, style.sky.bottom); scene.background = skyTex;
  if (style.fog) scene.fog = new THREE.Fog(style.sky.bottom, style.fog[0], style.fog[1]);
  camera = new THREE.PerspectiveCamera(style.fov || 60, W / H, 0.1, 400);
  ambientL = new THREE.AmbientLight(style.ambient.color, style.ambient.intensity); scene.add(ambientL);
  sun = new THREE.DirectionalLight(style.sun.color, style.sun.intensity);
  sun.position.set(...style.sun.dir.map((v) => v * 30)); sun.castShadow = !!style.shadows;
  const sc = sun.shadow.camera; sc.left = sc.bottom = -24; sc.right = sc.top = 24; sc.near = 1; sc.far = 120; sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0006;
  scene.add(sun);
  // blocks
  blockDefs = (await getJSON('/core/builtin/blocks/index.json')).blocks;
  projBlocksDir = story.blocks ?? null;
  if (projBlocksDir && await exists(`${BASE}${projBlocksDir}/index.json`)) Object.assign(blockDefs, (await getJSON(`${BASE}${projBlocksDir}/index.json`)).blocks);
  await buildWorld();
  for (const [n, cfg] of Object.entries(story.actors || {})) actors[n] = cfg.type && cfg.type !== 'player' ? await makeMob(n, cfg) : await makePlayer(n, cfg);
  particles = await buildParticles(THREE, scene, { ...story, fx: [...(story.fx || []), ...worldFx] }, particleCtx);
  if (style.clouds) {
    const cm = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9, fog: false });
    for (let i = 0; i < 14; i++) { const m = new THREE.Mesh(new THREE.BoxGeometry(6 + (i * 7) % 6, 1, 4 + (i * 5) % 4), cm); m.position.set(-60 + (i * 37) % 120, 28 + (i % 3), -60 + (i * 53) % 120); m.userData.x0 = m.position.x; scene.add(m); clouds.push(m); }
  }
  weather = createWeather(THREE, scene, story.weather || style.weather);
  const shotPosts = (story.camera || []).map((c) => c.post);
  if (usesPost(style.post, story.post, ...shotPosts)) post = createPost(THREE, renderer, scene, camera, Math.round(W * RES / k), Math.round(H * RES / k), [style.post, story.post, ...shotPosts]);
  window.__ready = true;
}

// ------------------------------------------------------------------- QA ----
// Automatic checks used by tools/qa.py (data only; the human still has to look at the frames).
function collectQA(t, camPos) {
  const W = story.size?.[0] ?? 1280, H = story.size?.[1] ?? 720;
  const solid = (p) => grid.has(`${Math.floor(p.x)},${Math.floor(p.y)},${Math.floor(p.z)}`);
  const lb = style.letterbox; const barPct = typeof lb === 'number' ? Math.max(0, (1 - (W / lb) / H) / 2) : (lb ? 0.11 : 0);
  const out = { t, cameraInBlock: solid(camPos), camera: [camPos.x, camPos.y, camPos.z], actors: {}, subtitle: null, activeShot: (currentShot(t) || {}).t ?? null };
  const cd = new THREE.Vector3(); camera.getWorldDirection(cd);
  for (const [n, a] of Object.entries(actors)) {
    const proj = (y) => { const v = new THREE.Vector3(a._pos[0], a._pos[1] + y, a._pos[2]).project(camera); return v; };
    const head = proj(a.headY * 0.95), feet = proj(0.05), chest = proj(a.headY * 0.6);
    const inView = (v) => v.z < 1 && Math.abs(v.x) <= 1 && v.y >= -1 + barPct * 2 && v.y <= 1 - barPct * 2;
    const pts = [head, chest, feet]; const vis = pts.filter(inView).length;
    const toCam = new THREE.Vector3(camPos.x - a._pos[0], 0, camPos.z - a._pos[2]).normalize();
    const fwd = new THREE.Vector3(Math.sin(a._heading + a.head.rotation.y), 0, Math.cos(a._heading + a.head.rotation.y));
    out.actors[n] = { visiblePoints: vis, ndc: [chest.x, chest.y], behindCamera: chest.z >= 1, facingCamera: fwd.dot(toCam), visible: a.root.visible, distance: Math.hypot(camPos.x - a._pos[0], camPos.y - a._pos[1], camPos.z - a._pos[2]), insideBlock: solid(new THREE.Vector3(a._pos[0], a._pos[1] + 1, a._pos[2])) };
  }
  const sp = document.querySelector('#sub span');
  if (sp) { const r = sp.getBoundingClientRect(), st = document.getElementById('stage').getBoundingClientRect(); out.subtitle = { clipped: r.left < st.left - 1 || r.right > st.right + 1 || r.top < st.top || r.bottom > st.bottom, width: r.width, height: r.height }; }
  return out;
}

function applyLighting(t) {
  if (!(story.lighting && story.lighting.length)) return;
  const L = lightingAt(THREE, style, story.lighting, t);
  skyTexture(THREE, L.sky.top, L.sky.bottom, skyTex);
  ambientL.color.set(L.ambient.color); ambientL.intensity = L.ambient.intensity;
  sun.color.set(L.sun.color); sun.intensity = L.sun.intensity; sun.position.set(...L.sun.dir.map((v) => v * 30));
  if (scene.fog && L.fog) { scene.fog.color.set(L.sky.bottom); scene.fog.near = L.fog[0]; scene.fog.far = L.fog[1]; }
}

window.renderAt = (t) => {
  const wt = worldTime(story, t); // speed ramps (story.timeRemap) bend world time only; cuts, subtitles, titles use t
  for (const a of Object.values(actors)) applyActor(a, wt);
  for (const a of Object.values(actors)) { a.face.update(faceStateAt(story, a, wt)); }
  updateWorld(wt); particles && particles.update(wt);
  clouds.forEach((c, i) => { c.position.x = ((c.userData.x0 + 60 + wt * 0.4 * (1 + (i % 3) * 0.2)) % 120) - 60; });
  for (const a of Object.values(actors)) applyLook(a, wt, null);
  const camPos = applyCamera(t, wt);
  for (const a of Object.values(actors)) { const ls = lookState(story, a, wt); if (ls && (ls.target === 'camera' || ls.prev === 'camera')) applyLook(a, wt, camPos); }
  applyLighting(t); weather && weather.update(wt, camPos);
  applyOverlays(t); applyTransitions(t);
  if (post) { const shot = currentShot(t) || {}; let fd; const f = shot.focus; if (f !== undefined) { const tp = (x) => { const v = typeof x === 'number' ? null : vec(x); return v ? camPos.distanceTo(v) : x; }; const f0 = tp(f), f1 = shot.focusTo !== undefined ? tp(shot.focusTo) : f0; const e = getEase(shot.ease || 'smooth')(clamp01((wt - worldTime(story, shot.t)) / (shot.dur ?? 3))); fd = f0 + (f1 - f0) * e; }
    post.render(t, [style.post, story.post, shot.post], fd); }
  else renderer.render(scene, camera);
  lastQA = { t, camPos: camPos.clone() };
  return true;
};
window.__qa = (t) => { window.renderAt(t); return collectQA(t, lastQA.camPos); };
window.__story = () => story;

// live preview (tools/preview.py): ?live=1 adds a time slider and a play button, re-rendering with renderAt(t)
function liveControls() {
  const dur = story.duration ?? 10; const bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99;display:flex;gap:10px;align-items:center;padding:8px 12px;background:#000c;color:#fff;font:14px monospace';
  bar.innerHTML = '<button id="lp">play</button><input id="ls" type="range" min="0" max="' + dur + '" step="0.01" value="0" style="flex:1"><span id="lt">0.00 / ' + dur + 's</span>';
  document.body.appendChild(bar);
  const sl = bar.querySelector('#ls'), lt = bar.querySelector('#lt'), bt = bar.querySelector('#lp'); let playing = false, last = 0;
  const draw = () => { window.renderAt(parseFloat(sl.value)); lt.textContent = parseFloat(sl.value).toFixed(2) + ' / ' + dur + 's'; };
  sl.oninput = draw; bt.onclick = () => { playing = !playing; bt.textContent = playing ? 'pause' : 'play'; last = performance.now(); };
  const loop = (now) => { if (playing) { let v = parseFloat(sl.value) + (now - last) / 1000; last = now; if (v >= dur) v = 0; sl.value = v; draw(); } requestAnimationFrame(loop); };
  requestAnimationFrame(loop); draw();
}
if (q.get('live')) { const w = setInterval(() => { if (window.__ready) { clearInterval(w); liveControls(); } }, 100); }
init().catch((e) => { window.__error = String(e); console.error(e); });
