#!/usr/bin/env python3
"""Compose an ORIGINAL background score that follows a film's energy shape (no samples, no downloads, safe to publish).

  python tools/score.py --out music.wav --duration 30 \
      --sections calm:0:7,build:7:14.8,battle:14.8:23.4,silence:23.4:26.2,dawn:26.2:30 --bpm 96 --key A

Section moods:
  calm    dark pad + slow bass (minor progression i-VI-III-VII)
  build   adds an 8th-note pluck ostinato and a heartbeat drum on beats 1 and 3
  battle  adds taiko-like drums on every beat, a snare on 2 and 4, louder pad and bass
  silence nothing (the film's held beat)
  dawn    a warm major progression (IV-I-V-I) with a slow melody, swelling in
Everything is synthesised with numpy (additive pads, decaying plucks, pitch-dropping drums), so the output is yours to use.
"""
import argparse
import wave

import numpy as np

SR = 44100
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(semi_from_a4):
    return 440.0 * 2 ** (semi_from_a4 / 12)


def tone(f, dur, harm=6, bright=0.55, attack=0.01, release=0.3, decay=None):
    t = np.arange(int(dur * SR)) / SR
    w = sum((bright ** (k - 1)) / k * np.sin(2 * np.pi * f * k * t + k) for k in range(1, harm + 1))
    env = np.minimum(1, t / max(attack, 1e-3)) * np.minimum(1, (dur - t) / max(release, 1e-3))
    if decay:
        env *= np.exp(-t / decay)
    return w * np.clip(env, 0, 1)


def drum(dur=0.6, f0=140, f1=45, noise=0.25, decay=0.18):
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.05)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay)
    return body + noise * np.random.default_rng(3).standard_normal(len(t)) * np.exp(-t / 0.03)


def snare(dur=0.3):
    t = np.arange(int(dur * SR)) / SR
    n = np.random.default_rng(5).standard_normal(len(t))
    n = np.convolve(n, [1, -0.9], "same")  # crude high-pass
    return (0.6 * n + 0.4 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t / 0.07)


def add(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def compose(duration, sections, bpm, key):
    out = np.zeros(int(duration * SR) + SR)
    root = NOTE[key] - 9 - 24  # semitones from A4 to the key's root two octaves down
    minor = [(0, [0, 3, 7]), (8, [0, 4, 7]), (3, [0, 4, 7]), (10, [0, 4, 7])]   # i VI III VII
    major = [(5, [0, 4, 7]), (0, [0, 4, 7]), (7, [0, 4, 7]), (0, [0, 4, 7])]    # IV I V I (on the relative major's 3rd up)
    beat = 60 / bpm; bar = 4 * beat
    melody = [7, 9, 12, 11, 12, 16, 14, 12]
    for mood, s0, s1 in sections:
        if mood == "silence" or s1 - s0 < 0.05:
            continue
        prog = major if mood == "dawn" else minor
        shift = 3 if mood == "dawn" else 0  # dawn: relative major (C for A minor)
        t = s0; b = 0
        while t < s1 - 0.05:
            seg = min(bar, s1 - t)
            deg, chord = prog[b % 4]
            base = root + shift + deg
            g_pad = {"calm": 0.10, "build": 0.12, "battle": 0.16, "dawn": 0.13}[mood]
            for c in chord:
                add(out, tone(hz(base + 24 + c), seg + 0.4, harm=7, bright=0.6, attack=0.6 if mood != "battle" else 0.15, release=0.5), t, g_pad / 3)
            add(out, tone(hz(base + 12), seg, harm=3, bright=0.4, attack=0.05, release=0.2), t, {"calm": 0.16, "build": 0.18, "battle": 0.24, "dawn": 0.14}[mood])
            if mood in ("build", "battle"):
                for k in range(8):  # 8th-note ostinato on the chord tones
                    n = base + 36 + chord[[0, 1, 2, 1][k % 4]]
                    add(out, tone(hz(n), beat / 2 + 0.3, harm=4, bright=0.5, attack=0.003, release=0.1, decay=0.18), t + k * beat / 2, 0.07 if mood == "build" else 0.09)
            for k in range(4):
                bt = t + k * beat
                if bt >= s1:
                    break
                if mood == "build" and k in (0, 2):
                    add(out, drum(f0=90, f1=40, noise=0.05, decay=0.22), bt, 0.35)
                if mood == "battle":
                    add(out, drum(), bt, 0.55)
                    if k % 2 == 1:
                        add(out, snare(), bt, 0.25)
                    if k == 3:
                        add(out, drum(f0=180, f1=70, decay=0.1), bt + beat / 2, 0.3)
            if mood == "dawn":
                for k in range(2):
                    n = base + 36 + melody[(b * 2 + k) % len(melody)] - 7
                    add(out, tone(hz(n), beat * 2.2, harm=5, bright=0.45, attack=0.08, release=0.6), t + k * beat * 2, 0.08)
            t += bar; b += 1
        # fade each section's edges
        i0, i1 = int(s0 * SR), min(len(out), int(s1 * SR) + int(0.5 * SR))
        ramp = int(0.6 * SR) if mood in ("calm", "dawn") else int(0.05 * SR)
        out[i0:i0 + ramp] *= np.linspace(0, 1, min(ramp, i1 - i0))[: len(out[i0:i0 + ramp])]
    # hard silence windows
    for mood, s0, s1 in sections:
        if mood == "silence":
            i0, i1 = int(s0 * SR), int(s1 * SR); tail = int(0.35 * SR)
            out[i0:i0 + tail] *= np.linspace(1, 0, tail); out[i0 + tail:i1] = 0
    out = out[: int(duration * SR)]
    fade = int(1.0 * SR); out[-fade:] *= np.linspace(1, 0, fade)
    out /= max(1e-9, np.abs(out).max()) / 0.8
    # simple stereo: a little delay on the right channel
    right = np.concatenate([np.zeros(int(0.012 * SR)), out[: -int(0.012 * SR)]])
    return np.stack([out, 0.85 * out + 0.15 * right], axis=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True); ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--sections", required=True, help="mood:start:end,... (calm build battle silence dawn)")
    ap.add_argument("--bpm", type=float, default=96); ap.add_argument("--key", default="A", choices=list(NOTE))
    a = ap.parse_args(argv)
    secs = [(m, float(s0), float(s1)) for m, s0, s1 in (x.split(":") for x in a.sections.split(","))]
    pcm = (compose(a.duration, secs, a.bpm, a.key) * 32767).astype("<i2")
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print("wrote", a.out)


if __name__ == "__main__":
    main()
