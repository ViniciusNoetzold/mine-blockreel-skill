#!/usr/bin/env python3
"""Render a BlockReel storyboard to MP4, frame by frame (deterministic, no video model).

  python tools/render.py examples/hello-world/story.json --out out/hello.mp4
  python tools/render.py story.json --preset preview --out preview.mp4         # 12 fps, half resolution (much faster)
  python tools/render.py story.json --preset 1080p60 --workers 4 --out hd.mp4  # 1920x1080 @ 60 fps, 4 Chrome workers
  python tools/render.py story.json --frame 3.5 --out frame.png                # one still
  python tools/render.py story.json --gpu                                      # use the real GPU instead of software GL

--scale S renders at S x the story size (the WebGL canvas itself is S x larger, so 0.5 is ~4x faster and 1.5 is sharp 1080p).
--workers N renders N chunks of frames in parallel Chrome processes, then joins them. Audio (story.audio / story.music) is
mixed by tools/audio.py and muxed at the end.

Needs: Node deps (`npm install`), Python deps (`pip install -r requirements.txt`), ffmpeg, and a Chromium/Chrome.
Set CHROME_PATH if Chrome is not found automatically.
"""
import argparse
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager, suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

PRESETS = {"preview": {"fps": 12, "scale": 0.5}, "1080p60": {"fps": 60, "size": 1920}, "720p30": {"fps": 30, "scale": 1.0}}


def speech_envelopes(story, base):
    """Loudness of each dialogue recording that names an actor, 30 values per second, for audio-driven lip-sync."""
    import numpy as np
    out = []
    for d in (story.get("audio") or {}).get("dialogue", []) or []:
        who = d.get("actor") or d.get("who")
        if not who:
            continue
        f = Path(d["file"]) if Path(d["file"]).is_absolute() else Path(base) / d["file"]
        if not f.exists():
            continue
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(f), "-ac", "1", "-ar", "12000", "-f", "s16le", "-"], capture_output=True).stdout
        a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0; step = 400  # 12000 / 30
        if not len(a):
            continue
        rms = np.sqrt(np.convolve(a * a, np.ones(step) / step, mode="same"))[::step]
        env = rms / max(1e-6, np.percentile(rms, 95))
        out.append({"actor": who, "t": d["t"], "dt": 1 / 30, "env": [round(float(min(1.5, v)), 3) for v in env]})
    return out


def prepare_story(story_path, story, size=None):
    """A render copy of the story when something must be added for the page (size override, speech envelopes). Returns its path."""
    extra = {}
    if size:
        extra["size"] = list(size)
    env = speech_envelopes(story, story_path.parent)
    if env:
        extra["lipsyncAudio"] = env
    if not extra:
        return story_path, story
    s2 = {**story, **extra}; p2 = story_path.parent / f".{story_path.stem}.render.json"
    p2.write_text(json.dumps(s2)); return p2, s2


def find_chrome():
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        p = shutil.which(n)
        if p:
            return p
    return None  # let Playwright use its own downloaded browser


class Handler(http.server.SimpleHTTPRequestHandler):
    project_dir = ROOT

    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith("/project/"):
            return str(self.project_dir / path[len("/project/"):])
        return str(ROOT / path.lstrip("/"))

    def log_message(self, *a):
        pass


def serve(project_dir):
    Handler.project_dir = Path(project_dir)
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def launch_args(gpu):
    base = ["--hide-scrollbars", "--ignore-gpu-blocklist"]
    if gpu:  # let Chrome use the real GPU (ANGLE picks D3D11 / Metal / GL)
        return base + ["--enable-gpu-rasterization", "--use-angle=default"]
    return base + ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]


