import json
import random
import sys
import zipfile
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "examples" / "skin-demo"))
sys.path.insert(0, str(ROOT / "examples" / "texture-pack-demo"))
import pack  # noqa: E402
import skin  # noqa: E402
import tilecheck  # noqa: E402
import make_textures  # noqa: E402
import paint_skin  # noqa: E402


# ------------------------------------------------------------------ skins ----
def test_ramp_goes_dark_to_light():
    r = skin.ramp("3a7ab8", 4)
    lum = [0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in r]
    assert len(r) == 4 and lum == sorted(lum) and lum[0] < lum[-1]
    warm = skin.ramp("808080", 4, hue_shift=0.06)
    assert warm[0][2] > warm[0][0] and warm[3][0] > warm[3][2]   # shadows cooler (bluer), lights warmer (redder)


def test_shaded_box_lights_the_top_more_than_the_bottom():
    cv = skin.SkinCanvas()
    cv.shaded_box("body", skin.ramp("808080", 4))
    top = cv.img.getpixel(skin.face_rect("body", "top")[:2]); bottom = cv.img.getpixel(skin.face_rect("body", "bottom")[:2])
    assert sum(top[:3]) > sum(bottom[:3])


def test_mirror_limbs_copies_the_right_side_mirrored():
    cv = skin.SkinCanvas()
    cv.fill_all("right_arm", (10, 10, 10, 255)); cv.px("right_arm", "front", 0, 0, (255, 0, 0, 255))
    cv.mirror_limbs()
    lx, ly, lw, lh = skin.face_rect("left_arm", "front")
    assert cv.img.getpixel((lx + lw - 1, ly)) == (255, 0, 0, 255)   # x=0 on the right arm becomes the last column on the left arm


@pytest.mark.parametrize("slim", [False, True])
def test_demo_skin_is_valid(tmp_path, slim):
    p = tmp_path / "s.png"
    paint_skin.paint(slim=slim).save(p)
    r = skin.validate(p)
    assert r["ok"] and r["model"] == ("slim" if slim else "classic") and r["transparent_base_pixels"] == 0


def test_committed_demo_skins_validate():
    for f, model in (("ranger.png", "classic"), ("ranger-slim.png", "slim")):
        r = skin.validate(ROOT / "examples" / "skin-demo" / f)
        assert r["ok"] and r["model"] == model


# --------------------------------------------------------------- tilecheck ----
def test_seam_detector_flags_a_cut_gradient_and_passes_wrapped_noise():
    g = Image.new("RGBA", (16, 16))
    for y in range(16):
        for x in range(16):
            g.putpixel((x, y), (x * 16, 60, 60, 255))
    assert tilecheck.seam_score(g)["visible_seam"]
    rng = random.Random(1); n = Image.new("RGBA", (16, 16))
    for y in range(16):
        for x in range(16):
            n.putpixel((x, y), (100 + rng.randrange(30), 120, 90, 255))
    assert not tilecheck.seam_score(n)["visible_seam"]


def test_patterned_textures_are_not_false_positives(tmp_path):
    out = make_textures.make_all(16)
    for name in ("block/bricks", "block/oak_planks", "block/cobblestone", "block/grass_block_top", "block/stone", "block/sand"):
        assert not tilecheck.seam_score(out[name])["visible_seam"], name


def test_palette_and_animated_frames(tmp_path):
    make_dir = tmp_path / "t"
    for key, val in make_textures.make_all(16).items():
        f = make_dir / f"{key}.png"; f.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(val, tuple):
            val[0].save(f); (make_dir / f"{key}.png.mcmeta").write_text(json.dumps(val[1]))
        else:
            val.save(f)
    assert len(tilecheck.frames(make_dir / "block" / "water_still.png")) == 8
    pal = tilecheck.palette(Image.open(make_dir / "block" / "stone.png"), 4)
    assert 1 <= len(pal) <= 4 and abs(sum(s for _, s in pal) - 1) < 0.02
    rep = tilecheck.set_report(make_dir, tmp_path / "rep")
    assert rep["count"] == 25 and not rep["issues"], rep["issues"]
    assert (tmp_path / "rep" / "set-sheet.png").exists()


def test_set_check_catches_mixed_sizes(tmp_path):
    d = tmp_path / "block"; d.mkdir()
    for n, size in (("a", 16), ("b", 16), ("c", 16), ("d", 32)):
        Image.new("RGBA", (size, size), (90, 120, 80, 255)).save(d / f"{n}.png")
    rep = tilecheck.set_report(tmp_path, tmp_path / "r")
    assert any("size" in i for i in rep["issues"])


