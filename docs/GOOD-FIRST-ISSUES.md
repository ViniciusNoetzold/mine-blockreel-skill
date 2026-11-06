# Good first issues

Each entry: title, body, labels. Create them with the `gh` commands at the bottom, or paste them into GitHub. They are scoped to one file or one small feature, with a way to check the result.

| # | Title | Where | Done when |
|---|---|---|---|
| 1 | Add a `sneak` clip | `core/engine/anim.js` `CLIPS` | `do: "sneak"` lowers the torso, bends the legs' stance, and a lab frame shows it; add a line in `docs/STORYBOARD.md` and `docs/COVERAGE.md` |
| 2 | Add a `swim` clip | `core/engine/anim.js` | arms alternate overhead, body horizontal; a rendered still in `examples/animation-lab` |
| 3 | Add a `bow` (draw and release) clip | `core/engine/anim.js` | anticipation, hold, release with overshoot; uses `kf()` |
| 4 | Verify and fix the mob texture layouts | `core/engine/mobs.js`, `docs/MOBS.md` | compare against a real entity texture you own (do not commit it); update the table and remove the "unverified" note |
| 5 | Add a villager-shaped mob rig | `core/engine/mobs.js` | new `type`, UV table in `docs/MOBS.md`, a frame in `examples/mobs-lab` |
| 6 | Add an enderman-shaped mob rig | `core/engine/mobs.js` | tall thin boxes, long limbs, a sample CC0 texture in `core/gen_textures.py` |
| 7 | Add a style: `retro-pixelated` | `styles/retro-pixelated/` | `pixelate` 3-4, saturated sky; `STYLE.md`, and a rendered frame checked by eye |
| 8 | Add a style: `cartoon-outline` | `styles/` + `core/engine/post.js` | an outline pass (edge detect on depth/normal) behind a style flag |
| 9 | `tools/qa.py`: warn when a subtitle covers a character's face | `tools/qa.py`, `core/engine/engine.js` `collectQA` | project the face to NDC and compare with the subtitle box; a test with a synthetic story |
| 10 | Export subtitles as an `.srt` | new `tools/srt.py` | `python tools/srt.py story.json --out film.srt`; test the timestamps |
| 11 | 9:16 vertical preset | `tools/render.py` `PRESETS` | `--preset vertical` renders 1080x1920; engine camera `fov` handling checked in a still |
| 12 | Tile checker: detect repeating "motifs" in a tile | `core/tilecheck.py` | flag a texture whose brightest pixel pattern repeats visibly when tiled 3x3; unit tests with a synthetic tile |
| 13 | Docs: translate the README to Portuguese | `README.pt-BR.md` | keep commands and file names unchanged |
| 14 | Add a `torch` held item (a lit glowstone stick) | `core/engine/engine.js` `holding` | `"holding": "torch"` shows an emissive stick; see `docs/COVERAGE.md` item 1 for the bigger version |

Labels to use: `good first issue`, plus `animation`, `mobs`, `styles`, `tools`, `docs` or `textures`.

```bash
gh issue create --title "Add a sneak clip" --label "good first issue,animation" \
  --body "Add \`sneak\` to CLIPS in core/engine/anim.js (lowered torso, bent stance). Add it to docs/STORYBOARD.md and docs/COVERAGE.md and render a frame in examples/animation-lab to check it. Run: python -m pytest tests -q"
# repeat for the other rows
```
