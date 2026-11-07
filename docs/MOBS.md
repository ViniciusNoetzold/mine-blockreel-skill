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

**Partial:** the blaze's rods and the magma cube's segments are placed by the game's Molang animations, which are not evaluated:
their parts sit stacked. The evoker and the boat are not in the samples under those names.

**Zombie as an actor:** a zombie can also be a normal actor with the zombie texture as its skin and the `zombie` walk clip
(`compose.py` does this): every player clip (fights, falls, faces) then works on it.

## Without the cache: original rigs and textures

Three box rigs ship with BlockReel (`core/engine/mobs.js`): `creeper`, `pig`, `spider`, driven by a 64x32 texture you provide in the
classic layout (`core/builtin/mobs/sample-*-layout.png` are CC0 placeholders that show the layout). They are used only when the game's
geometry is not cached or `"textures": "builtin"` is set.
