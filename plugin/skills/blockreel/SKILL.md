---
name: blockreel
description: Make Minecraft-style animated videos (the classic blocky "Minecraft animation" look) from a story idea, using the user's own skins and block textures, rendered in code. Runs a pre-production flow (briefing, web research, script, shot list), builds the film, and does a mandatory visual QA before delivering. Use when the user wants a Minecraft animation, a short film, or a scene with blocky characters. Skins and texture packs have their own skills.
---

# BlockReel

You direct and build short blocky animations as code, then render them to MP4 frame by frame.
No video model is involved: every frame comes from a Three.js scene driven by a JSON storyboard.

**The flow is A → E. Do not jump to the storyboard (D) before you have a brief and a shot list (A–C).**
Quality comes from preparation and from looking at your own frames (E), not from more JSON.

## 0. Bootstrap (first use)

```bash
export BLOCKREEL_HOME="${BLOCKREEL_HOME:-$HOME/blockreel}"
[ -d "$BLOCKREEL_HOME" ] || git clone https://github.com/ViniciusNoetzold/mine-blockreel-skill- "$BLOCKREEL_HOME"
cd "$BLOCKREEL_HOME" && npm install && pip install -r requirements.txt
python tools/vanilla.py fetch    # ORIGINAL game textures + mob/chest/steve/alex textures -> work/vanilla/ (local cache, ~45 KB)
python tools/vanilla.py sounds   # ORIGINAL game sound effects -> work/vanilla/sounds/ (local cache, ~1 MB, no music)
```
**Look like the game by default.** Unless the user asks for their own textures, films use the original textures from the cache
(the engine picks them up automatically; `"textures": "builtin"` opts out to the CC0 originals). Mobs: `/work/vanilla/entity/zombie.png`,
`creeper.png`, `pig.png`, `spider.png`; default skins `steve.png` / `alex.png`. These files are Mojang's: they stay in `work/` on the
user's machine and are **never** committed or shipped (`docs/LEGAL.md`).
Needs Node 20+, Python 3.11+, ffmpeg and Chrome/Chromium (set `CHROME_PATH`, or run
`python -m playwright install chromium`). Work in `$BLOCKREEL_HOME/films/<name>/` or in the
folder the user started in; never write inside `core/`.

## 1. Guides (read when you reach that step)

| File | Read it for |
|---|---|
| `docs/PREPRODUCTION.md` | steps A–C: briefing, research rules, templates for `brief.md` / `research.md` / `shotlist.md` |
| `DIRECTOR.md` | story, rhythm, camera, acting, action sequences |
| `TECHNIQUE.md` | pipeline, units, performance, extending the engine |
| `docs/STORYBOARD.md` | the exact `story.json` schema (the only source of truth for fields) |
| `docs/QA.md` | step E: the checklist and `tools/qa.py` |
| `styles/<style>/STYLE.md` | the look of the chosen style |
| `docs/SKINS.md`, `docs/BLOCK-ATLAS.md`, `docs/RESOURCE-PACKS.md`, `docs/MOBS.md` | asset work |
| `docs/COVERAGE.md` | what the engine can and cannot animate yet: check it before promising a scene |

## Genres (pick one first, like a style)

Read `docs/GENRES.md`: **opening** (YouTube channel intro, 5-12 s), **cinematic short** (an epic or dramatic 20-60 s film,
e.g. `examples/` and the "Farol Negro" production), **series episode** (talking characters, comedy or adventure, 1-5 min, the
format of the big Minecraft animation channels). Each genre fixes pacing, camera grammar, sound and what to deliver; the premise
can be about anything the user wants.

## A. Briefing (ask at most ONE short question)

Extract from the request: **premise** (one sentence), **tone** (comedy, horror, epic, wholesome…),
**length** (default 30–60 s), **characters** (which skins), **setting**, **style** (see `DIRECTOR.md` §8).
If something is missing and a sensible default exists, choose it and *say which defaults you chose*.
Ask a question only when the answer changes the whole film (e.g. "do you have skins for these characters?").
Save the result to `films/<name>/brief.md` (template in `docs/PREPRODUCTION.md`).

## B. Research (web, recorded with links)

Use WebSearch / WebFetch. Write everything to `films/<name>/research.md`, every claim with a link:

1. **Animation language for the tone**: pacing, camera, comedy timing / horror dread / epic scale.
2. **Rigid-body character animation**: anticipation, overshoot, follow-through, squash substitutes, impact frames.
3. **Setting references**: block architecture, color palettes, landmarks for the chosen setting.
4. **Free-to-use music and sound-effect sources**: list the source, the track name and **its license**. Never download
   or add audio without the user's permission; the user supplies the files that go into `story.json`.

Then add a **"Principles to apply"** section: 5–10 bullets in your own words, each tied to a shot or rule in this film.
Never copy another work's scenes, characters or lines; extract principles. Keep local copies of any reference video
only in `work/` (gitignored); only your written conclusions go in the repo.

## C. Script and shot list

