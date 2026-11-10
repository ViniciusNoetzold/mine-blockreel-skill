#!/usr/bin/env python3
"""Audio mixing for BlockReel: timed music / sfx / dialogue tracks (files YOU supply) -> one ffmpeg filter graph.

story.json:
  "audio": {
    "music":    { "file": "assets/theme.mp3", "volume": 0.6, "start": 0, "fadeIn": 0.8, "fadeOut": 1.5, "loop": true,
                  "duck": { "amount": 0.35 } },             // music drops to 35% while any dialogue plays
    "sfx":      [ { "file": "assets/boom.wav", "t": 3.0, "volume": 1.0 } ],
    "dialogue": [ { "file": "assets/line1.wav", "t": 5.2, "volume": 1.0 } ]
  }
Legacy form still works:  "music": "assets/theme.mp3".

  python tools/audio.py story.json --out mix.wav        # render only the audio (to check the mix)
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _path(base, f):
    return str(f if os.path.isabs(f) else (Path(base) / f))


def normalize(story):
    a = dict(story.get("audio") or {})
    if story.get("music") and not a.get("music"):
        a["music"] = {"file": story["music"], "fadeIn": 0.5, "fadeOut": 1.0}
    elif isinstance(a.get("music"), str):
        a["music"] = {"file": a["music"]}
    return a


def build(story, base_dir, start=0.0, end=None):
    """Return (ffmpeg input args, filter_complex, output label) or None if the story has no audio."""
    a = normalize(story)
    dur = (end if end is not None else story.get("duration", 10)) - start
    inputs, chains, sfx_labels, dlg_labels = [], [], [], []

    def add(fileinfo, loop=False):
        i = len(inputs) // 2 + (len(inputs) % 2)
        args = (["-stream_loop", "-1"] if loop else []) + ["-i", _path(base_dir, fileinfo["file"])]
        inputs.extend(args)
        return sum(1 for x in inputs if x == "-i") - 1

    def timed(items, kind, labels):
        for n, it in enumerate(items or []):
            t0 = it["t"] - start
            if t0 < -1e-6 or t0 >= dur:
                continue  # starts outside the rendered range
            idx = add(it)
            ms = int(round(max(0, t0) * 1000))
            chains.append(f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume={it.get('volume', 1.0)},adelay={ms}|{ms}[{kind}{n}]")
            labels.append(f"[{kind}{n}]")

    timed(a.get("sfx"), "sfx", sfx_labels)
    timed(a.get("dialogue"), "dlg", dlg_labels)

    mus = a.get("music")
    mus_label = None
    if mus:
        idx = add(mus, loop=mus.get("loop", False))
        ss = max(0.0, start - mus.get("start", 0.0)) if start else 0.0
        delay = int(round(max(0.0, mus.get("start", 0.0) - start) * 1000))
        fin, fout = mus.get("fadeIn", 0.5), mus.get("fadeOut", 1.0)
        f = f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo"
        if ss:
            f += f",atrim=start={ss},asetpts=PTS-STARTPTS"
        f += f",volume={mus.get('volume', 0.7)},afade=t=in:st=0:d={fin},afade=t=out:st={max(0.0, dur - fout)}:d={fout}"
        if delay:
            f += f",adelay={delay}|{delay}"
        chains.append(f + "[mus]")
        mus_label = "[mus]"

    if not (sfx_labels or dlg_labels or mus_label):
        return None

    mix_in = []
    if dlg_labels:
        chains.append(("".join(dlg_labels) + f"amix=inputs={len(dlg_labels)}:normalize=0[dlgbus]") if len(dlg_labels) > 1 else f"{dlg_labels[0]}anull[dlgbus]")
        duck = (mus or {}).get("duck")
        if mus_label and duck:
            amt = float(duck.get("amount", 0.35))
            ratio = max(2.0, min(20.0, 1.0 / max(amt, 0.05)))  # lower amount -> stronger compression
            chains.append("[dlgbus]asplit=2[dlgkeyraw][dlgout]")
            chains.append(f"[dlgkeyraw]apad=whole_dur={dur:.6f}[dlgkey]")
            chains.append(f"{mus_label}[dlgkey]sidechaincompress=threshold=0.01:ratio={ratio:.1f}:attack=40:release=450:makeup=1[musd]")
            mix_in += ["[musd]", "[dlgout]"]
        else:
            mix_in += ([mus_label] if mus_label else []) + ["[dlgbus]"]
    elif mus_label:
        mix_in.append(mus_label)
    mix_in += sfx_labels
    mix = "".join(mix_in) + f"amix=inputs={len(mix_in)}:normalize=0," if len(mix_in) > 1 else mix_in[0]
    chains.append(f"{mix}apad,alimiter=limit=0.95,atrim=0:{dur:.6f}[aout]")
    return inputs, ";".join(chains), "[aout]"


def render_audio(story, base_dir, out, start=0.0, end=None, *, sample_rate=44100):
    g = build(story, base_dir, start, end)
    if g is None:
        return False
    inputs, fc, label = g
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", label, "-ar", str(sample_rate), "-ac", "2", str(out)], check=True)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--out", default="out/mix.wav")
    ap.add_argument("--start", type=float, default=0.0); ap.add_argument("--end", type=float)
    a = ap.parse_args(argv)
    p = Path(a.story).resolve()
    story = json.loads(p.read_text(encoding="utf-8"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    if not render_audio(story, p.parent, a.out, a.start, a.end):
        print("no audio in this storyboard")
        return 1
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
