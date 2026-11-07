# The director plan (`plan.json` → `tools/compose.py` → `story.json`)

The fastest and cheapest way to a good film. You (the assistant) translate the user's prompt into a **short list of beats**;
`tools/compose.py` does the film-making arithmetic and writes a complete `story.json`:

- **blocking** on a flat arena inside generated terrain (trees and plants never grow in building sites or in the arena);
- **fight choreography** with anticipation, strike, reaction (block, dodge, hit, knock-back, fall, vanish), fencing distance kept at ~2 blocks;
- **coverage** that respects the 180° rule (the camera stays on one side of the line between the two fighters), cuts on action,
  over-the-shoulder for dialogue, low angles for heroes, extreme close-ups for reveals, a slow orbit to end;
- **impact grammar**: slow motion (`timeRemap`) and a white flash on decisive hits, handheld and dutch angles on action shots;
- **sound**: the game's own effects (attack, crit, sweep, shield block, hurt, thunder, teleport, footsteps) on every action, and an
  **original score** whose sections follow the beats (calm → build → battle → silence → dawn);
- **skins**: the user's skin, a persona painted from a photo, or a preset (Herobrine, knight, ninja, wizard, miner);
- a **shot list** (`shotlist.md`) you can review before rendering.

```bash
python tools/compose.py --example > plan.json          # the "me vs Herobrine" plan, ready to edit
python tools/compose.py plan.json --out films/duel      # story.json, music.wav, skins/, shotlist.md
python tools/render.py films/duel/story.json --preset preview --workers 4 --out films/duel/preview.mp4
python tools/qa.py films/duel/story.json --out films/duel/qa                              # then LOOK at the frames
python tools/render.py films/duel/story.json --workers 4 --out films/duel/film.mp4
```

The output is a normal `story.json`: after compiling you may still edit anything by hand (see `docs/STORYBOARD.md`).
Re-running `compose.py` overwrites it, so prefer fixing the plan.

## Top level

| field | meaning |
|---|---|
| `title`, `size`, `fps`, `seed` | as in `story.json` |
| `style`, `styleOverride`, `post`, `sky`, `weather`, `lighting`, `textures`, `blocks` | copied into the story (see `docs/STORYBOARD.md`) |
| `world` | `{ "biome", "radius", "arena": {"center":[x,z], "radius", "y"}, "trees", "water", "amp", "scale", "structures": [...], "extra": [...ops], "arenaFloor": "stone_bricks" }`, or a raw list of world ops |
| `cast` | `name -> { "skin": "file.png" \| "persona": {...} \| "preset": "herobrine", "name": "Shown name", "holding": "diamond_sword", "offhand", "eyes": "glow", "hidden": true, "nametag": true }`, or a mob: `{ "mob": "cow", "hidden": true, "parts": ["saddle"], "baby": true, "variant": "cold" }` (any of ~70 game mobs when cached; babies use the game's own baby models; variants: coats, breeds, biomes and professions, see `docs/MOBS.md`). Players also take `"armor"`, `"cape"`, `"elytra"`, `"offhand": "shield"` (the game's textures when cached; zombies walk with arms forward) |
| `marks` | `name -> [x, z]` start positions (defaults: first actor south of the centre, second north) |
| `beats` | the film, in order (below). Any beat may carry `"title"` (a title card over it), `"lighting"` (a key at its start), `"music"` (override its mood) and `"also"`: ambient actions that run in parallel without taking time, e.g. `[{"who": "calf", "to": [3, 4], "dur": 4}, {"who": "cat", "do": "sit", "at": 1.5, "dur": 3}]` (`do` defaults to `walk`, `at` is seconds after the beat starts) |
| `music` | `{ "key": "D", "bpm": 108, "volume": 0.55 }` or `false` |
| `nametags` | `true` to show floating name tags (off by default: cinematic) |
| `cameraSide` | `"right"` (default) or `"left"`: which side of the line of action the camera stays on |

Biomes: `plains forest taiga desert snowy nether wasteland` (top block, trees, plants). Structures:
`house tower ruins shrine pillar campfire` at `"pos": [x, null, z]` (null = on the ground). Keep structures out of the arena;
`compose` prints a warning when two structures overlap or one cuts into the arena.

## Beats

