// Face states for the player model: the 8x8 face region of the skin is repainted by time (eyes, mouth, wounds), and
// "glow" eyes add an emissive overlay. Works on any 64x64 (or scaled 128x128...) skin; colours are sampled from the skin.
//
// Face-local pixel grid (0,0 = top-left of the 8x8 face): eyes at cols 1-2 and 5-6, rows 3-4; mouth cols 2-5, rows 5-7.

const hash = (s) => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h; };
const VOWELS = 'aáàâãeéêèoóôõuúü';

// What the mouth does while `text` is spoken, `k` seconds after the line starts (~12.5 letters per second).
export function mouthForSpeech(text, k) {
  if (k < 0) return 'closed';
  const i = Math.floor(k * 12.5); if (i >= text.length) return 'closed';
  const ch = text[i].toLowerCase();
  if (ch === ' ' || /[.,!?…;:\-—'"]/.test(ch)) return 'closed';
  if ('bmp'.includes(ch)) return 'closed';
  if (VOWELS.includes(ch)) return ch === 'a' || ch === 'á' || ch === 'ã' || ch === 'â' || ch === 'à' ? 'shout' : 'open';
  return 'half';
}

export function faceStateAt(story, a, t) {
  const st = { eyes: 'open', mouth: 'closed', hurt: 0 };
  const es = a._faces || (a._faces = (story.faces || []).filter((f) => f.actor === a.name).sort((x, y) => x.t - y.t));
  for (const f of es) {
    if (f.t > t) break;
    if (f.dur !== undefined && t >= f.t + f.dur) continue; // temporary override expired
    for (const k of ['eyes', 'mouth', 'hurt']) if (k in f) st[k] = f[k];
  }
  if (st.eyes === 'open' && a.cfg.blink !== false) { // automatic blink, deterministic per actor
    const h = hash(a.name), period = 3.2 + (h % 7) * 0.17, off = (h % 13) * 0.31;
    if (((t + off) % period) < 0.13) st.eyes = 'closed';
  }
  if (st.mouth === 'closed' && story.lipsync !== false) { // mouth follows the subtitle spoken by this actor
    const nm = a.name.toLowerCase(), tag = (a.cfg.nametag || '').toLowerCase();
    const s = (story.subtitles || []).find((x) => t >= x.t && t < x.t + (x.dur ?? 2) && (x.actor === a.name || (x.who && [nm, tag].includes(String(x.who).toLowerCase()))));
    if (s) st.mouth = mouthForSpeech(s.text, t - s.t);
  }
  return st;
}

export function makeFace(THREE, img, head, PX, pixelFilters) {
  const s = img.width / 64;
  const canvas = document.createElement('canvas'); canvas.width = img.width; canvas.height = img.height;
  const g = canvas.getContext('2d', { willReadFrequently: true }); g.imageSmoothingEnabled = false; g.drawImage(img, 0, 0);
  const orig = g.getImageData(8 * s, 8 * s, 8 * s, 8 * s);
  const tex = new THREE.CanvasTexture(canvas); pixelFilters(tex);
  const material = new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.5, transparent: false });

  // skin colour = median of cheek pixels
  const cheek = [[0, 5], [1, 5], [6, 5], [7, 5], [0, 6], [7, 6]].map(([c, r]) => { const o = ((r * s) * 8 * s + c * s) * 4; return [orig.data[o], orig.data[o + 1], orig.data[o + 2]]; });
  const med = (i) => cheek.map((c) => c[i]).sort((a, b) => a - b)[Math.floor(cheek.length / 2)];
  const SK = [med(0), med(1), med(2)];
  const rgb = (c, k = 1) => `rgb(${Math.round(c[0] * k)},${Math.round(c[1] * k)},${Math.round(c[2] * k)})`;
  const px = (c, r, w, h, color) => { g.fillStyle = color; g.fillRect((8 + c) * s, (8 + r) * s, w * s, h * s); };

  const EYES = {
    closed: () => { px(1, 3, 2, 2, rgb(SK)); px(5, 3, 2, 2, rgb(SK)); px(1, 4, 2, 1, rgb(SK, 0.45)); px(5, 4, 2, 1, rgb(SK, 0.45)); },
    half: () => { px(1, 3, 2, 1, rgb(SK)); px(5, 3, 2, 1, rgb(SK)); },
    wide: () => { px(1, 2, 2, 3, '#fff'); px(5, 2, 2, 3, '#fff'); px(2, 3, 1, 2, '#15152a'); px(5, 3, 1, 2, '#15152a'); },
    angry: () => { px(1, 2, 2, 1, rgb(SK, 0.35)); px(5, 2, 2, 1, rgb(SK, 0.35)); px(2, 3, 1, 1, rgb(SK, 0.4)); px(5, 3, 1, 1, rgb(SK, 0.4)); },
    glow: () => { px(1, 3, 2, 2, '#fff'); px(5, 3, 2, 2, '#fff'); },
    dead: () => { for (const c of [1, 5]) { px(c, 3, 1, 1, '#222'); px(c + 1, 4, 1, 1, '#222'); px(c + 1, 3, 1, 1, '#222'); px(c, 4, 1, 1, '#222'); } },
  };
  const DARK = '#2b0e10';
  const MOUTH = {
    open: () => { px(2, 5, 4, 3, rgb(SK)); px(3, 6, 2, 2, DARK); },
    half: () => { px(2, 5, 4, 3, rgb(SK)); px(3, 6, 2, 1, DARK); },
    shout: () => { px(2, 5, 4, 3, rgb(SK)); px(2, 6, 4, 2, DARK); px(3, 7, 2, 1, '#8b2a2e'); },
    smile: () => { px(2, 5, 4, 3, rgb(SK)); px(2, 6, 4, 1, rgb(SK, 0.4)); px(2, 5, 1, 1, rgb(SK, 0.55)); px(5, 5, 1, 1, rgb(SK, 0.55)); },
    frown: () => { px(2, 5, 4, 3, rgb(SK)); px(2, 6, 4, 1, rgb(SK, 0.4)); px(2, 7, 1, 1, rgb(SK, 0.55)); px(5, 7, 1, 1, rgb(SK, 0.55)); },
  };
  const WOUNDS = [[1, 5], [6, 4], [2, 2], [5, 6], [3, 1]];

  // emissive overlay for glowing eyes: two flat white rectangles + one soft horizontal streak
  const eyeMat = new THREE.MeshBasicMaterial({ color: 0xffffff, fog: false });
  const c2 = document.createElement('canvas'); c2.width = 128; c2.height = 16; const g2 = c2.getContext('2d');
  const grad = g2.createLinearGradient(0, 0, 128, 0); grad.addColorStop(0, 'rgba(255,255,255,0)'); grad.addColorStop(0.5, 'rgba(255,255,255,1)'); grad.addColorStop(1, 'rgba(255,255,255,0)');
  g2.fillStyle = grad; g2.fillRect(0, 5, 128, 6); const g3 = g2.createLinearGradient(0, 0, 0, 16); g3.addColorStop(0, 'rgba(255,255,255,0)'); g3.addColorStop(0.5, 'rgba(255,255,255,.7)'); g3.addColorStop(1, 'rgba(255,255,255,0)');
  g2.globalCompositeOperation = 'destination-in'; g2.fillStyle = g3; g2.fillRect(0, 0, 128, 16);
  const streakMat = new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c2), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false, opacity: 0.5 });
  const glow = new THREE.Group(); glow.visible = false;
  for (const x of [-2, 2]) { const m = new THREE.Mesh(new THREE.PlaneGeometry(2 * PX, 2 * PX), eyeMat); m.position.set(x * PX, 4 * PX, 4.62 * PX); glow.add(m); }
  const streak = new THREE.Mesh(new THREE.PlaneGeometry(17 * PX, 2 * PX), streakMat); streak.position.set(0, 4 * PX, 4.7 * PX); glow.add(streak);
  head.add(glow);

  let key = '';
  return {
    material,
    update(st) {
      const k = `${st.eyes}|${st.mouth}|${st.hurt}`;
      if (k === key) return; key = k;
      g.putImageData(orig, 8 * s, 8 * s);
      if (EYES[st.eyes]) EYES[st.eyes]();
      if (MOUTH[st.mouth]) MOUTH[st.mouth]();
      for (let i = 0; i < Math.min(WOUNDS.length, Math.round(st.hurt || 0) * 2 + ((st.hurt || 0) > 1 ? 1 : 0)); i++) px(WOUNDS[i][0], WOUNDS[i][1], 1, 1, '#9a1414');
      tex.needsUpdate = true;
      glow.visible = st.eyes === 'glow';
    },
  };
}
