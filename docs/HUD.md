# Chat, hotbar, inventory and crafting

Add `hud` to `story.json` or `plan.json` only when the production calls for game UI. This layer lives above the scene and inside letterbox margins. Use it for point-of-view gameplay, survival stories, or a shot where the audience needs to see a recipe or an event. The normal dialogue subtitles remain independent.

## Chat

```json
{
  "hud": {
    "chat": {
      "maxLines": 4,
      "messages": [
        { "t": 1, "who": "Lia", "text": "Ouvi alguma coisa.", "dur": 4 },
        { "t": 5.2, "text": "Lia foi explodida por um Creeper", "dur": 5 }
      ]
    }
  }
}
```

Messages appear bottom-left in chronological order and fade near the end of their duration. Omit `who` for system messages. `dur` defaults to 7 seconds and `maxLines` defaults to 5. Use `clock: "world"` to sync a message to a world event inside a speed ramp. Other messages use output time.

For a compiled `creeper` beat, set `then: "die"` on the beat and `hud.chat.auto: true` in the plan to generate a message at the blast. Set `hud.chat.exploded` to a localized template such as `"{name} foi explodido por um Creeper"`. The compiler substitutes the target's display name. A nonlethal reaction leaves the chat unchanged.

## Items and crafting

```json
{
  "hud": {
    "labels": { "crafting": "Criação", "inventory": "Inventário" },
    "hotbar": { "slots": ["torch", null, null], "selected": 0 },
    "inventory": [{ "item": "planks", "count": 3 }, { "item": "stick", "count": 2 }],
    "events": [
      { "type": "inventory", "t": 1, "dur": 1 },
      {
        "type": "craft",
        "t": 2, "dur": 3,
        "grid": ["planks", "planks", "planks", null, "stick", null, null, "stick", null],
        "result": "wooden_pickaxe",
        "takeAt": 4,
        "toSlot": 1
      },
      { "type": "select", "t": 5, "slot": 1 }
    ]
  }
}
```

- Use zero-based slots. Hotbar and crafting grid each have nine slots. Inventory has 27. A string means one item. A stack object has `item` and a positive integer `count`. Use `null` for an empty slot.
- Add an `inventory` event to open the inventory panel for an interval. A `craft` event opens a crafting table panel and shows the authored 3×3 recipe and result. Use `takeAt` for the exact output time when the item is collected. The engine checks available counts, deducts the ingredients from the inventory and hotbar, and puts the result in `toSlot` on the hotbar. Without `toSlot`, it searches for a matching stack or an empty slot. Omit `takeAt` to show a recipe without collecting it. Keep panel intervals separate.
- Use `set` with `slot`, `stack` and optional `area: "inventory"` to script a pickup or slot change. The default area is `hotbar`. Use `select` to highlight a hotbar slot. Use a `hotbar` event with `visible: true` or `false` to toggle the bar at a cut.
- Add a `crafting_table` block to the world to frame the interaction. Use an actor clip and timed `holding` change to sell the physical action. Recipes and inventory events describe the film. Supply the exact ingredient arrangement, result and animation for the requested edition or mod.
- Custom item IDs use the same storyboard item definitions as held props. An item defined in the project's `items` map uses its declared texture as the HUD icon.

QA includes frames before and after collection inside a craft panel. Also check the shot before the panel opens and review the cut back to the scene. Inspect chat position above the hotbar and below the action in the intended aspect ratio.
