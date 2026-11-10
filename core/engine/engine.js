// BlockReel engine: deterministic Three.js scene player.  window.renderAt(t) draws the frame for time t (seconds).
import * as THREE from 'three';
import { ease, getEase, clamp01, actorState, lookState, aimAngles, worldTime, noise, hurtAt, clipState } from './anim.js';
import { extrudeItem, mountItem } from './items.js';
import { itemAsset } from './asset-refs.js';
import { equip, shieldMesh } from './equip.js';
import { loadFont, textCanvas, wrapRuns } from './font.js';
import { createHud } from './hud.js';
import { buildParticles } from './particles.js';
import { makeFace, faceStateAt } from './face.js';
import { skyTexture, lightingAt, createWeather, createSky, createLightning } from './env.js';
import { createPost, usesPost } from './post.js';
import { buildMob } from './mobs.js';
import { buildGeoModel } from './geo.js';
import { buildWolf } from './wolf.js';
import { actorSize } from './actor-size.js';
import { parseChanges, blockState, crackTextures, buildProps } from './world.js';
import { expandWorld, groundHeight } from './worldgen.js';
import { meshWorld, computeLight, resolveDef, pixelMipmaps, FACES, CHUNK } from './mesher.js';

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
let renderError;
const actors = {};
const clouds = [];
let blockDefs = {}; let projBlocksDir = null;
let vanillaDir = null; let dynByKey = new Map(), dynKeys = new Set(); let grid = new Map(); let particles = null; let lastQA = null; let dyn = [], cracks = [], flowTex = [], props = null, worldFx = []; let post = null, weather = null, ambientL = null, skyTex = null, bgBase = null; let worldLight = null; const worldMeshes = []; let sky = null, lightning = null;
const texCache = new Map();

