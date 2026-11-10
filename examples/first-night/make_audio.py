#!/usr/bin/env python3
"""Generate First Night's score, ambience and Foley from the timed cues."""

import json
import wave
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SR = 48_000
DURATION = 60
TAU = 2 * np.pi
SEED = 45097


def clock(duration):
    return np.arange(round(duration * SR)) / SR


def envelope(t, attack, release):
    return np.clip(t / attack, 0, 1) * np.clip((t[-1] - t) / release, 0, 1)


def noise(t, rng, rate):
    # Control points produce seeded, continuous noise with an adjustable bandwidth.
    count = int(t[-1] * rate) + 2
    return np.interp(t * rate, np.arange(count), rng.normal(0, 1, count))


def sine(t, hz):
    return np.sin(TAU * hz * t)


def add(mix, clip, start, gain=1, pan=0):
    i = round(start * SR)
    end = min(i + len(clip), len(mix))
    if end > i:
        direction = (pan + 1) * np.pi / 4
        mix[i:end] += clip[:end - i, None] * gain * np.array([np.cos(direction), np.sin(direction)])


def piano(midi, seconds=2.8):
    t = clock(seconds)
    hz = 440 * 2 ** ((midi - 69) / 12)
    tone = sum(
        sine(t, hz * k * (1 + 0.00035 * k * k)) * weight * np.exp(-t * (1.10 + k * 0.53))
        for k, weight in enumerate((0.88, 0.27, 0.16, 0.09, 0.04), 1)
    )
    return tone * envelope(t, 0.009, 0.5)


def bowed(midi, seconds, rng):
    t = clock(seconds)
    hz = 440 * 2 ** ((midi - 69) / 12)
    phase = TAU * (hz * t + 0.032 * sine(t, 4.3))
    bow = sum(np.sin(phase * k) * weight for k, weight in enumerate((0.68, 0.35, 0.21, 0.10), 1))
    return (bow * (0.83 + 0.17 * sine(t, 2.2)) + noise(t, rng, 1500) * 0.095) * envelope(t, 0.72, 0.64)


def beds(mix, rng):
    for t, seconds, gain, pan in (
        (0, 13, 0.062, -0.48), (0, 14, 0.057, 0.50),
        (10, 16, 0.045, -0.55), (11, 16, 0.042, 0.54),
        (25.5, 14.4, 0.057, -0.55), (25.8, 14.0, 0.053, 0.52),
    ):
        x = clock(seconds)
        gust = 0.65 + 0.25 * sine(x, 0.19) + 0.1 * sine(x, 0.37)
        leaves = (0.63 * noise(x, rng, 86) + 0.14 * noise(x, rng, 780) + 0.055 * noise(x, rng, 5200))
        add(mix, leaves * gust * envelope(x, 0.8, 1.5), t, gain, pan)
    for t, midi, gain, pan in (
        (0.60, 62, 0.096, -0.18), (2.12, 69, 0.090, 0.18), (3.35, 66, 0.078, -0.06),
        (5.22, 64, 0.083, 0.14), (6.89, 69, 0.063, 0.18), (8.22, 62, 0.095, -0.18),
        (12.40, 66, 0.057, -0.14), (15.65, 69, 0.053, 0.14), (18.90, 74, 0.068, 0.13),
        (21.18, 57, 0.048, -0.18), (24.05, 62, 0.060, -0.12),
        (52.47, 62, 0.076, -0.08), (53.67, 66, 0.067, 0.16), (54.92, 57, 0.050, -0.14),
    ):
        add(mix, piano(midi), t, gain, pan)
        add(mix, piano(midi), t + 0.086, gain * 0.14, -pan)
    for t, length, midi, gain, pan in (
        (25.25, 5.8, 38, 0.12, -0.36), (27.35, 5.1, 51, 0.083, 0.44),
        (30.42, 5.6, 38, 0.16, -0.22), (31.40, 5.7, 39, 0.10, 0.35),
        (34.68, 5.31, 38, 0.15, -0.34), (35.82, 4.08, 49, 0.11, 0.30),
    ):
        add(mix, bowed(midi, length, rng), t, gain, pan)
    for start, stop, step in ((28.8, 32, 0.68), (32, 39.3, 0.46)):
        for t in np.arange(start, stop, step):
            x = clock(0.19)
            add(mix, sine(x, 50) * np.exp(-15 * x) * envelope(x, 0.008, 0.035), t, 0.085)
    x = clock(12.3)
    cave = (0.64 * noise(x, rng, 48) + 0.28 * noise(x, rng, 150)) * envelope(x, 0.5, 0.8)
    add(mix, cave, 39.85, 0.034, -0.26)
    add(mix, cave, 39.91, 0.025, 0.42)
    for start, gain, pan in ((40.0, 0.38, -0.20), (45.36, 0.25, 0.16), (50.28, 0.28, -0.10)):
        add(mix, effect("breath_relief", rng), start, gain, pan)
    for i in range(20):
        at = 52.03 + 0.17 * i + rng.uniform(0, 0.15)
        add(mix, effect("torch_ignite", rng)[:round(0.10 * SR)], at, rng.uniform(0.024, 0.054), -0.43)


