#!/usr/bin/env python3
"""Compose reusable build blueprints into a city and generate its timelapse."""

import argparse
import json
import re
from pathlib import Path

from build_timelapse import BUILD_FILES, write_build


def read_object(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def coordinate(value):
    if not isinstance(value, list) or len(value) != 3 or any(type(n) is not int for n in value):
        raise ValueError("coordinates must be three integers [x, y, z]")
    return value


def transform_position(value, origin, turns):
    x, y, z = coordinate(value)
    for _ in range(turns):
        x, z = z, -x
    return [x + origin[0], y + origin[1], z + origin[2]]


def transform_block(block, turns):
    if not isinstance(block, str):
        raise ValueError("block must be a name")
    name, *state = block.split(":")
    if turns and not state and name.endswith(("_stairs", "_door")):
        raise ValueError(f"specify a facing for {block!r} before rotating its template")
    if not turns or not state:
        return block
    directions = ["south", "east", "north", "west"]
    if state[0] in directions:
        state[0] = directions[(directions.index(state[0]) + turns) % 4]
    elif turns % 2 and state[0] in ("x", "z"):
        state[0] = "z" if state[0] == "x" else "x"
    return ":".join([name, *state])


def transform_operation(op, origin, turns):
    if not isinstance(op, dict) or len(op) != 1:
        raise ValueError("each operation must contain one set or fill")
    kind, values = next(iter(op.items()))
    if kind not in ("set", "fill") or not isinstance(values, list) or len(values) != (2 if kind == "set" else 3):
        raise ValueError("use set [block, position] or fill [block, corner, corner]")
    block = transform_block(values[0], turns)
    corners = [transform_position(value, origin, turns) for value in values[1:]]
    if kind == "fill":
        axes = list(zip(*corners))
        corners = [[min(axis) for axis in axes], [max(axis) for axis in axes]]
    return {kind: [block, *corners]}


def expand_layout(layout, directory):
    districts = layout.get("districts")
    if not isinstance(districts, list) or not districts:
        raise ValueError("districts must be a non-empty list")
    phases = []
    names = set()
    for district in districts:
        if not isinstance(district, dict):
            raise ValueError("each district must be an object")
        name = district.get("id")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name) or name in names:
            raise ValueError("each district needs a unique id starting with a lowercase letter, using letters, digits and hyphens")
        names.add(name)
        try:
            origin = coordinate(district.get("origin"))
            rotation = district.get("rotation", 0)
            if type(rotation) is not int or rotation not in (0, 90, 180, 270):
                raise ValueError("rotation must be 0, 90, 180 or 270")
            source = district.get("blueprint")
            if not isinstance(source, str) or not source:
                raise ValueError("blueprint must name a JSON file")
            template = read_object(directory / source)
            local_phases = template.get("phases")
            if not isinstance(local_phases, list) or not local_phases:
                raise ValueError("the template needs at least one phase")
            for phase in local_phases:
                if not isinstance(phase, dict) or not isinstance(phase.get("id"), str) or not isinstance(phase.get("ops"), list):
                    raise ValueError("each template phase needs an id and a list of ops")
                phases.append({
                    "id": f"{name}-{phase['id']}",
                    "ops": [transform_operation(op, origin, rotation // 90) for op in phase["ops"]],
                })
        except ValueError as exc:
            raise ValueError(f"district {name}: {exc}") from exc
    blueprint = {key: layout[key] for key in ("title", "duration", "fps", "size") if key in layout}
    blueprint["phases"] = phases
    return blueprint


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        layout = read_object(args.layout)
        blueprint = expand_layout(layout, args.layout.parent)
        target = args.out / "city-blueprint.json"
        outputs = {(args.out / name).resolve() for name in (*BUILD_FILES, target.name)}
        sources = {(args.layout.parent / district["blueprint"]).resolve() for district in layout["districts"]}
        sources.add(args.layout.resolve())
        if outputs & sources:
            raise ValueError("use an output directory that keeps the source layout and templates separate")
        report = write_build(blueprint, args.out)
        target.write_text(json.dumps(blueprint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Built {len(layout['districts'])} districts with {report['blockCount']} blocks. Storyboard: {args.out / 'story.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
