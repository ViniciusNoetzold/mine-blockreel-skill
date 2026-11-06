# story.json reference

Everything the engine reads. Unknown fields are ignored (so a typo fails silently: check your stills).
Paths starting with `/` are served from the repo root (e.g. `/core/builtin/skins/hero.png`); other paths are
relative to the story file. All times are in seconds on the **output timeline** unless noted.

```jsonc
{
  "title": "My film",            // informational
  "fps": 30, "size": [1280, 720], "duration": 12,
  "seed": 1,                     // global seed for particles / explosions (renders are deterministic)
  "style": "classic-2012",       // folder name in styles/
  "styleOverride": { "shadows": false },             // merged over style.json
  "blocks": "assets/blocks",     // optional folder of your block PNGs (+ optional index.json)
  "audio": { ... },              // timed music / sfx / dialogue, see "Audio"
  "post": { ... },               // bloom / grade / grain / depth of field, see "Post-processing"
  "weather": { "type": "rain" }, // "rain" | "snow"
  "lighting": [ ... ],           // time-of-day keyframes
  "timeRemap": [ ... ],          // speed ramps (slow motion)
  "actors": { ... }, "world": [ ... ], "changes": [ ... ], "props": { ... }, "fx": [ ... ],
  "timeline": [ ... ], "faces": [ ... ], "camera": [ ... ], "transitions": [ ... ],
  "subtitles": [ ... ], "titles": [ ... ]
}
```

## Actors

```jsonc
"hero": {
  "skin": "assets/skins/hero.png",   // 64x64 or legacy 64x32
  "model": "auto",                   // "auto" | "classic" | "slim"
  "pos": [0, 1, 0],                  // feet position
  "face": 90,                        // heading in degrees; 0 faces +z, 90 faces +x
  "scale": 1, "nametag": "Hero", "holding": "planks",
  "blink": true,                     // automatic blinking (default true)
  "dust": false                      // footstep dust puffs while walking/running
}
```

Mobs use `type` + `texture` instead of `skin` (see `docs/MOBS.md`):
`{ "type": "creeper" | "pig" | "spider", "texture": "...", "pos": [...], "face": 0, "scale": 1 }`.
A zombie is a normal actor with a zombie-layout skin and the `zombie` clip.

## Timeline segments

```jsonc
{ "t": 0.5, "actor": "hero", "do": "walk", "to": [4,1,0], "dur": 3,
  "ease": "linear", "face": "explorer", "turn": 0.15, "speed": 1, "hold": false, "height": 1,
  "blend": 0.15, "lookAt": "villain" }
```

