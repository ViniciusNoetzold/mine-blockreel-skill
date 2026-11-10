# Mobs

## Every mob, with the game's own geometry (recommended)

```bash
python tools/vanilla.py mobs      # ~70 mobs: geometry + texture into work/vanilla/mobs/ (local cache, never committed)
```
`tools/vanilla.py mobs` reads Mojang's official `bedrock-samples`: each entity's client definition (which geometry and texture it uses)
and the geometry files (bones, pivots, cubes, UVs, inflate, mirror), resolves inherited geometries (a zombie is a humanoid) and writes a
normalised `<mob>.geo.json` + `<mob>.png`. The engine (`core/engine/geo.js`) builds the rig and animates it **by bone names**:
legs in diagonal pairs (two-legged mobs alternate), arms opposite the legs (zombies, husks, drowned and zombified piglins hold them
forward), wings flap, tails wag, tentacles wave, the head idles and follows `lookAt`, `swell` inflates and flashes like a creeper,
`hit`/`knockback` tilt back, `die` falls sideways like the game, attack clips swing the right arm, `cast`/`summon` raise both.

Use: `"actors": { "moo": { "type": "cow", "pos": [3, null, 2] } }`. Optional equipment (saddle, saddlebags, chest, reins, armour,
collar) is hidden like in the game unless you ask for it: `"parts": ["saddle"]`. In the director: `"cast": { "moo": { "mob": "cow" } }`.

Names: `cow pig sheep chicken wolf cat ocelot fox horse donkey skeleton_horse zombie_horse rabbit llama goat mooshroom panda polar_bear
villager zombie_villager witch pillager vindicator iron_golem snow_golem allay skeleton stray wither_skeleton zombie husk drowned
zombie_pigman piglin hoglin creeper spider cave_spider enderman endermite silverfish slime magma_cube ghast blaze bat bee parrot phantom
vex guardian ravager shulker warden ender_dragon wither axolotl frog squid glow_squid dolphin turtle cod salmon camel sniffer strider
breeze armadillo minecart armor_stand` (`work/vanilla/mobs/index.json` lists what your cache has).

Checked by rendering all of them walking (and by `tests/geo_check.mjs` for the rules): bodies lie down where the game lays them
(`bind_pose_rotation`, pivot-less cube rotations turn about the cube's centre; the polar bear, cat and ocelot body poses the game sets in
code are added by the fetch tool), bones marked `neverRender` hide only their own cubes.

**The game's own animations (Molang).** The fetch tool also stores each mob's animations and its `animate` / `pre_animation` scripts;
`core/engine/molang.js` evaluates them every frame (a small Molang interpreter: math in degrees, `query.*` / `variable.*`, ternaries,
keyframes, `this`). So the blaze's rods orbit, the magma cube's slices squash, a horse's legs and tail, a bee's wings, a villager's arms,
a chicken's flaps and ~60 other mobs move exactly like the game. Queries the engine answers: `life_time`, `anim_time`,
`modified_move_speed`, `modified_distance_moved` (gaits fade out when the mob stops), `is_sprinting`, `is_sleeping`, `is_sitting`,
`is_attacking`... Situational animations (sitting, lying, sleeping, baby, eating, attacking...) play only when the clip asks for them.
Disable per actor with `"molang": false` (the bone-name rules take over). The wolf, polar bear and ender dragon keep the bone-name rules (their
game animations drive an older rig the game builds in code); the guardian's spikes use the game's absolute positions. Emissive mobs (blaze, magma cube, glow squid) glow in the dark: their texture's alpha is
a glow map, as in the game. The evoker and the boat are not in the samples under those names.

**Babies and variants.** `"baby": true` uses the game's own baby model and texture (calf, piglet, lamb, chick, pup, kitten, foal, cria,
cub, kid villager, baby zombie... about 35 mobs); a mob without one is drawn at half size with the head its scripts enlarge.
`"variant"` picks another coat, breed, biome or state the game ships, e.g. `"cow": cold | warm`, `"chicken" / "pig": cold | warm`,
`"cat": black red siamese british calico persian ragdoll tabby jellie all_black`, `"wolf": ashen black rusty snowy spotted striped woods`,
`"horse": white creamy black gray darkbrown`, `"rabbit": white black white_splotched gold salt toast`, `"llama": white brown gray`,
`"fox": arctic`, `"panda": lazy worried playful brown weak aggressive`, `"axolotl": cyan gold lucy wild`, `"frog": cold warm`,
`"parrot": green red_blue yellow_blue grey`, `"shulker"`: the 16 colours, `"villager"` / `"zombie_villager"`: a biome
(`desert jungle plains savanna snow swamp taiga`) or a profession on plains clothes (`armorer butcher cartographer cleric farmer fisherman
fletcher leatherworker librarian shepherd tool_smith weapon_smith stonemason nitwit`). Babies take the same variants where the game has
them (`{ "type": "cat", "baby": true, "variant": "siamese" }`). `work/vanilla/mobs/index.json` lists what your cache has; an unknown
variant falls back to the default and logs the known ones. Villagers are layered like the game: bare skin + biome clothes + profession.

**Zombie as an actor:** a zombie can also be a normal actor with the zombie texture as its skin and the `zombie` walk clip
(`compose.py` does this): every player clip (fights, falls, faces) then works on it.

## Without the cache: original rigs and textures

BlockReel ships `creeper`, `pig`, and `spider` box rigs driven by a 64×32 texture in the classic layout
(`core/builtin/mobs/sample-*-layout.png` shows each layout). The bundled wolf has its own quadruped rig and original 64×64 coat.

## Direct a wolf as the lead

Start with this cast entry in a beat plan. The compiler picks the original rig for a wolf unless you request a cached variant or rig.

```json
{"cast": {"luna": {"mob": "wolf", "name": "Luna", "rig": "builtin", "parts": ["collar"]},
          "scout": {"height": 1.15, "name": "Scout"}}}
```

In a hand-authored storyboard, use `"type": "wolf"` and `"rig": "builtin"`. Keep `parts` empty for a wild wolf, or include `"collar"`
for a tamed look. Set `"baby": true` for a smaller cub. An optional `texture` in a storyboard can repaint the bundled coat using the
same layout as `core/builtin/mobs/wolf.png`. For a specific game coat, use `"rig": "vanilla"` with the desired `variant` from the local cache.

| Performance | Clips for the original wolf |
|---|---|
| Travel | `walk`, `run`, `sneak`, `jump` |
| Behavior | `sit`, `sleep`, `sniff`, `play_bow`, `head_tilt`, `wag` |
| Vocal pose | `bark`, `howl` (add a separate sound cue when the film calls for it) |
| Reaction | `scared`, `hit`, `knockback`, `fall`, `die` |

Use `act` with `do`, `dur`, and `shot` in a beat plan. The wolf can look at actors, the camera, or a world point via `lookAt`.
Build reactions through the muzzle, ears, legs, and tail. Player face textures, held gear, and humanoid combat clips belong to the
player rig. Cached models use their own rig and motion set.

`height` sets the standing height in blocks. Use `scale` for a multiplier instead, for example `"scale": 0.75` on a cub.
The director frames close and tracking shots to suit the cast. Check a full-body shot beside another actor or a familiar block
when the height difference matters to the story.
