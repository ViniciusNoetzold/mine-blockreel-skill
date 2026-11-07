// Equipment on the player rig, like the game: armour layers (helmet, chestplate, leggings, boots), the shield, a cape that swings
// with movement and the elytra that spreads to glide. Textures: the game's (tools/vanilla.py equipment) or CC0 originals.
//
// "armor": "diamond" | { "helmet": "iron", "chestplate": "diamond", "leggings": "iron", "boots": "gold", "color": "#a06540" }
// "cape": "red" | "path/to/cape.png"      "elytra": true      "offhand": "shield"
import { boxUV } from './geo.js';

const PX = 1 / 16;
const MATS = ['leather', 'chainmail', 'iron', 'gold', 'diamond', 'netherite', 'copper', 'turtle_scute'];

// parts: { head, body, rArm, lArm, rLeg, lLeg } groups of the player rig (pivots: head at the neck, arms at the shoulder, legs at the hip)
export async function equip(THREE, a, cfg, load, exists) {
  const out = { capes: [], wings: [], update() {} };
  const dir = async (rel) => { for (const d of ['/work/vanilla/equipment', '/core/builtin/equipment']) if (await exists(`${d}/${rel}`)) return `${d}/${rel}`; return null; };
  // ---- armour: layer 1 (helmet, chestplate, boots) and layer 2 (leggings), classic 64x32 layout, inflated like the game
  let arm = cfg.armor;
  if (typeof arm === 'string') arm = { helmet: arm, chestplate: arm, leggings: arm, boots: arm };
  if (arm) {
    const mats = new Map();
    const matFor = async (m, layer) => {
      const key = `${m}|${layer}`; if (mats.has(key)) return mats.get(key);
      const u = await dir(`${layer}/${MATS.includes(m) ? m : 'iron'}.png`); if (!u) return null;
      const mt = new THREE.MeshLambertMaterial({ map: await load(u), alphaTest: 0.5, transparent: false });
      if (m === 'leather') mt.color.set(arm.color || '#a06540'); // the game tints leather; its overlay stays untinted
      mats.set(key, mt); return mt;
    };
    const piece = async (m, layer, parent, w, h, d, u, v, grow, y, mirror = false) => {
      const mt = await matFor(m, layer); if (!mt) return;
      const mesh = new THREE.Mesh(boxUV(THREE, w, h, d, u, v, 64, 32, grow, mirror), mt); mesh.position.y = y * PX; mesh.castShadow = true; parent.add(mesh);
      if (m === 'leather') { const ou = await dir(`${layer}/leather_overlay.png`); if (ou) { const o = new THREE.Mesh(mesh.geometry, new THREE.MeshLambertMaterial({ map: await load(ou), alphaTest: 0.5 })); o.position.copy(mesh.position); o.scale.setScalar(1.001); parent.add(o); } }
    };
    if (arm.helmet) await piece(arm.helmet, 'humanoid', a.head, 8, 8, 8, 0, 0, 1.0, 4);
    if (arm.chestplate) {
      await piece(arm.chestplate, 'humanoid', a.body, 8, 12, 4, 16, 16, 1.0, 0);
      await piece(arm.chestplate, 'humanoid', a.rArm, 4, 12, 4, 40, 16, 1.0, -4);
      await piece(arm.chestplate, 'humanoid', a.lArm, 4, 12, 4, 40, 16, 1.0, -4, true);
    }
    if (arm.leggings) {
      await piece(arm.leggings, 'humanoid_leggings', a.body, 8, 12, 4, 16, 16, 0.5, 0);
      await piece(arm.leggings, 'humanoid_leggings', a.rLeg, 4, 12, 4, 0, 16, 0.5, -6);
      await piece(arm.leggings, 'humanoid_leggings', a.lLeg, 4, 12, 4, 0, 16, 0.5, -6, true);
    }
    if (arm.boots) {
      await piece(arm.boots, 'humanoid', a.rLeg, 4, 12, 4, 0, 16, 1.0, -6);
      await piece(arm.boots, 'humanoid', a.lLeg, 4, 12, 4, 0, 16, 1.0, -6, true);
    }
  }
  // ---- elytra (replaces the cape when both are given, like the game)
  if (cfg.elytra) {
    const u = await dir('wings/elytra.png');
    if (u) {
      const mt = new THREE.MeshLambertMaterial({ map: await load(u), alphaTest: 0.5, side: THREE.DoubleSide });
      for (const s of [1, -1]) { // left wing (+x) and right wing (-x, mirrored)
        const pivot = new THREE.Group(); pivot.position.set(s * 5 * PX, 6 * PX, -2 * PX); a.body.add(pivot);
        const w = new THREE.Mesh(boxUV(THREE, 10, 20, 2, 22, 0, 64, 32, 0, s < 0), mt); w.position.set(-s * 5 * PX, -10 * PX, -1 * PX); w.castShadow = true; pivot.add(w);
        pivot.rotation.order = 'ZYX'; out.wings.push({ pivot, s });
      }
    }
  } else if (cfg.cape) {
    const u = /\.png$/i.test(cfg.cape) ? cfg.cape : await dir(`capes/${cfg.cape}.png`);
    if (u) {
      const mt = new THREE.MeshLambertMaterial({ map: await load(u), alphaTest: 0.5, side: THREE.DoubleSide });
      const pivot = new THREE.Group(); pivot.position.set(0, 6 * PX, -2.2 * PX); a.body.add(pivot);
      const c = new THREE.Mesh(boxUV(THREE, 10, 16, 1, 0, 0, 64, 32, 0, false), mt); c.position.set(0, -8 * PX, -0.5 * PX); c.rotation.y = Math.PI; c.castShadow = true; pivot.add(c);
      out.capes.push(pivot);
    }
  }
  // per frame: the cape lifts with speed and flutters; the elytra folds or spreads to glide
  out.update = (st, t) => {
    const speed = st.clip === 'run' || st.clip === 'charge' ? 1 : st.clip === 'walk' || st.clip === 'sneak' ? 0.5 : st.clip === 'glide' || st.clip === 'knockback' ? 1.2 : 0;
    for (const p of out.capes) p.rotation.x = 0.08 + speed * 0.55 + Math.sin(t * (4 + speed * 8)) * (0.03 + speed * 0.07);
    for (const w of out.wings) {
      if (!w.pivot) continue;
      const glide = st.clip === 'glide' ? 1 : 0;
      w.pivot.rotation.set(0.26 + glide * 0.1, 0, w.s * (0.26 + glide * 1.2)); // folded in a V on the back; spread wide to glide
    }
  };
  return out;
}

// The game's shield: a 12x22x1 plate and a 2x6x6 handle on a 64x64 texture, held upright in the off hand.
export async function shieldMesh(THREE, load, exists) {
  let u = null; for (const d of ['/work/vanilla/equipment', '/core/builtin/equipment']) if (await exists(`${d}/shield.png`)) { u = `${d}/shield.png`; break; }
  if (!u) return null;
  const mt = new THREE.MeshLambertMaterial({ map: await load(u), alphaTest: 0.5 });
  const g = new THREE.Group();
  const plate = new THREE.Mesh(boxUV(THREE, 12, 22, 1, 0, 0, 64, 64, 0, false), mt); plate.castShadow = true;
  const handle = new THREE.Mesh(boxUV(THREE, 2, 6, 6, 26, 0, 64, 64, 0, false), mt); handle.position.set(0, 0, -3.5 * PX);
  g.add(plate); g.add(handle);
  return g;
}
