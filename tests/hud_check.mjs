import assert from 'node:assert/strict';
import { compileHud } from '../core/engine/hud.js';

const config = {
  hotbar: { slots: ['torch', { item: 'stick', count: 2 }] },
  inventory: [{ item: 'planks', count: 4 }],
  chat: {
    maxLines: 2,
    messages: [
      { t: 0.5, text: 'Old message' },
      { t: 2, text: 'Lia foi explodida por um Creeper', clock: 'world', dur: 1 },
      { t: 3, text: 'Recent message', dur: 2 },
    ],
  },
  events: [
    {
      type: 'craft', t: 1, dur: 3,
      grid: ['planks', 'planks', 'planks', null, 'stick', null, null, 'stick'],
      result: 'wooden_pickaxe', takeAt: 2, toSlot: 1,
    },
    { type: 'select', t: 3, slot: 1 },
    { type: 'inventory', t: 4, dur: 1 },
    { type: 'hotbar', t: 5, visible: false },
  ],
};
const hud = compileHud(config);
const crafted = hud.at(2);
assert.equal(crafted.taken, true);
assert.deepEqual(crafted.state.hotbar[1], { item: 'wooden_pickaxe', count: 1 });
assert.deepEqual(crafted.state.inventory[0], { item: 'planks', count: 1 });
assert.equal(hud.at(1.75).taken, false);
assert.equal(hud.at(1.75).state.hotbar[1].count, 2);
assert.deepEqual(hud.at(2), crafted, 'seeking backward preserves the craft snapshot');
assert.equal(hud.at(3).state.selected, 1);
assert.equal(hud.at(4).panel.type, 'inventory');
assert.equal(hud.at(5).state.visible, false);
assert.equal(hud.at(2.1, 1.99).chat.length, 1);
assert.deepEqual(hud.at(3.1, 2.9).chat.map((m) => m.text), ['Lia foi explodida por um Creeper', 'Recent message']);
assert.deepEqual(hud.at(3.1, 3).chat.map((m) => m.text), ['Old message', 'Recent message']);
assert.throws(() => compileHud({ ...config, inventory: [] }), /crafting at 2s is missing 3 × planks/);
assert.throws(() => compileHud({ ...config, events: [...config.events, { type: 'inventory', t: 1.5, dur: 2 }] }), /panels overlap/);
assert.throws(() => compileHud({ ...config, events: [{ ...config.events[0], toSlot: 0 }] }), /no free slot for wooden_pickaxe/);
assert.equal(compileHud({}).at(0).state.visible, false);
