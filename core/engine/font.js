// The game's bitmap font for name tags, chat subtitles and titles. Glyph sheets come from the local cache
// (python tools/vanilla.py font -> work/vanilla/font/); without it a crisp pixel fallback is drawn from a monospace CSS font.
// Text is rendered into canvases at an integer pixel scale with the game's 1 px drop shadow (25 % brightness).

const glyphs = new Map(); // char -> { img, sx, sy, cw, ch, adv, scale, top }
let ready = false;

export async function loadFont(base = '/work/vanilla/font') {
  try {
    const r = await fetch(`${base}/font.json`); if (!r.ok) return false;
    const meta = await r.json();
    for (const p of meta.providers) {
      const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `${base}/${p.file}`; });
      const rows = p.chars.map((s) => Array.from(s)); const cols = Math.max(...rows.map((r) => r.length));
      const cw = img.width / cols, ch = img.height / rows.length; const sc = p.height / ch; // glyph pixels -> font pixels
      const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
      const data = g.getImageData(0, 0, img.width, img.height).data;
      rows.forEach((row, ry) => row.forEach((chr, rx) => {
        if (chr === '\u0000' || chr === ' ' || glyphs.has(chr)) return;
        let right = -1;
        for (let x = cw - 1; x >= 0 && right < 0; x--) for (let y = 0; y < ch; y++) if (data[((ry * ch + y) * img.width + rx * cw + x) * 4 + 3] > 0) { right = x; break; }
        if (right < 0) return;
        glyphs.set(chr, { img: c, sx: rx * cw, sy: ry * ch, cw: right + 1, ch, adv: Math.round((right + 1) * sc) + 1, scale: sc, top: 7 - p.ascent });
      }));
    }
    ready = glyphs.size > 0; return ready;
  } catch { return false; }
}
export const fontReady = () => ready;

// width in font pixels (1 font pixel = `scale` screen pixels)
export function measure(text) { let w = 0; for (const c of Array.from(text)) w += c === ' ' ? 4 : (glyphs.get(c)?.adv ?? 6); return Math.max(0, w - 1); }

// runs: [[text, '#rrggbb'], ...]  ->  canvas (scale = screen pixels per font pixel)
export function textCanvas(runs, scale = 2, shadow = true) {
  if (typeof runs === 'string') runs = [[runs, '#ffffff']];
  if (!ready) return cssText(runs, scale, shadow);
  const W = runs.reduce((a, [t]) => a + measure(t) + 1, 0) + 1, H = 10;
  const c = document.createElement('canvas'); c.width = (W + 1) * scale; c.height = (H + 1) * scale; const g = c.getContext('2d'); g.imageSmoothingEnabled = false;
  const draw = (dx, dy, dim) => {
    let x = 0;
    for (const [text, col] of runs) {
      const tmp = document.createElement('canvas'); tmp.width = c.width; tmp.height = c.height; const tg = tmp.getContext('2d'); tg.imageSmoothingEnabled = false;
      let x0 = x;
      for (const ch of Array.from(text)) {
        if (ch === ' ') { x += 4; continue; }
        const gl = glyphs.get(ch); if (!gl) { x += 6; continue; }
        tg.drawImage(gl.img, gl.sx, gl.sy, gl.cw, gl.ch, (x + dx) * scale, (gl.top + 1 + dy) * scale, gl.cw * gl.scale * scale, gl.ch * gl.scale * scale);
        x += gl.adv;
      }
      tg.globalCompositeOperation = 'source-in'; tg.fillStyle = dim ? shadeHex(col, 0.25) : col; tg.fillRect(0, 0, tmp.width, tmp.height);
      g.drawImage(tmp, 0, 0); void x0;
    }
  };
  if (shadow) draw(1, 1, true);
  draw(0, 0, false);
  return c;
}

function shadeHex(h, k) { const n = parseInt(h.slice(1), 16); const r = ((n >> 16) & 255) * k, gg = ((n >> 8) & 255) * k, b = (n & 255) * k; return `rgb(${r | 0},${gg | 0},${b | 0})`; }

// fallback: draw small with a monospace font, then scale up with nearest-neighbour for the pixel look
function cssText(runs, scale, shadow) {
  const text = runs.map((r) => r[0]).join(''); const fs = 9; const m = document.createElement('canvas').getContext('2d'); m.font = `bold ${fs}px monospace`;
  const W = Math.ceil(m.measureText(text).width) + 3, H = 12;
  const small = document.createElement('canvas'); small.width = W; small.height = H; const g = small.getContext('2d'); g.font = `bold ${fs}px monospace`; g.textBaseline = 'top';
  const pass = (dx, dim) => { let x = 0; for (const [t, col] of runs) { g.fillStyle = dim ? shadeHex(col, 0.25) : col; g.fillText(t, x + dx, 1 + dx); x += g.measureText(t).width; } };
  if (shadow) pass(1, true); pass(0, false);
  const c = document.createElement('canvas'); c.width = W * scale; c.height = H * scale; const cg = c.getContext('2d'); cg.imageSmoothingEnabled = false; cg.drawImage(small, 0, 0, c.width, c.height);
  return c;
}

// wrap words so each line fits maxW font pixels; returns array of run-lists
export function wrapRuns(runs, maxW) {
  const words = []; for (const [t, col] of runs) for (const w of t.split(/(\s+)/)) if (w) words.push([w, col]);
  const lines = [[]]; let w = 0;
  for (const [t, col] of words) {
    const tw = /^\s+$/.test(t) ? 4 : measure(t) + 1;
    if (w + tw > maxW && w > 0 && !/^\s+$/.test(t)) { lines.push([]); w = 0; }
    if (w === 0 && /^\s+$/.test(t)) continue;
    lines[lines.length - 1].push([t, col]); w += tw;
  }
  return lines;
}
