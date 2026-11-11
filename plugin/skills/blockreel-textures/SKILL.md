---
name: blockreel-textures
description: Design a coherent set of Minecraft block/item textures (16x, 32x or 64x) with web research, one palette plan for the whole set, code-generated or hand-painted tiles, a tiling/seam and palette checker, an in-scene preview rendered by the engine, and a resource-pack zip built with a researched and cited pack format. Use when the user wants a texture pack, custom block textures, or to improve a set. Part of BlockReel; the main blockreel skill calls this one.
license: MIT
---

# BlockReel textures

Reuse a BlockReel checkout containing `core/pack.py`. If needed, clone and set up the runtime. Run commands and resolve project files from the checkout root. [Runtime setup](https://github.com/ViniciusNoetzold/mine-blockreel-skill#run-the-tools-directly)

Put each set in `work/textures/<name>/` (gitignored) or `films/<name>/textures/`. The folder mirrors
`assets/minecraft/textures/` (`block/…`, `item/…`). **Never copy game textures**; originals only (the repo's demo set is CC0).

## 1. Briefing (at most one short question)

Settle: **theme** (e.g. pastel cartoon, gritty medieval, snowy), **resolution** (16x default, 32x or 64x), **which blocks and items**
(default: a starter set of ~25: stone, cobblestone, dirt, grass top/side, planks, log, leaves, sand, glass, water, lava, bricks, obsidian, glowstone,
snow, wool, ores/metal blocks, TNT, plus 1-2 items), and **the target Java version** (needed for the pack format; ask if unknown).

## 2. Research (web), written to `research.md` with links

- **Official texture file names for the target version**: the names are the contract; a wrong name is silently ignored.
  Check [Minecraft Wiki: Resource pack](https://minecraft.wiki/w/Resource_pack) and the version's file list (the user can open their own client `.jar`,
  `assets/minecraft/textures/`, to list names; never copy the files).
- **Animated textures**: a vertical strip PNG plus a sidecar `<name>.png.mcmeta`, e.g. `water_still.png.mcmeta`:
  `{ "animation": { "frametime": 3, "interpolate": true } }`; optional `width`, `height` (frame size) and `frames`. Every frame must be the same size
  and the image must be a whole number of frames (source: the Wiki's Resource pack page).
- **Tiling conventions**: block textures are square; they repeat, so edges must wrap. Tops of terrain blocks repeat the most.
- **The pack format for the user's version**: [Minecraft Wiki: Pack format](https://minecraft.wiki/w/Pack_format), the **resource pack** column.
  Quote the version and the number and the link in your answer. Since 25w31a (Java 1.21.9) the wiki says packs use `min_format` / `max_format`
  instead of `pack_format`. **Never guess the number.** Versions listed with a decimal (like `97.1`) are not supported by `core/pack.py`
  (how to write them in `pack.mcmeta` was not confirmed); tell the user.
- **Style references** for the theme (palettes, how others handle tiling noise). Principles only.

## 3. Palette and style plan for the WHOLE set

Before drawing anything: one **global palette plan** (a base colour per material, each a 4-tone ramp with a slight hue shift:
`skin.ramp`), the **style rules** (banded flat tones vs soft gradients, outlines or not, how many single-pixel accents per tile),
and the **noise scale** (how large blobs are relative to the tile). Every texture follows the same rules; that is what makes a set.

## 4. Generate or paint

- By code (preferred for tiles): start from `examples/texture-pack-demo/make_textures.py` (seeded, tileable by construction: wrap-around noise,
  wrapping Voronoi cells, staggered boards, bevels, animated strips). Change `PLAN` and the patterns.
- By hand, pixel by pixel, for hero textures (item icons, ores).
- Side textures (`grass_block_side`), glass and metal blocks have borders by design; they do not tile.

## 5. Check (MANDATORY)

```bash
python core/tilecheck.py check block/stone.png --out stone_tiles.png   # 2x2 and 3x3 tiling preview + seam score
python core/tilecheck.py palette block/stone.png -k 6                  # dominant colours
python core/tilecheck.py set textures/ --out report/                   # whole set: PROBLEMS, notes, contact sheet
python core/pack.py check textures/                                    # names, sizes, animation strips
```
**Open the images** (`stone_tiles.png`, `report/set-sheet.png`) and look. PROBLEMS (visible seam on a tiling texture, mixed sizes, too many colours)
must be fixed; notes (brightness, saturation, palette overlap) are prompts to look closer, not errors. Framed textures are reported as notes.
Iterate at least once: fix what you saw, regenerate, look again.

## 6. Preview in a scene (MANDATORY)

```bash
python tools/pack_preview.py textures/ --out pack-preview.png
```
A mini-world rendered by the film engine with your textures: large terrain (repetition), a block gallery, a hut, a tree, water, lava, glass and a character
for scale. Look at: repetition on big surfaces, tops vs sides of grass and logs, transparency (glass, leaves), contrast between neighbours, and the mood in sunlight.
Blocks missing from your set are listed (the built-in originals are used for them).

## 7. Build the pack

```bash
python core/pack.py build textures/ --name "My Pack" --pack-format <N> --format-version <java version> \
  --format-source https://minecraft.wiki/w/Pack_format --icon pack.png --out build/
# Java 1.21.9 and newer:  --min-format <N> --max-format <M>   instead of --pack-format
```
The command refuses to run without a format number (there is no default on purpose). `pack.mcmeta` sits at the zip root, and a `README.txt` in the pack
records the number, the version and the source link. **Cite that link in your answer.**

## 8. Install and test checklist (give it to the user; YOU could not test in the game)

1. Copy the `.zip` into the game's `resourcepacks` folder (Options → Resource Packs → Open Pack Folder shows where).
2. Enable it in Options → Resource Packs. If the game says the pack is incompatible, the format number does not match the game version.
3. Check in a creative world: grass/dirt/stone/planks/logs/leaves, water and lava animation, glass transparency, TNT, a flat 20x20 floor of each main block (seams),
   and a few items.
4. Report anything that shows the purple/black checker: it means a wrong file name or a bad frame size.

## Rules

- Never claim the pack works in the game. Say "built, checked and previewed in the BlockReel engine".
- Never commit game textures. Do not take them from the user's `.jar` into the repo.
- Skins are a different thing (`blockreel-skins`); a resource pack cannot change the player's skin.
- Models, sounds, fonts and shaders are out of scope.
