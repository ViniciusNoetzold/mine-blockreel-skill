# BlockReel Showcase

[Watch the 75-second film with sound](https://viniciusnoetzold.github.io/mine-blockreel-skill/#blockreel-promo).

| Time | On screen |
| --- | --- |
| 0:00–0:12 | The temple goes up in five phases, followed by the completed facade and a first-person reveal. |
| 0:12–0:22 | A nighttime encounter with alternate camera perspectives and character reactions. |
| 0:22–0:40 | Custom skins, cape motion, and a stylized village chase. |
| 0:40–0:50 | A mounted run through the same village with original 64 × 64 block materials. |
| 0:50–1:11 | Excerpts from *Primeira Noite*, *Aurora Express*, the house and city timelapses, and a 16:9 / 9:16 comparison. |
| 1:11–1:15 | BlockReel and the repository address. |

The new scenes were rendered at 1920 × 1080 and 30 fps. The montage reuses earlier films at their original camera angles. An original score and timed effects run across the edit.

## Rebuild the temple

The editable [temple blueprint](temple.blueprint.json) captures the twin stairs, dark stone edges, amber bands, stepped tower, gardens, and central entrance of the supplied facade reference. The reference was a single frontal view, so the sides, back, and depth were inferred. Compile a standalone timelapse from the repository root.

```bash
python tools/build_timelapse.py examples/blockreel-promo/temple.blueprint.json --out films/temple
python tools/render.py films/temple/story.json --preset preview --out films/temple/preview.mp4
```

For the full cinematography and editing workflow, see the [cinematic production guide](../../docs/CINEMATIC-WORKFLOW.md).
