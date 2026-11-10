# Capes and mod items

## Capes

On a player actor or a plan's `cast` member, set `"cape": "red"`, `"blue"` or `"black"` for a built-in design. For a custom design, use a PNG in the 64×32 cape layout (or a whole-number multiple) beside the storyboard. Keep the 10×16×1 cape net at UV origin (0,0).

```json
"cape": { "texture": "wardrobe/ranger.png", "sway": 0.8 }
```

The string form `"cape": "wardrobe/ranger.png"` also works. `sway` ranges from 0 to 2 and defaults to 1. The cape drapes from the shoulders and blends between rest and travel. With elytra equipped, the wings take its place.

In the storyboard, an actor timeline entry can put on, swap or remove a cape. Plan authors can set the same field on an `act` beat.

```json
{ "t": 2.0, "actor": "ranger", "cape": "blue" }
{ "t": 4.0, "actor": "ranger", "cape": null }
```

## Mod item sprites

Get the item's exact ID and an authorized sprite from the user's resource pack or supplied art. Copy the PNG into the film folder and register it at the top level of the plan or storyboard.

```json
"items": {
  "trailgear:signal_compass": {
    "texture": "items/trailgear/signal_compass.png",
    "size": 0.65,
    "grip": [0.5, 0.75]
  }
}
```

Use `"holding": "trailgear:signal_compass"` in the cast, `holding` or `offhand` in a timeline entry, or the same ID in a HUD slot or recipe. The engine extrudes the sprite for the hand and uses the flat sprite for the HUD. Give it a transparent PNG of up to 128×128 pixels. `size` sets the sprite width in blocks (default 0.85). `grip` gives the normalized contact point measured from the top left (default [0.21875, 0.78125]). Use paths relative to the plan or storyboard, with letters, digits, dashes, dots, underscores and forward slashes. The compiler copies declared PNGs into the output project.

These entries describe how an item looks in a film. Stage the item's effect with BlockReel's props, lights, particles and sound cues. Import the specific PNG with permission to use it. When the item's appearance is essential and no authorized art is available, ask for the asset or approval to design a stand-in.