// ------------------------------------------------------------ textures ----
async function blockTexture(name) {
  if (texCache.has(name)) return texCache.get(name);
  const cands = [];
  if (projBlocksDir) cands.push(`${BASE}${projBlocksDir}/${name}.png`);
  if (vanillaDir) cands.push(`${vanillaDir}/${name}.png`);
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

// ---- world materials: mipmapped pixel textures + the game's light model (sky light, warm block light, AO) ----
const LIGHT_U = { uDay: { value: 1 }, uCave: { value: 0.07 }, uTorchLit: { value: 0 }, uBlockColor: { value: new THREE.Color('#ffc58a') } };
function mcLit(mat) {
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, LIGHT_U);
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute vec2 mcLight; varying vec2 vMcLight;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvMcLight = mcLight;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec2 vMcLight; uniform float uDay, uCave, uTorchLit; uniform vec3 uBlockColor;\nfloat mcCurve(float x){ x = clamp(x, 0.0, 1.0); return x / (4.0 - 3.0 * x); }')
      .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
        float mcSky = mcCurve(vMcLight.x), mcBlk = mcCurve(vMcLight.y);
        reflectedLight.directDiffuse *= mix(mcSky * mcSky, 1.0, uTorchLit);
        reflectedLight.indirectDiffuse *= mix(uCave, 1.0, mcSky);
        totalEmissiveRadiance += diffuseColor.rgb * uBlockColor * mcBlk * 1.15 * (1.0 - uDay * mcSky);`);
  };
  mat.customProgramCacheKey = () => 'mclit';
  return mat;
}
let maxAniso = 1;
const mipCache = new Map();
async function blockTexUrl(name) {
  const cands = [];
  if (projBlocksDir) cands.push(`${BASE}${projBlocksDir}/${name}.png`);
  if (vanillaDir) cands.push(`${vanillaDir}/${name}.png`);
  cands.push(`/core/builtin/blocks/${name}.png`);
  for (const u of cands) if (await exists(u)) return u;
  return null;
}
function mipTex(name, cutout, flow) {
  const key = `${name}|${cutout ? 1 : 0}|${flow ? flow.join(',') : ''}`;
  if (mipCache.has(key)) return mipCache.get(key);
  const p = (async () => {
    const u = await blockTexUrl(name);
    if (!u) return blockTexture(name); // missing checker (and the warning)
    const img = await loadImg(u); const pot = (v) => (v & (v - 1)) === 0;
    const t = new THREE.Texture(img); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter;
    if (img.height > img.width && img.height % img.width === 0) { // animated strip: show the first frame
      const c = document.createElement('canvas'); c.width = c.height = img.width; c.getContext('2d').drawImage(img, 0, 0); t.image = c;
    }
    if (pot(t.image.width) && pot(t.image.height)) { t.mipmaps = pixelMipmaps(t.image, cutout); t.generateMipmaps = false; t.minFilter = THREE.NearestMipmapLinearFilter; t.anisotropy = maxAniso; }
    else { t.generateMipmaps = false; t.minFilter = THREE.NearestFilter; }
    if (flow) { t.wrapS = t.wrapT = THREE.RepeatWrapping; flowTex.push({ map: t, flow }); }
    t.needsUpdate = true; return t;
  })();
  mipCache.set(key, p); return p;
}
const litCache = new Map();
async function worldMaterial(tex, kind, flow) {
  const key = `${tex}|${kind}|${flow ? flow.join(',') : ''}`;
  if (litCache.has(key)) return litCache.get(key);
  const p = (async () => {
    const map = await mipTex(tex, kind !== 'opaque', flow);
    if (kind === 'emissive') return new THREE.MeshBasicMaterial({ map, alphaTest: 0.5 });
    const o = { map, vertexColors: true };
    if (kind === 'cutout') Object.assign(o, { alphaTest: 0.5 });
    if (kind === 'translucent') Object.assign(o, { transparent: true, opacity: 1, depthWrite: true });
    return mcLit(new THREE.MeshLambertMaterial(o));
  })();
  litCache.set(key, p); return p;
}
const defCache = new Map();
const defOf = (name) => { if (!defCache.has(name)) defCache.set(name, resolveDef(blockDefs, name)); return defCache.get(name); };

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
// [x, null, z] means "on the ground here" for actors, moves, effects and lightning; cameras get eye height (1.7) above it
// thin layers (snow, carpet) are walked through; dirt paths and farmland (15/16 high) are ground you stand on
const passableBlock = (b) => { const d = defOf(b); return ['cross', 'torch', 'liquid', 'crop', 'rail', 'ladder', 'vine', 'door', 'trapdoor'].includes(d.shape) || (d.shape === 'layer' && (d.height ?? 2) <= 8); };
function snapToGround() {
  // actors stand on the terrain, never on a canopy; cameras ignore trees entirely (eye height above the real ground)
  const leafy = (b) => /leaves/.test(b) || passableBlock(b); const woody = (b) => /leaves|log/.test(b) || passableBlock(b);
  const fix = (p, lift = 0, pass = leafy) => { if (Array.isArray(p) && p.length === 3 && (p[1] === null || p[1] === 'ground')) p[1] = groundHeight(grid, p[0], p[2], 160, pass) + lift; };
  for (const c of Object.values(story.actors || {})) fix(c.pos);
  for (const sg of story.timeline || []) { fix(sg.to); if (Array.isArray(sg.face)) fix(sg.face, 1.6); if (Array.isArray(sg.lookAt)) fix(sg.lookAt, 1.6); }
  for (const f of story.fx || []) fix(f.pos, 0.5);
  for (const c of story.camera || []) { fix(c.pos, 1.7, woody); fix(c.to, 1.7, woody); fix(c.look, 1.2, woody); fix(c.lookTo, 1.2, woody); if (c.orbit) fix(c.orbit.center, 1.2, woody); }
  for (const pr of Object.values(story.props || {})) fix(pr.pos);
}

// Where will the camera be? Sampled along every shot (actor-relative offsets use the actors' planned paths), so foliage and
// plants that would block the lens can be cleared before the world is meshed - like trimming branches on a real set.
function cameraPath(step = 0.1) {
  const pts = []; const shots = (story.camera || []).slice().sort((a, b) => a.t - b.t); const dur = story.duration ?? 10;
  const pseudo = {}; for (const [n, cfg] of Object.entries(story.actors || {})) pseudo[n] = { name: n, cfg };
  const ctx = { posOf: (n, tt, depth) => (pseudo[n] ? actorState(story, pseudo[n], tt, ctx, depth).pos : [0, 0, 0]) };
  const P = (v, tt) => { if (Array.isArray(v)) return v; if (typeof v === 'string' && pseudo[v]) { const q = ctx.posOf(v, tt, 0); return [q[0], q[1] + 1.5, q[2]]; }
    if (v && v.actor && pseudo[v.actor]) { const q = ctx.posOf(v.actor, tt, 0), o = v.offset || [0, 0, 0]; return [q[0] + o[0], q[1] + o[1], q[2] + o[2]]; } return null; };
  shots.forEach((sh, i) => {
    const end = Math.min(dur, i + 1 < shots.length ? shots[i + 1].t : dur);
    for (let t = sh.t; t <= end + 1e-6; t += step) {
      const wt = worldTime(story, t); const u = clamp01((wt - worldTime(story, sh.t)) / (sh.dur ?? 3)); const e = getEase(sh.ease || 'smooth')(u);
      if (sh.orbit) { const c = P(sh.orbit.center, wt); if (!c) continue; const a = ((sh.orbit.from + (sh.orbit.to - sh.orbit.from) * e) * Math.PI) / 180; pts.push([[c[0] + Math.sin(a) * sh.orbit.radius, c[1] + (sh.orbit.height ?? 2), c[2] + Math.cos(a) * sh.orbit.radius], c]); continue; }
      const p0 = P(sh.pos, wt), p1 = sh.to ? P(sh.to, wt) : p0; if (!p0 || !p1) continue;
      const l0 = P(sh.look, wt), l1 = sh.lookTo ? P(sh.lookTo, wt) : l0;
      pts.push([p0.map((v, k) => v + (p1[k] - v) * e), l0 && l1 ? l0.map((v, k) => v + (l1[k] - v) * e) : null]);
    }
  });
  return pts;
}
function clearCameraFoliage() {
  if (story.clearFoliage === false) return 0;
  // a tree whose leaves touch the lens, or the first 6 blocks of the line of sight, is not planted at all (flood-fill its
  // leaves and logs): a clean frame instead of a camera buried in a canopy. Plants just in front of the lens are removed too.
  const TREE = /leaves|log/; let n = 0; const R = story.foliageClearance ?? 1.3;
  const removeTree = (k0) => { // flood the connected logs + leaves; delete only if it is a tree (has leaves), never a house's log pillars
    const q = [k0]; const seen = new Set([k0]); const comp = [];
    while (q.length && seen.size < 600) {
      const k = q.pop(); const b = grid.get(k); if (!b || !TREE.test(b)) continue; comp.push(k);
      const [x, y, z] = k.split(',').map(Number);
      for (const [dx, dy, dz] of [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]) { const k2 = `${x + dx},${y + dy},${z + dz}`; if (!seen.has(k2) && TREE.test(grid.get(k2) || '')) { seen.add(k2); q.push(k2); } }
    }
    if (!comp.some((k) => /leaves/.test(grid.get(k)))) return;
    for (const k of comp) { grid.delete(k); n++; }
  };
  const probe = (x, y, z, r) => {
    for (let dx = -2; dx <= 2; dx++) for (let dy = -2; dy <= 2; dy++) for (let dz = -2; dz <= 2; dz++) {
      const bx = Math.floor(x) + dx, by = Math.floor(y) + dy, bz = Math.floor(z) + dz;
      if (Math.hypot(bx + 0.5 - x, by + 0.5 - y, bz + 0.5 - z) > r) continue;
      const k = `${bx},${by},${bz}`; const b = grid.get(k); if (!b) continue;
      if (TREE.test(b)) removeTree(k); else if (defOf(b).shape === 'cross') { grid.delete(k); n++; }
    }
  };
  for (const [c, l] of cameraPath(0.2)) {
    probe(c[0], c[1], c[2], R);
    if (l) { const d = [l[0] - c[0], l[1] - c[1], l[2] - c[2]]; const L = Math.hypot(...d) || 1; for (let s2 = 0.6; s2 < Math.min(6, L - 1.5); s2 += 0.6) probe(c[0] + (d[0] / L) * s2, c[1] + (d[1] / L) * s2, c[2] + (d[2] / L) * s2, 0.9); }
  }
  window.__foliageCleared = n; return n;
}

async function buildWorld() {
  grid = expandWorld(story.world, story.seed ?? 1);
  snapToGround(); clearCameraFoliage();
  const ch = parseChanges(story, grid); worldFx = ch.fx;
  dynByKey = new Map(); for (const it of ch.insts) { const k = it.pos.join(','); (dynByKey.get(k) || dynByKey.set(k, []).get(k)).push(it); } dynKeys = ch.dynKeys;
  // static blocks: culled, shaded, smooth-lit meshes (core/engine/mesher.js)
  const { groups, light } = meshWorld(grid, defOf, ch.dynKeys); worldLight = light;
  for (const g of groups.values()) {
    const b = g.builder; if (!b.n) continue;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(b.pos, 3)); geo.setAttribute('normal', new THREE.Float32BufferAttribute(b.nor, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(b.uv, 2)); geo.setAttribute('color', new THREE.Float32BufferAttribute(b.col, 3));
    geo.setAttribute('mcLight', new THREE.Float32BufferAttribute(b.lit, 2)); geo.setIndex(b.idx); geo.computeBoundingSphere();
    const mesh = new THREE.Mesh(geo, await worldMaterial(g.tex, g.kind, g.flow));
    mesh.castShadow = g.kind !== 'translucent' && g.kind !== 'emissive'; mesh.receiveShadow = g.kind !== 'emissive';
    if (g.kind === 'translucent') mesh.renderOrder = 1;
    if (g.chunk) { const [cx, cz] = g.chunk.split(',').map(Number); mesh.userData.cx = (cx + 0.5) * CHUNK; mesh.userData.cz = (cz + 0.5) * CHUNK; }
    scene.add(mesh); worldMeshes.push(mesh);
  }
  const geo = new THREE.BoxGeometry(1, 1, 1); const m = new THREE.Matrix4();
  { // face shade per vertex for the dynamic cubes (BoxGeometry order: +x -x +y -y +z -z)
    const sh = [0.6, 0.6, 1, 0.5, 0.8, 0.8]; const col = []; for (let f = 0; f < 6; f++) for (let v = 0; v < 4; v++) col.push(sh[f], sh[f], sh[f]);
    geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  }
  // blocks that change over time (story.changes): one instanced mesh per block type, updated each frame
  const dby = {}; for (const it of ch.insts) (dby[it.block] ||= []).push(it);
  const white = new THREE.Color(1, 1, 1);
  for (const [b, list] of Object.entries(dby)) {
    const d = defOf(b); const kind = d.kind === 'emissive' ? 'emissive' : d.kind;
    const mats = await Promise.all(FACES.map((f) => worldMaterial(d.tex[f.slot], kind, d.flow)));
    const g2 = geo.clone(); const lit = new Float32Array(list.length * 2);
    list.forEach((it, i) => { // light of the brightest open neighbour (the block's own cell is solid)
      let best = [0, 0]; for (const f of FACES) { const l = light.at(it.pos[0] + f.n[0], it.pos[1] + f.n[1], it.pos[2] + f.n[2]); if (l[0] + l[1] > best[0] + best[1]) best = l; }
      lit[i * 2] = best[0] / 15; lit[i * 2 + 1] = best[1] / 15;
    });
    g2.setAttribute('mcLight', new THREE.InstancedBufferAttribute(lit, 2));
    const mesh = new THREE.InstancedMesh(g2, mats, list.length);
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
  props = await buildProps(THREE, scene, story.props, blockMaterials, { textCanvas });
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
  props.update(t);
  LIGHT_U.uTorchLit.value = props.litTorch() ? 1 : 0;
}

// -------------------------------------------------------------- player ----
function boxGeo(w, h, d, u, v, atlasHeight, grow = 0, depthGrow = grow) {
  const g = new THREE.BoxGeometry((w + grow * 2) * PX, (h + grow * 2) * PX, (d + depthGrow * 2) * PX);
  const uvRect = (x, y, width, height) => {
    // Keep the sampling footprint inside this face, even on glancing edges beside a filled hair texel.
    const inset = 1 / 32;
    const f = (px, py) => [px / 64, 1 - py / atlasHeight];
    return [f(x + inset, y + inset), f(x + width - inset, y + inset),
      f(x + inset, y + height - inset), f(x + width - inset, y + height - inset)];
  };
  const r = {
    top: uvRect(u + d, v, w, d), bottom: uvRect(u + d + w, v, w, d), right: uvRect(u, v + d, d, h),
    front: uvRect(u + d, v + d, w, h), left: uvRect(u + d + w, v + d, d, h), back: uvRect(u + 2 * d + w, v + d, w, h),
  };
  const order = ['left', 'right', 'top', 'bottom', 'front', 'back']; // three: +x -x +y -y +z -z (character faces +z)
  const uv = g.attributes.uv;
  const bounds = new THREE.Float32BufferAttribute(new Float32Array(uv.count * 4), 4);
  order.forEach((face, i) => {
    const [left, top] = r[face][0], [right, bottom] = r[face][3];
    r[face].forEach(([u, v], j) => {
      uv.setXY(i * 4 + j, u, v);
      bounds.setXYZW(i * 4 + j, left, bottom, right, top);
    });
  });
  uv.needsUpdate = true;
  g.setAttribute('skinBounds', bounds);
  return g;
}

function clampSkinUV(material) {
  // MSAA can interpolate outside the UV rectangle at grazing edges of a translucent skin face.
  // Clamp before sampling so a transparent hat side never picks up the hair texels of its neighbor.
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <uv_pars_vertex>', '#include <uv_pars_vertex>\nattribute vec4 skinBounds; varying vec4 vSkinBounds;')
      .replace('#include <uv_vertex>', '#include <uv_vertex>\nvSkinBounds = skinBounds;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <uv_pars_fragment>', '#include <uv_pars_fragment>\nvarying vec4 vSkinBounds;')
      .replace('#include <map_fragment>', THREE.ShaderChunk.map_fragment.replace('map, vMapUv', 'map, clamp(vMapUv, vSkinBounds.xy, vSkinBounds.zw)'));
  };
}

function detectSlim(img) {
  const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  const s = img.width / 64; const col = (x, y0, y1) => { const d = g.getImageData(x * s, y0 * s, 1, (y1 - y0) * s).data; for (let i = 3; i < d.length; i += 4) if (d[i]) return false; return true; };
  return col(55, 20, 32) && (img.height === 32 * s || col(47, 52, 64));
}

// a name tag like the game's: the game font on a 25 % black plate, 0.025 blocks per font pixel, always facing the camera
function nametag(text) {
  const tc = textCanvas([[text, '#ffffff']], 4, false); const pad = 4;
  const c = document.createElement('canvas'); c.width = tc.width + pad * 2; c.height = tc.height + pad; const g = c.getContext('2d');
  g.fillStyle = 'rgba(0,0,0,0.3)'; g.fillRect(0, 0, c.width, c.height); g.imageSmoothingEnabled = false; g.drawImage(tc, pad, pad);
  const t = new THREE.CanvasTexture(c); t.magFilter = THREE.NearestFilter; t.minFilter = THREE.LinearFilter; t.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true, fog: false }));
  sp.scale.set((c.width / 4) * 0.025, (c.height / 4) * 0.025, 1); sp.renderOrder = 5; return sp;
}

// Cached game geometry or one of the original BlockReel mob rigs.
let mobIndex = null;
async function makeMob(name, cfg) {
  const { scale, height } = actorSize(cfg, name);
  const wolf = cfg.type === 'wolf';
  if (wolf && cfg.rig !== undefined && !['builtin', 'vanilla'].includes(cfg.rig)) throw new Error(`Actor "${name}": wolf rig must be builtin or vanilla`);
  if (wolf && cfg.rig === 'builtin' && (cfg.geo || cfg.variant)) throw new Error(`Actor "${name}": wolf variants and custom geometry need the vanilla rig`);
  if (mobIndex === null) mobIndex = story.textures !== 'builtin' && await exists('/work/vanilla/mobs/index.json') ? (await getJSON('/work/vanilla/mobs/index.json')).mobs : {};
  let m;
  if (cfg.geo || (!(wolf && cfg.rig === 'builtin') && mobIndex[cfg.type])) {
    // "baby": true -> the game's own baby model and texture when it has one (else the adult at half size, head scaled by its scripts);
    // "variant": "cold" | "siamese" | "librarian"... -> another coat/breed/biome/profession (work/vanilla/mobs/index.json lists them)
    const ent = mobIndex[cfg.type] || {}; let geoFile = ent.geo, texFile = ent.texture ?? cfg.type + '.png'; let halve = false;
    const v = cfg.variant;
    if (v && !(ent.variants || {})[v] && !(cfg.baby && ent.baby && (ent.baby.variants || {})[v])) console.warn(`mob "${cfg.type}" has no variant "${v}"; known: ${Object.keys(ent.variants || {}).join(', ') || 'none'}`);
    if (cfg.baby && ent.baby) { geoFile = ent.baby.geo; texFile = (ent.baby.variants || {})[v] || ent.baby.texture; }
    else { const vv = (ent.variants || {})[v]; if (vv) { texFile = vv.texture; geoFile = vv.geo || geoFile; } halve = !!cfg.baby; }
    const geoUrl = cfg.geo ? resolve(cfg.geo) : `/work/vanilla/mobs/${geoFile}`;
    const texUrl = cfg.texture && (cfg.geo || !cfg.texture.startsWith('/core/builtin/')) ? resolve(cfg.texture) : `/work/vanilla/mobs/${texFile}`;
    const geo = await getJSON(geoUrl); // emissive mobs (blaze, magma cube, glow squid) carry a glow map: lit in the dark like the game
    const glowUrl = texUrl.replace(/\.png$/, '.glow.png');
    const glow = !cfg.texture && await exists(glowUrl) ? await pixelTex(glowUrl) : null;
    m = buildGeoModel(THREE, geo, await pixelTex(texUrl), { ...cfg, glow, scale: scale * (halve ? 0.5 : 1) });
  } else if (wolf && cfg.rig !== 'vanilla' && !cfg.variant) {
    const texture = await pixelTex(resolve(cfg.texture ?? '/core/builtin/mobs/wolf.png'));
    m = buildWolf(THREE, texture, { ...cfg, scale });
  } else {
    if (!['creeper', 'pig', 'spider'].includes(cfg.type)) throw new Error(`mob "${cfg.type}" needs the game's geometry: run python tools/vanilla.py mobs`);
    m = buildMob(THREE, cfg.type, await pixelTex(resolve(cfg.texture)), { ...cfg, scale });
  }
  if (height !== undefined) {
    const bounds = new THREE.Box3().setFromObject(m.root, true);
    const nativeHeight = bounds.max.y - bounds.min.y;
    if (!(nativeHeight > 0 && Number.isFinite(nativeHeight))) throw new Error(`Actor "${name}": cannot measure standing height`);
    const ratio = height / nativeHeight;
    m.root.scale.multiplyScalar(ratio);
    m.headY *= ratio;
    m.eyeY *= ratio;
    if (m.eyeZ !== undefined) m.eyeZ *= ratio;
  }
  m.root.position.set(...(cfg.pos || [0, 1, 0])); scene.add(m.root);
  if (cfg.nametag) { const sp = nametag(cfg.nametag); sp.position.set(0, m.headY / m.root.scale.x + 0.55, 0); m.root.add(sp); }
  m.head.rotation.order = 'YXZ';
  return { name, cfg, mob: m, mats: m.mats, root: m.root, head: m.head, face: { update() {} }, headY: m.headY, eyeY: m.eyeY, _pos: [...(cfg.pos || [0, 1, 0])], _heading: 0, _headPose: [0, 0, 0] };
}

