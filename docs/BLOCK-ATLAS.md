# Block / item atlases

You give BlockReel a picture that holds many blocks and items in a grid (an "everything" sheet).
It cuts them out, removes duplicates, and lets you (or Claude, by looking at the sheets) name them.

```bash
python core/atlas.py slice sheet.png work/atlas      # 1. cut
#   work/atlas/tiles/            one PNG per cell
#   work/atlas/sheets/           contact sheets: 64 unique tiles each, numbered #n
#   work/atlas/index.json        grid, cell size, duplicates
#   work/atlas/labels.json       you fill this: {"2": "grass_block", "23": "tnt"}
python core/atlas.py label work/atlas                # 2. copy labelled tiles to named/<name>.png
python core/atlas.py faces work/atlas                # 3. cube icons -> faces/<name>_top|left|right.png
```

## How the grid is found

Background colours are the most common colours in the sheet. The empty gaps between cells repeat every N pixels;
that gives the cell size and offset. If a sheet has no gaps, a correlation fallback runs; if detection fails,
pass `--grid cellW,cellH,offsetX,offsetY` and/or `--bg "r,g,b;r,g,b"`.

Tested on a 1944×3744 sheet: 27×52 cells of 72 px, 1 394 tiles, 1 190 unique.

## Teaching it

Labels are plain JSON keyed by the unique-tile number shown on the contact sheet. Label what you can identify, skip
the rest. Because unique numbers follow the order tiles first appear, the same sheet always yields the same numbers,
so keep your `labels.json` in `references/atlas-labels/<sheet-name>.json` and reuse it. A starter file is included.

## Cube faces

`faces` unprojects an isometric cube icon (hexagon outline) into flat top/left/right textures by sampling the three
rhombi. Non-cube shapes (items, stairs, flowers) are skipped. Because the source is a rendered icon, results are
approximate: edges can be soft, and shading baked into the icon (the left face is darker) stays in the texture.
For best quality, give a sheet of real flat textures instead and skip `faces`.

## Using the result in a film

Copy the flat textures into `my-film/assets/blocks/`, set `"blocks": "assets/blocks"` in `story.json`, and
(optional) add an `index.json` mapping block names to `{top, side, bottom}` (see `docs/STORYBOARD.md`).
Only use textures you have the right to use.
