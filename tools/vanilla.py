#!/usr/bin/env python3
"""Fetch the ORIGINAL Minecraft textures into a local cache, so films look like the game by default.

  python tools/vanilla.py fetch                 # Mojang's official Bedrock samples (default)
  python tools/vanilla.py fetch --source ztech  # mirror: github.com/ZtechNetwork/MCBVanillaResourcePack
  python tools/vanilla.py sounds                # original sound effects (Java asset index, official Mojang servers)
  python tools/vanilla.py font                  # the game's bitmap font (read from client.jar with HTTP ranges, ~1 MB)
  python tools/vanilla.py mobs                  # every mob's own geometry + texture (cow, villager, skeleton, horse, dragon...)
  python tools/vanilla.py equipment             # armour, elytra and shield textures (client.jar, HTTP ranges)
  python tools/vanilla.py all                   # everything above
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
import re
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
    # v0.2: plants, light sources and more building blocks (names match core/builtin/blocks so index.json works for both)
    "tall_grass": ("textures/blocks/tallgrass.png", GRASS), "flower_red": ("textures/blocks/flower_rose.png", None),
    "flower_yellow": ("textures/blocks/flower_dandelion.png", None), "torch": ("textures/blocks/torch_on.png", None),
    "redstone_torch": ("textures/blocks/redstone_torch_on.png", None), "netherrack": ("textures/blocks/netherrack.png", None),
    "mossy_cobble": ("textures/blocks/cobblestone_mossy.png", None), "stonebrick_mossy": ("textures/blocks/stonebrick_mossy.png", None),
    "stonebrick_cracked": ("textures/blocks/stonebrick_cracked.png", None), "birch_log": ("textures/blocks/log_birch.png", None),
    "birch_log_top": ("textures/blocks/log_birch_top.png", None), "birch_leaves": ("textures/blocks/leaves_birch_carried.tga", None),
    "spruce_log": ("textures/blocks/log_spruce.png", None), "spruce_log_top": ("textures/blocks/log_spruce_top.png", None),
    "spruce_leaves": ("textures/blocks/leaves_spruce_carried.tga", None), "iron_block": ("textures/blocks/iron_block.png", None),
    "redstone_block": ("textures/blocks/redstone_block.png", None), "emerald_block": ("textures/blocks/emerald_block.png", None),
    "sandstone": ("textures/blocks/sandstone_normal.png", None), "sandstone_top": ("textures/blocks/sandstone_top.png", None),
    "soul_sand": ("textures/blocks/soul_sand.png", None), "ice": ("textures/blocks/ice.png", None),
    "blackstone": ("textures/blocks/blackstone.png", None), "crying_obsidian": ("textures/blocks/crying_obsidian.png", None),
    "magma": ("textures/blocks/magma.png", None), "end_stone": ("textures/blocks/end_stone.png", None),
    "dead_bush": ("textures/blocks/deadbush.png", None), "mushroom_red": ("textures/blocks/mushroom_red.png", None),
    "mushroom_brown": ("textures/blocks/mushroom_brown.png", None), "sapling": ("textures/blocks/sapling_oak.png", None),
    "quartz": ("textures/blocks/quartz_block_side.png", None), "nether_bricks": ("textures/blocks/nether_brick.png", None),
    "coal_ore": ("textures/blocks/coal_ore.png", None), "iron_ore": ("textures/blocks/iron_ore.png", None),
    "gold_ore": ("textures/blocks/gold_ore.png", None), "diamond_ore": ("textures/blocks/diamond_ore.png", None),
    "redstone_ore": ("textures/blocks/redstone_ore.png", None), "bookshelf": ("textures/blocks/bookshelf.png", None),
    "furnace_front": ("textures/blocks/furnace_front_off.png", None), "furnace_side": ("textures/blocks/furnace_side.png", None),
    "furnace_top": ("textures/blocks/furnace_top.png", None), "pumpkin_side": ("textures/blocks/pumpkin_side.png", None),
    "pumpkin_top": ("textures/blocks/pumpkin_top.png", None), "jack_o_lantern": ("textures/blocks/pumpkin_face_on.png", None),
    "hay_side": ("textures/blocks/hay_block_side.png", None), "hay_top": ("textures/blocks/hay_block_top.png", None),
    "sea_lantern": ("textures/blocks/sea_lantern.png", None), "spruce_planks": ("textures/blocks/planks_spruce.png", None),
    "birch_planks": ("textures/blocks/planks_birch.png", None), "dark_oak_planks": ("textures/blocks/planks_big_oak.png", None),
    "dark_oak_log": ("textures/blocks/log_big_oak.png", None), "wool_black": ("textures/blocks/wool_colored_black.png", None),
    "wool_gray": ("textures/blocks/wool_colored_gray.png", None), "concrete_black": ("textures/blocks/concrete_black.png", None),
    "clay": ("textures/blocks/clay.png", None), "mycelium_top": ("textures/blocks/mycelium_top.png", None),
    "fire": ("textures/blocks/fire_0.png", None), "beacon": ("textures/blocks/beacon.png", None),
    "cactus_side": ("textures/blocks/cactus_side.tga", None), "cactus_top": ("textures/blocks/cactus_top.tga", None),
    # v0.3: doors, ladders, rails, panes, crops, paths, beds
    "door_lower": ("textures/blocks/door_wood_lower.png", None), "door_upper": ("textures/blocks/door_wood_upper.png", None),
    "spruce_door_lower": ("textures/blocks/door_spruce_lower.png", None), "spruce_door_upper": ("textures/blocks/door_spruce_upper.png", None),
    "iron_door_lower": ("textures/blocks/door_iron_lower.png", None), "iron_door_upper": ("textures/blocks/door_iron_upper.png", None),
    "trapdoor": ("textures/blocks/trapdoor.png", None), "ladder": ("textures/blocks/ladder.png", None), "vine": ("textures/blocks/vine.png", FOLIAGE),
    "rail": ("textures/blocks/rail_normal.png", None), "rail_golden": ("textures/blocks/rail_golden.png", None), "iron_bars": ("textures/blocks/iron_bars.png", None),
    "wheat": ("textures/blocks/wheat_stage_7.png", None), "wheat_young": ("textures/blocks/wheat_stage_3.png", None),
    "carrots": ("textures/blocks/carrots_stage_3.png", None), "potatoes": ("textures/blocks/potatoes_stage_3.png", None), "beetroots": ("textures/blocks/beetroots_stage_3.png", None),
    "dirt_path_top": ("textures/blocks/grass_path_top.png", None), "dirt_path_side": ("textures/blocks/grass_path_side.png", None),
    "farmland": ("textures/blocks/farmland_wet.png", None), "bed_head_top": ("textures/blocks/bed_head_top.png", None),
    "bed_feet_top": ("textures/blocks/bed_feet_top.png", None), "bed_side": ("textures/blocks/bed_head_side.png", None),
    "melon_side": ("textures/blocks/melon_side.png", None), "melon_top": ("textures/blocks/melon_top.png", None), "soul_torch": ("textures/blocks/soul_torch.png", None),
}
ITEM_FILES = {  # engine item name -> file in the pack (held items, extruded into 3D by the engine)
    "wooden_sword": "wood_sword", "stone_sword": "stone_sword", "iron_sword": "iron_sword", "golden_sword": "gold_sword",
    "diamond_sword": "diamond_sword", "netherite_sword": "netherite_sword",
    "wooden_pickaxe": "wood_pickaxe", "stone_pickaxe": "stone_pickaxe", "iron_pickaxe": "iron_pickaxe", "golden_pickaxe": "gold_pickaxe",
    "diamond_pickaxe": "diamond_pickaxe", "netherite_pickaxe": "netherite_pickaxe",
    "wooden_axe": "wood_axe", "stone_axe": "stone_axe", "iron_axe": "iron_axe", "golden_axe": "gold_axe", "diamond_axe": "diamond_axe",
    "netherite_axe": "netherite_axe", "iron_shovel": "iron_shovel", "diamond_shovel": "diamond_shovel",
    "bow": "bow_standby", "bow_pulling": "bow_pulling_2", "arrow": "arrow", "stick": "stick", "apple": "apple", "totem": "totem",
    "ender_pearl": "ender_pearl", "blaze_rod": "blaze_rod", "flint_and_steel": "flint_and_steel", "trident": "trident",
    "mace": "mace", "fishing_rod": "fishing_rod_uncast", "enchanted_book": "book_enchanted", "torch": "../blocks/torch_on",
}
ENV_FILES = {"sun": "textures/environment/sun.png", "moon_phases": "textures/environment/moon_phases.png",
             "clouds": "textures/environment/clouds.png"}
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
    "birch_log": {"top": "birch_log_top", "side": "birch_log", "bottom": "birch_log_top"},
    "spruce_log": {"top": "spruce_log_top", "side": "spruce_log", "bottom": "spruce_log_top"},
    "dark_oak_log": {"top": "log_top", "side": "dark_oak_log", "bottom": "log_top"},
    "sandstone": {"top": "sandstone_top", "side": "sandstone", "bottom": "sandstone_top"},
    "furnace": {"top": "furnace_top", "side": "furnace_side", "bottom": "furnace_top", "front": "furnace_front"},
    "pumpkin": {"top": "pumpkin_top", "side": "pumpkin_side", "bottom": "pumpkin_top"},
    "jack_o_lantern": {"top": "pumpkin_top", "side": "pumpkin_side", "bottom": "pumpkin_top", "front": "jack_o_lantern", "light": 15},
    "hay": {"top": "hay_top", "side": "hay_side", "bottom": "hay_top"},
    "sea_lantern": {"all": "sea_lantern", "emissive": True, "light": 15},
    "cactus": {"top": "cactus_top", "side": "cactus_side", "bottom": "cactus_top", "shape": "cactus"},
    "mycelium": {"top": "mycelium_top", "side": "dirt", "bottom": "dirt"},
    "dead_bush": {"all": "dead_bush", "shape": "cross"}, "mushroom_red": {"all": "mushroom_red", "shape": "cross"},
    "mushroom_brown": {"all": "mushroom_brown", "shape": "cross", "light": 1}, "sapling": {"all": "sapling", "shape": "cross"},
    "fire": {"all": "fire", "shape": "cross", "emissive": True, "light": 15, "flow": [0, 0.6]},
    "stonebrick_mossy": "stonebrick_mossy", "mossy_stone_bricks": "stonebrick_mossy", "stonebrick_cracked": "stonebrick_cracked",
    "emerald_block": "emerald_block", "end_stone": "end_stone", "quartz": "quartz", "nether_bricks": "nether_bricks",
    "coal_ore": "coal_ore", "iron_ore": "iron_ore", "gold_ore": "gold_ore", "diamond_ore": "diamond_ore", "redstone_ore": "redstone_ore",
    "bookshelf": {"top": "planks", "side": "bookshelf", "bottom": "planks"}, "beacon": {"all": "beacon", "light": 15},
    "spruce_planks": "spruce_planks", "birch_planks": "birch_planks", "dark_oak_planks": "dark_oak_planks",
    "melon": {"top": "melon_top", "side": "melon_side", "bottom": "melon_top"}, "soul_torch": {"all": "soul_torch", "shape": "torch", "light": 10},
    "spruce_door": {"top": "spruce_door_upper", "side": "spruce_door_lower", "shape": "door"}, "iron_door": {"top": "iron_door_upper", "side": "iron_door_lower", "shape": "door"},
    "rail_golden": {"all": "rail_golden", "shape": "rail"},
    "wool_black": "wool_black", "wool_gray": "wool_gray", "concrete_black": "concrete_black", "clay": "clay",
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
    items = OUT / "items"; env = OUT / "env"; items.mkdir(exist_ok=True); env.mkdir(exist_ok=True)
    for name, f in ITEM_FILES.items():
        try:
            first_frame(get(base, f"textures/items/{f}.png" if not f.startswith("..") else f"textures/blocks/{f[10:]}.png", raw)).save(items / f"{name}.png"); total += 1
        except Exception as e:  # an item missing upstream falls back to the CC0 built-in sprite
            print(f"  (item {name}: {e}; the built-in sprite is used)")
    for name, rel in ENV_FILES.items():
        im = get(base, rel, raw)
        if name == "moon_phases":  # 4x2 grid of phases: phase 0 (full moon) is the top-left cell
            im.crop((0, 0, im.width // 4, im.height // 2)).save(env / "moon.png")
        im.save(env / f"{name}.png"); total += 1
    builtin = json.loads((ROOT / "core" / "builtin" / "blocks" / "index.json").read_text())["blocks"]
    merged = {**{k: v for k, v in builtin.items() if k not in INDEX}, **INDEX}
    for k in ("glowstone", "lava", "water"):  # keep light / liquid flags from the built-in definitions
        if isinstance(merged[k], dict) and isinstance(builtin.get(k), dict):
            merged[k] = {**builtin[k], **merged[k]}
    (blocks / "index.json").write_text(json.dumps({"blocks": merged}, indent=1))
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
    # v0.2: combat and the supernatural (teleports, cave ambience, shields, boss stings)
    "step/grass3", "step/grass4", "entity/player/attack/weak1", "entity/player/attack/strong3", "entity/player/attack/crit2",
    "entity/player/attack/sweep2", "item/shield/block1", "item/shield/block2", "random/anvil_land",
    "mob/endermen/portal", "mob/endermen/portal2", "mob/endermen/stare", "mob/endermen/scream1", "mob/wither/spawn", "mob/wither/shoot",
    "ambient/cave/cave1", "ambient/cave/cave13", "ambient/cave/cave7", "mob/ghast/moan1", "random/totem_use", "item/trident/thunder1",
    # v0.3: celebrations, animals and village life
    "fireworks/launch1", "fireworks/blast1", "fireworks/largeblast1", "fireworks/twinkle1", "fireworks/twinkle_far1", "item/totem/use_totem",
    "mob/cow/say2", "mob/pig/say2", "mob/sheep/say2", "mob/chicken/say2", "mob/wolf/bark1", "mob/cat/meow1", "mob/horse/idle1", "mob/horse/gallop1",
    "mob/villager/haggle1", "mob/irongolem/hit1", "mob/enderdragon/growl1", "mob/wither/idle1", "mob/skeleton/hurt1", "mob/spider/say1",
    "random/drink", "random/eat2", "random/break", "random/splash", "liquid/swim1", "step/ladder1", "dig/cloth1", "random/door_open",
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



# ---------------------------------------------------------------------------------------------------- mobs ----
# Every mob with the game's own geometry: Mojang's bedrock-samples ship each entity's client definition (which geometry and
# texture it uses) and the geometry files (bones, cubes, pivots, UVs). They are normalised into work/vanilla/mobs/<mob>.geo.json
# + <mob>.png, which the engine builds into a rig (core/engine/geo.js) and animates by bone names.
MOB_ENTITIES = {  # engine name -> entity file in bedrock-samples/resource_pack/entity
    "cow": "cow", "pig": "pig", "sheep": "sheep", "chicken": "chicken", "wolf": "wolf", "cat": "cat", "ocelot": "ocelot", "fox": "fox",
    "horse": "horse_v3", "donkey": "donkey_v3", "skeleton_horse": "skeleton_horse_v3", "zombie_horse": "zombie_horse_v3",
    "rabbit": "rabbit", "llama": "llama", "goat": "goat", "mooshroom": "mooshroom", "panda": "panda", "polar_bear": "polar_bear",
    "villager": "villager_v2", "zombie_villager": "zombie_villager_v2", "witch": "witch", "pillager": "pillager", "vindicator": "vindicator",
    "evoker": "evoker", "iron_golem": "iron_golem", "snow_golem": "snow_golem", "allay": "allay",
    "skeleton": "skeleton", "stray": "stray", "wither_skeleton": "wither_skeleton", "zombie": "zombie", "husk": "husk", "drowned": "drowned",
    "zombie_pigman": "zombie_pigman", "piglin": "piglin", "hoglin": "hoglin", "creeper": "creeper", "spider": "spider", "cave_spider": "cave_spider",
    "enderman": "enderman", "endermite": "endermite", "silverfish": "silverfish", "slime": "slime", "magma_cube": "magma_cube", "ghast": "ghast",
    "blaze": "blaze", "bat": "bat", "bee": "bee", "parrot": "parrot", "phantom": "phantom", "vex": "vex", "guardian": "guardian",
    "ravager": "ravager", "shulker": "shulker", "warden": "warden", "ender_dragon": "ender_dragon", "wither": "wither",
    "axolotl": "axolotl", "frog": "frog", "squid": "squid", "glow_squid": "glow_squid", "dolphin": "dolphin", "turtle": "turtle", "cod": "cod",
    "salmon": "salmon", "camel": "camel", "sniffer": "sniffer", "strider": "strider", "breeze": "breeze", "armadillo": "armadillo",
    "minecart": "minecart", "boat": "boat", "armor_stand": "armor_stand",
}
GEO_FILES = """allay armadillo armor_stand arrow axolotl bat bat_v2 bee blaze bogged breeze camel cat chicken chicken.cold cod cow cow.cold cow.v2 cow.warm
cow_v1.0 creaking creeper creeper.v1.0 dolphin drowned drowned_v1.0 ender_crystal ender_dragon enderman enderman_v1.0 endermite evoker evoker_v1.0
fox frog ghast glow_squid goat guardian guardian.v1.0 happy_ghast hoglin horse_v1 horse_v2 horse_v3 humanoid.custom husk husk.v1.0 iron_golem llama
llama_v1.0 magma_cube magma_cube_v2 minecart minecart_v1.0 mooshroom mooshroom.v2 mooshroom_v1.0 ocelot ocelot_v1.0 panda parrot phantom pig pig.v3
pig_v1.0 piglin pillager polar_bear pufferfish rabbit rabbit.v2 rabbit_v1.0 ravager salmon sheep sheep_v1.0 shield shulker shulker_v1.0 silverfish
skeleton skeleton.v1.0 slime sniffer snow_golem snow_golem.v1.0 spider spider_v1.0 squid stray stray_v1.0 strider tropical_fish turtle vex vex.v1.0
villager villager_v1.0 villager_v2 vindicator vindicator_v1.0 warden witch witch_v1.0 wither_boss wither_skeleton wither_skeleton.v1.0 wolf zombie
zombie.v1.0 zombie_pigman zombie_pigman.v1.0 zombie_villager zombie_villager.v1.0 zombie_villager_v2
baby_armadillo baby_axolotl baby_bee baby_camel baby_cat baby_chicken baby_cow baby_dolphin baby_fox baby_goat baby_hoglin baby_horse
baby_llama baby_panda baby_pig baby_piglin baby_polar_bear baby_rabbit baby_sheep baby_squid baby_strider baby_turtle baby_villager
baby_wolf baby_zombie baby_zombie_villager""".split()


ANIM_FILES = """actor.animation.json agent.animation.json allay.animation.json armadillo.animation.json armor.animation.json armor_stand.animation.json arrow.animation.json axolotl.animation.json bat.animation.json bee.animation.json blaze.animation.json bow.animation.json breeze.animation.json camel.animation.json cat.animation.json chicken.animation.json cod.animation.json copper_golem.animation.json cow.animation.json creaking.animation.json creeper.animation.json crossbow.animation.json dolphin.animation.json drowned.animation.json drowned.animation.v1.0.json elytra.animation.json ender_crystal.animation.json ender_dragon.animation.json enderman.animation.json enderman.animation.v1.0.json endermite.animation.json evocation_fang.animation.json evoker.animation.json fireworks_rocket.animation.json fox.animation.json frog.animation.json ghast.animation.json goat.animation.json guardian.animation.json guardian.animation.v1.0.json happy_ghast.animation.json hoglin.animation.json horse_v1.animation.json horse_v2.animation.json horse_v3.animation.json humanoid.animation.json iron_golem.animation.json llama.animation.json llama_spit.animation.json look_at_target.animation.json magma_cube.animation.json minecart.animation.json minecart.animation.v1.0.json mooshroom.animation.json nautilus.animation.json npc.animation.json ocelot.animation.json ocelot.animations.v1.0.json panda.animation.json parrot.animation.json phantom.animation.json pig.animation.json piglin.animation.json pillager.animation.json player.animation.json player_firstperson.animation.json polar_bear.animation.json pufferfish.animation.json quadruped.animation.json rabbit.animation.json rabbit.v2.animation.json ravager.animation.json salmon.animation.json sheep.animation.json shield.animation.json shulker.animation.json shulker.animations.v1.0.json shulker_bullet.animation.json silverfish.animation.json skeleton.animation.json skeleton.animations.v1.0.json sniffer.animation.json snow_golem.animation.json snow_golem.animations.v1.0.json spear.animation.json spider.animation.json spyglass.animation.json squid.animation.json strider.animation.json sulfur_cube.animation.json tadpole.animation.json trident.animation.json tripod_camera.animation.json tropicalfish.animation.json turtle.animation.json turtle.animations.json vex.animation.json villager.animation.json vindicator.animation.json warden.animation.json wind_charge.animation.json witch.animation.json wither_boss.animation.json wither_skeleton.animation.json wither_skull.animation.json wolf.animations.json zombie.animation.json""".split()


def _anim_index(base, raw):
    """animation id -> animation definition, from every animation file of the samples."""
    idx = {}
    for fn in ANIM_FILES:
        rel = f"animations/{fn}"; dst = raw / rel
        try:
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                req = urllib.request.Request(base + rel, headers={"User-Agent": "blockreel-vanilla-fetch"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    dst.write_bytes(r.read())
            d = _loose_json(dst.read_text(encoding="utf-8", errors="replace"))
            idx.update(d.get("animations", {}))
        except Exception:
            continue
    return idx


# mobs whose game animations set absolute poses for a legacy rig (they fight our rest pose): animated procedurally instead
MOLANG_SKIP = {"wolf", "polar_bear", "ender_dragon"}
MOLANG_ABS_POS = {"guardian", "elder_guardian"}  # their animations write absolute pivots (the spikes)
MOB_FIXES = {"polar_bear": {"body": [90, 0, 0]}, "llama": {"body": [90, 0, 0]}, "trader_llama": {"body": [90, 0, 0]}, "cat": {"body": [90, 0, 0]}, "ocelot": {"body": [90, 0, 0]}}


def _loose_json(t):
    import re
    t = re.sub(r'(?m)^\s*//.*$', '', t); t = re.sub(r'(?<![:"])//[^\n"]*$', '', t, flags=re.M)
    return json.loads(t)


def _geo_index(base, raw):
    """identifier -> (geometry dict, parent identifier or None), from mobs.json and every .geo.json file."""
    idx = {}
    def take(ident, g):
        name, _, parent = ident.partition(":")
        idx[name] = (g, parent or None)
    files = ["models/mobs.json"] + [f"models/entity/{n}.geo.json" for n in GEO_FILES]
    for rel in files:
        dst = raw / rel
        try:
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                req = urllib.request.Request(base + rel, headers={"User-Agent": "blockreel-vanilla-fetch"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    dst.write_bytes(r.read())
            d = _loose_json(dst.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        for k, v in d.items():
            if k == "minecraft:geometry":
                for g in v:
                    take(g["description"]["identifier"], {"bones": g.get("bones", []), "tw": g["description"].get("texture_width", 64), "th": g["description"].get("texture_height", 64)})
            elif k.startswith("geometry.") and isinstance(v, dict):
                take(k, {"bones": v.get("bones", []), "tw": v.get("texturewidth", 64), "th": v.get("textureheight", 64)})
    return idx


def _resolve(idx, ident, depth=0):
    g, parent = idx[ident]
    if not parent or parent not in idx or depth > 6:
        return {"bones": [dict(b) for b in g["bones"]], "tw": g["tw"], "th": g["th"]}
    base = _resolve(idx, parent, depth + 1); bones = {b["name"].lower(): b for b in base["bones"]}; order = [b["name"].lower() for b in base["bones"]]
    for b in g["bones"]:  # a child geometry overrides bones by name and adds new ones
        k = b["name"].lower()
        bones[k] = {**bones.get(k, {}), **b}
        if k not in order:
            order.append(k)
    tw = g["tw"] if g["bones"] or not base["tw"] else base["tw"]
    return {"bones": [bones[k] for k in order], "tw": g.get("tw") or base["tw"], "th": g.get("th") or base["th"]}


VARIANT_SKIP = re.compile(r"saddle|decor|marking|armou?r|harness|chest|collar|leash|eyes|glow|overlay|invisible|charged|ghost|beam|crack"
                          r"|dissolve|layer|outer|clothes|sleep|shear|tame|angry|spawn|blink|emissive|wind|crying|zombified|profession|level")


LAYERED = {"villager", "zombie_villager"}
BIOMES = {"desert", "jungle", "plains", "savanna", "snow", "swamp", "taiga"}


def _mob_tex(base, raw, tpath):
    for ext in (".png", ".tga"):
        try:
            return get(base, tpath + ext, raw).convert("RGBA")
        except Exception:
            continue
    return None


def _layer(img, *overs):
    for o in overs:
        if o is not None and o.size == img.size:
            img = Image.alpha_composite(img, o)
    return img


def _coverage(img):
    return sum(1 for v in img.getchannel("A").getdata() if v > 0)


def _save_skin(img, dst):
    """Write a mob texture. Emissive-alpha materials (blaze, magma cube, glow squid) keep the glow in the alpha channel: the skin is
    written opaque and the glow (colour x alpha, like the game's lerp to unlit) next to it as <name>.glow.png. Returns True for those."""
    a = img.getchannel("A"); glow = 0 < a.getextrema()[1] < 255
    if glow:
        from PIL import ImageChops
        ImageChops.multiply(img.convert("RGB"), Image.merge("RGB", [a, a, a])).save(dst.with_suffix(".glow.png"))
        img = img.copy(); img.putalpha(255)
    img.save(dst); return glow


def mobs(source="mojang"):
    base = SOURCES[source]; raw = OUT / "raw" / source; out = OUT / "mobs"; out.mkdir(parents=True, exist_ok=True)
    idx = _geo_index(base, raw); aidx = _anim_index(base, raw); done, missing = {}, []
    for name, ent in MOB_ENTITIES.items():
        try:
            rel = f"entity/{ent}.entity.json"; dst = raw / rel
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                req = urllib.request.Request(base + rel, headers={"User-Agent": "blockreel-vanilla-fetch"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    dst.write_bytes(r.read())
            desc = _loose_json(dst.read_text(encoding="utf-8", errors="replace"))["minecraft:client_entity"]["description"]
            geos = desc.get("geometry", {}); texs = desc.get("textures", {})
            gid = geos.get("default") or next(iter(geos.values())); tpath = texs.get("default") or next(iter(texs.values()))
            if gid not in idx:
                missing.append(f"{name} (geometry {gid})"); continue
            anims = {k: aidx[v] for k, v in (desc.get("animations") or {}).items() if isinstance(v, str) and v in aidx}
            sc = desc.get("scripts") or {}

            def build(g_id, fixes=True):
                geo = _resolve(idx, g_id)
                for bone, r in (MOB_FIXES.get(name, {}) if fixes else {}).items():  # poses the game sets in code, not in the geometry
                    for b in geo["bones"]:
                        if b["name"].lower() == bone and not b.get("rotation") and not b.get("bind_pose_rotation"):
                            b["bind_pose_rotation"] = r
                geo["entity"] = ent; geo["geometry"] = g_id
                if anims and name not in MOLANG_SKIP:  # the game's animations for this mob (Molang), evaluated by core/engine/molang.js
                    geo["anims"] = anims; geo["animate"] = sc.get("animate") or list(anims.keys()); geo["absPos"] = name in MOLANG_ABS_POS
                    geo["pre"] = [x for x in (sc.get("initialize") or []) + (sc.get("pre_animation") or []) if isinstance(x, str)]
                return geo

            img = _mob_tex(base, raw, tpath)
            if img is None:
                missing.append(f"{name} (texture {tpath})"); continue
            layered = name in LAYERED  # villagers: a bare skin, the biome's clothes and the profession's, layered like the game
            if layered:
                bare = {False: img, True: None}; clothes = {}
                for key, path in texs.items():
                    k = key[5:] if key.startswith("baby_") else key
                    if isinstance(path, str) and k in ("default", "base", "plains"):
                        im = _mob_tex(base, raw, path)
                        if im is not None:
                            (bare if k != "plains" else clothes)[key.startswith("baby_")] = im
                if clothes.get(False) is not None:
                    img = _layer(img, clothes[False])
            geo = build(gid); geo["texture"] = f"{name}.png"
            if _save_skin(img, out / f"{name}.png"):
                geo["glow"] = f"{name}.glow.png"
            (out / f"{name}.geo.json").write_text(json.dumps(geo))
            entry = {"geo": f"{name}.geo.json", "texture": f"{name}.png"}
            # variants (cat breeds, wolf and rabbit coats, warm/cold cows...) and the game's own baby models and textures
            full = _coverage(img); seen = {(False, tpath)}; variants, babies = {}, {}
            adult = next((k for k, p in texs.items() if p == tpath), "default").removeprefix("base_").removesuffix("_default")
            for key, path in texs.items():
                baby = key == "baby" or key.startswith("baby_")
                if not isinstance(path, str) or (baby, path) in seen or VARIANT_SKIP.search(key):
                    continue
                v = key[5:] if key.startswith("baby_") else ("default" if baby else key)
                v = v[:-8] if v.endswith("_default") else v; v = v[5:] if v.startswith("base_") else v
                im = _mob_tex(base, raw, path)
                if layered and im is not None:
                    if re.fullmatch(r"base\d*|default", v) or bare[baby] is None:
                        continue
                    if v == "plains":
                        v = "default" if baby else "plains"
                    im = _layer(bare[baby], im) if v in BIOMES or v == "default" else _layer(bare[baby], clothes.get(baby), im)  # a profession: on plains clothes
                elif im is None or not baby and (im.size != img.size or _coverage(im) < full * 0.6):  # overlays (markings, biome cloth) are not skins
                    continue
                seen.add((baby, path)); fn = f"{name}.{'baby.' if baby else ''}{v}.png"; _save_skin(im, out / fn)
                if baby:
                    babies[v] = fn
                else:
                    variants[v] = {"texture": fn}
                    if geos.get(key) and geos[key] != gid and geos[key] in idx:  # a variant with its own shape (cold cow, cold chicken)
                        vg = build(geos[key]); vg["texture"] = fn; (out / f"{name}.{v}.geo.json").write_text(json.dumps(vg)); variants[v]["geo"] = f"{name}.{v}.geo.json"
            if variants:
                entry["variants"] = variants
            if geos.get("baby") in idx:
                bg = build(geos["baby"], fixes=False); bg["nativeBaby"] = True; btex = babies.pop("default", None) or babies.get(adult) or (next(iter(babies.values())) if babies else None)
                if btex or (bg.get("tw"), bg.get("th")) == (geo.get("tw"), geo.get("th")):  # no baby texture: the adult's, when the layout matches
                    bg["texture"] = btex or f"{name}.png"; (out / f"{name}.baby.geo.json").write_text(json.dumps(bg))
                    entry["baby"] = {"geo": f"{name}.baby.geo.json", "texture": bg["texture"], **({"variants": babies} if babies else {})}
            done[name] = entry
        except Exception as e:
            missing.append(f"{name} ({e})")
    (out / "index.json").write_text(json.dumps({"mobs": done}, indent=1))
    print(f"vanilla mobs ready: {len(done)} mobs with the game's geometry -> {out}" + (f"; skipped: {', '.join(missing)}" if missing else ""))
    return 0


# ---------------------------------------------------------------------------------------------------- font ----
def _zip_member(url, size, names):
    """Read a few members of a remote zip (the game's client.jar, ~40 MB) with HTTP Range requests: ~1 MB instead of 40."""
    import struct, zlib
    def rng(a, b):
        req = urllib.request.Request(url, headers={"User-Agent": "blockreel-vanilla-fetch", "Range": f"bytes={a}-{b}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    tail = rng(max(0, size - 66000), size - 1); i = tail.rfind(b"PK\x05\x06")
    cd_size, cd_off = struct.unpack("<II", tail[i + 12:i + 20])
    cd = rng(cd_off, cd_off + cd_size - 1); out = {}; p = 0
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        meth, = struct.unpack("<H", cd[p + 10:p + 12]); csz, usz = struct.unpack("<II", cd[p + 20:p + 28])
        nl, el, cl = struct.unpack("<HHH", cd[p + 28:p + 34]); lho, = struct.unpack("<I", cd[p + 42:p + 46])
        name = cd[p + 46:p + 46 + nl].decode("utf-8", "replace"); p += 46 + nl + el + cl
        if name in names:
            h = rng(lho, lho + 29); fnl, fel = struct.unpack("<HH", h[26:30]); start = lho + 30 + fnl + fel
            data = rng(start, start + csz - 1)
            out[name] = zlib.decompress(data, -15) if meth == 8 else data
    return out


def font():
    """The game's own bitmap font (ascii + accented glyphs) for name tags, chat subtitles and titles -> work/vanilla/font/."""
    def js(u):
        req = urllib.request.Request(u, headers={"User-Agent": "blockreel-vanilla-fetch"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    man = js("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    rel = man["latest"]["release"]; ver = js(next(v["url"] for v in man["versions"] if v["id"] == rel))
    url, size = ver["downloads"]["client"]["url"], ver["downloads"]["client"]["size"]
    cands = ["assets/minecraft/font/include/default.json", "assets/minecraft/font/default.json"]
    got = _zip_member(url, size, set(cands)); fdef = next((json.loads(got[c]) for c in cands if c in got), None)
    if not fdef:
        print("font definition not found in the client jar"); return 1
    provs = [pr for pr in fdef.get("providers", []) if pr.get("type") == "bitmap" and pr["file"].split(":")[-1] in ("font/ascii.png", "font/accented.png", "font/nonlatin_european.png")]
    files = {"assets/minecraft/textures/" + pr["file"].split(":")[-1]: pr for pr in provs}
    data = _zip_member(url, size, set(files)); out = OUT / "font"; out.mkdir(parents=True, exist_ok=True); meta = []
    for path, pr in files.items():
        if path not in data:
            continue
        fn = Path(path).name; (out / fn).write_bytes(data[path])
        meta.append({"file": fn, "height": pr.get("height", 8), "ascent": pr["ascent"], "chars": pr["chars"]})
    (out / "font.json").write_text(json.dumps({"version": rel, "providers": meta}, ensure_ascii=False))
    (out / "SOURCE.txt").write_text(f"Minecraft Java {rel} client.jar (read with HTTP ranges). Mojang's font: local use only, never commit.\n")
    print(f"vanilla font ready: {len(meta)} glyph sheets from Java {rel} -> {out}"); return 0


EQUIPMENT = ["humanoid/" + m for m in ("leather", "leather_overlay", "chainmail", "iron", "gold", "diamond", "netherite", "turtle_scute", "copper")] + \
            ["humanoid_leggings/" + m for m in ("leather", "leather_overlay", "chainmail", "iron", "gold", "diamond", "netherite", "copper")] + ["wings/elytra"]


def equipment():
    """Armour layers, the elytra and the shield from the game's client.jar (HTTP ranges, ~100 KB) -> work/vanilla/equipment/."""
    def js(u):
        req = urllib.request.Request(u, headers={"User-Agent": "blockreel-vanilla-fetch"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    man = js("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    rel = man["latest"]["release"]; ver = js(next(v["url"] for v in man["versions"] if v["id"] == rel))
    url, size = ver["downloads"]["client"]["url"], ver["downloads"]["client"]["size"]
    want = {f"assets/minecraft/textures/entity/equipment/{e}.png": e for e in EQUIPMENT}
    want["assets/minecraft/textures/entity/shield/shield_base_nopattern.png"] = "shield"
    data = _zip_member(url, size, set(want)); out = OUT / "equipment"; n = 0
    for path, name in want.items():
        if path in data:
            dst = out / f"{name}.png"; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(data[path]); n += 1
    print(f"vanilla equipment ready: {n} textures (armour, elytra, shield) from Java {rel} -> {out}"); return 0


def status():
    if not (OUT / "blocks" / "index.json").exists():
        print("no vanilla cache: run  python tools/vanilla.py fetch"); return 1
    print((OUT / "SOURCE.txt").read_text()); return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch"); f.add_argument("--source", choices=sorted(SOURCES), default="mojang")
    sub.add_parser("status"); sub.add_parser("sounds"); sub.add_parser("font"); sub.add_parser("mobs"); sub.add_parser("equipment")
    sub.add_parser("all", help="fetch + sounds + font")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        fetch(a.source); return 0
    if a.cmd == "sounds":
        sounds(); return 0
    if a.cmd == "font":
        return font()
    if a.cmd == "mobs":
        return mobs()
    if a.cmd == "equipment":
        return equipment()
    if a.cmd == "all":
        fetch("mojang"); sounds(); mobs(); equipment(); return font()
    return status()


if __name__ == "__main__":
    sys.exit(main())
