---
name: blockreel-builds
description: Recreate a house, facade, large build, or city from reference images or a brief as an editable Minecraft-style blueprint and render its block-by-block construction as a timelapse. Use for staged builds, neighborhood construction, and portrait or landscape reveals.
---

# BlockReel Builds

Use the BlockReel runtime checkout and read `docs/BUILD-TIMELAPSE.md`. The agent reads the supplied images and authors the blueprint. The compiler validates and animates those blocks. Use the worked example in `examples/house-timelapse/` to check a new setup.

## Match the reference

1. Identify the view and list the visual anchors that define the building: silhouette, width-to-height ratio, number of levels, post spacing, door and window positions, materials, roof direction and overhang. If the reference is mid-build, separate the visible construction from the completed design.
2. Map the visible facade to a block grid with its front facing +Z. Count visible modules in a Minecraft screenshot. For a photograph, choose a scale that preserves the relative proportions and opening spacing. Note the chosen scale.
3. Mark each surface or dimension as observed, supplied, or inferred. With one facade image, estimate hidden depth, rear elevation and roof slope as needed and record the assumptions. Use side or roof views when provided. Ask for another view when hidden geometry is essential to the requested match.
4. Build a unique set of final block cells and divide it into stages that make sense visually: base, framing, walls, glazing and roof. Preserve the positions of the openings. Use actual stair and slab shapes where the engine supports them and document any visible approximation.

## Compile and review

```sh
python tools/build_timelapse.py films/my-build/blueprint.json --out films/my-build
python tools/render.py films/my-build/story.json --preset preview --out films/my-build/preview.mp4
python tools/qa.py films/my-build/story.json --out films/my-build/qa
```

Compare the finished frame with the reference from the closest available angle. Confirm the massing, spacing and roof silhouette before judging color. Review the start, the end of each construction stage and the final hold. Look for gaps, stray blocks, roof direction, an obstructed camera, and placements that the viewer cannot read. Review the moving preview with sound and change the blueprint if the facade or timing misses the brief.

Render and verify the master at the requested format. For portrait delivery, use the Reels workflow in `docs/REELS.md` and check the full roof and base in that frame. Deliver the video, editable blueprint, generated storyboard, build report and a short QA note with the assumptions and checked frames. A render can reproduce the modeled building. A single photo gives direct evidence only for the surfaces it shows.

## Large builds and cities

Use `tools/city_timelapse.py` with a layout and district blueprints. Establish roads, terrain levels and open space on one grid before placing buildings. Keep a shared scale and reserve room around each silhouette. Reuse templates only where the reference or brief calls for repetition. Check the combined layout for overlaps, connecting streets and distinctive landmarks.

Review the whole city and the densest district at delivery resolution before rendering the master. If the overview makes a district too small to read, add a closer shot. Split builds that exceed the per-scene limits in the guide into linked sections. Keep a shared map and consistent light, palette and screen direction across those shots.
