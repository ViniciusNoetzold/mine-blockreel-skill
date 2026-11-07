// A small Molang interpreter: the expression language the game uses for its entity animations
// ("math.cos(query.anim_time * 38.17) * 80.0", "variable.wing_flap - this", "q.is_baby ? 2 : 1").
// Expressions compile once into JS closures. Supported: numbers, strings, + - * / unary - !, comparisons, && || ?? ?:,
// parentheses, assignments and ';' statements, math.* (trigonometry in degrees, like the game), query.* / variable.* / temp.* /
// context.* (with the short forms q. v. t. c.) and `this`. Unknown queries and functions read as 0, so any animation evaluates.

const MATH = {
  sin: (d) => Math.sin(d * Math.PI / 180), cos: (d) => Math.cos(d * Math.PI / 180), abs: Math.abs, floor: Math.floor, ceil: Math.ceil,
  round: Math.round, trunc: Math.trunc, sqrt: Math.sqrt, pow: Math.pow, exp: Math.exp, ln: Math.log, min: Math.min, max: Math.max,
  clamp: (v, a, b) => Math.max(a, Math.min(b, v)), lerp: (a, b, t) => a + (b - a) * t, mod: (a, b) => a % b, pi: Math.PI,
  asin: (v) => Math.asin(v) * 180 / Math.PI, acos: (v) => Math.acos(v) * 180 / Math.PI, atan: (v) => Math.atan(v) * 180 / Math.PI,
  atan2: (y, x) => Math.atan2(y, x) * 180 / Math.PI, sign: Math.sign, hermite_blend: (t) => 3 * t * t - 2 * t * t * t,
  lerprotate: (a, b, t) => { const d = ((((b - a) % 360) + 540) % 360) - 180; return a + d * t; },
  random: (a, b) => a + (b - a) * 0.5, random_integer: (a, b) => Math.round((a + b) / 2), die_roll: (n, a, b) => n * (a + b) / 2,
  min_angle: (v) => { let a = v % 360; if (a >= 180) a -= 360; if (a < -180) a += 360; return a; },
};
const ALIAS = { q: 'query', v: 'variable', t: 'temp', c: 'context' };

function tokenize(src) {
  const out = []; let i = 0;
  while (i < src.length) {
    const ch = src[i];
    if (/\s/.test(ch)) { i++; continue; }
    if (/[0-9]/.test(ch) || (ch === '.' && /[0-9]/.test(src[i + 1] ?? ''))) { let j = i; while (j < src.length && /[0-9.]/.test(src[j])) j++; if (src[j] === 'f') j++; out.push({ t: 'num', v: parseFloat(src.slice(i, j)) }); i = j; continue; }
    if (/[A-Za-z_]/.test(ch)) { let j = i; while (j < src.length && /[A-Za-z0-9_.]/.test(src[j])) j++; out.push({ t: 'id', v: src.slice(i, j).toLowerCase() }); i = j; continue; }
    if (ch === "'" || ch === '"') { let j = i + 1; while (j < src.length && src[j] !== ch) j++; out.push({ t: 'str', v: src.slice(i + 1, j) }); i = j + 1; continue; }
    const two = src.slice(i, i + 2);
    if (['&&', '||', '<=', '>=', '==', '!=', '??', '->'].includes(two)) { out.push({ t: 'op', v: two }); i += 2; continue; }
    out.push({ t: 'op', v: ch }); i++;
  }
  return out;
}

const BP = { '=': 1, '?': 2, '??': 3, '||': 4, '&&': 5, '==': 6, '!=': 6, '<': 7, '>': 7, '<=': 7, '>=': 7, '+': 8, '-': 8, '*': 9, '/': 9 };