def test_demo_generation_is_deterministic():
    a, b = make_textures.make_all(16, 5), make_textures.make_all(16, 5)
    for k in a:
        ia = a[k][0] if isinstance(a[k], tuple) else a[k]; ib = b[k][0] if isinstance(b[k], tuple) else b[k]
        assert ia.tobytes() == ib.tobytes(), k


# -------------------------------------------------------------------- pack ----
def test_pack_cli_refuses_without_a_format_number(tmp_path, capsys):
    src = tmp_path / "tex" / "block"; src.mkdir(parents=True)
    Image.new("RGBA", (16, 16), (1, 2, 3, 255)).save(src / "stone.png")
    with pytest.raises(SystemExit) as e:
        pack.main(["build", str(tmp_path / "tex"), "--name", "T", "--out", str(tmp_path / "b")])
    assert e.value.code != 0


def test_pack_min_max_format_and_cited_source(tmp_path):
    src = tmp_path / "tex" / "block"; src.mkdir(parents=True)
    Image.new("RGBA", (16, 16), (1, 2, 3, 255)).save(src / "stone.png")
    rc = pack.main(["build", str(tmp_path / "tex"), "--name", "T", "--min-format", "69", "--max-format", "69",
                    "--format-version", "1.21.9", "--format-source", "https://minecraft.wiki/w/Pack_format", "--out", str(tmp_path / "b")])
    assert rc == 0
    meta = json.loads((tmp_path / "b" / "T" / "pack.mcmeta").read_text())["pack"]
    assert meta["min_format"] == 69 and meta["max_format"] == 69 and "pack_format" not in meta
    readme = (tmp_path / "b" / "T" / "README.txt").read_text()
    assert "https://minecraft.wiki/w/Pack_format" in readme and "1.21.9" in readme
    names = zipfile.ZipFile(tmp_path / "b" / "T.zip").namelist()
    assert "pack.mcmeta" in names                                        # at the zip root


def test_pack_check_reports_broken_animation_strips(tmp_path):
    d = tmp_path / "block"; d.mkdir()
    Image.new("RGBA", (16, 40), (1, 2, 3, 255)).save(d / "w.png")        # 40 px tall: not a whole number of 16 px frames
    (d / "w.png.mcmeta").write_text(json.dumps({"animation": {"frametime": 2}}))
    n, probs = pack.check(tmp_path)
    assert any("whole number" in p for p in probs)


# ------------------------------------------------------- real renders (browser) ----
@pytest.fixture(scope="module")
def browser_ok():
    pytest.importorskip("playwright")
    import tempfile
    import render as R
    try:
        assert R.main([str(ROOT / "examples" / "hello-world" / "story.json"), "--frame", "1", "--scale", "0.25", "--out", str(Path(tempfile.gettempdir()) / "br_probe2.png")]) == 0
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"cannot render here: {e}")


def test_turntable_renders_four_views(browser_ok, tmp_path):
    import turntable
    out = tmp_path / "tt.png"
    assert turntable.main([str(ROOT / "examples" / "skin-demo" / "ranger.png"), "--out", str(out), "--size", "200x300"]) == 0
    im = Image.open(out)
    assert im.size == (800, 300)
    views = [im.crop((i * 200, 0, (i + 1) * 200, 300)) for i in range(4)]
    assert all(len(set(v.convert("RGB").getdata())) > 20 for v in views)   # every view shows the character, not an empty background


def test_pack_preview_renders_the_scene(browser_ok, tmp_path):
    import pack_preview
    out = tmp_path / "pp.png"
    assert pack_preview.main([str(ROOT / "examples" / "texture-pack-demo" / "textures"), "--out", str(out)]) == 0
    assert Image.open(out).size == (1920, 1080)


# --------------------------------------------------------------- publishing ----
def test_set_placeholders_dry_run_changes_nothing_and_rejects_bad_user(capsys):
    import set_placeholders
    before = (ROOT / "README.md").read_text(encoding="utf-8")
    assert set_placeholders.main(["--user", "octocat", "--name", "Octo Cat"]) == 0
    assert (ROOT / "README.md").read_text(encoding="utf-8") == before        # dry run only
    assert set_placeholders.main(["--user", "octo/cat", "--name", "x"]) == 2   # a slash is not a user name
