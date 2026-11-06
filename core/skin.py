#!/usr/bin/env python3
"""BlockReel skin tools: validate, convert, unwrap, preview, make, snap.

Works on standard Minecraft-style skin PNGs (64x64, legacy 64x32, or HD multiples).
Everything here is original code; no game assets are used or shipped.

Usage:
  python core/skin.py validate  skin.png
  python core/skin.py convert   old_64x32.png new_64x64.png
  python core/skin.py unwrap    skin.png out_dir/        # every body part + face as its own PNG
  python core/skin.py preview   skin.png preview.png     # flat front/back paper-doll
  python core/skin.py layout    layout.png               # labelled UV map (reference image)
  python core/skin.py make      out.png --skin f1c27d --hair 4a2f1b --shirt 2e8bc0 --pants 3b3b98
  python core/skin.py snap      screenshot.png out.png --crop x0,y0,x1,y1   # clean up a screenshot
"""
import argparse
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

FACES = ("top", "bottom", "right", "front", "left", "back")


# ---------------------------------------------------------------- layout ----
def box_uv(u, v, w, h, d):
    """Rectangles (x, y, width, height) of the 6 faces of a box whose UV origin is (u, v).
    Texture order left->right: right side, front, left side, back.  Top/bottom sit above."""
    return {
        "top": (u + d, v, w, d),
        "bottom": (u + d + w, v, w, d),
        "right": (u, v + d, d, h),
        "front": (u + d, v + d, w, h),
        "left": (u + d + w, v + d, d, h),
        "back": (u + 2 * d + w, v + d, w, h),
    }


def parts(slim=False):
    """name -> (u, v, w, h, d) in 64x64 skin pixels."""
    aw = 3 if slim else 4
    return {
        "head": (0, 0, 8, 8, 8), "hat": (32, 0, 8, 8, 8),
        "body": (16, 16, 8, 12, 4), "jacket": (16, 32, 8, 12, 4),
        "right_arm": (40, 16, aw, 12, 4), "right_sleeve": (40, 32, aw, 12, 4),
        "left_arm": (32, 48, aw, 12, 4), "left_sleeve": (48, 48, aw, 12, 4),
        "right_leg": (0, 16, 4, 12, 4), "right_pants": (0, 32, 4, 12, 4),
        "left_leg": (16, 48, 4, 12, 4), "left_pants": (0, 48, 4, 12, 4),
    }


OVERLAY_OF = {"head": "hat", "body": "jacket", "right_arm": "right_sleeve",
              "left_arm": "left_sleeve", "right_leg": "right_pants", "left_leg": "left_pants"}


def face_rect(part, face, slim=False, scale=1):
    u, v, w, h, d = parts(slim)[part]
    x, y, fw, fh = box_uv(u, v, w, h, d)[face]
    return (x * scale, y * scale, fw * scale, fh * scale)


# ------------------------------------------------------------- inspection ----
def load(path):
    return Image.open(path).convert("RGBA")


def detect_model(img):
    """'slim' (3px arms) or 'classic' (4px arms), judged by the transparent arm column."""
    s = img.width // 64
    a = img.getchannel("A")
    def col_empty(x, y0, y1):
        return all(a.getpixel((x * s + dx, y * s + dy)) == 0
                   for y in range(y0, y1) for dx in range(s) for dy in range(s))
    # slim arms are 3px wide: the last column of the arm's back face is unused (empty)
    right = col_empty(55, 20, 32)
    if img.height == 32 * s:
        return "slim" if right else "classic"
    return "slim" if (right and col_empty(47, 52, 64)) else "classic"


