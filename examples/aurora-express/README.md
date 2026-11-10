# Aurora Express

A courier carries a glowstone across a frozen rail bridge. Lightning tears out part of the walkway, and the last signal goes live just before dawn.

[Watch the 30-second film](showcase.mp4) · [Shot list](shotlist.md) · [Quality review](qa.md)

The goal was a story that reads without dialogue. The glowstone connects the opening, the crossing and the payoff. Cold light and snowfall establish the canyon, a quiet reaction separates the run from the signal, and warm dawn reveals the full crossing in the last shot.

`story.json` is the hand-directed master. It uses BlockReel's built-in skin and textures, timed block changes, actor-relative tracking shots, particles, and lighting keyframes. `make_audio.py` synthesizes a score, wind, footsteps, rail resonance, impact, landing and the signal's ascending chime. The project uses only assets provided by BlockReel and generated audio.

## Reproduce

After the [repository setup](../../README.md), run from the repository root.

```sh
python examples/aurora-express/make_audio.py
python tools/qa.py examples/aurora-express/story.json --out work/aurora-qa --no-md
python tools/render.py examples/aurora-express/story.json --workers 2 --crf 20 --out work/aurora-express.mp4
python tools/check_media.py work/aurora-express.mp4 --duration 30 --size 1280x720 --fps 24 --require-audio
ffmpeg -ss 10.875 -i work/aurora-express.mp4 -frames:v 1 -vf crop=1280:588:0:66 -q:v 2 work/aurora-poster.jpg
```

`--gpu` can speed up the render on a compatible host. The audio script writes its WAVs to the ignored `generated/` folder beside the story.