def transient(rng, seconds, hz, grit, bandwidth, decay):
    t = clock(seconds)
    knock = (0.37 * sine(t, hz) + 0.13 * sine(t, hz * 2.37)) * np.exp(-t * decay * 0.7)
    grain = grit * noise(t, rng, bandwidth) * np.exp(-t * decay)
    return (knock + grain) * envelope(t, 0.0024, min(0.06, seconds * 0.4))


def scatter(rng, offsets, gain, seconds, hz, grit, bandwidth, decay):
    result = np.zeros(round((offsets[-1] + seconds) * SR))
    for i, at in enumerate(offsets):
        tap = transient(rng, seconds, hz * rng.uniform(0.76, 1.2), grit, bandwidth, decay)
        start = round(at * SR)
        n = min(len(tap), len(result) - start)
        result[start:start + n] += tap[:n] * gain ** i
    return result


def chime(up=True):
    t = clock(0.24)
    p = TAU * ((460 if up else 680) * t + (850 if up else -580) * t * t)
    return (np.sin(p) + 0.31 * np.sin(2.01 * p)) * np.exp(-15 * t) * envelope(t, 0.005, 0.035) * 0.36


def effect(kind, rng, duration=None):
    if kind == "cloth":
        t = clock(0.42)
        return noise(t, rng, 740) * np.sin(np.pi * t / 0.42) ** 2 * 0.20
    if kind in {"footstep", "step_stone", "creeper_step"}:
        stone = kind == "step_stone"
        return transient(rng, 0.17, rng.uniform(65, 105), 0.39 if stone else 0.42, 1040 if stone else 1740, 24)
    if kind == "wood_hit":
        return transient(rng, 0.15, rng.uniform(145, 208), 0.32, 2600, 28)
    if kind in {"wood_break", "soil_break", "stone_break", "ore_break"}:
        hz = {"wood_break": 170, "soil_break": 85, "stone_break": 235, "ore_break": 261}[kind]
        return scatter(rng, (0, 0.023, 0.062, 0.127, 0.196), 0.69, 0.16, hz, 0.48, 3700, 33)
    if kind in {"stone_hit", "pick_tap"}:
        clip = transient(rng, 0.16, rng.uniform(510, 750), 0.47, 4250, 32)
        t = clock(0.16)
        return clip + 0.11 * sine(t, 1470) * np.exp(-33 * t) * envelope(t, 0.001, 0.05)
    if kind in {"dig", "table_place", "seal"}:
        hz = {"dig": 95, "table_place": 139, "seal": 77}[kind]
        return scatter(rng, (0, 0.038, 0.084), 0.46, 0.19, hz, 0.43, 2100, 23)
    if kind in {"craft", "craft_take", "pickup"}:
        return chime()
    if kind in {"craft_open", "craft_place", "craft_close", "tool_equip"}:
        return transient(rng, 0.13, rng.uniform(360, 540), 0.30, 3700, 34)
    if kind == "spider":
        return scatter(rng, (0, 0.037, 0.10, 0.21, 0.24), 0.83, 0.11, 790, 0.49, 6400, 41)
    if kind == "skeleton":
        return scatter(rng, (0, 0.068, 0.118, 0.25, 0.31), 0.86, 0.19, 441, 0.39, 4300, 28)
    if kind == "zombie":
        t = clock(1.08)
        ph = TAU * (87 * t - 15 * t * t + 0.067 * sine(t, 7.1))
        call = np.sin(ph) + 0.35 * np.sin(2.16 * ph) + 0.18 * np.sin(4.47 * ph)
        return (call * 0.32 + noise(t, rng, 1020) * 0.17) * envelope(t, 0.16, 0.40) * (0.8 + 0.2 * sine(t, 5.2))
    if kind == "torch_ignite":
        t = clock(0.48)
        flame = 0.51 * noise(t, rng, 2300) + 0.26 * noise(t, rng, 490)
        return flame * np.exp(-9 * t) * envelope(t, 0.004, 0.11)
    if kind == "breath_relief":
        t = clock(1.22)
        curve = np.sin(np.pi * t / 1.22) ** 1.7
        return (0.27 * noise(t, rng, 510) + 0.105 * noise(t, rng, 2300)) * curve
    if kind == "creeper_hiss":
        t = clock(duration or 2)
        rise = 0.23 + 0.77 * (t / t[-1]) ** 1.7
        spray = 0.45 * noise(t, rng, 11_000) + 0.42 * noise(t, rng, 4000)
        return spray * rise * (0.93 + 0.07 * sine(t, 8.2)) * envelope(t, 0.064, 0.008)
    if kind == "blast":
        t = clock(0.83)
        phase = TAU * (33 * t + 13.5 * (1 - np.exp(-7.4 * t)))
        bass = 1.24 * np.sin(phase) * np.exp(-5.1 * t)
        body = 0.82 * noise(t, rng, 410) * np.exp(-7.3 * t)
        crack = 0.93 * noise(t, rng, 8200) * np.exp(-32 * t)
        return (bass + body + crack) * envelope(t, 0.0018, 0.07)
    if kind == "debris":
        return scatter(rng, (0, 0.078, 0.187, 0.29), 0.82, 0.22, 109, 0.53, 4700, 17)
    raise ValueError(f"unknown sound cue {kind!r}")