def validate(path):
    img = load(path)
    w, h = img.size
    report = {"file": str(path), "size": [w, h], "errors": [], "warnings": []}
    s = w // 64 if w % 64 == 0 else 0
    if not s or h not in (32 * s, 64 * s):
        report["errors"].append(f"size {w}x{h} is not 64x64, 64x32 or an HD multiple of them")
        return report
    report["legacy"] = h == 32 * s
    report["hd_scale"] = s
    if report["legacy"]:
        report["warnings"].append("legacy 64x32 skin: run `convert` to get a 64x64 skin with a left arm/leg")
    slim = detect_model(img) == "slim"
    report["model"] = "slim" if slim else "classic"
    a = img.getchannel("A")
    base = ["head", "body", "right_arm", "left_arm", "right_leg", "left_leg"]
    bad = 0
    total = 0
    for name in base:
        if report["legacy"] and name in ("left_arm", "left_leg"):
            continue
        for f in FACES:
            x, y, fw, fh = face_rect(name, f, slim, s)
            for yy in range(y, y + fh):
                for xx in range(x, x + fw):
                    total += 1
                    if a.getpixel((xx, yy)) < 255:
                        bad += 1
    report["transparent_base_pixels"] = bad
    if bad:
        pct = 100.0 * bad / max(total, 1)
        report["warnings"].append(
            f"{bad} transparent pixels ({pct:.1f}%) inside the base layer; "
            "they may render as holes or black. Keep transparency only in the overlay layer.")
    report["ok"] = not report["errors"]
    return report


# ------------------------------------------------------------- conversion ----
def legacy_to_modern(img):
    s = img.width // 64
    if img.height != 32 * s:
        return img
    out = Image.new("RGBA", (64 * s, 64 * s), (0, 0, 0, 0))
    out.paste(img, (0, 0))
    swap = {"top": "top", "bottom": "bottom", "front": "front", "back": "back",
            "right": "left", "left": "right"}
    for src, dst in (("right_leg", "left_leg"), ("right_arm", "left_arm")):
        for f, g in swap.items():
            sx, sy, w, h = face_rect(src, f, False, s)
            dx, dy, _, _ = face_rect(dst, g, False, s)
            tile = img.crop((sx, sy, sx + w, sy + h)).transpose(Image.FLIP_LEFT_RIGHT)
            out.paste(tile, (dx, dy))
    return out


# ----------------------------------------------------------------- unwrap ----
def unwrap(path, out_dir):
    img = load(path)
    if img.height == img.width // 2:
        img = legacy_to_modern(img)
    s = img.width // 64
    slim = detect_model(img) == "slim"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"model": "slim" if slim else "classic", "scale": s, "parts": {}}
    for name in parts(slim):
        manifest["parts"][name] = {}
        for f in FACES:
            x, y, w, h = face_rect(name, f, slim, s)
            fn = f"{name}_{f}.png"
            img.crop((x, y, x + w, y + h)).save(out / fn)
            manifest["parts"][name][f] = {"file": fn, "rect": [x, y, w, h]}
    (out / "parts.json").write_text(json.dumps(manifest, indent=2))
    return manifest


# ---------------------------------------------------------------- preview ----
def _paste_face(canvas, img, part, face, pos, slim, s):
    x, y, w, h = face_rect(part, face, slim, s)
    tile = img.crop((x, y, x + w, y + h))
    canvas.alpha_composite(tile, pos)


