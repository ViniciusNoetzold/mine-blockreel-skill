# Resource packs (custom textures for your world)

Workflow (the `blockreel-textures` skill follows it): plan palette → generate/paint → **check** → **preview in a scene** → build → install and test.

```bash
python core/tilecheck.py set textures/ --out report/        # seams, palette, size, contact sheet (look at report/set-sheet.png)
python core/pack.py check textures/                         # file names, sizes, animation strips
python tools/pack_preview.py textures/ --out preview.png    # the set rendered in a mini-world with a character for scale
python core/pack.py build textures/ --name "My Pack" --pack-format <N> \
   --format-version <java version> --format-source https://minecraft.wiki/w/Pack_format --icon pack.png --out build/
```
`textures/` mirrors `assets/minecraft/textures/`:

```
textures/
  block/stone.png   block/grass_block_top.png   block/water_still.png   block/water_still.png.mcmeta
  item/diamond.png
```
Names must match the game's texture names exactly (lowercase `a-z 0-9 _ - .`). The easiest way to list the names for your version is to open the
game's own client `.jar` yourself and look under `assets/minecraft/textures/` (never copy those files into a repo).

## The format number (never guess it)

`core/pack.py` has **no default** format. Look up the **resource pack** value for your Java version in the table on
[Minecraft Wiki: Pack format](https://minecraft.wiki/w/Pack_format) and pass it with `--format-version` and `--format-source`; the pack's `README.txt` records them.

- Versions up to 1.21.8: `--pack-format N`. Example from the table: 1.21.4 = 46 (1.21.5 = 55, 1.21.6 = 63, 1.21.7-1.21.8 = 64).
- Java 1.21.9 and newer: the wiki says packs use `min_format` / `max_format` instead of `pack_format` (since 25w31a): `--min-format N --max-format M`.
- The table also lists versions with a decimal number (for example 97.1). `core/pack.py` does not support those; how to write them in `pack.mcmeta`
  was not confirmed. Check the wiki, or edit `pack.mcmeta` by hand.
- A wrong number makes the game warn that the pack is incompatible.

## Animated textures

A vertical strip PNG (frames stacked, all the same size) plus `<name>.png.mcmeta`:

```json
{ "animation": { "frametime": 3, "interpolate": true } }
```
Optional: `width` / `height` (frame size), `frames` (order and per-frame time). `core/pack.py check` reports an image that is not a whole number of frames.
Source: the Resource pack page of the [Minecraft Wiki](https://minecraft.wiki/w/Resource_pack).

## Checks

- `core/tilecheck.py`: wrap-around **seam** score (the tile edge compared with the worst interior boundary), dominant **palette**, brightness/saturation outliers,
  mixed sizes, noisy textures; PROBLEMS fail the run, notes are advisory; framed textures (glass, metal blocks, grass side) are notes.
- `core/pack.py check`: lowercase names, power-of-two width (a warning; the wiki does not require it), square block/item textures (animated strips excepted),
  valid `.mcmeta`, animation strips that are not whole frames.
- `tools/pack_preview.py`: judge repetition, tops vs sides, transparency and mood. Blocks missing from your set fall back to the built-in originals and are listed.

## What a resource pack cannot do

- It cannot set *your account's* player skin. See `docs/SKINS.md`.
- Models, sounds, fonts and shaders are out of scope.

## Install (not tested here)

Put the `.zip` in the game's `resourcepacks` folder (Options → Resource Packs → Open Pack Folder shows it) and enable it. Test checklist: `plugin/skills/blockreel-textures/SKILL.md`.
