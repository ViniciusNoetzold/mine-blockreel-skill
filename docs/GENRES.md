# Genres

A genre is to BlockReel what a style is to a style library: it fixes the grammar (length, pacing, camera, sound, deliverables)
and leaves the topic open. Pick one in the briefing; the premise can be about anything. Look (`styles/`) is a separate choice.

| Genre | Length | Shot length | Camera grammar | Sound | Deliver |
|---|---|---|---|---|---|
| **opening** (channel intro) | 5-12 s | 0.4-1.5 s, one held logo beat at the end | fast push-ins, whip pans between hits, one orbit around the logo, end locked | one riser into ONE hit on the logo; game "pop"/level-up stings; no dialogue | `opening.mp4`, a 1080x1920 crop if asked, the still of the logo frame |
| **cinematic short** | 20-60 s | calm 2-4 s, action 1-2 s | establishing → scale reveal → close-ups → fight with handheld/dutch → one silence → wide pull-back | music bed with a silence before the payoff, game effects on every impact, 0-3 short lines | film, `brief/research/shotlist/qa.md`, 6 key stills, a 6 s GIF |
| **series episode** | 1-5 min | dialogue 2-4 s, gags 0.5-1 s | shot / reverse-shot singles for every line, reaction close-ups, wides only to reset geography | voices for every line (recorded or TTS), lip-sync from subtitles, game ambience and effects, light music under dialogue (ducked) | episode, subtitles in chat format, thumbnail still |

## opening (YouTube-style channel intro)

- **Beats:** a block or mob in extreme close-up (0-1 s) → the world assembles or explodes (TNT, blocks placed in a wave with `changes.place`)
  → the channel name built from blocks or as a title card over a moving shot → the logo hold (1-2 s, locked camera) → cut.
- **Text:** the channel name is the only text. Build it from blocks (world `set`/`place` ops, one letter column per beat) or use a title.
- **Sound:** riser 1-2 s, a hit exactly on the logo frame (`random/explode` or `random/levelup` from the game cache), a whoosh on every whip.
- **Pitfall:** more than one idea. An opening is one gesture.

## cinematic short (what "Farol Negro" is)

- The structure, energy shape and action rules of `DIRECTOR.md` §2 and §10: hook in 3 s, one scale reveal, 1-2 s action shots,
  slow motion on the decisive hit, one silence, a quiet end card.
- Three lighting acts by `lighting` keyframes; one palette per location.
- **Sound recipe** (see `films/farol-negro/make_audio.py` when you have the film folder, or rebuild it): layer 2-3 game effects per
  impact (hit + hurt + knockback), loop the game's rain/fire ambience, synthesise only what the game lacks (whoosh, riser, music beds),
  voices by TTS or recordings with a pitch shift for villains, `music.duck` under dialogue, a limiter at the end (peaks ≤ -1 dB).

## series episode (dialogue-driven, any topic)

- Every line: the speaker in a single, face toward camera, `talk` clip, subtitle ≤ 10 words, ≥ 1.5 s on screen; reaction shot after
  the line that lands. Comedy timing: hold 0.4-0.8 s before the reaction (`DIRECTOR.md` §3).
- Characters: the user's skins (use them as sent), else Steve/Alex from the vanilla cache, else originals made with `blockreel-skins`.
- World: original game textures from the vanilla cache, built from real block names; no character spawns inside a block or a tree
  (`tools/qa.py` FAILs actors inside blocks at sampled frames; check every walk path against the world too).
- Sound: a voice for every line (the user's recordings, or local TTS), game footsteps on walks, door/chest sounds on every prop event.

## Fidelity rules (all genres)

- Behave like the game: doors swing 90° in ~0.4 s, a chest lid opens to 90° in ~0.5 s with an ease-out and no bounce, TNT flashes
  for its fuse then explodes, mobs use their own clips (`zombie` arms forward). Do not invent mechanics the game does not have unless the
  premise asks for it.
- No character may start or walk inside a block, a tree or a wall: route walks through doors and around obstacles.
- If a needed thing is missing in `docs/COVERAGE.md`, say so and use the closest thing that exists.
