#!/usr/bin/env python3
"""Deliverables from a finished BlockReel film: subtitles, a GIF, a vertical cut for Shorts/Reels/TikTok, a thumbnail.

  python tools/export.py srt       story.json --out film.srt                    # subtitles in SubRip (chat lines as "Name: text")
  python tools/export.py gif       film.mp4 --start 7.4 --dur 6 --out clip.gif  # palette-optimised GIF (width 560, 10 fps by default)
  python tools/export.py vertical  story.json --out vertical.mp4 [--preset preview] [--workers 4]   # re-rendered at 1080x1920
  python tools/export.py thumbnail story.json --t 8.6 --out thumb.jpg [--title "EU vs HEROBRINE"]   # a 1280x720 still

`vertical` RE-RENDERS the film at 9:16 (cameras follow the actors, so the framing holds) instead of cropping a 16:9 picture.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ts(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt(story):
    lines = []
    subs = sorted(story.get("subtitles", []), key=lambda x: x["t"])
    for i, s in enumerate(subs, 1):
        text = f"{s['who']}: {s['text']}" if s.get("who") else s["text"]
        lines += [str(i), f"{ts(s['t'])} --> {ts(s['t'] + s.get('dur', 2))}", text, ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("srt"); p.add_argument("story"); p.add_argument("--out", required=True)
    p = sub.add_parser("gif"); p.add_argument("video"); p.add_argument("--out", required=True); p.add_argument("--start", type=float, default=0)
    p.add_argument("--dur", type=float, default=6); p.add_argument("--width", type=int, default=560); p.add_argument("--fps", type=float, default=10)
    p = sub.add_parser("vertical"); p.add_argument("story"); p.add_argument("--out", required=True); p.add_argument("--size", default="1080x1920")
    p.add_argument("--preset"); p.add_argument("--workers", type=int, default=1)
    p = sub.add_parser("thumbnail"); p.add_argument("story"); p.add_argument("--out", required=True); p.add_argument("--t", type=float, required=True)
    p.add_argument("--title"); p.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args(argv)

    if a.cmd == "srt":
        Path(a.out).write_text(srt(json.loads(Path(a.story).read_text(encoding="utf-8"))), encoding="utf-8"); print("wrote", a.out); return 0
    if a.cmd == "gif":
        vf = f"fps={a.fps},scale={a.width}:-1:flags=lanczos,split[x][y];[x]palettegen=max_colors=96:stats_mode=diff[p];[y][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(a.start), "-t", str(a.dur), "-i", a.video, "-vf", vf, a.out], check=True)
        print("wrote", a.out, f"({Path(a.out).stat().st_size // 1024} KB)"); return 0
    if a.cmd == "vertical":
        cmd = [sys.executable, str(HERE / "render.py"), a.story, "--size", a.size, "--out", a.out, "--workers", str(a.workers)] + (["--preset", a.preset] if a.preset else [])
        return subprocess.run(cmd).returncode
    if a.cmd == "thumbnail":
        story = json.loads(Path(a.story).read_text(encoding="utf-8"))
        if a.title:  # a title card for the still, drawn by the engine in the game font
            story = {**story, "titles": [{"t": a.t - 0.5, "dur": 1.0, "text": a.title, "size": 72}], "subtitles": []}
            tmp = Path(a.story).parent / f".{Path(a.story).stem}.thumb.json"; tmp.write_text(json.dumps(story)); src = tmp
        else:
            src = Path(a.story); tmp = None
        png = Path(a.out).with_suffix(".png")
        rc = subprocess.run([sys.executable, str(HERE / "render.py"), str(src), "--frame", str(a.t), "--scale", str(a.scale), "--out", str(png)]).returncode
        if tmp:
            tmp.unlink(missing_ok=True)
        if rc == 0 and Path(a.out).suffix.lower() in (".jpg", ".jpeg"):
            from PIL import Image
            Image.open(png).convert("RGB").save(a.out, quality=90); png.unlink()
        print("wrote", a.out); return rc
    return 1


if __name__ == "__main__":
    sys.exit(main())
