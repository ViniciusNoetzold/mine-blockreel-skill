#!/usr/bin/env python3
"""Render a skin with the BlockReel engine from 4 angles (front, back, 3/4 left, 3/4 right) into ONE image.

  python tools/turntable.py skin.png --out turntable.png
  python tools/turntable.py skin.png --out tt.png --pose wave --bg "#2b2f3a" --model slim

It uses the same renderer as the films, so what you see here (skin layers, arm width, shading, face) is what the video will show.
Look at the picture before you call a skin finished: seams, a missing overlay, a mirrored side and a wrong model are obvious in it.
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import open_page, serve  # noqa: E402

VIEWS = [("front", 0), ("3/4 left", 40), ("back", 180), ("3/4 right", -40)]


def make_story(pose, bg, model, size, face):
    return {
        "fps": 30, "size": list(size), "duration": 5, "style": "classic-2012",
        "styleOverride": {"sky": {"top": bg, "bottom": bg}, "clouds": False, "shadows": False, "fog": None, "vignette": False, "letterbox": False,
                          "ambient": {"color": "#ffffff", "intensity": 0.75}, "sun": {"color": "#ffffff", "intensity": 0.95, "dir": [0.5, 1.0, 0.8]}},
        "actors": {"skin": {"skin": "skin.png", "model": model, "pos": [0, 0, 0], "face": 0, "blink": False}},
        "world": [{"fill": ["wool_white", [-3, -1, -3], [3, -1, 3]]}] if False else [],
        "timeline": [{"t": 0, "actor": "skin", "do": pose, "dur": 5, "hold": True}],
        "faces": [{"t": 0, "actor": "skin", **face}] if face else [],
        "camera": [{"t": i, "dur": 1, "orbit": {"center": [0, 1.0, 0], "radius": 5.4, "height": 0.1, "from": ang, "to": ang}, "fov": 28} for i, (_, ang) in enumerate(VIEWS)],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skin"); ap.add_argument("--out", default="turntable.png")
    ap.add_argument("--pose", default="idle", help="any clip from docs/STORYBOARD.md (idle, wave, stance, walk...)")
    ap.add_argument("--model", default="auto", choices=["auto", "classic", "slim"])
    ap.add_argument("--bg", default="#8e96a3", help="background colour")
    ap.add_argument("--size", default="360x520", help="size of ONE view, WxH")
    ap.add_argument("--eyes", help="face state for the preview (open, wide, angry, glow...)")
    ap.add_argument("--mouth", help="mouth state (closed, smile, shout...)")
    a = ap.parse_args(argv)

    W, H = (int(x) for x in a.size.lower().split("x"))
    face = {k: v for k, v in (("eyes", a.eyes), ("mouth", a.mouth)) if v}
    tmp = Path(tempfile.mkdtemp(prefix="turntable_"))
    try:
        shutil.copyfile(a.skin, tmp / "skin.png")
        story = make_story(a.pose, a.bg, a.model, (W, H), face)
        # the engine looks for a floor to put shadows on; there is none here by design (flat studio background)
        (tmp / "story.json").write_text(json.dumps(story), encoding="utf-8")
        from playwright.sync_api import sync_playwright
        srv, port = serve(tmp)
        shots = []
        with sync_playwright() as pw:
            browser, page = open_page(pw, port, tmp / "story.json", story, 1.0, False)
            for i in range(len(VIEWS)):
                page.evaluate(f"renderAt({i + 0.5})")
                f = tmp / f"v{i}.png"; page.screenshot(path=str(f)); shots.append(f)
            browser.close()
        from PIL import Image, ImageDraw
        ims = [Image.open(f).convert("RGB") for f in shots]
        sheet = Image.new("RGB", (W * len(ims), H), (0, 0, 0))
        for i, im in enumerate(ims):
            d = ImageDraw.Draw(im); d.rectangle([0, 0, 80, 14], fill=(0, 0, 0)); d.text((4, 2), VIEWS[i][0], fill=(255, 255, 0))
            sheet.paste(im, (i * W, 0))
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        sheet.save(a.out)
        print("wrote", a.out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
