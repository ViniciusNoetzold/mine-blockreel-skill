"""Project-local equipment assets survive compilation and show up in rendered frames."""
import io
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import compose
import render


def equipment_project(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    (src / "gear").mkdir()
    sprite = Image.new("RGBA", (20, 28))
    ImageDraw.Draw(sprite).polygon([(5, 0), (15, 0), (19, 19), (10, 27), (0, 19)], fill=(50, 250, 20, 255))
    sprite.save(src / "gear" / "wand.png")
    Image.new("RGBA", (64, 32), (240, 40, 200, 255)).save(src / "gear" / "cape.png")
    return src


def test_compile_equipment_assets(tmp_path):
    src = equipment_project(tmp_path)
    plan = {
        "_dir": str(src),
        "textures": "builtin",
        "cast": {"actor": {"cape": {"texture": "gear/cape.png"}, "holding": "forest:wand"}},
        "items": {"forest:wand": {"texture": "gear/wand.png", "grip": [0.5, 0.8]}},
        "beats": [{"beat": "act", "who": "actor", "do": "idle", "cape": None}],
    }
    output = tmp_path / "output"
    story = compose.Film(plan, output).build(music=False)
    assert (output / "gear" / "cape.png").read_bytes() == (src / "gear" / "cape.png").read_bytes()
    assert (output / "gear" / "wand.png").read_bytes() == (src / "gear" / "wand.png").read_bytes()
    assert story["items"] == plan["items"]
    assert story["timeline"][0]["cape"] is None
    plan["items"]["forest:wand"]["texture"] = "../wand.png"
    with pytest.raises(ValueError, match="project-relative PNG"):
        compose.Film(plan, output).build(music=False)


def test_mod_sprite_and_cape_switch_in_render(tmp_path):
    src = equipment_project(tmp_path)
    story = {
        "size": [384, 240],
        "duration": 3,
        "textures": "builtin",
        "styleOverride": {"letterbox": False},
        "items": {"forest:wand": {"texture": "gear/wand.png", "size": 0.75, "grip": [0.5, 0.8]}},
        "actors": {"actor": {
            "skin": "/core/builtin/skins/hero.png", "pos": [0.5, 1, 0.5],
            "holding": "forest:wand", "cape": {"texture": "gear/cape.png", "sway": 0},
        }},
        "world": [{"fill": ["stone", [-4, 0, -4], [4, 0, 4]]}],
        "camera": [{"t": 0, "dur": 3, "pos": [-3.5, 2.3, -2.6], "look": [0.5, 2, 0.5], "fov": 32}],
        "timeline": [{"t": 1, "actor": "actor", "cape": None}, {"t": 2, "actor": "actor", "holding": None}],
    }
    source = src / "story.json"
    source.write_text(json.dumps(story), encoding="utf-8")
    server, port = render.serve(src)
    try:
        with sync_playwright() as pw:
            browser, page = render.open_page(pw, port, source, story, 1, False)
            try:
                def frame_at(t):
                    page.evaluate("renderAt", t)
                    return Image.open(io.BytesIO(page.screenshot())).convert("RGB")

                def cape_pixels(im):
                    r, g, b = np.asarray(im, dtype=np.int16).transpose(2, 0, 1)
                    return np.count_nonzero((r > 100) & (r > g * 2) & (b > g * 2))

                def wand_pixels(im):
                    r, g, b = np.asarray(im, dtype=np.int16).transpose(2, 0, 1)
                    return np.count_nonzero((g > 100) & (g > r * 2) & (g > b * 2))

                visible = frame_at(0.25)
                cape_removed = frame_at(1.25)
                both_removed = frame_at(2.25)
                assert cape_pixels(visible) > 100
                assert cape_pixels(cape_removed) < 10
                assert wand_pixels(cape_removed) > 100
                assert wand_pixels(both_removed) < 10
                assert frame_at(0.25).tobytes() == visible.tobytes()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_sword_head_qa_uses_pose_visibility_and_opaque_pixels(tmp_path):
    Image.new("RGBA", (16, 16)).save(tmp_path / "transparent.png")
    third_person = {"pos": [-3.5, 2.3, -2.6], "look": [0.5, 2, 0.5], "fov": 32}
    story = {
        "size": [320, 180], "duration": 3, "textures": "builtin",
        "actors": {"hero": {
            "skin": "/core/builtin/skins/hero.png", "model": "classic",
            "pos": [0.5, 1, 0.5], "height": 1.4, "holding": "diamond_sword",
        }},
        "items": {"test:transparent_sword": {"texture": "transparent.png"}},
        "world": [{"fill": ["stone", [-4, 0, -4], [4, 0, 4]]}],
        "camera": [
            {"t": 0, **third_person},
            {"t": 1.2, "first": "hero"},
            {"t": 1.6, **third_person},
        ],
        "timeline": [
            {"t": 0.5, "actor": "hero", "do": "guard", "dur": 2.4},
            {"t": 2.25, "actor": "hero", "do": "guard", "dur": 0.75, "holding": "test:transparent_sword"},
        ],
    }
    source = tmp_path / "story.json"
    source.write_text(json.dumps(story), encoding="utf-8")
    with render.render_page(source, story, 1, False) as page:
        swords = page.evaluate("window.__pathCheck(0.05).swords")
    assert len(swords) == 2
    for hit in swords:
        assert (hit["actor"], hit["item"], hit["hand"]) == ("hero", "diamond_sword", "right")
    assert 0.5 <= swords[0]["t0"] < 0.8
    assert swords[0]["t1"] == 1.2
    assert swords[1]["t0"] == 1.6
    assert swords[1]["t1"] == 2.25
