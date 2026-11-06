# QA: The Last Torch

Run: `python tools/qa.py examples/last-torch/story.json --out out/qa-lt` (26 frames: opening, after every cut, inside longer shots, ending),
then every frame was opened and looked at. Three review rounds; this is the state of the final one.

## Automatic checks (final run: 0 FAIL, 8 WARN) and the decision for each

| Check | Decision |
|---|---|
| t=6.25, 6.8: warden acting but out of frame | **Intentional.** Shot 3 is the courier's reaction close-up; she looks at what the audience has not seen yet. The next shot shows him |
| t=12.85: courier acting but out of frame | **Intentional.** Shot 6 is the warden's coil; the courier was established in shots 5 and 7 |
| t=13.85: courier cropped (2/3 body points), warden out of frame | **Intentional.** Shot 7 is an extreme close-up of the torch swing; the TNT, the warden and her stance were already established |
| t=21.75, 23.3: courier faces away, cropped | **Intentional.** Shots 11 follows her from behind as she walks to the tower; her face is not needed |
| shot lengths | no shot over its limit after setting `tone` per shot (calm shots 17.5, 24.5, 27.5, 31.0; action shots 12.6-16.2) |
| INFO | 14 shots, average 2.4 s per shot, duration 34 s |

## Frames reviewed by eye (final round)

| # | t | what I looked at | verdict | action taken |
|---|---|---|---|---|
| 1 | 0.25 | opening: tower readable in rain, lit sconces | ok | opening was too dark in round 1: raised ambient/sun, added emissive sconces, removed a lamp post that blocked the tower |
| 2 | 1.8 | title over the tower, TNT in the foreground | ok | the visible TNT is deliberate set-up for the trap |
| 3-4 | 3.25, 4.8 | courier walking, full body, footstep dust | ok | round 1 cut off her feet: camera moved back to z=8.5 |
| 5-6 | 6.25, 6.8 | reaction close-up: wide eyes, open mouth | ok | none |
| 7-9 | 8.25-9.44 | warden low angle, glowing eyes with streak, subtitle | ok | subtitle sits at the bottom of the active picture, not clipped |
| 10-11 | 10.65, 11.72 | standoff two-shot: courier left, TNT centre, warden right | ok | none |
| 12 | 12.85 | warden coil, whip pan just before | ok | none |
| 13 | 13.85 | torch swing close-up (wind-up pose) | ok | none |
| 14 | 14.65 | blast flash | ok | full white for about 0.2 s at the peak; short enough |
| 15 | 16.45 | warden dissolves into sparks | ok | round 1: sparks filled the frame (scale 1.7); reduced to 1.0 |
| 16-17 | 17.75, 19.9 | quiet beat: courier at the crater edge, tower behind | ok | round 1 shot 9 ended on empty grass for 1 s: shortened to 1.3 s |
| 18-19 | 21.75, 23.3 | courier walks to the tower | ok | round 1 she walked over the crater and floated above the hole: path now goes around it |
| 20 | 24.75 | low angle up the tower, courier in the doorway between the sconces | acceptable | her blonde hair sits close to the glowing sconces; a darker door gap would read better |
| 21 | 26.3 | beacon placed: sparks and glow at the top | ok | round 1 the beacon was hidden behind the wall edge and not emissive: pillar raised, glowstone made emissive |
| 22-25 | 27.75-32.8 | dawn pull-back, card, fade | ok | card is faint while it fades in (29.6) but readable at 31.25 |
| 26 | 33.75 | fade to black | ok | none |

Also found and fixed during this review (engine, not story): a transient `ERR_NO_BUFFER_SPACE` turned one texture into the magenta
missing checker for a single render. The engine now retries texture lookups, and `tools/render.py` / `tools/qa.py` refuse to
render (or FAIL) when any block texture is missing, so a film can no longer silently ship with magenta blocks.

## Checklist

- [x] camera inside a block (automatic: none)
- [x] character out of frame (automatic + by eye; all remaining cases are intentional, see above)
- [x] subtitle cut off or overlapping (checked on frames 8-11)
- [x] face turned away in a dialogue shot (the two dialogue shots show the face)
- [x] odd shadows / floating objects (round 1: the courier over the crater; fixed)
- [x] skin holes or missing texture (no magenta in the final frames)
- [x] pacing: any shot too long (automatic, per-shot tone)
- [x] story clear without audio (contact sheet reads: arrive, threat, trap, blast, silence, climb, light)
- [x] energy shape quiet / loud / quiet
- [x] ending reads (beacon lit, card, fade)

## Could not verify

- **Motion.** I reviewed stills, not the playing video. Timing of the swing against the TNT blast (about 0.3 s apart), the feel of the slow-motion
  ramp, and the handheld drift are judged from frames and the numbers only. Watch the MP4.
- **Audio.** The story has no audio; the sources in `research.md` are unverified suggestions (one license page was blocked from fetching).
- **GPU rendering and 60 fps / 1080p full renders** were not run on this film.
