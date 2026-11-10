#!/usr/bin/env python3
"""Compile an ordered voxel blueprint into a BlockReel build with original audio."""

import argparse
import itertools
import json
import math
import re
import tempfile
import wave
from fractions import Fraction
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
BLOCK_INDEX = ROOT / "core" / "builtin" / "blocks" / "index.json"
DIRECTIONS = {"north", "south", "east", "west"}
MAX_BLOCKS = 20_000
SAMPLE_RATE = 48_000
BUILD_FILES = ("mix.wav", "build-report.json", "story.json")


def voxel(value):
    if not isinstance(value, list) or len(value) != 3 or any(type(n) is not int for n in value):
        raise ValueError("use integer [x, y, z] coordinates")
    x, y, z = value
    if abs(x) > 128 or abs(z) > 128 or not 0 <= y <= 64:
        raise ValueError("build coordinates must use x/z from -128 to 128 and y from 0 to 64")
    return tuple(value)


def block_shape(block, definitions):
    if not isinstance(block, str):
        raise ValueError("expected a built-in block ID")
    name, *suffix = block.split(":")
    if name not in definitions:
        raise ValueError(f"unknown built-in block {block!r}")
    definition = definitions[name]
    shape = definition.get("shape", "cube") if isinstance(definition, dict) else "cube"
    if shape not in {"cube", "stairs", "slab", "door", "torch"} or name in {"water", "lava"}:
        raise ValueError(f"{block!r} has a shape this compiler cannot place; use a full block or supported stairs, slabs, doors, and torches")
    if not suffix:
        return shape
    if shape == "stairs" and len(suffix) == 1 and suffix[0] in DIRECTIONS:
        return shape
    if shape == "slab" and suffix == ["top"]:
        return shape
    if shape == "door" and suffix[0] in DIRECTIONS and suffix[1:] in ([], ["open"]):
        return shape
    if (name == "log" or name.endswith("_log")) and suffix in (["x"], ["y"], ["z"]):
        return shape
    raise ValueError(f"unsupported orientation for {block!r}")


def read_phases(phases):
    if not isinstance(phases, list) or not phases:
        raise ValueError("provide a nonempty phases list")
    definitions = json.loads(BLOCK_INDEX.read_text(encoding="utf-8"))["blocks"]
    occupied, named = set(), set()
    result = []
    for phase in phases:
        if not isinstance(phase, dict):
            raise ValueError("each phase needs an id and a nonempty ops list")
        name, ops = phase.get("id"), phase.get("ops")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", name) or name in named:
            raise ValueError("each phase needs a unique lowercase id")
        if not isinstance(ops, list) or not ops:
            raise ValueError(f"phase {name!r} needs a nonempty ops list")
        named.add(name)
        blocks = []
        for op in ops:
            if not isinstance(op, dict) or len(op) != 1:
                raise ValueError(f"phase {name!r} expects a set or fill operation")
            kind, args = next(iter(op.items()))
            if kind not in {"set", "fill"} or not isinstance(args, list) or len(args) != (2 if kind == "set" else 3):
                raise ValueError(f"invalid set/fill in phase {name!r}")
            block, first, *last = args
            shape = block_shape(block, definitions)
            lo = voxel(first)
            hi = voxel(last[0]) if last else lo
            if any(a > b for a, b in zip(lo, hi)):
                raise ValueError(f"fill bounds in phase {name!r} must start at the minimum coordinate")
            span = math.prod(b - a + 1 for a, b in zip(lo, hi))
            if span + len(occupied) > MAX_BLOCKS:
                raise ValueError(f"build exceeds {MAX_BLOCKS:,} occupied cells; split it into districts or sequences")
            # Walk each operation from the ground up, starting from the back of the lot.
            for y, z, x in itertools.product(range(lo[1], hi[1] + 1), range(lo[2], hi[2] + 1), range(lo[0], hi[0] + 1)):
                pos = (x, y, z)
                cells = (pos, voxel([x, y + 1, z])) if shape == "door" else (pos,)
                for cell in cells:
                    if cell in occupied:
                        raise ValueError(f"duplicate voxel {cell} in phase {name!r}; leave both door cells clear")
                    occupied.add(cell)
                if len(occupied) > MAX_BLOCKS:
                    raise ValueError(f"build exceeds {MAX_BLOCKS:,} occupied cells; split it into districts or sequences")
                blocks.append((block, pos))
        result.append((name, blocks))
    return result, occupied


