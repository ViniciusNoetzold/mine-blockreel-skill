# Coverage: what BlockReel can and cannot animate yet

The goal is a skill that can make *any* Minecraft animation. It is not there yet. This file is the honest gap list, so nobody
(including the assistant) claims more than is true. Status: **done** (rendered and looked at), **partial**, **missing**.

## Characters

| Need | Status | Notes |
|---|---|---|
| Player model from a skin (classic / slim, legacy 64x32, both layers) | done | proportions checked against the game: shoulders flush with the torso top, head sits directly on the body (no neck) |
| Face: blink, eyes, mouth, wounds, glow, lip-sync | done | rows 3-7 of the face are repainted; skins must keep eyes on row 4 |
| ~70 mobs with the game's own geometry and texture (cow, sheep, horse, villager, skeleton, enderman, iron golem, warden, ender dragon...) | done | `tools/vanilla.py mobs` + `core/engine/geo.js`; walk/idle/look/hit/die/swell animated by bone names; all rendered and checked (`docs/MOBS.md`) |
| Blaze rods, magma cube segments | partial | placed by the game's Molang animations, not evaluated |
| Creeper-, pig-, spider-shaped rigs without the cache | done | CC0 fallback rigs (`core/engine/mobs.js`) |
| Zombie / any humanoid mob | done | a normal actor with its texture and the `zombie` clip |
| Mob-specific animations (a spider's crawl, a horse's gallop, a dragon's flight path) | partial | generic leg/arm/wing/tail rules; exact per-mob animations would need a Molang interpreter |
| Baby mobs, mob variants | missing | |
| Armor layers, capes, elytra, shields | missing | |
| Crowds of hundreds | missing | many actors work, but there is no instancing |

## Held items and props

| Need | Status | Notes |
|---|---|---|
| A block in the hand | done | `"holding": "planks"` |
| Tools, swords, bows, torches as items (extruded sprite from an item texture) | done | `holding`/`offhand`, switchable per segment; the blade follows the strike (`wrist`) |
| Doors, chests | done | `props`; chest lid now 90° / 0.5 s / ease-out like the game. **Open:** the chest uses a block texture, not the entity texture (`entity/chest.png` is fetched but not mapped yet) |
| Beds, signs, furnaces, minecarts, boats, rails | missing | |

## Animation (player)

| Need | Status |
|---|---|
| idle walk run wave talk mine punch dance sit look scared jump die spin | done |
| swing hit lunge stance shout point raise zombie (anticipation, overshoot) | done |
| Clip blending, turning, look-at, speed ramps | done |
| slash overhead thrust guard dodge knockback (with hop) fall getup kneel cast summon levitate bow charge celebrate sneak crouch stagger | done |
| swim, crawl, climb, ride a mob or vehicle, eat/drink, sleep, elytra glide | **missing** |
| Held-item-aware hand poses (arm follows the tool) | partial: `wrist` turns the blade along the arm in thrusts and slashes |
| Inverse kinematics, cloth/cape physics | missing |

## World

| Need | Status | Notes |
|---|---|---|
| Cube blocks with any texture, tops/sides/bottoms, transparency, emissive, flowing water/lava | done | |
| Break, place, TNT, explosions, crack stages, debris | done | |
| Non-cube blocks: stairs, slabs, fences, walls, torches, plants (cross), snow layers, carpets, fire | done | `core/engine/mesher.js` shapes |
| Trapdoors, doors as blocks, vines, rails, redstone, pistons, signs, beds | missing | |
| Face culling, the game's face shading, smooth-lighting AO, sky + block light propagation, mip-maps | done | no z-fighting, no shimmer, torches light the night |
| Terrain generation, biomes, arena flattening, structures (house, tower, ruins, shrine, pillar, campfire) | done | `terrain` / `structure` ops; building sites are kept free of trees |
| Very large worlds | done | measured: 1.7 M blocks set up in 5 s and render at 0.7 s/frame (720p, software GL); 4.4 M blocks in 13 s and 0.6 s/frame. Dense volume mesher, 32x32 chunks, chunks past the fog are not drawn |
| Caves, overhangs, villages | missing | |
| Trees | done | oak, birch, spruce, dead; trees blocking a camera are not planted |
| Sky: sun, moon, stars, the game's cloud layer, lightning | done | dome with a level horizon, sunset glow |
| Rain and snow | done | |

## Effects and look

| Need | Status |
|---|---|
| Seeded cube particles: break, explosion, smoke, fire, sparks, dust, blood, confetti | done |
| Bloom, depth of field, grain, grade, chromatic aberration, flash/whip/fade | done |
| Motion blur | missing |
| Crit stars, sweep arc, death poof, portal, aura, enchant dust, torch flame | done |
| Potion swirls, totem, fireworks | missing |
| Custom shaders (RTX-style reflections, ambient occlusion) | missing |

## Production

| Need | Status |
|---|---|
| Pre-production flow, research, shot list, QA tool | done |
| Director compiler: a short beat plan -> full story with coverage, fight choreography, sound and score | done: `tools/compose.py`, `docs/DIRECTOR-PLAN.md` |
| Skin from a photo of a person (persona painter + colour sampling) | done: `core/persona.py` (the assistant reads the photo; the tool samples exact colours and paints) |
| The game's font for name tags, chat subtitles, titles (accents included) | done (cached locally) |
| Skins and textures: skills, turntable, tile checker, pack builder, in-scene preview | done (not tested in the game) |
| Music, sfx, dialogue mix with ducking | done (you supply the audio) |
| Original game textures and sound effects | done: `tools/vanilla.py fetch` / `sounds` into a local cache (not shipped) |
| Background music | done: `tools/score.py` composes an original score from a section list (calm, build, battle, silence, dawn); synthesised, not orchestral |
| Voices | done (offline): `tools/voice.py` with Piper neural pt-BR voices (CC0 datasets, fetched to `work/voices/`) or Windows OneCore voices with SSML, plus character presets. Piper has no female pt-BR voice; no audio-driven lip-sync |
| Audio-driven lip-sync | missing |
| GIF / social crops (9:16), subtitles export (SRT) | missing |
| YouTube-style channel openings | done: `tools/opening.py` (name in blocks, blast, orbit, logo hold, sound) |
| Parallel rendering, 1080p60, GPU | done / untested GPU |

## Suggested order to close the gaps (highest impact first)

1. **Molang animations** for exact per-mob motion (blaze rods, magma cube, gallop, flight).
2. **Armor, capes, elytra, shields** layers.
3. **Player clips**: swim, ride, eat, sleep, climb, crawl.
4. **Doors/trapdoors/beds/signs as blocks**, villages, caves.
5. **Motion blur**, crowd instancing, audio-driven lip-sync.

## Polish log

- **v0.2 fidelity pass (2026-11):** world mesher (culling, the game's face shading, AO, light propagation, mip-maps), sky dome with sun/moon/
  stars/clouds and lightning, held items, combat clips, red damage tint and death poof, terrain and structures, the game font, the director
  compiler, persona skins. Found and fixed while reviewing frames: a house generated inside a tree canopy (sites are now reserved), cameras
  snapped onto tree tops or buried in leaves (cameras ignore canopies; trees blocking a lens are not planted), smoke hiding a face during
  dialogue, a talking gesture raising the sword across the face, close-ups with the lens inside the other fighter.

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
