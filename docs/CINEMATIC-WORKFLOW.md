# Cinematic production workflow

Use this route for showcase films, multi-scene stories, or work with exact delivery requirements. It extends the beat compiler and the hand-authored storyboard routes.

## 1. Lock the brief

Record one sentence for the story, the intended audience and language, and the format (runtime, dimensions, frame rate, audio, and any alternate aspect ratios). Identify the hook, escalation, turning point, and payoff. Name the image or sound that should carry each beat. If references matter, record the specific framing, palette, or rhythm decisions they change.

Read [DIRECTOR.md](../DIRECTOR.md) and [TECHNIQUE.md](../TECHNIQUE.md). Check [engine coverage](COVERAGE.md) before planning a shot around a new rig, movement, or effect. For the most technically uncertain shot, render a still and a short moving test before building the rest.

## 2. Budget shots and sound together

Keep one timebase. List each shot with in and out times, subject, story purpose, camera and screen direction, light or palette, and sound cue. Track prop, costume, weather, and location changes across cuts. Assign each scene a distinct visual anchor and keep a recurring element that connects the sequence.

For exact delivery, calculate the frame budget before writing the storyboard. For example, 30 seconds at 30 fps gives 900 frames. The compiler adds a 0.1-second tail to the beat sum. Inspect the emitted `story.json` duration because some beat types determine their own timing. If the tail is intentional, budget it inside the target. Keep cut points on the chosen frame grid.

## 3. Keep one reproducible source

- Use [a beat plan](DIRECTOR-PLAN.md) when it expresses the shot. Read back the generated shot list and story after compiling.
- For precise camera moves, transitions, and cue timings, use [a hand-authored storyboard](STORYBOARD.md) or version a post-compile script that applies those edits. Keep generated files separate from the source that will be edited next.
- For a longer film, establish continuity in a shared shot list and give each sequence its own storyboard when it needs a different world. Use consistent frame rate and dimensions across sequences. Review both sides of each cut, then check the assembled master.
- Keep fetched game assets in the ignored local cache. For public examples, document the license of any third-party asset and the inputs a clean checkout needs to reproduce the film.

## 4. Iterate before the master

Run the [visual QA](QA.md) and inspect the contact sheet and the individual frames at cuts and close-ups. Use a moving preview for acting, camera speed, transitions, and continuity. Review the most expensive effects in a short test at delivery resolution.

```sh
python tools/render.py films/example/story.json --preset preview --out films/example/preview.mp4
python tools/qa.py films/example/story.json --out films/example/qa
```

Listen to the mix with picture. Check that voices are intelligible, effects land on the intended frames, and the score leaves room for important cues. Check the tail of each layer and any intentional silence. If playback or listening is unavailable, record the limitation in the QA log.

## 5. Verify the encoded delivery

```sh
python tools/render.py films/example/story.json --fps 30 --size 1280x720 --workers 2 --out films/example/film.mp4
python tools/check_media.py films/example/film.mp4 --duration 30 --size 1280x720 --fps 30 --require-audio
```

If a parallel render misses the exact frame rate, rerender with `--workers 1` to avoid rounding at segment joins. Review the encoded opening, a key cut or audio cue, and the ending. The media check confirms the picture's frame count and format and, when requested, the presence and timeline coverage of the audio stream. Playback is still needed for the mix and picture quality. Save the QA decisions and deliver the master with a poster and source or reproduction commands when publishing a showcase.
