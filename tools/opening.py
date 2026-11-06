#!/usr/bin/env python3
"""Build a YouTube-style channel opening (5-9 s): the channel name built from blocks that pop in a wave, a blast, an orbit
around the logo, a locked logo hold. Writes a ready story.json (plus its sound files) that you then render as usual.

  python tools/opening.py "MEU CANAL" --out films/meu-canal-intro [--block gold] [--skin path/to/skin.png] [--duration 8]
  python tools/render.py films/meu-canal-intro/story.json --out films/meu-canal-intro/opening.mp4

Sound: original game effects from the local cache (python tools/vanilla.py sounds): a pop per letter column, an explosion on
the hit, a level-up chime on the logo; plus an original score from tools/score.py. Without the cache it writes the story
with music only and says so. Genre rules: docs/GENRES.md ("opening").
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SND = ROOT / "work" / "vanilla" / "sounds"


def text_pixels(text, height=7):
    """Rasterise the text into a block grid (1 = block). Uses Pillow's built-in font, thresholded to whole pixels."""
    font = ImageFont.load_default(size=height + 3)
    w = int(font.getlength(text)) + 4
    im = Image.new("L", (w, height + 6), 0)
    ImageDraw.Draw(im).text((2, 0), text, fill=255, font=font)
    bbox = im.point(lambda v: 255 if v > 70 else 0).getbbox()
    im = im.crop(bbox).point(lambda v: 1 if v > 70 else 0)
    return [[im.getpixel((x, y)) for x in range(im.width)] for y in range(im.height)]


