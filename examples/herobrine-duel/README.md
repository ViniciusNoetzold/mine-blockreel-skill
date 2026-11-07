# Eu vs Herobrine (director example)

The whole film is `plan.json` (about 30 lines). Compile, preview, check, render:

```bash
python tools/vanilla.py all                                    # original textures, sounds and font (local cache, once)
python tools/compose.py examples/herobrine-duel/plan.json --out films/herobrine
python tools/render.py films/herobrine/story.json --preset preview --workers 4 --out films/herobrine/preview.mp4
python tools/qa.py films/herobrine/story.json --out films/herobrine/qa
python tools/render.py films/herobrine/story.json --workers 4 --out films/herobrine/film.mp4
```

- **The hero** is a `persona` (stubble, dark hoodie, jeans, white sneakers). With a photo of the user, fill the persona from the photo and
  sample its colours (`python core/persona.py sample ...`), or give `"skin": "my-skin.png"`.
- **Herobrine** is `preset: herobrine`: with the texture cache it is derived from the game's default skin with empty white eyes (kept
  locally in the film folder, never committed); without it, an original CC0 painting. `eyes: glow` adds the emissive eyes and light streak.
- **World**: plains terrain with a flat arena, a shrine at the north edge and ruins to the south-east. Trees never grow on the building
  sites or in the arena; a tree that would cover a camera is not planted.

## QA record (v0.2 build)

`tools/qa.py`: 0 FAIL (no actor or camera inside a block at any 0.05 s step). WARNs are close-ups that crop the body (intended).
Frame review found and fixed, in the compiler or the engine, before this plan shipped:

| Found | Fix |
|---|---|
| reveal smoke hung in front of Herobrine's face during his line | short smoke behind him + a poof |
| the talking gesture raised the sword across the face in close-ups | `talk` gestures with the free hand |
| extreme close-up on the glowing eyes too tight, light streak flooding the frame | wider lens distance, smaller streak |
| close-ups with the lens inside the other fighter at short range | close-up distance limited by the real gap; fencing distance kept at ~2 blocks |
| the get-up low angle showed only sky | side shot |
| the silence beat showed the back of the head | camera placed in front of the face |
| night too dark to read the fight | brighter moonlight in the plan's `styleOverride` |
