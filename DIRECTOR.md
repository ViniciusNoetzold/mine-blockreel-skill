# DIRECTOR.md — how to direct a blocky animation

These are craft conventions of the classic fan-animation era (blocky characters, big expressive
motion, chat-style dialogue). They are general guidance, not a copy of any specific video.

## 1. The hook (first 3 seconds)

Open on motion or a question, not a logo. A title card is allowed, but over a moving shot
(the demo does this). Good openers: a character sprinting toward camera, a TNT block in
foreground, a creeper-sized silence, a door slamming.

## 2. Structure for 30–90 seconds

| Beat | Share | Job |
|---|---|---|
| Setup | 15% | who, where, what they want |
| Escalation | 45% | complication, each step bigger or funnier |
| Turn | 20% | the surprise / twist / fail |
| Payoff + button | 20% | resolve, then a 1-second visual joke after the resolution |

One idea per film. If you can't say the premise in one sentence, cut.

## 3. Acting with a rigid body

Characters are boxes, but faces swap (eyes, mouth, wounds) and the mouth follows subtitles. Acting comes from:
- **Silhouette**: arms out, arms up, body tilt. Every emotion needs a pose readable in black.
- **Clips** (`idle`, `walk`, `run`, `wave`, `talk`, `mine`, `punch`, `dance`, `sit`, `look`, `scared`, `jump`, `die`, `spin`).
- **Timing**: hold a pose 0.4–0.8 s before reacting. Reaction beats are the comedy.
- **Facing and looking**: characters turn toward what they care about (`"face": "otherActor"`) and their head follows a target (`"lookAt"`, also `"camera"`).
- **Faces**: use `faces` for wide eyes on a scare, `angry` before a fight, `glow` for a villain, `hurt` after a hit. Change the face *before* the body reacts.
- **Talking** = `talk` clip (head bob) + a subtitle line in chat format. Max ~10 words per line, ~2 s on screen.

Use short emotes for different jobs: a nod answers a question, a shrug reveals uncertainty, a flinch shows danger, and a sigh of relief pays off tension. Leave time to settle after the strongest pose. Keep the camera on the reaction long enough to read the eyes and silhouette. The variety of social gestures in [Not Enough Emotes](https://www.curseforge.com/minecraft-bedrock/addons/not-enough-emotes) is a reference for the kind of performance choices a director can offer. BlockReel's motion clips are authored in code.

## 4. Camera

- Cut on action. Hard cuts by default. Dialogue/calm: 2–4 s per shot. **Action: 1–2 s per shot** (see section 10).
  A held shot longer than 5 s needs movement, unless it is a deliberate calm beat (section 10).
- Shot ladder: **establishing** (wide, slow dolly) → **medium** (two characters) → **close-up** (face, `fov` 40–48) → **reaction**.
- Orbit (`orbit`) for hero moments; `shake` 0.03–0.08 for impacts; `handheld` 0.5–1 for action; `first` for a character's point of view.
- Put the camera **in front of the face** you want to read. The engine's offsets are world-space.
- Low camera = powerful or scary; high camera = small or lost.
- Keep the horizon level in calm scenes; tilt it (`dutch`) in action scenes on purpose.
- **Scale reveal:** start with a foreground object filling the frame, pull back to show the crowd/structure. Use it once per film.
- **Handheld shake** (`shake` 0.02–0.05) on every action shot, not only on impacts; static camera only for calm beats.

## 5. Sound and music (you provide the files)

The renderer mixes one `music` track. Use royalty-free or original audio you have the right to use.
Plan beats on the cut points: a stinger on the turn, silence for one beat before the payoff.
Do not use the game's own sounds or soundtrack unless you own the right to publish them.

## 6. Text

Subtitles use the in-game chat format (`<Name> text`). Titles: 1–3 words, 1.5–2.2 s.
No paragraphs on screen.

## 7. Shot list template (fill before writing JSON)

```
#  t      dur  shot            camera            action / clip                  line
1  0.0    3.5  establishing    dolly in, wide    hero walk to the house         —
2  3.5    2.7  two-shot        orbit             both wave                      —
3  6.2    2.2  close-up hero   fov 45            talk                           "…"
```

## 8. Style choice

- `classic-2012`: bright sky, hard shadows, clouds. Comedy, adventure.
- `golden-hour`: warm low sun, letterbox, vignette, narrow fov. Emotional, epic.
- `nightfall`: dark blue, fog, letterbox. Horror, suspense.
- `void-arena`: violet void, cool key light, letterbox. Duels and finales.
- `ember-haze`: warm red-magenta smoke haze. Aftermath and epilogues.

## 9. Pitfalls

- Two characters talking in the same shot with no framing change → cut to singles.
- Camera inside a block (clips through the wall) → check stills.
- A character inside a block: `hollow` builds a floor and a roof too, so clear the inside (`fill` air) before standing anyone in it;
  walk through door gaps along the gap's centre line, never diagonally past a corner. `tools/qa.py` FAILs every such interval.
- Subtitles that overlap titles → separate by time.
- Everything moving at once → give the eye one thing to follow.

## 10. Energy shape, act palettes and action (from the reference analysis)

Source: `references/video-analysis/673z48KEXy0.md`. Principles only, no copied scenes.

- **Energy is a shape, not a constant.** Quiet start → dense middle → one deliberate silence → quiet tail.
  A loud middle only works if the opening and ending are quiet.
- **Open with motion + a scale change in the first 3 s** (foreground object fills frame, then wide).
- **One palette per location, and change palette at an act break** (cool navy → violet → warm red is the
  reference's order). The color shift tells the viewer the chapter changed. One `style` per act.
- **Light the thing to look at:** one warm point of light on cold stone, glowing eyes in dark frames; turn on `post.bloom`.
- **Action cutting:** 1–2 s per shot, extreme close-ups on faces and weapons alternating with a wide. Cover a cut
  with a `flash` or a `whip` transition. Slow motion on the key hit with a `timeRemap` window.
- **Impact:** the `swing`/`hit` clips already wind up, strike, overshoot and settle; add `shake` and a `break`/`explosion` fx on the hit frame.
- **Anticipation, overshoot, follow-through** on every attack: crouch → strike → overshoot → settle.
- **Stakes escalate in scale:** character → crowd → giant creature. Each step should look bigger than the last.
- **Hold the emotional beat.** After the peak, stop the action: white-out, silence, a character looking off-screen.
- **End quiet:** a locked or slowly drifting shot, particles only, then a plain text card (one sentence, centered).
- **Letterbox 2.37:1** suits epic films. Keep text inside the active picture.

Shot-list template for an action scene (`dutch`, `timeRemap`, `flash` and `whip` are engine features):

```
#  dur  shot                     camera                      action                      transition
1  2.0  wide, low               shake 0.04                  both charge                 whip pan
2  1.2  extreme close-up face   fov 35, slow zoom           eyes narrow                 hard cut
3  1.0  medium hit              dutch 8                       strike (impact frame)       flash
4  1.5  wide recoil             timeRemap 0.6             knock-back                  hard cut
```
