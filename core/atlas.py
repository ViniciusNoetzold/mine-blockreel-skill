#!/usr/bin/env python3
"""BlockReel atlas tools: turn a "sheet of all blocks/items" image into individual textures.

You supply the sheet (BlockReel never ships game assets). Typical flow:

  python core/atlas.py slice   sheet.png  work/atlas1          # auto-detect grid, crop, dedupe, contact sheets
  # look at work/atlas1/sheets/sheet_001.png ... and write work/atlas1/labels.json  {"0": "stone", "1": "grass_block"}
  python core/atlas.py label   work/atlas1                      # copy labelled tiles to named/<name>.png
  python core/atlas.py faces   work/atlas1                      # isometric cube icons -> flat top/left/right textures

Teaching it "one by one" = editing labels.json. Labels are plain JSON, so they can be
committed to references/atlas-labels/ and reused for the same sheet next time.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ------------------------------------------------------------- detection ----
def background_colors(arr, min_share=0.02):
    flat = arr.reshape(-1, arr.shape[-1])[::5, :3]
    counts = Counter(map(tuple, flat.tolist()))
    total = sum(counts.values())
    return [c for c, n in counts.items() if n / total >= min_share]


def bg_mask(arr, colors):
    m = np.zeros(arr.shape[:2], bool)
    for c in colors:
        m |= (arr[..., :3] == np.array(c)).all(-1)
    return m


def find_period(mass, lo=8, hi=200):
    s = mass.astype(float) - mass.mean()
    n = len(s)
    ac = np.correlate(s, s, mode="full")[n - 1:]
    if ac[0] == 0:
        raise ValueError("no structure found in image")
    ac = ac / ac[0]
    hi = min(hi, n // 2)
    best = max(range(lo, hi), key=lambda k: ac[k])
    for k in range(lo, best):  # prefer the smallest divisor that is almost as good
        if best % k == 0 and ac[k] >= 0.85 * ac[best]:
            return k
    return best


def find_phase(mass, period):
    """Offset whose window borders fall in the empty gap between cells."""
    folded = np.array([mass[r::period].sum() for r in range(period)])
    low = folded.min()
    idx = np.where(folded <= low * 1.05 + 1e-9)[0]
    # centre of the longest circular run of low values
    runs, cur = [], [idx[0]]
    for i in idx[1:]:
        if i == cur[-1] + 1:
            cur.append(i)
        else:
            runs.append(cur); cur = [i]
    runs.append(cur)
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == period - 1:
        runs[0] = runs[-1] + runs[0]; runs.pop()
    run = max(runs, key=len)
    return int(run[len(run) // 2] % period)


def gap_period(mass):
    """Period from the repeating empty gaps between cells (robust for gridded sheets).
    Returns (period, phase) or None when the cells touch each other."""
    empty = mass <= 0.01 * mass.max()
    starts, centers, i, n = [], [], 0, len(mass)
    while i < n:
        if empty[i]:
            j = i
            while j < n and empty[j]:
                j += 1
            if i > 0 and j < n:  # ignore partial gaps touching the image border
                starts.append(i); centers.append((i + j) // 2)
            i = j
        else:
            i += 1
    if len(centers) < 3:
        return None
    diffs = np.diff(centers)
    # most common spacing (merging +-1 jitter); stray gaps inside a tile are outvoted
    votes = Counter(int(d) for d in diffs if d >= 8)
    if not votes:
        return None
    mode = max(votes, key=votes.get)
    near = [d for d in diffs if abs(d - mode) <= 4]
    period = int(round(float(np.median(near))))
    phase = int(np.median(np.array(centers) % period))
    dist = lambda c: min((c - phase) % period, (phase - c) % period)
    fit = sum(dist(c) <= 6 for c in centers) / len(centers)
    return (period, phase) if fit >= 0.6 else None


def detect_grid(arr, bg):
    content = ~bg_mask(arr, bg)
    col_mass = content.sum(0)
    row_mass = content.sum(1)
    cg, rg = gap_period(col_mass), gap_period(row_mass)
    pw, ox = cg if cg else (find_period(col_mass), None)
    ph, oy = rg if rg else (find_period(row_mass), None)
    if ox is None:
        ox = find_phase(col_mass, pw)
    if oy is None:
        oy = find_phase(row_mass, ph)
    return pw, ph, ox, oy


def native_factor(tiles):
    """Largest integer f such that every tile is an f-times nearest-neighbour upscale."""
    best = 1
    for f in (8, 6, 5, 4, 3, 2):
        ok = True
        for t in tiles[:300]:
            h, w = t.shape[:2]
            if h % f or w % f:
                ok = False; break
            small = t[::f, ::f]
            if not (np.repeat(np.repeat(small, f, 0), f, 1) == t).all():
                ok = False; break
        if ok:
            best = f; break
    return best


# ----------------------------------------------------------------- slice ----
def do_slice(sheet, out_dir, bg=None, grid=None, per_sheet=64):
    out = Path(out_dir)
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    (out / "sheets").mkdir(exist_ok=True)
    arr = np.array(Image.open(sheet).convert("RGB"))
    bg = bg or background_colors(arr)
    if grid:
        pw, ph, ox, oy = grid
    else:
        pw, ph, ox, oy = detect_grid(arr, bg)
    H, W = arr.shape[:2]
    cols = (W - ox) // pw
    rows = (H - oy) // ph
    content = ~bg_mask(arr, bg)
    # common content window inside a cell
    cell_mass = np.zeros((ph, pw), bool)
    for r in range(rows):
        for c in range(cols):
            cell_mass |= content[oy + r * ph: oy + (r + 1) * ph, ox + c * pw: ox + (c + 1) * pw]
    ys, xs = np.where(cell_mass)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cells = []
    for r in range(rows):
        for c in range(cols):
            sl = (slice(oy + r * ph + y0, oy + r * ph + y1), slice(ox + c * pw + x0, ox + c * pw + x1))
            rgb = arr[sl]
            alpha = (~bg_mask(rgb, bg)).astype(np.uint8) * 255
            if alpha.sum() == 0:
                continue
            cells.append((r, c, np.dstack([rgb, alpha])))
    f = native_factor([t for _, _, t in cells])
    seen, uniques, tiles = {}, [], []
    hi_dir = out / "tiles_hi"
    if f > 1:
        hi_dir.mkdir(exist_ok=True)
    for r, c, t in cells:
        native = t[::f, ::f] if f > 1 else t
        key = hashlib.sha1(native.tobytes()).hexdigest()[:12]
        name = f"r{r:03d}_c{c:02d}.png"
        Image.fromarray(native, "RGBA").save(out / "tiles" / name)
        if f > 1:
            Image.fromarray(t, "RGBA").save(hi_dir / name)
        if key not in seen:
            seen[key] = len(uniques)
            uniques.append({"u": len(uniques), "file": name, "count": 0, "first": [r, c]})
        uniques[seen[key]]["count"] += 1
        tiles.append({"row": r, "col": c, "file": name, "unique": seen[key]})
    index = {"source": str(sheet), "cell": [pw, ph], "offset": [ox, oy], "grid": [cols, rows],
             "content_box": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)], "native_factor": f,
             "background": [list(c) for c in bg], "tile_count": len(tiles),
             "unique_count": len(uniques), "uniques": uniques, "tiles": tiles}
    (out / "index.json").write_text(json.dumps(index, indent=1))
    make_contact_sheets(out, uniques, per_sheet)
    if not (out / "labels.json").exists():
        (out / "labels.json").write_text("{}\n")
    return index


def make_contact_sheets(out, uniques, per_sheet=64, cols=8, tile_px=64):
    try:
        font = ImageFont.load_default(size=13)
    except TypeError:
        font = ImageFont.load_default()
    cw, ch = tile_px + 20, tile_px + 28
    for n in range(0, len(uniques), per_sheet):
        chunk = uniques[n:n + per_sheet]
        rows = (len(chunk) + cols - 1) // cols
        img = Image.new("RGB", (cols * cw, rows * ch), (28, 28, 32))
        d = ImageDraw.Draw(img)
        for i, u in enumerate(chunk):
            x, y = (i % cols) * cw, (i // cols) * ch
            t = Image.open(out / "tiles" / u["file"]).convert("RGBA")
            t = t.resize((tile_px, tile_px), Image.NEAREST)
            d.rectangle([x + 9, y + 3, x + 10 + tile_px, y + 4 + tile_px], fill=(60, 60, 66))
            img.paste(t, (x + 10, y + 4), t)
            d.text((x + 10, y + tile_px + 8), f"#{u['u']}", fill=(255, 220, 90), font=font)
        img.save(out / "sheets" / f"sheet_{n // per_sheet + 1:03d}.png")


# ----------------------------------------------------------------- label ----
def safe(name):
    return re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")


def do_label(out_dir):
    out = Path(out_dir)
    index = json.loads((out / "index.json").read_text())
    labels = json.loads((out / "labels.json").read_text())
    named = out / "named"
    named.mkdir(exist_ok=True)
    by_u = {u["u"]: u for u in index["uniques"]}
    done = 0
    for k, name in labels.items():
        u = by_u.get(int(k))
        if not u or not name:
            continue
        Image.open(out / "tiles" / u["file"]).save(named / f"{safe(name)}.png")
        done += 1
    left = len(index["uniques"]) - done
    print(f"labelled {done}, {left} still unlabelled")
    return done


# ----------------------------------------------------------------- faces ----
def hexagon(w, h):
    cx = w / 2
    return [(cx, 0), (w - 1, (h - 1) / 4), (w - 1, 3 * (h - 1) / 4), (cx, h - 1),
            (0, 3 * (h - 1) / 4), (0, (h - 1) / 4)]


def is_cube_icon(tile):
    a = np.array(tile.getchannel("A")) > 0
    ys, xs = np.where(a)
    if len(xs) == 0:
        return False
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    w, h = x1 - x0, y1 - y0
    if w < 0.7 * tile.width or abs(w - h) > 0.25 * w:
        return False
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(hexagon(w, h), fill=1)
    hexm = np.array(m) > 0
    sub = a[y0:y1, x0:x1]
    inside = (sub & hexm).sum() / max(hexm.sum(), 1)
    outside = (sub & ~hexm).sum() / max(sub.sum(), 1)
    return inside > 0.9 and outside < 0.06


def cube_faces(tile, size=16):
    """Unproject an isometric cube icon into flat top / left / right face textures."""
    a = np.array(tile.getchannel("A")) > 0
    ys, xs = np.where(a)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    w, h = x1 - x0, y1 - y0
    cx = x0 + w / 2
    T, UR, LR, B = (cx, y0), (x1, y0 + h / 4), (x1, y0 + 3 * h / 4), (cx, y1)
    LL, UL, C = (x0, y0 + 3 * h / 4), (x0, y0 + h / 4), (cx, y0 + h / 2)

    def quad(nw, sw, se, ne):
        return nw + sw + se + ne  # PIL QUAD order: NW, SW, SE, NE

    out = {}
    out["top"] = tile.transform((size, size), Image.QUAD, quad(T, UL, C, UR), Image.NEAREST)
    out["left"] = tile.transform((size, size), Image.QUAD, quad(UL, LL, B, C), Image.NEAREST)
    out["right"] = tile.transform((size, size), Image.QUAD, quad(C, B, LR, UR), Image.NEAREST)
    return out


def do_faces(out_dir, size=16, only_labelled=True):
    out = Path(out_dir)
    index = json.loads((out / "index.json").read_text())
    labels = json.loads((out / "labels.json").read_text())
    src_dir = out / ("tiles_hi" if (out / "tiles_hi").exists() else "tiles")
    dest = out / "faces"
    dest.mkdir(exist_ok=True)
    n = 0
    for u in index["uniques"]:
        name = labels.get(str(u["u"]))
        if only_labelled and not name:
            continue
        tile = Image.open(src_dir / u["file"]).convert("RGBA")
        if not is_cube_icon(tile):
            continue
        base = safe(name) if name else f"u{u['u']:04d}"
        for face, im in cube_faces(tile, size).items():
            im.save(dest / f"{base}_{face}.png")
        n += 1
    print(f"extracted faces for {n} cube-shaped blocks into {dest}")
    return n


# ------------------------------------------------------------------- CLI ----
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("slice"); p.add_argument("sheet"); p.add_argument("out_dir")
    p.add_argument("--grid", help="cellW,cellH,offsetX,offsetY (skip auto-detect)")
    p.add_argument("--bg", help="background colours 'r,g,b;r,g,b' (skip auto-detect)")
    p.add_argument("--per-sheet", type=int, default=64)
    p = sub.add_parser("label"); p.add_argument("out_dir")
    p = sub.add_parser("faces"); p.add_argument("out_dir"); p.add_argument("--size", type=int, default=16)
    p.add_argument("--all", action="store_true", help="also unlabelled tiles")
    a = ap.parse_args(argv)
    if a.cmd == "slice":
        grid = tuple(int(x) for x in a.grid.split(",")) if a.grid else None
        bg = [tuple(int(v) for v in c.split(",")) for c in a.bg.split(";")] if a.bg else None
        idx = do_slice(a.sheet, a.out_dir, bg, grid, a.per_sheet)
        print(f"cell {idx['cell']} grid {idx['grid']} | {idx['tile_count']} tiles, {idx['unique_count']} unique "
              f"| native factor x{idx['native_factor']} | contact sheets in {a.out_dir}/sheets")
    elif a.cmd == "label":
        do_label(a.out_dir)
    elif a.cmd == "faces":
        do_faces(a.out_dir, a.size, not a.all)
    return 0


if __name__ == "__main__":
    sys.exit(main())