Write `films/<name>/shotlist.md` using the table in `DIRECTOR.md` §7 (add an **intent** column: what the shot makes
the viewer feel or know). Check it against the briefing: one idea, clear beats (setup → escalation → turn → payoff),
energy shape (quiet → loud → quiet), shot lengths per the tone, every line short.

## D. Build

1. **Assets.**
   - **The user sends a skin → use THAT skin**, unchanged, in the film (copy it into the film folder, reference it in `story.json`).
     `python core/skin.py validate skin.png` first; if legacy 64x32, `convert` to a new file. Skins you create must pass `validate`
     (64x64 RGBA PNG, base layer fully opaque, slim/classic detected) so they also upload to the real game (Java skin page/launcher).
   - Skin given as a screenshot / scaled image → `python core/skin.py snap in.png out.png --crop x0,y0,x1,y1`, then `validate`.
     If rows are missing, say so and ask for the full image.
   - Skin as a rendered 3D picture of a character → cannot be turned into a texture reliably. Say so.
   - Skin to create or improve → run the **`blockreel-skins`** skill (`/blockreel:blockreel-skins`): research, palette plan, layered painting,
     `python tools/turntable.py skin.png --out tt.png` and at least 2 looked-at rounds. Block/item textures or a resource pack → **`blockreel-textures`**
     (`core/tilecheck.py`, `tools/pack_preview.py`, `core/pack.py`). Use the results inside the film (`story.json` skin paths / `blocks` folder).
   - Mobs: `docs/MOBS.md` (you need the user's textures; creeper-, pig-, spider-shaped rigs and a zombie via the player rig).
   - No skin → `python core/skin.py make ...` or the originals in `core/builtin/skins/`.
   - Sheet of blocks/items → `python core/atlas.py slice|label|faces` (see `docs/BLOCK-ATLAS.md`). Label only what you can identify.
2. **Storyboard.** Letterbox bars and the vignette (darkened corners) come from the style (`letterbox`, `vignette`); for a
   2.37:1 delivery crop the bars away at the end (`ffmpeg -vf crop=iw:iw/2.37`) so players do not show black bars, and turn the
   vignette off (`styleOverride.vignette: false`) if the user does not want it.
    Write `story.json` from the shot list (`docs/STORYBOARD.md`). Start from the nearest `examples/*/story.json`.
   Camera offsets are world-space: put the camera in front of the face you want to see.
3. **Test stills.** `python tools/render.py story.json --frame <t> --out check.png` and LOOK at the image
   (framing first, then light, then acting).
4. **Preview.** `python tools/render.py story.json --out preview.mp4 --fps 12 --scale 0.5`.
5. **Sound (not optional).** Build every file the `audio` block points at: original game effects from `work/vanilla/sounds/`
   (explosions, doors, chests, mobs, hits, steps, rain, thunder, fire), made-up sounds only where the game has none (whoosh,
   riser: the game's music has other rights holders), an ORIGINAL score that follows the energy shape
   (`python tools/score.py --out music.wav --duration 30 --sections calm:0:7,build:7:15,battle:15:23,silence:23:26,dawn:26:30`), and voices (the user's recordings, or local TTS, e.g. the
   Windows voice "Microsoft Maria" for pt-BR; pitch-shift for villains). See `films/`-style `make_audio.py` in `docs/GENRES.md`.
   `python tools/audio.py story.json --out mix.wav`, listen, then render with audio (or mux the mix into the silent render).
6. **Final render.** `python tools/render.py story.json --out film.mp4`. Software GL is about 1 s/frame at 960x540:
   tell the user how long a long film will take.

## E. Quality review (MANDATORY before delivery)

```bash
python tools/qa.py films/<name>/story.json --out films/<name>/qa
```
It renders at least 8 spread frames (opening, every shot change, close-ups, ending), builds a contact sheet, and runs
automatic checks (camera inside a block, actor out of frame, face pointing away from camera, subtitle clipped, shot
longer than the limit for its tone). Then **open every frame image and look at it** and judge what the script cannot:
skin holes, odd shadows, awkward pose, unclear story, pacing. Fix, re-render, repeat until clean.
Record the result in `films/<name>/qa.md` (template in `docs/QA.md`): what you checked, what you found, what you fixed,
and what you could not verify. Only then deliver `film.mp4` plus the project folder.

## Rules

- Never copy game assets (textures, sounds, fonts) into the repo or the film folder unless the user supplied them
  and owns them. Use the original built-ins otherwise. See `docs/LEGAL.md`.
- Do not claim a feature works if you did not run it. If a render or asset step fails, say what failed.
- Use the engine's real features (listed in `docs/STORYBOARD.md`). If the scene needs something marked missing in `docs/COVERAGE.md`
  (held tools, stairs and fences, more mobs, sneak/swim/ride clips...), say so up front and offer the closest thing that exists;
  do not fake it with unsupported JSON fields (they are silently ignored).
- Check proportions in close-ups, not only wide shots (shoulders flush with the torso, head directly on the body, faces readable).
- Keep user skins/textures untouched; write derived files next to them with a new name.
- Everything under `films/` and `work/` is gitignored. Examples that ship with the repo live in `examples/`.
