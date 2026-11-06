import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
import atlas  # noqa: E402
import pack  # noqa: E402
import skin  # noqa: E402


def test_made_skin_validates_and_previews(tmp_path):
    p = tmp_path / "s.png"
    skin.make_base().save(p)
    r = skin.validate(p)
    assert r["ok"] and r["model"] == "classic" and r["transparent_base_pixels"] == 0
    skin.preview(p, tmp_path / "pv.png")
    assert (tmp_path / "pv.png").exists()


def test_slim_detection(tmp_path):
    p = tmp_path / "slim.png"
    skin.make_base(slim=True).save(p)
    assert skin.validate(p)["model"] == "slim"


def test_legacy_conversion_mirrors_limbs():
    old = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    old.putpixel((4, 20), (255, 0, 0, 255))  # right leg, front-left pixel region
    new = skin.legacy_to_modern(old)
    assert new.size == (64, 64)
    assert any(new.getpixel((x, y))[3] for x in range(16, 32) for y in range(48, 64))


def test_unwrap_writes_every_face(tmp_path):
    p = tmp_path / "s.png"
    skin.make_base().save(p)
    m = skin.unwrap(p, tmp_path / "u")
    assert len(m["parts"]) == 12 and (tmp_path / "u" / "head_front.png").exists()


def test_atlas_slice_dedupes(tmp_path):
    bg, cell, gap = (38, 38, 38), 40, 8
    sheet = Image.new("RGB", (cell * 5 + gap, cell * 4 + gap), bg)
    colours = [(200, 30, 30), (30, 200, 30), (30, 30, 200), (200, 200, 30), (200, 30, 200)]
    for r in range(4):
        for c in range(5):
            col = colours[(r * 5 + c) % 5] if r < 3 else colours[0]  # row 3 repeats colour 0
            sheet.paste(Image.new("RGB", (cell - gap, cell - gap), col), (gap + c * cell, gap + r * cell))
    sp = tmp_path / "sheet.png"
    sheet.save(sp)
    idx = atlas.do_slice(sp, tmp_path / "out", bg=[bg])
    assert idx["cell"] == [cell, cell] and idx["grid"][0] >= 5
    assert idx["unique_count"] == 5 and idx["tile_count"] == 20


def test_pack_build(tmp_path):
    src = tmp_path / "tex" / "block"
    src.mkdir(parents=True)
    Image.new("RGBA", (16, 16), (1, 2, 3, 255)).save(src / "stone.png")
    pk, z, n, problems = pack.build(tmp_path / "tex", "T", 1, "d", tmp_path / "b")
    assert n == 1 and not problems and z.exists()
    assert json.loads((pk / "pack.mcmeta").read_text())["pack"]["pack_format"] == 1


def test_snap_roundtrip_is_exact(tmp_path):
    p = tmp_path / "s.png"
    skin.make_base().save(p)
    Image.open(p).resize((512, 512), Image.NEAREST).save(tmp_path / "big.png")
    skin.snap(tmp_path / "big.png", tmp_path / "back.png")
    a, b = Image.open(p).convert("RGBA"), Image.open(tmp_path / "back.png").convert("RGBA")
    assert list(a.getdata()) == list(b.getdata())


def test_opening_builds_the_name_from_blocks(tmp_path):
    """tools/opening.py writes a valid story whose placed blocks spell a readable bitmap of the name, plus its music."""
    import json, sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "tools"))
    import opening
    grid = opening.text_pixels("AB")
    assert len(grid) >= 6 and len(grid[0]) >= 8 and sum(map(sum, grid)) > 20
    opening.build("AB", tmp_path / "op", block="gold", duration=7)
    s = json.loads((tmp_path / "op" / "story.json").read_text(encoding="utf-8"))
    places = [c for c in s["changes"] if "place" in c]
    assert len(places) == sum(map(sum, grid)) and all(c["block"] == "gold" for c in places)
    assert all(0 < c["t"] < 3.6 for c in places) and s["duration"] == 7
    assert (tmp_path / "op" / "assets" / "audio" / "score.wav").exists() and (tmp_path / "op" / "host.png").exists()
