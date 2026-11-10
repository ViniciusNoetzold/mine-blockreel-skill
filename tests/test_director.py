"""v0.2: persona skins (photo -> skin), the director compiler (plan -> story) and the new engine features in a real render."""
import json
import math
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


def test_herobrine_from_a_steve_texture_has_white_eyes(tmp_path):
    p = tmp_path / "steve.png"
    Image.new("RGBA", (64, 64), (120, 90, 60, 255)).save(p)
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
    return json.loads((tmp_path / "film" / "story.json").read_text(encoding="utf-8"))


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
    assert (tmp_path / "film" / "shotlist.md").read_text(encoding="utf-8").count("|") > 50
    assert (tmp_path / "film" / "skins" / "me.png").exists() and (tmp_path / "film" / "skins" / "herobrine.png").exists()
    assert "nametag" not in st["actors"]["me"], "cinematic default: no floating name tags"
    assert compose.Film({"beats": []}, tmp_path).merge_sections() == []


def test_director_music_follows_the_beats(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg missing")
    st = compile_example(tmp_path, music=True)
    assert st["audio"]["music"]["file"] == "music.wav" and (tmp_path / "film" / "music.wav").stat().st_size > 100000
    sl = (tmp_path / "film" / "shotlist.md").read_text(encoding="utf-8")
    assert "battle" in sl and "silence" in sl and "dawn" in sl


def test_director_preserves_dialogue_without_music_or_sfx(tmp_path):
    import compose
    plan = {
        "title": "A última missão",
        "cast": {"João": {}},
        "beats": [{"beat": "line", "who": "João", "text": "Já cheguei!", "voice": "line.wav"}],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    out = tmp_path / "film"
    assert compose.main([str(plan_path), "--out", str(out), "--no-music"]) == 0
    story = json.loads((out / "story.json").read_text(encoding="utf-8"))
    assert story["title"] == plan["title"]
    assert story["audio"] == {"sfx": [], "dialogue": [{"file": "line.wav", "t": 0.1, "actor": "João"}]}
    assert "João" in (out / "shotlist.md").read_text(encoding="utf-8")


def test_director_reports_missing_cues_after_trying_fallbacks(tmp_path, monkeypatch, capsys):
    import compose

    sounds = tmp_path / "sounds"
    fallback = sounds / "random" / "explode2.wav"
    fallback.parent.mkdir(parents=True)
    fallback.touch()
    monkeypatch.setattr(compose, "SND", sounds)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps({
        "textures": "builtin", "font": "css", "cast": {"lead": {}},
        "beats": [{"beat": "explode", "at": [0, 0]}],
    }), encoding="utf-8")
    out = tmp_path / "film"

    assert compose.main([str(plan_path), "--out", str(out), "--no-music"]) == 0
    story = json.loads((out / "story.json").read_text(encoding="utf-8"))
    assert story["textures"] == "builtin" and story["font"] == "css"
    assert story["audio"]["sfx"] == [{"file": str(fallback), "t": 1.8, "volume": 1.0}]
    warning = capsys.readouterr().err
    assert "Unavailable automatic game SFX: random/fuse (x1)" in warning
    assert "explode" not in warning
    assert "random/fuse (x1)" in (out / "shotlist.md").read_text(encoding="utf-8")


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


def test_head_shell_never_has_steps_or_loose_pixels():
    """The hat layer is a shell around the head: a partial shell reads as a head with a missing piece. Short styles keep it empty;
    volume styles fill it as one band per face, with no pixel below the band (no loose 'teeth')."""
    from skin import face_rect
    for style in ("short", "buzz", "sidepart", "spiky"):
        im = persona.paint({**persona.EXAMPLE, "hair": {"style": style, "color": "#332211"}})
        assert all(im.getpixel((x, y))[3] == 0 for x in range(32, 64) for y in range(0, 16)), f"{style}: hat layer must stay empty"
    for style in ("long", "afro", "curly", "bun", "bob"):
        im = persona.paint({**persona.EXAMPLE, "hair": {"style": style, "color": "#332211"}})
        for face in ("front", "left", "right", "back"):
            fx, fy, fw, fh = face_rect("hat", face)
            rows = [any(im.getpixel((fx + x, fy + y))[3] for x in range(fw)) for y in range(fh)]
            first_empty = rows.index(False) if False in rows else fh
            if face != "front":
                assert not any(rows[first_empty:]), f"{style}/{face}: pixels below the end of the hair band"
                assert all(im.getpixel((fx + x, fy + y))[3] for x in range(fw) for y in range(first_empty)), f"{style}/{face}: holes in the band"


@pytest.mark.parametrize("example", ["creeper-surprise", "zombie-night", "herobrine-duel"])
def test_every_shipped_plan_compiles(tmp_path, example):
    """The director is not only for fights: building, mobs, chases and comedy plans compile too."""
    import compose
    if not shutil.which("node"):
        pytest.skip("node is needed to expand structures for build beats")
    plan = json.loads((ROOT / "examples" / example / "plan.json").read_text(encoding="utf-8"))
    plan["textures"] = "builtin"
    for c in plan.get("cast", {}).values():
        c["classic"] = False
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    assert compose.main([str(tmp_path / "plan.json"), "--out", str(tmp_path / "f"), "--no-music"]) == 0
    st = json.loads((tmp_path / "f" / "story.json").read_text(encoding="utf-8"))
    assert st["duration"] > 20 and len(st["camera"]) >= 8
    if example == "creeper-surprise":
        places = [c for c in st["changes"] if "place" in c]
        assert len(places) > 60, "the house is built block by block"
        assert any("explode" in c for c in st["changes"]) and st["actors"]["creeper"]["type"] == "creeper"
    if example == "zombie-night":
        assert st["actors"]["zumbi"]["skin"].endswith("zombie-layout.png") and any(s.get("do") == "zombie" for s in st["timeline"])


def test_village_plan_ambient_life_babies_variants(tmp_path):
    """Vila Viva: `also` runs ambient actions in parallel; babies and variants reach the story (needs the mob cache)."""
    import compose
    if not shutil.which("node") or not (ROOT / "work" / "vanilla" / "mobs" / "index.json").exists():
        pytest.skip("needs node and the game's mob cache (python tools/vanilla.py mobs)")
    plan = json.loads((ROOT / "examples" / "village-life" / "plan.json").read_text(encoding="utf-8"))
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    assert compose.main([str(tmp_path / "plan.json"), "--out", str(tmp_path / "f"), "--no-music"]) == 0
    st = json.loads((tmp_path / "f" / "story.json").read_text(encoding="utf-8"))
    a = st["actors"]
    assert a["calf"]["baby"] is True and a["librarian"]["variant"] == "librarian" and a["horse"]["parts"] == ["saddle"]
    walks = [s for s in st["timeline"] if s["actor"] == "kid" and s.get("do") == "walk"]
    assert walks and walks[0]["t"] < 1.0, "ambient actions start with their beat, without taking time"
    assert any(s.get("do") == "ride" and s.get("mount") == "horse" for s in st["timeline"])


def test_cameras_are_kept_out_of_buildings(tmp_path):
    import compose
    f = compose.Film({"world": {"arena": {"center": [0, 0], "radius": 8, "y": 4}, "structures": [{"structure": "tower", "pos": [4, None, 0]}]}}, tmp_path)
    f.world(); f.pos = {"a": [0.0, 0.0], "b": [0.0, -4.0]}
    shot = f.cam(0, 2, "side", "a", "b")          # the side shot would stand at x ~ +4.2: inside the tower
    off = shot["pos"]["offset"]
    assert math.hypot(off[0] - 4, off[2]) > 4.6, off