| field | meaning |
|---|---|
| `actor`, `t`, `dur` | who, start, length |
| `do` | clip, see below |
| `to` | move the feet to this point during the segment; the actor stays there afterwards |
| `ease` | easing for the movement: `linear` (default) `smooth in out inCubic outCubic inBack outBack inOutBack outElastic outBounce` |
| `face` | degrees, an actor name (uses that actor's position at that time), or `[x,y,z]`. Without it, moving sets the heading |
| `turn` | seconds the body takes to turn to a new heading (default 0.15, shortest arc) |
| `speed` | multiplies walk/run cadence |
| `hold` | keep the clip going after `dur` until the next segment (use for `sit`, `die`, `stance`) |
| `height` | jump height in blocks |
| `blend` | seconds of crossfade from the previous clip (default 0.15; 0 = hard cut) |
| `lookAt` | the head follows a target until changed: actor name, `[x,y,z]`, `"camera"`, or `null` to release. Optional `limit` (rad) |
| `hide` / `show` | `true` removes / restores the actor (e.g. a mob that exploded) |

**Clips.** Loops: `idle walk run wave talk mine punch dance sit look scared spin zombie stance shout point`.
One-shots that stretch to the segment `dur` and have built-in **anticipation, overshoot and follow-through**:
`swing` (wind-up, strike, overshoot), `hit` (knock-back and recover), `lunge` (coil and spring), plus `jump`, `die`.
Mobs: `walk run swell hit die` (`swell` = creeper-style inflate and flash).
The torso, head and arms lean together from the hips; legs stay planted.

## Faces

```jsonc
"faces": [ { "t": 2, "actor": "hero", "eyes": "wide", "mouth": "shout", "hurt": 0, "dur": 1.5 } ]
```
`eyes`: `open closed half wide angry glow dead`. `mouth`: `closed open half shout smile frown`.
`hurt`: 0-3 (red wound pixels). Fields persist until changed; with `dur` the override ends after that time.
`glow` = pure white emissive eyes with a horizontal light streak (looks best with `post.bloom`).
**Lip-sync:** while a subtitle whose `who` (or `actor`) matches the actor's name/nametag is on screen, the mouth
follows the letters of the text (disable with `"lipsync": false`). Face painting samples the skin's own colours.

## Camera

```jsonc
{ "t": 0, "dur": 3.5, "pos": [-9,3,9], "to": [-4,2,7], "look": [-3,1.5,0], "lookTo": "hero",
  "fov": 60, "fovTo": 40, "ease": "smooth", "shake": 0.0, "handheld": 0.0, "dutch": 0, "dutchTo": 0,
  "focus": "hero", "focusTo": "villain", "post": { "dof": {} } }
{ "t": 3.5, "dur": 2.7, "orbit": { "center": [1,1.4,0.5], "radius": 8, "height": 2, "from": -25, "to": 25 } }
{ "t": 6.2, "dur": 2,   "first": "hero", "fov": 80 }                  // first-person (the actor's head is hidden)
```
The last shot with `t <= now` is active (hard cuts). `shake` = fast jitter for impacts; `handheld` (0..1.5) = slow organic
drift of position, aim and roll for every action shot; `dutch` = tilt in degrees (animated to `dutchTo`); `fovTo` = zoom.
`focus`/`focusTo` (actor name or distance in blocks) rack-focus when `post.dof` is on. `pos`/`look` accept
`[x,y,z]`, `"actorName"`, or `{ "actor": "name", "offset": [dx,dy,dz] }` (world-space offset).

## Transitions (on the output timeline)

```jsonc
"transitions": [
  { "t": 3.95, "type": "flash", "dur": 0.5, "color": "#fff", "peak": 1 },       // white flash, fast attack, soft decay
  { "t": 1.85, "type": "whip",  "dur": 0.3, "dir": "right", "strength": 40 },   // horizontal motion blur: cover a cut with it
  { "t": 12.5, "type": "fade",  "dur": 1.4, "dir": "out", "color": "#000" }     // "out": to colour and stays; "in": from colour
]
```

## Speed ramps (slow motion)

`"timeRemap": [ { "t": 8, "dur": 2, "slow": 0.85 } ]`: inside the window the world (actors, particles, weather, camera
movement) slows to `1 - slow` and then catches up, so world time is **unchanged outside the window** and nothing else
needs shifting. Cuts, subtitles, titles and transitions stay on real time. `slow` 0..0.95.

## Particles (`fx`)

```jsonc
"fx": [ { "t": 3, "kind": "explosion", "pos": [2.5,1.5,-1.5], "scale": 1.3, "seed": 4, "block": "stone",
          "dur": 5, "density": 1, "floor": 1 } ]
```
`kind`: `break explosion smoke fire sparks dust blood confetti`. `smoke` and `fire` are continuous for `dur`; the rest are
bursts. `pos` is `[x,y,z]`, an actor name, or `{actor, offset}`. `block` picks the debris colours from that block's texture
(default: the block under `pos`). Particles are cubes, seeded (`story.seed`, `fx.seed`) and evaluated in closed form
(gravity, drag, floor), so renders are deterministic. Debris lands on the ground below the emitter.

## World, changes and props

`world` ops (applied in order; `"air"` removes): `fill`, `set`, `hollow`, `tree`.

```jsonc
"changes": [
  { "t": 1.0, "break": [-2,2,-2], "crack": 0.9 },                  // cracks for 0.9 s, then pops (debris automatic)
  { "t": 2.6, "place": [-2,2,-2], "block": "gold" },               // appears with a small pop
  { "t": 5.0, "tnt": [2,1,-2], "fuse": 1.6, "radius": 3 },         // TNT flashes and swells, then explodes
  { "t": 7.0, "explode": [0,1,0], "radius": 2.5 }                  // explosion without a TNT block
],
"props": {
  "door1":  { "type": "door",  "pos": [-1,1,1], "axis": "x", "hinge": "min", "block": "planks", "events": [ { "t": 7.5, "do": "open" }, { "t": 10, "do": "close" } ] },
  "chest1": { "type": "chest", "pos": [4,1,1], "face": 180, "events": [ { "t": 8, "do": "open" } ] }
}
```
Explosions remove blocks within `radius` (irregular edge, delayed by distance), spawn fireball, debris and smoke, and spare
`obsidian`, `water`, `lava` (override with `"blastResistant": [...]`). A crater shows what is *below*: build extra dirt layers.
Use `place` on an empty position or after a `break`. `water` and `lava` flow automatically (texture scroll).

## Blocks

Built-in names: `grass dirt stone cobblestone planks log leaves sand bricks obsidian glowstone snow water lava glass tnt chest
wool_white wool_red wool_blue gold diamond`. Any other name loads `<name>.png` from your `blocks` folder. A project `index.json` can map names:

```json
{ "blocks": { "grass_block": { "top": "grass_top", "side": "grass_side", "bottom": "dirt" },
              "ice": { "all": "ice", "transparent": true },
              "magma": { "all": "magma", "flow": [0, 0.2], "emissive": true } } }
```
`flow: [u, v]` scrolls the texture in blocks per second (pixel-stepped); `emissive` ignores lighting.

## Style fields (`styles/*/style.json`)

`sky.top/bottom`, `fog [near, far]`, `ambient {color,intensity}`, `sun {color,intensity,dir}`, `shadows`, `clouds`,
`pixelate` (render at 1/n resolution, upscaled with nearest), `letterbox` (`true` = 11% bars, or a number = target aspect
ratio such as `2.37`), `vignette`, `fov`, plus optional `post` and `weather` defaults.

## Lighting keyframes (day / night)

```json
"lighting": [
  { "t": 0, "sky": { "top": "#ff9a5a", "bottom": "#ffd9a0" }, "ambient": { "color": "#ffd9b0", "intensity": 0.7 }, "sun": { "color": "#ffb36b", "intensity": 1, "dir": [0.6, 0.35, 0.4] } },
  { "t": 9, "sky": { "top": "#050818", "bottom": "#1a2350" }, "fog": [10, 50] }
]
```
Any subset of `sky`, `ambient`, `sun`, `fog` per key; values interpolate smoothly. Use it for sunsets, for an act-break colour shift, or lightning.

## Weather

`"weather": { "type": "rain" | "snow", "density": 1, "wind": 3, "radius": 14 }`: drops are seeded and wrap in a volume around the camera.

## Post-processing

```json
"post": { "bloom": { "strength": 0.7, "radius": 0.6, "threshold": 0.8 },
          "grade": { "exposure": 1, "contrast": 1.08, "saturation": 1.1, "tint": [1, 0.95, 0.9], "lift": [0, 0, 0.02], "gain": [1, 1, 1] },
          "grain": 0.05, "chroma": 0.002,
          "dof": { "aperture": 0.0005, "maxblur": 0.02 } }
```
Set in the style, the story, or per camera shot (`camera[i].post`, merged over the story's). `dof` + `focus` gives a rack focus.
Grain is seeded by time, so it is deterministic. Post-processing adds cost per frame; leave it off for quick previews if needed.

## Audio

```json
"audio": {
  "music":    { "file": "assets/theme.mp3", "volume": 0.6, "start": 0, "fadeIn": 0.8, "fadeOut": 1.5, "loop": true, "duck": { "amount": 0.35 } },
  "sfx":      [ { "file": "assets/boom.wav", "t": 5.0, "volume": 1.0 } ],
  "dialogue": [ { "file": "assets/line1.wav", "t": 5.2 } ]
}
```
Files are yours (never ship game audio). `duck` lowers the music while any dialogue plays. The legacy `"music": "file"` still works.
`python tools/audio.py story.json --out mix.wav` renders only the mix so you can listen first.

## Subtitles and titles

`"subtitles": [ { "t": 6, "dur": 2, "who": "Hero", "text": "Hello!" } ]`,
`"titles": [ { "t": 0.4, "dur": 2.2, "text": "BLOCKREEL", "color": "#fff", "size": 64 } ]`.
