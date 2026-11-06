# Coverage: what BlockReel can and cannot animate yet

The goal is a skill that can make *any* Minecraft animation. It is not there yet. This file is the honest gap list, so nobody
(including the assistant) claims more than is true. Status: **done** (rendered and looked at), **partial**, **missing**.

## Characters

| Need | Status | Notes |
|---|---|---|
| Player model from a skin (classic / slim, legacy 64x32, both layers) | done | proportions checked against the game: shoulders flush with the torso top, head sits directly on the body (no neck) |
| Face: blink, eyes, mouth, wounds, glow, lip-sync | done | rows 3-7 of the face are repainted; skins must keep eyes on row 4 |
| Creeper-, pig-, spider-shaped mobs | partial | boxes and clips work; **texture offsets unverified** (`docs/MOBS.md`) |
| Zombie / any humanoid mob | done | a normal actor with its texture and the `zombie` clip |
| Enderman, skeleton (bow), villager, iron golem, wolf, cow, sheep, chicken, horse, bat, ghast, wither, dragon, fish | missing | each needs its own rig (boxes + UV table + clips) |
| Baby mobs, mob variants | missing | |
| Armor layers, capes, elytra, shields | missing | |
| Crowds of hundreds | missing | many actors work, but there is no instancing |

## Held items and props

| Need | Status | Notes |
|---|---|---|
| A block in the hand | done | `"holding": "planks"` |
| Tools, swords, bows, torches as items (extruded sprite from an item texture) | **missing** | highest-impact gap for fight, mining and adventure scenes |
| Doors, chests | done | `props`; chest lid now 90° / 0.5 s / ease-out like the game. **Open:** the chest uses a block texture, not the entity texture (`entity/chest.png` is fetched but not mapped yet) |
| Beds, signs, furnaces, minecarts, boats, rails | missing | |

## Animation (player)

| Need | Status |
|---|---|
| idle walk run wave talk mine punch dance sit look scared jump die spin | done |
| swing hit lunge stance shout point raise zombie (anticipation, overshoot) | done |
| Clip blending, turning, look-at, speed ramps | done |
| sneak, swim, crawl, climb, ride a mob or vehicle, draw a bow, eat/drink, sleep, elytra glide, emotes library | **missing** |
| Held-item-aware hand poses (arm follows the tool) | missing |
| Inverse kinematics, cloth/cape physics | missing |

## World

| Need | Status | Notes |
|---|---|---|
| Cube blocks with any texture, tops/sides/bottoms, transparency, emissive, flowing water/lava | done | |
| Break, place, TNT, explosions, crack stages, debris | done | |
| **Non-cube blocks**: stairs, slabs, fences, walls, trapdoors, torches, flowers, grass, vines, rails, redstone, pistons | **missing** | needed for believable builds |
| Terrain generation, biomes, caves, large worlds | missing | worlds are hand-written ops; hundreds of thousands of blocks are not supported |
| Trees | partial | one oak shape |
| Sky: sun, moon, stars, moving clouds, lightning | partial | gradient sky, cubes clouds; no sun/moon/stars/lightning |
| Rain and snow | done | |

## Effects and look

| Need | Status |
|---|---|
| Seeded cube particles: break, explosion, smoke, fire, sparks, dust, blood, confetti | done |
| Bloom, depth of field, grain, grade, chromatic aberration, flash/whip/fade | done |
| Motion blur | missing |
| Potion swirls, enchant glyphs, portal particles, totem, fireworks | missing |
| Custom shaders (RTX-style reflections, ambient occlusion) | missing |

## Production

| Need | Status |
|---|---|
| Pre-production flow, research, shot list, QA tool | done |
| Skins and textures: skills, turntable, tile checker, pack builder, in-scene preview | done (not tested in the game) |
| Music, sfx, dialogue mix with ducking | done (you supply the audio) |
| Original game textures and sound effects | done: `tools/vanilla.py fetch` / `sounds` into a local cache (not shipped) |
| Background music | done: `tools/score.py` composes an original score from a section list (calm, build, battle, silence, dawn); synthesised, not orchestral |
| Voices | done (offline): `tools/voice.py` with Piper neural pt-BR voices (CC0 datasets, fetched to `work/voices/`) or Windows OneCore voices with SSML, plus character presets. Piper has no female pt-BR voice; no audio-driven lip-sync |
| Voice generation, audio-driven lip-sync | missing |
| GIF / social crops (9:16), subtitles export (SRT) | missing |
| Parallel rendering, 1080p60, GPU | done / untested GPU |

## Suggested order to close the gaps (highest impact first)

1. **Held items from item textures** (swords, pickaxes, bows, torches) plus hand poses.
2. **Non-cube blocks** (stairs, slabs, fences, torches, plants).
3. **More mobs**: enderman, skeleton, villager, iron golem, cow, sheep, wolf.
4. **Player clips**: sneak, swim, ride, bow draw, eat, sleep, climb, crawl.
5. **Armor, capes, elytra** layers.
6. **Sky**: sun, moon, stars, lightning; **motion blur**.
7. Verified mob UV tables, crowd instancing.

## Polish log

- **Walking through blocks (2026-11):** `tools/qa.py` now runs a dense path check (`window.__pathCheck`, every 0.05 s). On its first run it found
  real bugs in two films: in *The Last Torch* the courier ended the film inside the tower wall (fixed in `examples/last-torch`, the README
  media still show the old render), and in *Farol Negro* the warrior started inside the floor of a `hollow` (a hollow box also has a floor and a roof).

- **Shoulders / neck (2026-11):** arms were drawn 2 px lower than the torso top, so the torso showed above the shoulders and the head looked like it sat on a neck.
  Fixed: the arm box now extends 2 px above its pivot (flush with the torso top), as in the game.
- **Rain on the lens (2026-11):** drops 1.6 blocks from the camera read as big white bars in about a third of the stills of a rainy film.
  `weather.clear` (default 1.6, unchanged) now sets that distance; 3.0 removed the bars in "Farol Negro".
- **First-person and body lean (open):** the `first` camera follows the head rotation but ignores the body's `bodyRx` lean, so during
  `stance` (and other leaning clips) the view tilts toward the sky. Workaround: use `idle` + `lookAt` while a `first` shot is on.
- **Face art pass (open):** the `wide` and `angry` eye states are readable but blocky; under coloured night light the white reads lavender. A finer expression set (pupil size, lids, brows per skin) is the next face polish item.
