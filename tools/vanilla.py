#!/usr/bin/env python3
"""Fetch the ORIGINAL Minecraft textures into a local cache, so films look like the game by default.

  python tools/vanilla.py fetch                 # Mojang's official Bedrock samples (default)
  python tools/vanilla.py fetch --source ztech  # mirror: github.com/ZtechNetwork/MCBVanillaResourcePack
  python tools/vanilla.py sounds                # original sound effects (Java asset index, official Mojang servers)
  python tools/vanilla.py status

What it does: downloads only the ~40 small PNG/TGA files the engine uses (about 70 KB) from GitHub into
`work/vanilla/raw/`, then writes `work/vanilla/blocks/` (engine block names + index.json) and `work/vanilla/entity/`
(zombie, creeper, pig, spider, chest, steve, alex). Greyscale textures are tinted the way the game tints them in a plains
biome (grass, leaves, water). Animated strips (water, lava) keep their first frame; the engine scrolls them.

The engine uses this cache automatically when it exists (story.json can opt out with "textures": "builtin").
LEGAL: these are Mojang's textures. They stay in work/ (gitignored) on the user's machine; never commit or redistribute them.
"""
import argparse
import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "vanilla"
SOURCES = {
    "mojang": "https://raw.githubusercontent.com/Mojang/bedrock-samples/main/resource_pack/",
    "ztech": "https://raw.githubusercontent.com/ZtechNetwork/MCBVanillaResourcePack/master/",
}
# Biome tints for greyscale textures (plains biome colours as used by the game's colormaps; approximate values).
GRASS, FOLIAGE, WATER = (0x91, 0xBD, 0x59), (0x77, 0xAB, 0x2F), (0x3F, 0x76, 0xE4)

# engine texture name -> (file in the pack, tint or None)
BLOCK_FILES = {
    "stone": ("textures/blocks/stone.png", None), "cobble": ("textures/blocks/cobblestone.png", None),
    "dirt": ("textures/blocks/dirt.png", None), "grass_top": ("textures/blocks/grass_top.png", GRASS),
    "grass_side": ("textures/blocks/grass_side_carried.png", None), "planks": ("textures/blocks/planks_oak.png", None),
    "log_side": ("textures/blocks/log_oak.png", None), "log_top": ("textures/blocks/log_oak_top.png", None),
    "leaves": ("textures/blocks/leaves_oak_carried.tga", None), "sand": ("textures/blocks/sand.png", None),
    "bricks": ("textures/blocks/brick.png", None), "obsidian": ("textures/blocks/obsidian.png", None),
    "glowstone": ("textures/blocks/glowstone.png", None), "snow": ("textures/blocks/snow.png", None),
    "glass": ("textures/blocks/glass.png", None), "tnt_side": ("textures/blocks/tnt_side.png", None),
    "tnt_top": ("textures/blocks/tnt_top.png", None), "tnt_bottom": ("textures/blocks/tnt_bottom.png", None),
    "wool_white": ("textures/blocks/wool_colored_white.png", None), "wool_red": ("textures/blocks/wool_colored_red.png", None),
    "wool_blue": ("textures/blocks/wool_colored_blue.png", None), "gold": ("textures/blocks/gold_block.png", None),
    "diamond": ("textures/blocks/diamond_block.png", None), "water": ("textures/blocks/water_still_grey.png", WATER),
    "lava": ("textures/blocks/lava_still.png", None), "stonebrick": ("textures/blocks/stonebrick.png", None),
    "gravel": ("textures/blocks/gravel.png", None), "bedrock": ("textures/blocks/bedrock.png", None),
    "crafting_table_front": ("textures/blocks/crafting_table_front.png", None), "chest_front": ("textures/blocks/chest_front.png", None),
}
ENTITY_FILES = {
    "zombie": "textures/entity/zombie/zombie.png", "creeper": "textures/entity/creeper/creeper.png",
    "pig": "textures/entity/pig/pig.png", "spider": "textures/entity/spider/spider.tga",
    "chest": "textures/entity/chest/normal.png", "steve": "textures/entity/steve.png", "alex": "textures/entity/alex.png",
}
INDEX = {
    "stone": "stone", "cobblestone": "cobble", "dirt": "dirt", "planks": "planks", "sand": "sand", "bricks": "bricks",
    "obsidian": "obsidian", "snow": "snow", "wool_white": "wool_white", "wool_red": "wool_red", "wool_blue": "wool_blue",
    "gold": "gold", "diamond": "diamond", "stonebrick": "stonebrick", "gravel": "gravel", "bedrock": "bedrock",
    "grass": {"top": "grass_top", "side": "grass_side", "bottom": "dirt"},
    "log": {"top": "log_top", "side": "log_side", "bottom": "log_top"},
    "leaves": {"all": "leaves", "transparent": True},
    "glass": {"all": "glass", "transparent": True},
    "glowstone": {"all": "glowstone", "emissive": True},
    "tnt": {"top": "tnt_top", "side": "tnt_side", "bottom": "tnt_bottom"},
    "water": {"all": "water", "transparent": True, "flow": [0, 0.12]},
    "lava": {"all": "lava", "flow": [0, 0.22], "emissive": True},
    "chest": {"all": "chest_front"},
    "crafting_table": {"top": "planks", "side": "crafting_table_front", "bottom": "planks"},
}


def tint(im, rgb):
    im = im.convert("RGBA"); px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]; lum = (r + g + b) / 3 / 255
            px[x, y] = (int(rgb[0] * lum), int(rgb[1] * lum), int(rgb[2] * lum), a)
    return im


