#!/usr/bin/env python3
"""BlockReel tile checker: does a texture repeat without visible seams, what is its palette, and does the whole SET look coherent?

  python core/tilecheck.py check  stone.png --out stone_tiles.png        # 2x2 and 3x3 tiling preview + seam score
  python core/tilecheck.py palette stone.png -k 6                         # dominant colours
  python core/tilecheck.py set    textures/block --out report/            # every texture: palette, seam, brightness; outliers; contact sheet

Animated textures (a tall strip with a `.png.mcmeta`) are checked frame by frame.
The numbers are heuristics. PROBLEMS (visible seam, size mismatch, too many colours) fail the run; notes (brightness, saturation,
palette overlap) are advisory. They do not judge taste: look at the preview images and the contact sheet.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# textures that carry an intentional border or are not meant to tile (their tile seam is by design): reported as notes, never as problems
FRAMED = ('glass', '_block', 'side', 'tnt', 'item/', 'diamond', 'stick')


def frames(path):
    """The frames of a texture: [img] for a static one, several for an animated strip."""
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    meta = Path(str(path) + ".mcmeta")
    n = 1
    if meta.exists():
        try:
            anim = json.loads(meta.read_text(encoding="utf-8")).get("animation", {})
            fw, fh = anim.get("width", w), anim.get("height", w if h >= w else h)
            if fw and fh and w % fw == 0 and h % fh == 0:
                cols, rows = w // fw, h // fh
                return [im.crop((c * fw, r * fh, (c + 1) * fw, (r + 1) * fh)) for r in range(rows) for c in range(cols)]
        except Exception:  # noqa: BLE001
            pass
    elif h > w and h % w == 0:
        n = h // w
    return [im.crop((0, i * (h // n), w, (i + 1) * (h // n))) for i in range(n)]


def _pixels(im):
    """RGBA tuples of an image (works on every Pillow version; getdata() is deprecated)."""
    raw = im.convert("RGBA").tobytes()
    return [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]


def _diff(a, b):
    return sum(abs(x - y) for x, y in zip(a[:3], b[:3])) / 3.0


def seam_score(im):
    """How visible is the wrap-around seam? The mean difference across the tile edge (pixel column/row 15 next to 0) is compared with the
    WORST mean difference of any interior column/row boundary. A pattern with real structure (bricks, planks) has strong interior
    boundaries too, so its edge is not worse than them; a texture cut out of a gradient has an edge far worse than everything inside it.
    ratio <= 1 means "no worse than the worst interior boundary"; > 1.25 (and a clearly visible difference) means a visible seam."""
    px = im.load(); w, h = im.size
    ok = lambda p: p[3] > 0  # noqa: E731
    def col_diff(x0, x1):
        v = [_diff(px[x0, y], px[x1, y]) for y in range(h) if ok(px[x0, y]) and ok(px[x1, y])]
        return sum(v) / len(v) if v else 0.0
    def row_diff(y0, y1):
        v = [_diff(px[x, y0], px[x, y1]) for x in range(w) if ok(px[x, y0]) and ok(px[x, y1])]
        return sum(v) / len(v) if v else 0.0
    inner_x = max([col_diff(x, x + 1) for x in range(w - 1)] or [0.0]); inner_y = max([row_diff(y, y + 1) for y in range(h - 1)] or [0.0])
    edge_x, edge_y = col_diff(w - 1, 0), row_diff(h - 1, 0)
    rx = edge_x / inner_x if inner_x else (9.9 if edge_x > 4 else 0.0)
    ry = edge_y / inner_y if inner_y else (9.9 if edge_y > 4 else 0.0)
    bad = (rx > 1.25 and edge_x > 10) or (ry > 1.25 and edge_y > 10)
    return {"edge_x": round(edge_x, 1), "edge_y": round(edge_y, 1), "ratio_x": round(rx, 2), "ratio_y": round(ry, 2), "visible_seam": bool(bad)}


def tile_preview(path, out, scale=None):
    """Write a preview: the texture tiled 2x2 and 3x3 side by side (nearest-neighbour upscale so you can see single pixels)."""
    fr = frames(path)[0]
    w, h = fr.size
    s = scale or max(1, 192 // w)
    big = fr.resize((w * s, h * s), Image.NEAREST)
    bg = Image.new("RGBA", (1, 1), (60, 60, 66, 255))
    def tiled(n):
        im = Image.new("RGBA", (big.width * n, big.height * n), (60, 60, 66, 255))
        for ty in range(n):
            for tx in range(n):
                im.alpha_composite(big, (tx * big.width, ty * big.height))
        return im
    a, b = tiled(2), tiled(3)
    sheet = Image.new("RGBA", (a.width + b.width + 12, max(a.height, b.height) + 16), (30, 30, 34, 255))
    sheet.paste(a, (4, 12)); sheet.paste(b, (a.width + 8, 12))
    d = ImageDraw.Draw(sheet); d.text((4, 0), "2x2", fill=(255, 255, 0, 255)); d.text((a.width + 8, 0), "3x3", fill=(255, 255, 0, 255))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out)
    return out


def palette(im, k=8):
    """Dominant colours (hex, share of opaque pixels), most frequent first."""
    rgba = im.convert("RGBA")
    opaque = [p[:3] for p in _pixels(rgba) if p[3] > 8]
    if not opaque:
        return []
    img = Image.new("RGB", (len(opaque), 1)); img.putdata(opaque)
    q = img.quantize(colors=min(k, max(1, len(set(opaque)))), method=Image.MEDIANCUT)
    pal = q.getpalette(); counts = sorted(q.getcolors(), reverse=True)
    return [("#%02x%02x%02x" % tuple(pal[i * 3:i * 3 + 3]), round(c / len(opaque), 3)) for c, i in counts]


def stats(im):
    """Mean luminance and saturation (0..1) of the opaque pixels, and the number of distinct colours."""
    allpx = _pixels(im)
    px = [p for p in allpx if p[3] > 8]
    if not px:
        return {"lum": 0.0, "sat": 0.0, "colors": 0, "alpha": True}
    lum = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b, _ in px) / len(px) / 255
    sat = sum((max(p[:3]) - min(p[:3])) / max(1, max(p[:3])) for p in px) / len(px)
    return {"lum": round(lum, 3), "sat": round(sat, 3), "colors": len(set(p[:3] for p in px)), "alpha": any(p[3] < 250 for p in allpx)}


def check_file(path):
    fr = frames(path)
    seams = [seam_score(f) for f in fr]
    worst = max(seams, key=lambda s: max(s["ratio_x"], s["ratio_y"]))
    first = fr[0]
    r = {"file": Path(path).name, "size": list(first.size), "frames": len(fr), "seam": worst, "palette": palette(first, 6), **stats(first)}
    return r


def set_report(folder, out):
    folder, out = Path(folder), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in folder.rglob("*.png") if not (p.name == "pack.png" and p.parent == folder))  # the pack icon is not a texture
    rows = [check_file(f) for f in files]
    if not rows:
        return {"count": 0, "rows": [], "issues": ["no PNG files found"]}
    med = lambda xs: sorted(xs)[len(xs) // 2]  # noqa: E731
    mlum, msat = med([r["lum"] for r in rows]), med([r["sat"] for r in rows])
    sizes = {tuple(r["size"]) for r in rows}
    issues, notes = [], []
    base_size = med([r["size"][0] for r in rows])
    # shared palette: how much of the set uses colours that other textures also use
    from collections import Counter
    cnt = Counter()
    per = {}
    for f, r in zip(files, rows):
        im = frames(f)[0].convert("RGBA")
        cols = {(p[0] >> 5, p[1] >> 5, p[2] >> 5) for p in _pixels(im) if p[3] > 8}
        per[r["file"]] = cols; cnt.update(cols)
    for f, r in zip(files, rows):
        cols = per[r["file"]]
        shared = sum(1 for c in cols if cnt[c] >= 3) / max(1, len(cols))
        r["shared_palette"] = round(shared, 2)
        name = r["file"]
        if r["seam"]["visible_seam"]:
            msg = f"{name}: visible tiling seam (edge diff {max(r['seam']['edge_x'], r['seam']['edge_y'])}, ratio {max(r['seam']['ratio_x'], r['seam']['ratio_y'])})"
            rel = f.relative_to(folder).as_posix()
            if any(k in rel for k in FRAMED) and 'snow' not in rel:
                notes.append(msg + " [framed/non-tiling texture: fine if the border is intended]")
            else:
                issues.append(msg)
        if abs(r["lum"] - mlum) > 0.40:
            notes.append(f"{name}: brightness {r['lum']} is far from the set median {mlum} (fine for snow, sand, obsidian; odd for anything else)")
        if abs(r["sat"] - msat) > 0.50:
            notes.append(f"{name}: saturation {r['sat']} is far from the set median {msat} (grey stone and white wool are naturally low)")
        if r["size"][0] != base_size:
            issues.append(f"{name}: size {r['size'][0]} differs from the set's {base_size}")
        if r["colors"] > 64 and r["size"][0] <= 32:
            issues.append(f"{name}: {r['colors']} distinct colours for a {r['size'][0]}px texture (noisy; most pixel-art styles use ~8-24)")
        if r["shared_palette"] < 0.1 and len(rows) > 6:
            notes.append(f"{name}: shares few colours with the rest of the set ({r['shared_palette']}); check that it belongs to the same style")
    # contact sheet
    cell = 96; cols_n = 6; rows_n = (len(files) + cols_n - 1) // cols_n
    sheet = Image.new("RGB", (cols_n * cell, rows_n * (cell + 14)), (30, 30, 34))
    d = ImageDraw.Draw(sheet)
    for i, (f, r) in enumerate(zip(files, rows)):
        fr = frames(f)[0]
        t = fr.resize((cell - 8, cell - 8), Image.NEAREST)
        x, y = (i % cols_n) * cell, (i // cols_n) * (cell + 14)
        tile = Image.new("RGBA", (cell - 8, cell - 8), (60, 60, 66, 255)); tile.alpha_composite(t)
        sheet.paste(tile.convert("RGB"), (x + 4, y + 2))
        d.text((x + 4, y + cell - 4), r["file"][:15], fill=(255, 80, 80) if any(r["file"] in m for m in issues) else (255, 200, 80) if any(r["file"] in m for m in notes) else (220, 220, 220))
    sheet.save(out / "set-sheet.png")
    rep = {"count": len(rows), "median_lum": mlum, "median_sat": msat, "sizes": sorted(sizes), "issues": issues, "notes": notes, "rows": rows}
    (out / "set-report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check"); p.add_argument("path"); p.add_argument("--out")
    p = sub.add_parser("palette"); p.add_argument("path"); p.add_argument("-k", type=int, default=8)
    p = sub.add_parser("set"); p.add_argument("folder"); p.add_argument("--out", default="tilecheck-report")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        r = check_file(a.path)
        print(json.dumps(r, indent=1))
        if a.out:
            tile_preview(a.path, a.out); print("wrote", a.out)
        return 1 if r["seam"]["visible_seam"] else 0
    if a.cmd == "palette":
        for hexc, share in palette(frames(a.path)[0], a.k):
            print(hexc, f"{share:.1%}")
        return 0
    rep = set_report(a.folder, a.out)
    print(f"{rep['count']} textures; median brightness {rep.get('median_lum')}, saturation {rep.get('median_sat')}; sizes {rep.get('sizes')}")
    for i in rep["issues"]:
        print(" PROBLEM:", i)
    for n_ in rep.get("notes", []):
        print(" note:", n_)
    print("sheet:", Path(a.out) / "set-sheet.png")
    return 1 if rep["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
