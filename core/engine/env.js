// Environment: sky gradient texture, time-of-day lighting keyframes, and deterministic rain / snow.
import { ease, clamp01 } from './anim.js';

export function skyTexture(THREE, top, bottom, old) {
  const c = old ? old.image : document.createElement('canvas'); c.width = 4; c.height = 256;
  const g = c.getContext('2d'); const gr = g.createLinearGradient(0, 0, 0, 256); gr.addColorStop(0, top); gr.addColorStop(1, bottom); g.fillStyle = gr; g.fillRect(0, 0, 4, 256);
  const t = old || new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.needsUpdate = true; return t;
}

// story.lighting: [{ t, sky:{top,bottom}, ambient:{color,intensity}, sun:{color,intensity,dir}, fog:[near,far] }] (keys optional).
// Values interpolate smoothly between keyframes; before the first key the style's values are used.
export function lightingAt(THREE, style, keys, t) {
  const base = { sky: style.sky, ambient: style.ambient, sun: style.sun, fog: style.fog };
  if (!keys || !keys.length) return base;
  const ks = [{ t: -1e9, ...base }, ...keys.slice().sort((a, b) => a.t - b.t)];
  let i = 0; while (i + 1 < ks.length && ks[i + 1].t <= t) i++;
  const a = ks[i], b = ks[Math.min(i + 1, ks.length - 1)];
  const u = a === b ? 1 : ease.smooth(clamp01((t - Math.max(a.t, -1e8)) / Math.max(1e-6, b.t - Math.max(a.t, -1e8))));
  const mixc = (x, y) => '#' + new THREE.Color(x).lerp(new THREE.Color(y), u).getHexString();
  const mixn = (x, y) => x + (y - x) * u;
  const pick = (k) => ({ ...base[k], ...(a[k] || {}) }); const pickb = (k) => ({ ...pick(k), ...(b[k] || {}) });
  const A = { sky: pick('sky'), ambient: pick('ambient'), sun: pick('sun') }, B = { sky: pickb('sky'), ambient: pickb('ambient'), sun: pickb('sun') };
  const f0 = a.fog || base.fog, f1 = b.fog || f0;
  return {
    sky: { top: mixc(A.sky.top, B.sky.top), bottom: mixc(A.sky.bottom, B.sky.bottom) },
    ambient: { color: mixc(A.ambient.color, B.ambient.color), intensity: mixn(A.ambient.intensity, B.ambient.intensity) },
    sun: { color: mixc(A.sun.color, B.sun.color), intensity: mixn(A.sun.intensity, B.sun.intensity), dir: A.sun.dir.map((v, k) => mixn(v, B.sun.dir[k])) },
    fog: f0 ? [mixn(f0[0], f1[0]), mixn(f0[1], f1[1])] : null,
  };
}