// Resolve icons and in-hand sprites from the same asset definitions.
const itemCache = new Map();
const spriteUrls = new Map();
function spriteUrl(id, asset) {
  if (!spriteUrls.has(id)) spriteUrls.set(id, (async () => {
    if (asset.texture) {
      const url = resolve(asset.texture);
      if (await exists(url)) return url;
      throw new Error(`item "${id}" texture is missing: ${asset.texture}`);
    }
    const { name } = asset;
    const candidates = [`${BASE}items/${name}.png`, vanillaDir && `/work/vanilla/items/${name}.png`, `/core/builtin/items/${name}.png`];
    for (const url of candidates) if (url && await exists(url)) return url;
    return null;
  })());
  return spriteUrls.get(id);
}

async function itemIconUrl(id) {
  const asset = itemAsset(id, story.items);
  const sprite = await spriteUrl(id, asset);
  if (sprite) return sprite;
  const def = defOf(asset.name);
  return blockTexUrl(def.tex.side);
}

async function heldObject(id) {
  const asset = itemAsset(id, story.items);
  const url = await spriteUrl(id, asset);
  if (url) {
    if (!itemCache.has(url)) itemCache.set(url, pixelTex(url));
    const tex = await itemCache.get(url);
    const img = tex.image;
    if (asset.texture && (img.width > 128 || img.height > 128)) {
      throw new Error(`item "${id}" sprite must fit within 128 × 128 pixels`);
    }
    return { item: extrudeItem(THREE, img, tex, asset.size, asset.grip) };
  }
  const { name } = asset;
  if (window.__missing.includes(name)) return null;
  const mats = await blockMaterials(name);
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.34, 0.34), mats);
  mesh.castShadow = true;
  return { mesh };
}