function parse(tokens) {
  let p = 0; const peek = () => tokens[p]; const next = () => tokens[p++];
  const expect = (v) => { const t = next(); if (!t || t.v !== v) throw new Error('molang: expected ' + v); };
  const ref = (name) => { const [head, ...rest] = name.split('.'); const ns = ALIAS[head] || head; return [ns, rest.join('.')]; };
  function nud(tk) {
    if (!tk) return () => 0;
    if (tk.t === 'num') { const v = tk.v; return () => v; }
    if (tk.t === 'str') { const v = tk.v; return () => v; }
    if (tk.v === '(') { const e = expr(0); expect(')'); return e; }
    if (tk.v === '{') { const body = statements('}'); expect('}'); return body; }
    if (tk.v === '-') { const e = expr(10); return (env) => -e(env); }
    if (tk.v === '+') return expr(10);
    if (tk.v === '!') { const e = expr(10); return (env) => (e(env) ? 0 : 1); }
    if (tk.t === 'id') {
      const name = tk.v;
      if (name === 'this') return (env) => env.this ?? 0;
      if (name === 'true') return () => 1; if (name === 'false') return () => 0;
      if (name === 'return') { const e = expr(0); return e; }
      if (peek() && peek().v === '(') { // function call
        next(); const args = []; while (peek() && peek().v !== ')') { args.push(expr(0)); if (peek() && peek().v === ',') next(); } expect(')');
        const [ns, fn] = ref(name);
        if (ns === 'math' && MATH[fn]) { const f = MATH[fn]; return (env) => f(...args.map((a) => a(env))); }
        return (env) => { const q = env.query[fn]; return typeof q === 'function' ? q(...args.map((a) => a(env))) : (typeof q === 'number' ? q : 0); };
      }
      const [ns, key] = ref(name);
      if (ns === 'math' && key === 'pi') return () => Math.PI;
      if (ns === 'query') return (env) => { const q = env.query[key]; return typeof q === 'function' ? q() : (q ?? 0); };
      return (env) => { const scope = env[ns] || (env[ns] = {}); return scope[key] ?? 0; };
    }
    return () => 0;
  }
  function expr(rbp) {
    let left = nud(next());
    for (;;) {
      const tk = peek(); if (!tk || tk.t !== 'op') break; const bp = BP[tk.v]; if (bp === undefined || bp <= rbp) break;
      next(); const op = tk.v; const l = left;
      if (op === '?') { const a = expr(0); let b = () => 0; if (peek() && peek().v === ':') { next(); b = expr(1); } left = (env) => (l(env) ? a(env) : b(env)); continue; }
      if (op === '=') { // assignment: the identifier is the token just before '='
        const id = tokens[p - 2]; const r = expr(0);
        if (id && id.t === 'id') { const [ns, key] = ref(id.v); left = (env) => { const v = r(env); (env[ns] || (env[ns] = {}))[key] = v; return v; }; } else left = r;
        continue;
      }
      const r = expr(op === '??' ? bp - 1 : bp);
      left = {
        '+': (e) => l(e) + r(e), '-': (e) => l(e) - r(e), '*': (e) => l(e) * r(e), '/': (e) => { const d = r(e); return d === 0 ? 0 : l(e) / d; },
        '<': (e) => +(l(e) < r(e)), '>': (e) => +(l(e) > r(e)), '<=': (e) => +(l(e) <= r(e)), '>=': (e) => +(l(e) >= r(e)),
        '==': (e) => +(l(e) === r(e)), '!=': (e) => +(l(e) !== r(e)), '&&': (e) => +(!!l(e) && !!r(e)), '||': (e) => +(!!l(e) || !!r(e)),
        '??': (e) => { const v = l(e); return v === undefined || v === null || v === 0 ? r(e) : v; },
      }[op];
    }
    return left;
  }
  function statements(end) {
    const list = [];
    while (p < tokens.length && !(end && peek().v === end)) { if (peek().v === ';') { next(); continue; } list.push(expr(0)); if (peek() && peek().v === ';') next(); }
    return (env) => { let v = 0; for (const s of list) v = s(env); return v; };
  }
  return statements(null);
}

const cache = new Map();
export function compile(src) {
  if (typeof src === 'number') return () => src;
  if (typeof src !== 'string') return () => 0;
  if (!cache.has(src)) { let f; try { f = parse(tokenize(src)); } catch { f = () => 0; } cache.set(src, f); }
  return cache.get(src);
}
export const evaluate = (src, env) => { const v = compile(src)(env); return typeof v === 'number' && isFinite(v) ? v : 0; };

