# Skin demo: "Ranger"

An original hooded woodland scout, painted from scratch with `SkinCanvas` (CC0). Files:

| File | What |
|---|---|
| `ranger.png` | final, classic (4 px arms) |
| `ranger-slim.png` | final, slim (3 px arms), same design repainted with `--slim` |
| `paint_skin.py` | the painter: palette plan, base layer, then overlay layer, then `mirror_limbs()` |
| `iterations/` | the turntable image of every review round |
| `turntable_slim.png` | the slim skin in a `wave` pose (checks the arm joint and mantle) |

```bash
python examples/skin-demo/paint_skin.py out/ranger.png            # final (--detail 3)
python examples/skin-demo/paint_skin.py out/ranger-slim.png --slim
python core/skin.py validate out/ranger.png                       # ok, model classic, 0 transparent base pixels
python tools/turntable.py out/ranger.png --out out/tt.png         # the 4-angle preview
```

## Review log (what I saw in each turntable and what I changed)

| Round | Image | What was wrong | Fix |
|---|---|---|---|
| 1 | `iterations/turntable_v1.png` | flat colour, weak face; the dark green cloak read as a black slab on the back | add detail pass: belt, bracers, brows, boots with a cuff |
| 2 | `iterations/turntable_v2.png` | belt and bracers work, but the face got worse: "cheek" pixels read as freckles or ears, the jaw shade as a beard; 2 px front cloak panels read as black bars; cloak still too dark | remove cheeks and jaw, keep one nose pixel; lighter blue-green cloak (separates from the yellow-green tunic); 1 px front edges; light/dark fold stripes on the back; clasp and chain; knee seam |
| 3 | `iterations/turntable_v3.png` | readable. Small nitpicks: trousers seam looks like stitching (kept), flat shading on the tunic | final pass (`--detail 3`): subtle noise and a few hand-painted pixels |
| final | `iterations/turntable_v4_final.png`, `turntable_slim.png` | none found | none |

Palette (each a 4-tone ramp with a slight hue shift): skin `e3a77a`, hair `a8532b`, tunic `56803c`, cloak `3a7466`, leather `7b5231`, trousers `5d4d3c`, boots `3a2a1e`, metal `c9b25a`.

**Not tested in the game.** Validated and previewed in the BlockReel engine only.