def first_frame(im):
    return im.crop((0, 0, im.width, im.width)) if im.height > im.width and im.height % im.width == 0 else im


def get(base, rel, raw_dir):
    dst = raw_dir / rel
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(base + rel, headers={"User-Agent": "blockreel-vanilla-fetch"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dst.write_bytes(r.read())
    return Image.open(io.BytesIO(dst.read_bytes())).convert("RGBA")


def fetch(source):
    base = SOURCES[source]; raw = OUT / "raw" / source; blocks = OUT / "blocks"; ent = OUT / "entity"
    blocks.mkdir(parents=True, exist_ok=True); ent.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, (rel, t) in BLOCK_FILES.items():
        im = first_frame(get(base, rel, raw))
        if t:
            im = tint(im, t)
        if name == "water":
            im.putalpha(200)
        im.save(blocks / f"{name}.png"); total += 1
    for name, rel in ENTITY_FILES.items():
        get(base, rel, raw).save(ent / f"{name}.png"); total += 1
    (blocks / "index.json").write_text(json.dumps({"blocks": INDEX}, indent=1))
    (OUT / "SOURCE.txt").write_text(f"source: {source}\nbase: {base}\nfiles: {total}\n"
                                    "These are Mojang's textures, cached for local rendering only. Do not commit or redistribute.\n")
    size = sum(f.stat().st_size for f in (OUT / "raw").rglob("*") if f.is_file())
    print(f"vanilla textures ready: {total} files from {source} ({size // 1024} KB downloaded) -> {OUT}")


SOUND_KEYS = [  # minecraft/sounds/<key>.ogg -> work/vanilla/sounds/<key>.wav (effects only: no music, it has its own rights holders)
    "ambient/weather/rain1", "ambient/weather/rain2", "ambient/weather/rain3", "ambient/weather/rain4",
    "ambient/weather/thunder1", "ambient/weather/thunder2", "ambient/weather/thunder3",
    "random/explode1", "random/explode2", "random/explode3", "random/explode4", "random/fuse",
    "random/door_open", "random/door_close", "random/chestopen", "random/chestclosed", "random/click", "random/levelup",
    "random/glass1", "random/pop", "random/orb", "random/bow", "random/eat1", "random/burp",
    "mob/zombie/say1", "mob/zombie/say2", "mob/zombie/say3", "mob/zombie/hurt1", "mob/zombie/hurt2", "mob/zombie/death",
    "mob/zombie/step1", "mob/creeper/say1", "mob/creeper/death", "mob/skeleton/say1", "mob/pig/say1", "mob/cow/say1",
    "mob/sheep/say1", "mob/chicken/say1", "mob/villager/idle1", "mob/villager/yes1", "mob/villager/no1",
    "damage/hit1", "damage/hit2", "damage/hit3", "damage/fallbig", "damage/fallsmall",
    "entity/player/attack/strong1", "entity/player/attack/strong2", "entity/player/attack/crit1",
    "entity/player/attack/sweep1", "entity/player/attack/knockback1", "entity/player/hurt/fire_hurt1",
    "fire/ignite", "fire/fire", "liquid/lava", "liquid/water", "liquid/splash",
    "dig/stone1", "dig/stone2", "dig/stone3", "dig/stone4", "dig/wood1", "dig/grass1", "dig/gravel1", "dig/sand1", "dig/glass1",
    "step/stone1", "step/stone2", "step/stone3", "step/grass1", "step/grass2", "step/wood1", "step/gravel1", "step/sand1",
]


def sounds():
    import subprocess
    def js(url):
        req = urllib.request.Request(url, headers={"User-Agent": "blockreel-vanilla-fetch"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    man = js("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    rel = man["latest"]["release"]; ver = js(next(v["url"] for v in man["versions"] if v["id"] == rel))
    objs = js(ver["assetIndex"]["url"])["objects"]
    out = OUT / "sounds"; raw = OUT / "raw" / "sounds"; got, miss, size = 0, [], 0
    for key in SOUND_KEYS:
        o = objs.get(f"minecraft/sounds/{key}.ogg")
        if not o:
            miss.append(key); continue
        ogg = raw / f"{key}.ogg"; wav = out / f"{key}.wav"
        if not ogg.exists():
            ogg.parent.mkdir(parents=True, exist_ok=True); h = o["hash"]
            req = urllib.request.Request(f"https://resources.download.minecraft.net/{h[:2]}/{h}", headers={"User-Agent": "blockreel-vanilla-fetch"})
            with urllib.request.urlopen(req, timeout=30) as r:
                ogg.write_bytes(r.read())
        size += ogg.stat().st_size; wav.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ogg), "-ar", "44100", "-ac", "2", str(wav)], check=True); got += 1
    (out / "SOURCE.txt").write_text(f"Minecraft Java {rel} asset index (piston-meta.mojang.com / resources.download.minecraft.net)\n"
                                    f"{got} sounds. Mojang's sounds, cached for local use only. Do not commit or redistribute.\n")
    print(f"vanilla sounds ready: {got} files from Java {rel} ({size // 1024} KB) -> {out}" + (f"; not in this version: {', '.join(miss)}" if miss else ""))


def status():
    if not (OUT / "blocks" / "index.json").exists():
        print("no vanilla cache: run  python tools/vanilla.py fetch"); return 1
    print((OUT / "SOURCE.txt").read_text()); return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch"); f.add_argument("--source", choices=sorted(SOURCES), default="mojang")
    sub.add_parser("status"); sub.add_parser("sounds")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        fetch(a.source); return 0
    if a.cmd == "sounds":
        sounds(); return 0
    return status()


if __name__ == "__main__":
    sys.exit(main())
