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


# ----------------------------------------------------------------------------------------------- extras (v0.2) ----
def _blank(size=16):
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def _plant(stem, accent=None, seed=40, blades=7):
    """Cross-shaped plant sprite (tall grass, flowers): thin vertical blades on transparency."""
    rng = random.Random(seed); im = _blank()
    for i in range(blades):
        x = 1 + (i * 13 + rng.randrange(3)) % 14; top = rng.randrange(2, 9) if accent is None else rng.randrange(6, 11)
        for y in range(top, 16):
            lean = (y - top) // 5 * (1 if x < 8 else -1)
            f = 0.75 + 0.35 * (y - top) / max(1, 16 - top)
            im.putpixel((max(0, min(15, x - lean)), y), tuple(int(c * (1.15 - f * 0.4)) for c in stem) + (255,))
    if accent:
        for (x, y) in ((7, 3), (8, 3), (6, 4), (7, 4), (8, 4), (9, 4), (7, 5), (8, 5)):
            im.putpixel((x, y), accent + (255,))
        im.putpixel((7, 4), tuple(min(255, c + 60) for c in accent) + (255,))
        for y in range(6, 16):
            im.putpixel((8 if y % 4 else 7, y), stem + (255,))
    return im


def _torch(flame=((255, 236, 140), (255, 176, 40)), stick=(120, 86, 48)):
    """Torch sprite: a 2-px stick (cols 7-8, rows 6-15) with a 2x2 flame head, like the block-model torch."""
    im = _blank()
    for y in range(8, 16):
        for x in (7, 8):
            im.putpixel((x, y), tuple(int(c * (0.85 if x == 8 else 1)) for c in stick) + (255,))
    for (x, y, c) in ((7, 6, flame[0]), (8, 6, flame[1]), (7, 7, flame[1]), (8, 7, flame[0])):
        im.putpixel((x, y), c + (255,))
    return im


