// Project-local PNGs keep the scene portable and avoid interpreting mod code.
export function projectPng(value, field) {
  if (typeof value !== 'string' || !/^[a-z0-9_.-]+(?:\/[a-z0-9_.-]+)*\.png$/i.test(value)
      || value.split('/').some((part) => part === '.' || part === '..')) {
    throw new Error(`${field} must be a project-relative PNG path`);
  }
  return value;
}

export function itemAsset(id, items = {}) {
  if (typeof id !== 'string') throw new Error('item ID must be a string');
  const parts = id.split(':');
  if (parts.length > 2 || !parts.every((part) => /^[a-z0-9_./-]+$/i.test(part)
      && part.split('/').every((p) => p && p !== '.' && p !== '..'))) {
    throw new Error(`invalid item ID "${id}"`);
  }
  const name = parts.at(-1);
  if (parts.length === 1 || parts[0] === 'minecraft') return { name };

  const item = Object.hasOwn(items, id) ? items[id] : null;
  if (!item || typeof item !== 'object' || Array.isArray(item)) {
    throw new Error(`item "${id}" needs an entry in story.items with its PNG texture`);
  }
  const texture = projectPng(item.texture, `item "${id}" texture`);
  const size = item.size ?? 0.85;
  if (!Number.isFinite(size) || size < 0.05 || size > 3) throw new Error(`item "${id}" size must be 0.05–3 blocks`);
  const grip = item.grip ?? [3.5 / 16, 12.5 / 16];
  if (!Array.isArray(grip) || grip.length !== 2 || !grip.every((v) => Number.isFinite(v) && v >= 0 && v <= 1)) {
    throw new Error(`item "${id}" grip must contain two numbers from 0 to 1`);
  }
  return { name, texture, size, grip };
}

export function capeAsset(cape) {
  if (typeof cape === 'string') {
    if (/\.png$/i.test(cape)) return { texture: cape, sway: 1 };
    if (/^(red|blue|black)$/.test(cape)) return { preset: cape, sway: 1 };
  }
  if (cape && typeof cape === 'object') {
    const { preset, texture, sway = 1 } = cape;
    if (!Number.isFinite(sway) || sway < 0 || sway > 2) throw new Error('cape sway must be 0–2');
    if (texture !== undefined && preset === undefined) return { texture: projectPng(texture, 'cape texture'), sway };
    if (texture === undefined && /^(red|blue|black)$/.test(preset)) return { preset, sway };
  }
  throw new Error('cape must be red, blue, black, a PNG path, or an object with preset or texture');
}
