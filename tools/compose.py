#!/usr/bin/env python3
"""BlockReel director: compile a short beat plan (plan.json) into a complete, polished story.json.

The assistant turns the user's prompt ("make me in Minecraft fighting Herobrine") into ~20 lines of beats; this tool does the
film-making arithmetic: blocking on an arena, fight choreography with anticipation and reactions, coverage that respects the
180-degree rule, cuts on action, slow motion and flashes on the big hits, game sound effects on every impact, footsteps,
an original score that follows the energy of the beats, subtitles in chat format, skins (photo personas, presets) and a shot list.

  python tools/compose.py plan.json --out films/herobrine            # writes story.json, music.wav, skins/, shotlist.md
  python tools/compose.py plan.json --out films/x --no-music          # skip the score
  python tools/compose.py --example > plan.json                      # a complete example plan (me vs Herobrine)

Then: python tools/render.py films/x/story.json --preset preview --out preview.mp4, look, adjust the plan or story, render final.
See docs/DIRECTOR-PLAN.md for every beat and option.
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SND = ROOT / "work" / "vanilla" / "sounds"
sys.path.insert(0, str(ROOT / "core"))

STRIKE = {"slash": (0.6, 0.47), "overhead": (0.7, 0.48), "thrust": (0.55, 0.5), "swing": (0.7, 0.42), "punch": (0.5, 0.4), "lunge": (0.8, 0.5)}
SECTION = {"establish": "calm", "walk": "calm", "line": "calm", "look": "calm", "act": "calm", "wait": "calm", "title": None,
           "reveal": "build", "faceoff": "build", "teleport": "build", "charge": "battle", "duel": "battle", "power": "battle",
           "knockdown": "battle", "getup": "build", "finisher": "battle", "explode": "battle", "silence": "silence", "ending": "dawn", "victory": "dawn"}


def v_add(a, b): return [a[0] + b[0], a[1] + b[1]]
def v_sub(a, b): return [a[0] - b[0], a[1] - b[1]]
def v_mul(a, k): return [a[0] * k, a[1] * k]
def v_len(a): return math.hypot(a[0], a[1])
def v_norm(a):
    l = v_len(a) or 1.0
    return [a[0] / l, a[1] / l]
def r2(x): return round(x, 3)


class Film:
    def __init__(self, plan, out):
        self.p = plan; self.out = Path(out); self.t = 0.0
        self.story = {"title": plan.get("title", "BlockReel film"), "fps": plan.get("fps", 30), "size": plan.get("size", [1280, 720]),
                      "seed": plan.get("seed", 7), "style": plan.get("style", "classic-2012"), "actors": {}, "world": [], "timeline": [],
                      "faces": [], "camera": [], "fx": [], "changes": [], "subtitles": [], "titles": [], "transitions": [], "timeRemap": [],
                      "lightning": [], "lighting": list(plan.get("lighting", []))}
        for k in ("styleOverride", "post", "weather", "sky", "textures", "blocks"):
            if k in plan:
                self.story[k] = plan[k]
        self.sfx = []; self.sections = []; self.shots = []; self.pos = {}; self.hidden = set(); self.hurt = {}
        self.side = 1 if plan.get("cameraSide", "right") == "right" else -1
        self.arena = None; self.cast_names = {}; self.k = 0

    # ------------------------------------------------------------------------------------------------ setup ----
    def world(self):
        w = self.p.get("world", {})
        if isinstance(w, list):
            self.story["world"] = w; a = self.p.get("arena", {"center": [0, 0], "radius": 8}); self.arena = a; return
        a = w.get("arena", {"center": [0, 0], "radius": 8, "y": 4}); a.setdefault("center", [0, 0]); a.setdefault("radius", 8); a.setdefault("y", 4)
        self.arena = a
        terrain = {"radius": w.get("radius", 40), "center": a["center"], "base": w.get("base", a["y"]), "amp": w.get("amp", 3), "scale": w.get("scale", 16),
                   "biome": w.get("biome", "plains"), "flat": {"center": a["center"], "radius": a["radius"], "y": a["y"]},
                   "trees": w.get("trees", 0.02), "seed": w.get("seed", self.story["seed"])}
        for k in ("water", "plants", "flowers", "treeKinds", "clear", "top", "soil", "stone"):
            if k in w:
                terrain[k] = w[k]
        self.story["world"] = [{"terrain": terrain}] + list(w.get("structures", [])) + list(w.get("extra", []))
        if w.get("arenaFloor"):  # paint the arena floor with a block (e.g. stone_bricks for a duel ring)
            r = a["radius"]; cx, cz = a["center"]
            self.story["world"].append({"cylinder": [w["arenaFloor"], [cx, a["y"], cz], r - 1, 1]})

    def cast(self):
        (self.out / "skins").mkdir(parents=True, exist_ok=True)
        marks = self.p.get("marks", {})
        names = list(self.p.get("cast", {}).keys())
        cx, cz = self.arena["center"]
        for i, (name, c) in enumerate(self.p.get("cast", {}).items()):
            skin = self.skin_for(name, c)
            default_mark = [cx, cz + 3.5] if i == 0 else [cx, cz - 3.5] if i == 1 else [cx + (i - 1) * 2.5, cz + 6]
            m = marks.get(name, default_mark); self.pos[name] = [float(m[0]), float(m[1])]
            a = {"skin": skin, "pos": [m[0], None, m[1]], "face": c.get("face", 180 if i == 0 else 0)}
            for k in ("holding", "offhand", "model", "scale", "dust"):
                if k in c:
                    a[k] = c[k]
            if c.get("name") and c.get("nametag", self.p.get("nametags", False)):  # cinematic default: no floating name tags
                a["nametag"] = c["name"]
            self.cast_names[name] = c.get("name", name)
            self.story["actors"][name] = a
            if c.get("eyes"):
                self.story["faces"].append({"t": 0, "actor": name, "eyes": c["eyes"]})
            if c.get("hidden"):
                self.hide(name, 0)

    def skin_for(self, name, c):
        from persona import PRESETS, herobrine_from_steve, paint
        dst = self.out / "skins" / f"{name}.png"
        if c.get("skin"):
            src = Path(c["skin"]);
            if not src.is_absolute():
                src = (Path(self.p.get("_dir", ".")) / src)
            if src.resolve() != dst.resolve():
                shutil.copyfile(src, dst)
        elif c.get("persona"):
            paint(c["persona"]).save(dst)
        elif c.get("preset"):
            steve = ROOT / "work" / "vanilla" / "entity" / "steve.png"
            if c["preset"] == "herobrine" and steve.exists() and c.get("classic", True):
                herobrine_from_steve(steve).save(dst)
            elif c["preset"] in ("steve", "alex") and (ROOT / "work" / "vanilla" / "entity" / f"{c['preset']}.png").exists():
                shutil.copyfile(ROOT / "work" / "vanilla" / "entity" / f"{c['preset']}.png", dst)
            else:
                paint(PRESETS.get(c["preset"], PRESETS["knight"])).save(dst)
        else:
            return "/core/builtin/skins/hero.png"
        return f"skins/{name}.png"

    # ------------------------------------------------------------------------------------------ primitives ----
    def seg(self, **kw):
        kw["t"] = r2(kw["t"]); self.story["timeline"].append(kw); return kw

    def face(self, t, who, **kw):
        self.story["faces"].append({"t": r2(t), "actor": who, **kw})

    def sound(self, key, t, vol=1.0):
        for k in ([key] if isinstance(key, str) else key):
            f = SND / f"{k}.wav"
            if f.exists():
                self.sfx.append({"file": str(f), "t": r2(max(0, t)), "volume": vol}); return True
        return False

    def fx(self, kind, t, pos, **kw):
        self.story["fx"].append({"t": r2(t), "kind": kind, "pos": pos, **kw})

    def hide(self, who, t):
        self.seg(t=t, actor=who, hide=True); self.hidden.add(who)

    def show(self, who, t):
        self.seg(t=t, actor=who, show=True); self.hidden.discard(who)

    def p3(self, xz, lift=0.0):
        return [r2(xz[0]), None, r2(xz[1])] if lift == 0 else [r2(xz[0]), None, r2(xz[1])]

    def clamp(self, xz):
        c = self.arena["center"]; r = self.arena["radius"] - 1.2; d = v_sub(xz, c); l = v_len(d)
        return v_add(c, v_mul(d, r / l)) if l > r else xz

    def axis(self, a, b):
        d = v_norm(v_sub(self.pos[b], self.pos[a])); n = [-d[1] * self.side, d[0] * self.side]
        return d, n

    def section(self, kind, t0, t1):
        if kind:
            self.sections.append([kind, t0, t1])

    # camera: offsets relative to an actor (world-space), so the frame follows the actor wherever the engine puts it
    def cam(self, t, dur, kind, a, b=None, **kw):
        P = self.pos; shot = {"t": r2(t), "dur": r2(dur)}
        gap = 99.0
        if b and b in P and a in P and P[a] != P[b]:
            d, n = self.axis(a, b); gap = v_len(v_sub(P[b], P[a]))
        else:
            hd = kw.pop("heading", None); d = hd or [0, -1]; n = [-d[1] * self.side, d[0] * self.side]
        fwd = lambda want: min(want, max(0.6, gap * 0.4))  # a close-up never puts the lens inside the other actor
        def off(base_actor, vec_xz, y):
            return {"actor": base_actor, "offset": [r2(vec_xz[0]), y, r2(vec_xz[1])]}
        if kind == "wide":  # two-shot from the side of the line of action
            mid = v_mul(v_sub(P[b], P[a]), 0.5) if b else [0, 0]; dist = kw.pop("dist", max(5.5, v_len(v_sub(P[b], P[a])) * 1.25 if b else 6))
            shot.update(pos=off(a, v_add(mid, v_mul(n, dist)), 2.0), look=off(a, mid, 1.1), fov=kw.pop("fov", 50))
        elif kind == "side":
            mid = v_mul(v_sub(P[b], P[a]), 0.5) if b else [0, 0]
            shot.update(pos=off(a, v_add(mid, v_mul(n, 4.2)), 1.3), look=off(a, mid, 1.2), fov=kw.pop("fov", 46))
        elif kind == "ots":  # over a's shoulder onto b
            shot.update(pos=off(a, v_add(v_mul(d, -2.3), v_mul(n, 1.15)), 1.95), look=off(b, [0, 0], 1.3), fov=kw.pop("fov", 46))
        elif kind == "close":  # a's face, from the camera side of the line, slightly in front
            shot.update(pos=off(a, v_add(v_mul(d, fwd(1.55)), v_mul(n, 1.15 if gap < 3 else 0.9)), 1.62), look=off(a, [0, 0], 1.55), fov=kw.pop("fov", 40 if gap >= 3 else 46))
        elif kind == "xclose":  # eyes
            shot.update(pos=off(a, v_add(v_mul(d, fwd(1.8)), v_mul(n, 0.45 if gap >= 3 else 1.1)), 1.64), look=off(a, [0, 0], 1.62), fov=kw.pop("fov", 34 if gap >= 3 else 44))
        elif kind == "low":  # hero angle
            shot.update(pos=off(a, v_add(v_mul(d, 2.3), v_mul(n, 1.3)), 0.35), look=off(a, [0, 0], 1.45), fov=kw.pop("fov", 56))
        elif kind == "high":
            shot.update(pos=off(a, v_add(v_mul(d, 3.5), v_mul(n, 2.0)), 5.5), look=off(a, [0, 0], 0.8), fov=kw.pop("fov", 50))
        elif kind == "track":  # follow a walking actor from the side, slightly ahead
            dd = v_norm(kw.pop("dir", d)); nn = [-dd[1] * self.side, dd[0] * self.side]
            shot.update(pos=off(a, v_add(v_mul(nn, 4.0), v_mul(dd, 1.6)), 1.7), look=off(a, v_mul(dd, 0.8), 1.2), fov=kw.pop("fov", 50))
        elif kind == "front":  # in front of the actor (along its heading dir), looking back at it
            dd = v_norm(kw.pop("dir", d)); shot.update(pos=off(a, v_add(v_mul(dd, 3.4), v_mul([-dd[1], dd[0]], 0.8 * self.side)), 1.6), look=off(a, [0, 0], 1.35), fov=kw.pop("fov", 46))
        elif kind == "pov":
            shot.update(first=a, fov=kw.pop("fov", 75))
        elif kind == "orbit":
            c = self.arena["center"]; shot.update(orbit={"center": kw.pop("center", [c[0], None, c[1]]), "radius": kw.pop("radius", 14), "height": kw.pop("height", 5),
                                                         "from": kw.pop("from_", -40), "to": kw.pop("to_", 10)}, fov=kw.pop("fov", 55))
        elif kind == "crane":  # wide establishing move toward the arena
            c = self.arena["center"]; dir_ = kw.pop("dir", [0.55, 1]); dn = v_norm(dir_)
            shot.update(pos=[r2(c[0] + dn[0] * 22), None, r2(c[1] + dn[1] * 22)], to=[r2(c[0] + dn[0] * 12), None, r2(c[1] + dn[1] * 12)],
                        look=[c[0], None, c[1]], fov=kw.pop("fov", 55))
            shot["pos"][1] = None; shot["_lift"] = [7, 3.5]
        shot.update(kw)
        if "_lift" in shot:  # absolute positions: engine puts null y on the ground + eye height; lift it further with an offset form
            lift = shot.pop("_lift"); c = self.arena["center"]
            shot["pos"] = [shot["pos"][0], self.arena["y"] + 1 + lift[0], shot["pos"][2]]
            shot["to"] = [shot["to"][0], self.arena["y"] + 1 + lift[1], shot["to"][2]]
            shot["look"] = [c[0], self.arena["y"] + 2, c[1]]
        self.story["camera"].append(shot); self.shots.append((r2(t), r2(dur), kind, a, b)); return shot

    # ---------------------------------------------------------------------------------------------- beats ----
    def b_establish(self, b):
        dur = b.get("dur", 4.0); t = self.t
        if b.get("shot", "crane") == "orbit":
            self.cam(t, dur, "orbit", None, ease="smooth")
        else:
            self.cam(t, dur, "crane", None, dir=b.get("dir", [0.55, 1]), ease="smooth")
        if b.get("text"):
            self.story["titles"].append({"t": r2(t + 0.6), "dur": min(2.6, dur - 0.8), "text": b["text"], "size": b.get("size", 56)})
        self.sound(["ambient/cave/cave13"], t + 0.3, 0.35) if b.get("eerie") else None
        return dur

    def walk_to(self, who, to, t, run=False, speed=None):
        to = self.clamp(to); d = v_len(v_sub(to, self.pos[who])); sp = speed or (4.3 if run else 2.6); dur = max(0.4, d / sp)
        self.seg(t=t, actor=who, do="run" if run else "walk", to=self.p3(to), dur=r2(dur), speed=1.0)
        step = 0.3 if run else 0.48; k = 0; tt = t + 0.15
        while tt < t + dur:
            self.sound([f"step/grass{1 + (k % 4)}", f"step/grass{1 + (k % 2)}", "step/stone1"], tt, 0.22 if run else 0.16); tt += step; k += 1
        self.pos[who] = to; return dur

    def b_walk(self, b):
        who = b["who"]; t = self.t; start = list(self.pos[who])
        to = b["to"] if "to" in b else v_add(self.pos[who], v_mul(v_norm(v_sub(self.pos[b["toward"]], self.pos[who])), b.get("dist", 3)))
        if "toward" in b and "to" not in b:
            to = v_add(self.pos[b["toward"]], v_mul(v_norm(v_sub(self.pos[who], self.pos[b["toward"]])), b.get("stop", 3.0)))
        dur = self.walk_to(who, to, t, b.get("run", False))
        dirv = v_norm(v_sub(to, start)) if v_len(v_sub(to, start)) > 0.01 else [0, -1]
        self.pos_tmp = start
        if dur > 2.4 and b.get("shot") != "track":
            self.cam(t, dur * 0.55, "track", who, dir=dirv, handheld=0.3)
            self.cam(t + dur * 0.55, dur * 0.45, "front", who, dir=dirv, handheld=0.3)
        else:
            self.cam(t, dur, b.get("shot", "track"), who, dir=dirv, handheld=0.3)
        return dur + b.get("pause", 0.2)

    def b_line(self, b):
        who = b["who"]; to = b.get("to") or next((n for n in self.pos if n != who and n not in self.hidden), None)
        text = b["text"]; dur = b.get("dur", max(1.8, min(4.5, 0.75 + len(text) * 0.06))); t = self.t
        if to:
            self.seg(t=t, actor=who, face=to, lookAt=to, turn=0.25)
        self.seg(t=t + 0.05, actor=who, do=b.get("do", "talk"), dur=r2(dur - 0.1))
        emo = b.get("emotion")
        if emo:
            m = {"angry": {"eyes": "angry"}, "scared": {"eyes": "wide"}, "shout": {"eyes": "angry"}, "smile": {"mouth": "smile"}, "sad": {"eyes": "half"}}.get(emo, {})
            if m:
                self.face(t, who, dur=dur, **m)
        self.story["subtitles"].append({"t": r2(t + 0.1), "dur": r2(dur - 0.15), "who": self.cast_names.get(who, who), "text": text})
        shot = b.get("shot") or ("close" if self.k % 2 == 0 else "ots")
        if shot == "ots" and to:
            self.cam(t, dur, "ots", to, who, handheld=0.25)  # over the listener's shoulder onto the speaker
        else:
            self.cam(t, dur, shot, who, to, handheld=0.2, **({"fovTo": 34} if emo in ("angry", "shout") else {}))
        self.k += 1
        return dur

    def b_look(self, b):
        who = b["who"]; at = b["at"]; dur = b.get("dur", 1.5); t = self.t
        self.seg(t=t, actor=who, face=at, lookAt=at, turn=b.get("turn", 0.5))
        if b.get("emotion") == "scared":
            self.face(t + 0.2, who, eyes="wide", dur=dur)
        self.cam(t, dur, b.get("shot", "close"), who, at if at in self.pos else None, handheld=0.2)
        return dur

    def b_reveal(self, b):
        who = b["who"]; t = self.t; dur = b.get("dur", 3.2); witness = b.get("witness") or next((n for n in self.pos if n != who), None)
        if "at" in b:
            self.pos[who] = list(b["at"])
            if not any(x.get("actor") == who and ("to" in x or "do" in x) for x in self.story["timeline"]):
                self.story["actors"][who]["pos"] = [b["at"][0], None, b["at"][1]]
            else:
                self.seg(t=t, actor=who, do="idle", to=self.p3(self.pos[who]), dur=0.02)
        if who not in self.hidden:
            self.hide(who, 0)
        strike = t + 0.9
        self.cam(t, 1.6, "ots" if witness else "wide", witness or who, who, handheld=0.4)
        if b.get("fx", "lightning") == "lightning":
            self.story["lightning"].append({"t": r2(strike), "pos": [r2(self.pos[who][0]), r2(self.pos[who][1])], "seed": int(strike * 10)})
            self.sound(["ambient/weather/thunder1", "ambient/weather/thunder2"], strike, 1.0)
            self.sound(["item/trident/thunder1"], strike, 0.6)
            self.story["transitions"].append({"t": r2(strike), "type": "flash", "dur": 0.45, "color": "#e8eeff", "peak": 0.8})
        else:
            self.sound(["mob/endermen/portal"], strike, 0.9)
        back = v_add(self.pos[who], v_mul(v_norm(v_sub(self.pos[who], self.pos[witness])) if witness else [0, -1], 0.8))
        self.fx("smoke", strike + 0.05, self.p3(back), dur=0.5, scale=0.7); self.fx("poof", strike, {"actor": who, "offset": [0, 1, 0]}, scale=1.3)
        self.show(who, strike + 0.02)
        if witness:
            self.seg(t=strike, actor=who, face=witness, lookAt=witness, turn=0)
            self.seg(t=strike + 0.1, actor=witness, do="hit", dur=0.5, face=who, lookAt=who) if b.get("flinch", True) else None
            self.face(strike + 0.1, witness, eyes="wide", dur=2.2)
        self.face(strike, who, eyes="glow") if b.get("glow", True) else None
        self.cam(t + 1.6, dur - 1.6, "xclose", who, witness, fovTo=27, ease="smooth")
        self.sound(["mob/endermen/stare", "mob/ghast/moan1"], t + 1.7, 0.7)
        return dur

    def b_teleport(self, b):
        who = b["who"]; t = self.t; dur = b.get("dur", 1.6); old = list(self.pos[who])
        if isinstance(b.get("to"), str) and b["to"].startswith("behind:"):
            tgt = b["to"].split(":", 1)[1]; d = v_norm(v_sub(self.pos[tgt], old)); new = v_add(self.pos[tgt], v_mul(d, 1.8))
        else:
            new = list(b["to"])
        new = self.clamp(new)
        self.fx("portal", t, self.p3(old), dur=0.5); self.fx("poof", t + 0.3, {"actor": who, "offset": [0, 1, 0]}, scale=1.2)
        self.sound(["mob/endermen/portal", "mob/endermen/portal2"], t + 0.25, 0.9)
        self.hide(who, t + 0.32); self.seg(t=t + 0.35, actor=who, do="idle", to=self.p3(new), dur=0.02); self.pos[who] = new
        self.show(who, t + 0.55); self.fx("portal", t + 0.5, self.p3(new), dur=0.4); self.fx("poof", t + 0.55, self.p3(new), scale=1.0)
        self.sound(["mob/endermen/portal2", "mob/endermen/portal"], t + 0.55, 0.8)
        other = b.get("facing") or next((n for n in self.pos if n != who), None)
        if other:
            self.seg(t=t + 0.56, actor=who, face=other, lookAt=other, turn=0)
        self.cam(t, dur, "wide", other or who, who, handheld=0.5)
        return dur

    def b_faceoff(self, b):
        a, c = b["a"], b["b"]; t = self.t; dur = b.get("dur", 3.0)
        gap = b.get("gap", 3.2); mid = v_mul(v_add(self.pos[a], self.pos[c]), 0.5); d = v_norm(v_sub(self.pos[c], self.pos[a]))
        ta, tc = v_sub(mid, v_mul(d, gap / 2)), v_add(mid, v_mul(d, gap / 2))
        for who, to, other in ((a, ta, c), (c, tc, a)):
            if v_len(v_sub(to, self.pos[who])) > 0.3:
                self.seg(t=t, actor=who, do="walk", to=self.p3(self.clamp(to)), dur=0.8, face=other); self.pos[who] = self.clamp(to)
            self.seg(t=t + 0.8, actor=who, do="ready", dur=r2(dur - 0.8), hold=True, face=other, lookAt=other)
            self.face(t + 0.5, who, eyes="angry") if not b.get("calm") else None
        self.cam(t, dur * 0.4, "wide", a, c, handheld=0.3, fovTo=44)
        self.cam(t + dur * 0.4, dur * 0.3, "close", a, c, handheld=0.3)
        self.cam(t + dur * 0.7, dur * 0.3, "close", c, a, handheld=0.3)
        self.sound(["entity/player/attack/sweep1"], t + 0.8, 0.35)
        return dur

    def exchange(self, tok, a, c, t, i, total):
        parts = tok.split(":"); att = parts[0]; move = parts[1] if len(parts) > 1 else "slash"; res = parts[2] if len(parts) > 2 else "hit"
        dfn = c if att == a else a
        if att not in (a, c):
            raise SystemExit(f"duel token {tok!r}: attacker must be {a} or {c}")
        crit = move == "crit"; sweep = move == "sweep"; mv = "overhead" if crit else "slash" if sweep else move
        dur, frac = STRIKE.get(mv, (0.6, 0.47)); tt = t
        # close the distance first
        dist = v_len(v_sub(self.pos[dfn], self.pos[att]))
        if dist > 2.6:
            d = v_norm(v_sub(self.pos[dfn], self.pos[att])); to = v_add(self.pos[att], v_mul(d, dist - 2.0))
            cd = self.walk_to(att, to, tt, run=True, speed=6.0); self.seg(t=tt, actor=att, do="charge", to=self.p3(self.pos[att]), dur=r2(cd), face=dfn) if False else None
            self.story["timeline"][-1]["do"] = "charge" if self.story["timeline"][-1].get("actor") == att else self.story["timeline"][-1].get("do")
            tt += cd
        d = v_norm(v_sub(self.pos[dfn], self.pos[att])); n = [-d[1], d[0]]
        gap_now = v_len(v_sub(self.pos[dfn], self.pos[att])); step_to = self.clamp(v_add(self.pos[att], v_mul(d, max(0.0, min(0.55, gap_now - 2.0)))))  # keep fencing distance (~2 blocks)
        seg = {"t": tt, "actor": att, "do": mv, "dur": dur, "to": self.p3(step_to), "ease": "outCubic", "face": dfn}
        if crit:
            seg["arc"] = 0.7
        self.seg(**seg); self.pos[att] = step_to
        self.face(tt, att, eyes="angry", dur=dur + 0.3)
        strike = tt + dur * frac; ex_len = dur + 0.22
        self.sound(["entity/player/attack/weak1", "entity/player/attack/sweep1"], tt + dur * frac * 0.5, 0.45)
        chest = {"actor": dfn, "offset": [0, 1.25, 0]}
        if res in ("hit", "knockback", "fall", "die", "vanish"):
            kb = 2.4 if res == "knockback" else 0.6 if res == "hit" else 1.2
            back = self.clamp(v_add(self.pos[dfn], v_mul(d, kb)))
            clip = "knockback" if res in ("knockback",) else "hit"
            if res in ("fall", "die", "vanish"):
                self.seg(t=strike, actor=dfn, do="fall" if res == "fall" else "die", dur=1.0 if res == "fall" else 1.0, to=self.p3(back), ease="outCubic",
                         hold=True, face=att, **({"vanish": True} if res == "vanish" else {}))
                ex_len += 1.4
            else:
                self.seg(t=strike, actor=dfn, do=clip, dur=0.8 if clip == "knockback" else 0.5, to=self.p3(back), ease="outCubic", face=att,
                         **({"arc": 0.45} if clip == "knockback" else {}))
                self.seg(t=strike + (0.8 if clip == "knockback" else 0.5), actor=dfn, do="ready", dur=3, hold=True, face=att)
                if clip == "knockback":
                    ex_len += 0.45
            self.pos[dfn] = back
            self.hurt[dfn] = min(3, self.hurt.get(dfn, 0) + 1)
            self.face(strike, dfn, eyes="wide", hurt=self.hurt[dfn], dur=0.6); self.face(strike + 0.6, dfn, hurt=self.hurt[dfn])
            self.fx("crit" if not crit else "magiccrit", strike, chest, scale=1.0 if res == "hit" else 1.4)
            if sweep:
                deg = math.degrees(math.atan2(d[0], d[1])); self.fx("sweep", strike - 0.02, {"actor": att, "offset": [0, 1.15, 0]}, face=r2(deg))
                self.sound(["entity/player/attack/sweep1", "entity/player/attack/sweep2"], strike, 0.8)
            self.sound(["entity/player/attack/crit1", "entity/player/attack/crit2"] if crit else ["entity/player/attack/strong1", "entity/player/attack/strong2", "entity/player/attack/strong3"][i % 3:] + ["entity/player/attack/strong1"], strike, 0.95)
            self.sound([f"damage/hit{1 + i % 3}"], strike + 0.02, 0.9)
            if res == "knockback":
                self.sound(["entity/player/attack/knockback1"], strike + 0.03, 0.9)
            if res in ("knockback", "vanish", "die", "fall"):
                self.story["transitions"].append({"t": r2(strike), "type": "flash", "dur": 0.3, "color": "#ffffff", "peak": 0.5})
                self.story["timeRemap"].append({"t": r2(strike - 0.15), "dur": 0.9, "slow": 0.75})
        elif res == "block":
            self.seg(t=tt + 0.05, actor=dfn, do="guard", dur=r2(dur + 0.1), face=att)
            self.seg(t=tt + dur + 0.15, actor=dfn, do="ready", dur=3, hold=True, face=att)
            self.fx("sparks", strike, {"actor": dfn, "offset": [r2(-d[0] * 0.4), 1.45, r2(-d[1] * 0.4)]}, scale=0.7)
            self.sound(["item/shield/block1", "item/shield/block2", "random/anvil_land"], strike, 0.8)
        elif res == "dodge":
            side = self.clamp(v_add(self.pos[dfn], v_mul(n, 1.2 if i % 2 else -1.2)))
            self.seg(t=tt + 0.08, actor=dfn, do="dodge", dur=0.5, to=self.p3(side), ease="outCubic", face=att); self.pos[dfn] = side
            self.seg(t=tt + 0.6, actor=dfn, do="ready", dur=3, hold=True, face=att)
            deg = math.degrees(math.atan2(d[0], d[1])); self.fx("sweep", strike - 0.02, {"actor": att, "offset": [0, 1.15, 0]}, face=r2(deg))
            self.sound(["entity/player/attack/sweep1", "entity/player/attack/sweep2"], strike, 0.7)
        self.seg(t=tt + dur, actor=att, do="ready", dur=3, hold=True, face=dfn)
        # coverage: rotate angles, cut on the action (the cut lands just before the wind-up)
        kinds = ["side", "ots", "low", "close_dfn", "wide"]
        k = "wide" if res in ("knockback", "vanish", "die", "fall") else kinds[i % len(kinds)]
        cut = t - 0.04 if i else t
        L = (tt - t) + ex_len
        if k == "close_dfn":
            self.cam(cut, L, "close", dfn, att, handheld=0.7, shake=0.02)
        elif k == "ots":
            self.cam(cut, L, "ots", att, dfn, handheld=0.7, dutch=(5 if i % 2 else -5))
        elif k == "low":
            self.cam(cut, L, "low", att, dfn, handheld=0.6)
        elif k == "side":
            self.cam(cut, L, "side", att, dfn, handheld=0.8, dutch=(-6 if i % 2 else 6), shake=0.015)
        else:
            self.cam(cut, L, "wide", att, dfn, handheld=0.6, dist=6.5)
        return (tt - t) + ex_len

    def b_duel(self, b):
        a, c = b["a"], b["b"]; t = self.t; total = 0.0; ex = b.get("exchanges", [f"{a}:slash:block", f"{c}:overhead:dodge", f"{a}:thrust:hit"])
        for i, tok in enumerate(ex):
            total += self.exchange(tok, a, c, t + total, i, len(ex))
        return total + b.get("pause", 0.2)

    def b_power(self, b):
        who = b["who"]; kind = b.get("kind", "lightning"); tgt = b.get("target"); t = self.t; dur = b.get("dur", 2.6)
        self.seg(t=t, actor=who, do="summon" if kind in ("lightning", "storm") else "cast", dur=r2(min(1.2, dur)), face=tgt, lookAt=tgt) if tgt else self.seg(t=t, actor=who, do="cast", dur=r2(min(1.2, dur)))
        self.seg(t=t + min(1.2, dur), actor=who, do="cast" if kind != "levitate" else "levitate", dur=r2(max(0.4, dur - 1.2)), hold=True, face=tgt) if tgt else None
        self.fx("aura", t, {"actor": who, "offset": [0, 0.2, 0]}, dur=dur, scale=1.0)
        self.face(t, who, eyes="glow")
        self.sound(["mob/wither/spawn", "mob/endermen/stare"], t + 0.1, 0.5)
        self.cam(t, 1.2, "low", who, tgt, handheld=0.4, fovTo=48)
        hit_t = t + 1.25
        if kind in ("lightning", "storm"):
            n = 3 if kind == "storm" else 1
            for j in range(n):
                tp = self.pos[tgt] if (tgt and j == n - 1 and b.get("hit", True)) else v_add(self.pos[tgt or who], [((j * 37) % 7) - 3, ((j * 53) % 7) - 3])
                tj = hit_t + j * 0.35
                self.story["lightning"].append({"t": r2(tj), "pos": [r2(tp[0]), r2(tp[1])], "seed": 11 + j})
                self.sound(["ambient/weather/thunder2", "ambient/weather/thunder3", "ambient/weather/thunder1"][j % 3:], tj, 1.0)
                self.story["transitions"].append({"t": r2(tj), "type": "flash", "dur": 0.35, "color": "#dfe6ff", "peak": 0.6})
                self.fx("smoke", tj + 0.05, self.p3(tp), dur=0.6, scale=0.6); self.fx("fire", tj, self.p3(tp), dur=0.8, scale=0.6)
            hit_t = hit_t + (n - 1) * 0.35
        elif kind == "shockwave":
            self.fx("explosion", hit_t, {"actor": who, "offset": [0, 0.6, 0]}, scale=1.1); self.sound(["random/explode1", "random/explode2"], hit_t, 0.9)
        elif kind == "fireball" and tgt:
            self.fx("fire", hit_t, {"actor": tgt, "offset": [0, 1.0, 0]}, dur=0.6); self.fx("explosion", hit_t + 0.05, {"actor": tgt, "offset": [0, 0.8, 0]}, scale=0.7)
            self.sound(["mob/ghast/moan1"], t + 0.6, 0.6); self.sound(["random/explode3"], hit_t, 0.9)
        if b.get("crater"):
            p = self.pos[tgt] if tgt else self.pos[who]; y = self.arena["y"]
            self.story["changes"].append({"t": r2(hit_t), "explode": [int(math.floor(p[0])), y, int(math.floor(p[1]))], "radius": b.get("crater", 2)})
        if tgt and b.get("hit", True) and kind != "levitate":
            d = v_norm(v_sub(self.pos[tgt], self.pos[who])); back = self.clamp(v_add(self.pos[tgt], v_mul(d, 2.2)))
            self.seg(t=hit_t, actor=tgt, do="knockback", dur=0.8, to=self.p3(back), arc=0.6, ease="outCubic", face=who); self.pos[tgt] = back
            self.hurt[tgt] = min(3, self.hurt.get(tgt, 0) + 1); self.face(hit_t, tgt, eyes="wide", hurt=self.hurt[tgt], dur=0.8)
            self.seg(t=hit_t + 0.8, actor=tgt, do=b.get("then", "ready"), dur=3, hold=True, face=who)
            self.sound(["damage/hit2"], hit_t + 0.02, 0.9)
        if kind == "levitate":
            p = self.pos[who]; self.seg(t=t + 0.3, actor=who, do="levitate", to=[r2(p[0]), self.arena["y"] + 1 + b.get("height", 2.2), r2(p[1])], dur=r2(dur - 0.3), ease="smooth", hold=True)
            self.lifted = getattr(self, "lifted", set()) | {who}
        self.cam(t + 1.2, dur - 1.2, "wide", tgt or who, who, handheld=0.7, dist=8, shake=0.03)
        return dur

    def b_knockdown(self, b):
        who = b["who"]; t = self.t; dur = b.get("dur", 1.6)
        self.seg(t=t, actor=who, do="fall", dur=0.9, hold=True); self.sound(["damage/fallbig"], t + 0.7, 0.8)
        self.fx("dust", t + 0.75, {"actor": who, "offset": [0, 0.1, 0]}, scale=1.4)
        self.cam(t, dur, b.get("shot", "high"), who, b.get("by"), handheld=0.4)
        return dur

    def b_getup(self, b):
        who = b["who"]; t = self.t; dur = b.get("dur", 1.4); other = b.get("facing")
        self.seg(t=t, actor=who, do="getup", dur=1.0); self.seg(t=t + 1.0, actor=who, do="ready", dur=3, hold=True, **({"face": other} if other else {}))
        self.face(t + 0.4, who, eyes="angry") if b.get("angry", True) else None
        self.cam(t, dur, "side", who, other, handheld=0.4) if other else self.cam(t, dur, "wide", who, None, handheld=0.4)
        return dur

    def b_finisher(self, b):
        a, c = b["a"], b["b"]; t = self.t; mv = b.get("move", "overhead"); res = b.get("result", "vanish")
        self.cam(t, 0.9, "ots", c, a, fov=44, fovTo=36, handheld=0.2); self.face(t, a, eyes="angry")  # over the loser's shoulder onto the winner's face
        self.sound(["entity/player/attack/sweep2", "entity/player/attack/sweep1"], t + 0.5, 0.6)
        self.section("silence", t, t + 0.9)
        dur = self.exchange(f"{a}:{mv}:{res}", a, c, t + 0.9, 99, 1)
        if b.get("slowmo", True):
            pass  # exchange() already adds the speed ramp and flash for decisive results
        return 0.9 + dur + 0.4

    def b_explode(self, b):
        t = self.t; at = b["at"]; y = self.arena["y"]; r = b.get("radius", 3)
        if b.get("tnt", True):
            self.story["changes"].append({"t": r2(t), "place": [at[0], y + 1, at[1]], "block": "tnt"})
            self.story["changes"].append({"t": r2(t + 0.3), "tnt": [at[0], y + 1, at[1]], "fuse": 1.5, "radius": r}); te = t + 1.8
            self.sound(["random/fuse"], t + 0.3, 0.8)
        else:
            self.story["changes"].append({"t": r2(t), "explode": [at[0], y, at[1]], "radius": r}); te = t
        self.sound(["random/explode1", "random/explode2", "random/explode3"], te, 1.0)
        self.story["transitions"].append({"t": r2(te), "type": "flash", "dur": 0.4, "peak": 0.6})
        who = b.get("near") or next(iter(self.pos)); self.cam(t, te - t + 1.6, "wide", who, None, dist=10, shake=0.03, handheld=0.6)
        return te - t + 1.6

    def b_silence(self, b):
        t = self.t; dur = b.get("dur", 2.0); who = b.get("who") or next(iter(self.pos))
        at = b.get("at") or next((n for n in self.pos if n != who), None)  # face the camera the way the actor looks (toward the last opponent's spot)
        self.cam(t, dur, b.get("shot", "close"), who, at, ease="smooth", fovTo=b.get("fovTo", 36))
        return dur

    def b_victory(self, b):
        who = b["who"]; t = self.t; dur = b.get("dur", 2.5)
        self.seg(t=t, actor=who, do=b.get("do", "celebrate"), dur=r2(dur), face=b.get("face", 0))
        self.face(t, who, mouth="smile", eyes="open")
        self.sound(["random/levelup"], t + 0.2, 0.6)
        self.cam(t, dur, "low", who, None, fovTo=50, handheld=0.2)
        return dur

    def b_act(self, b):
        who = b["who"]; t = self.t; dur = b.get("dur", 1.5); seg = {k: v for k, v in b.items() if k not in ("beat", "who", "shot", "with")}
        seg.setdefault("do", "idle"); seg["dur"] = dur
        if "to" in seg:
            self.pos[who] = list(seg["to"][::2]) if len(seg["to"]) == 3 else list(seg["to"]); seg["to"] = self.p3(self.pos[who])
        self.seg(t=t, actor=who, **seg)
        self.cam(t, dur, b.get("shot", "wide"), who, b.get("with"), handheld=0.3)
        return dur

    def b_wait(self, b):
        t = self.t; dur = b.get("dur", 1.5); who = b.get("who") or next(iter(self.pos)); self.cam(t, dur, b.get("shot", "wide"), who, b.get("with"), handheld=0.2)
        return dur

    def b_ending(self, b):
        t = self.t; dur = b.get("dur", 5.0)
        self.cam(t, dur, "orbit", None, radius=b.get("radius", 11), height=b.get("height", 4), from_=10, to_=60, ease="smooth")
        if b.get("text"):
            self.story["titles"].append({"t": r2(t + dur - 2.6), "dur": 2.4, "text": b["text"], "size": b.get("size", 40)})
        self.story["transitions"].append({"t": r2(t + dur - 1.2), "type": "fade", "dur": 1.2, "dir": "out"})
        return dur

    def b_title(self, b):  # a title card over the next beat (no time of its own)
        self.story["titles"].append({"t": r2(self.t + b.get("delay", 0.3)), "dur": b.get("dur", 2.2), "text": b["text"], "size": b.get("size", 56), **({"color": b["color"]} if "color" in b else {})})
        return 0.0

    # ----------------------------------------------------------------------------------------------- build ----
    def build(self, music=True):
        self.world(); self.cast()
        for b in self.p.get("beats", []):
            kind = b["beat"]; fn = getattr(self, f"b_{kind}", None)
            if not fn:
                raise SystemExit(f"unknown beat: {kind}. Known: " + ", ".join(sorted(m[2:] for m in dir(self) if m.startswith("b_"))))
            if b.get("lighting"):
                self.story["lighting"].append({"t": r2(self.t), **b["lighting"]})
            if b.get("title"):
                self.story["titles"].append({"t": r2(self.t + 0.3), "dur": 2.2, "text": b["title"], "size": 56})
            t0 = self.t; d = fn(b); self.t += d
            self.section(b.get("music", SECTION.get(kind)), t0, self.t)
        self.story["duration"] = r2(self.t + 0.1)
        for k in ("lightning", "lighting", "timeRemap", "changes", "transitions", "titles", "fx"):
            if not self.story[k]:
                self.story.pop(k)
        self.story["camera"].sort(key=lambda c: c["t"])
        audio = {"sfx": self.sfx}
        if music and self.p.get("music", True) is not False:
            m = self.p.get("music") if isinstance(self.p.get("music"), dict) else {}
            secs = self.merge_sections()
            wav = self.out / "music.wav"
            spec = ",".join(f"{k}:{a:.2f}:{b:.2f}" for k, a, b in secs)
            r = subprocess.run([sys.executable, str(ROOT / "tools" / "score.py"), "--out", str(wav), "--duration", f"{self.t + 0.1:.2f}", "--sections", spec,
                                "--bpm", str(m.get("bpm", 104)), "--key", m.get("key", "D")], capture_output=True, text=True)
            if r.returncode == 0:
                audio["music"] = {"file": "music.wav", "volume": m.get("volume", 0.55), "fadeIn": 0.5, "fadeOut": 1.5, "duck": {"amount": 0.4}}
            else:
                print("score failed:", r.stderr[-400:], file=sys.stderr)
        if audio.get("sfx") or audio.get("music"):
            self.story["audio"] = audio
        (self.out / "story.json").write_text(json.dumps(self.story, ensure_ascii=False, indent=1))
        self.shotlist()
        return self.story

    def merge_sections(self):
        """Paint the sections on a 50 ms grid (the shortest section covering an instant wins, so a finisher's silence cuts into
        its battle), then run-length encode: a clean list of mood sections for the score."""
        if not self.sections:
            return []
        end = max(s[2] for s in self.sections); out = []; t = 0.0
        while t < end - 1e-6:
            cov = [s for s in self.sections if s[1] <= t + 1e-6 < s[2]]
            k = min(cov, key=lambda s: s[2] - s[1])[0] if cov else "calm"
            if out and out[-1][0] == k:
                out[-1][2] = round(t + 0.05, 2)
            else:
                out.append([k, round(t, 2), round(t + 0.05, 2)])
            t += 0.05
        return [s for s in out if s[2] - s[1] > 0.05]

    def shotlist(self):
        lines = ["# Shot list (generated by tools/compose.py)", "", "| # | t | dur | shot | subject | toward |", "|---|---|---|---|---|---|"]
        for i, (t, d, k, a, b) in enumerate(sorted(self.shots)):
            lines.append(f"| {i + 1} | {t:.2f} | {d:.2f} | {k} | {a or '-'} | {b or '-'} |")
        lines += ["", f"Duration {self.t:.1f} s, {len(self.shots)} shots, {len(self.sfx)} game sound cues, music sections: " +
                  ", ".join(f"{k} {a:.1f}-{b:.1f}" for k, a, b in self.merge_sections())]
        (self.out / "shotlist.md").write_text("\n".join(lines) + "\n")


EXAMPLE = {
    "title": "Eu vs Herobrine", "size": [1280, 720], "fps": 30, "seed": 7, "style": "nightfall",
    "styleOverride": {"letterbox": 2.0, "fog": [16, 70], "ambient": {"color": "#8090ff", "intensity": 0.95}, "sun": {"color": "#b8c8ff", "intensity": 1.1, "dir": [0.4, 1, -0.3]}},
    "post": {"bloom": {"strength": 0.55, "radius": 0.5, "threshold": 0.82}, "grade": {"contrast": 1.08, "saturation": 1.05}, "grain": 0.03},
    "sky": {"clouds": True, "stars": 1},
    "world": {"biome": "plains", "radius": 42, "arena": {"center": [0, 0], "radius": 8, "y": 4}, "trees": 0.025, "water": 2,
              "structures": [{"structure": "shrine", "pos": [0, None, -9]}, {"structure": "ruins", "pos": [11, None, 7], "seed": 2}]},
    "cast": {"me": {"persona": {"skin": "#c68e6a", "hair": {"color": "#2a1a10", "style": "short"}, "facial_hair": "stubble",
                                "top": {"type": "hoodie", "color": "#2b2f3a"}, "bottom": {"type": "jeans", "color": "#3b4f7a"},
                                "shoes": {"type": "sneakers", "color": "#f0f0f0"}},
                    "name": "Vini", "holding": "diamond_sword"},
             "herobrine": {"preset": "herobrine", "name": "Herobrine", "holding": "iron_sword", "eyes": "glow", "hidden": True}},
    "marks": {"me": [0, 9], "herobrine": [0, -3]},
    "beats": [
        {"beat": "establish", "dur": 4, "text": "EU vs HEROBRINE", "eerie": True},
        {"beat": "walk", "who": "me", "to": [0, 3], "pause": 0.3},
        {"beat": "reveal", "who": "herobrine", "at": [0, -2], "witness": "me"},
        {"beat": "line", "who": "herobrine", "text": "Você não deveria ter vindo.", "emotion": "angry"},
        {"beat": "line", "who": "me", "text": "Eu vim te parar.", "emotion": "angry"},
        {"beat": "faceoff", "a": "me", "b": "herobrine", "dur": 2.4},
        {"beat": "duel", "a": "me", "b": "herobrine", "exchanges": ["me:slash:block", "herobrine:overhead:dodge", "me:thrust:hit", "herobrine:slash:knockback"]},
        {"beat": "teleport", "who": "herobrine", "to": "behind:me"},
        {"beat": "power", "who": "herobrine", "kind": "lightning", "target": "me", "dur": 2.6},
        {"beat": "getup", "who": "me", "facing": "herobrine"},
        {"beat": "duel", "a": "me", "b": "herobrine", "exchanges": ["me:sweep:hit", "herobrine:thrust:block", "me:crit:hit"]},
        {"beat": "finisher", "a": "me", "b": "herobrine", "move": "overhead", "result": "vanish"},
        {"beat": "silence", "who": "me", "dur": 2.0},
        {"beat": "ending", "dur": 5, "text": "Herobrine voltará?"},
    ],
    "music": {"key": "D", "bpm": 108},
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", nargs="?"); ap.add_argument("--out"); ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--example", action="store_true", help="print the example plan (me vs Herobrine)")
    a = ap.parse_args(argv)
    if a.example:
        print(json.dumps(EXAMPLE, ensure_ascii=False, indent=1)); return 0
    if not a.plan or not a.out:
        ap.error("plan and --out are required")
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8")); plan["_dir"] = str(Path(a.plan).resolve().parent)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    st = Film(plan, out).build(music=not a.no_music)
    print(f"wrote {out / 'story.json'}  ({st['duration']:.1f} s, {len(st['camera'])} shots, {len(st['timeline'])} actions, "
          f"{len(st.get('audio', {}).get('sfx', []))} sound cues{', music' if st.get('audio', {}).get('music') else ''})  +  shotlist.md")
    if not SND.exists():
        print("note: no game sounds cached (python tools/vanilla.py sounds); the film has music only", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