async function makePlayer(name, cfg) {
  const { scale, height } = actorSize(cfg, name);
  const url = resolve(cfg.skin);
  const img = await loadImg(url);
  const tex = await pixelTex(url);
  let slim = cfg.model === 'slim' || ((cfg.model ?? 'auto') === 'auto' && detectSlim(img));
  const legacy = img.height === img.width / 2;
  const aw = slim ? 3 : 4;
  const atlasHeight = legacy ? 32 : 64;
  const box = (w, h, d, u, v, grow, depthGrow) => boxGeo(w, h, d, u, v, atlasHeight, grow, depthGrow);
  const base = new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.5, transparent: false });
  const over = new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.5, transparent: true });
  clampSkinUV(over);
  const root = new THREE.Group(); const inner = new THREE.Group(); root.add(inner);
  const upper = new THREE.Group(); upper.position.set(0, 12 * PX, 0); inner.add(upper); // hip pivot: torso, head and arms lean together
  const limb = (parent, w, h, d, u, v, ou, ov, pivot, shell, rise = 0) => {
    const g = new THREE.Group(); g.position.set(...pivot.map((c) => c * PX));
    // A tiny arm depth offset and distinct shell sizes prevent coplanar surfaces at skin seams.
    const a = new THREE.Mesh(box(w, h, d, u, v, 0, rise ? 0.025 : 0), base);
    a.position.y = (-h / 2 + rise) * PX; a.castShadow = true; g.add(a);
    if (!legacy) {
      const b = new THREE.Mesh(box(w, h, d, ou, ov, shell), over);
      b.position.y = a.position.y; g.add(b);
    }
    parent.add(g); return g;
  };
  const head = new THREE.Group(); head.position.set(0, 12 * PX, 0);
  const face = makeFace(THREE, img, head, PX, (t) => { t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; t.colorSpace = THREE.SRGBColorSpace; });
  const hm = new THREE.Mesh(box(8, 8, 8, 0, 0), face.material); hm.position.y = 4 * PX; hm.castShadow = true; head.add(hm);
  const hat = new THREE.Mesh(box(8, 8, 8, 32, 0, 0.5), over); hat.position.y = 4 * PX; head.add(hat); upper.add(head);
  const body = new THREE.Group(); body.position.set(0, 6 * PX, 0);
  const bm = new THREE.Mesh(box(8, 12, 4, 16, 16), base); bm.castShadow = true; body.add(bm);
  if (!legacy) body.add(new THREE.Mesh(box(8, 12, 4, 16, 32, 0.30), over));
  upper.add(body);
  const ax = 4 + aw / 2 + 0.05;
  const rArm = limb(upper, aw, 12, 4, 40, 16, 40, 32, [-ax, 10, 0], 0.40, 2);
  // Legacy 64x32 skins only have a head overlay and one side of the base limbs.
  const lArm = legacy ? limb(upper, aw, 12, 4, 40, 16, 0, 0, [ax, 10, 0], 0, 2) : limb(upper, aw, 12, 4, 32, 48, 48, 48, [ax, 10, 0], 0.40, 2);
  const rLeg = limb(inner, 4, 12, 4, 0, 16, 0, 32, [-2.02, 12, 0], 0.32);
  const lLeg = legacy ? limb(inner, 4, 12, 4, 0, 16, 0, 0, [2.02, 12, 0], 0) : limb(inner, 4, 12, 4, 16, 48, 0, 48, [2.02, 12, 0], 0.35);
  if (legacy) { lArm.scale.x = -1; lLeg.scale.x = -1; }
  // held items: everything this actor holds at any time (cfg.holding / cfg.offhand and timeline "holding" / "offhand" switches)
  const hands = { right: {}, left: {} };
  const wants = { right: new Set([cfg.holding].filter(Boolean)), left: new Set([cfg.offhand].filter(Boolean)) };
  for (const sg of story.timeline || []) if (sg.actor === name) { if (sg.holding) wants.right.add(sg.holding); if (sg.offhand) wants.left.add(sg.offhand); }
  for (const side of ['right', 'left']) for (const it of wants[side]) {
    const arm = side === 'right' ? rArm : lArm;
    if (it === 'shield' || it === 'minecraft:shield') { // the game's shield, upright along the outside of the forearm; turned to face forward while blocking
      const sh = await shieldMesh(THREE, pixelTex, exists); if (!sh) continue;
      const hold = new THREE.Group(); hold.position.set((side === 'left' ? 2.6 : -2.6) * PX, -7 * PX, 1.5 * PX); hold.rotation.y = (side === 'left' ? 1 : -1) * Math.PI / 2;
      sh.userData.shield = true; hold.add(sh); arm.add(hold); hold.visible = false; hands[side][it] = hold; continue;
    }
    const obj = await heldObject(it);
    if (!obj) continue;
    const g = obj.item ? mountItem(THREE, arm, obj.item, { left: side === 'left', tilt: cfg.itemTilt }) : (() => { const h = new THREE.Group(); h.position.set(0, -10.5 * PX, 5 * PX); obj.mesh.position.set(0, 0, 0); h.add(obj.mesh); arm.add(h); return h; })();
    if (side === 'left' && legacy) g.scale.x = -1;
    g.visible = false; hands[side][it] = g;
  }
  // name tag
  if (cfg.nametag) { const sp = nametag(cfg.nametag); sp.position.set(0, 2.32, 0); root.add(sp); }
  const sc = height === undefined ? scale : height / 2; root.scale.setScalar(sc);
  head.rotation.order = 'YXZ'; upper.rotation.order = 'YXZ';
  scene.add(root);
  const capeCues = (story.timeline || []).filter((s) => s.actor === name && 'cape' in s);
  const eq = await equip(THREE, { head, body, rArm, lArm, rLeg, lLeg }, cfg, pixelTex, exists, resolve, capeCues);
  for (const m of [base, over, face.material]) { m.emissiveMap = m.map; m.emissive = new THREE.Color(0, 0, 0); }
  return { name, cfg, root, inner, upper, head, body, rArm, lArm, rLeg, lLeg, face, hands, equip: eq, mats: [base, over, face.material], headY: 1.9 * sc, eyeY: 1.62 * sc, _pos: [...(cfg.pos || [0, 1, 0])], _heading: 0 };
}

