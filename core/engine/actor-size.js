export function actorSize(cfg, name) {
  if (cfg.height !== undefined && cfg.scale !== undefined) {
    throw new Error(`Actor "${name}": choose either height or scale`);
  }
  for (const field of ['height', 'scale']) {
    if (cfg[field] !== undefined && !(Number.isFinite(cfg[field]) && cfg[field] > 0)) {
      throw new Error(`Actor "${name}": ${field} must be a positive number`);
    }
  }
  return { scale: cfg.scale ?? 1, height: cfg.height };
}
