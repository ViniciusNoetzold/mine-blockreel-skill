import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import render
import export


def test_reels_profile_leaves_landscape_unchanged(tmp_path):
    path = tmp_path / "story.json"
    story = {
        "size": [1280, 720], "fps": 24, "duration": 60, "styleOverride": {"letterbox": 2.05},
        "camera": [{"t": 0, "fov": 44}, {"t": 2.5, "fov": 58, "shake": 0.1}],
        "reels": {"camera": [{"t": 2.5, "fov": 65}], "safeArea": {"bottom": 0.3}},
    }
    path.write_text(json.dumps(story), encoding="utf-8")
    reel, portrait = render.prepare_story(path, story, reels=True)
    other, wide = render.prepare_story(path, story, size=(1920, 1080))
    assert reel.parent == path.parent and other.parent == path.parent and reel != other
    assert json.loads(reel.read_text(encoding="utf-8")) == portrait
    assert portrait["size"] == [1080, 1920]
    assert portrait["fps"] == 30 and portrait["duration"] == 60
    assert portrait["styleOverride"]["letterbox"] is False
    assert portrait["reelsLayout"]["bottom"] == 0.3
    assert portrait["camera"] == [{"t": 0, "fov": 44}, {"t": 2.5, "fov": 65, "shake": 0.1}]
    assert wide["styleOverride"] == {"letterbox": 2.05} and wide["camera"] == story["camera"]
    assert json.loads(path.read_text(encoding="utf-8")) == story


@pytest.mark.parametrize("config, message", [
    ({"camera": [{"t": 0}, {"t": 0}]}, "unique existing shot start"),
    ({"camera": [{"t": 1}]}, "unique existing shot start"),
    ({"safeArea": {"top": 0.4, "bottom": 0.4}}, "at least 40%"),
])
def test_invalid_reels_overrides(config, message):
    with pytest.raises(ValueError, match=message):
        render.reels_overrides({"camera": [{"t": 0}], "reels": config})


def test_export_reels_calls_portrait_renderer(monkeypatch):
    calls = []
    monkeypatch.setattr(export.subprocess, "run", lambda cmd: calls.append(cmd) or SimpleNamespace(returncode=0))
    assert export.main(["reels", "story.json", "--out", "reel.mp4", "--start", "3", "--end", "12"]) == 0
    assert calls[0][2:] == ["story.json", "--preset", "reels", "--out", "reel.mp4", "--workers", "1", "--start", "3.0", "--end", "12.0"]
