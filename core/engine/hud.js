// Opt-in Minecraft-style film UI. All inventory changes are evaluated before playback.
const HOTBAR = 9;
const INVENTORY = 27;

function time(value, label, minimum = 0) {
  if (!Number.isFinite(value) || value < minimum) throw new Error(`hud: invalid ${label}`);
  return value;
}

function slotIndex(value, length) {
  if (!Number.isInteger(value) || value < 0 || value >= length) throw new Error(`hud: invalid slot ${value}`);
  return value;
}

function slotsOf(value, count, readStack) {
  if (!Array.isArray(value) || value.length > count) throw new Error(`hud: expected up to ${count} slots`);
  return Array.from({ length: count }, (_, i) => readStack(value[i]));
}

function takeCraft(state, grid, result, toSlot, t) {
  const needed = new Map();
  for (const stack of grid) if (stack) needed.set(stack.item, (needed.get(stack.item) ?? 0) + stack.count);
  for (const area of [state.inventory, state.hotbar]) {
    for (let i = 0; i < area.length; i++) {
      const stack = area[i];
      if (!stack || !needed.has(stack.item)) continue;
      const take = Math.min(stack.count, needed.get(stack.item));
      const count = stack.count - take;
      area[i] = count ? { ...stack, count } : null;
      needed.set(stack.item, needed.get(stack.item) - take);
    }
  }
  for (const [item, count] of needed) {
    if (count) throw new Error(`hud: crafting at ${t}s is missing ${count} × ${item}`);
  }

  const area = toSlot === undefined ? [...state.hotbar, ...state.inventory] : state.hotbar;
  const matching = area.findIndex((s) => s?.item === result.item);
  const free = area.indexOf(null);
  const index = toSlot ?? (matching >= 0 ? matching : free);
  const target = index < HOTBAR ? state.hotbar : state.inventory;
  const slot = index < HOTBAR ? index : index - HOTBAR;
  const before = target[slot];
  if (index < 0 || (before && before.item !== result.item)) throw new Error(`hud: no free slot for ${result.item} at ${t}s`);
  target[slot] = { item: result.item, count: result.count + (before?.count ?? 0) };
}

