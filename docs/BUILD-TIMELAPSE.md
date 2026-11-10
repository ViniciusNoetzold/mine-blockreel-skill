# Building timelapses from a reference

Use the `blockreel-builds` skill in a BlockReel runtime checkout. Send a photograph, sketch, elevation or Minecraft screenshot and describe the desired duration and format. The skill turns the visual brief into a block blueprint. The compiler turns that blueprint into an ordered build with a fixed site, camera coverage, and generated placement sound.

## From image to blocks

| Input | What to preserve |
| --- | --- |
| One frontal view | Outline, floor heights, bay widths, symmetry, placement of windows and doors, and material contrast. Record the assumed depth, rear and roof if they are hidden. |
| Angled view | Use visible side planes and repeated block or window widths to estimate depth. Compare the final image from a similar angle. |
| Multiple elevations or a plan | Use the same scale and origin in every view. Check that each window or corner agrees where two views meet. |
| Mid-build frame | Match the visible stage first. Use another frame or stated assumptions for any unfinished surfaces. |

When precision matters, render the finished structure from the reference angle at a similar apparent scale and compare it alongside the reference. Check silhouette, proportions and openings first. For stairs and tiered roofs, count the visible runs and levels and compare their placement, width, setbacks and contrast with the surrounding trim. Use a side or three-quarter check to inspect tread depth, landings, rail or trim offsets and roof overhang. Mark inferred dimensions or surfaces in the review and record any feature that had to be simplified to the block grid.

## Blueprint format

Use integer coordinates and +Z as the front of the building. The top of the ground is at Y=0, so the first visible construction layer uses Y=0. Each phase owns distinct cells. Leave door and window openings unfilled until the phase that installs them.

```json
{
  "title": "Oak cabin",
  "size": [1280, 720],
  "fps": 24,
  "duration": 12,
  "phases": [
    {"id": "foundation", "ops": [{"fill": ["cobblestone", [-2, 0, -1], [2, 0, 1]]}]},
    {"id": "frame", "ops": [{"fill": ["log", [-2, 1, 1], [-2, 3, 1]]}]},
    {"id": "glazing", "ops": [{"set": ["glass", [0, 2, 1]]}]}
  ]
}
```

The example above illustrates coordinates. Start from the [complete house blueprint](../examples/house-timelapse/) for a full structure. A fill includes both corners. Put phases in playback order and use separate operations where placement order matters. The compiler reports the overall bounds and the times of each phase so you can sample the end of each stage.

Use built-in full blocks, glass blocks, oriented logs, stairs, slabs, doors and torches. Orient stairs toward the direction of ascent and use supported shapes to model visible changes in height and depth. A door reserves the cell immediately above its base. Connection-dependent shapes such as panes and fences and flowing liquids need a different staging approach. Record visible substitutions, such as full glass in place of connected panes.

## Render and verify

From the runtime checkout, run:

```sh
python tools/build_timelapse.py examples/house-timelapse/blueprint.json --out work/house-timelapse
python tools/render.py work/house-timelapse/story.json --preset preview --out work/house-timelapse/preview.mp4
python tools/qa.py work/house-timelapse/story.json --out work/house-timelapse/qa
python tools/render.py work/house-timelapse/story.json --out work/house-timelapse/film.mp4
python tools/check_media.py work/house-timelapse/film.mp4 --duration 12 --size 1280x720 --fps 24 --require-audio
```

Use the preview to check that each stage adds something legible and the finished shot gives viewers time to see the result. Keep the comparison frame and notes on any mismatch with the QA record. Compare the encoded final shot with the approved frame and listen to the timing of the build sounds. For a Reel, render portrait with [the Reels preset](REELS.md) and inspect the frame on a narrow viewport.

For a build with visible characters, keep the blueprint as the source for placements. Add cast and actions to a separate copy of the generated storyboard. Keep the builders outside the active placement area or time their routes around the blocks that appear.

## Assemble a city

Use [the city example](../examples/city-timelapse/) to plan infrastructure and districts as reusable templates. Mark the road network, entrances, open spaces and landmarks on the same coordinate grid. Give each district a recognizable shape and keep a clear path from its streets to the next district.

```json
{
  "title": "Oak Crossing",
  "size": [1280, 720],
  "fps": 24,
  "duration": 14,
  "districts": [
    {"id": "roads", "origin": [0, 0, 0], "blueprint": "roads.json"},
    {"id": "west-homes", "origin": [-20, 0, -16], "blueprint": "homes.json"},
    {"id": "east-homes", "origin": [20, 0, -16], "blueprint": "homes.json", "rotation": 180}
  ]
}
```

Districts build in list order. Paths are relative to the layout. The origin is the translated template origin. Rotation accepts 0, 90, 180 or 270 degrees around Y. A 90-degree turn maps a +Z-facing facade to +X. Use explicit orientation suffixes on shaped blocks in rotated templates, such as `oak_stairs:east`. Rotations also transform directional suffixes and log axes. Intersections must have a single owner, including road crossings shared by two districts.

```sh
python tools/city_timelapse.py examples/city-timelapse/layout.json --out work/city-timelapse
python tools/qa.py work/city-timelapse/story.json --out work/city-timelapse/qa
python tools/render.py work/city-timelapse/story.json --out work/city-timelapse/film.mp4
```

Keep the layout and templates as your source. The tool writes an assembled blueprint, story, build report and audio. Review the site before publishing and use the report to verify that streets, districts and landmarks appear in the intended order. Dense builds can place several blocks between video frames.

One scene supports up to 20,000 occupied cells within a 128 × 128 footprint and construction Y coordinates from 0 through 64. For a larger city, plan sections around a shared street map. Record each section's origin and translate its X/Z coordinates into the local −128 to 128 range. Render the sections and assemble them with the [cinematic workflow](CINEMATIC-WORKFLOW.md). Give each cut a shared road, skyline or landmark so the viewer can follow the construction across locations.

If the overview is too wide to compare a facade, add a close shot to a copy of the generated `story.json` and trim the preceding shot to its start. For a separate vertical composition, add the portrait override at that exact start time. Review the overview and close shot in the final aspect ratio. [Camera and Reels schema](STORYBOARD.md#camera)