def build_camera(center, extents, aspect, reveal, duration):
    """Fit the entire silhouette against both camera axes in perspective."""
    corners = list(itertools.product(*[(-extent / 2, extent / 2) for extent in extents]))
    shots, far_depth = [], 0
    for start, stop, pitch, first, last in ((0, reveal, 28, 16, 31), (reveal, duration, 13, 19, 12)):
        p = math.radians(pitch)
        projections = []
        for step in range(17):
            a = math.radians(first + (last - first) * step / 16)
            for x, y, z in corners:
                lateral = x * math.cos(a) - z * math.sin(a)
                radial = x * math.sin(a) + z * math.cos(a)
                up = y * math.cos(p) - radial * math.sin(p)
                depth = y * math.sin(p) + radial * math.cos(p)
                projections.append((abs(lateral), abs(up), depth))
        deepest = max(depth for _, _, depth in projections)
        # Widen large compositions before the engine's 400-block far plane can clip them.
        for fov in range(42, 85, 6):
            tan_y = math.tan(math.radians(fov / 2)) * 0.84
            tan_x = tan_y * aspect
            distance = max(8, max(depth + max(x / tan_x, y / tan_y) for x, y, depth in projections))
            if distance + deepest < 380:
                break
        else:
            raise ValueError("the build cannot fit this aspect ratio; use a wider canvas or split it into sequences")
        far_depth = max(far_depth, distance + deepest)
        shots.append({"t": start, "dur": stop - start, "fov": fov, "ease": "smooth", "orbit": {
            "center": center, "from": first, "to": last,
            "height": round(distance * math.sin(p), 3), "radius": round(distance * math.cos(p), 3),
        }})
    return shots, far_depth


def viewing_corridor(center, shots, clear_radius, ground_radius):
    """Reserve the sight line from the front arc to the complete footprint."""
    orbits = [shot["orbit"] for shot in shots]
    angles = [a for orbit in orbits for a in (orbit["from"], orbit["to"])]
    middle = math.radians((min(angles) + max(angles)) / 2)
    spread = math.sin(math.radians((max(angles) - min(angles)) / 2))
    distance = min(ground_radius, max(orbit["radius"] for orbit in orbits))
    step = max(5, clear_radius)
    stations = [*range(step, math.ceil(distance), step), distance]
    return [[round(center[0] + math.sin(middle) * at, 2),
             round(center[2] + math.cos(middle) * at, 2),
             round(clear_radius + at * spread, 2)] for at in stations]


def compile_blueprint(blueprint):
    if not isinstance(blueprint, dict):
        raise ValueError("the blueprint must be a JSON object")
    title = blueprint.get("title", "BlockReel Timelapse")
    duration, fps = blueprint.get("duration", 15), blueprint.get("fps", 24)
    size = blueprint.get("size", [1280, 720])
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be nonempty text")
    if type(duration) not in (int, float) or not 4 <= duration <= 120:
        raise ValueError("duration must be from 4 to 120 seconds")
    if type(fps) is not int or not 12 <= fps <= 60:
        raise ValueError("fps must be a whole number from 12 to 60")
    if (not isinstance(size, list) or len(size) != 2
            or any(type(n) is not int or not 64 <= n <= 3840 or n % 2 for n in size)):
        raise ValueError("size must give two even pixel dimensions from 64 to 3840")
    total_frames = Fraction(str(duration)) * fps
    if total_frames.denominator != 1:
        raise ValueError("duration and fps must produce a whole number of frames")
    total_frames = int(total_frames)
    phases, occupied = read_phases(blueprint.get("phases"))
    lo = [min(axis) for axis in zip(*occupied)]
    hi = [max(axis) for axis in zip(*occupied)]
    extents = [b - a + 1 for a, b in zip(lo, hi)]
    if extents[0] > 128 or extents[2] > 128:
        raise ValueError("the footprint exceeds 128×128 blocks; split it into districts or sequences")
    center = [a + extent / 2 for a, extent in zip(lo, extents)]
    start_frame = max(1, round(total_frames * 0.055))
    reveal_frame = total_frames - max(fps, round(total_frames * 0.22))
    reveal = reveal_frame / fps
    construction = reveal_frame - start_frame - max(1, round(0.35 * fps))
    count = sum(len(blocks) for _, blocks in phases)
    changes, stages = [], []
    for name, blocks in phases:
        first = len(changes)
        for block, pos in blocks:
            t = (start_frame + construction * len(changes) / count) / fps
            changes.append({"t": round(t, 6), "place": list(pos), "block": block})
        stages.append({"id": name, "firstTime": changes[first]["t"],
                       "lastTime": changes[-1]["t"], "blockCount": len(blocks)})
    land_camera, land_far = build_camera(center, extents, size[0] / size[1], reveal, duration)
    portrait_camera, portrait_far = build_camera(center, extents, 9 / 16, reveal, duration)
    camera_ceiling = center[1] + max(shot["orbit"]["height"] for shot in land_camera + portrait_camera)
    cloud_height = max(34, math.ceil(camera_ceiling) + 10)
    fog_near = max(land_far, portrait_far)
    style = {"sun": {"color": "#fff1d5", "intensity": 1.8, "dir": [0.52, 0.8, 0.68]}}
    if fog_near > 40:
        fog_near = math.ceil(fog_near) + 2
        style["fog"] = [fog_near, min(400, fog_near + 70)]
    flat_radius = math.ceil(math.hypot(extents[0], extents[2]) / 2) + 3
    ground_radius = max(32, flat_radius + 15, math.ceil(land_camera[0]["orbit"]["radius"]) + 16)
    ground_radius = min(96, ground_radius)
    cx, cz = round(center[0]), round(center[2])
    sky = {"clouds": True, "cloudSpeed": 1.6, "cloudHeight": cloud_height}
    if max(extents[0], extents[2]) >= 32:
        sky["groundBackdrop"] = [cx, -0.35, cz]
    story = {
        "title": title, "duration": duration, "fps": fps, "size": size, "seed": 29,
        "style": "classic-2012", "textures": "builtin", "font": "css",
        "styleOverride": style,
        "sky": sky,
        "world": [{"terrain": {
            "center": [cx, cz], "radius": ground_radius, "biome": "forest",
            "base": -1, "amp": 2.2, "depth": 2, "bottom": -5,
            "flat": {"center": [cx, cz], "radius": flat_radius, "y": -1},
            "clear": viewing_corridor(center, land_camera + portrait_camera, flat_radius, ground_radius),
            "trees": 0.03, "plants": 0.13, "flowers": 0.015,
        }}],
        "changes": changes, "camera": land_camera, "reels": {"camera": portrait_camera},
        "audio": {"music": {"file": "mix.wav", "volume": 1, "fadeIn": 0, "fadeOut": 0}},
    }
    report = {"bounds": {"min": lo, "max": hi}, "blockCount": count, "occupiedCellCount": len(occupied),
              "revealTime": reveal, "phases": stages}
    return story, report


