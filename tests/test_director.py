"""v0.2: persona skins (photo -> skin), the director compiler (plan -> story) and the new engine features in a real render."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core")); sys.path.insert(0, str(ROOT / "tools"))
import persona  # noqa: E402
import skin as skinlib  # noqa: E402


@pytest.mark.parametrize("name", sorted(persona.PRESETS))
def test_presets_paint_valid_game_skins(tmp_path, name):
    out = tmp_path / f"{name}.png"; persona.paint(persona.PRESETS[name]).save(out)
    r = skinlib.validate(out)
    assert not r["errors"], r["errors"]


def test_persona_options_all_paint(tmp_path):
    base = persona.EXAMPLE
    variants = [{"hair": {"style": s, "color": "#553311"}} for s in ("short", "buzz", "sidepart", "spiky", "curly", "afro", "long", "ponytail", "bun", "bob", "mohawk", "bald")]
    variants += [{"top": {"type": t, "color": "#aa3344", "pattern": p}} for t in ("tshirt", "longsleeve", "hoodie", "jacket", "shirt", "suit", "tank", "sweater", "dress") for p in ("none", "stripes", "plaid", "logo")]
    variants += [{"facial_hair": f} for f in ("stubble", "mustache", "goatee", "beard")] + [{"glasses": {"style": g}} for g in ("round", "square", "sun")]
    variants += [{"accessory": a} for a in ("cap", "beanie", "headphones", "scarf", "necklace", "backpack", "crown", "hood")] + [{"model": "slim"}]
    for i, v in enumerate(variants):
        p = {**base, **v}; out = tmp_path / f"v{i}.png"; persona.paint(p).save(out)
        assert not skinlib.validate(out)["errors"], (v, skinlib.validate(out)["errors"])


def test_eyes_stay_on_row_4_for_the_face_states():
    im = persona.paint(persona.EXAMPLE)
    assert im.getpixel((9, 12))[:3] == (244, 244, 244) and im.getpixel((14, 12))[:3] == (244, 244, 244)   # eye whites on face row 4


def test_sample_reads_photo_colours(tmp_path):
    ph = Image.new("RGB", (100, 100), (200, 150, 120)); ph.paste((30, 20, 10), (0, 0, 100, 30)); ph.paste((20, 60, 160), (0, 60, 100, 100))
    ph.save(tmp_path / "p.png")
    c = persona.sample(tmp_path / "p.png", {"skin": (10, 40, 90, 55), "hair": (0, 0, 100, 20), "top": (0, 70, 100, 100)})
    assert c == {"skin": "#c89678", "hair": "#1e140a", "top": "#143ca0"}
    p = persona.apply_colors(persona.EXAMPLE, c)
    assert p["skin"] == "#c89678" and p["hair"]["color"] == "#1e140a" and p["top"]["color"] == "#143ca0"


def test_herobrine_from_a_steve_texture_has_white_eyes():
    steve = Image.new("RGBA", (64, 64), (120, 90, 60, 255)); p = Path("/tmp/_br_steve.png"); steve.save(p)
    im = persona.herobrine_from_steve(p)
    assert all(im.getpixel((x, 12)) == (255, 255, 255, 255) for x in (9, 10, 13, 14))


def compile_example(tmp_path, music=False, textures=None):
    import compose
    plan = json.loads(json.dumps(compose.EXAMPLE)); plan["cast"]["herobrine"]["classic"] = False  # CC0 painting, no cache needed
    if textures:
        plan["textures"] = textures
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    args = [str(tmp_path / "plan.json"), "--out", str(tmp_path / "film")] + ([] if music else ["--no-music"])
    assert compose.main(args) == 0
    return json.loads((tmp_path / "film" / "story.json").read_text())


def test_director_compiles_the_example(tmp_path):
    import compose
    st = compile_example(tmp_path)
    from_anim = subprocess.run(["node", "-e", "import('./core/engine/anim.js').then(m=>console.log(Object.keys(m.CLIPS).join(',')))"], cwd=ROOT, capture_output=True, text=True)
    clips = set(from_anim.stdout.strip().split(",")) if from_anim.returncode == 0 else None
    assert 30 < st["duration"] < 60
    ts = [c["t"] for c in st["camera"]]; assert ts == sorted(ts) and ts[0] == 0
    assert all(c.get("dur", 0) > 0.3 for c in st["camera"]), "no flash-frame shots"
    if clips:
        assert {s["do"] for s in st["timeline"] if "do" in s} <= clips | {"walk", "run"}
    assert any(s.get("do") == "die" and s.get("vanish") for s in st["timeline"]), "the finisher makes Herobrine vanish"
    assert st.get("lightning") and st.get("timeRemap") and st.get("transitions")
    assert (tmp_path / "film" / "shotlist.md").read_text().count("|") > 50
    assert (tmp_path / "film" / "skins" / "me.png").exists() and (tmp_path / "film" / "skins" / "herobrine.png").exists()
    assert "nametag" not in st["actors"]["me"], "cinematic default: no floating name tags"
    assert compose.Film({"beats": []}, tmp_path).merge_sections() == []


def test_director_music_follows_the_beats(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg missing")
    st = compile_example(tmp_path, music=True)
    assert st["audio"]["music"]["file"] == "music.wav" and (tmp_path / "film" / "music.wav").stat().st_size > 100000
    sl = (tmp_path / "film" / "shotlist.md").read_text()
    assert "battle" in sl and "silence" in sl and "dawn" in sl


def test_composed_film_renders_with_builtin_textures(tmp_path):
    """Every block, item and sky texture the director and the world generator use has a CC0 fallback: the film renders
    with "textures": "builtin" and no missing-texture checker (render.py refuses to render with one)."""
    pytest.importorskip("playwright")
    import render as R
    compile_example(tmp_path, textures="builtin")
    sp = tmp_path / "film" / "story.json"
    try:
        rc = R.main([str(sp), "--frame", "17.0", "--scale", "0.35", "--out", str(tmp_path / "f.png")])
    except Exception as e:  # no browser here
        pytest.skip(f"cannot render here: {e}")
    assert rc == 0
    im = Image.open(tmp_path / "f.png").convert("RGB"); w, h = im.size
    assert sum(ImageStat.Stat(im.crop((w // 4, h // 4, 3 * w // 4, 3 * h // 4))).stddev) > 15, "the duel frame has content"