// Rain / snow around the camera. Each drop is a pure function of time: it falls, wraps in a volume centred on the camera.
export function createWeather(THREE, scene, cfg) {
  if (!cfg || !cfg.type) return null;
  const rain = cfg.type === 'rain'; const n = Math.round((rain ? 1800 : 1400) * (cfg.density ?? 1));
  const clear = cfg.clear ?? 1.6; // drops closer than this to the lens read as huge streaks
  const R = cfg.radius ?? 14, Hh = cfg.height ?? 18, speed = cfg.speed ?? (rain ? 24 : 2.4), wind = cfg.wind ?? (rain ? 3 : 0.6);
  const geo = new THREE.BoxGeometry(rain ? 0.025 : 0.07, rain ? 0.55 : 0.07, rain ? 0.025 : 0.07);
  const mat = new THREE.MeshBasicMaterial({ color: rain ? 0xaec6ff : 0xffffff, transparent: true, opacity: rain ? 0.55 : 0.9, fog: true });
  const mesh = new THREE.InstancedMesh(geo, mat, n); mesh.frustumCulled = false; mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage); scene.add(mesh);
  const h = (i, s) => { const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453; return x - Math.floor(x); };
  const d = new THREE.Object3D();
  return {
    update(t, cam) {
      for (let i = 0; i < n; i++) {
        const ph = h(i, 1) * Hh, fall = (speed * t + ph) % Hh;
        const sway = rain ? 0 : Math.sin(t * 1.3 + i) * 0.4;
        let ox = (h(i, 2) - 0.5) * 2 * R, oz = (h(i, 3) - 0.5) * 2 * R;
        if (Math.abs(ox) < clear && Math.abs(oz) < clear) { ox += ox < 0 ? -clear : clear; oz += oz < 0 ? -clear : clear; } // keep drops away from the lens
        d.position.set(cam.x + ox + wind * (fall / Hh) + sway, cam.y + Hh * 0.5 - fall + 2, cam.z + oz);
        d.rotation.set(0, 0, rain ? -Math.atan2(wind, speed) : 0); d.updateMatrix(); mesh.setMatrixAt(i, d.matrix);
      }
      mesh.instanceMatrix.needsUpdate = true;
    },
  };
}

// ------------------------------------------------------------------------------------------------- sky ----
// A sky dome that follows the camera (the horizon stays on the horizon when the camera tilts), the square sun and moon on
// the light's direction, stars at night and the game's flat-topped cloud layer. Everything is a pure function of time.
const hash1 = (i, s) => { const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453; return x - Math.floor(x); };

