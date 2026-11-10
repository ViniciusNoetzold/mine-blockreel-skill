#!/usr/bin/env python3
"""Quality review helper (step E of the BlockReel flow).

  python tools/qa.py films/my-film/story.json --out films/my-film/qa [--tone dialogue|action|calm] [--min-frames 8]

It (1) picks at least N frames spread over the film: the opening, every shot change, every close-up, the ending;
(2) renders them and builds a contact sheet; (3) runs automatic checks through the engine (camera inside a block,
actor out of frame, face turned away from the camera, subtitle clipped, shots longer than the tone allows,
subtitle/title overlap, reading speed); (4) writes qa/auto.json and, if missing, a qa.md next to the story.

The automatic checks cannot see skin holes, odd shadows, awkward poses or a confusing story. After running it you
MUST open every frame image and look at it, then record what you saw in qa.md.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import find_chrome, serve  # noqa: E402

LIMITS = {"calm": 6.0, "dialogue": 4.5, "action": 2.5}  # longest allowed shot (s) when the camera is static; +1.5 s if it moves


def shot_moves(s):
    return bool(s.get("orbit") or s.get("to") or s.get("lookTo") or s.get("fovTo") or s.get("handheld") or s.get("first"))


def pick_times(story, n_min):
    dur = story.get("duration", 10)
    shots = sorted(story.get("camera", []), key=lambda s: s["t"])
    ts = [min(0.3, dur / 20)]
    for i, s in enumerate(shots):
        end = shots[i + 1]["t"] if i + 1 < len(shots) else dur
        ts.append(min(end - 0.05, s["t"] + 0.25))                  # just after the cut
        if end - s["t"] > 2.0:
            ts.append(s["t"] + (end - s["t"]) * 0.6)               # inside the shot
        if (s.get("fov") or 60) <= 45:
            ts.append(min(end - 0.05, s["t"] + (end - s["t"]) * 0.4))  # close-ups get an extra look
    ts.append(dur - 0.25)
    ts = sorted(t for t in ts if 0 <= t < dur)
    out = []
    for t in ts:
        if not out or t - out[-1] >= 0.4:
            out.append(round(t, 2))
    k = 1
    while len(out) < n_min:                                         # pad with evenly spread frames
        extra = round(dur * k / (n_min + 1), 2)
        if all(abs(extra - t) >= 0.4 for t in out):
            out.append(extra)
        k += 1
        if k > 4 * n_min:
            break
    # Keep panel states even when they are closer together than the normal still spacing.
    for event in (story.get("hud") or {}).get("events", []):
        if event.get("type") not in ("inventory", "craft"):
            continue
        start = event["t"]
        end = min(start + event["dur"], dur)
        take = event.get("takeAt", start)
        if start < take < end:
            out.extend(((start + take) / 2, (take + end) / 2))
        elif start < end:
            out.append((start + end) / 2)
    return sorted(set(out))


def shot_tone(shot, default):
    return shot.get("tone", default) if shot.get("tone", default) in LIMITS else default


def static_checks(story, tone):
    issues = []
    dur = story.get("duration", 10)
    shots = sorted(story.get("camera", []), key=lambda s: s["t"])
    if not shots:
        issues.append(("WARN", None, "no camera shots defined (the default camera is used)"))
    for i, s in enumerate(shots):
        end = shots[i + 1]["t"] if i + 1 < len(shots) else dur
        L = end - s["t"]
        lim = LIMITS[shot_tone(s, tone)] + (1.5 if shot_moves(s) else 0)
        if L > lim:
            issues.append(("WARN", s["t"], f"shot at {s['t']}s lasts {L:.1f}s (limit {lim:.1f}s for tone '{shot_tone(s, tone)}'): cut or add movement"))
    if shots:
        avg = sum((shots[i + 1]["t"] if i + 1 < len(shots) else dur) - s["t"] for i, s in enumerate(shots)) / len(shots)
        issues.append(("INFO", None, f"{len(shots)} shots, average {avg:.1f}s per shot, duration {dur}s"))
    for sub in story.get("subtitles", []):
        words, chars, d = len(sub["text"].split()), len(sub["text"]), sub.get("dur", 2)
        if words > 10:
            issues.append(("WARN", sub["t"], f"subtitle at {sub['t']}s has {words} words (max ~10)"))
        if d < chars / 17:
            issues.append(("WARN", sub["t"], f"subtitle at {sub['t']}s is on screen {d:.1f}s but needs ~{chars / 17:.1f}s to read"))
        for ti in story.get("titles", []):
            if sub["t"] < ti["t"] + ti.get("dur", 2) and ti["t"] < sub["t"] + d:
                issues.append(("WARN", sub["t"], f"subtitle at {sub['t']}s overlaps the title '{ti['text']}'"))
    return issues


def active_actors(story, t):
    names = set()
    for s in story.get("timeline", []):
        if s.get("do", "idle") == "idle":
            continue  # standing still is not "acting"; the shot subject check covers who must be visible
        if s["t"] - 0.3 <= t <= s["t"] + s.get("dur", 0) + 0.3 or (s.get("hold") and s["t"] <= t):
            names.add(s["actor"])
    return names


def first_person_actor(story, t):
    cur = None
    for s in sorted(story.get("camera", []), key=lambda s: s["t"]):
        if s["t"] <= t:
            cur = s
    f = (cur or {}).get("first")
    return (f.get("actor") if isinstance(f, dict) else f) if f else None


def shot_subject(story, t):
    shots = sorted(story.get("camera", []), key=lambda s: s["t"])
    cur = None
    for s in shots:
        if s["t"] <= t:
            cur = s
    if not cur:
        return None
    tgt = cur.get("look") or (cur.get("orbit") or {}).get("center") or cur.get("first")
    if isinstance(tgt, dict):
        tgt = tgt.get("actor")
    return tgt if isinstance(tgt, str) and tgt in story.get("actors", {}) else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--out", default=None)
    ap.add_argument("--tone", default="dialogue", choices=sorted(LIMITS), help="default pacing tone; a camera shot can override it with \"tone\"")
    ap.add_argument("--min-frames", type=int, default=8)
    ap.add_argument("--scale", type=float, default=0.75)
    ap.add_argument("--no-md", action="store_true", help="do not create qa.md")
    a = ap.parse_args(argv)

    story_path = Path(a.story).resolve()
    story = json.loads(story_path.read_text(encoding="utf-8"))
    out = Path(a.out) if a.out else story_path.parent / "qa"
    (out / "frames").mkdir(parents=True, exist_ok=True)
    times = pick_times(story, a.min_frames)
    issues = static_checks(story, a.tone)

    from playwright.sync_api import sync_playwright
    srv, port = serve(story_path.parent)
    W, H = story.get("size", [1280, 720])
    frames = []
    with sync_playwright() as pw:
        kw = {"args": ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--hide-scrollbars"]}
        if find_chrome():
            kw["executable_path"] = find_chrome()
        browser = pw.chromium.launch(**kw)
        page = browser.new_page(viewport={"width": int(W * a.scale), "height": int(H * a.scale)})
        page.goto(f"http://127.0.0.1:{port}/core/engine/index.html?project=/project/{story_path.name}")
        page.wait_for_function("window.__ready === true || window.__error", timeout=60000)
        err = page.evaluate("window.__error || null")
        if err:
            print("engine error:", err, file=sys.stderr)
            return 2
        missing = page.evaluate("window.__missing || []")
        if missing:
            issues.append(("FAIL", None, "missing block textures (they render as magenta/black): " + ", ".join(sorted(set(missing)))))
        # dense path check: every 0.05 s, actors' bodies and the camera against the world at that moment
        pc = page.evaluate("window.__pathCheck(0.05)")
        for h in pc["actors"]:
            issues.append(("FAIL", h["t0"], f"{h['actor']} is inside {h['block']} at {h['pos']} from {h['t0']:.2f} s to {h['t1']:.2f} s "
                                            "(spawns in or walks through a block/tree/wall: move it or route the walk around it)"))
        for h in pc["camera"]:
            issues.append(("FAIL", h["t0"], f"camera passes through {h['block']} at {h['pos']} from {h['t0']:.2f} s to {h['t1']:.2f} s"))
        page.add_style_tag(content=f"#stage{{transform:scale({a.scale});transform-origin:0 0}}")
        for t in times:
            q = page.evaluate(f"window.__qa({t})")
            f = out / "frames" / f"{len(frames) + 1:02d}_t{t:06.2f}.png"
            page.screenshot(path=str(f))
            frames.append((t, f, q))
            subj = shot_subject(story, t)
            fp = first_person_actor(story, t)  # the camera IS this actor: never "out of frame"
            act = (active_actors(story, t) | ({subj} if subj else set())) - ({fp} if fp else set())
            if q["cameraInBlock"]:
                issues.append(("FAIL", t, f"t={t}: camera is inside a block {q['camera']}"))
            for name, info in q["actors"].items():
                if not info.get("visible", True):
                    continue  # hidden actors (hide: true) are not checked
                if info["insideBlock"]:
                    issues.append(("FAIL", t, f"t={t}: {name} is standing inside a block"))
                if name == fp:
                    continue
                if name in act and info["visiblePoints"] == 0:
                    issues.append(("WARN", t, f"t={t}: {name} is acting but out of frame"))
                elif name == subj and info["visiblePoints"] < 3:
                    issues.append(("WARN", t, f"t={t}: {name} is the subject of the shot but is cropped (only {info['visiblePoints']}/3 body points in frame)"))
                if name == subj and info["facingCamera"] < -0.35 and info["distance"] < 8:
                    issues.append(("WARN", t, f"t={t}: {name} faces away from the camera (dot={info['facingCamera']:.2f}); show the face or cut"))
                if info["distance"] < 0.9:
                    issues.append(("WARN", t, f"t={t}: camera is only {info['distance']:.1f} blocks from {name} (near-plane clipping risk)"))
            if q["subtitle"] and q["subtitle"]["clipped"]:
                issues.append(("WARN", t, f"t={t}: subtitle is clipped by the frame"))
        browser.close()

    # contact sheet
    from PIL import Image, ImageDraw
    ims = [(t, Image.open(f)) for t, f, _ in frames]
    tw = 480; cols = 4
    th = int(ims[0][1].height * tw / ims[0][1].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
    for i, (t, im) in enumerate(ims):
        im = im.resize((tw, th)); d = ImageDraw.Draw(im); d.rectangle([0, 0, 60, 14], fill=(0, 0, 0)); d.text((3, 2), f"{i + 1}: {t}s", fill=(255, 255, 0))
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    sheet.save(out / "contact-sheet.png")

    (out / "auto.json").write_text(json.dumps({"times": times, "issues": issues, "frames": [{"t": t, "file": f.name, "qa": q} for t, f, q in frames]}, indent=1), encoding="utf-8")
    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    issues.sort(key=lambda x: (order[x[0]], x[1] if x[1] is not None else -1))
    print(f"\nQA: {len(frames)} frames in {out / 'frames'}  (contact sheet: {out / 'contact-sheet.png'})")
    for sev, t, msg in issues:
        print(f"  [{sev}] {msg}")
    nfail = sum(1 for s, *_ in issues if s == "FAIL"); nwarn = sum(1 for s, *_ in issues if s == "WARN")
    print(f"automatic checks: {nfail} FAIL, {nwarn} WARN. Now LOOK at every frame image and fill in qa.md.")

    md = story_path.parent / "qa.md"
    if not a.no_md and not md.exists():
        lines = [f"# QA: {story.get('title', story_path.parent.name)}", "", "## Automatic checks (tools/qa.py)", ""]
        lines += [f"- [{s}] {m}" for s, _, m in issues] or ["- none"]
        lines += ["", "## Frames reviewed by eye", "", "| # | t | what I looked at | verdict | action taken |", "|---|---|---|---|---|"]
        lines += [f"| {i + 1} | {t} | TODO | TODO | TODO |" for i, (t, _, _) in enumerate(frames)]
        lines += ["", "## Checklist (tick only what you actually checked)", ""]
        for c in ["camera inside a block", "character out of frame", "subtitle cut off or overlapping", "face turned away in a dialogue shot",
                  "odd shadows / floating objects", "skin holes or missing texture (magenta)", "pacing: any shot too long", "story clear without audio",
                  "energy shape: quiet, loud, quiet", "ending reads (button or card)"]:
            lines.append(f"- [ ] {c}")
        lines += ["", "## Found and fixed", "", "TODO", "", "## Could not verify", "", "TODO (e.g. audio, in-game behaviour)", ""]
        md.write_text("\n".join(lines), encoding="utf-8")
        print("created", md)
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
