#!/usr/bin/env python3
"""Synthesize the score and Foley for Aurora Express using NumPy and BlockReel."""

import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
from score import SR, add, compose, drum, tone  # noqa: E402


def timebase(seconds):
    return np.arange(round(seconds * SR)) / SR


def write_audio(path, samples):
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1 if pcm.ndim == 1 else pcm.shape[1])
        output.setsampwidth(2)
        output.setframerate(SR)
        output.writeframes(pcm.tobytes())


def wind(rng):
    t = timebase(30)
    control = rng.normal(0, 0.14, 3002)
    low = np.interp(t, np.arange(len(control)) / 100, control)
    gust = 0.53 + 0.25 * np.sin(2 * np.pi * 0.18 * t) + 0.12 * np.sin(2 * np.pi * 0.31 * t)
    envelope = np.minimum(1, t * 4) * np.clip((30 - t) / 1.2, 0, 1)
    return low * gust * envelope


def rail():
    t = timebase(0.9)
    ringing = sum(np.sin(2 * np.pi * f * t) / (k + 1) for k, f in enumerate((227, 641, 983, 1884)))
    return ringing * np.minimum(1, 1500 * t) * np.exp(-6 * t) * 0.38


def footstep(rng):
    t = timebase(0.16)
    grit = np.convolve(rng.normal(0, 0.3, len(t)), np.ones(8) / 8, mode="same")
    thud = 0.24 * np.sin(2 * np.pi * 102 * t) * np.exp(-35 * t)
    return (grit * np.exp(-16 * t) + thud) * np.minimum(1, 350 * t)


def impact(rng):
    t = timebase(2.85)
    crackle = np.convolve(rng.normal(0, 0.4, len(t)), np.ones(16) / 16, mode="same")
    bass = np.sin(2 * np.pi * (36 * t + 15 * (1 - np.exp(-8 * t))))
    blast = (0.53 * bass + 2.0 * crackle) * np.minimum(1, 100 * t) * np.exp(-1.8 * t)
    for at in (0.23, 0.38, 0.47, 0.76, 1.02, 1.39):
        add(blast, footstep(rng), at, 1.25 - at / 2)
    return blast


def signal():
    samples = np.zeros(round(4.8 * SR))
    for index, frequency in enumerate((392, 493.88, 587.33, 783.99)):
        chime = tone(frequency, 2.6, harm=8, bright=0.64, attack=0.02, release=0.8, decay=0.66)
        add(samples, chime, 0.13 * index, 0.31 - 0.035 * index)
        add(samples, chime, 0.61 + 0.19 * index, 0.09)
    return samples


def main():
    output = HERE / "generated"
    output.mkdir(exist_ok=True)
    rng = np.random.default_rng(73)
    score = compose(30, [("calm", 0, 5.4), ("build", 5.4, 9.72), ("battle", 9.72, 16.85),
                         ("silence", 16.85, 22.48), ("dawn", 22.48, 30)], 108, "E")
    steps = np.zeros(round(4.25 * SR))
    for at in (0.02, 0.36, 0.68, 1.01, 1.35, 1.70, 2.01, 2.34, 2.68, 3.02, 3.36, 3.71, 4.04):
        add(steps, footstep(rng), at, rng.uniform(0.75, 1.0))
    landing = drum(0.45, f0=105, f1=44, noise=0.08, decay=0.09) * 0.46
    add(landing, footstep(rng), 0.025)
    for name, samples in {"score": score, "wind": wind(rng), "rail": rail(), "steps": steps,
                          "impact": impact(rng), "landing": landing, "signal": signal()}.items():
        write_audio(output / f"{name}.wav", samples)
    print(f"Wrote original score and effects to {output}")


if __name__ == "__main__":
    main()