def open_page(pw, port, story_path, story, scale, gpu, allow_missing=False):
    kw = {"args": launch_args(gpu)}
    if find_chrome():
        kw["executable_path"] = find_chrome()
    browser = pw.chromium.launch(**kw)
    W, H = story.get("size", [1280, 720])
    page = browser.new_page(viewport={"width": int(W * scale) // 2 * 2, "height": int(H * scale) // 2 * 2})
    page.on("console", lambda m: print("[page]", m.text) if m.type in ("error", "warning") and "willReadFrequently" not in m.text and "status of 404" not in m.text else None)
    page.goto(f"http://127.0.0.1:{port}/core/engine/index.html?project=/project/{story_path.name}&res={scale}")
    page.wait_for_function("window.__ready === true || window.__error", timeout=120000)
    err = page.evaluate("window.__error || null")
    if err:
        raise RuntimeError("engine error: " + err)
    missing = page.evaluate("window.__missing || []")
    if missing and not allow_missing:
        browser.close()
        raise RuntimeError("missing block textures: " + ", ".join(sorted(set(missing))) + "  (fix the names or pass --allow-missing)")
    if scale != 1.0:
        page.add_style_tag(content=f"#stage{{transform:scale({scale});transform-origin:0 0}}")
    return browser, page


@contextmanager
def render_page(story_path, story, scale, gpu, allow_missing=False):
    from playwright.sync_api import sync_playwright
    server, port = serve(story_path.parent)
    try:
        with sync_playwright() as pw:
            browser, page = open_page(pw, port, story_path, story, scale, gpu, allow_missing)
            try:
                yield page
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


def capture_frame(page, t):
    from playwright.sync_api import Error

    try:
        page.evaluate("window.renderAt", t)
        png = page.screenshot(type="png")
        # A context loss can arrive after the draw while the screenshot is captured.
        page.evaluate("window.__assertRenderHealthy()")
        return png
    except Error as exc:
        raise RuntimeError(f"render failed at {t:.3f}s: {exc}") from exc


def render_range(story_path, story, fps, scale, n0, n1, out, crf, gpu, quiet=False, allow_missing=False, mblur=1):
    """Render frames [n0, n1) to a silent mp4."""
    out = Path(out)
    with render_page(story_path, story, scale, gpu, allow_missing) as page, tempfile.TemporaryDirectory(dir=out.parent) as staging:
        staged = Path(staging) / out.name
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                               "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
                               "-movflags", "+faststart", str(staged)], stdin=subprocess.PIPE)
        try:
            for i in range(n0, n1):
                if mblur > 1:  # average sub-frames across half a frame (a 180-degree shutter): deterministic motion blur
                    import io
                    import numpy as np
                    from PIL import Image
                    acc = None
                    for k in range(mblur):
                        t = (i + ((k + 0.5) / mblur - 0.5) * 0.5) / fps
                        png = capture_frame(page, t)
                        im = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), dtype=np.float32)
                        acc = im if acc is None else acc + im
                    buf = io.BytesIO(); Image.fromarray((acc / mblur).round().astype(np.uint8)).save(buf, format="PNG"); ff.stdin.write(buf.getvalue())
                else:
                    ff.stdin.write(capture_frame(page, i / fps))
                if not quiet and (i - n0) % max(1, int(fps)) == 0:
                    print(f"\r{i - n0}/{n1 - n0} frames", end="", flush=True)
            ff.stdin.close()
        except BaseException:
            if ff.poll() is None:
                ff.terminate()
            with suppress(BrokenPipeError):
                ff.stdin.close()
            ff.wait()
            raise
        returncode = ff.wait()
        if returncode:
            raise subprocess.CalledProcessError(returncode, ff.args)
        staged.replace(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--out", default="out/film.mp4")
    ap.add_argument("--fps", type=float); ap.add_argument("--scale", type=float)
    ap.add_argument("--preset", choices=sorted(PRESETS))
    ap.add_argument("--frame", type=float, help="render a single PNG at this time (seconds)")
    ap.add_argument("--start", type=float, default=0); ap.add_argument("--end", type=float)
    ap.add_argument("--frames", help="internal: frame range a:b (used by --workers)")
    ap.add_argument("--workers", type=int, default=1, help="parallel Chrome workers (each renders a chunk of frames)")
    ap.add_argument("--gpu", action="store_true", help="use the real GPU instead of software GL (SwiftShader)")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--allow-missing", action="store_true", help="render even if a block texture is missing (it shows as magenta/black)")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--motion-blur", type=int, default=1, metavar="N", help="average N sub-frames per frame (N x slower; 3-5 looks good)")
    ap.add_argument("--size", help="override the story size, e.g. 1080x1920 for a vertical (9:16) version")
    a = ap.parse_args(argv)

    story_path = Path(a.story).resolve()
    story = json.loads(story_path.read_text(encoding="utf-8"))
    audio_story_path = story_path
    if not a.frames:  # workers receive the prepared copy directly
        story_path, story = prepare_story(story_path, story, tuple(int(v) for v in a.size.lower().split("x")) if a.size else None)
    W0, H0 = story.get("size", [1280, 720])
    pre = PRESETS.get(a.preset, {})
    fps = a.fps or pre.get("fps") or story.get("fps", 30)
    scale = a.scale or (pre["size"] / W0 if "size" in pre else pre.get("scale", 1.0))
    dur = story.get("duration", 10)
    end = min(a.end or dur, dur)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)

    if a.frame is not None:
        try:
            with render_page(story_path, story, scale, a.gpu, a.allow_missing) as page:
                Path(a.out).write_bytes(capture_frame(page, a.frame))
        except RuntimeError as e:
            print(e, file=sys.stderr); return 2
        finally:
            if story_path != audio_story_path and story_path.name.startswith("."):
                story_path.unlink(missing_ok=True)
        print("wrote", a.out)
        return 0

    n0, n1 = int(round(a.start * fps)), int(round(end * fps))
    if a.frames:
        n0, n1 = map(int, a.frames.split(":"))
        try:
            render_range(story_path, story, fps, scale, n0, n1, a.out, a.crf, a.gpu, quiet=True, allow_missing=a.allow_missing, mblur=a.motion_blur)
        except RuntimeError as e:
            print(e, file=sys.stderr); return 2
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="blockreel_"))
    silent = tmp / "silent.mp4"
    try:
        if a.workers <= 1:
            render_range(story_path, story, fps, scale, n0, n1, silent, a.crf, a.gpu, allow_missing=a.allow_missing, mblur=a.motion_blur)
        else:
            n = max(1, min(a.workers, n1 - n0)); size = -(-(n1 - n0) // n)
            procs, parts = [], []
            for k in range(n):
                s, e = n0 + k * size, min(n1, n0 + (k + 1) * size)
                if s >= e:
                    break
                part = tmp / f"part{k:02d}.mp4"; parts.append(part)
                cmd = [sys.executable, str(Path(__file__)), str(story_path), "--frames", f"{s}:{e}", "--fps", str(fps), "--scale", str(scale),
                       "--crf", str(a.crf), "--out", str(part), "--motion-blur", str(a.motion_blur)] + (["--gpu"] if a.gpu else []) + (["--allow-missing"] if a.allow_missing else [])
                procs.append(subprocess.Popen(cmd))
            print(f"rendering {n1 - n0} frames in {len(procs)} workers...")
            codes = [p.wait() for p in procs]
            if any(codes):
                print("a worker failed", codes, file=sys.stderr); return 2
            lst = tmp / "parts.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                            "-movflags", "+faststart", str(silent)], check=True)
        # audio
        mixed = False
        if not a.no_audio:
            import audio
            wav = tmp / "mix.wav"
            if audio.render_audio(story, story_path.parent, wav, a.start, end):
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                                "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(a.out)], check=True)
                mixed = True
        if not mixed:
            shutil.copyfile(silent, a.out)
    except RuntimeError as e:
        print(e, file=sys.stderr); return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if story_path != audio_story_path and story_path.name.startswith("."):
            story_path.unlink(missing_ok=True)
    W, H = int(W0 * scale) // 2 * 2, int(H0 * scale) // 2 * 2
    print(f"\nwrote {a.out}  ({W}x{H} @ {fps}fps, {n1 - n0} frames{', with audio' if mixed else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
