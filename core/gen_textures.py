#!/usr/bin/env python3
"""Generate BlockReel's ORIGINAL built-in 16x16 block textures and starter skins.
Procedural, seeded, CC0. Run once: python core/gen_textures.py
Users swap them for their own textures (see docs/BLOCK-ATLAS.md)."""
import json
import random
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import skin as skinlib  # noqa: E402

OUT = Path(__file__).parent / "builtin"


def noisy(base, var=0.08, seed=1, size=16, alpha=255):
    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size))
    for y in range(size):
        for x in range(size):
            f = 1 + rng.uniform(-var, var)
            im.putpixel((x, y), tuple(max(0, min(255, int(c * f))) for c in base) + (alpha,))
    return im


def speckle(im, color, n, seed):
    rng = random.Random(seed)
    for _ in range(n):
        im.putpixel((rng.randrange(im.width), rng.randrange(im.height)), color + (255,))
    return im


def build_mobs():
    """ORIGINAL sample textures that follow the standard 64x32 entity layout (see docs/MOBS.md). They are placeholders
    so the rigs can be tested; users supply their own textures."""
    (OUT / "mobs").mkdir(parents=True, exist_ok=True)

    def sheet(base, seed):
        im = Image.new("RGBA", (64, 32))
        im.paste(noisy(base, 0.12, seed, size=64).crop((0, 0, 64, 32)), (0, 0))
        return im

    def fill(im, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                im.putpixel((xx, yy), c + (255,))

    g = sheet((74, 168, 82), 31)                       # creeper-layout sample: head (0,0), body (16,16), legs (0,16)
    fill(g, 9, 11, 2, 2, (20, 40, 24)); fill(g, 13, 11, 2, 2, (20, 40, 24)); fill(g, 10, 14, 4, 1, (20, 40, 24)); fill(g, 9, 13, 1, 1, (20, 40, 24)); fill(g, 14, 13, 1, 1, (20, 40, 24))
    g.save(OUT / "mobs" / "sample-creeper-layout.png")
    p = sheet((240, 150, 160), 32)                     # pig-layout sample: head (0,0), snout (16,16), legs (0,16), body (28,8)
    fill(p, 9, 11, 1, 1, (40, 20, 30)); fill(p, 14, 11, 1, 1, (40, 20, 30)); fill(p, 17, 17, 4, 3, (214, 110, 124)); fill(p, 18, 18, 1, 1, (90, 40, 50)); fill(p, 20, 18, 1, 1, (90, 40, 50))
    p.save(OUT / "mobs" / "sample-pig-layout.png")
    sp = sheet((74, 62, 60), 33)                       # spider-layout sample: neck (0,0), head (32,4), body (0,12), legs (18,0)
    fill(sp, 41, 14, 2, 2, (220, 40, 40)); fill(sp, 45, 14, 2, 2, (220, 40, 40)); fill(sp, 43, 17, 2, 1, (30, 24, 24))
    sp.save(OUT / "mobs" / "sample-spider-layout.png")
    skinlib.make_base("7fb06a", "3a5230", "4a8a8a", "3e6f9e", "3b3b98", "2a2a2a").save(OUT / "mobs" / "sample-zombie-layout.png")


def build():
    (OUT / "blocks").mkdir(parents=True, exist_ok=True)
    (OUT / "skins").mkdir(parents=True, exist_ok=True)
    T = {}
    T["grass_top"] = noisy((96, 158, 62), 0.10, 1)
    T["dirt"] = speckle(noisy((134, 96, 67), 0.09, 2), (101, 70, 48), 18, 22)
    g = noisy((134, 96, 67), 0.09, 3)
    gt = noisy((96, 158, 62), 0.10, 4)
    for y in range(4):
        for x in range(16):
            g.putpixel((x, y), gt.getpixel((x, y)))
    for x in range(0, 16, 3):
        g.putpixel((x, 4), gt.getpixel((x, 4)))
    T["grass_side"] = g
    T["stone"] = speckle(noisy((125, 125, 128), 0.07, 5), (100, 100, 104), 22, 55)
    c = noisy((112, 112, 114), 0.12, 6)
    for i in range(0, 16, 4):
        for x in range(16):
            c.putpixel((x, i), (78, 78, 82, 255))
        for y in range(i, i + 4):
            c.putpixel(((i * 3 + 2) % 16, y), (78, 78, 82, 255))
    T["cobble"] = c
    p = noisy((176, 138, 84), 0.05, 7)
    for y in (3, 7, 11, 15):
        for x in range(16):
            p.putpixel((x, y), (126, 96, 56, 255))
    T["planks"] = p
    lg = noisy((106, 82, 48), 0.07, 8)
    for x in range(0, 16, 4):
        for y in range(16):
            lg.putpixel((x, y), (80, 60, 34, 255))
    T["log_side"] = lg
    lt = noisy((170, 134, 82), 0.05, 9)
    for r in (2, 4, 6):
        for i in range(r, 16 - r):
            for (a, b) in ((i, r), (i, 15 - r), (r, i), (15 - r, i)):
                lt.putpixel((a, b), (122, 92, 52, 255))
    T["log_top"] = lt
    lv = noisy((52, 122, 44), 0.18, 10)
    speckle(lv, (30, 90, 28), 30, 100)
    T["leaves"] = lv
    T["sand"] = speckle(noisy((226, 212, 150), 0.04, 11), (206, 190, 128), 14, 111)
    br = noisy((150, 70, 56), 0.07, 12)
    for y in (0, 4, 8, 12):
        for x in range(16):
            br.putpixel((x, y), (190, 180, 170, 255))
    for y in range(16):
        for x in ((0, 8) if (y // 4) % 2 == 0 else (4, 12)):
            br.putpixel((x, y), (190, 180, 170, 255))
    T["bricks"] = br
    T["obsidian"] = speckle(noisy((24, 16, 40), 0.25, 13), (70, 40, 110), 14, 133)
    T["glowstone"] = speckle(noisy((236, 196, 92), 0.15, 14), (255, 240, 170), 26, 144)
    T["snow"] = noisy((244, 248, 252), 0.025, 15)
    T["water"] = noisy((48, 102, 214), 0.06, 16, alpha=170)
    gl = Image.new("RGBA", (16, 16), (200, 230, 240, 40))
    for i in range(16):
        for (a, b) in ((i, 0), (i, 15), (0, i), (15, i)):
            gl.putpixel((a, b), (220, 240, 250, 255))
    for i in range(3, 8):
        gl.putpixel((i, 15 - i), (255, 255, 255, 220))
    T["glass"] = gl
    T["tnt_side"] = noisy((200, 52, 44), 0.05, 17)
    for y in range(6, 10):
        for x in range(16):
            T["tnt_side"].putpixel((x, y), (236, 230, 214, 255))
    T["tnt_top"] = noisy((190, 60, 52), 0.05, 18)
    T["wool_white"] = noisy((232, 232, 232), 0.04, 19)
    T["wool_red"] = noisy((176, 46, 38), 0.04, 20)
    T["wool_blue"] = noisy((52, 76, 170), 0.04, 21)
    T["gold"] = noisy((246, 208, 60), 0.08, 22)
    T["diamond"] = noisy((90, 220, 210), 0.10, 23)
    lava = noisy((222, 84, 18), 0.18, 24)
    speckle(lava, (255, 196, 64), 40, 244)
    speckle(lava, (150, 36, 10), 30, 245)
    T["lava"] = lava
    ch = noisy((138, 96, 52), 0.06, 25)
    for i in range(16):
        for (a, b) in ((i, 0), (i, 15), (0, i), (15, i)):
            ch.putpixel((a, b), (70, 44, 22, 255))
    for x in range(16):
        ch.putpixel((x, 5), (90, 60, 30, 255))
    for y in range(16):
        ch.putpixel((7, y), (190, 190, 196, 255)); ch.putpixel((8, y), (150, 150, 158, 255))
    T["chest"] = ch
    for name, im in T.items():
        im.save(OUT / "blocks" / f"{name}.png")
    index = {
        "blocks": {
            "grass": {"top": "grass_top", "side": "grass_side", "bottom": "dirt"},
            "dirt": "dirt", "stone": "stone", "cobblestone": "cobble", "planks": "planks",
            "log": {"top": "log_top", "side": "log_side", "bottom": "log_top"},
            "leaves": {"all": "leaves", "transparent": True},
            "sand": "sand", "bricks": "bricks", "obsidian": "obsidian", "glowstone": {"all": "glowstone", "emissive": True},
            "snow": "snow", "water": {"all": "water", "transparent": True, "flow": [0, 0.12]},
            "lava": {"all": "lava", "flow": [0, 0.22], "emissive": True}, "chest": "chest",
            "glass": {"all": "glass", "transparent": True},
            "tnt": {"top": "tnt_top", "side": "tnt_side", "bottom": "tnt_top"},
            "wool_white": "wool_white", "wool_red": "wool_red", "wool_blue": "wool_blue",
            "gold": "gold", "diamond": "diamond",
        }
    }
    (OUT / "blocks" / "index.json").write_text(json.dumps(index, indent=2))
    skinlib.make_base("e8b894", "3b2a1e", "2b5fb4", "2e8bc0", "3b3b98", "3a3a3a").save(OUT / "skins" / "hero.png")
    skinlib.make_base("c98f6b", "d9a441", "2f8f4e", "b8433a", "2f4f6f", "2a2a2a",
                      slim=True, hair_style="long").save(OUT / "skins" / "explorer.png")
    skinlib.make_base("f1c27d", "cfcfcf", "5a3b8c", "6b3fa0", "2c2c3a", "1f1f26").save(OUT / "skins" / "villain.png")
    build_mobs()
    print(f"wrote {len(T)} block textures, 3 skins and 4 sample mob textures to {OUT}")


if __name__ == "__main__":
    build()
