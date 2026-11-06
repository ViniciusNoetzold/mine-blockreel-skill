# Quality review (step E)

Mandatory before you deliver a film. Two halves: the script finds what a machine can find, **you look at every frame**
for what it cannot.

```bash
python tools/qa.py films/<name>/story.json --out films/<name>/qa --tone dialogue   # tone: calm | dialogue | action
```

It renders at least 8 frames (opening, just after every shot change, inside long shots, extra looks at close-ups, the
ending), writes them to `qa/frames/`, builds `qa/contact-sheet.png`, writes `qa/auto.json`, and creates `qa.md` next to the
story if it does not exist. Exit code 1 if any FAIL.

## Automatic checks

| Severity | Check |
|---|---|
| FAIL | camera inside a block; an actor standing inside a block |
| FAIL | **path check** (every 0.05 s, no rendering): an actor's body (feet, waist, head; centre and 4 corners) or the camera inside a solid block at that moment, breaks/places/blasts included. Catches a character that spawns in a tree or the floor of a `hollow`, cuts a wall corner, or falls through a ledge between two sampled frames. Water and lava do not count |
| WARN | an acting actor is out of frame; the shot's subject is cropped; the subject faces away from the camera in a medium/close shot; camera very close to an actor; subtitle clipped by the frame |
| WARN | a shot is longer than the tone allows (calm 6 s, dialogue 4.5 s, action 2.5 s, +1.5 s if the camera moves); subtitle > 10 words; subtitle shown shorter than reading time; subtitle overlaps a title |
| INFO | shot count and average shot length |

A WARN can be intentional (a character walking away on purpose). Decide, and write the decision in `qa.md`.
The first-person actor is never reported as out of frame.

## What you must look at (open each frame image)

- skin holes, missing or magenta textures, floating blocks, limbs stuck in walls
- shadows: detached, flickering, missing under a character
- pose and acting: is the emotion readable in silhouette? any awkward arm or head angle?
- framing: face visible where the story needs it, headroom, nothing important under the subtitle
- lighting and palette: does each act have its own look? is anything crushed to black or blown out?
- pacing: the energy shape (quiet, loud, quiet); any shot that overstays
- story clarity: could someone understand the film from the contact sheet alone?

## qa.md template

```markdown
# QA: <title>
## Automatic checks (tools/qa.py)
- [WARN] ...  -> decision: fixed / intentional because ...
## Frames reviewed by eye
| # | t | what I looked at | verdict | action taken |
## Checklist (tick only what you actually checked)
- [x] camera inside a block ...
## Found and fixed
## Could not verify (audio, in-game behaviour, etc.)
```
Re-run `tools/qa.py` after fixes. Deliver only when no FAIL remains and every WARN has a recorded decision.