def preview(path, out_path, scale=10, bg=(40, 40, 46, 255)):
    img = load(path)
    if img.height == img.width // 2:
        img = legacy_to_modern(img)
    s = img.width // 64
    slim = detect_model(img) == "slim"
    aw = 3 if slim else 4

    def doll(view):
        c = Image.new("RGBA", (16 * s, 32 * s), (0, 0, 0, 0))
        f = view
        layers = (0, 1)  # base then overlay
        for layer in layers:
            def P(part):
                return part if layer == 0 else OVERLAY_OF[part]
            put = lambda part, pos: _paste_face(c, img, P(part), f, (pos[0] * s, pos[1] * s), slim, s)
            put("head", (4, 0))
            put("body", (4, 8))
            if view == "front":  # viewer's left = character's right
                put("right_arm", (4 - aw, 8)); put("left_arm", (12, 8))
                put("right_leg", (4, 20)); put("left_leg", (8, 20))
            else:
                put("left_arm", (4 - aw, 8)); put("right_arm", (12, 8))
                put("left_leg", (4, 20)); put("right_leg", (8, 20))
        return c

    sheet = Image.new("RGBA", (36 * s, 36 * s), bg)
    sheet.alpha_composite(doll("front"), (1 * s, 2 * s))
    sheet.alpha_composite(doll("back"), (19 * s, 2 * s))
    sheet = sheet.resize((sheet.width * scale // s, sheet.height * scale // s), Image.NEAREST)
    sheet.save(out_path)
    return out_path


def layout_image(out_path, scale=10, slim=False):
    """Reference picture of the UV map with every box labelled."""
    img = Image.new("RGBA", (64 * scale, 64 * scale), (30, 30, 36, 255))
    d = ImageDraw.Draw(img)
    palette = {"head": (231, 76, 60), "hat": (192, 57, 43), "body": (52, 152, 219),
               "jacket": (41, 128, 185), "right_arm": (46, 204, 113), "right_sleeve": (39, 174, 96),
               "left_arm": (241, 196, 15), "left_sleeve": (243, 156, 18),
               "right_leg": (155, 89, 182), "right_pants": (142, 68, 173),
               "left_leg": (26, 188, 156), "left_pants": (22, 160, 133)}
    for name, (u, v, w, h, dd) in parts(slim).items():
        for f, (x, y, fw, fh) in box_uv(u, v, w, h, dd).items():
            col = palette[name]
            d.rectangle([x * scale, y * scale, (x + fw) * scale - 1, (y + fh) * scale - 1],
                        fill=col + (150,), outline=(255, 255, 255, 255))
            if fw * scale > 40 and fh * scale > 24:
                d.text((x * scale + 3, y * scale + 3), f"{name}\n{f}", fill=(255, 255, 255, 255))
    img.save(out_path)
    return out_path


# ------------------------------------------------------------------- make ----
def hexcolor(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def shade(c, f):
    return (max(0, min(255, int(c[0] * f))), max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))), c[3])


# ------------------------------------------------------- painting helpers ----
def ramp(base, steps=4, spread=0.24, hue_shift=0.0):
    """A dark -> light ramp of `steps` tones around `base` (RGBA tuple or hex). Pixel-art shading uses 3-4 tones per material.
    `hue_shift` pushes shadows toward blue/purple and lights toward yellow (0.0 = none, ~0.06 = a gentle painterly shift)."""
    c = hexcolor(base) if isinstance(base, str) else tuple(base)
    out = []
    for i in range(steps):
        t = i / (steps - 1) if steps > 1 else 0.5          # 0 = darkest, 1 = lightest
        f = 1 - spread + 2 * spread * t * 0.9
        r, g, b = c[0] * f, c[1] * f, c[2] * f
        if hue_shift:
            k = (t - 0.5) * 2                                # -1 shadow .. +1 light
            r += k * hue_shift * 255 * 0.6; g += k * hue_shift * 255 * 0.25; b -= k * hue_shift * 255 * 0.7
        out.append((max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b))), c[3] if len(c) > 3 else 255))
    return out


# faces a light from the upper left front hits hardest: top > front > right/left > back > bottom
FACE_LIGHT = {"top": 1.0, "front": 0.72, "left": 0.55, "right": 0.5, "back": 0.38, "bottom": 0.12}