export function compileHud(hud) {
  const itemIds = new Set();
  const stack = (value) => {
    if (value == null) return null;
    const { item, count = 1 } = typeof value === 'string' ? { item: value } : value;
    if (typeof item !== 'string' || !item.trim() || !Number.isSafeInteger(count) || count <= 0) {
      throw new Error('hud: each stack requires a nonempty item and a positive integer count');
    }
    itemIds.add(item);
    return { item, count };
  };
  const initial = {
    hotbar: slotsOf(hud.hotbar?.slots ?? [], HOTBAR, stack),
    inventory: slotsOf(hud.inventory ?? [], INVENTORY, stack),
    selected: slotIndex(hud.hotbar?.selected ?? 0, HOTBAR),
    visible: hud.hotbar != null && hud.hotbar !== false,
  };
  const messages = (hud.chat?.messages ?? []).map((msg) => {
    time(msg.t, 'chat time');
    if (typeof msg.text !== 'string' || !msg.text.trim()) throw new Error('hud: expected chat text');
    return { ...msg, dur: time(msg.dur ?? 7, 'chat duration', Number.EPSILON) };
  }).sort((a, b) => a.t - b.t);
  const limit = hud.chat?.maxLines ?? 5;
  if (!Number.isInteger(limit) || limit < 1 || limit > 10) throw new Error('hud: maxLines must be an integer from 1 to 10');

  const panels = [];
  const changes = [];
  for (const event of hud.events ?? []) {
    const t = time(event.t, 'event time');
    switch (event.type) {
      case 'select': {
        const selected = slotIndex(event.slot, HOTBAR);
        changes.push({ t, apply: (state) => { state.selected = selected; } });
        break;
      }
      case 'hotbar': {
        if (typeof event.visible !== 'boolean') throw new Error('hud: hotbar events require visible: true or false');
        changes.push({ t, apply: (state) => { state.visible = event.visible; } });
        break;
      }
      case 'set': {
        const area = event.area ?? 'hotbar';
        if (area !== 'hotbar' && area !== 'inventory') throw new Error(`hud: invalid area ${area}`);
        const index = slotIndex(event.slot, initial[area].length);
        const value = stack(event.stack);
        changes.push({ t, apply: (state) => { state[area][index] = value; } });
        break;
      }
      case 'inventory':
        panels.push({ type: event.type, t, end: t + time(event.dur, 'inventory duration', Number.EPSILON) });
        break;
      case 'craft': {
        const end = t + time(event.dur, 'craft duration', Number.EPSILON);
        const gridSize = event.gridSize ?? 3;
        if (gridSize !== 2 && gridSize !== 3) throw new Error('hud: crafting gridSize must be 2 or 3');
        const grid = slotsOf(event.grid, gridSize ** 2, stack);
        const result = stack(event.result);
        if (!grid.some(Boolean) || !result) throw new Error('hud: craft requires ingredients and a result');
        const takeAt = event.takeAt;
        if (takeAt !== undefined) {
          time(takeAt, 'craft takeAt', t);
          if (takeAt >= end) throw new Error('hud: craft takeAt must be inside its panel interval');
          if (event.toSlot !== undefined) slotIndex(event.toSlot, HOTBAR);
          changes.push({ t: takeAt, apply: (state) => takeCraft(state, grid, result, event.toSlot, takeAt) });
        }
        panels.push({ type: event.type, t, end, grid, gridSize, result, takeAt });
        break;
      }
      default:
        throw new Error(`hud: unknown event type ${event.type}`);
    }
  }
  panels.sort((a, b) => a.t - b.t);
  if (panels.some((panel, i) => i && panel.t < panels[i - 1].end)) throw new Error('hud: inventory and craft panels overlap');

  const snapshots = [{ t: -Infinity, state: initial }];
  for (const change of changes.sort((a, b) => a.t - b.t)) {
    const previous = snapshots.at(-1).state;
    const state = { ...previous, hotbar: [...previous.hotbar], inventory: [...previous.inventory] };
    change.apply(state);
    snapshots.push({ t: change.t, state });
  }

  return {
    itemIds,
    at(t, worldTime = t) {
      const state = snapshots.findLast((entry) => entry.t <= t).state;
      const panel = panels.find((entry) => entry.t <= t && t < entry.end);
      const chat = messages.filter((msg) => {
        const now = msg.clock === 'world' ? worldTime : t;
        return msg.t <= now && now < msg.t + msg.dur;
      }).slice(-limit);
      return { state, panel, taken: panel?.takeAt !== undefined && t >= panel.takeAt, chat };
    },
  };
}

const CSS = `
#br-hud { inset: 0; }
.br-hud-chat { position: absolute; left: calc(7 * var(--u)); max-width: 58%; display: grid; justify-items: start; gap: calc(1 * var(--u)); }
.br-hud-line { color: #fff; background: #111b; padding: calc(1 * var(--u)) calc(3 * var(--u)); font-size: calc(9 * var(--u)); line-height: 1.2; text-shadow: 2px 2px #292929; overflow-wrap: anywhere; }
.br-hud-panel { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); display: grid; gap: calc(4 * var(--u)); padding: calc(6 * var(--u)); color: #3c3c3c; background: #c5c5c5; border: calc(2 * var(--u)) solid #202020; box-shadow: inset calc(2 * var(--u)) calc(2 * var(--u)) #f3f3f3, inset calc(-2 * var(--u)) calc(-2 * var(--u)) #646464; }
.br-hud-panel[hidden], .br-hud-hotbar[hidden] { display: none; }
.br-hud-title { font-size: calc(9 * var(--u)); font-weight: bold; }
.br-hud-craft { display: flex; align-items: center; gap: calc(8 * var(--u)); }
.br-hud-grid { display: grid; grid-template-columns: repeat(var(--cols), calc(18 * var(--u))); }
.br-hud-hotbar { position: absolute; left: 50%; transform: translateX(-50%); padding: calc(1 * var(--u)); background: #171717; box-shadow: 0 0 0 calc(1 * var(--u)) #9b9b9b; }
.br-hud-slot { width: calc(18 * var(--u)); height: calc(18 * var(--u)); position: relative; display: grid; place-items: center; box-sizing: border-box; background: #8b8b8b; border: calc(1 * var(--u)) solid; border-color: #383838 #fff #fff #383838; }
.br-hud-hotbar .br-hud-slot { background: #343434d9; border-color: #656565 #222 #222 #656565; }
.br-hud-slot.selected { outline: calc(1 * var(--u)) solid #fff; z-index: 1; }
.br-hud-slot img { width: 85%; height: 85%; object-fit: contain; image-rendering: pixelated; }
.br-hud-count { position: absolute; bottom: 0; right: 0; color: white; font: bold calc(7 * var(--u))/1 monospace; text-shadow: 2px 2px #252525; }
.br-hud-fallback { width: 75%; color: white; background: #4a514f; text-align: center; font-size: calc(8 * var(--u)); }
`;

