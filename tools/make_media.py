#!/usr/bin/env python3
"""Build the README media (banner, feature galleries, film stills, skin and texture boards) from real renders.

  python tools/make_media.py --film out/last-torch.mp4              # everything into docs/media/
  python tools/make_media.py --only gallery,skin --film out/last-torch.mp4

Everything is produced by the BlockReel engine and tools; nothing is a mock-up. Needs ffmpeg and Chromium (same as the renderer).
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "media"

GALLERIES = {   # example -> [(time, caption)]
    "animation": ("animation-lab", [(0.8, "stance"), (1.22, "swing: wind-up"), (1.34, "swing: strike"), (1.42, "swing: overshoot"), (3.35, "lunge"), (3.6, "scared (blend)")]),
    "faces": ("faces-lab", [(0.5, "glowing eyes"), (2.4, "wide eyes + shout"), (4.5, "angry + frown"), (6.0, "smile + wounds + lip-sync"), (7.5, "look-at + open mouth"), (9.0, "dead eyes")]),
    "particles": ("particles-lab", [(1.4, "block break"), (3.12, "explosion flash"), (3.5, "fire + debris"), (4.5, "smoke"), (6.7, "sparks"), (9.6, "confetti")]),
    "camera": ("camera-lab", [(1.0, "handheld + 2.37:1"), (1.95, "whip pan"), (2.5, "dutch + zoom"), (4.05, "flash"), (7.0, "first person"), (8.9, "orbit + slow motion")]),
    "post": ("post-lab", [(0.5, "dusk + rain + rack focus"), (4.5, "focus pulled"), (8.5, "night + bloom")]),
    "world": ("world-lab", [(1.2, "crack stages"), (3.0, "block placed"), (5.5, "TNT fuse"), (6.8, "explosion"), (8.6, "door + chest"), (9.5, "lava + water")]),
    "mobs": ("mobs-lab", [(1.5, "four rigs"), (2.8, "creeper-style swell"), (4.4, "blast + crater")]),
}


def font(size, bold=True):
    for f in (["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"] if bold else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]) + ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def caption(im, text, size=18):
    d = ImageDraw.Draw(im, "RGBA"); f = font(size)
    w = d.textlength(text, font=f) + 16
    d.rectangle([8, im.height - size - 18, 8 + w, im.height - 8], fill=(0, 0, 0, 170))
    d.text((16, im.height - size - 14), text, font=f, fill=(255, 255, 255, 255))
    return im


def grid(tiles, cols, tw=480, th=270, gap=6, bg=(14, 14, 18)):
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), bg)
    for i, t in enumerate(tiles):
        sheet.paste(t.resize((tw, th)), (gap + (i % cols) * (tw + gap), gap + (i // cols) * (th + gap)))
    return sheet


def render_stills(example, times, scale=0.5):
    """Render stills of an example with the real renderer (one browser session)."""
    import json
    from playwright.sync_api import sync_playwright
    from render import open_page, serve
    sp = ROOT / "examples" / example / "story.json"; story = json.loads(sp.read_text(encoding="utf-8"))
    srv, port = serve(sp.parent); tmp = Path(tempfile.mkdtemp()); out = []
    with sync_playwright() as pw:
        browser, page = open_page(pw, port, sp, story, scale, False)
        for t in times:
            page.evaluate(f"renderAt({t})"); f = tmp / f"{t}.png"; page.screenshot(path=str(f)); out.append(Image.open(f).convert("RGB"))
        browser.close()
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def film_frame(film, t, width=960):
    f = Path(tempfile.mkdtemp()) / "f.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(film), "-frames:v", "1", "-vf", f"scale={width}:-1", str(f)], check=True)
    return Image.open(f).convert("RGB")


def make_gallery():
    for name, (example, items) in GALLERIES.items():
        ims = render_stills(example, [t for t, _ in items])
        tiles = [caption(im.copy(), cap) for im, (_, cap) in zip(ims, items)]
        cols = 3
        sheet = grid(tiles, cols, tw=ims[0].width, th=ims[0].height)
        sheet.save(OUT / f"gallery-{name}.jpg", quality=88); print("wrote", OUT / f"gallery-{name}.jpg", sheet.size)


def make_film(film):
    shots = [(1.8, "torch-1-tower"), (9.0, "torch-2-warden"), (15.0, "torch-3-blast"), (28.6, "torch-4-beacon")]
    for t, n in shots:
        film_frame(film, t).save(OUT / f"{n}.jpg", quality=90); print("wrote", OUT / f"{n}.jpg")
    # banner: three vertical panels from the film with the title on top
    W, H = 1600, 640
    cuts = [film_frame(film, 3.8, 1200), film_frame(film, 12.3, 1200), film_frame(film, 28.6, 1200)]
    bn = Image.new("RGB", (W, H)); pw_ = W // 3
    for i, c in enumerate(cuts):
        c = c.crop((0, int(c.height * 0.125), c.width, int(c.height * 0.875)))   # drop the 2.37:1 letterbox bars
        s = H / c.height; c = c.resize((int(c.width * s), H), Image.LANCZOS); x0 = (c.width - pw_) // 2
        bn.paste(c.crop((x0, 0, x0 + pw_ + (W - 3 * pw_ if i == 2 else 0), H)), (i * pw_, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for y in range(H):  # darken the centre band for legibility
        a = int(190 * max(0.0, 1 - abs(y - H * 0.5) / (H * 0.42)) ** 0.8)
        d.line([(0, y), (W, y)], fill=(8, 8, 14, a))
    bn = Image.alpha_composite(bn.convert("RGBA"), ov); d = ImageDraw.Draw(bn)
    def centered(text, y, f, fill=(255, 255, 255, 255), shadow=True):
        w = d.textlength(text, font=f)
        if shadow:
            d.text(((W - w) / 2 + 3, y + 3), text, font=f, fill=(0, 0, 0, 200))
        d.text(((W - w) / 2, y), text, font=f, fill=fill)
    centered("BLOCKREEL", 190, font(150), (255, 255, 255, 255))
    centered("Minecraft-style animations, skins and texture packs", 362, font(42, False), (255, 226, 168, 255))
    centered("made from a prompt, rendered in code. No video model.", 414, font(42, False), (255, 226, 168, 255))
    centered("Claude Code plugin  -  Three.js  -  Chromium  -  ffmpeg", 500, font(26, False), (200, 210, 230, 255), shadow=False)
    bn.convert("RGB").save(OUT / "banner.jpg", quality=90); print("wrote", OUT / "banner.jpg")


def make_skin():
    it = ROOT / "examples" / "skin-demo" / "iterations"
    names = [("turntable_v1.png", "round 1: flat colours, cloak reads as a black slab"), ("turntable_v2.png", "round 2: belt and bracers, but the face got busy"),
             ("turntable_v3.png", "round 3: clean face, lighter cloak with folds"), ("turntable_v4_final.png", "final: subtle noise and hand-painted pixels")]
    rows = [caption(Image.open(it / n).convert("RGB").resize((1080, 390)), cap, 24) for n, cap in names]
    sheet = Image.new("RGB", (1080, 390 * 4 + 6 * 5), (14, 14, 18))
    for i, r in enumerate(rows):
        sheet.paste(r, (0, 6 + i * 396))
    sheet.save(OUT / "skin-iterations.jpg", quality=90); print("wrote skin-iterations.jpg")
    slim = Image.open(ROOT / "examples" / "skin-demo" / "turntable_slim.png").convert("RGB")
    slim.save(OUT / "skin-slim-wave.jpg", quality=90)


def make_textures():
    d = ROOT / "examples" / "texture-pack-demo"
    Image.open(d / "preview-in-scene.png").convert("RGB").resize((1440, 810), Image.LANCZOS).save(OUT / "textures-scene.jpg", quality=88)
    s = Image.open(d / "set-sheet.png").convert("RGB"); s.resize((s.width * 2, s.height * 2), Image.NEAREST).save(OUT / "textures-set.png")
    tiles = [Image.open(d / "tiling" / f"{n}.png").convert("RGB") for n in ("grass_block_top", "cobblestone", "oak_planks")]
    w = max(t.width for t in tiles); sheet = Image.new("RGB", (w, sum(t.height for t in tiles)), (30, 30, 34)); y = 0
    for t in tiles:
        sheet.paste(t, (0, y)); y += t.height
    sheet.save(OUT / "textures-tiling.png"); print("wrote textures-*.{jpg,png}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--film", help="the rendered film (mp4) used for the stills and the banner")
    ap.add_argument("--only", default="film,gallery,skin,textures")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    todo = set(a.only.split(","))
    if "film" in todo:
        if not a.film:
            print("--film is required for the film stills and the banner", file=sys.stderr); return 2
        make_film(Path(a.film))
    if "gallery" in todo:
        make_gallery()
    if "skin" in todo:
        make_skin()
    if "textures" in todo:
        make_textures()
    return 0


if __name__ == "__main__":
    sys.exit(main())
