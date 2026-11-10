---
name: blockreel
description: Direct and render Minecraft-style animated films, cinematic shorts, vertical Reels, intros, and episodes from a prompt or references. Build block worlds, cast skins, stage shots, mix original music and effects, and deliver a reviewed MP4 using BlockReel. For standalone skins or resource packs, use the dedicated skills.
---

# BlockReel

You direct and build short blocky animations as code, then render them to MP4 frame by frame.
No video model is involved: every frame comes from a Three.js scene driven by a JSON storyboard.

## Choose the workflow before building

- **Reproduce an example.** Use its checked-in storyboard and audio recipe. Follow the reproduction commands before changing any creative decisions. Use the torch scene in `examples/first-night/README.md` as a clean-checkout control when diagnosing a different result.
- **Finish a cinematic film.** Use `docs/CINEMATIC-WORKFLOW.md` for showcase quality, multi-beat narrative, a look to match, or exact delivery requirements. Record the route in the brief. Compile supported beats as a starting point when useful, then direct each scene's camera, staging, lighting, and sound.
- **Build a simple clip or a draft.** Use the beat compiler for a straightforward action its presets cover, or when the user explicitly wants a rough preview. For any requested final, continue through picture and sound review and export the master at the brief's settings.

## 0. Bootstrap

Reuse a working checkout when available. The Claude Code marketplace installs the skill files. In Codex, open the runtime checkout as the project and have Codex read this file if the skill is not installed. Run the tools from the checkout. If needed, clone it:

```sh
git clone https://github.com/ViniciusNoetzold/mine-blockreel-skill-.git blockreel
cd blockreel
npm ci
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Use Node 20+, Python 3.11+, FFmpeg and FFprobe. With a compatible installed Chrome, set `CHROME_PATH` to its executable instead of downloading Chromium. Run commands from the checkout root and put film sources in `films/<name>/` or a project folder requested by the user.

For a Reel, check that `python tools/export.py reels --help` works in the runtime checkout. If the command is missing, use a current checkout with the dependencies installed.

Before building, identify which inputs are bundled, generated, supplied by the user, or in an optional cache. For a portable look use `"textures": "builtin"` for automatic texture and mob lookups and `"font": "css"` for text. Explicit asset paths still apply. Confirm the rig and load the requested skins, sprites and sounds in a test shot. Generate the audio referenced by the storyboard before previewing or rendering it.

For local game fidelity, use the optional commands in `tools/vanilla.py` as needed and keep their downloads in the ignored `work/` cache. Consult `docs/LEGAL.md` before distributing a render or project. If an intended asset is missing, use an appropriate permitted substitute or report what is pending. Use original or licensed effects for a public production.

## 1. Guides (read when you reach that step)

| File | Read it for |
|---|---|
| `docs/DIRECTOR-PLAN.md` | the beat plan for `tools/compose.py` (fights, reveals, dialogue, endings) |
| `docs/PREPRODUCTION.md` | steps A–C: briefing, research rules, templates for `brief.md` / `research.md` / `shotlist.md` |
| `DIRECTOR.md` | story, rhythm, camera, acting, action sequences |
| `TECHNIQUE.md` | pipeline, units, performance, extending the engine |
| `docs/STORYBOARD.md` | the exact `story.json` schema (the only source of truth for fields) |
| `docs/QA.md` | step E: the checklist and `tools/qa.py` |
| `docs/CINEMATIC-WORKFLOW.md` | exact timing, multi-scene continuity, shot review, audio and final media checks |
| `docs/REELS.md` | portrait direction, platform insets, native 9:16 QA, and Reels export |
| `styles/<style>/STYLE.md` | the look of the chosen style |
| `docs/SKINS.md`, `docs/BLOCK-ATLAS.md`, `docs/RESOURCE-PACKS.md`, `docs/MOBS.md` | asset work and mob-specific acting |
| `docs/EQUIPMENT.md` | capes, costume changes, and authorized mod item sprites |
| `docs/HUD.md` | opt-in event chat, hotbar, inventory, and timed crafting |
| `docs/COVERAGE.md` | what the engine can and cannot animate yet: check it before promising a scene |

## Genres (pick one first, like a style)

For an **opening**, start from `python tools/opening.py "<CHANNEL>" --out films/<name>` (name in blocks, blast, orbit, logo hold,
game sounds and an original score) and then adapt the generated `story.json` (block, skin, timing, extra shots).

Read `docs/GENRES.md`: **opening** (YouTube channel intro, 5-12 s), **cinematic short** (an epic or dramatic 20-60 s film,
e.g. `examples/` and the "Farol Negro" production), **series episode** (talking characters, comedy or adventure, 1-5 min, the
format of the big Minecraft animation channels). Each genre fixes pacing, camera grammar, sound and what to deliver; the premise
can be about anything the user wants.

## Beat compiler for simple clips and drafts

For supported actions, write a **beat plan** and compile it. The compiler provides default camera coverage, choreography and music. For a cinematic project, review what it generated against the brief and take manual control where the defaults miss the intended shot.

```bash
python tools/compose.py --example
# Save and adapt the example as films/<name>/plan.json (UTF-8).
python tools/compose.py films/<name>/plan.json --out films/<name>
python tools/render.py films/<name>/story.json --preset preview --out films/<name>/preview.mp4
```
This command produces a draft at half resolution and 12 fps. See `docs/DIRECTOR-PLAN.md` for supported beats. Record the brief (A), review the compiler's shot list (C), and complete QA (E) before delivering a requested master. If the compiler reports unavailable game sound cues, fill the beats that need sound with original or licensed effects. A music track alone can pass the audio stream check.
Write the plan in the user's language (subtitles, title, end card). Mix beats freely: **not every film is a fight**. The skill is for
any Minecraft animation the user imagines: comedy (`examples/creeper-surprise`), survival and chases (`examples/zombie-night`),
builds and timelapses (`build`), mining (`mine`), dialogue episodes (`line`/`look`), calm moods (`walk`/`act`/`wait`), slice of life with
villagers, babies and ambient `also` actions (`examples/village-life`), action
(`examples/herobrine-duel`). When a beat does not exist for what the user wants, use `act` (any clip) and world `changes`, or write that
part of the storyboard by hand. Save manual edits in a separate source or a repeatable post-compile script, since recompiling replaces the generated storyboard and shot list.

**Prompt → plan, worked example.** *"Me faça no Minecraft numa batalha contra o Herobrine"*: the user = `persona` from their photo
(or their skin, or ask once), Herobrine = `preset: herobrine`, `eyes: glow`, `hidden: true` (he arrives by `reveal`); night style;
a shrine near the arena; beats: establish → walk → reveal → 2 lines → faceoff → duel → teleport → power (lightning) → getup → duel →
finisher → silence → ending. Swords: `diamond_sword` for the hero, `iron_sword` for the villain.

## Casting and acting

- Cast a requested Minecraft wolf as `"mob": "wolf", "rig": "builtin"` in a plan or `"type": "wolf", "rig": "builtin"` in a storyboard. Use wolf acting such as `sniff`, `play_bow`, `head_tilt`, `bark`, and `howl`. Check `docs/MOBS.md` for the rig's full clip list and available looks. Place bark and howl sounds on the matching cue if the scene calls for them.
- For a short character, set an explicit standing `height` in blocks (for example 1.15), or use relative `scale`. Reframe close-ups to the actor's eyes and keep the feet on the floor.
- Stage a reaction around a clear target. Select a short clip such as `nod`, `shake_head`, `shrug`, `flinch`, `relief`, `salute`, `laugh`, or `inspect`. Use an `act` beat or timeline `do` with enough time for anticipation, the gesture, and recovery. Add a short `blend` and `lookAt` as needed. Check the transition in motion and inspect hair, shoulders and sleeve seams in the closest frame.
- When a cape is requested, choose a preset or use the supplied PNG with `cape.texture`. Use timeline changes for costume swaps. When a mod item is requested, confirm its ID and appearance, register its local sprite in `items`, and use that ID across held props and HUD. Stage its effect with supported scene cues. See `docs/EQUIPMENT.md`.
- Add `hud` only when the producer asks for a gameplay overlay. Match event text to the film's language. Time any death message to the actual story event. If a craft is shown, author the ingredients, result, and when the result moves to the inventory. Check legibility above letterbox bars and alongside subtitles.

## The user's photo → their skin

The user sends a photo of themself and wants to be in the film: look at the photo and fill a persona (`python core/persona.py example`
prints the template): skin tone, hair colour and style, facial hair, glasses, eye colour, top type/colour/pattern, bottom, shoes,
accessory. Then read the exact colours from the photo instead of guessing them:
```bash
python core/persona.py sample photo.jpg --region skin=X0,Y0,X1,Y1 --region hair=... --region top=... --region bottom=... --out colors.json
python core/persona.py paint persona.json films/<name>/skins/me.png --colors colors.json --preview films/<name>/tt.png
```
Pick regions inside flat, evenly lit areas (cheek, hair mass, shirt chest, trouser thigh). LOOK at the turntable and adjust once; tell
the user it is a stylised Minecraft version of them. In the plan use `"persona": {...}` or `"skin": "skins/me.png"`. Never use a photo of
someone who is not the user (or who did not agree). Presets: `herobrine knight ninja wizard miner`.

## A reference image

If the user sends a reference (a place, a build, a mood): read its palette and composition and translate them: time of day → style and
`lighting`, dominant materials → blocks (stone castle → `stonebrick`/`mossy_cobblestone`, desert → `biome: desert`), landmarks →
`structure` ops or hand-written `fill`/`set` builds, framing → the establishing `shot`. Describe what you took from it.

## World sense (rules the generator enforces - keep them when you build by hand)

- Things stand where they would in the game: buildings on levelled ground with a foundation, never inside or on top of a tree;
  trees and tall plants never grow inside a building site or the arena; no two buildings overlap; nothing floats.
- The action happens on clear, flat ground; landmarks (shrine, tower, house) frame it from the edges, not from inside it.
- Cameras are never inside leaves or blocks and never on a tree top: a tree that would block the lens is simply not planted.
- Light makes sense: torches and fire light the night warmly, caves and rooms without openings are dark, lightning flashes the scene.
- If you hand-write a world, run `tools/qa.py`: it FAILs actors or cameras inside blocks.

## A. Briefing (ask at most ONE short question)

Extract from the request: **premise** (one sentence), **tone** (comedy, horror, epic, wholesome…),
**length** (default 30–60 s), **characters** (which skins), **setting**, **style** (see `DIRECTOR.md` §8).
If something is missing and a sensible default exists, choose it and *say which defaults you chose*.
Ask a question only when the answer changes the whole film (e.g. "do you have skins for these characters?").
Save the result to `films/<name>/brief.md` (template in `docs/PREPRODUCTION.md`).

## B. Research (when it changes a production decision)

Use targeted research for unfamiliar techniques, references the user wants matched, or externally sourced assets. Record sources and the production decisions they informed in `films/<name>/research.md`:

1. **Animation language for the tone**: pacing, camera, comedy timing / horror dread / epic scale.
2. **Rigid-body character animation**: anticipation, overshoot, follow-through, squash substitutes, impact frames.
3. **Setting references**: block architecture, color palettes, landmarks for the chosen setting.
4. **Third-party music and sound-effect sources**: list the source, track name and license. Ask permission before downloading third-party audio. Use original generated or user-supplied audio when appropriate.

Then add a **"Principles to apply"** section: 5–10 bullets in your own words, each tied to a shot or rule in this film.
Never copy another work's scenes, characters or lines; extract principles. Keep local copies of any reference video
only in `work/` (gitignored); only your written conclusions go in the repo.

## C. Script and shot list

Write `films/<name>/shotlist.md` using the table in `DIRECTOR.md` §7 (add an **intent** column: what the shot makes
the viewer feel or know). Check it against the briefing: one idea, clear beats (setup → escalation → turn → payoff),
energy shape (quiet → loud → quiet), shot lengths per the tone, every line short.

Give each scene a change the viewer can perceive in action, composition, light, or sound. In first person, use gaze, depth, reveals and motivated changes of distance to preserve the viewpoint while giving each beat its own image. Check adjacent shots for repetitions that add no information or tension.

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
   - The user sends a **photo of themself** → persona skin (section above). Herobrine and other characters → `core/persona.py preset`.
   - Mobs: `docs/MOBS.md` lists portable rigs and cache-backed models. Match clips to the chosen rig and test its framing.
   - No skin → `python core/skin.py make ...` or the originals in `core/builtin/skins/`.
   - Sheet of blocks/items → `python core/atlas.py slice|label|faces` (see `docs/BLOCK-ATLAS.md`). Label only what you can identify.
2. **Storyboard.** Letterbox bars and the vignette (darkened corners) come from the style (`letterbox`, `vignette`); for a
   2.37:1 delivery crop the bars away at the end (`ffmpeg -vf crop=iw:iw/2.37`) so players do not show black bars, and turn the
   vignette off (`styleOverride.vignette: false`) if the user does not want it.
    Write `story.json` from the shot list (`docs/STORYBOARD.md`). Start from the nearest `examples/*/story.json`.
   Camera offsets are world-space: put the camera in front of the face you want to see.
3. **Test stills.** `python tools/render.py story.json --frame <t> --out check.png` and LOOK at the image
   (framing first, then light, then acting).
4. **Sound (unless the brief calls for silence).** Build every file the `audio` block points at. Use original or licensed sound effects for public projects, and reserve cached game effects for permitted local work. Compose an original score that follows the energy shape
   (`python tools/score.py --out music.wav --duration 30 --sections calm:0:7,build:7:15,battle:15:23,silence:23:26,dawn:26:30`), and voices: the user's recordings first; otherwise `tools/voice.py` (offline only: Piper neural voices fetched with
   `python tools/voice.py fetch`, e.g. `--voice piper:faber`, or the Windows OneCore voices `daniel`/`maria` with SSML pauses and emphasis),
   with a character preset (`hero`, `villain`, `monster`, `child`, `narrator`, `radio`). Fit each line inside its shot: measure it, then
   adjust `--rate` or the shot length. See `films/`-style `make_audio.py` in `docs/GENRES.md`.
   `python tools/audio.py story.json --out mix.wav`, listen, then render with audio (or mux the mix into the silent render).
5. **Preview.** `python tools/render.py story.json --out preview.mp4 --fps 12 --scale 0.5`. Review the moving preview with the mix. Fix issues in staging, timing, legibility or sound, then review the affected interval again.
6. **Final render.** `python tools/render.py story.json --workers 2 --out film.mp4`. Benchmark a short segment at the delivery resolution with the intended renderer and worker count. Include the scene with the most geometry and a lighting or material change. Each worker loads the world in a separate browser. Try `--gpu` after a successful full-size probe. If WebGL reports a failed shader or lost context, rerender the affected interval using the default software renderer.
   Economy: compose → preview → QA on stills → only then the final render; never re-render the whole film to check one shot
   (`--frame t` or `--start/--end`).

## Reels and portrait films

When the user asks for a Reel or vertical 9:16, use `tools/export.py reels story.json --out reel.mp4`. Read `docs/REELS.md`. Plan each shot for portrait, use `reels.camera` overrides for a landscape storyboard, and check the first-person hands, action near the edges, subtitles and crafting with `tools/qa.py --preset reels`. Preserve the requested runtime and audio. For both formats, deliver separate reviewed MP4s from the shared storyboard.

## Deliverables (after QA)

`python tools/export.py thumbnail story.json --t <best moment> --title "TITLE" --out thumb.jpg`, `export.py srt` for subtitles,
`export.py gif film.mp4 --start .. --dur 6` for a teaser, `export.py reels story.json --out reel.mp4` for Reels
(re-rendered at 1080x1920). Add `--motion-blur 3` to the final render for fast action if the user can wait 3x longer.

## E. Quality review (MANDATORY before delivery)

```bash
python tools/qa.py films/<name>/story.json --out films/<name>/qa
```
It renders at least 8 spread frames (opening, every shot change, close-ups, ending), builds a contact sheet, and runs
automatic checks (camera inside a block, actor out of frame, face pointing away from camera, subtitle clipped, shot
longer than the limit for its tone). Then **open every frame image and look at it** and judge what the script cannot:
skin holes, odd shadows, awkward pose, unclear story, pacing. Fix, re-render, repeat until clean.
After the final render, play the encoded file with sound. Inspect decoded frames from the opening, both sides of major lighting or set changes, each recovered interval, and the ending. Check terrain, walls, particles and practical lights against the approved preview. Use `tools/check_media.py` with the target duration, size, fps, and `--require-audio` when sound is requested.

Record the reviewed intervals, fixes and media check in `films/<name>/qa.md` (see `docs/QA.md`). Resolve each FAIL and record a decision for every WARN. If a requested element or playback check is pending, label the output as a preview or an unreviewed export and report the specific gap. Deliver the reviewed MP4 plus the brief, shot list, storyboard and the permitted audio sources or recipe. For a browser-playable publication, link the README to the deployed player and verify sound, seeking and full duration at the public URL.

## Rules

- Never copy game assets (textures, sounds, fonts) into the repo or the film folder unless the user supplied them
  and owns them. Use the original built-ins otherwise. See `docs/LEGAL.md`.
- Do not claim a feature works if you did not run it. If a render or asset step fails, say what failed.
- Use the engine's real features (listed in `docs/STORYBOARD.md`). If the scene needs something marked missing in `docs/COVERAGE.md`
  (more mobs, armor, swim/ride clips...), say so up front and offer the closest thing that exists;
  do not fake it with unsupported JSON fields (they are silently ignored).
- Check proportions in close-ups, not only wide shots (shoulders flush with the torso, head directly on the body, faces readable).
- Keep user skins/textures untouched; write derived files next to them with a new name.
- Everything under `films/` and `work/` is gitignored. Examples that ship with the repo live in `examples/`.
