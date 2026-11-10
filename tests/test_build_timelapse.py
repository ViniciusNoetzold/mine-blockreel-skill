import io
import itertools
import json
import math
import sys
import wave
from pathlib import Path

import pytest
from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_timelapse as build


def small_blueprint():
    return {
        "title": "Casa de teste", "duration": 4, "fps": 24, "size": [640, 360],
        "phases": [
            {"id": "base", "ops": [{"fill": ["cobblestone", [-2, 0, -1], [2, 0, 1]]}]},
            {"id": "front", "ops": [{"set": ["oak_door:south", [0, 1, 1]]},
                                    {"set": ["glass", [1, 2, 1]]}]},
            {"id": "roof", "ops": [{"set": ["oak_stairs:east", [-2, 3, 0]]},
                                   {"set": ["oak_slab:top", [0, 4, 0]]},
                                   {"set": ["log:z", [1, 3, 0]]}]},
        ],
    }


def test_compiler_keeps_every_voxel_and_generates_portable_mix(tmp_path):
    blueprint = small_blueprint()
    report = build.write_build(blueprint, tmp_path)
    story = json.loads((tmp_path / "story.json").read_text(encoding="utf-8"))
    assert json.loads((tmp_path / "build-report.json").read_text(encoding="utf-8")) == report
    assert report["bounds"] == {"min": [-2, 0, -1], "max": [2, 4, 1]}
    assert report["blockCount"] == len(story["changes"]) == 20
    assert report["occupiedCellCount"] == 21
    assert [p["id"] for p in report["phases"]] == ["base", "front", "roof"]
    times = [c["t"] for c in story["changes"]]
    assert 0 < times[0] < times[-1] < report["revealTime"] < story["duration"]
    assert times == sorted(set(times))
    assert story["changes"][-1]["block"] == "log:z"
    assert story["camera"][-1]["t"] == story["reels"]["camera"][-1]["t"] == report["revealTime"]
    assert story["reels"]["camera"][-1]["orbit"]["radius"] > story["camera"][-1]["orbit"]["radius"]
    clear = story["world"][0]["terrain"]["clear"]
    for shot in story["camera"] + story["reels"]["camera"]:
        orbit = shot["orbit"]
        cx, _, cz = orbit["center"]
        for angle in (orbit["from"], orbit["to"]):
            yaw = math.radians(angle)
            x = cx + math.sin(yaw) * orbit["radius"]
            z = cz + math.cos(yaw) * orbit["radius"]
            assert any(math.hypot(a - x, b - z) < r for a, b, r in clear)
    with wave.open(str(tmp_path / "mix.wav"), "rb") as audio:
        assert audio.getnframes() == 4 * 48_000
        assert audio.getnchannels() == 2
        assert any(audio.readframes(audio.getnframes()))


@pytest.mark.parametrize(("ops", "error"), [
    ([{"set": ["unknown_material", [0, 3, 0]]}], "unknown built-in"),
    ([{"set": ["glass_pane", [0, 3, 0]]}], "shape this compiler cannot place"),
    ([{"set": ["stone", [0, 2, 1]]}], "duplicate voxel"),  # upper half of the door
    ([{"set": ["stone", [0, -1, 0]]}], "build coordinates"),
    ([{"fill": ["stone", [1, 5, 0], [0, 5, 0]]}], "minimum coordinate"),
    ([{"fill": ["stone", [0, 5, 0], [128, 64, 128]]}], "split it into districts"),
    ([], "nonempty ops"),
])
def test_compiler_rejects_invalid_blueprint_without_writing(tmp_path, ops, error):
    blueprint = small_blueprint()
    blueprint["phases"][-1]["ops"] = ops
    output = tmp_path / "film"
    with pytest.raises(ValueError, match=error):
        build.write_build(blueprint, output)
    assert not output.exists()


def test_large_city_fits_both_cameras_before_fog_and_far_plane():
    story, report = build.compile_blueprint({"phases": [{"id": "city", "ops": [
        {"set": ["stone", [-64, 0, -64]]}, {"set": ["stone", [63, 64, 63]]},
    ]}]})
    near_fog, far_fog = story["styleOverride"]["fog"]
    assert 40 < near_fog < far_fog <= 400
    assert story["sky"]["groundBackdrop"] == [0, -0.35, 0]
    assert max(shot["fov"] for shot in story["reels"]["camera"]) > 42
    corners = list(itertools.product(*zip(report["bounds"]["min"], (n + 1 for n in report["bounds"]["max"]))))
    for shots, aspect in ((story["camera"], 16 / 9), (story["reels"]["camera"], 9 / 16)):
        for shot in shots:
            orbit = shot["orbit"]
            assert story["sky"]["cloudHeight"] > orbit["center"][1] + orbit["height"]
            pitch = math.atan2(orbit["height"], orbit["radius"])
            distance = math.hypot(orbit["height"], orbit["radius"])
            screen = math.tan(math.radians(shot["fov"] / 2))
            for angle in (orbit["from"], orbit["to"]):
                yaw = math.radians(angle)
                for point in corners:
                    x, y, z = (value - center for value, center in zip(point, orbit["center"]))
                    radial = x * math.sin(yaw) + z * math.cos(yaw)
                    depth = distance - y * math.sin(pitch) - radial * math.cos(pitch)
                    assert 0 < depth < near_fog
                    assert abs(x * math.cos(yaw) - z * math.sin(yaw)) < depth * screen * aspect
                    assert abs(y * math.cos(pitch) - radial * math.sin(pitch)) < depth * screen


def test_timed_slab_keeps_half_height(tmp_path):
    pytest.importorskip("playwright")
    from playwright.sync_api import Error
    import render

    story = {
        "fps": 24, "size": [320, 180], "duration": 3, "style": "classic-2012", "textures": "builtin",
        "styleOverride": {"shadows": False}, "sky": {"clouds": False, "stars": 0, "celestial": False},
        "changes": [{"t": 1, "place": [0, 1, 0], "block": "oak_slab"}],
        "camera": [{"t": 0, "dur": 3, "pos": [0.5, 1.5, 5], "look": [0.5, 1.5, 0], "fov": 42}],
    }
    path = tmp_path / "story.json"
    path.write_text(json.dumps(story), encoding="utf-8")
    try:
        with render.render_page(path, story, 1.0, False) as page:
            before = Image.open(io.BytesIO(render.capture_frame(page, 0))).convert("RGB")
            after = Image.open(io.BytesIO(render.capture_frame(page, 2))).convert("RGB")
    except Error as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Chromium browser unavailable")
        raise
    box = ImageChops.difference(before, after).getbbox()
    assert box is not None
    left, top, right, bottom = box
    assert 0.42 < (bottom - top) / (right - left) < 0.62, box
