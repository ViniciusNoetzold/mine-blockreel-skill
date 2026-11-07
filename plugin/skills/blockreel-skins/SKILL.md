---
name: blockreel-skins
description: Design a polished Minecraft player skin (64x64 PNG, classic or slim) from a character idea, with web research, a colour-ramp palette plan, layered painting in code, validation, and a 4-angle turntable preview you must look at and iterate on. Use when the user asks for a skin, a character design for a film, or wants to improve or convert a skin. Part of BlockReel; the main blockreel skill calls this one.
---

# BlockReel skins

Work in the BlockReel folder (`$BLOCKREEL_HOME`, see the `blockreel` skill bootstrap). Put each skin in `work/skins/<name>/`
(gitignored) or `films/<name>/skins/`. **Never copy someone else's skin**; take ideas, not pixels.

## 0. The user sent a skin

Use it exactly as sent: copy it into the film folder, `python core/skin.py validate` it (convert legacy 64x32 into a NEW file),
and reference it in `story.json`. Never repaint a user's skin unless they ask. Only design a new skin when there is none.

## 0b. The user sent a photo of themself

Make *their* skin: look at the photo, fill a persona (`python core/persona.py example`), sample the real colours from flat regions of the
photo (`python core/persona.py sample photo.jpg --region skin=x0,y0,x1,y1 --region hair=... --region top=... --region bottom=... --out colors.json`),
paint (`python core/persona.py paint persona.json skin.png --colors colors.json --preview tt.png`), LOOK at the turntable, adjust once
(hair style, facial hair, glasses, clothing type) and validate. The painter keeps the face rows BlockReel animates (brows 3, eyes 4,
mouth 6) and gives hair and hoods volume on the overlay layer. Presets for other characters: `python core/persona.py preset herobrine|knight|ninja|wizard|miner out.png`.
For a hand-crafted design go on with the steps below (persona output is a good base layer to refine).

## 1. Briefing (at most one short question)

Settle: the **character** (who, role, mood), the **style** and **model**.

| Style | What to aim for |
|---|---|
| clean pixel art | 3-4 tone ramps per material, no noise, 1 px highlights/shadows, readable silhouette |
| cartoon | saturated colours, 1 px darker outline on the face/overlay edges, big simple eyes, strong colour blocking |
| realistic | muted palette, subtle noise (`noise=0.03-0.05`), folds and seams, material variety (cloth, leather, metal) |
| anime | large eyes (use the 2 px iris + highlight pixel), pastel/saturated hair in 3 tones with a highlight strand, simple clothes |

`classic` = 4 px arms (Steve-like), `slim` = 3 px arms. If the user does not say, choose classic and say so; offer the slim variant.

## 2. Research (web), written to `research.md` with links

Search and read: the skin **UV layout and layer rules** ([Minecraft Wiki: Skin](https://minecraft.wiki/w/Skin); the repo's own map is
`docs/SKINS.md` / `references/skin-layout.png`), **pixel-art shading and palette** techniques (hue shifting, ramps, avoiding pillow shading),
and **style references** for the character type. Record: link, what you will use. No copying of third-party skins or art.

## 3. Palette plan

Write the plan before painting: one base colour per material and a **ramp of 3-4 tones** from it (`skin.ramp(base, 4, hue_shift=0.04)`:
shadows slightly cooler, lights slightly warmer). Typical materials: skin, hair, two cloth colours, leather, metal, boots, accent. Keep the
total under ~24 colours; one accent colour is enough.

## 4. Paint in layers (`core/skin.py` `SkinCanvas`)

Base layer first (head, body, arms, legs), **then** the overlay layer (hat = hood/hair volume, jacket = cloak/coat, sleeves, pants).
Useful helpers: `shaded_box(part, ramp)` (lit from top/front), `rect`, `px`, `line`, `edge_light`, `clear`, and `mirror_limbs()` to
paint the right side and copy it mirrored to the left. Face-relative coordinates: you never compute atlas positions by hand.
Face rule for BlockReel films: keep the eyes on **row 4** (and brows on row 3) of the front face, mouth on **row 6**, because
the engine's face states (`blink`, `wide`, `glow`, lip-sync) repaint those rows and sample the skin colour from the cheeks (row 5).
Start from `examples/skin-demo/paint_skin.py` and change the palette plan and the per-part blocks.

## 5. Validate

`python core/skin.py validate out.png`: size, `model` (classic/slim) and **0 transparent base pixels** (the base layer must be
fully opaque in Java). `python core/skin.py unwrap out.png parts/` if you need every face as a separate image.

## 6. Preview and iterate (MANDATORY, at least 2 rounds)

```bash
python tools/turntable.py skin.png --out tt.png [--pose idle|wave|stance] [--model slim] [--eyes wide --mouth smile]
```
Open `tt.png` and look at all four views. Check: silhouette, face readable at game scale, hood/hair overlay not floating, seams and
mirrored limbs, back and sides not left blank, shading direction consistent, nothing muddy. Write down what is wrong, fix, render again.
Keep each round's image (see `examples/skin-demo/iterations/`). Do not stop after one render.

## 7. Export

Final PNG (and the other model if asked: repaint with `slim=True`/`False`; there is no automatic classic<->slim conversion).
Name files `<character>.png` and `<character>-slim.png`. Check both with `validate`.

## 8. Installing in the game (tell the user; you have not tested it)

- **Java Edition:** upload the PNG (64x64, or legacy 64x32) on the minecraft.net profile page or in the Launcher's Skins tab and pick
  3 px or 4 px arms. Only accounts that own the game can change skins; offline-mode players cannot use a custom skin without mods.
  Source read: [Minecraft Wiki: Skin](https://minecraft.wiki/w/Skin). Mojang's own help page could not be loaded when this was written,
  so check [help.minecraft.net](https://help.minecraft.net) for the current menu names.
- **Bedrock Edition:** a different process (and the format supports larger templates, e.g. 128x128, per the wiki). Do not give Java steps for Bedrock;
  point the user to Mojang's current Bedrock help page.
- Inside a BlockReel film nothing needs installing: reference the PNG in `story.json`.

## Rules

- Never claim a skin was tested in the game. Say "validated and previewed in the BlockReel engine".
- Never ship or commit game skins or someone else's skin. The repo's demo skin is original (CC0).
- If the user gives a screenshot of a 3D skin render, it cannot become a texture (`docs/SKINS.md`); build a lookalike instead.
