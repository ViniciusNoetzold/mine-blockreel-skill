#!/usr/bin/env python3
"""BlockReel resource-pack builder: your custom textures -> a pack the game can load.

  python core/pack.py build my_textures/ --name "My Pack" --pack-format <N> --out build/              # versions up to 1.21.8
  python core/pack.py build my_textures/ --name "My Pack" --min-format <N> --max-format <M> --out build/ # 1.21.9 and newer
  python core/pack.py check my_textures/

my_textures/ mirrors assets/minecraft/textures/, e.g.
  block/stone.png   block/grass_block_top.png   item/diamond_sword.png   entity/...

The format number has NO default on purpose: it changes with game versions. Look up the RESOURCE PACK value for your version on the
Minecraft Wiki "Pack format" page (https://minecraft.wiki/w/Pack_format) first, and pass --format-version / --format-source so the
pack's README.txt records where the number came from. Since 25w31a (Java 1.21.9) the wiki says packs use min_format / max_format
instead of pack_format. Versions listed with a decimal (for example 97.1) are not supported here: I could not confirm how to write them.
Custom *player skins* are not part of a resource pack: see docs/SKINS.md.
"""
import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image

NAME_RE = re.compile(r"^[a-z0-9/._-]+$")


def check(src):
    src = Path(src)
    problems, count = [], 0
    for f in sorted(src.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(src).as_posix()
        if f.suffix == ".mcmeta":
            try:
                json.loads(f.read_text())
            except Exception as e:  # noqa: BLE001
                problems.append(f"{rel}: invalid JSON ({e})")
            continue
        if f.suffix.lower() != ".png":
            problems.append(f"{rel}: only .png textures are expected (skipped)")
            continue
        if not NAME_RE.match(rel):
            problems.append(f"{rel}: names must be lowercase a-z 0-9 _ - . only")
        im = Image.open(f)
        w, h = im.size
        if w & (w - 1):
            problems.append(f"{rel}: width {w} is not a power of two")
        meta = f.with_name(f.name + ".mcmeta")
        animated = meta.exists()
        if animated:
            try:
                anim = json.loads(meta.read_text()).get("animation", {})
                fw, fh = anim.get("width", w), anim.get("height", w)
                if "animation" not in json.loads(meta.read_text()):
                    problems.append(f"{rel}.mcmeta: no \"animation\" object (the texture would be static)")
                elif h % fh or w % fw:
                    problems.append(f"{rel}: {w}x{h} is not a whole number of {fw}x{fh} frames (the game would show the missing-texture checker)")
            except Exception:  # noqa: BLE001
                pass
        if rel.startswith(("block/", "item/")) and not animated and w != h:
            problems.append(f"{rel}: {w}x{h} is not square (animated strips need a .png.mcmeta)")
        count += 1
    return count, problems


def build(src, name, pack_format, description, out, make_zip=True, icon=None, min_format=None, max_format=None, format_version=None, format_source=None):
    src, out = Path(src), Path(out)
    count, problems = check(src)
    pack = out / name.replace(" ", "_")
    if pack.exists():
        shutil.rmtree(pack)
    tex = pack / "assets" / "minecraft" / "textures"
    tex.mkdir(parents=True)
    for f in src.rglob("*"):
        if f.is_file() and (f.suffix.lower() == ".png" or f.suffix == ".mcmeta"):
            dst = tex / f.relative_to(src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
    if min_format is not None or max_format is not None:
        if min_format is None or max_format is None:
            raise ValueError("give both --min-format and --max-format")
        meta = {"pack": {"description": description, "min_format": int(min_format), "max_format": int(max_format)}}
        fmt = f"min_format {min_format}, max_format {max_format}"
    else:
        meta = {"pack": {"pack_format": int(pack_format), "description": description}}
        fmt = f"pack_format {pack_format}"
    (pack / "pack.mcmeta").write_text(json.dumps(meta, indent=2))
    (pack / "README.txt").write_text(
        f"{name}\nBuilt with BlockReel (https://github.com/ViniciusNoetzold/mine-blockreel-skill). Textures: see the project's license.\n\n"
        f"Pack format used: {fmt}\nFor Minecraft Java Edition: {format_version or 'NOT RECORDED (look it up!)'}\n"
        f"Source of the number: {format_source or 'NOT RECORDED'}\n"
        "If the game says the pack is incompatible, the format number does not match your game version.\n", encoding="utf-8")
    if icon:
        shutil.copy2(icon, pack / "pack.png")
    zpath = None
    if make_zip:
        zpath = out / (pack.name + ".zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(pack.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(pack).as_posix())  # pack.mcmeta must sit at the zip root
    return pack, zpath, count, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check"); p.add_argument("src")
    p = sub.add_parser("build"); p.add_argument("src"); p.add_argument("--name", required=True)
    p.add_argument("--pack-format", type=int, help="single number (versions up to 1.21.8)")
    p.add_argument("--min-format", type=int, help="1.21.9 and newer: lowest supported resource pack format")
    p.add_argument("--max-format", type=int, help="1.21.9 and newer: highest supported resource pack format")
    p.add_argument("--format-version", help="the Java version this number is for, e.g. 1.21.4 (recorded in README.txt)")
    p.add_argument("--format-source", help="where you found the number, e.g. the wiki URL (recorded in README.txt)")
    p.add_argument("--description", default="Made with BlockReel")
    p.add_argument("--out", default="build"); p.add_argument("--no-zip", action="store_true")
    p.add_argument("--icon")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        n, probs = check(a.src)
        print(f"{n} textures checked")
        for x in probs:
            print(" -", x)
        return 1 if probs else 0
    if a.pack_format is None and a.min_format is None:
        ap.error("a format number is required: --pack-format N, or --min-format N --max-format M (look it up for your version; there is no default)")
    if a.pack_format is not None and (a.min_format is not None or a.max_format is not None):
        ap.error("use either --pack-format or --min-format/--max-format, not both")
    if not (a.format_version and a.format_source):
        print("warning: pass --format-version and --format-source so the pack records where its format number came from")
    pack, z, n, probs = build(a.src, a.name, a.pack_format, a.description, a.out, not a.no_zip, a.icon, a.min_format, a.max_format, a.format_version, a.format_source)
    print(f"built {pack} ({n} textures){' + ' + str(z) if z else ''}")
    for x in probs:
        print(" warning:", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
