#!/usr/bin/env python3
"""Preview a texture set IN A SCENE: a small showcase world (terrain, a block gallery, a hut, a tree, water and lava, a character for scale)
rendered by the BlockReel engine with YOUR textures applied.

  python tools/pack_preview.py out/pack-src --out pack-preview.png [--style classic-2012] [--hero core/builtin/skins/hero.png]

`textures` is a folder that mirrors assets/minecraft/textures (it must contain block/). Official block names are mapped to the engine's block
names (table below); animated strips show their first frame. Blocks missing from your set fall back to the built-in originals and are listed.
What it shows that a flat sheet cannot: how the textures read at game scale, repetition on large surfaces, how sides and tops fit together,
and how the set looks next to a character and in real lighting.
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from render import open_page, serve  # noqa: E402
import tilecheck  # noqa: E402

# engine block name -> how it is built from the pack's official texture names
MAP = {
    "stone": "stone", "cobblestone": "cobblestone", "dirt": "dirt", "planks": "oak_planks", "sand": "sand", "bricks": "bricks",
    "obsidian": "obsidian", "snow": "snow_block", "wool_white": "white_wool", "gold": "gold_block", "diamond": "diamond_block",
    "grass": {"top": "grass_block_top", "side": "grass_block_side", "bottom": "dirt"},
    "log": {"top": "oak_log_top", "side": "oak_log", "bottom": "oak_log_top"},
    "leaves": {"all": "oak_leaves", "transparent": True},
    "glass": {"all": "glass", "transparent": True},
    "glowstone": {"all": "glowstone", "emissive": True},
    "tnt": {"top": "tnt_top", "side": "tnt_side", "bottom": "tnt_bottom"},
    "water": {"all": "water_still", "transparent": True, "flow": [0, 0.12]},
    "lava": {"all": "lava_still", "emissive": True, "flow": [0, 0.22]},
}

ROW_A = ["stone", "cobblestone", "dirt", "planks", "log", "leaves", "sand", "bricks"]
ROW_B = ["obsidian", "glowstone", "snow", "wool_white", "gold", "diamond", "tnt", "glass"]


def names_of(spec):
    return [spec] if isinstance(spec, str) else [v for k, v in spec.items() if isinstance(v, str)]


def build_project(src, tmp, hero, style):
    src = Path(src)
    blocks = tmp / "blocks"; blocks.mkdir()
    index, missing = {}, []
    for engine_name, spec in MAP.items():
        needed = names_of(spec)
        if not all((src / "block" / f"{n}.png").exists() for n in needed):
            missing.append(engine_name); continue
        for n in needed:  # first frame only for animated strips (the engine tiles 16x16-style squares)
            fr = tilecheck.frames(src / "block" / f"{n}.png")[0]
            fr.save(blocks / f"{n}.png")
        index[engine_name] = spec if isinstance(spec, dict) else {"all": spec}
    (blocks / "index.json").write_text(json.dumps({"blocks": index}), encoding="utf-8")
    shutil.copyfile(hero, tmp / "hero.png")
    world = [{"fill": ["grass", [-11, 0, -9], [11, 0, 7]]}, {"fill": ["dirt", [-11, -3, -9], [11, -1, 7]]},
             {"fill": ["water", [8, 0, -3], [10, 0, 0]]}, {"fill": ["lava", [8, 0, 2], [10, 0, 4]]},
             {"hollow": ["planks", [-9, 1, -8], [-5, 3, -6]]}, {"set": ["glass", [-7, 2, -6]]}, {"set": ["air", [-7, 1, -6]]},
             {"tree": [5, 1, -7], "height": 4}]
    for i, b in enumerate(ROW_A):
        world.append({"set": [b, [-9 + 2 * i, 1, 1]]})
    for i, b in enumerate(ROW_B):
        world.append({"set": [b, [-9 + 2 * i, 1, -2]]})
    story = {
        "fps": 30, "size": [960, 540], "duration": 3, "style": style, "blocks": "blocks",
        "styleOverride": {"letterbox": False, "vignette": False},
        "actors": {"hero": {"skin": "hero.png", "pos": [6.5, 1, 4.5], "face": 200}},
        "world": world,
        "camera": [
            {"t": 0, "dur": 1, "pos": [0, 8.5, 15], "look": [0, 0.8, -1], "fov": 50},
            {"t": 1, "dur": 1, "pos": [-3.5, 2.6, 5.2], "look": [-3.5, 1.2, 0], "fov": 55},
            {"t": 2, "dur": 1, "pos": [4, 2.4, 3.2], "look": [3.2, 1.3, -2], "fov": 55},
        ],
    }
    (tmp / "story.json").write_text(json.dumps(story), encoding="utf-8")
    return story, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("textures"); ap.add_argument("--out", default="pack-preview.png")
    ap.add_argument("--style", default="classic-2012"); ap.add_argument("--hero", default=str(Path(__file__).resolve().parents[1] / "core/builtin/skins/hero.png"))
    a = ap.parse_args(argv)
    if not (Path(a.textures) / "block").is_dir():
        print("error: expected a block/ folder inside", a.textures, file=sys.stderr)
        return 2
    tmp = Path(tempfile.mkdtemp(prefix="packprev_"))
    try:
        story, missing = build_project(a.textures, tmp, a.hero, a.style)
        from playwright.sync_api import sync_playwright
        srv, port = serve(tmp)
        shots = []
        with sync_playwright() as pw:
            browser, page = open_page(pw, port, tmp / "story.json", story, 1.0, False, allow_missing=True)
            for i in range(3):
                page.evaluate(f"renderAt({i + 0.5})"); f = tmp / f"v{i}.png"; page.screenshot(path=str(f)); shots.append(f)
            miss = page.evaluate("window.__missing || []")
            browser.close()
        from PIL import Image
        ims = [Image.open(f).convert("RGB") for f in shots]
        w, h = ims[0].size
        sheet = Image.new("RGB", (w * 2, h * 2), (0, 0, 0))
        sheet.paste(ims[0], (0, 0)); sheet.paste(ims[1], (w, 0)); sheet.paste(ims[2], (0, h)); sheet.paste(ims[0].resize((w, h)).crop((0, 0, w, h)), (w, h))
        # 4th panel: a close crop of the large grass + stone surfaces so repetition is easy to judge
        sheet.paste(ims[0].crop((w // 4, h // 2, w * 3 // 4, h)).resize((w, h), Image.NEAREST), (w, h))
        Path(a.out).parent.mkdir(parents=True, exist_ok=True); sheet.save(a.out)
        print("wrote", a.out)
        if missing:
            print("not in your set (built-in originals used):", ", ".join(missing))
        if miss:
            print("MISSING textures in the scene:", ", ".join(sorted(set(miss))))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
