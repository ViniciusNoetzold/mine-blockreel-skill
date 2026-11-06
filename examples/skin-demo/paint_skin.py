#!/usr/bin/env python3
"""Original demo skin: "Ranger" (a hooded woodland scout). CC0, painted from scratch with BlockReel's SkinCanvas.

  python examples/skin-demo/paint_skin.py out/ranger.png [--slim] [--detail 0|1|2|3]

Process used (see examples/skin-demo/README.md):
  1. palette plan: a 4-tone ramp per material (skin, hair, tunic, cloak, leather, trousers, boots, metal)
  2. base layer first (head, body, arms, legs), then the overlay layer (hood = hat, open cloak = jacket, sleeves = shoulder mantle)
  3. render tools/turntable.py, LOOK, fix, repeat  (--detail 0..3 are the saved states of those iterations)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "core"))
import skin as S  # noqa: E402

PALETTE_PLAN = {                      # base colour -> ramp(4): dark, mid-dark, mid-light, light
    "skin": "e3a77a", "hair": "a8532b", "tunic": "56803c", "cloak": "2f5a3a", "leather": "7b5231",
    "trousers": "5d4d3c", "boots": "3a2a1e", "metal": "c9b25a", "eyes": "2f8f5f",
}


def paint(slim=False, detail=3, seed=11):
    cv = S.SkinCanvas(slim=slim, seed=seed)
    plan = dict(PALETTE_PLAN)
    if detail >= 2:
        plan["cloak"] = "3a7466"                       # iteration 2: the dark green cloak read as a black slab; lighter + bluer
    R = {k: S.ramp(v, 4, hue_shift=0.04) for k, v in plan.items()}   # hue_shift: cooler shadows, warmer lights
    skin, hair, tunic, cloak, leather, trou, boots, metal = (R[k] for k in ("skin", "hair", "tunic", "cloak", "leather", "trousers", "boots", "metal"))
    EYE = S.hexcolor(PALETTE_PLAN["eyes"]); WHITE = (240, 240, 235, 255); DARK = (28, 20, 18, 255)
    n = 0.035 if detail >= 3 else 0.0                       # subtle noise only in the final pass (flat tones read cleaner at low res)

    # ---------------- BASE LAYER ----------------
    cv.shaded_box("head", skin, n)
    cv.shaded_box("body", tunic, n)
    cv.shaded_box("right_arm", tunic, n)
    cv.shaded_box("right_leg", trou, n)
    # head: hair cap (top, back, sides, fringe)
    for f in ("top", "back"):
        cv.fill("head", f, hair[1], n)
    for f in ("left", "right"):
        cv.rect("head", f, 0, 0, 8, 3, hair[1], n); cv.rect("head", f, 5 if f == "left" else 0, 3, 3, 3, hair[1], n)
    cv.rect("head", "front", 0, 0, 8, 2, hair[2], n)
    cv.rect("head", "front", 0, 2, 1, 2, hair[1]); cv.rect("head", "front", 7, 2, 1, 2, hair[1])
    cv.rect("head", "front", 2, 2, 4, 1, hair[1])                                   # fringe over the brow
    # face
    cv.rect("head", "front", 1, 4, 2, 1, WHITE); cv.rect("head", "front", 5, 4, 2, 1, WHITE)
    cv.px("head", "front", 2, 4, EYE); cv.px("head", "front", 5, 4, EYE)
    cv.rect("head", "front", 3, 6, 2, 1, S.shade(skin[1], 0.85))                  # mouth
    if detail >= 1:
        cv.rect("head", "front", 1, 3, 2, 1, hair[0]); cv.rect("head", "front", 5, 3, 2, 1, hair[0])   # brows
        if detail == 1:                                  # iteration 1 (kept for the record): too busy, cheeks read as freckles, the jaw as a beard
            cv.rect("head", "front", 3, 5, 2, 1, skin[3])
            cv.px("head", "front", 1, 5, S.shade(skin[2], 1.05)); cv.px("head", "front", 6, 5, S.shade(skin[2], 1.05))
            cv.rect("head", "front", 2, 7, 4, 1, skin[0])
        else:                                            # iteration 2: one nose pixel and the mouth, nothing else on the face
            cv.px("head", "front", 3, 5, skin[3])
    # body: collar, belt, buckle
    if detail >= 1:
        cv.rect("body", "front", 3, 0, 2, 2, skin[1]); cv.rect("body", "front", 2, 0, 1, 1, tunic[0]); cv.rect("body", "front", 5, 0, 1, 1, tunic[0])
        cv.rect("body", "front", 0, 8, 8, 2, leather[1]); cv.rect("body", "back", 0, 8, 8, 2, leather[0])
        cv.rect("body", "front", 3, 8, 2, 2, metal[2]); cv.px("body", "front", 3, 8, metal[3]); cv.px("body", "front", 4, 9, metal[0])
        cv.rect("body", "front", 0, 10, 8, 2, tunic[0])                                   # tunic hem shadow
    # arms: bracer on the forearm, hand
    for part in ("right_arm",):
        cv.rect(part, "front", 0, 10, 4, 2, skin[2], n); cv.rect(part, "back", 0, 10, 4, 2, skin[1], n)
        cv.rect(part, "left", 0, 10, 4, 2, skin[1], n); cv.rect(part, "right", 0, 10, 4, 2, skin[1], n); cv.fill(part, "bottom", skin[0])
        if detail >= 1:
            for f in ("front", "back", "left", "right"):
                cv.rect(part, f, 0, 7, 4, 3, leather[2 if f == "front" else 1], n)
            cv.line(part, "front", 0, 7, 3, 7, leather[3]); cv.line(part, "front", 0, 9, 3, 9, leather[0])
    # legs: trousers, boots with a cuff
    for f in ("front", "back", "left", "right"):
        cv.rect("right_leg", f, 0, 7, 4, 5, boots[1 if f != "front" else 2], n)
        if detail >= 1:
            cv.rect("right_leg", f, 0, 7, 4, 1, boots[3])                                   # folded cuff
    cv.fill("right_leg", "bottom", boots[0])
    if detail >= 2:
        cv.line("right_leg", "front", 1, 2, 1, 6, trou[3]); cv.rect("right_leg", "front", 0, 4, 4, 1, trou[1])   # seam + knee fold
        cv.px("right_leg", "front", 1, 11, boots[3])                                         # toe shine

    # ---------------- OVERLAY LAYER (drawn after the base, so it sits on top) ----------------
    # hood = hat layer: crown, back, sides, a brim over the forehead (the face stays open)
    cv.fill("hat", "top", cloak[2], n); cv.fill("hat", "back", cloak[1], n)
    for f in ("left", "right"):
        cv.fill("hat", f, cloak[1], n); cv.rect("hat", f, 4 if f == "left" else 0, 5, 4, 3, (0, 0, 0, 0))
    cv.rect("hat", "front", 0, 0, 8, 2, cloak[2], n); cv.rect("hat", "front", 0, 2, 1, 5, cloak[1], n); cv.rect("hat", "front", 7, 2, 1, 5, cloak[1], n)
    if detail >= 2:
        cv.rect("hat", "front", 0, 2, 8, 1, cloak[0])                                       # brim shadow on the forehead
        cv.line("hat", "top", 3, 0, 3, 7, cloak[3]); cv.line("hat", "top", 4, 1, 4, 6, cloak[0])      # hood seam
        cv.rect("hat", "back", 0, 5, 8, 3, cloak[0], n)                                     # hood bunches at the nape
    # open cloak = jacket layer: shoulder mantle plus two panels at the front edges, full back
    cv.rect("jacket", "top", 0, 0, 8, 4, cloak[2], n)
    cv.rect("jacket", "back", 0, 0, 8, 12, cloak[1], n); cv.rect("jacket", "left", 0, 0, 4, 12, cloak[1], n); cv.rect("jacket", "right", 0, 0, 4, 12, cloak[1], n)
    edge = 2 if detail < 2 else 1                          # iteration 2: 2 px front panels read as black bars; 1 px edges
    cv.rect("jacket", "front", 0, 0, edge, 12, cloak[1], n); cv.rect("jacket", "front", 8 - edge, 0, edge, 12, cloak[1], n); cv.rect("jacket", "front", 0, 0, 8, 2, cloak[2], n)
    cv.rect("jacket", "bottom", 0, 0, 8, 4, cloak[0])
    if detail >= 2:
        for x, c in ((1, cloak[2]), (2, cloak[0]), (4, cloak[3]), (5, cloak[0]), (6, cloak[2])):
            cv.rect("jacket", "back", x, 2, 1, 10, c)                                       # cloak folds: light and dark stripes
        cv.rect("jacket", "back", 0, 11, 8, 1, cloak[0]); cv.rect("jacket", "front", 0, 11, 2, 1, cloak[0]); cv.rect("jacket", "front", 6, 11, 2, 1, cloak[0])
        cv.px("jacket", "front", 2, 1, metal[2]); cv.px("jacket", "front", 5, 1, metal[2])  # clasp pins on the mantle
        cv.line("jacket", "front", 2, 1, 5, 1, metal[1])                                     # chain between them
    # shoulder mantle on the sleeve overlay
    cv.rect("right_sleeve", "top", 0, 0, 4, 4, cloak[2], n)
    for f in ("front", "back", "left", "right"):
        cv.rect("right_sleeve", f, 0, 0, 4, 3, cloak[1], n)
    if detail >= 2:
        for f in ("front", "back", "left", "right"):
            cv.rect("right_sleeve", f, 0, 2, 4, 1, cloak[0])
    if detail >= 3:                                         # last pass: small imperfections that read as hand-painted
        cv.px("head", "front", 0, 4, hair[0]); cv.px("head", "front", 7, 4, hair[0])
        cv.px("hat", "front", 2, 1, cloak[3]); cv.px("hat", "front", 5, 1, cloak[3])
        cv.px("body", "front", 1, 5, tunic[3]); cv.px("body", "front", 6, 3, tunic[3]); cv.px("body", "front", 2, 6, tunic[0])

    cv.mirror_limbs(layers=True)                            # paint the right side, get the left for free
    return cv.img


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out"); ap.add_argument("--slim", action="store_true"); ap.add_argument("--detail", type=int, default=3)
    a = ap.parse_args(argv)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    paint(a.slim, a.detail).save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