// ----------------------------------------------------- actors (see anim.js) ----
// mounts are placed before their riders
let _order = null;
function actorOrder() {
  if (_order) return _order;
  const riders = new Set((story.timeline || []).filter((s) => s.mount).map((s) => s.actor));
  _order = [...Object.values(actors).filter((a) => !riders.has(a.name)), ...Object.values(actors).filter((a) => riders.has(a.name))];
  return _order;
}
const actorCtx = { posOf: (n, tt, depth) => (actors[n] ? actorState(story, actors[n], tt, actorCtx, depth).pos : [0, 0, 0]) };

function applyActor(a, t) {
  const st = actorState(story, a, t, actorCtx);
  a.root.visible = !st.hidden;
  if (a.mob) {
    a.mob.update(st, t);
    a._pos = [st.pos[0], st.pos[1] + st.jumpY, st.pos[2]];
    a.root.position.set(...a._pos); a.root.rotation.set(0, st.heading, 0);
    a._heading = st.heading; a._headPose = [a.head.rotation.x, a.head.rotation.y, a.head.rotation.z];
    a._hurt = hurtAt(story, a, t); a._clip = st.clip; return;
  }
  const p = st.pose;
  a._headPose = p.head;
  a.head.rotation.set(p.head[0], p.head[1], p.head[2]);
  a.rArm.rotation.set(p.rArm[0], p.rArm[1], p.rArm[2]); a.lArm.rotation.set(p.lArm[0], p.lArm[1], p.lArm[2]);
  a.rLeg.rotation.set(p.rLeg[0], p.rLeg[1], p.rLeg[2]); a.lLeg.rotation.set(p.lLeg[0], p.lLeg[1], p.lLeg[2]);
  a.upper.rotation.set(p.bodyRx + p.body[0], p.body[1], p.body[2]);
  a.root.position.set(st.pos[0], st.pos[1] + (p.bob - p.sink) * a.root.scale.x + st.jumpY, st.pos[2]);
  a.root.rotation.order = 'YXZ'; a.root.rotation.set(p.pitch || 0, st.heading + p.spinY, p.roll);
  a._pos = st.pos; a._heading = st.heading; a._hurt = hurtAt(story, a, t);
  if (a.hands) for (const side of ['right', 'left']) { // which item is in each hand now
    const key = side === 'right' ? 'holding' : 'offhand'; let cur = side === 'right' ? a.cfg.holding : a.cfg.offhand;
    for (const sg of story.timeline || []) { if (sg.actor !== a.name || sg.t > t) continue; if (key in sg) cur = sg[key]; }
    for (const [n, g] of Object.entries(a.hands[side])) {
      const shield = n === 'shield' || n === 'minecraft:shield';
      g.visible = n === cur; if (side === 'right' && !shield) g.rotation.x = p.wrist || 0;
      if (shield) { const blocking = /guard|block/.test(st.clip); g.rotation.set(blocking ? 1.1 : 0, (side === 'left' ? 1 : -1) * (blocking ? 0.15 : Math.PI / 2), 0); }
    }
  }
  if (a.equip) a.equip.update(st, t, (time) => clipState(story, a, time));
  a._clip = st.clip;
  // riding: { "do": "ride", "mount": "horse1" } puts the actor on the mount's saddle, turning with it (the mount moves itself)
  const mt = st.seg && st.seg.mount && actors[st.seg.mount];
  if (mt && st.clip === 'ride') {
    const seat = st.seg.seat ?? SEATS[mt.cfg.type] ?? Math.max(0.4, (mt.headY || 1.4) * 0.55); const back = st.seg.seatBack ?? SEAT_BACK[mt.cfg.type] ?? 0;
    const h = mt._heading; const pos = [mt._pos[0] - Math.sin(h) * back, mt._pos[1] + seat - 0.62 * a.root.scale.x, mt._pos[2] - Math.cos(h) * back];
    a.root.position.set(pos[0], pos[1], pos[2]); a.root.rotation.y = h + p.spinY; a._pos = pos; a._heading = h;
  }
}
// where a rider sits on each mount (feet height of the seat above the mount's feet, and how far back from its centre)
const SEATS = { horse: 1.45, donkey: 1.3, skeleton_horse: 1.45, zombie_horse: 1.45, llama: 1.45, camel: 2.1, pig: 0.85, strider: 1.6, minecart: 0.55, boat: 0.4, polar_bear: 1.4, ravager: 2.0, spider: 0.95 };
const SEAT_BACK = { horse: 0.1, donkey: 0.1, camel: 0.25, pig: 0.0 };

