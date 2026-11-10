# Cinematic production workflow

Use this route for a finished film with a cinematic quality target, a showcase reference, several distinct scenes, or exact delivery requirements. Use a beat plan where it can express the direction and write or refine the storyboard directly where the film needs more control.

## 1. Lock the brief

Record one sentence for the story, the intended audience and language, and the format (runtime, dimensions, frame rate, audio, and any alternate aspect ratios). Identify the hook, escalation, turning point, and payoff. Name the image or sound that should carry each beat. If references matter, record the specific framing, palette, or rhythm decisions they change.

When the brief calls for a visual match, name the details that make the subject recognizable and schedule a still from the reference viewpoint. Record what the reference shows and what you inferred about the side or back. Use the [building workflow](BUILD-TIMELAPSE.md) to review a reconstructed facade and its depth.

Read [DIRECTOR.md](../DIRECTOR.md) and [TECHNIQUE.md](../TECHNIQUE.md). Check [engine coverage](COVERAGE.md) before planning a shot around a new rig, movement, or effect. For the most technically uncertain shot, render a still and a short moving test before building the rest.

## 2. Budget shots and sound together

Keep one timebase. List each shot with in and out times, subject, story purpose, camera and screen direction, light or palette, and sound cue. Track prop, costume, weather, and location changes across cuts. Assign each scene a distinct visual anchor and keep a recurring element that connects the sequence.

In a sustained point of view, use the subject, blocking, light, distance, or sound to make story changes perceptible. For a suspenseful corridor, the next beat could redirect the viewer toward an object near the camera or change what the light reveals. In the moving preview, check that each return to a similar composition adds information or deliberately builds tension.

For a showcase or recap of your own work, log the source and in/out points of the earlier clips requested in the brief. Give each clip a job in the edit, such as showing a build stage, a character reaction or a finished camera move. Let those shots carry the demonstration. Keep the opening title and closing call to action short enough to read on the intended screen while the film moves.

For exact delivery, calculate the frame budget before writing the storyboard. For example, 30 seconds at 30 fps gives 900 frames. The compiler adds a 0.1-second tail to the beat sum. Inspect the emitted `story.json` duration because some beat types determine their own timing. If the tail is intentional, budget it inside the target. Keep cut points on the chosen frame grid.

## 3. Keep one reproducible source

- Use [a beat plan](DIRECTOR-PLAN.md) when it expresses the shot. Read back the generated shot list and story after compiling.
- For precise camera moves, transitions, and cue timings, use [a hand-authored storyboard](STORYBOARD.md) or version a post-compile script that applies those edits. Keep generated files separate from the source that will be edited next.
- For a longer film, establish continuity in a shared shot list and give each sequence its own storyboard when it needs a different world. Use consistent frame rate and dimensions across sequences. Review both sides of each cut, then check the assembled master.
- Record the assets the film actually uses. Verify that project-relative textures, skins, item sprites, and audio inputs are present. Confirm the rig, font, and sound sources if the production relies on optional caches or voices. For a shared project, keep permitted inputs beside the storyboard or document how to regenerate them. Resolve cache-dependent paths on the target machine. Sample a planned effect with picture before rendering the full film.
- When the look calls for detailed 64 × 64 block or item textures, author the detail at that size. Give materials their own surface patterns and edge treatment. Inspect the loaded tiles under the shot lighting at near and far distances for tiling seams, shimmer, and detail that disappears in the delivery frame. [Texture authoring workflow](../plugin/skills/blockreel-textures/SKILL.md)
- Keep fetched game assets in the ignored local cache. For public examples, document the license of any third-party asset and the inputs a clean checkout needs to reproduce the film.

## 4. Iterate before the master

Run the [visual QA](QA.md) and inspect the contact sheet and the individual frames at cuts and close-ups. Use a moving preview for acting, camera speed, transitions, and continuity. Probe the densest scene and a lighting or material change at delivery resolution using the intended backend and worker count. Compare the probe with software output if hardware rendering changes the look or reports a WebGL failure.

```sh
python tools/render.py films/example/story.json --preset preview --out films/example/preview.mp4
python tools/qa.py films/example/story.json --out films/example/qa
```

For first-person action or a held prop, sample the ready pose, the greatest swing or turn, and the recovery. Include intermediate poses that bring the wrist near the face, such as `inspect` or `guard`. Check clearance from the actor's head and body and whether the prop blocks the intended view. Compare the last frame of the outgoing shot and the first frame of the incoming shot for hand, prop, position and direction continuity. Watch those actions in motion to catch overlaps between samples.

Audition the score and effects against the moving preview before the master. Listen through scene changes to check that music follows the intended energy, voices are intelligible and effects land on the action. Lower or re-time music that masks a cue. Check intentional silence and the end of each layer. If playback or listening is unavailable, record the limitation in the QA log.

The automatic QA report flags issues such as clipping and pacing thresholds. Use the contact sheet to judge framing, readability, lighting and visible assets, then use playback to judge acting, rhythm and synchronization. When the preview misses the brief, fix the affected shots and check them again before rendering the master.

## 5. Verify the encoded delivery

```sh
python tools/render.py films/example/story.json --fps 30 --size 1280x720 --workers 2 --out films/example/film.mp4
python tools/check_media.py films/example/film.mp4 --duration 30 --size 1280x720 --fps 30 --require-audio
```

If a parallel render misses the exact frame rate, rerender with `--workers 1` to avoid rounding at segment joins. A WebGL shader or context failure stops the render. Run a software probe of the affected scene, then rerender it with the default backend. For a partial repair, cut on the frame grid, rejoin the picture and the original audio, and run the media check again.

Check that the full encoded file decodes and inspect frames from the opening, the most demanding set, transitions in lighting or geometry, any repaired interval, and the ending. Compare those frames against the approved QA stills. The media check confirms duration, dimensions, frame rate, and audio coverage. Record the separate picture and sound review in `qa.md` and identify any checks that could not be performed. Label an export that still needs that review as an unreviewed render.

For a browser-playable showcase, publish a poster and a page with native video controls. Make the README's primary link open that player. Put the short description and project or install link beside the player so they stay visible without taking up screen time in the film. After deployment, load the public page, start playback with sound, seek into the film and verify the advertised duration. Save the QA decisions alongside the project sources and reproduction commands.

## Compare with a known render

If a new setup gives a surprising result, render the [two-second torch scene from *Primeira Noite* with the original mix](../examples/first-night/README.md#teste-rápido-com-a-cena-da-tocha) from a clean checkout. Compare the same moment with the gallery. A close match gives you a reference for reviewing the new film's cameras, lighting and cues. If the reference also differs, check the runtime revision, render command and asset sources first.
