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
