#!/usr/bin/env python3
"""Persona -> Minecraft skin. Turn a description of a real person (usually read from a photo) into a polished 64x64 skin.

The assistant looks at the photo and writes persona.json (what the person looks like); `sample` reads the exact colours
from regions of the photo; `paint` renders the skin with 3-4 tone ramps, soft vertical shading, a hair/hood volume on the
overlay layer and a face laid out for BlockReel's face states (eyes on row 4, brows row 3, mouth row 6).

  python core/persona.py sample photo.jpg --region skin=410,300,450,340 --region hair=380,120,520,170 \\
                                          --region top=330,620,560,760 --region bottom=360,900,520,1000 --out colors.json
  python core/persona.py paint persona.json skin.png [--colors colors.json] [--preview tt.png]
  python core/persona.py preset herobrine herobrine.png          # original CC0 painting
  python core/persona.py preset herobrine herobrine.png --from-steve work/vanilla/entity/steve.png   # the iconic look, local only
  python core/persona.py example > persona.json                   # a filled-in template

persona.json (every field optional):
{ "model": "classic|slim", "skin": "#c68e6a",
  "hair":  { "color": "#3b2416", "style": "short|buzz|sidepart|spiky|curly|afro|long|ponytail|bun|bob|mohawk|bald" },
  "eyes":  { "color": "#5a3a22" }, "brows": "#2a1a10", "mouth": "neutral|smile", "blush": false,
  "facial_hair": "none|stubble|mustache|goatee|beard", "facial_hair_color": "#2a1a10",
  "glasses": null | { "style": "round|square|sun", "color": "#222222" },
  "top":    { "type": "tshirt|longsleeve|hoodie|jacket|shirt|suit|tank|sweater|dress", "color": "#2e8bc0", "accent": "#ffffff",
              "pattern": "none|stripes|plaid|logo", "pattern_color": "#ffffff" },
  "bottom": { "type": "jeans|pants|shorts|skirt", "color": "#3b4f7a" },
  "shoes":  { "type": "sneakers|boots|shoes", "color": "#f0f0f0" },
  "accessory": "none|cap|beanie|headphones|scarf|necklace|backpack|crown|hood", "accessory_color": "#c03030",
  "eye_glow": false }
"""
import argparse
import json
import random
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from skin import SkinCanvas, hexcolor, ramp, shade, validate  # noqa: E402

LIGHT = {"top": 1.08, "front": 1.0, "left": 0.9, "right": 0.9, "back": 0.84, "bottom": 0.72}
LIMB_FACES = ("front", "back", "left", "right")


def _c(v, default):
    if v is None:
        v = default
    return hexcolor(v) if isinstance(v, str) else tuple(v) + ((255,) if len(v) == 3 else ())


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)) + (255,)


