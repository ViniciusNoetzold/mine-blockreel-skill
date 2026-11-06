# TECHNIQUE.md — how a BlockReel film is built

```
story.json ──► Three.js engine (core/engine) ──► Chrome (headless) ──► PNG per frame ──► ffmpeg ──► film.mp4
   ▲                  ▲
 skins, textures   styles/<name>/style.json
```

## Determinism

`window.renderAt(t)` is a pure function of time: actor poses, camera, clouds, particles, weather, block changes, props,
grain and subtitles are all computed from `t` (and seeds), never from the previous frame. Speed ramps (`timeRemap`) bend
a separate *world time* derived from `t`. That is why `--frame 4.0` gives exactly the
frame you will get in the final video, and why previews at lower fps match the final cut.

## Units and coordinates

- 1 world unit = 1 block = 16 skin pixels. A player is 2 units tall.
- Block `[x, y, z]` occupies the cube from `x..x+1`, so its centre is `x+0.5`. Ground blocks at `y=0` have their top at `y=1`.
- Actor `pos` is the **feet** position. Stand on the ground at `y=1`; use `x.5 / z.5` to centre on a block.
- Characters face **+z** at heading 0. `"face": 90` turns to face **+x**. Moving with `to` sets the heading automatically.
- Camera offsets `{actor, offset}` are world-space.

## Skins

Boxes are UV-mapped from the standard 64x64 layout (`core/skin.py`, `docs/SKINS.md`). Legacy 64x32 skins work
(left limbs are mirrored from the right). Slim (3px) arms are auto-detected from the transparent arm column;
override with `"model": "slim" | "classic"`.

## Blocks

A block name resolves through, in order: project `blocks` dir `index.json` → built-in `core/builtin/blocks/index.json`
→ a texture file with that name → magenta/black missing-texture checker (with a console warning).
`index.json` maps a name to a texture name, or `{top, side, bottom}`, or `{all, transparent}`.

## Engine modules (`core/engine/`)

| File | Job |
|---|---|
| `engine.js` | scene setup, actors, camera, overlays, `renderAt(t)`, QA hook |
| `anim.js` | pure math: easing, clip library, blending, timeline, look-at, speed ramps (unit-tested in node) |
| `face.js` | repaints eyes/mouth/wounds on the head texture; lip-sync from subtitles; glowing eyes |
| `particles.js` | seeded cube particles evaluated in closed form |
| `world.js` | block changes (break, place, explode, TNT), props (door, chest), crack textures |
| `mobs.js` | box-model mob rigs |
| `post.js` | bloom, depth of field, grade, grain, chromatic aberration |
| `env.js` | sky texture, lighting keyframes, rain and snow |

## Performance

Headless Chrome uses software GL (SwiftShader). Measured here: about 3.5 s per **still** including browser start-up; a
24-frame 640x360 preview rendered in about 6 s; cost grows with pixels, shadows and post-processing.
- Preview: `--preset preview` (12 fps, half size; the WebGL canvas really renders at that size).
- `--scale S` renders at S x the story size (1.5 on a 1280x720 story = sharp 1080p); `--preset 1080p60` also sets 60 fps.
- `--workers N` renders N frame ranges in parallel Chrome processes and joins them (a win on long films with several cores).
- `--gpu` uses the real GPU instead of SwiftShader (not tested on every machine).
- Turn `shadows` off (`styleOverride`) for ~2x speed; leave `post` off in previews if you need more.
- `python tools/preview.py story.json` is a live browser preview with a time slider (best with a real GPU).
- Instanced meshes keep a few thousand blocks cheap; hundreds of thousands are not supported.

## Extending

| Want | Do |
|---|---|
| New motion | add a function to `CLIPS` in `core/engine/anim.js` returning rotations (radians) per limb: `head, rArm, lArm, rLeg, lLeg, body`, plus optional `bodyRx, bob, sink, roll, spinY`. Use `kf()` for keyframes with easing (anticipation and overshoot are just keys) |
| New style | copy `styles/classic-2012/` and edit `style.json` + `STYLE.md` |
| New world helper | add an op next to `fill/set/hollow/tree` in `expandWorld` |
| New particle kind | add an entry to `KINDS` in `core/engine/particles.js` (layer specs: count, life, speed, gravity, drag, size, colours) |
| New mob | add a branch in `buildMob` (`mobs.js`) with its boxes and UV offsets |
| New face state | add a drawing function to `EYES` or `MOUTH` in `face.js` |
| New post effect | add a pass in `post.js` |

## Rendering details

`tools/render.py` serves the repo plus your project folder (as `/project/`) from a local server,
drives Chrome with Playwright, calls `renderAt(t)`, screenshots each frame, and pipes PNGs to ffmpeg
(`libx264`, `-preset veryfast`, `-crf 18`) into a silent video; `tools/audio.py` builds the audio mix
(music, sfx, dialogue, ducking) and it is muxed at the end.
