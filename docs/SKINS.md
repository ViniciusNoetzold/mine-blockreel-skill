# Skins

## The 64x64 layout

`python core/skin.py layout docs/skin-layout.png` draws the labelled map (also in `references/`).
Each body part is an unfolded box. From left to right: **right side, front, left side, back**; the **top** and **bottom** sit above.
There are two layers: the base (head, body, arms, legs) and an overlay (hat, jacket, sleeves, pants) that may be transparent.

| part | origin (u,v) | size w×h×d |
|---|---|---|
| head / hat | (0,0) / (32,0) | 8×8×8 |
| body / jacket | (16,16) / (16,32) | 8×12×4 |
| right arm / sleeve | (40,16) / (40,32) | 4×12×4 (3 wide if slim) |
| left arm / sleeve | (32,48) / (48,48) | 4×12×4 (3 wide if slim) |
| right leg / pants | (0,16) / (0,32) | 4×12×4 |
| left leg / pants | (16,48) / (0,48) | 4×12×4 |

Classic = 4px arms, slim = 3px arms. The tools tell them apart by the unused last column of the arm's back face (x=55 on the right arm, x=47 on the left arm) being fully transparent.

## Tools

```bash
python core/skin.py validate skin.png                 # size, classic/slim, transparent base pixels
python core/skin.py convert old32.png new64.png       # legacy 64x32 -> 64x64 (mirrors left limbs)
python core/skin.py unwrap  skin.png parts/           # every face of every part as its own PNG + parts.json
python core/skin.py preview skin.png preview.png      # flat front/back paper-doll
python core/skin.py make    out.png --skin f1c27d --hair 4a2f1b --shirt 2e8bc0 --pants 3b3b98 [--slim] [--hair-style long]
python core/skin.py snap    screenshot.png out.png --crop x0,y0,x1,y1
```

For custom art, use `SkinCanvas` from `core/skin.py`: `rect(part, face, x, y, w, h, color)` paints on one face using
face-relative pixel coordinates, so you never compute atlas coordinates by hand.

## Which input can be used

| You have | Works? |
|---|---|
| Clean 64x64 / 64x32 / HD PNG | Yes, directly |
| Screenshot of the flat texture (scaled up) | Yes, with `snap --crop` if the whole 64x64 area is visible and the crop is exact. If an app cut off rows or drew buttons over it, ask for the original PNG |
| Picture of a 3D character render | Not as a texture (only visible faces). Build a lookalike with `make` and repaint |

## Painting workflow and helpers

The `blockreel-skins` skill follows this: briefing → research → palette plan → paint in layers → validate → **turntable preview and iterate** → export.

```bash
python tools/turntable.py skin.png --out tt.png [--pose wave] [--model slim] [--eyes wide --mouth smile]   # 4 angles in one image
```
`core/skin.py` helpers on top of `SkinCanvas`: `ramp(base, 4, hue_shift)` (a 4-tone ramp, shadows cooler and lights warmer), `shaded_box(part, ramp)`
(lit from top and front), `rect`, `px`, `line`, `edge_light`, `clear`, and `mirror_limbs()` (paint the right arm and leg, get the left ones mirrored, layers included).
Paint the **base layer first**, then the overlay (hat, jacket, sleeves, pants). Keep the eyes on row 4 of the front face, brows on row 3, mouth on row 6:
the engine's face states repaint rows 3-7 and sample the skin colour from the cheeks. A full example with a review log: `examples/skin-demo/`.

## Layer facts (from the Minecraft Wiki)

Per [Minecraft Wiki: Skin](https://minecraft.wiki/w/Skin): a 64x64 skin has an inner and an outer layer; the outer layer is slightly larger than the inner one
(0.5 px on body, arms and legs, 1 px on the head) and is used for hats, glasses and accessories. In Java Edition the **inner layer is forced fully opaque**
(`validate` reports transparent base pixels); the outer layer may be transparent. Classic arms are 4 px wide, slim arms 3 px (the unused rightmost pixels are ignored).

## Using a skin in the game (not tested here)

- **Java Edition:** upload the PNG (64x64, or the legacy 64x32) on the minecraft.net profile page or in the Launcher's Skins tab, and pick 3 px or 4 px arms
  to match `validate`'s `model`. Only accounts that own the game can change skins; offline-mode players cannot use a custom skin without mods.
  Source: [Minecraft Wiki: Skin](https://minecraft.wiki/w/Skin). Mojang's own help article could not be loaded when this was written; check
  [help.minecraft.net](https://help.minecraft.net) for the current menu names.
- **Bedrock Edition:** a different process, and the format supports larger templates (the wiki mentions 128x128). Do not follow the Java steps; use Mojang's current Bedrock help page
  (also not loaded when this was written).
- **Skins used inside a BlockReel video need nothing in-game.**