// head follows a look-at target (actor, [x,y,z] or "camera"); camPos is null until the camera is placed
function eyePoint(a) {
  const forward = a.mob?.eyeZ ?? 0;
  return [a._pos[0] + Math.sin(a._heading) * forward, a._pos[1] + a.eyeY, a._pos[2] + Math.cos(a._heading) * forward];
}
function targetPoint(tg, camPos) {
  if (tg === 'camera') return camPos ? [camPos.x, camPos.y, camPos.z] : null;
  if (Array.isArray(tg)) return tg;
  const o = actors[tg]; return o ? eyePoint(o) : null;
}
function applyLook(a, t, camPos) {
  const ls = lookState(story, a, t); const hp = a._headPose || [0, 0, 0];
  let dyaw = 0, dpitch = 0;
  if (ls) {
    const aim = (tg) => { if (tg === null || tg === undefined) return [0, 0]; const pt = targetPoint(tg, camPos); return pt ? aimAngles(eyePoint(a), a._heading, 0, pt, ls.limit) : [0, 0]; };
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
    pos = new THREE.Vector3(...eyePoint(a)).addScaledVector(fwd, 0.14 * a.root.scale.x); look = pos.clone().add(fwd);
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
// subtitles in the chat format (<Name> line) and titles, drawn with the game font; canvases are cached per string
const ovCache = new Map(); let lastSub = null, lastTitle = null;
let updateHud = null;
function applyOverlays(t) {
  const sub = document.getElementById('sub'); const title = document.getElementById('title');
  const W = story.size?.[0] ?? 1280, H = story.size?.[1] ?? 720;
  const s = (story.subtitles || []).find((x) => t >= x.t && t < x.t + (x.dur ?? 2));
  const sk = s ? `${s.who}|${s.text}|${s.color}` : null;
  if (sk !== lastSub) {
    lastSub = sk; sub.innerHTML = '';
    if (s) {
      const scale = Math.max(2, Math.round((H / 720) * (story.subtitleScale ?? 3)));
      const runs = [...(s.who ? [[`<${s.who}> `, s.color || '#ffd84a']] : []), [s.text, '#ffffff']];
      if (!ovCache.has(sk)) ovCache.set(sk, wrapRuns(runs, Math.floor((W * 0.74) / scale)).map((ln) => textCanvas(ln, scale)));
      const span = document.createElement('span'); span.style.cssText = 'display:inline-block;padding:.3em .55em .2em;line-height:0';
      for (const im of ovCache.get(sk)) { const d = document.createElement('div'); const c2 = document.createElement('canvas'); c2.width = im.width; c2.height = im.height; c2.getContext('2d').drawImage(im, 0, 0); c2.style.imageRendering = 'pixelated'; d.appendChild(c2); span.appendChild(d); }
      sub.appendChild(span);
    }
  }
  const ti = (story.titles || []).find((x) => t >= x.t && t < x.t + (x.dur ?? 2));
  if (ti) {
    const k = (t - ti.t); const fade = Math.min(1, k / 0.3, (ti.dur ?? 2) - k > 0.3 ? 1 : ((ti.dur ?? 2) - k) / 0.3); title.style.opacity = fade;
    const tk = `${ti.text}|${ti.color}|${ti.size}`;
    if (tk !== lastTitle) {
      lastTitle = tk; title.innerHTML = '';
      const scale = Math.max(2, Math.round(((ti.size || 64) / 8) * (H / 720)));
      for (const ln of String(ti.text).split('\n')) { const c = textCanvas([[ln, ti.color || '#ffffff']], scale); c.style.display = 'block'; c.style.margin = '0 auto'; title.appendChild(c); }
      title.style.flexDirection = 'column';
    }
  } else if (lastTitle !== null) { lastTitle = null; title.innerHTML = ''; }
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
  if (vanillaDir) cands.push(`${vanillaDir}/${tn}.png`);
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
  groundAt: (x, y, z) => { const ix = Math.floor(x), iz = Math.floor(z); for (let yy = Math.floor(y + 0.6); yy > Math.floor(y) - 160; yy--) if (grid.has(`${ix},${yy},${iz}`)) return yy + 1; return null; },
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
  renderer.debug.onShaderError = (gl, program, vertex, fragment) => {
    const logs = [gl.getProgramInfoLog(program), gl.getShaderInfoLog(vertex), gl.getShaderInfoLog(fragment)].filter(Boolean);
    renderError ??= ['WebGL shader compilation failed', ...logs].join('\n');
  };
  renderer.domElement.addEventListener('webglcontextlost', () => { renderError ??= 'WebGL context lost'; });
  renderer.setSize(W * RES / k, H * RES / k, false); renderer.setPixelRatio(1);
  maxAniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  renderer.shadowMap.enabled = !!style.shadows; renderer.shadowMap.type = THREE.PCFShadowMap;
  scene = new THREE.Scene();
  skyTex = skyTexture(THREE, style.sky.top, style.sky.bottom); // (kept for compatibility; the sky dome below draws the sky)
  if (style.fog) scene.fog = new THREE.Fog(style.sky.bottom, style.fog[0], style.fog[1]);
  camera = new THREE.PerspectiveCamera(style.fov || 60, W / H, 0.1, 400);
  ambientL = new THREE.AmbientLight(style.ambient.color, style.ambient.intensity); scene.add(ambientL);
  sun = new THREE.DirectionalLight(style.sun.color, style.sun.intensity);
  sun.position.set(...new THREE.Vector3(...style.sun.dir).normalize().multiplyScalar(60).toArray()); sun.castShadow = !!style.shadows;
  const SR = style.shadowRange ?? 24; const sc = sun.shadow.camera; sc.left = sc.bottom = -SR; sc.right = sc.top = SR; sc.near = 1; sc.far = 160;
  sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02;
  scene.add(sun); scene.add(sun.target);
  LIGHT_U.uDay.value = daylight(style.ambient, style.sun, style.daylight); if (style.blockLight) LIGHT_U.uBlockColor.value.set(style.blockLight);
  // blocks
  if (story.font !== 'css') await loadFont(story.fontDir || '/work/vanilla/font');
  blockDefs = (await getJSON('/core/builtin/blocks/index.json')).blocks;
  projBlocksDir = story.blocks ?? null;
  // original game textures (tools/vanilla.py fetch) sit between the project's own blocks and the CC0 built-ins; opt out with "textures": "builtin"
  vanillaDir = story.textures !== 'builtin' && await exists('/work/vanilla/blocks/index.json') ? '/work/vanilla/blocks' : null;
  if (vanillaDir) Object.assign(blockDefs, (await getJSON(`${vanillaDir}/index.json`)).blocks);
  window.__textures = vanillaDir ? 'vanilla' : 'builtin';
  if (projBlocksDir && await exists(`${BASE}${projBlocksDir}/index.json`)) Object.assign(blockDefs, (await getJSON(`${BASE}${projBlocksDir}/index.json`)).blocks);
  if (story.hud) updateHud = await createHud(story.hud, stage, W, H, lb ? barPct : 0, itemIconUrl);
  await buildWorld();
  for (const [n, cfg] of Object.entries(story.actors || {})) actors[n] = cfg.type && cfg.type !== 'player' ? await makeMob(n, cfg) : await makePlayer(n, cfg);
  particles = await buildParticles(THREE, scene, { ...story, fx: [...(story.fx || []), ...worldFx] }, particleCtx);
  // sky: dome, sun/moon (original textures when cached), stars, cloud layer (the game's cloud map when cached)
  const envDir = vanillaDir ? '/work/vanilla/env' : null; const envTex = async (n) => { for (const u of [envDir && `${envDir}/${n}.png`, `/core/builtin/env/${n}.png`]) if (u && await exists(u)) return pixelTex(u); return null; };
  let cloudMask = null;
  if (style.clouds && envDir && await exists(`${envDir}/clouds.png`)) {
    const im = await loadImg(`${envDir}/clouds.png`); const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const g = c.getContext('2d'); g.drawImage(im, 0, 0);
    const d = g.getImageData(0, 0, im.width, im.height).data; const data = new Uint8Array(im.width * im.height); for (let i = 0; i < data.length; i++) data[i] = d[i * 4 + 3] > 127 ? 1 : 0;
    cloudMask = { w: im.width, data };
  }
  const skyCfg = { ...(style.skyOptions || {}), ...(story.sky || {}) };
  sky = createSky(THREE, scene, { clouds: !!(skyCfg.clouds ?? style.clouds), cloudMask, sunTex: await envTex('sun'), moonTex: await envTex('moon'), ...skyCfg });
  lightning = (story.lightning || []).length ? createLightning(THREE, scene, story.lightning, particleCtx) : null;
  weather = createWeather(THREE, scene, story.weather || style.weather);
  const shotPosts = (story.camera || []).map((c) => c.post);
  if (usesPost(style.post, story.post, ...shotPosts)) post = createPost(THREE, renderer, scene, camera, Math.round(W * RES / k), Math.round(H * RES / k), [style.post, story.post, ...shotPosts]);
  window.__ready = true;
}

// ------------------------------------------------------------------- QA ----
// Automatic checks used by tools/qa.py (data only; the human still has to look at the frames).
function collectQA(t, camPos) {
  const W = story.size?.[0] ?? 1280, H = story.size?.[1] ?? 720;
  const wt = worldTime(story, t);
  const solid = (p) => {
    const block = blockAt(`${Math.floor(p.x)},${Math.floor(p.y)},${Math.floor(p.z)}`, wt);
    return block != null && !passableBlock(block);
  };
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
    out.actors[n] = { visiblePoints: vis, ndc: [chest.x, chest.y], behindCamera: chest.z >= 1, facingCamera: fwd.dot(toCam), visible: a.root.visible, distance: Math.hypot(camPos.x - a._pos[0], camPos.y - a._pos[1], camPos.z - a._pos[2]), insideBlock: solid(new THREE.Vector3(a._pos[0], a._pos[1] + a.headY * 0.5, a._pos[2])) };
  }
  const sp = document.querySelector('#sub span');
  if (sp) { const r = sp.getBoundingClientRect(), st = document.getElementById('stage').getBoundingClientRect(); out.subtitle = { clipped: r.left < st.left - 1 || r.right > st.right + 1 || r.top < st.top || r.bottom > st.bottom, width: r.width, height: r.height }; }
  return out;
}

// how much daylight reaches open-sky blocks (0 night .. 1 day): block light (torches) shows only where this is low
function daylight(amb, sunL, override) {
  if (typeof override === 'number') return override;
  const lum = (c) => { const x = new THREE.Color(c); return 0.2126 * x.r + 0.7152 * x.g + 0.0722 * x.b; };
  return clamp01((lum(amb.color) * amb.intensity + lum(sunL.color) * sunL.intensity * 0.5 - 0.6) / 1.2);
}
// actors take the light of the cell they stand in, like entities in the game (dark in caves, warm next to a torch)
function lightActors() {
  if (!worldLight) return;
  const day = LIGHT_U.uDay.value, cave = LIGHT_U.uCave.value; const curve = (l) => { const x = clamp01(l / 15); return x / (4 - 3 * x); };
  for (const a of Object.values(actors)) {
    if (!a.mats) continue;
    const [sk, bl] = worldLight.sample(a._pos[0], a._pos[1] + 0.5, a._pos[2]); const s = curve(sk), b = curve(bl);
    const k = (cave + (1 - cave) * s) * (a.mob && a.mob.flash ? 2.6 : 1); const warm = b * 1.0 * (1 - day * s); const hurt = a._hurt || 0;
    for (const m of a.mats) {
      m.color.setRGB(k, k * (1 - hurt * 0.6), k * (1 - hurt * 0.6));
      if (m.userData.glow) { m.emissive.setRGB(1, 1 - hurt * 0.5, 1 - hurt * 0.5); continue; } // glowing texels ignore the light
      m.emissive.setRGB(LIGHT_U.uBlockColor.value.r * warm + hurt * 0.45, LIGHT_U.uBlockColor.value.g * warm, LIGHT_U.uBlockColor.value.b * warm);
    }
  }
}
// chunks hidden by the fog are not drawn at all (big worlds cost only what can be seen); the frustum skips the rest
function cullChunks(camPos) {
  const far = (scene.fog ? scene.fog.far : 400) + CHUNK * 0.75;
  for (const m of worldMeshes) { if (m.userData.cx === undefined) continue; m.visible = Math.hypot(m.userData.cx - camPos.x, m.userData.cz - camPos.z) < far; }
}
// the sun's shadow box follows what the camera looks at (snapped to whole shadow texels, so shadows never crawl or flicker)
const _sv = new THREE.Vector3(), _sd = new THREE.Vector3();
function followShadow(camPos) {
  if (!sun.castShadow) return;
  camera.getWorldDirection(_sd); const R = style.shadowRange ?? 24;
  _sv.copy(camPos).addScaledVector(_sd, Math.min(R * 0.6, 14)); const texel = (2 * R) / sun.shadow.mapSize.x;
  _sv.x = Math.round(_sv.x / texel) * texel; _sv.y = Math.round(_sv.y / texel) * texel; _sv.z = Math.round(_sv.z / texel) * texel;
  const d = sun.position.clone().sub(sun.target.position).normalize();
  sun.target.position.copy(_sv); sun.position.copy(_sv).addScaledVector(d, 60); sun.target.updateMatrixWorld();
}

function applyLighting(t, wt, camPos) {
  const L = lightingAt(THREE, style, story.lighting || [], t);
  const flash = lightning ? lightning.update(wt) : 0;
  ambientL.color.set(L.ambient.color); ambientL.intensity = L.ambient.intensity + flash * 1.6;
  sun.color.set(L.sun.color); sun.intensity = L.sun.intensity;
  sun.position.copy(sun.target.position).add(new THREE.Vector3(...L.sun.dir).normalize().multiplyScalar(60));
  const key = (story.lighting || []).filter((x) => x.t <= t).pop();
  LIGHT_U.uDay.value = clamp01(daylight(L.ambient, L.sun, key?.daylight ?? style.daylight) + flash * 0.6);
  if (scene.fog && L.fog) { scene.fog.color.set(L.sky.bottom); if (flash) scene.fog.color.lerp(new THREE.Color(0.85, 0.9, 1), flash * 0.4); scene.fog.near = L.fog[0]; scene.fog.far = L.fog[1]; }
  sky && sky.update(L, LIGHT_U.uDay.value, camPos, camera, wt, flash);
}

function assertRenderHealthy() {
  if (renderer.getContext().isContextLost()) renderError ??= 'WebGL context lost';
  if (renderError) throw new Error(renderError);
}

window.__assertRenderHealthy = assertRenderHealthy;
window.renderAt = (t) => {
  assertRenderHealthy();
  const wt = worldTime(story, t); // speed ramps (story.timeRemap) bend world time only; cuts, subtitles, titles use t
  for (const a of actorOrder()) applyActor(a, wt);
  for (const a of Object.values(actors)) { const fs = faceStateAt(story, a, wt); if (a._clip === 'sleep') fs.eyes = 'closed'; a.face.update(fs); }
  updateWorld(wt); particles && particles.update(wt);
  for (const a of Object.values(actors)) applyLook(a, wt, null);
  const camPos = applyCamera(t, wt);
  for (const a of Object.values(actors)) { const ls = lookState(story, a, wt); if (ls && (ls.target === 'camera' || ls.prev === 'camera')) applyLook(a, wt, camPos); }
  applyLighting(t, wt, camPos); followShadow(camPos); lightActors(); cullChunks(camPos); weather && weather.update(wt, camPos);
  applyOverlays(t); updateHud?.(t, wt); applyTransitions(t);
  if (post) { const shot = currentShot(t) || {}; let fd; const f = shot.focus; if (f !== undefined) { const tp = (x) => { const v = typeof x === 'number' ? null : vec(x); return v ? camPos.distanceTo(v) : x; }; const f0 = tp(f), f1 = shot.focusTo !== undefined ? tp(shot.focusTo) : f0; const e = getEase(shot.ease || 'smooth')(clamp01((wt - worldTime(story, shot.t)) / (shot.dur ?? 3))); fd = f0 + (f1 - f0) * e; }
    post.render(t, [style.post, story.post, shot.post], fd); }
  else renderer.render(scene, camera);
  assertRenderHealthy();
  lastQA = { t, camPos: camPos.clone() };
  return true;
};
window.__qa = (t) => { window.renderAt(t); return collectQA(t, lastQA.camPos); };
window.__story = () => story;
window.__actorPos = (n, t) => { if (t !== undefined) window.renderAt(t); const a = actors[n]; return a ? [...a._pos, a._clip] : null; };

// Dense path check (tools/qa.py): walks the whole film every `step` seconds WITHOUT rendering and reports every interval in which
// an actor's body or the camera is inside a solid block of the world as it is at that moment (breaks, places and blasts included).
// Catches characters that spawn in a tree, cut through a wall between two sampled frames, or a camera that clips through a roof.
const PASSABLE = { has: (b) => passableBlock(b) };
function blockAt(k, t) {
  const its = dynByKey.get(k);
  if (its) { for (const it of its) if (blockState(it.evs, it.vis0, t).vis) return it.block; if (dynKeys.has(k)) return null; }
  return grid.get(k) ?? null;
}
window.__pathCheck = (step = 0.05) => {
  const dur = story.duration ?? 10; const open = {}; const out = { actors: [], camera: [] };
  const close = (key, list, t) => { const o = open[key]; if (o) { list.push({ ...o, t1: +t.toFixed(2) }); delete open[key]; } };
  for (let i = 0; i * step <= dur + 1e-6; i++) {
    const t = i * step, wt = worldTime(story, t);
    for (const a of actorOrder()) applyActor(a, wt);
    for (const [n, a] of Object.entries(actors)) {
      let hit = null;
      if (a._clip === 'ride') { if (open[n]) { close(n, out.actors, t); } continue; } // a rider sits inside its mount's box
      if (a.root.visible) {
        const scale = a.root.scale.x;
        const ys = [0.15 * scale, a.headY * 0.5, a.headY * 0.9];
        const bounds = a.mob?.footprint;
        let samples;
        if (bounds) {
          const s = Math.sin(a._heading), c = Math.cos(a._heading), w = bounds.width;
          samples = [[0, 0], [w, bounds.front], [-w, bounds.front], [w, bounds.back], [-w, bounds.back]]
            .map(([x, z]) => [scale * (x * c + z * s), scale * (-x * s + z * c)]);
        } else {
          const r = 0.22 * scale;
          samples = [[0, 0], [r, r], [r, -r], [-r, r], [-r, -r]];
        }
        outer: for (const y of ys) for (const [dx, dz] of samples) {
          const k = `${Math.floor(a._pos[0] + dx)},${Math.floor(a._pos[1] + y)},${Math.floor(a._pos[2] + dz)}`; const b = blockAt(k, wt);
          if (b && !PASSABLE.has(b)) { hit = { block: b, pos: k.split(',').map(Number) }; break outer; }
        }
      }
      if (hit && !open[n]) open[n] = { actor: n, t0: +t.toFixed(2), ...hit };
      else if (!hit) close(n, out.actors, t);
    }
    const cp = applyCamera(t, wt); const ck = `${Math.floor(cp.x)},${Math.floor(cp.y)},${Math.floor(cp.z)}`; const cb = blockAt(ck, wt);
    if (cb && !PASSABLE.has(cb)) { if (!open.__cam) open.__cam = { t0: +t.toFixed(2), block: cb, pos: ck.split(',').map(Number) }; }
    else close('__cam', out.camera, t);
  }
  for (const n of Object.keys(open)) close(n, n === '__cam' ? out.camera : out.actors, dur);
  window.renderAt(0);
  return out;
};

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