def main():
    cues = json.loads((HERE / "audio-cues.json").read_text(encoding="utf-8"))
    mix = np.zeros((DURATION * SR, 2))
    rng = np.random.default_rng(SEED)
    beds(mix, rng)
    pans = {"spider": -0.68, "zombie": 0.40, "skeleton": -0.32, "pick_tap": -0.40,
            "ore_break": -0.38, "torch_ignite": -0.40, "creeper_step": 0.42, "creeper_hiss": 0.38, "debris": 0.30}
    for cue in sorted(cues, key=lambda item: item["t"]):
        t, kind, gain = cue["t"], cue["kind"], cue["vol"]
        if not 0 <= t < DURATION or not 0 <= gain <= 1:
            raise ValueError(f"invalid cue time or volume: {cue}")
        pan = pans.get(kind, rng.uniform(-0.15, 0.15))
        clip = effect(kind, rng, cue.get("dur"))
        add(mix, clip, t, gain, pan)
        if 37 <= t < 56 and kind in {"step_stone", "seal", "pick_tap", "ore_break"}:
            add(mix, clip, t + 0.061, gain * 0.17, -pan)
            add(mix, clip, t + 0.109, gain * 0.07, pan)
    # Mute every stem for the held beat before the hiss, then end the blast cleanly.
    fade = round(0.065 * SR)
    silence = round(56.25 * SR)
    mix[silence - fade:silence] *= np.linspace(1, 0, fade)[:, None]
    mix[silence:round(57.25 * SR)] = 0
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mix = 0.86 * np.tanh(mix * 1.45)
    output = HERE / "generated" / "mix.wav"
    output.parent.mkdir(exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SR)
        wav.writeframes((mix * 32767).astype("<i2").tobytes())
    print(f"Wrote {DURATION}s stereo score and {len(cues)} cues to {output}")


if __name__ == "__main__":
    main()