// ----------------------------------------------------------------------------------------------- animations ----
// Evaluate an entity's animations at one instant: returns Map(boneName -> { rot:[x,y,z] deg, pos:[x,y,z] px, scale }) of offsets that
// add to the bind pose, like the game. `rest(bone)` gives the bind-pose rotation (for `this`).
export function animateEntity(geo, queries, rest) {
  const env = { query: queries, variable: {}, temp: {}, context: {} };
  for (const s of geo.pre || []) evaluate(s, env);
  const out = new Map(); const pivots = new Map((geo.bones || []).map((bn) => [bn.name.toLowerCase(), bn.pivot || [0, 0, 0]]));
  // which animations play: the entity's animate list; controllers resolve to their base animation (move_controller -> move);
  // situational ones (sleeping, sitting, riding, baby, attacks...) play only when the actor's clip asks for them
  const A = geo.anims || {};
  const resolveName = (n) => { if (A[n]) return n; if (n.endsWith('_controller')) { const b = n.slice(0, -11); for (const c of [b, b + '_default', b + '.rotations', b + '.v1.0']) if (A[c]) return c; } return null; };
  const allow0 = (n) => (queries.is_attacking && /attack|bare_hand/.test(n)) || (queries.is_sprinting && /sprint/.test(n)) || (queries.is_flying && /fly/.test(n)) || (queries.is_sitting && /sit/.test(n)) || (queries.is_sleeping && /sleep|bed|lie/.test(n)) || (queries.is_baby && /baby/.test(n)) || (/bare_hand/.test(n) && queries.undead_arms);
  // a baby animation plays for babies, unless it is also situational (baby_sit, baby_lie_down) and that situation is off
  const allow = (n) => { if (!/baby/.test(n)) return allow0(n); const rest = n.replace(/baby_?/g, ''); return !!queries.is_baby && (!SITUATIONAL.test(rest) || allow0(rest)); };
  const SITUATIONAL = /play_dead|bed|sleep|lying|rolling|sneez|unhappy|baby|sit|lie_?down|rear|eat|graz|swim|sneak|rid(e|ing)|spear|bow|holding|use_item|damage|scary|carry|charg|celebr|roar|sniff|dig|emerge|sonic|ram_|shake|beg|panic|stand|inflate|attack|bare_hand|spyglass|gliding|crossbow|tongue|croak|jump|sprint|fly|tame|angry|interest|look_at_player_while/;
  const entries = (geo.animate && geo.animate.length ? geo.animate : Object.keys(A));
  const list = [];
  // mobs whose state machine lives in code (axolotl): idle_* only standing, walk_* only moving, *_water / float only in water
  const names = entries.map((x) => (typeof x === 'string' ? x : Object.keys(x)[0]));
  const stateful = names.some((x) => /idle/.test(x)) && names.some((x) => /walk/.test(x));
  const stateOff = (n) => (/_water|float/.test(n) && !queries.is_in_water) || (stateful && ((/idle/.test(n) && queries.is_moving) || (/walk/.test(n) && !queries.is_moving)));
  for (const x of entries) {
    const [n0, c] = typeof x === 'string' ? [x, 1] : Object.entries(x)[0]; const n = resolveName(n0); if (!n) continue;
    if (SITUATIONAL.test(n) && !allow(n)) continue;
    if (stateOff(n)) continue;
    if (geo.nativeBaby && /baby_(transform|scal)/.test(n)) continue; // made to shrink the adult model; the game's baby model is already small
    let w = typeof c === 'number' ? c : evaluate(c, env); w = w || (allow(n) ? 1 : 0);
    // a gait driven by distance moved freezes mid-stride when the mob stops: the game fades it with the move speed
    if (typeof c === 'number' && /modified_distance_moved/.test(A[n].anim_time_update || '')) w *= queries.modified_move_speed || 0;
    list.push([n, w]);
  }
  for (const [name, weight] of list) {
    const an = A[name]; if (!an || !weight || !an.bones) continue;
    const len = an.animation_length || 0;
    let at = an.anim_time_update ? evaluate(an.anim_time_update, env) : queries.life_time;
    if (len && an.loop === true) at = ((at % len) + len) % len; else if (len) at = Math.min(at, len);
    env.query = { ...queries, anim_time: at };
    for (const [bone, ch] of Object.entries(an.bones)) {
      const b = bone.toLowerCase(); const o = out.get(b) || { rot: [0, 0, 0], pos: [0, 0, 0], scale: 1 }; out.set(b, o);
      void rest;
      const read = (val, i, cur) => { env.this = cur; return evaluate(val, env); };
      const chan = (v, at2) => { // a constant/expression triple, a single value, or keyframes {"0.0": [...], "0.5": [...]}
        if (Array.isArray(v) || typeof v !== 'object' || v === null) return v;
        const keys = Object.keys(v).map(Number).sort((a2, b2) => a2 - b2); if (!keys.length) return [0, 0, 0];
        const pick = (k) => { const x = v[Object.keys(v).find((kk) => Number(kk) === k)]; return Array.isArray(x) ? x : (x && (x.post || x.pre)) || [0, 0, 0]; };
        if (at2 <= keys[0]) return pick(keys[0]); if (at2 >= keys[keys.length - 1]) return pick(keys[keys.length - 1]);
        let i = 0; while (keys[i + 1] < at2) i++; const k0 = keys[i], k1 = keys[i + 1], u = (at2 - k0) / (k1 - k0 || 1);
        const A = pick(k0), B = pick(k1); return [0, 1, 2].map((j) => ({ lerp: [A[j], B[j], u] }));
      };
      const val3 = (v, cur) => {
        const c = chan(v, env.query.anim_time);
        if (!Array.isArray(c)) { const s = read(c, 0, cur[0]); return [s, s, s]; }
        return c.map((x, j) => (x && x.lerp ? evaluate(x.lerp[0], env) + (evaluate(x.lerp[1], env) - evaluate(x.lerp[0], env)) * x.lerp[2] : read(x, j, cur[j])));
      };
      if (ch.rotation !== undefined) { const r = val3(ch.rotation, o.rot.slice()); for (let j = 0; j < 3; j++) o.rot[j] += r[j] * weight; } // `this` = what earlier animations added (the game's meaning)
      if (ch.position !== undefined) { // legacy rigs (guardian) write absolute pivots: there `this` is the bone's own pivot
        const base = geo.absPos ? (pivots.get(b) || [0, 0, 0]).map((v, j) => v + o.pos[j]) : o.pos;
        const r = val3(ch.position, base); for (let j = 0; j < 3; j++) o.pos[j] += r[j] * weight;
      }
      if (ch.scale !== undefined) { const r = val3(ch.scale, [o.scale, o.scale, o.scale]); o.scale *= 1 + (r[0] - 1) * weight; }
    }
  }
  return out;
}
