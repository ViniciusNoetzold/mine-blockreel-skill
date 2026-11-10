import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def test_compiler_frames_a_wolf_lead_and_short_cast_member(tmp_path):
    from compose import Film

    plan = {
        "textures": "builtin",
        "world": [{"fill": ["grass", [-8, 0, -8], [8, 0, 8]]}],
        "arena": {"center": [0, 0], "radius": 8, "y": 0},
        "cast": {"luna": {"mob": "wolf", "parts": ["collar"]}, "scout": {"height": 1.15}},
        "beats": [
            {"beat": "walk", "who": "luna", "to": [3, 3.5]},
            {"beat": "act", "who": "luna", "do": "howl", "shot": "close"},
            {"beat": "act", "who": "scout", "do": "wave", "shot": "close"},
        ],
    }
    story = Film(plan, tmp_path).build(music=False)
    wolf, scout = story["actors"]["luna"], story["actors"]["scout"]
    assert (wolf["type"], wolf["rig"], wolf["parts"]) == ("wolf", "builtin", ["collar"])
    assert "texture" not in wolf  # the built-in coat does not need a cached asset
    assert scout["height"] == 1.15
    wolf_close, scout_close = story["camera"][1:]
    assert wolf_close["look"]["offset"][0] > 0.6  # wolf just moved east; the muzzle sits ahead of its feet
    assert wolf_close["pos"]["offset"][0] > wolf_close["look"]["offset"][0]
    assert 0.9 < wolf_close["look"]["offset"][1] < 1.05
    assert scout_close["look"]["offset"][1] == pytest.approx(1.62 * 1.15 / 2, abs=0.001)


@pytest.mark.parametrize("size", [{"height": 0}, {"height": "1.15"}, {"scale": True}, {"scale": 1, "height": 1}])
def test_compiler_rejects_invalid_cast_size(tmp_path, size):
    from compose import Film

    with pytest.raises(SystemExit, match="cast 'scout': (height|scale|choose)"):
        Film({"cast": {"scout": size}}, tmp_path).build(music=False)


def test_rendered_wolf_jumps_and_short_player_clears_low_roof(tmp_path):
    pw_api = pytest.importorskip("playwright.sync_api")
    from render import open_page, serve

    player = {"skin": "/core/builtin/skins/hero.png"}
    story = {
        "size": [384, 216], "duration": 3, "textures": "builtin",
        "world": [
            {"fill": ["grass", [-8, 0, -8], [8, 0, 8]]},
            {"set": ["stone", [3, 2, 0]]}, {"set": ["stone", [-4, 2, 0]]},
        ],
        "actors": {
            "luna": {"type": "wolf", "pos": [0.5, 1, 0.5]},
            "short": {**player, "pos": [3.5, 1, 0.5], "height": 0.8},
            "tall": {**player, "pos": [-3.5, 1, 0.5]},
        },
        "timeline": [
            {"actor": "luna", "t": 0.4, "do": "jump", "dur": 1, "height": 0.5},
            {"actor": "luna", "t": 1.5, "do": "howl", "dur": 1},
        ],
        "camera": [
            {"t": 0, "dur": 2.6, "pos": [2, 2.15, 3.5], "look": [0.5, 1.7, 0.6]},
            {"t": 2.6, "first": "short"},
        ],
    }
    story_path = tmp_path / "story.json"
    story_path.write_text(json.dumps(story), encoding="utf-8")
    server, port = serve(tmp_path)
    try:
        with pw_api.sync_playwright() as pw:
            try:
                browser, page = open_page(pw, port, story_path, story, 1, False)
            except pw_api.Error as exc:
                if "Executable doesn't exist" in str(exc):
                    pytest.skip("Playwright Chromium is not installed")
                raise
            try:
                before = page.screenshot()
                assert page.evaluate("window.__actorPos('luna', 0.9)") == [0.5, 1.5, 0.5, "jump"]
                page.evaluate("window.renderAt(2)")
                howl = page.screenshot()
                assert howl != before
                page.evaluate("window.renderAt(0.9); window.renderAt(2)")
                assert page.screenshot() == howl
                assert page.evaluate("window.__qa(2.7).camera[1]") == pytest.approx(1 + 1.62 * 0.4, abs=0.02)
                hits = page.evaluate("window.__pathCheck()")["actors"]
                assert {hit["actor"] for hit in hits} == {"tall"}
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