def _tool(kind, head, dark, handle=(137, 103, 39), handle_dark=(73, 54, 21)):
    """ORIGINAL 16x16 item sprites drawn on the diagonal like hand-held tools (blade/head up-right, grip down-left)."""
    im = _blank(); P = lambda x, y, c: im.putpixel((x, y), c + (255,)) if 0 <= x < 16 and 0 <= y < 16 else None
    light = tuple(min(255, int(c * 1.35) + 20) for c in head)
    if kind == "sword":
        for i in range(10):                 # blade: 3-px diagonal band from (14,1) to (5,10)
            x, y = 14 - i, 1 + i
            P(x, y, light); P(x - 1, y, head); P(x, y + 1, head); P(x - 1, y + 1, dark) if i < 9 else None
        P(15, 0, dark); P(14, 0, dark); P(15, 1, dark)
        for (x, y) in ((2, 9), (3, 10), (4, 11), (6, 13), (7, 14), (5, 12)):   # cross guard
            P(x, y, dark)
        for (x, y) in ((3, 9), (4, 10), (6, 12), (7, 13)):
            P(x, y, head)
        for i in range(4):                  # grip
            P(3 - i + 1, 12 + i - 1, handle); P(3 - i, 12 + i - 1, handle_dark)
        P(0, 15, dark); P(1, 15, dark); P(0, 14, dark)
    elif kind in ("pickaxe", "axe", "shovel"):
        for i in range(11):                 # handle along the diagonal
            P(3 + i, 13 - i, handle); P(2 + i, 13 - i, handle_dark)
        if kind == "pickaxe":
            pts = [(4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (9, 1), (10, 2), (11, 2), (12, 3), (13, 4), (13, 5), (14, 6), (14, 7), (14, 8), (14, 9), (14, 10)]
            for j, (x, y) in enumerate(pts):
                P(x, y, light if j % 3 else head); P(x, y + 1 if x < 12 else y, dark if j % 4 == 0 else head)
            for (x, y) in ((3, 2), (15, 11)):
                P(x, y, dark)
        elif kind == "axe":
            for y in range(1, 8):
                for x in range(9, 15):
                    if (x - 9) + (7 - y) >= 2 and (x - 9) - (y - 1) <= 4:
                        P(x, y, light if x > 12 else head)
            for (x, y) in ((9, 1), (14, 7), (8, 6), (13, 8)):
                P(x, y, dark)
        else:
            for (x, y) in ((11, 1), (12, 1), (13, 1), (14, 2), (14, 3), (14, 4), (11, 2), (12, 2), (13, 2), (12, 3), (13, 3), (13, 4)):
                P(x, y, light if x > 12 else head)
    elif kind == "bow":
        for i in range(12):                 # limb arc
            x = 3 + i; y = 13 - i; bend = 2 if 3 < i < 8 else (1 if 1 < i < 10 else 0)
            P(x + bend, y + bend, handle if i % 3 else handle_dark)
        for i in range(11):                 # string
            P(2 + i, 13 - i, (220, 220, 220))
    elif kind == "stick":
        for i in range(10):
            P(4 + i, 13 - i, handle); P(3 + i, 13 - i, handle_dark)
    return im


def build_extras(T):
    """Non-cube blocks, more cube blocks and items added in v0.2 (CC0, procedural)."""
    T["tall_grass"] = _plant((96, 158, 62), seed=41, blades=9)
    T["flower_red"] = _plant((60, 130, 44), accent=(214, 40, 40), seed=42, blades=2)
    T["flower_yellow"] = _plant((60, 130, 44), accent=(246, 214, 52), seed=43, blades=2)
    T["torch"] = _torch()
    T["redstone_torch"] = _torch(flame=((255, 90, 70), (200, 20, 20)))
    T["netherrack"] = speckle(noisy((112, 46, 46), 0.16, 44), (80, 26, 30), 30, 144)
    sb = noisy((122, 122, 124), 0.05, 45)
    for y in range(16):
        for x in range(16):
            if y in (0, 7, 8, 15) or x in ((0, 15) if y < 8 else (7, 8)):
                sb.putpixel((x, y), (84, 84, 88, 255))
    T["stonebrick"] = sb
    T["mossy_cobble"] = speckle(speckle(T["cobble"].copy(), (70, 110, 50), 30, 146), (90, 130, 60), 14, 147)
    T["gravel"] = speckle(speckle(noisy((132, 126, 122), 0.16, 48), (90, 86, 84), 30, 148), (170, 160, 156), 20, 149)
    T["bedrock"] = speckle(noisy((84, 84, 84), 0.35, 50), (30, 30, 30), 40, 150)
    T["birch_log"] = noisy((216, 214, 204), 0.04, 51)
    for (x, y) in ((2, 3), (3, 3), (9, 7), (10, 7), (11, 7), (5, 12), (6, 12), (13, 1), (14, 13), (0, 9)):
        T["birch_log"].putpixel((x, y), (52, 48, 44, 255))
    T["spruce_log"] = noisy((74, 52, 30), 0.08, 52)
    T["spruce_leaves"] = speckle(noisy((52, 88, 56), 0.16, 53), (34, 64, 40), 30, 153)
    T["birch_leaves"] = speckle(noisy((110, 150, 70), 0.16, 54), (80, 120, 50), 30, 154)
    T["iron_block"] = noisy((220, 220, 222), 0.04, 55)
    T["redstone_block"] = noisy((170, 24, 14), 0.10, 56)
    T["sandstone"] = noisy((216, 202, 152), 0.04, 57)
    T["soul_sand"] = speckle(noisy((84, 64, 50), 0.12, 58), (54, 40, 32), 26, 158)
    T["ice"] = noisy((150, 186, 246), 0.05, 59, alpha=210)
    T["blackstone"] = speckle(noisy((44, 38, 46), 0.14, 60), (26, 22, 28), 24, 160)
    T["crying_obsidian"] = speckle(T["obsidian"].copy(), (150, 60, 230), 18, 161)
    T["magma"] = speckle(noisy((120, 40, 14), 0.15, 61), (255, 140, 30), 26, 162)
    T["lantern"] = _torch(flame=((255, 230, 150), (240, 170, 60)), stick=(60, 60, 70))
    fire = _blank(); rng = random.Random(63)
    for x in range(16):
        top = 3 + int(5 * abs(((x * 7) % 11) / 11 - 0.5) * 2) + rng.randrange(3)
        for y in range(top, 16):
            k = (y - top) / max(1, 15 - top)
            fire.putpixel((x, y), (255, int(230 - 150 * k), int(120 - 110 * k), 255) if (x + y) % 5 or k > 0.3 else (255, 250, 200, 255))
    T["fire"] = fire
    T["dead_bush"] = _plant((140, 100, 52), seed=64, blades=6)
    T["quartz"] = noisy((236, 230, 222), 0.025, 65)
    T["dark_oak_planks"] = noisy((74, 50, 26), 0.05, 66)
    for y in (3, 7, 11, 15):
        for x in range(16):
            T["dark_oak_planks"].putpixel((x, y), (50, 32, 16, 255))
    I = {}
    for name, head, dark in (("wooden", (150, 116, 60), (90, 66, 30)), ("stone", (140, 140, 140), (80, 80, 80)),
                             ("iron", (216, 216, 216), (110, 110, 116)), ("golden", (250, 220, 70), (170, 120, 20)),
                             ("diamond", (80, 230, 220), (20, 120, 120)), ("netherite", (80, 70, 78), (36, 30, 34))):
        for kind in ("sword", "pickaxe", "axe", "shovel"):
            I[f"{name}_{kind}"] = _tool(kind, head, dark)
    I["bow"] = _tool("bow", (0, 0, 0), (0, 0, 0)); I["stick"] = _tool("stick", (0, 0, 0), (0, 0, 0))
    I["torch"] = T["torch"]
    sun = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for y in range(8, 24):
        for x in range(8, 24):
            edge = x in (8, 23) or y in (8, 23)
            sun.putpixel((x, y), (255, 236, 150, 255) if edge else (255, 250, 210, 255))
    moon = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    rng = random.Random(62)
    for y in range(10, 22):
        for x in range(10, 22):
            v = 214 + rng.randrange(-20, 20) - (30 if (x - 13) ** 2 + (y - 14) ** 2 < 4 or (x - 18) ** 2 + (y - 18) ** 2 < 3 else 0)
            moon.putpixel((x, y), (v, v, v + 8, 255))
    return I, {"sun": sun, "moon": moon}


EXTRA_INDEX = {
    "tall_grass": {"all": "tall_grass", "shape": "cross"}, "flower_red": {"all": "flower_red", "shape": "cross"},
    "flower_yellow": {"all": "flower_yellow", "shape": "cross"}, "poppy": {"all": "flower_red", "shape": "cross"},
    "dandelion": {"all": "flower_yellow", "shape": "cross"},
    "torch": {"all": "torch", "shape": "torch", "light": 14}, "redstone_torch": {"all": "redstone_torch", "shape": "torch", "light": 7, "lightColor": "#ff4030"},
    "lantern": {"all": "lantern", "shape": "torch", "light": 15},
    "netherrack": "netherrack", "stonebrick": "stonebrick", "stone_bricks": "stonebrick", "mossy_cobblestone": "mossy_cobble",
    "gravel": "gravel", "bedrock": "bedrock", "iron_block": "iron_block", "redstone_block": "redstone_block",
    "sandstone": "sandstone", "soul_sand": "soul_sand", "blackstone": "blackstone", "crying_obsidian": {"all": "crying_obsidian", "light": 10, "lightColor": "#a040ff"},
    "magma": {"all": "magma", "emissive": True, "light": 3},
    "ice": {"all": "ice", "transparent": True},
    "birch_log": {"top": "log_top", "side": "birch_log", "bottom": "log_top"},
    "spruce_log": {"top": "log_top", "side": "spruce_log", "bottom": "log_top"},
    "birch_leaves": {"all": "birch_leaves", "transparent": True}, "spruce_leaves": {"all": "spruce_leaves", "transparent": True},
    "stone_slab": {"all": "stone", "shape": "slab"}, "cobblestone_slab": {"all": "cobble", "shape": "slab"},
    "planks_slab": {"all": "planks", "shape": "slab"}, "oak_slab": {"all": "planks", "shape": "slab"},
    "cobblestone_stairs": {"all": "cobble", "shape": "stairs"}, "planks_stairs": {"all": "planks", "shape": "stairs"},
    "oak_stairs": {"all": "planks", "shape": "stairs"}, "stone_brick_stairs": {"all": "stonebrick", "shape": "stairs"},
    "oak_fence": {"all": "planks", "shape": "fence"}, "fence": {"all": "planks", "shape": "fence"},
    "cobblestone_wall": {"all": "cobble", "shape": "wall"},
    "fire": {"all": "fire", "shape": "cross", "emissive": True, "light": 15}, "dead_bush": {"all": "dead_bush", "shape": "cross"},
    "quartz": "quartz", "dark_oak_planks": "dark_oak_planks", "spruce_planks": "planks", "birch_planks": "planks",
    "stonebrick_mossy": "stonebrick", "mossy_stone_bricks": "stonebrick", "stonebrick_cracked": "stonebrick",
    "crafting_table": {"top": "planks", "side": "planks", "bottom": "planks"}, "dark_oak_log": {"top": "log_top", "side": "spruce_log", "bottom": "log_top"},
    "oak_planks": "planks", "oak_log": {"top": "log_top", "side": "log_side", "bottom": "log_top"}, "oak_leaves": {"all": "leaves", "transparent": True},
    "cobble": "cobble", "grass_block": {"top": "grass_top", "side": "grass_side", "bottom": "dirt"},
    "snow_layer": {"all": "snow", "shape": "layer", "height": 2}, "carpet_red": {"all": "wool_red", "shape": "layer", "height": 1},
}


# ------------------------------------------------------------------------------------------- equipment (v0.3) ----
def _uvbox(u, v, w, h, d):
    return {"top": (u + d, v, w, d), "bottom": (u + d + w, v, w, d), "right": (u, v + d, d, h), "front": (u + d, v + d, w, h),
            "left": (u + d + w, v + d, d, h), "back": (u + 2 * d + w, v + d, w, h)}


def _paint(im, rect, color, rows=None, seed=1, var=0.07, edge=True):
    x0, y0, w, h = rect; rng = random.Random(seed)
    for y in range(h):
        if rows is not None and y not in rows:
            continue
        for x in range(w):
            f = 1 + rng.uniform(-var, var) - (0.18 if edge and (y == h - 1 or x == w - 1) else 0) + (0.12 if edge and (y == 0 or x == 0) else 0)
            im.putpixel((x0 + x, y0 + y), tuple(max(0, min(255, int(c * f))) for c in color) + (255,))


def build_equipment():
    """ORIGINAL armour (64x32 classic layout), cape, elytra and shield textures: fallbacks when the game's are not cached."""
    out = OUT / "equipment"; (out / "humanoid").mkdir(parents=True, exist_ok=True); (out / "humanoid_leggings").mkdir(parents=True, exist_ok=True); (out / "wings").mkdir(parents=True, exist_ok=True)
    mats = {"leather": (150, 96, 60), "chainmail": (150, 150, 156), "iron": (205, 205, 210), "gold": (240, 200, 60), "diamond": (90, 215, 210),
            "netherite": (70, 62, 68), "copper": (205, 120, 80), "turtle_scute": (80, 160, 70)}
    for i, (m, c) in enumerate(mats.items()):
        a = Image.new("RGBA", (64, 32), (0, 0, 0, 0)); b = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
        head = _uvbox(0, 0, 8, 8, 8)
        _paint(a, head["top"], c, seed=i); _paint(a, head["back"], c, seed=i + 1)
        for f in ("right", "left"):
            _paint(a, head[f], c, rows=range(0, 6), seed=i + 2)
        _paint(a, head["front"], c, rows=range(0, 2), seed=i + 3)
        for f, r in _uvbox(16, 16, 8, 12, 4).items():
            _paint(a, r, c, seed=i + 4)
        for f, r in _uvbox(40, 16, 4, 12, 4).items():
            _paint(a, r, c, rows=range(0, 5) if f not in ("top", "bottom") else None, seed=i + 5)
        for f, r in _uvbox(0, 16, 4, 12, 4).items():   # boots on layer 1: the bottom rows of the legs
            _paint(a, r, c, rows=range(8, 12) if f not in ("top", "bottom") else None, seed=i + 6) if f != "top" else None
        for f, r in _uvbox(16, 16, 8, 12, 4).items():  # leggings on layer 2: belt + legs
            _paint(b, r, c, rows=range(8, 12) if f not in ("top", "bottom") else None, seed=i + 7) if f != "top" else None
        for f, r in _uvbox(0, 16, 4, 12, 4).items():
            _paint(b, r, c, rows=range(0, 9) if f not in ("top", "bottom") else None, seed=i + 8) if f != "bottom" else None
        a.save(out / "humanoid" / f"{m}.png"); b.save(out / "humanoid_leggings" / f"{m}.png")
    for name in ("leather_overlay",):
        Image.new("RGBA", (64, 32), (0, 0, 0, 0)).save(out / "humanoid" / f"{name}.png"); Image.new("RGBA", (64, 32), (0, 0, 0, 0)).save(out / "humanoid_leggings" / f"{name}.png")
    el = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    for f, r in _uvbox(22, 0, 10, 20, 2).items():
        _paint(el, r, (120, 120, 140), seed=70)
    el.save(out / "wings" / "elytra.png")
    sh = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    for f, r in _uvbox(0, 0, 12, 22, 1).items():
        _paint(sh, r, (140, 100, 60), seed=71)
    for f, r in _uvbox(26, 0, 2, 6, 6).items():
        _paint(sh, r, (90, 70, 50), seed=72)
    x0, y0, w, h = _uvbox(0, 0, 12, 22, 1)["front"]
    for y in range(h):
        for x in (0, w - 1):
            sh.putpixel((x0 + x, y0 + y), (160, 160, 170, 255))
    sh.save(out / "shield.png")
    for name, col in (("red", (180, 30, 40)), ("blue", (40, 70, 170)), ("black", (30, 30, 36))):   # capes (64x32, cape box 10x16x1 at 0,0)
        cp = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
        for f, r in _uvbox(0, 0, 10, 16, 1).items():
            _paint(cp, r, col, seed=73)
        (out / "capes").mkdir(exist_ok=True); cp.save(out / "capes" / f"{name}.png")


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
    items, env = build_extras(T)
    for name, im in T.items():
        im.save(OUT / "blocks" / f"{name}.png")
    (OUT / "items").mkdir(parents=True, exist_ok=True); (OUT / "env").mkdir(parents=True, exist_ok=True)
    for name, im in items.items():
        im.save(OUT / "items" / f"{name}.png")
    for name, im in env.items():
        im.save(OUT / "env" / f"{name}.png")
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
            "glowstone": {"all": "glowstone", "emissive": True, "light": 15},
            "lava": {"all": "lava", "flow": [0, 0.22], "emissive": True, "light": 15, "liquid": True},
            "water": {"all": "water", "transparent": True, "flow": [0, 0.12], "liquid": True},
            **EXTRA_INDEX,
        }
    }
    (OUT / "blocks" / "index.json").write_text(json.dumps(index, indent=2))
    skinlib.make_base("e8b894", "3b2a1e", "2b5fb4", "2e8bc0", "3b3b98", "3a3a3a").save(OUT / "skins" / "hero.png")
    skinlib.make_base("c98f6b", "d9a441", "2f8f4e", "b8433a", "2f4f6f", "2a2a2a",
                      slim=True, hair_style="long").save(OUT / "skins" / "explorer.png")
    skinlib.make_base("f1c27d", "cfcfcf", "5a3b8c", "6b3fa0", "2c2c3a", "1f1f26").save(OUT / "skins" / "villain.png")
    build_mobs()
    build_equipment()
    print(f"wrote {len(T)} block textures, 3 skins and 4 sample mob textures to {OUT}")


if __name__ == "__main__":
    build()
