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
  "textures": "vanilla",         // default: original game textures from work/vanilla (tools/vanilla.py fetch) when present; "builtin" = CC0 originals
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
  "scale": 1, "nametag": "Hero", "holding": "diamond_sword", "offhand": "torch",   // items are extruded 3D sprites; a block name holds a block
  "blink": true,                     // automatic blinking (default true)
  "dust": false,                     // footstep dust puffs while walking/running
  "armor": "diamond",                // or { "helmet": "iron", "chestplate": "diamond", "leggings": "iron", "boots": "gold", "color": "#3a6ad0" (leather) }
                                     // leather chainmail iron gold diamond netherite copper turtle_scute
  "cape": "red",                     // red | blue | black (CC0) or "path/to/cape.png" (64x32 layout); swings with speed
  "elytra": true                     // folded on the back; spreads with the "glide" clip (hides the cape, like the game)
}
```

`"offhand": "shield"` holds the game's shield on the outside of the left forearm; it turns to face forward during `guard`/`block`.

Mobs use `type` (+ `texture` for the built-in rigs) instead of `skin` (see `docs/MOBS.md`; ~70 types with the game's geometry):
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
| `arc` | a hop of this many blocks along any move (knock-back, leap), peaking mid-segment |
| `holding` / `offhand` | switch the item in the right / left hand from this time on (`null` = empty hand). Entries with only these fields (or only `lookAt`, `hide`, `show`, `hurt`) do not interrupt the running clip |
| `vanish` | on a `die` segment: when the fall ends the body disappears in the game's white poof |
| `hurt` | `true` flashes the red damage tint (automatic on `hit` and `knockback`, held while dying) |

Positions anywhere (`pos`, `to`, `face`, `lookAt`, fx, props, camera `pos`/`look`/`orbit.center`) may use `null` as y:
`[x, null, z]` = on the ground there (actors on the terrain, never on a tree top; cameras at eye height above the real ground).

**Clips.** Loops: `idle walk run wave talk mine punch dance sit look scared spin zombie stance shout point`.
One-shots that stretch to the segment `dur` and have built-in **anticipation, overshoot and follow-through**:
`swing` (wind-up, strike, overshoot), `hit` (knock-back and recover), `lunge` (coil and spring), plus `jump`, `die`.
Combat and magic (v0.2): `slash` (horizontal cut), `overhead` (two-handed chop), `thrust` (stab), `knockback` (thrown back; use `to` + `arc`),
`dodge` (side-step lean), `summon` (arms rise), `getup`, `fall` (onto the back; `hold`), `throw` are one-shots;
`ready` (sword stance), `guard`/`block`, `cast` (arms forward, trembling), `levitate` (float pose: move up with `to`), `kneel`, `bow` (draw),
`charge` (run with the weapon forward), `celebrate`, `sneak`, `crouch`, `stagger` loop.
Movement and life (v0.3): `swim` (breaststroke, horizontal), `crawl`, `climb` (move up with `to`), `ride` (with `"mount": "horse1"`:
the actor sits on that actor's saddle and turns with it; the mount moves itself), `eat`, `drink`, `sleep` (lying, eyes closed), `glide`
(horizontal, spreads the elytra).
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
`kind`: `break explosion smoke fire sparks dust blood confetti crit magiccrit poof portal sweep flame enchant aura`
(`sweep` takes `"face": degrees`: the arc in front of a swing). `smoke` and `fire` are continuous for `dur`; the rest are
bursts. `pos` is `[x,y,z]`, an actor name, or `{actor, offset}`. `block` picks the debris colours from that block's texture
(default: the block under `pos`). Particles are cubes, seeded (`story.seed`, `fx.seed`) and evaluated in closed form
(gravity, drag, floor), so renders are deterministic. Debris lands on the ground below the emitter.

## World, changes and props

`world` ops (`"air"` removes). `terrain` ops run first, everything else in the given order:

```jsonc
{ "fill": ["stone", [x0,y0,z0], [x1,y1,z1]] }   { "set": ["gold", [x,y,z]] }   { "hollow": ["planks", [..], [..]] }
{ "tree": [x, null, z], "kind": "oak|birch|spruce|dead", "height": 5 }
{ "sphere": ["glass", [cx,cy,cz], 4], "hollow": true, "half": true }      { "cylinder": ["cobblestone", [cx,y0,cz], 3, 6], "hollow": true }
{ "terrain": { "radius": 40, "center": [0,0], "biome": "plains|forest|taiga|desert|snowy|nether|wasteland", "base": 4, "amp": 3, "scale": 16,
               "water": 2, "flat": { "center": [0,0], "radius": 8, "y": 4 }, "trees": 0.02, "plants": 0.07, "flowers": 0.02,
               "clear": [[x, z, r]], "arenaPlants": false, "seed": 1 } }
{ "scatter": ["flower_red", [x0,z0], [x1,z1]], "density": 0.1, "on": ["grass"] }
{ "structure": "house|tower|ruins|shrine|pillar|campfire", "pos": [x, null, z], "w": 7, "d": 6, "h": 12, "block": "...", "seed": 1 }
```
Building sites are reserved: no tree or plant of the terrain grows on them, the site is cleared and levelled, and the building gets a
foundation down to the ground. Keep sites out of the arena (`tools/compose.py` warns about overlaps).
Trees whose leaves would cover the lens or the first blocks of a camera's line of sight are not planted (`"clearFoliage": false` turns
this off; `foliageClearance` sets the lens radius, default 1.3).

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

Built-in names (CC0 originals, and the same names map to the game's textures in the cache): `grass dirt stone cobblestone planks log leaves
sand bricks obsidian glowstone snow water lava glass tnt chest wool_white wool_red wool_blue gold diamond netherrack stonebrick
mossy_cobblestone gravel bedrock iron_block redstone_block sandstone soul_sand ice blackstone crying_obsidian magma quartz
birch_log spruce_log dark_oak_log birch_leaves spruce_leaves dark_oak_planks crafting_table`, plants `tall_grass flower_red flower_yellow
dead_bush fire`, light sources `torch redstone_torch lantern`, shapes `stone_slab cobblestone_slab oak_slab oak_stairs cobblestone_stairs
stone_brick_stairs oak_fence cobblestone_wall snow_layer carpet_red`. With the cache also: ores, `bookshelf furnace pumpkin jack_o_lantern
hay sea_lantern cactus mycelium emerald_block end_stone nether_bricks beacon mushroom_red mushroom_brown sapling`, wood variants and more.
A suffix sets orientation: `oak_stairs:east` (the side the stairs climb toward), `log:x` / `log:z` (a log lying down), `stone_slab:top`.

How the world is drawn (`core/engine/mesher.js`): faces between solid blocks are never emitted (no z-fighting, no see-through water);
each face gets the game's directional shade and per-vertex ambient occlusion; sky light and block light are propagated like in the game
(torches 14, glowstone/lava 15), so caves are dark and torches light the area warmly at night; textures are mip-mapped with an
alpha-aware filter so distant blocks do not shimmer. Any other name loads `<name>.png` from your `blocks` folder. A project `index.json` can map names:

```json
{ "blocks": { "grass_block": { "top": "grass_top", "side": "grass_side", "bottom": "dirt" },
              "lamp": { "all": "lamp", "light": 15 }, "rose": { "all": "rose", "shape": "cross" },   // shape: cube cross torch slab stairs fence wall layer liquid
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

## Sky and lightning

`"sky": { "clouds": true, "stars": 1, "celestial": true, "cloudHeight": 34, "cloudSpeed": 0.6, "sunsetGlow": true }`: a dome that keeps the
horizon level, the square sun and moon on the light direction (night styles show the moon), stars that fade in at night and the
game's cloud layer (from its cloud map when cached).
`"lightning": [ { "t": 5, "pos": [x, z] | "actorName", "dur": 0.45, "seed": 3 } ]`: a jagged bolt that flickers, lights the area and
flashes the sky and the scene.

## Weather

`"weather": { "type": "rain" | "snow", "density": 1, "wind": 3, "radius": 14, "clear": 1.6 }`: drops are seeded and wrap in a volume around the camera.
`clear` keeps drops at least that many blocks (on x and z) away from the lens; raise it (2.5-3.5) if close drops read as big streaks in your shots.

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

Drawn with the game's own font when cached (`python tools/vanilla.py font`), with its 1 px shadow; otherwise a pixel fallback.
`"subtitleScale": 3` sets the chat text size at 720p; `"font": "css"` forces the fallback. Titles accept `\n` for two lines.

`"subtitles": [ { "t": 6, "dur": 2, "who": "Hero", "text": "Hello!" } ]`,
`"titles": [ { "t": 0.4, "dur": 2.2, "text": "BLOCKREEL", "color": "#fff", "size": 64 } ]`.
