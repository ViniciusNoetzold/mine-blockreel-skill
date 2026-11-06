# Mobs (box-model rigs)

BlockReel ships rigs for four mob shapes. **You provide the texture**: the repo contains only original placeholder
textures (`core/builtin/mobs/sample-*-layout.png`, CC0) so the rigs can be tested. Never commit game textures (`docs/LEGAL.md`).

```json
"actors": {
  "boomer":  { "type": "creeper", "texture": "assets/creeper.png", "pos": [0,1,0], "face": 0, "scale": 1, "nametag": "Boomer" },
  "oinker":  { "type": "pig",     "texture": "assets/pig.png",     "pos": [2,1,0] },
  "crawler": { "type": "spider",  "texture": "assets/spider.png",  "pos": [4,1,0] },
  "groaner": { "type": "player",  "skin": "assets/zombie.png",     "pos": [6,1,0] }
}
```
Zombie-shaped mobs are normal actors (`skin` = a 64x64 or 64x32 zombie-layout texture) driven with the `zombie` clip.

## Texture layouts (64x32)

Boxes are unfolded like a skin: `(u, v)` is the box's top-left corner on the sheet, `w x h x d` its size in pixels.

| Mob | Part | `u, v` | `w x h x d` |
|---|---|---|---|
| creeper | head | 0, 0 | 8 x 8 x 8 |
| | body | 16, 16 | 8 x 12 x 4 |
| | 4 legs (all use the same region) | 0, 16 | 4 x 6 x 4 |
| pig | head | 0, 0 | 8 x 8 x 8 |
| | snout | 16, 16 | 4 x 3 x 1 |
| | body (rotated so the long side runs front to back) | 28, 8 | 10 x 16 x 8 |
| | 4 legs | 0, 16 | 4 x 6 x 4 |
| spider | neck | 0, 0 | 6 x 6 x 6 |
| | head | 32, 4 | 8 x 8 x 8 |
| | body | 0, 12 | 10 x 8 x 12 |
| | 8 legs (all use the same region) | 18, 0 | 16 x 2 x 2 |

**Not verified.** These offsets come from my recollection of the classic Java entity models; I searched for an authoritative
source and could not confirm the numbers. They are consistent with the original sample textures in this repo, but you must
check them against the texture you use: render one still (`python tools/render.py story.json --frame 1`) and look at the mob
from the front and back. If a part shows the wrong region, edit the numbers in `core/engine/mobs.js` (`buildMob`), one line per part.
Textures that use another layout (e.g. 64x64 entity sheets) are not supported yet.

## Clips

`walk`, `run` (leg cycle; spider legs ripple), `swell` (creeper-style inflate with white flashes over the segment `dur`),
`hit` (rock back), `die` (fall over), idle (head sway). Pair `swell` with a `changes` explosion and a `hide`:

```json
{ "t": 2.2, "actor": "boomer", "do": "swell", "dur": 1.6 },
{ "t": 3.8, "actor": "boomer", "hide": true }
...
"changes": [ { "t": 3.8, "explode": [-2, 0, 2], "radius": 2.2 } ]
```
Mobs support `lookAt`, `face`, `to`, camera targets and particles like any actor. They have no face states or skin layers.
