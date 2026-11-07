# Primeira Noite (survival / chase)

Night in a birch forest, a campfire, ruins. A zombie (the game's texture, arms forward like the game) shows up; a chase through the trees
(`chase` beat), then a stone-sword fight (`duel`, `finisher` with the death poof) and a victory pose that turns to the camera.

```bash
python tools/compose.py examples/zombie-night/plan.json --out films/primeira-noite
python tools/render.py films/primeira-noite/story.json --preset preview --workers 4 --out films/primeira-noite/preview.mp4
```
QA: 0 FAIL. Found while reviewing: a tracking camera that passed through the ruins' wall (the director now keeps cameras out of
buildings), a character shown from behind during a close-up, a victory pose seen from behind next to the ruins.