export function createSky(THREE, scene, cfg) {
  const U = { top: { value: new THREE.Color() }, bottom: { value: new THREE.Color() }, sunDir: { value: new THREE.Vector3(0, 1, 0) },
    glow: { value: new THREE.Color('#ff7a3a') }, glowK: { value: 0 }, flash: { value: 0 } };
  const dome = new THREE.Mesh(new THREE.SphereGeometry(300, 32, 16), new THREE.ShaderMaterial({
    uniforms: U, side: THREE.BackSide, depthWrite: false, depthTest: false, fog: false,
    vertexShader: 'varying vec3 vDir; void main(){ vDir = position; vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_Position = p.xyww; }',
    fragmentShader: `uniform vec3 top, bottom, sunDir, glow; uniform float glowK, flash; varying vec3 vDir;
      void main(){ vec3 d = normalize(vDir); float y = d.y;
        vec3 c = mix(bottom, top, smoothstep(-0.02, 0.55, y));
        c = mix(c, bottom * 0.45, smoothstep(-0.02, -0.5, y));                                   // below the horizon: the darker void colour
        float s = max(0.0, dot(d, normalize(sunDir)));
        c += glow * glowK * (pow(s, 5.0) * 0.9 + 0.25) * (1.0 - smoothstep(0.0, 0.45, abs(y)));   // sunrise / sunset band around the sun
        c = mix(c, vec3(0.86, 0.9, 1.0), flash);
        gl_FragColor = vec4(c, 1.0);
        #include <colorspace_fragment>
      }`,
  }));
  dome.renderOrder = -10; dome.frustumCulled = false; scene.add(dome);
  const group = new THREE.Group(); scene.add(group);
  // sun and moon: flat squares like the game (additive), on the light direction; textures from the cache or the CC0 built-ins
  const quad = (tex, size, additive) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: true, fog: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending }));
    m.renderOrder = -9; m.frustumCulled = false; group.add(m); return m;
  };
  const sunM = cfg.sunTex ? quad(cfg.sunTex, 52, true) : null, moonM = cfg.moonTex ? quad(cfg.moonTex, 34, false) : null;
  // stars: seeded points on the upper sphere, fading in with the night
  const n = 900, sp = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { const z = hash1(i, 1) * 1.1 - 0.1, a = hash1(i, 2) * Math.PI * 2, r = Math.sqrt(Math.max(0, 1 - z * z)); sp[i * 3] = Math.cos(a) * r * 260; sp[i * 3 + 1] = z * 260; sp[i * 3 + 2] = Math.sin(a) * r * 260; }
  const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(sp, 3));
  const starMat = new THREE.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0, depthWrite: false, depthTest: true, fog: false });
  const stars = new THREE.Points(sg, starMat); stars.renderOrder = -9; stars.frustumCulled = false; group.add(stars);
  // clouds: the game's layer of 12x12x4 cells (scaled down to this film's scale), faces between cells culled, shaded per face
  let clouds = null;
  if (cfg.clouds) {
    const cell = cfg.cloudCell ?? 6, H = cfg.cloudThickness ?? 2, Y = cfg.cloudHeight ?? 34, mask = cfg.cloudMask; const N = mask ? mask.w : 64;
    const on = (i, j) => { const x = ((i % N) + N) % N, y = ((j % N) + N) % N; return mask ? mask.data[y * N + x] : (Math.sin(i * 0.9) + Math.sin(j * 0.7 + 1.3) + Math.sin((i + j) * 0.37) * 1.2 + hash1(i * 64 + j, 9) * 1.1) > 1.6; };
    const pos = [], col = [], idx = []; const R = Math.ceil((cfg.cloudRadius ?? 150) / cell);
    const face = (v, shade) => { const b = pos.length / 3; v.forEach((p) => { pos.push(...p); col.push(shade, shade, shade); }); idx.push(b, b + 1, b + 2, b, b + 2, b + 3); };
    for (let i = -R; i < R; i++) for (let j = -R; j < R; j++) {
      if (!on(i, j)) continue; const x0 = i * cell, x1 = x0 + cell, z0 = j * cell, z1 = z0 + cell, y0 = 0, y1 = H;
      face([[x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0]], 1.0); face([[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]], 0.7);
      if (!on(i + 1, j)) face([[x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1]], 0.85);
      if (!on(i - 1, j)) face([[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]], 0.85);
      if (!on(i, j + 1)) face([[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], 0.9);
      if (!on(i, j - 1)) face([[x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]], 0.9);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.setIndex(idx);
    clouds = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.82, depthWrite: true, fog: true }));
    clouds.position.y = Y; clouds.frustumCulled = false; clouds.renderOrder = 2; scene.add(clouds); clouds.userData = { Y, span: N * cell };
  }
  const tmp = new THREE.Vector3();
  return {
    // L: lightingAt() result, day: 0..1, cam: camera position, t: world time, flash: 0..1 (lightning)
    update(L, day, cam, camera, t, flash = 0) {
      U.top.value.set(L.sky.top); U.bottom.value.set(L.sky.bottom); U.flash.value = flash * 0.55;
      const d = new THREE.Vector3(...L.sun.dir).normalize(); U.sunDir.value.copy(d);
      U.glowK.value = cfg.sunsetGlow === false ? 0 : Math.max(0, 1 - Math.abs(d.y - 0.12) / 0.38) * (day > 0.25 ? 1 : 0) * 0.55;
      dome.position.copy(cam); group.position.copy(cam);
      const night = 1 - day; starMat.opacity = (cfg.stars ?? 1) * Math.max(0, night - 0.35) / 0.65 * (1 - flash);
      stars.rotation.y = t * 0.002;
      const place = (m, dir, show) => { if (!m) return; m.visible = show && dir.y > -0.15; tmp.copy(dir).multiplyScalar(240); m.position.copy(tmp); m.lookAt(0, 0, 0); m.material.opacity = Math.min(1, (dir.y + 0.15) / 0.2); };
      if (cfg.celestial !== false) { const isNight = day < 0.35; place(sunM, isNight ? d.clone().negate() : d, !isNight); place(moonM, isNight ? d : d.clone().negate(), true); }
      if (clouds) {
        const sp = clouds.userData.span; clouds.position.x = ((t * (cfg.cloudSpeed ?? 0.6)) % sp); clouds.position.z = 0;
        const c = new THREE.Color(L.sky.bottom).lerp(new THREE.Color(1, 1, 1), 0.55 * day + 0.1); clouds.material.color.copy(c).multiplyScalar(0.35 + 0.65 * day + flash * 0.5);
      }
    },
  };
}