class SkinCanvas:
    """Paint a 64x64 skin face by face. Coordinates are relative to the face's top-left."""

    def __init__(self, slim=False, seed=7):
        self.img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        self.slim = slim
        self.rng = random.Random(seed)

    def rect(self, part, face, x, y, w, h, color, noise=0.0):
        fx, fy, fw, fh = face_rect(part, face, self.slim)
        for yy in range(y, min(y + h, fh)):
            for xx in range(x, min(x + w, fw)):
                c = color
                if noise and c[3] == 255:
                    c = shade(c, 1 + self.rng.uniform(-noise, noise))
                self.img.putpixel((fx + xx, fy + yy), c)

    def fill(self, part, face, color, noise=0.0):
        _, _, fw, fh = face_rect(part, face, self.slim)
        self.rect(part, face, 0, 0, fw, fh, color, noise)

    def fill_all(self, part, color, noise=0.0):
        for f in FACES:
            self.fill(part, f, color, noise)

    # --- helpers for layered, shaded painting ---------------------------------------------------------------
    def px(self, part, face, x, y, color):
        self.rect(part, face, x, y, 1, 1, color)

    def line(self, part, face, x0, y0, x1, y1, color):
        """Bresenham line in face coordinates (for belts, stripes, seams)."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1; err = dx + dy
        while True:
            self.px(part, face, x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy; x0 += sx
            if e2 <= dx:
                err += dx; y0 += sy

    def shaded_box(self, part, tones, noise=0.0):
        """Fill every face of `part` from a ramp (dark..light), lighter on top and front, darker underneath."""
        n = len(tones)
        for f in FACES:
            self.fill(part, f, tones[min(n - 1, int(FACE_LIGHT[f] * (n - 1) + 0.5))], noise)

    def edge_light(self, part, face, light, dark=None, left=True, bottom=True):
        """1 px highlight on the top (and left) edge and a 1 px shade on the bottom (and right) edge of a face."""
        _, _, fw, fh = face_rect(part, face, self.slim)
        self.rect(part, face, 0, 0, fw, 1, light)
        if left:
            self.rect(part, face, 0, 0, 1, fh, light)
        if dark and bottom:
            self.rect(part, face, 0, fh - 1, fw, 1, dark)
            self.rect(part, face, fw - 1, 0, 1, fh, dark)

    def clear(self, part, face=None):
        for f in ([face] if face else FACES):
            fx, fy, fw, fh = face_rect(part, f, self.slim)
            for yy in range(fy, fy + fh):
                for xx in range(fx, fx + fw):
                    self.img.putpixel((xx, yy), (0, 0, 0, 0))

    def mirror_limbs(self, layers=True):
        """Copy the right arm and leg (and their overlays) onto the left ones, mirrored: paint one side, get both."""
        pairs = [("right_arm", "left_arm"), ("right_leg", "left_leg")]
        if layers:
            pairs += [("right_sleeve", "left_sleeve"), ("right_pants", "left_pants")]
        for r, l in pairs:
            for src_face, dst_face in (("front", "front"), ("back", "back"), ("top", "top"), ("bottom", "bottom"), ("right", "left"), ("left", "right")):
                sx, sy, sw, sh = face_rect(r, src_face, self.slim); dx, dy, dw, dh = face_rect(l, dst_face, self.slim)
                tile = self.img.crop((sx, sy, sx + sw, sy + sh)).transpose(Image.FLIP_LEFT_RIGHT)
                self.img.paste(tile, (dx, dy))


def make_base(skin="f1c27d", hair="4a2f1b", eyes="2b5fb4", shirt="2e8bc0", pants="3b3b98",
              shoes="3a3a3a", slim=False, hair_style="short", seed=7):
    """Original starter skin from a handful of colours. Edit the result in any pixel editor."""
    cv = SkinCanvas(slim, seed)
    S, H, E, T, P, B = (hexcolor(x) for x in (skin, hair, eyes, shirt, pants, shoes))
    n = 0.05
    # head
    cv.fill_all("head", S, n)
    cv.fill("head", "top", H, n)
    cv.fill("head", "back", H, n)
    for side in ("left", "right"):
        cv.rect("head", side, 0, 0, 8, 3, H, n)
        cv.rect("head", side, 0, 3, 3, 1, H, n)
    cv.rect("head", "front", 0, 0, 8, 2, H, n)
    cv.rect("head", "front", 0, 2, 2, 1, H, n)
    cv.rect("head", "front", 6, 2, 2, 1, H, n)
    cv.rect("head", "front", 1, 4, 2, 1, (255, 255, 255, 255))
    cv.rect("head", "front", 5, 4, 2, 1, (255, 255, 255, 255))
    cv.rect("head", "front", 2, 4, 1, 1, E)
    cv.rect("head", "front", 5, 4, 1, 1, E)
    cv.rect("head", "front", 3, 6, 2, 1, shade(S, 0.78))
    cv.rect("head", "front", 3, 5, 2, 1, shade(S, 0.92))
    if hair_style == "long":
        cv.rect("head", "right", 0, 3, 8, 5, H, n)
        cv.rect("head", "left", 0, 3, 8, 5, H, n)
        cv.rect("head", "back", 0, 0, 8, 8, H, n)
    # hat layer: a little hair volume
    cv.fill("hat", "top", H, n)
    cv.rect("hat", "back", 0, 0, 8, 4, H, n)
    # body
    cv.fill_all("body", T, n)
    cv.fill("body", "bottom", shade(T, 0.8), n)
    # arms
    for arm in ("right_arm", "left_arm"):
        cv.fill_all(arm, S, n)
        for f in ("front", "back", "left", "right"):
            cv.rect(arm, f, 0, 0, 4, 4, T, n)
        cv.fill(arm, "top", T, n)
    # legs
    for leg in ("right_leg", "left_leg"):
        cv.fill_all(leg, P, n)
        for f in ("front", "back", "left", "right"):
            cv.rect(leg, f, 0, 10, 4, 2, B, n)
        cv.fill(leg, "bottom", B, n)
    return cv.img


# ------------------------------------------------------------------- snap ----
def snap(in_path, out_path, crop=None, size=64):
    """Turn a (screenshot of a) scaled-up skin into a clean size x size PNG.
    Samples the centre of every source cell, so integer or fractional zoom both work."""
    img = Image.open(in_path).convert("RGBA")
    if crop:
        img = img.crop(crop)
    if abs(img.width - img.height) > max(2, img.width * 0.02):
        print(f"warning: crop is {img.width}x{img.height}, a skin is square. "
              "Crop exactly the texture (no app UI, no missing rows).", file=sys.stderr)
    out = img.resize((size, size), Image.NEAREST)
    out.save(out_path)
    # alignment check: re-zoom the result and compare with the source. A clean, correctly cropped
    # pixel-art texture reproduces almost exactly; a misaligned crop does not.
    import numpy as np
    a = np.asarray(img.convert("RGB"), dtype=float)
    b = np.asarray(out.resize(img.size, Image.NEAREST).convert("RGB"), dtype=float)
    err = float(np.abs(a - b).mean())
    if err > 5:
        print(f"warning: the snapped skin differs from the source by {err:.1f}/255 on average, so the crop/size "
              "probably does not match the pixel grid (cropped rows, UI overlay, or non-integer zoom). "
              "Do not trust the result: get the original PNG.", file=sys.stderr)
    return out_path


# -------------------------------------------------------------------- CLI ----
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate"); p.add_argument("skin")
    p = sub.add_parser("convert"); p.add_argument("skin"); p.add_argument("out")
    p = sub.add_parser("unwrap"); p.add_argument("skin"); p.add_argument("out_dir")
    p = sub.add_parser("preview"); p.add_argument("skin"); p.add_argument("out"); p.add_argument("--scale", type=int, default=10)
    p = sub.add_parser("layout"); p.add_argument("out"); p.add_argument("--slim", action="store_true")
    p = sub.add_parser("make"); p.add_argument("out")
    for k, v in (("skin", "f1c27d"), ("hair", "4a2f1b"), ("eyes", "2b5fb4"), ("shirt", "2e8bc0"),
                 ("pants", "3b3b98"), ("shoes", "3a3a3a")):
        p.add_argument(f"--{k}", default=v)
    p.add_argument("--slim", action="store_true"); p.add_argument("--hair-style", default="short", choices=["short", "long"])
    p = sub.add_parser("snap"); p.add_argument("inp"); p.add_argument("out")
    p.add_argument("--crop", help="x0,y0,x1,y1 in pixels"); p.add_argument("--size", type=int, default=64)
    a = ap.parse_args(argv)

    if a.cmd == "validate":
        r = validate(a.skin)
        print(json.dumps(r, indent=2))
        return 0 if not r["errors"] else 1
    if a.cmd == "convert":
        legacy_to_modern(load(a.skin)).save(a.out); print("wrote", a.out)
    elif a.cmd == "unwrap":
        m = unwrap(a.skin, a.out_dir); print(f"wrote {sum(len(v) for v in m['parts'].values())} faces to {a.out_dir} ({m['model']})")
    elif a.cmd == "preview":
        preview(a.skin, a.out, a.scale); print("wrote", a.out)
    elif a.cmd == "layout":
        layout_image(a.out, slim=a.slim); print("wrote", a.out)
    elif a.cmd == "make":
        make_base(a.skin, a.hair, a.eyes, a.shirt, a.pants, a.shoes, a.slim, a.hair_style).save(a.out)
        print("wrote", a.out)
    elif a.cmd == "snap":
        crop = tuple(int(x) for x in a.crop.split(",")) if a.crop else None
        snap(a.inp, a.out, crop, a.size); print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
