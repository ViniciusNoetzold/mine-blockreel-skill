# BlockReel Showcase

[Watch the complete 2 min 53 s showcase](https://viniciusnoetzold.github.io/mine-blockreel-skill/#blockreel-promo) · [Watch Characters & Textures separately](https://viniciusnoetzold.github.io/mine-blockreel-skill/#blockreel-characters)

| Time | On screen | Source |
| --- | --- | --- |
| 0:00–0:50 | Temple reveal, nighttime encounter, custom skins, cape motion, and a mounted run through 64 × 64 materials. | Original showcase animation |
| 0:50–1:02 | An oak cabin rises from the clearing. | [*A Casa Nova*](../house-timelapse/), complete build |
| 1:02–1:16 | From the first avenue to the clock tower and final skyline. | [*Praça do Horizonte*](../city-timelapse/), complete city build |
| 1:16–1:46 | A courier races across a frozen rail bridge. | [*Aurora Express*](../aurora-express/), complete short |
| 1:46–2:46 | From the first look at the world to the cave reveal. | [*Primeira Noite*](../first-night/), complete short |
| 2:46–2:49 | A side-by-side comparison of the horizontal and vertical cuts. | [*Primeira Noite* and its Reel](../first-night/) |
| 2:49–2:53 | BlockReel and the repository address. | Showcase end card |

The master combines the original showcase with four complete films and a closing aspect-ratio comparison. The separate 50-second showcase focuses on the temple, characters, and materials. *Primeira Noite* retains its pause, fuse and blast.

## Rebuild the temple

The editable [temple blueprint](temple.blueprint.json) captures the twin stairs, dark stone edges, amber bands, stepped tower, gardens, and central entrance of the supplied facade reference. The reference was a single frontal view, so the sides, back, and depth were inferred. Compile a standalone timelapse from the repository root.

```bash
python tools/build_timelapse.py examples/blockreel-promo/temple.blueprint.json --out films/temple
python tools/render.py films/temple/story.json --preset preview --out films/temple/preview.mp4
```

For the full cinematography and editing workflow, see the [cinematic production guide](../../docs/CINEMATIC-WORKFLOW.md).
