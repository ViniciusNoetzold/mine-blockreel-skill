"""Engine tests: pure animation math (node) and real renders (Playwright + Chromium). Renders are skipped
when Playwright or a browser is not available."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def test_anim_math_in_node():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    r = subprocess.run(["node", str(ROOT / "tests" / "anim_check.mjs")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "anim ok" in r.stdout
    r = subprocess.run(["node", str(ROOT / "tests" / "world_check.mjs")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0 and "world ok" in r.stdout, r.stderr + r.stdout


@pytest.fixture(scope="module")
def render():
    pytest.importorskip("playwright")
    import render as R

    def run(story, t, out, scale=0.4):
        rc = R.main([str(ROOT / "examples" / story / "story.json"), "--frame", str(t), "--scale", str(scale), "--out", str(out)])
        assert rc == 0
        return Image.open(out).convert("RGB")
    try:
        import tempfile
        run("hello-world", 1.0, Path(tempfile.gettempdir()) / "br_probe.png")
    except Exception as e:  # no browser available
        pytest.skip(f"cannot render here: {e}")
    return run


def center_mean(im):
    w, h = im.size
    return sum(ImageStat.Stat(im.crop((w * 3 // 10, h * 3 // 10, w * 7 // 10, h * 7 // 10))).mean) / 3  # skips bars + vignette


def diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean)


def test_render_is_deterministic(render, tmp_path):
    a = render("camera-lab", 8.9, tmp_path / "a.png")
    b = render("camera-lab", 8.9, tmp_path / "b.png")
    assert diff(a, b) == 0  # renderAt(t) is a pure function of t


def test_face_states_change_pixels(render, tmp_path):
    neutral = render("faces-lab", 1.0, tmp_path / "n.png", 0.5)  # hero is neutral at t=1
    shout = render("faces-lab", 2.4, tmp_path / "s.png", 0.5)    # hero wide eyes + shout at t=2.4
    assert diff(neutral, shout) > 3


def test_particles_appear(render, tmp_path):
    before = render("particles-lab", 2.9, tmp_path / "b.png")
    boom = render("particles-lab", 3.5, tmp_path / "e.png")
    assert diff(before, boom) > 3


def test_flash_and_fade(render, tmp_path):
    flash = render("camera-lab", 4.05, tmp_path / "f.png")
    assert center_mean(flash) > 235  # nearly white at the flash peak
    fade = render("camera-lab", 13.9, tmp_path / "d.png")
    assert center_mean(fade) < 25  # nearly black near the end of the fade


def test_every_example_renders(render, tmp_path):
    """Smoke test: each example storyboard loads, renders a frame without engine errors, and is not blank."""
    for story in sorted(p.parent.name for p in (ROOT / "examples").glob("*/story.json")):
        im = render(story, 1.0, tmp_path / f"{story}.png", 0.3)
        assert sum(ImageStat.Stat(im).stddev) > 3, f"{story} rendered a blank frame"


def test_tnt_explosion_changes_the_world(render, tmp_path):
    before = render("world-lab", 5.5, tmp_path / "b.png", 0.4)   # TNT is fusing
    after = render("world-lab", 7.5, tmp_path / "a.png", 0.4)    # crater + smoke after the blast at ~6.6 s
    assert diff(before, after) > 5


def test_mobs_render_with_their_textures(render, tmp_path):
    im = render("mobs-lab", 1.5, tmp_path / "m.png", 0.5)
    px = im.load(); w, h = im.size
    pink = sum(1 for x in range(0, w, 2) for y in range(0, h, 2) if px[x, y][0] > 200 and 120 < px[x, y][1] < 190 and px[x, y][2] > 130)
    red = sum(1 for x in range(0, w, 2) for y in range(0, h, 2) if px[x, y][0] > 130 and px[x, y][1] < 80 and px[x, y][2] < 80)
    assert pink > 10, "pig texture missing"
    assert red > 2, "spider eyes missing"


def test_qa_path_check_catches_walking_through_blocks(render, tmp_path):
    """The dense path check must FAIL an actor that spawns inside a tree trunk and one that crosses a wall between two
    sampled frames, and stay quiet for an actor that walks around the wall and for a wall that was broken first."""
    import json
    import qa
    story = {
        "fps": 30, "size": [320, 180], "duration": 4, "style": "classic-2012", "textures": "builtin",
        "world": [{"fill": ["grass", [-8, 0, -8], [8, 0, 8]]}, {"fill": ["stone", [0, 1, -3], [0, 2, 3]]},
                  {"tree": [-5, 1, 5], "height": 4}, {"set": ["stone", [3, 1, 0]]}],
        "changes": [{"t": 0.5, "break": [3, 1, 0]}],
        "actors": {
            "intree": {"skin": "/core/builtin/skins/hero.png", "pos": [-4.5, 1, 5.5]},
            "ghost": {"skin": "/core/builtin/skins/hero.png", "pos": [-2.5, 1, 0.5]},
            "polite": {"skin": "/core/builtin/skins/villain.png", "pos": [-2.5, 1, 6]},
            "after": {"skin": "/core/builtin/skins/explorer.png", "pos": [3.5, 1, -2]},
        },
        "timeline": [
            {"t": 0, "actor": "ghost", "do": "walk", "to": [2.5, 1, 0.5], "dur": 0.9},
            {"t": 0, "actor": "polite", "do": "walk", "to": [2.5, 1, 6], "dur": 3},
            {"t": 1.0, "actor": "after", "do": "walk", "to": [3.5, 1, 2], "dur": 2},
        ],
        "camera": [{"t": 0, "dur": 4, "pos": [0, 6, 14], "look": [0, 1, 0]}],
    }
    sp = tmp_path / "story.json"; sp.write_text(json.dumps(story))
    rc = qa.main([str(sp), "--out", str(tmp_path / "qa"), "--min-frames", "2", "--no-md", "--scale", "0.5"])
    assert rc == 1
    fails = [i[2] for i in json.loads((tmp_path / "qa" / "auto.json").read_text())["issues"] if i[0] == "FAIL"]
    assert any(f.startswith("intree is inside log") for f in fails), fails
    assert any(f.startswith("ghost is inside stone at [0,") for f in fails), fails
    assert not any(f.startswith(("polite", "after")) for f in fails), fails
