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
