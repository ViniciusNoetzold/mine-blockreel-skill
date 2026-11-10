"""Opt-in HUD regression tests at the model, compiler, and render entry points."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def test_hud_timeline_in_node():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    result = subprocess.run(["node", "tests/hud_check.mjs"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("then,auto,emits", [("die", True, True), ("fall", True, False), ("die", False, False)])
def test_creeper_chat_requires_lethal_result_and_opt_in(tmp_path, then, auto, emits):
    from compose import Film

    plan = {
        "cast": {
            "lia": {"name": "Lia"},
            "creeper": {"mob": "creeper"},
        },
        "marks": {"lia": [0, 1], "creeper": [0, -2]},
        "hud": {"chat": {"auto": auto, "exploded": "{name} foi explodida por um Creeper"}},
        "beats": [{"beat": "creeper", "who": "creeper", "target": "lia", "then": then}],
    }
    story = Film(plan, tmp_path).build(music=False)
    assert "messages" not in plan["hud"]["chat"]
    messages = story["hud"]["chat"].get("messages", [])
    if emits:
        assert messages == [{
            "t": story["changes"][0]["t"], "clock": "world", "text": "Lia foi explodida por um Creeper",
        }]
    else:
        assert not messages


def test_qa_samples_both_sides_of_collection():
    from qa import pick_times

    times = pick_times({"duration": 4, "hud": {"events": [
        {"type": "inventory", "t": 0.5, "dur": 0.2},
        {"type": "craft", "t": 1, "dur": 0.4, "takeAt": 1.2},
    ]}}, 2)
    assert any(0.5 < t < 0.7 for t in times)
    assert any(1 < t < 1.2 for t in times)
    assert any(1.2 < t < 1.4 for t in times)


def test_render_crafting_and_chat_seek(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    from render import open_page, serve

    assets = tmp_path / "items"
    assets.mkdir()
    shutil.copyfile(ROOT / "core" / "builtin" / "items" / "diamond_pickaxe.png", assets / "pickaxe.png")
    story = {
        "size": [640, 360], "fps": 24, "duration": 6, "textures": "builtin",
        "font": "css", "styleOverride": {"letterbox": True},
        "world": [{"fill": ["planks", [-4, 0, -4], [4, 0, 4]]}, {"set": ["crafting_table", [0, 1, 0]]}],
        "camera": [{"t": 0, "dur": 6, "pos": [2, 3, 6], "look": [0, 1, 0]}],
        "items": {"demo:pickaxe": {"texture": "items/pickaxe.png"}},
        "hud": {
            "labels": {"crafting": "Criação"},
            "hotbar": {"slots": ["stick"]},
            "chat": {"messages": [{"t": 0.5, "text": "Lia foi explodida por um Creeper", "dur": 4}]},
            "events": [{"type": "craft", "t": 1, "dur": 3, "grid": ["stick"],
                        "result": "demo:pickaxe", "takeAt": 3, "toSlot": 1}],
        },
    }
    file = tmp_path / "story.json"
    file.write_text(json.dumps(story), encoding="utf-8")
    server, port = serve(tmp_path)
    try:
        with playwright.sync_playwright() as pw:
            try:
                browser, page = open_page(pw, port, file, story, 1, False)
            except playwright.Error as exc:
                if "Executable doesn't exist" in str(exc):
                    pytest.skip("Chromium browser unavailable")
                raise
            try:
                page.evaluate("window.renderAt(2)")
                panel = page.locator(".br-hud-panel")
                assert panel.is_visible() and "Criação" in panel.text_content()
                preview = panel.locator("img[alt='demo:pickaxe']")
                assert preview.evaluate("(img) => img.complete && img.naturalWidth === 16")
                assert page.locator(".br-hud-hotbar").is_hidden()
                assert page.locator(".br-hud-line").text_content() == "Lia foi explodida por um Creeper"
                before = page.screenshot()

                page.evaluate("window.renderAt(3.5)")
                assert not panel.locator(".br-hud-craft img").count()
                assert panel.locator("img[alt='demo:pickaxe']").count() == 1

                page.evaluate("window.renderAt(5)")
                bar = page.locator(".br-hud-hotbar")
                assert panel.is_hidden() and bar.is_visible()
                assert bar.locator("img[alt='demo:pickaxe']").count() == 1
                assert page.locator(".br-hud-line").count() == 0

                page.evaluate("window.renderAt(2)")
                assert page.screenshot() == before
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