const element = (tag, cls, text) => {
  const el = document.createElement(tag);
  el.className = cls;
  if (text !== undefined) el.textContent = text;
  return el;
};

export async function createHud(config, stage, width, height, barPct, itemIconUrl) {
  const model = compileHud(config);
  const icons = new Map(await Promise.all([...model.itemIds].map(async (id) => {
    const url = await itemIconUrl(id);
    if (!url) return [id, null];
    const image = new Image();
    image.src = url;
    await image.decode();
    return [id, image];
  })));
  const u = Math.max(1, Math.min(width / 420, height / 360, height * (1 - barPct * 0.02) / 270));
  const margin = height * barPct / 100 + 7 * u;
  const hud = element('div', 'ov');
  hud.id = 'br-hud';
  hud.style.setProperty('--u', `${u}px`);
  const css = element('style', '', CSS);
  const chat = element('div', 'br-hud-chat');
  const panel = element('div', 'br-hud-panel');
  const hotbar = element('div', 'br-hud-hotbar');
  panel.hidden = hotbar.hidden = true;
  hotbar.style.bottom = `${margin}px`;
  hud.append(css, chat, panel, hotbar);
  stage.insertBefore(hud, stage.querySelector('#fade'));

  const label = (key, fallback) => config.labels?.[key] ?? fallback;
  function drawGrid(stacks, columns, selected = -1) {
    const grid = element('div', 'br-hud-grid');
    grid.style.setProperty('--cols', columns);
    for (let i = 0; i < stacks.length; i++) {
      const slot = element('div', 'br-hud-slot' + (selected === i ? ' selected' : ''));
      const stack = stacks[i];
      if (stack) {
        slot.title = stack.item;
        const image = icons.get(stack.item);
        if (image) {
          const clone = image.cloneNode();
          clone.alt = stack.item;
          slot.append(clone);
        } else {
          const initial = stack.item.split(':').at(-1).slice(0, 2).toUpperCase();
          slot.append(element('span', 'br-hud-fallback', initial));
        }
        if (stack.count > 1) slot.append(element('span', 'br-hud-count', String(stack.count)));
      }
      grid.append(slot);
    }
    return grid;
  }

  let previous = {};
  return (t, wt) => {
    const { state, panel: active, taken, chat: messages } = model.at(t, wt);
    if (state !== previous.state || active !== previous.active || taken !== previous.taken) {
      hotbar.hidden = !state.visible || !!active;
      hotbar.replaceChildren(...(hotbar.hidden ? [] : [drawGrid(state.hotbar, 9, state.selected)]));
      panel.hidden = !active;
      panel.replaceChildren();
      if (active) {
        if (active.type === 'craft') {
          panel.append(element('div', 'br-hud-title', label('crafting', 'Crafting')));
          const row = element('div', 'br-hud-craft');
          row.append(drawGrid(taken ? active.grid.map(() => null) : active.grid, active.gridSize),
            element('span', 'br-hud-title', '→'), drawGrid([taken ? null : active.result], 1));
          panel.append(row);
        }
        panel.append(element('div', 'br-hud-title', label('inventory', 'Inventory')),
          drawGrid(state.inventory, 9), drawGrid(state.hotbar, 9, state.selected));
      }
    }
    if (messages.length !== previous.messages?.length || messages.some((msg, i) => msg !== previous.messages[i])) {
      chat.replaceChildren(...messages.map((msg) => {
        const line = element('div', 'br-hud-line', msg.who ? `<${msg.who}> ${msg.text}` : msg.text);
        line.style.color = msg.color ?? '';
        return line;
      }));
    }
    const sub = stage.querySelector('#sub');
    const bottom = margin + (!hotbar.hidden ? 21 * u : 0);
    chat.style.bottom = `${sub?.childElementCount ? Math.max(bottom, height - sub.offsetTop + 3 * u) : bottom}px`;
    for (const [i, msg] of messages.entries()) {
      const now = msg.clock === 'world' ? wt : t;
      chat.children[i].style.opacity = Math.min(1, (msg.t + msg.dur - now) / Math.min(msg.dur, 0.35));
    }
    previous = { state, active, taken, messages };
  };
}
