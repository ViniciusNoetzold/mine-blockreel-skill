import json
import math
import shutil
import struct
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import audio  # noqa: E402

SR = 22050


def tone(path, freq, secs, amp=0.5):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(32767 * amp * math.sin(2 * math.pi * freq * i / SR))) for i in range(int(SR * secs))))


def goertzel(samples, freq):
    k = 2 * math.cos(2 * math.pi * freq / 44100); s1 = s2 = 0.0
    for x in samples:
        s0 = x + k * s1 - s2; s2, s1 = s1, s0
    return math.sqrt(max(0.0, s1 * s1 + s2 * s2 - k * s1 * s2)) / len(samples) * 2


def read(path):
    with wave.open(str(path)) as w:
        raw = w.readframes(w.getnframes()); ch = w.getnchannels()
        xs = struct.unpack("<%dh" % (len(raw) // 2), raw)
        return [x / 32768 for x in xs[::ch]], w.getframerate()


def test_filter_graph_shape(tmp_path):
    story = {"duration": 10, "audio": {"music": {"file": "m.wav", "duck": {"amount": 0.3}}, "sfx": [{"file": "s.wav", "t": 2}], "dialogue": [{"file": "d.wav", "t": 4}]}}
    inputs, fc, label = audio.build(story, tmp_path)
    assert label == "[aout]" and inputs.count("-i") == 3
    assert "adelay=2000|2000" in fc and "adelay=4000|4000" in fc and "sidechaincompress" in fc
    assert audio.build({"duration": 5}, tmp_path) is None
    # legacy "music": "file" still works
    assert audio.build({"duration": 5, "music": "m.wav"}, tmp_path) is not None


def test_ducking_and_timing_in_a_real_mix(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    tone(tmp_path / "m.wav", 440, 10); tone(tmp_path / "d.wav", 1000, 2); tone(tmp_path / "s.wav", 800, 0.5)
    story = {"duration": 10, "audio": {"music": {"file": "m.wav", "volume": 0.8, "fadeIn": 0.1, "fadeOut": 0.1, "duck": {"amount": 0.3}},
                                       "dialogue": [{"file": "d.wav", "t": 3}], "sfx": [{"file": "s.wav", "t": 6}]}}
    out = tmp_path / "mix.wav"
    assert audio.render_audio(story, tmp_path, out)
    xs, sr = read(out)
    seg = lambda a, b: xs[int(a * sr):int(b * sr)]
    free = goertzel(seg(1.0, 2.0), 440)          # music alone
    ducked = goertzel(seg(3.6, 4.6), 440)         # music while the dialogue plays
    assert free > 0.1 and ducked < free * 0.75, (free, ducked)
    assert goertzel(seg(3.4, 4.6), 1000) > 0.1    # dialogue is audible at 3 s
    assert goertzel(seg(1.0, 2.5), 1000) < 0.02   # and absent before it
    assert goertzel(seg(6.05, 6.45), 800) > 0.1   # sfx at 6 s
    assert goertzel(seg(1.0, 2.5), 800) < 0.02


def test_score_follows_sections(tmp_path):
    """tools/score.py writes a stereo wav of the right length, with a real silence window and a louder battle than calm."""
    import subprocess, sys, wave
    import numpy as np
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    out = tmp_path / "s.wav"
    subprocess.run([sys.executable, str(root / "tools" / "score.py"), "--out", str(out), "--duration", "12",
                    "--sections", "calm:0:4,battle:4:8,silence:8:10,dawn:10:12"], check=True)
    with wave.open(str(out)) as w:
        assert w.getnchannels() == 2 and abs(w.getnframes() / w.getframerate() - 12) < 0.01
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2)[:, 0].astype(float)
    sr = 44100; rms = lambda a, b: float(np.sqrt(np.mean(x[int(a * sr):int(b * sr)] ** 2)))
    assert rms(8.5, 9.9) < 1.0
    assert rms(5, 7.5) > rms(1, 3.5) > 0