class Painter:
    def __init__(self, p, seed=11):
        self.p = p; self.slim = p.get("model") == "slim"; self.cv = SkinCanvas(self.slim, seed); self.rng = random.Random(seed)

    # a face filled with a vertical gradient (lighter at the top) and a whisper of noise: reads as cloth/skin, not flat paint
    def shade_face(self, part, face, base, x=0, y=0, w=None, h=None, grad=0.14, noise=0.025, light=True):
        from skin import face_rect
        _, _, fw, fh = face_rect(part, face, self.slim)
        w = fw - x if w is None else w; h = fh - y if h is None else h
        k0 = LIGHT[face] if light else 1.0
        for yy in range(y, min(fh, y + h)):
            g = 1 + grad * (0.5 - (yy / max(1, fh - 1))) if face not in ("top", "bottom") else 1
            for xx in range(x, min(fw, x + w)):
                f = k0 * g * (1 + self.rng.uniform(-noise, noise))
                self.cv.px(part, face, xx, yy, shade(base, f))

    def box(self, part, base, **kw):
        for f in ("top", "bottom", "front", "back", "left", "right"):
            self.shade_face(part, f, base, **kw)

    def limb_rows(self, part, y0, y1, base, **kw):  # rows y0..y1-1 on the 4 vertical faces
        for f in LIMB_FACES:
            self.shade_face(part, f, base, y=y0, h=y1 - y0, **kw)

    # ------------------------------------------------------------------------------------------------- head ----
    def head(self):
        p = self.p; S = _c(p.get("skin"), "#c99a73"); hair = p.get("hair") or {}; H = _c(hair.get("color"), "#3b2416")
        style = hair.get("style", "short"); E = _c((p.get("eyes") or {}).get("color"), "#3a5f9a"); B = _c(p.get("brows"), shade(H, 0.8)[:3])
        cv = self.cv; HR = ramp(H, 4, 0.22, 0.03)
        self.box("head", S, grad=0.06)
        # hair on the base layer
        bald = style == "bald"; long_ = style in ("long", "ponytail", "bob")
        if not bald:
            self.shade_face("head", "top", H)
            back_rows = 8 if long_ else 6 if style in ("bun", "curly", "afro", "short", "sidepart", "spiky") else 4
            self.shade_face("head", "back", H, h=back_rows)
            for side in ("left", "right"):
                rows = 7 if long_ else 3
                self.shade_face("head", side, H, h=rows)
                ex = 4 if side == "right" else 3  # sideburn column next to the face
                self.shade_face("head", side, H, x=(5 if side == "right" else 0), w=3, y=3, h=1) if not long_ else None
                cv.px("head", side, ex, 4, shade(S, 0.8)); cv.px("head", side, ex, 5, shade(S, 0.85))  # ear
            # fringe on the face
            fringe = {"buzz": 1, "short": 2, "sidepart": 2, "spiky": 2, "curly": 2, "afro": 2, "long": 2, "ponytail": 2, "bun": 1, "bob": 3, "mohawk": 1}.get(style, 2)
            self.shade_face("head", "front", H, h=fringe, grad=0)
            if style == "sidepart":
                for x in range(5, 8):
                    cv.px("head", "front", x, 2, HR[1])
            if style in ("spiky", "short", "curly"):
                for x in (0, 7):
                    cv.px("head", "front", x, 2, HR[1])
            if long_ or style == "bob":
                for y in range(2, 7 if long_ else 5):
                    cv.px("head", "front", 0, y, HR[1]); cv.px("head", "front", 7, y, HR[1])
            if style == "mohawk":
                for f in ("left", "right"):
                    self.shade_face("head", f, shade(S, 0.92), h=3)
        # face: brows row 3, eyes row 4 (white + iris looking in), nose shade row 5, mouth row 6
        for x in (1, 2):
            cv.px("head", "front", x, 3, B)
        for x in (5, 6):
            cv.px("head", "front", x, 3, B)
        white = (244, 244, 244, 255)
        cv.px("head", "front", 1, 4, white); cv.px("head", "front", 2, 4, E)
        cv.px("head", "front", 5, 4, E); cv.px("head", "front", 6, 4, white)
        if p.get("eye_glow"):
            for x in (1, 2, 5, 6):
                cv.px("head", "front", x, 4, (255, 255, 255, 255))
        cv.px("head", "front", 3, 5, shade(S, 0.86)); cv.px("head", "front", 4, 5, shade(S, 0.86))
        lip = _mix(shade(S, 0.62), (150, 60, 60), 0.25)
        if p.get("mouth") == "smile":
            cv.px("head", "front", 2, 5, shade(S, 0.7)); cv.px("head", "front", 5, 5, shade(S, 0.7))
            for x in (3, 4):
                cv.px("head", "front", x, 6, lip)
            cv.px("head", "front", 2, 6, shade(S, 0.75)); cv.px("head", "front", 5, 6, shade(S, 0.75))
        else:
            for x in (3, 4):
                cv.px("head", "front", x, 6, lip)
        if p.get("blush"):
            cv.px("head", "front", 1, 5, _mix(S, (230, 120, 120), 0.35)); cv.px("head", "front", 6, 5, _mix(S, (230, 120, 120), 0.35))
        fh = p.get("facial_hair", "none"); FH = _c(p.get("facial_hair_color"), H[:3])
        if fh == "stubble":
            for y in (5, 6, 7):
                for x in range(8):
                    if (x in (3, 4) and y == 6) or self.rng.random() > 0.55:
                        continue
                    cv.px("head", "front", x, y, _mix(S, FH, 0.35))
        elif fh in ("beard", "goatee", "mustache"):
            if fh in ("beard", "mustache"):
                for x in range(2, 6):
                    cv.px("head", "front", x, 5, shade(FH, 0.95))
            if fh == "beard":
                for y in (6, 7):
                    for x in range(8):
                        cv.px("head", "front", x, y, shade(FH, 1.0 - 0.06 * (y - 6)))
                for x in (3, 4):
                    cv.px("head", "front", x, 6, lip)
                for y in (4, 5):
                    cv.px("head", "front", 0, y, FH); cv.px("head", "front", 7, y, FH)
                self.shade_face("head", "bottom", FH)
                for side in ("left", "right"):
                    self.shade_face("head", side, FH, x=(4 if side == "right" else 0), w=4, y=5, h=3)
            if fh == "goatee":
                for x in (3, 4):
                    cv.px("head", "front", x, 7, FH)
        # overlay: hair volume. The hat layer is a shell 0.5 px bigger than the head: a partial shell reads as steps or a missing
        # piece, so short styles stay on the base layer (a clean cube, like the default skins) and volume styles get a shell that
        # follows the base hair EXACTLY on every face (same rows front, sides and back): one continuous layer of hair, no steps.
        VOLUME = {"long": (2, 7, 8), "ponytail": (2, 7, 8), "bob": (3, 7, 8), "afro": (2, 3, 6), "curly": (2, 3, 6), "bun": (1, 3, 6)}
        if not bald and style in VOLUME:
            fr, sd, bk = VOLUME[style]; hv = HR[2]
            self.shade_face("hat", "top", hv, noise=0.04)
            self.shade_face("hat", "back", hv, h=bk)
            for side in ("left", "right"):
                self.shade_face("hat", side, hv, h=sd)
            self.shade_face("hat", "front", hv, h=fr, grad=0)
            if long_ or style == "bob":  # the strands framing the face continue down the shell, as on the base
                for y in range(fr, 7 if long_ else 5):
                    cv.px("hat", "front", 0, y, HR[1]); cv.px("hat", "front", 7, y, HR[1])
            if style in ("curly", "afro"):  # curls as texture inside the shell (never loose pixels below its edge)
                for f, rows in (("front", fr), ("left", sd), ("right", sd), ("back", bk), ("top", 8)):
                    for y in range(rows):
                        for x in range(8):
                            if (x + y * 3) % 4 == 0:
                                cv.px("hat", f, x, y, HR[1] if (x + y) % 2 else HR[3])
            if style == "ponytail":
                for y in range(4, 8):
                    cv.px("hat", "back", 3, y, HR[1]); cv.px("hat", "back", 4, y, HR[2])
            if style == "bun":
                for x in (3, 4):
                    cv.px("hat", "top", x, 6, HR[3]); cv.px("hat", "back", x, 0, HR[3])
        if style == "spiky" and not bald:  # spikes are texture on the base, not loose bits of shell
            for x in range(0, 8, 2):
                cv.px("head", "front", x, 1, HR[3])
        if style == "mohawk":  # the one intended raised strip
            for y in range(8):
                for x in (3, 4):
                    cv.px("hat", "top", x, y, HR[3])
            for f in ("front", "back"):
                for x in (3, 4):
                    cv.px("hat", f, x, 0, HR[3])
        g = p.get("glasses")
        if g:
            gc = _c(g.get("color") if isinstance(g, dict) else None, "#2e2e30"); st = g.get("style", "square") if isinstance(g, dict) else "square"
            lens = (30, 30, 36, 255) if st == "sun" else None
            for x in (0, 3, 4, 7):
                cv.px("hat", "front", x, 4, gc)
            for x in (1, 2, 5, 6):
                cv.px("hat", "front", x, 3, gc)
                if lens:
                    cv.px("hat", "front", x, 4, lens)
            if st == "round":
                for x in (1, 6):
                    cv.px("hat", "front", x, 5, shade(gc, 1.3))
            for side in ("left", "right"):  # temples on the base layer (a loose bit of the shell would float)
                for x in ((5, 6, 7) if side == "right" else (0, 1, 2)):
                    cv.px("head", side, x, 4, gc)
        acc = p.get("accessory", "none"); A = _c(p.get("accessory_color"), "#c03030")
        if acc in ("cap", "beanie", "crown", "hood"):
            for f in ("top", "front", "back", "left", "right"):
                self.cv.clear("hat", f)
            if acc == "cap":
                self.shade_face("hat", "top", A); self.shade_face("hat", "back", A, h=3)
                for f in ("left", "right"):
                    self.shade_face("hat", f, A, h=3)
                self.shade_face("hat", "front", A, h=2, grad=0); self.shade_face("head", "front", shade(A, 0.75), h=1, grad=0)
            elif acc == "beanie":
                for f in ("top", "back", "left", "right", "front"):
                    self.shade_face("hat", f, A, h=8 if f == "top" else 3, noise=0.05)
                for x in range(8):
                    self.cv.px("hat", "front", x, 2, shade(A, 0.8))
            elif acc == "crown":
                gold = (240, 196, 60, 255)
                for f in ("front", "back", "left", "right"):
                    for x in range(8):
                        self.cv.px("hat", f, x, 1, gold)
                        if x % 3 == 1:
                            self.cv.px("hat", f, x, 0, gold)
                self.cv.px("hat", "front", 3, 1, (220, 40, 60, 255)); self.cv.px("hat", "front", 4, 1, (60, 120, 230, 255))
            elif acc == "hood":
                for f in ("top", "back", "left", "right"):
                    self.shade_face("hat", f, A, h=8)
                self.shade_face("hat", "front", A, h=2, grad=0)
                for y in range(2, 8):
                    self.cv.px("hat", "front", 0, y, shade(A, 0.8)); self.cv.px("hat", "front", 7, y, shade(A, 0.8))
        elif acc == "headphones":
            for side in ("left", "right"):
                for y in range(3, 7):
                    for x in range(2, 6):
                        self.cv.px("hat", side, x, y, shade(A, 0.9 if 2 < x < 5 else 0.7))
            for x in range(8):
                self.cv.px("hat", "top", 3, x, A); self.cv.px("hat", "top", 4, x, shade(A, 0.85))

    # ------------------------------------------------------------------------------------------------- body ----
    def body(self):
        p = self.p; S = _c(p.get("skin"), "#c99a73"); top = p.get("top") or {}; T = _c(top.get("color"), "#2e8bc0"); A = _c(top.get("accent"), "#f0f0f0")
        kind = top.get("type", "tshirt"); cv = self.cv
        self.box("body", T)
        arms = ("right_arm", "left_arm")
        sleeve_rows = {"tshirt": 4, "tank": 0, "dress": 3}.get(kind, 11)
        for arm in arms:
            self.box(arm, S, grad=0.06)
            if sleeve_rows:
                self.limb_rows(arm, 0, sleeve_rows, T); self.shade_face(arm, "top", T)
                if sleeve_rows == 4:
                    self.limb_rows(arm, 3, 4, shade(T, 0.82), grad=0)
        # neckline / collar
        if kind in ("tshirt", "tank", "longsleeve", "sweater", "dress"):
            for x in (3, 4):
                cv.px("body", "front", x, 0, shade(S, 0.92))
            for x in (2, 5):
                cv.px("body", "front", x, 0, shade(T, 0.75))
        if kind == "tank":
            for x in (0, 1, 6, 7):
                cv.px("body", "front", x, 0, shade(S, 0.95)); cv.px("body", "back", x, 0, shade(S, 0.9))
        if kind == "hoodie":
            for x in range(1, 7):
                cv.px("body", "front", x, 0, shade(T, 0.72))
            for y in range(1, 4):
                cv.px("body", "front", 2, y, (226, 226, 226, 255) if y < 3 else (190, 190, 190, 255)); cv.px("body", "front", 5, y, (226, 226, 226, 255) if y < 3 else (190, 190, 190, 255))
            for y in range(7, 10):
                for x in range(1, 7):
                    cv.px("body", "front", x, y, shade(T, 0.86 if y > 7 else 0.78))
            for x in range(8):
                cv.px("jacket", "back", x, 0, shade(T, 0.8)); cv.px("jacket", "back", x, 1, shade(T, 0.9))
            for f in LIMB_FACES:
                for arm in arms:
                    cv.px(arm, f, 0, 10, shade(T, 0.75)) if f in ("front", "back") else None
        if kind in ("jacket", "suit"):
            under = A if kind == "jacket" else (240, 240, 240, 255)
            for y in range(0, 12 if kind == "jacket" else 5):
                for x in ((3, 4) if kind == "jacket" else range(3 - min(y, 2) // 2, 5 + min(y, 2) // 2)):
                    cv.px("body", "front", x, y, shade(under, 1 - 0.01 * y))
            if kind == "suit":
                tie = _c(top.get("tie"), "#b02828")
                for y in range(1, 7):
                    cv.px("body", "front", 3, y, tie); cv.px("body", "front", 4, y, shade(tie, 0.85))
            for y in range(0, 12):  # lapels / open edges on the overlay
                cv.px("jacket", "front", 2, y, shade(T, 0.85)); cv.px("jacket", "front", 5, y, shade(T, 0.85))
            for x in range(8):
                cv.px("jacket", "front", x, 11, shade(T, 0.8)) if x not in (3, 4) else None
        if kind == "shirt":
            for x in (2, 3, 4, 5):
                cv.px("body", "front", x, 0, shade(A, 0.95))
            for y in range(2, 11, 3):
                cv.px("body", "front", 4, y, shade(T, 0.7))
        if kind == "sweater":
            for x in range(8):
                cv.px("body", "front", x, 11, shade(T, 0.8))
            for arm in arms:
                self.limb_rows(arm, 10, 11, shade(T, 0.8), grad=0)
        pat = top.get("pattern", "none"); PC = _c(top.get("pattern_color"), A[:3])
        if pat == "stripes":
            for f in ("front", "back", "left", "right"):
                for y in range(2, 11, 3):
                    self.shade_face("body", f, PC, y=y, h=1, grad=0)
        elif pat == "plaid":
            for f in ("front", "back"):
                for y in range(12):
                    for x in range(8):
                        if x % 3 == 0 or y % 3 == 0:
                            cv.px("body", f, x, y, _mix(T, PC, 0.45 if (x % 3 == 0) != (y % 3 == 0) else 0.7))
        elif pat == "logo":
            for (x, y) in ((3, 3), (4, 3), (2, 4), (3, 4), (4, 4), (5, 4), (3, 5), (4, 5)):
                cv.px("body", "front", x, y, PC)
        # hands
        for arm in arms:
            self.limb_rows(arm, 11, 12, shade(S, 0.95), grad=0); self.shade_face(arm, "bottom", S)

    # ------------------------------------------------------------------------------------------------- legs ----
    def legs(self):
        p = self.p; S = _c(p.get("skin"), "#c99a73"); bt = p.get("bottom") or {}; P = _c(bt.get("color"), "#3b4f7a"); kind = bt.get("type", "jeans")
        sh = p.get("shoes") or {}; Sh = _c(sh.get("color"), "#3a3a3a"); skind = sh.get("type", "shoes"); cv = self.cv
        top = p.get("top") or {}
        legs = ("right_leg", "left_leg")
        for leg in legs:
            self.box(leg, P)
            if kind == "jeans":
                for f in ("front",):
                    for y in (5, 6):
                        for x in (1, 2):
                            cv.px(leg, f, x, y, shade(P, 1.12))
                self.limb_rows(leg, 0, 1, shade(P, 0.85), grad=0)
            if kind == "shorts":
                self.limb_rows(leg, 6, 10, S, grad=0.04)
            if kind == "skirt" or top.get("type") == "dress":
                SC = _c(top.get("color"), P[:3]) if top.get("type") == "dress" else P
                self.limb_rows(leg, 0, 5, SC); self.limb_rows(leg, 5, 10, S, grad=0.04)
                pants = "right_pants" if leg == "right_leg" else "left_pants"
                for f in LIMB_FACES:
                    self.shade_face(pants, f, shade(SC, 0.95), h=5)
            # shoes
            if skind == "boots":
                self.limb_rows(leg, 8, 12, Sh); self.limb_rows(leg, 8, 9, shade(Sh, 1.15), grad=0)
            elif skind == "sneakers":
                self.limb_rows(leg, 10, 11, Sh, grad=0); self.limb_rows(leg, 11, 12, (238, 238, 238, 255), grad=0)
            else:
                self.limb_rows(leg, 10, 12, Sh, grad=0.1)
            self.shade_face(leg, "bottom", shade(Sh, 0.8))
        if top.get("type", "tshirt") in ("tshirt", "tank", "shirt", "suit") and kind != "skirt":  # belt line (hidden under hoodies, sweaters, coats)
            for f in ("front", "back", "left", "right"):
                self.shade_face("body", f, shade(_c(bt.get("belt"), "#3a2a1a"), 1.0), y=11, h=1, grad=0, noise=0)
            cv.px("body", "front", 3, 11, (190, 190, 196, 255)); cv.px("body", "front", 4, 11, (150, 150, 158, 255))

    def extras(self):
        acc = self.p.get("accessory", "none"); A = _c(self.p.get("accessory_color"), "#c03030"); cv = self.cv
        if acc == "scarf":
            for f in ("front", "back", "left", "right"):
                self.shade_face("jacket", f, A, h=2, grad=0)
            for y in range(2, 6):
                cv.px("jacket", "front", 5, y, shade(A, 0.9))
        elif acc == "necklace":
            for (x, y) in ((2, 1), (3, 2), (4, 2), (5, 1)):
                cv.px("body", "front", x, y, (230, 200, 90, 255))
        elif acc == "backpack":
            for y in range(1, 11):
                for x in range(1, 7):
                    cv.px("jacket", "back", x, y, shade(A, 0.9 if 2 < y < 9 else 0.75))
            for y in range(0, 6):
                cv.px("jacket", "front", 1, y, shade(A, 0.7)); cv.px("jacket", "front", 6, y, shade(A, 0.7))

    def paint(self):
        self.head(); self.body(); self.legs(); self.extras()
        return self.cv.img


def paint(persona, seed=11):
    return Painter(persona, seed).paint()


PRESETS = {
    # an ORIGINAL painting in the spirit of the fan legend: cyan shirt, blue trousers, brown hair, empty white eyes
    "herobrine": {"skin": "#b0805e", "hair": {"color": "#2b1d14", "style": "short"}, "eyes": {"color": "#ffffff"}, "eye_glow": True,
                  "brows": "#2b1d14", "facial_hair": "stubble", "facial_hair_color": "#5a3c28",
                  "top": {"type": "tshirt", "color": "#00a8a8"}, "bottom": {"type": "pants", "color": "#463aa5"}, "shoes": {"color": "#555555"}},
    "knight": {"skin": "#d2a07c", "hair": {"color": "#6a4a2a", "style": "short"}, "top": {"type": "longsleeve", "color": "#9aa0a8", "pattern": "logo", "pattern_color": "#c03030"},
               "bottom": {"type": "pants", "color": "#6a6e76"}, "shoes": {"type": "boots", "color": "#4a3a2a"}, "accessory": "none"},
    "ninja": {"skin": "#d8a882", "hair": {"color": "#141414", "style": "short"}, "top": {"type": "longsleeve", "color": "#1e1e24"}, "bottom": {"type": "pants", "color": "#1a1a20"},
              "shoes": {"type": "boots", "color": "#111111"}, "accessory": "hood", "accessory_color": "#1e1e24"},
    "wizard": {"skin": "#e0b090", "hair": {"color": "#d8d8d8", "style": "long"}, "facial_hair": "beard", "facial_hair_color": "#e8e8e8",
               "top": {"type": "dress", "color": "#3a3a9a"}, "bottom": {"type": "skirt", "color": "#3a3a9a"}, "shoes": {"color": "#3a2a1a"}, "accessory": "hood", "accessory_color": "#2e2e80"},
    "miner": {"skin": "#c08a64", "hair": {"color": "#4a3018", "style": "short"}, "facial_hair": "beard", "top": {"type": "shirt", "color": "#7a5a3a", "accent": "#d0c0a0"},
              "bottom": {"type": "jeans", "color": "#3b4f7a"}, "shoes": {"type": "boots", "color": "#3a2a1a"}, "accessory": "cap", "accessory_color": "#e0b020"},
}


def herobrine_from_steve(steve_path):
    """The classic look, derived from the cached game texture at render time (stays local: never commit the result)."""
    im = Image.open(steve_path).convert("RGBA").copy()
    for x in (9, 10, 13, 14):          # face eye pixels (row 4 of the face at 8,8)
        im.putpixel((x, 12), (255, 255, 255, 255))
    return im


def sample(photo, regions, out=None):
    """Median colour of each named region of a photo (robust to highlights/shadows: the middle 50 % of luminance)."""
    import numpy as np
    im = np.asarray(Image.open(photo).convert("RGB"), dtype=float); res = {}
    for name, (x0, y0, x1, y1) in regions.items():
        r = im[y0:y1, x0:x1].reshape(-1, 3)
        lum = r @ np.array([0.299, 0.587, 0.114]); lo, hi = np.percentile(lum, 25), np.percentile(lum, 75)
        sel = r[(lum >= lo) & (lum <= hi)] if ((lum >= lo) & (lum <= hi)).sum() > 3 else r
        c = np.median(sel, axis=0).astype(int); res[name] = "#%02x%02x%02x" % tuple(int(v) for v in c)
    if out:
        Path(out).write_text(json.dumps(res, indent=2))
    return res


def apply_colors(persona, colors):
    """Put sampled colours into a persona: keys skin, hair, eyes, top, bottom, shoes, accent, accessory, facial_hair."""
    p = json.loads(json.dumps(persona))
    for k, v in colors.items():
        if k == "skin":
            p["skin"] = v
        elif k in ("hair", "eyes", "top", "bottom", "shoes"):
            p.setdefault(k, {}); p[k] = p[k] if isinstance(p[k], dict) else {}; p[k]["color"] = v
        elif k == "accent":
            p.setdefault("top", {})["accent"] = v
        elif k == "accessory":
            p["accessory_color"] = v
        elif k == "facial_hair":
            p["facial_hair_color"] = v
    return p


EXAMPLE = {"model": "classic", "skin": "#c68e6a", "hair": {"color": "#2a1a10", "style": "short"}, "eyes": {"color": "#4a3020"},
           "facial_hair": "stubble", "glasses": None, "mouth": "neutral",
           "top": {"type": "hoodie", "color": "#2b2f3a", "accent": "#e0e0e0"}, "bottom": {"type": "jeans", "color": "#3b4f7a"},
           "shoes": {"type": "sneakers", "color": "#f0f0f0"}, "accessory": "none"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("paint"); s.add_argument("persona"); s.add_argument("out"); s.add_argument("--colors"); s.add_argument("--preview"); s.add_argument("--seed", type=int, default=11)
    s = sub.add_parser("sample"); s.add_argument("photo"); s.add_argument("--region", action="append", default=[], help="name=x0,y0,x1,y1"); s.add_argument("--out")
    s = sub.add_parser("preset"); s.add_argument("name", choices=sorted(PRESETS)); s.add_argument("out"); s.add_argument("--from-steve")
    sub.add_parser("example")
    a = ap.parse_args(argv)
    if a.cmd == "example":
        print(json.dumps(EXAMPLE, indent=2)); return 0
    if a.cmd == "sample":
        regs = {r.split("=")[0]: tuple(int(v) for v in r.split("=")[1].split(",")) for r in a.region}
        print(json.dumps(sample(a.photo, regs, a.out), indent=2)); return 0
    if a.cmd == "preset":
        img = herobrine_from_steve(a.from_steve) if (a.name == "herobrine" and a.from_steve) else paint(PRESETS[a.name])
        img.save(a.out); out = a.out
    else:
        persona = json.loads(Path(a.persona).read_text())
        if a.colors:
            persona = apply_colors(persona, json.loads(Path(a.colors).read_text()))
        paint(persona, a.seed).save(a.out); out = a.out
        if a.preview:
            import subprocess
            subprocess.run([sys.executable, str(Path(__file__).parent.parent / "tools" / "turntable.py"), out, "--out", a.preview], check=False)
    r = validate(out)
    print(f"wrote {out} ({r['model']}){'  ERRORS: ' + '; '.join(r['errors']) if r['errors'] else ''}")
    return 1 if r["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