// --------------------------------------------------------------------------------------------- lightning ----
// story.lightning: [{ t, pos: [x,z] | [x,y,z] | actor, dur: 0.45, seed }]. A jagged bolt of glowing boxes from the sky to the ground
// (like the game's), flickering 2-3 times, a point light at the strike and a sky/scene flash returned to the engine.
export function createLightning(THREE, scene, list, ctx) {
  const bolts = [];
  (list || []).forEach((L, k) => {
    let rng = L.seed ?? k * 7 + 3; const R = () => { rng = (rng * 16807) % 2147483647; return rng / 2147483647; };
    const g = new THREE.Group(); const mat = new THREE.MeshBasicMaterial({ color: 0xdfe6ff, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false, fog: false });
    const core = new THREE.MeshBasicMaterial({ color: 0xffffff, fog: false });
    let [x, z] = [0, 0]; let y0 = null;
    if (typeof L.pos === 'string') { const p = ctx.posOf(L.pos, L.t); x = p[0]; z = p[2]; y0 = p[1]; } else if (L.pos && L.pos.length === 3) { [x, y0, z] = L.pos; } else if (L.pos) [x, z] = L.pos;
    if (y0 === null) y0 = ctx.groundAt(x, 200, z) ?? 1;
    let px = x, pz = z, py = y0 + 70; const pts = [[px, py, pz]];
    while (py > y0) { py = Math.max(y0, py - (2 + R() * 4)); px += (R() - 0.5) * 3.2; pz += (R() - 0.5) * 3.2; if (py === y0) { px = x; pz = z; } pts.push([px, py, pz]); }
    for (let i = 1; i < pts.length; i++) {
      const a = new THREE.Vector3(...pts[i - 1]), b = new THREE.Vector3(...pts[i]); const len = a.distanceTo(b); const mid = a.clone().add(b).multiplyScalar(0.5);
      for (const [w, m] of [[0.55, mat], [0.18, core]]) { const s = new THREE.Mesh(new THREE.BoxGeometry(w, len + w, w), m); s.position.copy(mid); s.lookAt(b); s.rotateX(Math.PI / 2); g.add(s); }
      if (R() < 0.3 && i > 2) { const br = b.clone().add(new THREE.Vector3((R() - 0.5) * 6, -3 - R() * 3, (R() - 0.5) * 6)); const l2 = b.distanceTo(br); const s = new THREE.Mesh(new THREE.BoxGeometry(0.25, l2, 0.25), mat); s.position.copy(b.clone().add(br).multiplyScalar(0.5)); s.lookAt(br); s.rotateX(Math.PI / 2); g.add(s); }
    }
    const pl = new THREE.PointLight(0xcfd8ff, 0, 26, 1.4); pl.position.set(x, y0 + 2, z); g.add(pl);
    g.visible = false; scene.add(g); bolts.push({ L, g, pl, dur: L.dur ?? 0.45 });
  });
  return {
    update(t) {
      let flash = 0;
      for (const b of bolts) {
        const u = (t - b.L.t) / b.dur; const on = u >= 0 && u <= 1 && (u < 0.18 || (u > 0.32 && u < 0.5) || (u > 0.68 && u < 0.8));
        b.g.visible = on; b.pl.intensity = on ? 60 : 0;
        if (u >= 0 && u < 1.6) flash = Math.max(flash, on ? 1 : Math.max(0, 0.35 * (1 - (u - 1) / 0.6)) * (u > 1 ? 1 : 0.6));
      }
      return flash;
    },
  };
}
