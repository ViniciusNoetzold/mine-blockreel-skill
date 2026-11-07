# A Casa Nova (comedy / building)

Two friends decide where to build, one of them builds a house in a timelapse (`build` beat: blocks appear bottom-up with the right dig
sounds, the camera circles the site, then looks over the builder's shoulder), they admire it... and a creeper creeps up, hisses, swells
and blows half of it away (`creeper` beat). Punchline, quiet ending.

```bash
python tools/compose.py examples/creeper-surprise/plan.json --out films/casa-nova
python tools/render.py films/casa-nova/story.json --preset preview --workers 4 --out films/casa-nova/preview.mp4
```
Both characters are personas (no skin files needed); the creeper uses the game's texture from the local cache.
QA: 0 FAIL. Fixed while reviewing: talking close-ups too tight, the build shot looked away from the house.
