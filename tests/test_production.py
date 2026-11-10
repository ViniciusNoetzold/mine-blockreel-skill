"""v0.3 production tools: subtitles export, speech envelopes for audio lip-sync, render copies with a size override, GIF export."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def test_srt_has_chat_lines_and_times():
    import export
    out = export.srt({"subtitles": [{"t": 61.25, "dur": 2, "who": "Herobrine", "text": "Volte."}, {"t": 1, "text": "FIM"}]})
    assert out.startswith("1\n00:00:01,000 --> 00:00:03,000\nFIM") and "00:01:01,250 --> 00:01:03,250\nHerobrine: Volte." in out


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg missing")
def test_speech_envelope_follows_the_voice(tmp_path):
    import render
    # 0.5 s of silence, then 0.5 s of a loud tone: the envelope must be low then high
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "0.5", str(tmp_path / "s.wav")], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=220:r=16000", "-t", "0.5", str(tmp_path / "v.wav")], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(tmp_path / "s.wav"), "-i", str(tmp_path / "v.wav"), "-filter_complex", "concat=n=2:v=0:a=1", str(tmp_path / "line.wav")], check=True)
    story = {"audio": {"dialogue": [{"file": "line.wav", "t": 3.0, "actor": "hero"}, {"file": "line.wav", "t": 9.0}]}}
    env = render.speech_envelopes(story, tmp_path)
    assert len(env) == 1 and env[0]["actor"] == "hero" and env[0]["t"] == 3.0
    e = env[0]["env"]; assert max(e[:10]) < 0.1 and min(e[20:28]) > 0.5


def test_prepare_story_writes_a_render_copy_only_when_needed(tmp_path):
    import render
    sp = tmp_path / "story.json"; story = {"size": [1280, 720]}; sp.write_text(json.dumps(story))
    assert render.prepare_story(sp, story)[0] == sp
    p2, s2 = render.prepare_story(sp, story, (1080, 1920))
    assert p2 != sp and p2.name.startswith(".") and json.loads(p2.read_text())["size"] == [1080, 1920] and s2["size"] == [1080, 1920]


def test_render_range_propagates_encoder_failure(tmp_path, monkeypatch):
    import io
    from contextlib import nullcontext
    from unittest.mock import Mock

    import render
    playwright = pytest.importorskip("playwright.sync_api")
    browser, page = Mock(), Mock()
    page.screenshot.return_value = b"frame"
    encoder = Mock(stdin=io.BytesIO(), args=["ffmpeg"])
    encoder.wait.return_value = 1
    monkeypatch.setattr(playwright, "sync_playwright", nullcontext)
    monkeypatch.setattr(render, "serve", lambda _: (None, 0))
    monkeypatch.setattr(render, "open_page", lambda *_: (browser, page))
    monkeypatch.setattr(render.subprocess, "Popen", lambda *_, **__: encoder)
    with pytest.raises(subprocess.CalledProcessError):
        render.render_range(tmp_path / "story.json", {}, 30, 1, 0, 1, tmp_path / "film.mp4", 18, False)
    browser.close.assert_called_once()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg missing")
def test_gif_export(tmp_path):
    import export
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=s=320x180:r=30", "-t", "2", str(tmp_path / "v.mp4")], check=True)
    assert export.main(["gif", str(tmp_path / "v.mp4"), "--dur", "1", "--width", "160", "--out", str(tmp_path / "c.gif")]) == 0
    from PIL import Image
    im = Image.open(tmp_path / "c.gif"); assert im.size[0] == 160 and getattr(im, "n_frames", 1) >= 8