def write_audio(path, story, report):
    duration = story["duration"]
    rng = np.random.default_rng(story["seed"])
    mix = np.zeros((round(duration * SAMPLE_RATE), 2), dtype=np.float32)

    def add(mono, when, pan):
        start = round(when * SAMPLE_RATE)
        count = min(len(mono), len(mix) - start)
        mix[start:start + count, 0] += mono[:count] * (1 - pan)
        mix[start:start + count, 1] += mono[:count] * (1 + pan)

    # Quiet repeating plucks underneath the block Foley.
    note_time = np.arange(round(1.15 * SAMPLE_RATE)) / SAMPLE_RATE
    notes = (48, 55, 60, 64, 53, 60, 65, 69, 45, 52, 57, 60, 43, 50, 55, 59)
    for i, when in enumerate(np.arange(0.22, duration - 0.3, 0.43)):
        hz = 440 * 2 ** ((notes[i % len(notes)] - 69) / 12)
        wave_t = math.tau * hz * note_time
        tone = np.sin(wave_t) + 0.22 * np.sin(2.005 * wave_t)
        gain = np.minimum(1, note_time / 0.024) * np.exp(-note_time * 4)
        add(tone * gain * (0.05 if i % 4 == 0 else 0.035), when, -0.13 if i % 2 == 0 else 0.13)

    # Fast builds group dense clicks so the material still reads without saturating the mix.
    cue_time = np.arange(round(0.12 * SAMPLE_RATE)) / SAMPLE_RATE
    previous = -1
    phase_starts = {phase["firstTime"] for phase in report["phases"]}
    for change in story["changes"]:
        when, block = change["t"], change["block"]
        if when - previous < 0.085 and when not in phase_starts:
            continue
        previous = when
        hz, roughness = (660, 0.12) if "glass" in block else (160, 0.31)
        if any(k in block for k in ("stone", "brick", "cobble")):
            hz, roughness = 91, 0.56
        hz *= rng.uniform(0.86, 1.15)
        resonance = np.sin(math.tau * hz * cue_time)
        grit = rng.standard_normal(len(cue_time))
        attack = np.minimum(1, cue_time / 0.003) * np.exp(-cue_time * 43)
        add(0.17 * attack * (resonance + roughness * grit), when, rng.uniform(-0.22, 0.22))

    for i, hz in enumerate((261.63, 329.63, 392.00, 523.25)):
        tone = np.sin(math.tau * hz * note_time)
        add(0.055 * tone * np.minimum(1, note_time / 0.022) * np.exp(-note_time * 3.3),
            report["revealTime"] + i * 0.055, -0.12 + i * 0.08)
    mix[-round(0.28 * SAMPLE_RATE):] *= np.linspace(1, 0, round(0.28 * SAMPLE_RATE))[:, None]
    with wave.open(str(path), "wb") as output:
        output.setparams((2, 2, SAMPLE_RATE, len(mix), "NONE", "not compressed"))
        output.writeframes((np.clip(mix, -0.95, 0.95) * 32767).astype("<i2").tobytes())


def write_build(blueprint, out):
    story, report = compile_blueprint(blueprint)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out) as directory:
        staging = Path(directory)
        write_audio(staging / "mix.wav", story, report)
        for name, data in (("story.json", story), ("build-report.json", report)):
            (staging / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name in BUILD_FILES:
            (staging / name).replace(out / name)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blueprint", type=Path)
    parser.add_argument("--out", required=True, type=Path, help="directory for story.json, build-report.json and mix.wav")
    args = parser.parse_args(argv)
    try:
        if args.blueprint.resolve() in {(args.out / name).resolve() for name in BUILD_FILES}:
            raise ValueError("use an output directory that keeps the source blueprint separate")
        blueprint = json.loads(args.blueprint.read_text(encoding="utf-8"))
        report = write_build(blueprint, args.out)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Wrote {report['blockCount']} placements in {len(report['phases'])} phases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
