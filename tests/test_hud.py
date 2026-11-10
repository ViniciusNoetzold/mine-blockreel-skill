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


@pytest.mark.parametrize("portrait", [False, True], ids=["landscape", "reels"])
def test_render_crafting_and_chat_seek(tmp_path, portrait):
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
            "inventory": ["oak_log"],
            "chat": {"messages": [{"t": 0.5, "text": "Lia foi explodida por um Creeper", "dur": 4}]},
            "events": [
                {"type": "craft", "t": 0, "dur": 0.5, "gridSize": 2, "grid": ["oak_log"],
                 "result": {"item": "planks", "count": 4}, "takeAt": 0.25, "toSlot": 2},
                {"type": "craft", "t": 1, "dur": 3, "grid": ["stick"],
                 "result": "demo:pickaxe", "takeAt": 3, "toSlot": 1},
            ],
        },
    }
    if portrait:
        story.update({
            "size": [360, 640],
            "styleOverride": {"letterbox": False},
            "reelsLayout": {"left": 0.08, "right": 0.16, "top": 0.12, "bottom": 0.25},
            "titles": [{"t": 4.1, "dur": 0.65, "text": "UM TÍTULO EXTENSO DENTRO DA ÁREA SEGURA"}],
            "subtitles": [{"t": 4.8, "dur": 1.2, "who": "Lia",
                           "text": "Uma legenda longa com supercalifragilisticexpialidocious."}],
        })
        story["hud"]["chat"]["messages"].append({"t": 4.7, "text": "A noite caiu.", "dur": 1.2})

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
                def inside_safe_area(selector):
                    boxes = [locator.bounding_box() for locator in page.locator(selector).all()]
                    assert boxes
                    for box in boxes:
                        assert box is not None
                        assert box["x"] >= 360 * 0.08 - 1
                        assert box["x"] + box["width"] <= 360 * (1 - 0.16) + 1
                        assert box["y"] >= 640 * 0.12 - 1
                        assert box["y"] + box["height"] <= 640 * (1 - 0.25) + 1
                    return boxes[0]

                panel = page.locator(".br-hud-panel")
                grid = panel.locator(".br-hud-craft .br-hud-grid").first
                page.evaluate("window.renderAt(0.15)")
                assert grid.locator(".br-hud-slot").count() == 4
                assert grid.locator("img[alt='oak_log']").count() == 1
                page.evaluate("window.renderAt(0.3)")
                assert grid.locator(".br-hud-slot").count() == 4
                assert not grid.locator("img").count()
                assert panel.locator("img[alt='planks']").count() == 1

                page.evaluate("window.renderAt(2)")
                assert grid.locator(".br-hud-slot").count() == 9
                assert panel.is_visible() and "Criação" in panel.text_content()
                preview = panel.locator("img[alt='demo:pickaxe']")
                assert preview.evaluate("(img) => img.complete && img.naturalWidth === 16")
                assert page.locator(".br-hud-hotbar").is_hidden()
                assert page.locator(".br-hud-line").text_content() == "Lia foi explodida por um Creeper"
                if portrait:
                    inside_safe_area(".br-hud-panel")
                before = page.screenshot()

                page.evaluate("window.renderAt(3.5)")
                assert not panel.locator(".br-hud-craft img").count()
                assert panel.locator("img[alt='demo:pickaxe']").count() == 1

                page.evaluate("window.renderAt(5)")
                bar = page.locator(".br-hud-hotbar")
                assert panel.is_hidden() and bar.is_visible()
                assert bar.locator("img[alt='demo:pickaxe']").count() == 1
                if portrait:
                    bar_box = inside_safe_area(".br-hud-hotbar")
                    sub_box = inside_safe_area("#sub span")
                    inside_safe_area("#sub canvas")
                    chat_box = inside_safe_area(".br-hud-chat")
                    assert chat_box["y"] + chat_box["height"] <= sub_box["y"]
                    assert sub_box["y"] + sub_box["height"] <= bar_box["y"]
                    assert not page.evaluate("window.__qa(5).subtitle.clipped")
                    page.evaluate("window.renderAt(4.4)")
                    inside_safe_area("#title canvas")
                else:
                    assert page.locator(".br-hud-line").count() == 0

                page.evaluate("window.renderAt(2)")
                assert page.screenshot() == before
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
