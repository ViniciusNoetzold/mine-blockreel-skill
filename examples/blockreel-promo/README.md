# BlockReel Showcase

[Watch the 111-second cinematic cut with sound](https://viniciusnoetzold.github.io/mine-blockreel-skill/#blockreel-promo).

| Time | On screen | Source |
| --- | --- | --- |
| 0:00–0:08 | An oak cabin rises from the clearing. | [*A Casa Nova* build timelapse](../house-timelapse/) |
| 0:08–0:15 | The temple goes up in five phases and holds on the completed facade. | Showcase temple |
| 0:15–0:29 | From the first avenue to the clock tower and final skyline. | [*Praça do Horizonte*](../city-timelapse/), complete 14-second build |
| 0:29–0:47 | Custom skins, cape motion, a mounted run through 64 × 64 materials, and a nighttime encounter. | Showcase animation |
| 0:47–1:47 | From the first look at the world to the cave reveal. | [*Primeira Noite*](../first-night/), complete 60-second short |
| 1:47–1:51 | BlockReel and the repository address. | Showcase end card |

The master is 1920 × 1080 at 30 fps with stereo AAC and seven chapter markers. It combines native 1080p showcase shots with the original angles of the earlier 720p films. A new score accompanies the opening showcase. *Primeira Noite* keeps its original score and effects, including the silence, fuse and blast.

## Rebuild the temple

The editable [temple blueprint](temple.blueprint.json) captures the twin stairs, dark stone edges, amber bands, stepped tower, gardens, and central entrance of the supplied facade reference. The reference was a single frontal view, so the sides, back, and depth were inferred. Compile a standalone timelapse from the repository root.

```bash
python tools/build_timelapse.py examples/blockreel-promo/temple.blueprint.json --out films/temple
python tools/render.py films/temple/story.json --preset preview --out films/temple/preview.mp4
```

For the full cinematography and editing workflow, see the [cinematic production guide](../../docs/CINEMATIC-WORKFLOW.md).
