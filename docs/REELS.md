# Reels in BlockReel

Use the Reels preset for vertical productions. It renders the scene at **1080 × 1920, 9:16, 30 fps** with H.264 picture and stereo AAC at 48 kHz when the storyboard has audio. Titles, subtitles and gameplay HUD use an inset layout. The camera, shadows and motion are evaluated in the portrait viewport.

## Export

From the runtime checkout, prepare the project's audio and run:

```sh
python tools/export.py reels films/my-story/story.json --out films/my-story/reel.mp4
```

The command renders the full storyboard. Use `--start 8 --end 28` to export only that timeline interval with its sound. Use a smaller preview to iterate quickly:

```sh
python tools/render.py films/my-story/story.json --preset reels --scale 0.5 --fps 12 --out films/my-story/reel-preview.mp4
python tools/qa.py films/my-story/story.json --preset reels --scale 0.4 --out films/my-story/qa-reels --no-md
```

Check the final MP4 against your target. This example is for a 30-second Reel with audio:

```sh
python tools/check_media.py films/my-story/reel.mp4 --duration 30 --size 1080x1920 --fps 30 --require-audio
```

## Direct the portrait cut

For a vertical-first production, compose the storyboard's camera shots in the portrait preview. Keep the main action near the middle and use depth to stage more than one subject in the frame. Let quick pans or cuts reveal wide action when a single vertical frame cannot contain it.

To keep both formats in one storyboard, add `reels.camera` patches keyed by the exact `t` of existing camera shots. Fields on each patch override that shot for the portrait render. To replace an orbit or first-person mode, set its field to `null` in the patch and provide the new position and aim.

```json
{
  "reels": {
    "camera": [
      { "t": 0, "fov": 62 },
      { "t": 8, "pos": [3, 2.8, 5], "look": [0, 1.8, 0], "fov": 56 }
    ],
    "safeArea": { "left": 0.08, "right": 0.16, "top": 0.12, "bottom": 0.25 }
  }
}
```

The insets are BlockReel defaults that leave space for player controls. They are fractions of the frame and can be tuned for your placement. Review the opening, close-ups, physical actions near the edges, subtitles and every HUD panel in the intended placement.

[Primeira Noite](../examples/first-night/story.json) has portrait overrides for its full 60-second timeline. Its published Reel is 720 × 1280 at 30 fps. To reproduce that size, use `tools/render.py` with `--preset reels --scale 0.6666666666666666`. The full-resolution export uses the same portrait layout.