| beat | fields | what it does |
|---|---|---|
| `establish` | `dur`, `text`, `shot: crane\|orbit`, `eerie` | wide move onto the location, optional title |
| `walk` | `who`, `to: [x,z]` or `toward: actor, stop`, `run`, `pause` | walk/run with footsteps; tracking + front coverage |
| `line` | `who`, `text`, `to`, `emotion: angry\|scared\|shout\|smile\|sad`, `shot`, `voice: "lines/01.wav"` (a recording: mixed, music ducks, the mouth follows its loudness) | dialogue: subtitle in chat format, lip-sync, alternating close / over-the-shoulder |
| `look` | `who`, `at`, `emotion` | a reaction: turn the head and body |
| `reveal` | `who`, `at: [x,z]`, `witness`, `fx: lightning\|portal`, `glow` | the actor appears (lightning strike, flash, thunder), the witness flinches, extreme close-up on glowing eyes |
| `teleport` | `who`, `to: [x,z]` or `"behind:<actor>"` | portal particles, poof, Enderman teleport sounds |
| `faceoff` | `a`, `b`, `dur`, `gap`, `calm` | both take the ready stance facing each other; wide → close → close |
| `duel` | `a`, `b`, `exchanges` | a sword fight, one exchange per token (below) |
| `power` | `who`, `kind: lightning\|storm\|shockwave\|fireball\|levitate`, `target`, `hit`, `crater`, `then` | magic: summon pose, aura, the effect, knock-back on the target |
| `knockdown` / `getup` | `who`, `by` / `facing` | fall flat on the back / stand back up angry |
| `finisher` | `a`, `b`, `move`, `result: vanish\|die\|fall\|knockback` | a held beat (silence) on the winner's face, then the decisive slow-motion hit |
| `explode` | `at: [x,z]`, `radius`, `tnt` | TNT with fuse (or a plain explosion), crater, debris |
| `build` | `who`, `structure: house\|tower\|ruins\|shrine\|pillar\|campfire` (+ `w d h r block`) or `blocks: [[block,[x,y,z]],...]`, `at: [x,z]`, `dur`, `holding` | a build timelapse: the builder works, blocks pop in bottom-up with the right dig sounds, the camera circles the site then looks over the builder's shoulder. The site is kept free of trees automatically |
| `mine` | `who`, `blocks: [[x,y,z],...]`, `per`, `holding` | mining: cracks, debris and dig sounds block after block |
| `creeper` | `who` (a creeper in the cast), `target` (actor or `[x,z]`), `radius`, `then` | creeps up, hisses, swells and explodes: crater, blocks of nearby builds blown away, the victim thrown |
| `ride` | `who`, `mount` (a mob in the cast: horse, donkey, camel, pig, llama, strider, minecart...), `path: [[x,z],...]` or `to`, `run`, `dismount` | the rider walks to the mount, sits in the saddle, the mount walks or gallops along the path; tracking + front shots |
| `chase` | `runner`, `chaser`, `path: [[x,z],...]`, `speed`, `lag`, `gap` | a run along waypoints with the pursuer half a second behind; tracking then front shots |
| `silence` | `who`, `at`, `dur` | the held emotional beat after the climax: slow push-in, music silent |
| `victory` | `who`, `do`, `fireworks` (true or a count), `totem` | celebrate + level-up sound |
| `act` | `who`, `do`, `dur`, `to`, `face`, ... | any raw timeline action (all clips in `docs/STORYBOARD.md`) |
| `wait` | `dur`, `who`, `shot` | hold a shot |
| `title` | `text`, `dur`, `delay` | a title card over the next beat (takes no time) |
| `ending` | `dur`, `text`, `fireworks` | slow orbit, end card, fade out |

### Duel tokens

`"<attacker>:<move>[:<result>]"`, e.g. `"me:slash:block"`, `"herobrine:overhead:dodge"`, `"me:crit:hit"`.

- moves: `slash` (horizontal), `overhead` (two-handed chop), `thrust` (stab), `crit` (jump + chop, crit particles and sound),
  `sweep` (slash with the sweep arc), `swing`, `punch`, `lunge`
- results: `hit` (default; small knock-back, red damage tint, crit stars), `block` (guard + sparks + shield sound), `dodge`
  (side-step, the blade sweeps air), `knockback` (thrown 2.4 blocks with a hop, slow motion + flash), `fall`, `die`, `vanish`
  (death fall, then the game's white poof and the body disappears)

The attacker closes the distance with a short charge when the gap is over ~2.6 blocks; nobody leaves the arena.

Cameras stay out of buildings: if a planned camera would stand inside a structure (from `world.structures` or a `build`) anywhere
along the actor's path, it is mirrored to the other side of the action or pulled in.

## Shipped examples (all compile with `python tools/compose.py examples/<name>/plan.json --out films/<name>`)

| example | genre | what it shows |
|---|---|---|
| `herobrine-duel` | action / supernatural | reveal in lightning, dialogue, duel, teleport, lightning power, finisher, silence, ending |
| `creeper-surprise` | comedy / building | dialogue, a house built in a timelapse, a creeper sneaks up and blows half of it away, the punchline |
| `zombie-night` | survival / chase | first night: a zombie appears, a chase through the forest, a stone-sword fight, victory |
| `village-life` | slice of life | *Vila Viva*: a village, villagers by profession, babies and variants, ambient `also` actions, a horse ride, fireworks at dusk |

## From a prompt to a plan (examples)

- *"me in Minecraft fighting Herobrine"* → a persona from the user's photo (or their skin), `preset: herobrine` with `eyes: glow`
  and `hidden: true`, a night style, a shrine; beats: establish → walk → reveal → line ×2 → faceoff → duel → teleport → power → getup →
  duel → finisher → silence → ending. This is `python tools/compose.py --example`.
- *"two friends build a house and a creeper blows it up"* → `build` + `creeper` + `line` for the punchline: `examples/creeper-surprise`.
- *"my first night: a zombie chases me"* → `mob: zombie` in the cast, `chase`, `duel`, `victory`: `examples/zombie-night`.
- *"a mining trip that finds diamonds"* → a hand-built cave (`hollow` + `fill` ores), `mine` with `iron_pickaxe`, `look` + `line`, `victory`.
- *"a calm sunset fishing video"* → `golden-hour`, `walk`, `act` (`sit`, hold), `wait` shots, `ending`; music `calm`/`dawn` only.

Not everything is action: use `line`, `look`, `wait`, `walk` and `act` alone for dialogue, comedy and calm films.