def build(name, out, block="gold", skin=None, duration=8.0):
    if duration < 6.5:
        raise SystemExit("an opening needs at least 6.5 s (pop-in, hit, orbit, logo hold)")
    out = Path(out); (out / "assets" / "audio").mkdir(parents=True, exist_ok=True)
    grid = text_pixels(name.upper())
    H, W = len(grid), len(grid[0])
    x0 = -W // 2
    world = [{"fill": ["grass", [x0 - 8, 0, -10], [x0 + W + 8, 0, 8]]}, {"fill": ["dirt", [x0 - 8, -3, -10], [x0 + W + 8, -1, 8]]},
             {"set": ["tnt", [0, 1, -5]]}]
    t_start, t_end = 0.45, 3.3
    changes, cols = [], {}
    for y in range(H):
        for x in range(W):
            if grid[y][x]:
                t = round(t_start + (t_end - t_start) * x / max(1, W - 1) + 0.04 * (H - 1 - y), 3)
                changes.append({"t": t, "place": [x0 + x, 1 + (H - 1 - y), 0], "block": block})
                cols.setdefault(x, t)
    hit = 3.6
    changes.append({"t": hit - 0.9, "tnt": [0, 1, -5], "fuse": 0.9, "radius": 2.2})
    cx, cy = 0.0, 1 + H / 2
    if skin is None:
        vs = ROOT / "work" / "vanilla" / "entity" / "steve.png"
        skin = str(vs) if vs.exists() else str(ROOT / "core" / "builtin" / "skins" / "hero.png")
    shutil.copyfile(skin, out / "host.png")
    host_x = x0 + W + 1.5
    story = {
        "title": f"{name} opening", "fps": 30, "size": [1280, 720], "duration": duration, "seed": 7,
        "style": "classic-2012", "styleOverride": {"letterbox": False, "vignette": False, "fog": [40, 120]},
        "post": {"bloom": {"strength": 0.45, "radius": 0.5, "threshold": 0.85}, "grade": {"contrast": 1.06, "saturation": 1.12}, "grain": 0.02},
        "actors": {"host": {"skin": "host.png", "pos": [host_x, 1, 2.5], "face": -20}},
        "world": world, "changes": changes,
        "fx": [{"t": hit, "kind": "confetti", "pos": [cx, cy + 1.5, 0.5], "scale": 1.4, "seed": 3},
               {"t": hit, "kind": "sparks", "pos": [cx, cy, 0.6], "scale": 1.2, "seed": 4},
               {"t": 1.0, "kind": "dust", "pos": [x0, 1.1, 0.5], "scale": 0.8, "seed": 5}],
        "timeline": [{"t": 0, "actor": "host", "do": "idle", "dur": hit, "lookAt": [cx, cy, 0]},
                     {"t": hit + 0.2, "actor": "host", "do": "wave", "dur": 1.6, "lookAt": "camera"},
                     {"t": hit + 1.8, "actor": "host", "do": "idle", "dur": duration, "lookAt": "camera"}],
        "faces": [{"t": hit, "actor": "host", "eyes": "wide", "mouth": "smile", "dur": 0.6}, {"t": hit + 0.6, "actor": "host", "mouth": "smile"}],
        "camera": [
            {"t": 0, "dur": 1.1, "pos": [x0 - 0.5, 1.6, 2.2], "to": [x0 + 1.5, 1.9, 2.6], "look": [x0 + 1.5, 1.4, 0], "fov": 50, "handheld": 0.5},
            {"t": 1.1, "dur": 2.5, "pos": [x0 + 2, 2.5, 4], "to": [cx, cy + 1.5, W * 0.62 + 4], "look": [x0 + 3, cy, 0], "lookTo": [cx, cy, 0],
             "fov": 55, "ease": "smooth", "handheld": 0.4},
            {"t": hit, "dur": 2.4, "orbit": {"center": [cx, cy, 0], "radius": W * 0.6 + 3, "height": 2.5, "from": -30, "to": 25}, "shake": 0.03},
            {"t": hit + 2.4, "dur": duration - hit - 2.4, "pos": [cx, cy + 0.8, W * 0.62 + 3], "look": [cx, cy, 0], "fov": 52},
        ],
        "transitions": [{"t": hit - 0.12, "type": "whip", "dur": 0.24, "dir": "right", "strength": 40},
                        {"t": hit, "type": "flash", "dur": 0.35, "peak": 0.8},
                        {"t": duration - 0.6, "type": "fade", "dur": 0.6, "dir": "out", "color": "#000"}],
        "audio": {"music": {"file": "assets/audio/score.wav", "volume": 0.5, "fadeIn": 0.2, "fadeOut": 0.6}, "sfx": []},
    }
    subprocess.run([sys.executable, str(ROOT / "tools" / "score.py"), "--out", str(out / "assets" / "audio" / "score.wav"),
                    "--duration", str(duration), "--bpm", "120", "--key", "C",
                    "--sections", f"build:0:{hit},battle:{hit}:{hit + 2.4},dawn:{hit + 2.4}:{duration}"], check=True, capture_output=True)
    have = SND.exists()
    if have:
        for src, dst in (("random/pop", "pop"), ("random/explode2", "boom"), ("random/levelup", "logo")):
            shutil.copyfile(SND / f"{src}.wav", out / "assets" / "audio" / f"{dst}.wav")
        sfx = story["audio"]["sfx"]
        for i, (x, t) in enumerate(sorted(cols.items())):
            if i % 2 == 0:
                sfx.append({"file": "assets/audio/pop.wav", "t": t, "volume": 0.5})
        sfx += [{"file": "assets/audio/boom.wav", "t": hit, "volume": 0.9}, {"file": "assets/audio/logo.wav", "t": hit + 2.4, "volume": 0.7}]
    (out / "story.json").write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out / 'story.json'}: '{name}' as {W}x{H} {block} blocks, {len(changes) - 1} placements, hit at {hit} s"
          + ("" if have else "; no game sounds cached (python tools/vanilla.py sounds), music only"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name"); ap.add_argument("--out", required=True); ap.add_argument("--block", default="gold")
    ap.add_argument("--skin"); ap.add_argument("--duration", type=float, default=8.0)
    a = ap.parse_args(argv)
    build(a.name, a.out, a.block, a.skin, a.duration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
