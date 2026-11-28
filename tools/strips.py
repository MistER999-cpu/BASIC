#!/usr/bin/env python3
"""Paper-strip reel.

Three photo prints lie on a table, one band of the frame each. They are swapped
on staggered clocks, so one look's head sits over another look's body over a
third look's trousers. Each new print lands like paper dropped by hand: a touch
large and high, then settling with its shadow.

Two ways to drive it:

    # automatic cut from whatever shots are in the folder
    python3 tools/strips.py assets/strips --out out/strips.mp4

    # an authored cut: views, events, paper labels, end card, sound
    python3 tools/strips.py assets/strips --timeline assets/strips/ad.json --out out/ad.mp4

    # stills to check a cut quickly
    python3 tools/strips.py assets/strips --timeline assets/strips/ad.json --stills 0.5,4.6,12.8

Shots are named <colour>_<kind>_<anything>.jpg, kind one of full, profile,
half, detail. A timeline refers to them by file stem.

Timeline JSON (every key but events/views optional):

    size, fps, duration, table, camera, bands, bleed
    views   {name: {shot, u, v, z, anchor: canvas|strip, fit: strip}}
              u, v   the source point (0-1) put at the centre of the frame
                     (anchor canvas: one virtual full frame, sliced across the
                     three strips, so strips line up) or of the strip itself
                     (anchor strip: an independent crop)
              z      zoom over a cover-fit of the frame
    events  [{t, strip | strips, stagger, view, enter: drop|slide-left|slide-right|cut, logo: ink|paper}]
    labels  [{t0, t1, title, sub, x, y, angle, size}]    paper tags, French copy welcome
    card    {logo_width, cta, swatches: [[hex, name]]}  becomes view "__card__"
    sound   {chords, kicks, thumps, risers, chime, levels} synthesised score and paper foley
"""
import argparse
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
LOGO = ROOT / "assets" / "brand" / "basic-logo.png"

KINDS = ("full", "profile", "half", "detail")
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
PAD = 200                      # edge-extended margin around every source
SLACK = 150                    # how far a crop may run into that margin

PAPER = (247, 244, 239)        # BASIC paper
INK = (22, 17, 14)             # BASIC ink
SHADOW = np.array([38, 28, 22], np.float32)
FIG_TOP, FIG_BOTTOM = 0.035, 0.975


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def ease_out(p):
    return 1 - (1 - p) ** 3


def smooth(p):
    return p * p * (3 - 2 * p)


# ---------------------------------------------------------------- shots

def load_shots(folder):
    shots = {}
    for p in sorted(Path(folder).iterdir()):
        if p.suffix.lower() not in EXTS:
            continue
        parts = p.stem.lower().split("_")
        if len(parts) < 2 or parts[1] not in KINDS:
            print(f"skip {p.name}: name it <colour>_<kind>_..., kind one of {KINDS}", file=sys.stderr)
            continue
        shots[p.stem] = {"id": p.stem, "path": str(p), "colour": parts[0], "kind": parts[1]}
    if not shots:
        sys.exit(f"no usable shots in {folder}")
    return shots


class Sources:
    def __init__(self, shots):
        self.shots, self.cache = shots, {}

    def add(self, sid, img):
        self.cache[sid] = self._prep(img)

    def get(self, sid):
        if sid not in self.cache:
            if sid not in self.shots:
                sys.exit(f"timeline names shot {sid!r}, which is not in the folder")
            self.cache[sid] = self._prep(Image.open(self.shots[sid]["path"]))
        return self.cache[sid]

    @staticmethod
    def _prep(img):
        a = np.asarray(img.convert("RGB"))
        h, w = a.shape[:2]
        padded = np.pad(a, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
        return {"img": Image.fromarray(padded), "w": w, "h": h, "thumb": img.convert("L").resize((64, 64))}


def backdrop_mask(rgb_img):
    """Foreground from distance to the border colour, smoothed so a garment close
    to the backdrop colour is not carved open."""
    a = np.asarray(rgb_img, dtype=np.float32)
    border = np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3),
                             a[:, :8].reshape(-1, 3), a[:, -8:].reshape(-1, 3)])
    d = np.sqrt(((a - np.median(border, axis=0)) ** 2).sum(axis=2))
    d = np.asarray(Image.fromarray(np.clip(d, 0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(6)),
                   dtype=np.float32)
    return d > max(18.0, np.percentile(d, 60) * 0.5)


def align_full(src, W, H):
    """View that stands a full-body figure at the same height and centreline as
    every other one, so heads and feet line up across looks."""
    img = src["img"].crop((PAD, PAD, PAD + src["w"], PAD + src["h"]))
    img.thumbnail((400, 400))
    mask = backdrop_mask(img)
    ys, xs = np.nonzero(mask)
    if len(ys) < mask.size * 0.02:
        return {}
    k = src["w"] / img.width
    top, bot, cx = ys.min() * k, ys.max() * k, float(np.median(xs)) * k
    s0 = max(W / src["w"], H / src["h"])
    s = (FIG_BOTTOM - FIG_TOP) * H / max(1.0, bot - top)
    v = (top - (FIG_TOP * H - H / 2) / s) / src["h"]
    return {"u": cx / src["w"], "v": v, "z": s / s0}


# ---------------------------------------------------------------- type, labels, card

def font(name, size):
    path = FONTS / name
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        sys.exit(f"missing font {path}")


def tracked(draw, x_center, baseline, text, fnt, track, fill):
    widths = [fnt.getlength(c) for c in text]
    total = sum(widths) + track * (len(text) - 1)
    x = x_center - total / 2
    for c, w in zip(text, widths):
        draw.text((x, baseline), c, font=fnt, fill=fill, anchor="ls")
        x += w + track
    return total


def tracked_width(text, fnt, track):
    return sum(fnt.getlength(c) for c in text) + track * (len(text) - 1)


def paper_texture(w, h, base=PAPER, seed=3, amount=2.2):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, amount, (h, w)).astype(np.float32)
    fibre = np.asarray(Image.fromarray(np.clip(rng.normal(128, 40, (h // 4 + 1, w // 4 + 1)), 0, 255)
                                       .astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32)
    n += (fibre - 128) * 0.03
    return np.clip(np.array(base, np.float32)[None, None, :] + n[..., None], 0, 255)


def make_label(title, sub, size):
    serif = font("BodoniModa-MediumItalic.ttf", size)
    sans = font("Jost-Regular.ttf", max(20, round(size * 0.36)))
    track = sans.size * 0.34
    lines = title.split("\n")
    asc, desc = serif.getmetrics()
    s_asc, s_desc = sans.getmetrics()
    content_w = max([serif.getlength(l) for l in lines] + [tracked_width(sub, sans, track) if sub else 0])
    padx, pady = round(size * 0.6), round(size * 0.36)
    line_h = round((asc + desc) * 0.92)
    gap, rule_h = round(size * 0.2), max(2, size // 36)
    h = pady * 2 + line_h * len(lines) + (gap * 2 + rule_h + s_asc + s_desc if sub else 0)
    w = round(content_w + padx * 2)
    B = 3                                     # transparent border so edges antialias when rotated
    body = paper_texture(w, h, seed=len(title))
    img = Image.fromarray(body.astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    y = pady
    for l in lines:
        d.text((w / 2, y + asc), l, font=serif, fill=INK, anchor="ms")
        y += line_h
    if sub:
        y += gap
        rw = round(size * 0.5)
        d.rectangle((w / 2 - rw / 2, y, w / 2 + rw / 2, y + rule_h - 1), fill=INK)
        y += rule_h + gap
        tracked(d, w / 2, y + s_asc, sub, sans, track, (59, 51, 44))
    out = Image.new("RGBA", (w + 2 * B, h + 2 * B), PAPER + (0,))
    out.paste(img, (B, B))
    return out


def load_logo(colour):
    logo = Image.open(LOGO).convert("RGBA")
    logo = logo.crop(logo.getchannel("A").getbbox())
    solid = Image.new("RGBA", logo.size, colour + (0,))
    solid.putalpha(logo.getchannel("A"))
    return solid


def make_card(spec, size):
    pw, ph = size
    img = Image.fromarray(paper_texture(pw, ph, seed=11).astype(np.uint8))
    d = ImageDraw.Draw(img)
    logo = load_logo(INK)
    lw = spec.get("logo_width", 560)
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    cta = font("BodoniModa-MediumItalic.ttf", spec.get("cta_size", 58))
    sans = font("Jost-Regular.ttf", spec.get("swatch_size", 24))
    track = sans.size * 0.3
    c_asc, c_desc = cta.getmetrics()
    s_asc, s_desc = sans.getmetrics()
    gap1, gap2 = spec.get("gap", 34), round(spec.get("gap", 34) * 0.75)
    total = logo.height + gap1 + c_asc + c_desc + gap2 + s_asc + s_desc
    y = (ph - total) / 2
    img.paste(logo, (round(pw / 2 - lw / 2), round(y)), logo)
    y += logo.height + gap1
    d.text((pw / 2, y + c_asc), spec.get("cta", ""), font=cta, fill=INK, anchor="ms")
    y += c_asc + c_desc + gap2
    sw = spec.get("swatches", [])
    if sw:
        dot, dgap, igap = round(sans.size * 0.62), round(sans.size * 0.5), round(sans.size * 1.6)
        widths = [dot + dgap + tracked_width(n.upper(), sans, track) for _, n in sw]
        x = pw / 2 - (sum(widths) + igap * (len(sw) - 1)) / 2
        base = y + s_asc
        for (hexc, name), wdt in zip(sw, widths):
            cy = base - s_asc * 0.36
            d.ellipse((x, cy - dot / 2, x + dot, cy + dot / 2), fill=rgb(hexc))
            tw = tracked_width(name.upper(), sans, track)
            tracked(d, x + dot + dgap + tw / 2, base, name.upper(), sans, track, (59, 51, 44))
            x += wdt + igap
    return img


# ---------------------------------------------------------------- geometry

def local_from_canvas(center, theta, L, C, c0):
    """q = A @ P + b: canvas point P -> layer-local point q (origin at layer centre).
    Undoes the camera zoom C about c0, the layer position, rotation and lift scale."""
    ct, st = math.cos(theta), math.sin(theta)
    rinv = np.array([[ct, st], [-st, ct]])
    A = rinv / (L * C)
    b = rinv @ (np.array(c0, float) * (1 - 1 / C) - np.array(center, float)) / L
    return A, b


def clamp_window(c, half, size):
    lo, hi = half - SLACK, size - half + SLACK
    return size / 2 if lo > hi else min(max(c, lo), hi)


def view_map(view, src, band_cy, W, H, pw, ph):
    """Local print point q -> padded source pixel: q / s + k."""
    w, h = src["w"], src["h"]
    z = view.get("z", 1.0)
    if "s" in view:
        s = view["s"]
    elif view.get("fit") == "strip":
        s = max(pw / w, ph / h) * z
    else:
        s = max(W / w, H / h) * z
    cx, cy = view.get("u", 0.5) * w, view.get("v", 0.5) * h
    if view.get("anchor", "canvas") == "canvas":
        cx, cy = clamp_window(cx, W / 2 / s, w), clamp_window(cy, H / 2 / s, h)
        cy += (band_cy - H / 2) / s
    else:
        cx, cy = clamp_window(cx, pw / 2 / s, w), clamp_window(cy, ph / 2 / s, h)
    return s, np.array([cx + PAD, cy + PAD])


def shift_down(a, n):
    if n <= 0:
        return a
    out = np.zeros_like(a)
    out[n:] = a[:-n]
    return out


# ---------------------------------------------------------------- render

class Reel:
    def __init__(self, tl, shots):
        self.tl = tl
        self.W, self.H = tl.get("size", [1080, 1920])
        self.fps, self.D = tl.get("fps", 30), tl["duration"]
        W, H = self.W, self.H
        self.bands = tl.get("bands") or [[40, 647], [657, 1264], [1274, 1881]]
        self.bleed = tl.get("bleed", 30)
        self.pw = W + 2 * self.bleed
        self.cam = tl.get("camera", 0.03)
        self.c0 = (W / 2, H / 2)
        self.table = paper_texture(W, H, base=rgb(tl.get("table", "#E7DFD3")), seed=1, amount=2.6)
        yy = np.linspace(-1, 1, H)[:, None]
        xx = np.linspace(-1, 1, W)[None, :]
        self.table *= (1 - 0.05 * (xx ** 2 + yy ** 2) / 2)[..., None]
        self.sources = Sources(shots)
        self.views = dict(tl["views"])
        self.masks = {}
        self.logos = {}
        if "card" in tl:
            mid = self.bands[1]
            self.sources.add("__card__", make_card(tl["card"], (self.pw, mid[1] - mid[0])))
            self.views["__card__"] = {"shot": "__card__", "anchor": "strip", "s": 1.0}
        self.events = self.expand(tl["events"])
        self.labels = []
        for lab in tl.get("labels", []):
            img = make_label(lab["title"], lab.get("sub", ""), lab.get("size", 72))
            self.labels.append(dict(lab, img=img.convert("RGB"), alpha=img.getchannel("A")))

    def expand(self, events):
        out = []
        rnd = random.Random(self.tl.get("seed", 5))
        for i, e in enumerate(sorted(events, key=lambda e: e["t"])):
            strips = e.get("strips", [e.get("strip", 0)])
            for k, sidx in enumerate(strips):
                ev = dict(e, strip=sidx, t=e["t"] + k * e.get("stagger", 0.0), order=len(out))
                if ev["view"] not in self.views:
                    sys.exit(f"event at {e['t']}s names view {ev['view']!r}, which is not defined")
                tidy = len(strips) == 3 or ev["view"] == "__card__"
                ev["jitter"] = (rnd.uniform(-0.12, 0.12), 0.0, 0.0) if tidy else \
                    (rnd.uniform(-0.38, 0.38), rnd.uniform(-6, 6), rnd.uniform(-2, 2))
                ev["tilt"] = rnd.choice((-1, 1)) * rnd.uniform(0.4, 0.9)
                ev.setdefault("dur", 0.24 if ev.get("enter", "drop").startswith("slide") else 0.12)
                ev.setdefault("lift", 0.035)
                out.append(ev)
        return out

    def current(self, strip, t):
        best = None
        for e in self.events:
            if e["strip"] == strip and e["t"] <= t + 1e-6:
                best = e
        return best

    def rect_mask(self, w, h):
        key = (w, h)
        if key not in self.masks:
            m = Image.new("L", (w + 4, h + 4), 0)
            ImageDraw.Draw(m).rectangle((2, 2, w + 1, h + 1), fill=255)
            self.masks[key] = m
        return self.masks[key]

    def logo(self, colour):
        if colour not in self.logos:
            self.logos[colour] = load_logo(PAPER if colour == "paper" else INK)
        return self.logos[colour]

    def frame(self, t):
        C = 1 + self.cam * smooth(clamp(t / self.D))
        canvas = self.table.copy()
        live = [e for e in (self.current(i, t) for i in range(3)) if e]
        for e in sorted(live, key=lambda e: (e["t"], e["order"])):
            self.draw_print(canvas, e, t, C)
        for lab in self.labels:
            if lab["t0"] <= t < lab["t1"] + 0.14:
                self.draw_label(canvas, lab, t, C)
        return np.clip(canvas, 0, 255).astype(np.uint8)

    def draw_print(self, canvas, e, t, C):
        i = e["strip"]
        y0, y1 = self.bands[i]
        ph, bcy = y1 - y0, (y0 + y1) / 2
        enter = e.get("enter", "drop")
        p = 1.0 if enter == "cut" else clamp((t - e["t"]) / e["dur"])
        k = 1 - ease_out(p)
        ang, jx, jy = e["jitter"]
        dx = 0.0
        if enter.startswith("slide"):
            side = -1 if enter == "slide-left" else 1
            dx = side * self.W * 1.1 * k
            ang += side * 3.0 * k
        else:
            ang += e["tilt"] * k
        L = 1 + e["lift"] * k
        A, b = local_from_canvas((self.W / 2 + jx + dx, bcy + jy), math.radians(ang), L, C, self.c0)
        view = self.views[e["view"]]
        src = self.sources.get(view["shot"])
        s, kk = view_map(view, src, bcy, self.W, self.H, self.pw, ph)
        overlay = None
        if e.get("logo"):
            lg = self.logo(e["logo"])
            lw = e.get("logo_width", 0.62) * self.W
            ls = lw / lg.width
            overlay = (lg, A / ls, b / ls + np.array([lg.width / 2, lg.height / 2]))
        self.draw_layer(canvas, (self.pw, ph),
                        src["img"], A / s, b / s + kk,
                        self.rect_mask(self.pw, ph), A, b + np.array([self.pw / 2 + 2, ph / 2 + 2]),
                        shadow=(5 + 16 * k, 7 + 12 * k, 0.36 - 0.08 * k), overlay=overlay, edge=True)

    def draw_label(self, canvas, lab, t, C):
        p = clamp((t - lab["t0"]) / 0.22)
        k = 1 - ease_out(p)
        alpha, L = 1.0, 1 + 0.10 * k
        if t >= lab["t1"]:
            q = clamp((t - lab["t1"]) / 0.14)
            alpha, L = 1 - q, L * (1 + 0.05 * q)
        ang = lab.get("angle", 0) + 2.2 * k * (1 if lab.get("angle", 0) >= 0 else -1)
        A, b = local_from_canvas((lab["x"], lab["y"]), math.radians(ang), L, C, self.c0)
        img = lab["img"]
        bb = b + np.array([img.width / 2, img.height / 2])
        self.draw_layer(canvas, img.size, img, A, bb, lab["alpha"], A, bb,
                        shadow=(6 + 14 * k, 8 + 10 * k, 0.32 * alpha), alpha=alpha)

    def draw_layer(self, canvas, size, img, Ac, bc, mimg, Am, bm, shadow, alpha=1.0, overlay=None, edge=False):
        W, H = self.W, self.H
        w, h = size
        # canvas bounding box of the layer, via the inverse of the local map
        Ainv = np.linalg.inv(Am)
        off = bm - Am @ np.zeros(2)
        corners = [Ainv @ (np.array([x, y]) - off) for x in (0, w + 4) for y in (0, h + 4)]
        sx, sy, sop = shadow
        m = int(sy * 2.5 + sx + 6)
        x0 = max(0, int(min(c[0] for c in corners)) - m)
        x1 = min(W, int(max(c[0] for c in corners)) + m + 1)
        y0 = max(0, int(min(c[1] for c in corners)) - m)
        y1 = min(H, int(max(c[1] for c in corners)) + m + 1)
        if x1 <= x0 or y1 <= y0:
            return
        rw, rh = x1 - x0, y1 - y0

        def coeffs(A, b):
            return (A[0, 0], A[0, 1], A[0, 0] * x0 + A[0, 1] * y0 + b[0],
                    A[1, 0], A[1, 1], A[1, 0] * x0 + A[1, 1] * y0 + b[1])

        mask = np.asarray(mimg.transform((rw, rh), Image.AFFINE, coeffs(Am, bm), resample=Image.BILINEAR),
                          np.float32) / 255 * alpha
        reg = canvas[y0:y1, x0:x1]
        if sop > 0:
            sh = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(sy))
            sh = shift_down(np.asarray(sh, np.float32) / 255, int(round(sx)))[..., None] * sop
            reg *= 1 - sh
            reg += SHADOW * sh
        col = np.asarray(img.transform((rw, rh), Image.AFFINE, coeffs(Ac, bc), resample=Image.BICUBIC),
                         np.float32)
        mk = mask[..., None]
        reg *= 1 - mk
        reg += col * mk
        if overlay is not None:
            oimg, Ao, bo = overlay
            ov = np.asarray(oimg.transform((rw, rh), Image.AFFINE, coeffs(Ao, bo), resample=Image.BICUBIC),
                            np.float32)
            oa = ov[..., 3:4] / 255 * mk
            reg *= 1 - oa
            reg += ov[..., :3] * oa
        if edge:
            # the cut edge of the paper catches the light along the top of each print
            te = np.clip(mask - shift_down(mask, 2), 0, 1)[..., None] * 0.5
            reg *= 1 - te
            reg += 252 * te


# ---------------------------------------------------------------- sound

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def freq(name):
    n = NOTE[name[0]]
    rest = name[1:]
    while rest and rest[0] in "#b":
        n += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 440.0 * 2 ** ((n + 12 * (int(rest) + 1) - 69) / 12)


def lufs(x, sr=48000):
    """Integrated loudness, ITU-R BS.1770 (K-weighting, 400 ms blocks, gated)."""
    from scipy.signal import lfilter
    k1 = ([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585])
    k2 = ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])
    y = lfilter(*k2, lfilter(*k1, x, axis=0), axis=0)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if len(y) < blk:
        return -70.0
    idx = np.arange(0, len(y) - blk + 1, hop)
    ms = np.array([(y[i:i + blk] ** 2).mean(axis=0).sum() for i in idx])
    ld = -0.691 + 10 * np.log10(np.maximum(ms, 1e-12))
    g = ms[ld > -70]
    if not len(g):
        return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = ms[(ld > -70) & (ld > rel)]
    return float(-0.691 + 10 * np.log10(g.mean()))


def limit(x, sr=48000, ceiling_db=-1.5):
    """Lookahead true-peak limiter: hold the gain down 30 ms around each overshoot,
    ramp over 12 ms, so transients are caught without pumping the bed."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    from scipy.signal import resample_poly
    ceil = 10 ** (ceiling_db / 20)
    over = np.abs(resample_poly(x, 4, 1, axis=0)).max(axis=1)
    peak = over[: len(x) * 4].reshape(-1, 4).max(axis=1)
    need = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
    g = uniform_filter1d(minimum_filter1d(need, size=int(0.03 * sr)), size=int(0.012 * sr))
    return x * np.minimum(g, need)[:, None]


def synth_sound(tl, events, path, sr=48000):
    """Score and foley from the timeline, as stems levelled against each other,
    then a true-peak limiter and -14 LUFS, where Instagram plays back."""
    from scipy.signal import butter, sosfilt, fftconvolve
    from scipy.io import wavfile

    spec = tl.get("sound", {})
    D = tl["duration"]
    n = int(D * sr) + sr
    rng = np.random.default_rng(9)
    T = np.arange(n) / sr
    names = ("pad", "drums", "foley", "fx")
    dry = {k: np.zeros((n, 2)) for k in names}
    send = {k: np.zeros((n, 2)) for k in names}

    def bp(x, lo, hi, order=2):
        return sosfilt(butter(order, [lo, hi], btype="band", fs=sr, output="sos"), x)

    def lp(x, f, order=2):
        return sosfilt(butter(order, f, btype="low", fs=sr, output="sos"), x)

    def place(stem, sig, t, gain=1.0, pan=0.0, wet=0.0):
        i = int(round(t * sr))
        if i >= n or i + len(sig) <= 0:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        sig = sig[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        for c, g in ((0, l), (1, r)):
            dry[stem][i:i + len(sig), c] += sig * gain * g
            send[stem][i:i + len(sig), c] += sig * gain * g * wet

    # pad and bass, one chord per section; each side gets the same voices,
    # detuned a few cents apart so the bed is wide but balanced
    chords = spec.get("chords", [])
    for ci, (t0, root, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else D + 0.5
        env = smooth(np.clip(np.clip((T - t0) / 0.45, 0, 1) * np.clip(1 - (T - t1) / 0.7, 0, 1), 0, 1))
        live = env > 0
        tl_ = T[live]
        phases = rng.uniform(0, 2 * math.pi, len(notes))
        fb = freq(root)
        bass = 0.55 * (np.sin(2 * math.pi * fb * tl_) + 0.15 * np.sin(4 * math.pi * fb * tl_))
        for side, cents in ((0, 3.0), (1, -3.0)):
            det = 2 ** (cents / 1200)
            v = np.zeros(len(tl_))
            for nm, ph in zip(notes, phases):
                f = freq(nm) * det
                v += (np.sin(2 * math.pi * f * tl_ + ph) + 0.22 * np.sin(4 * math.pi * f * tl_ + ph)
                      + 0.06 * np.sin(6 * math.pi * f * tl_ + ph)) / len(notes)
            dry["pad"][live, side] += (v + bass) * env[live]
    for c in range(2):
        dry["pad"][:, c] = lp(dry["pad"][:, c], 1900)
    dry["pad"] *= (0.85 + 0.15 * np.sin(2 * math.pi * T / 4.0 - math.pi / 2))[:, None]
    send["pad"] = dry["pad"] * 0.6

    # paper: a dry slap and a bright flick for every print that lands
    pans = {0: -0.25, 1: 0.0, 2: 0.25}
    for e in events:
        m = int(0.14 * sr)
        tt = np.arange(m) / sr
        env = np.minimum(tt / 0.0015, 1) * np.exp(-tt / rng.uniform(0.018, 0.03))
        flick = bp(rng.normal(0, 1, m), rng.uniform(1400, 2200), rng.uniform(5200, 7500)) * env
        slap = lp(rng.normal(0, 1, m), 520) * np.minimum(tt / 0.001, 1) * np.exp(-tt / 0.012)
        sig = 0.55 * flick + 1.3 * slap
        if e.get("enter", "drop").startswith("slide"):
            mm = int(0.22 * sr)
            ts = np.arange(mm) / sr
            swish = bp(rng.normal(0, 1, mm), 900, 6000) * (ts / ts[-1]) ** 2
            place("foley", swish, e["t"], 0.35, pans[e["strip"]], 0.2)
            place("foley", sig, e["t"] + 0.20, 1.0, pans[e["strip"]], 0.12)
        else:
            gain = 1.3 if e["view"] == "__card__" else 1.0
            place("foley", sig, e["t"] + 0.03, gain * rng.uniform(0.85, 1.0), pans[e["strip"]], 0.12)

    def kick(length=0.45, f_lo=46, f_hi=120, decay=0.16):
        m = int(length * sr)
        tt = np.arange(m) / sr
        f = f_lo + (f_hi - f_lo) * np.exp(-tt / 0.03)
        body = np.sin(2 * math.pi * np.cumsum(f) / sr) * np.exp(-tt / decay)
        return body + bp(rng.normal(0, 1, m), 2000, 6000) * np.exp(-tt / 0.003) * 0.25

    for t in spec.get("kicks", []):
        place("drums", kick(decay=0.11), t, 0.5)
    for t in spec.get("thumps", []):
        place("drums", kick(0.9, 40, 140, 0.32), t, 1.0, wet=0.08)
    for t in spec.get("risers", []):
        L = 0.7
        tt = np.arange(int(L * sr)) / sr
        place("fx", bp(rng.normal(0, 1, len(tt)), 1500, 9000) * (tt / L) ** 3, t - L, 1.0, 0, 0.3)
    if "chime" in spec:
        m = int(2.6 * sr)
        tt = np.arange(m) / sr
        bell = np.zeros(m)
        for f0, a0, delay in ((freq("F5"), 1.0, 0.0), (freq("C6"), 0.55, 0.11), (freq("A5"), 0.4, 0.2)):
            st = int(delay * sr)
            ts = tt[: m - st]
            bell[st:] += a0 * np.minimum(ts / 0.002, 1) * sum(
                a * np.sin(2 * math.pi * f0 * r * ts) * np.exp(-ts / dcy)
                for r, a, dcy in ((1, 1, 1.3), (2.0, 0.28, 0.6), (3.01, 0.1, 0.3), (4.2, 0.05, 0.18)))
        place("fx", bell, spec["chime"], 1.6, 0.0, 0.55)

    # one room for everything
    ir_n = int(2.2 * sr)
    ti = np.arange(ir_n) / sr
    hp = butter(2, 240, btype="high", fs=sr, output="sos")
    # no lows in the room: two random tails differ by several dB down there,
    # which would pull the kick and bass to one side
    ir = np.stack([sosfilt(hp, lp(rng.normal(0, 1, ir_n), 5200)) * np.exp(-ti / 0.45) for _ in range(2)], axis=1)
    ir /= np.sqrt((ir ** 2).sum(axis=0))
    targets = spec.get("levels", {"pad": -21.0, "drums": -18.0, "foley": -19.5, "fx": -23.0})
    mix = np.zeros((n, 2))
    for k in names:
        stem = dry[k] + 0.9 * np.stack([fftconvolve(sosfilt(hp, send[k][:, c]), ir[:, c])[:n]
                                        for c in range(2)], axis=1)
        level = lufs(stem[: int(D * sr)], sr)
        if level > -69:
            mix += stem * 10 ** ((targets[k] - level) / 20)
    mix = mix[: int(D * sr)]
    fade = int(0.35 * sr)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    for _ in range(3):
        mix = limit(mix * 10 ** ((-14.0 - lufs(mix, sr)) / 20), sr)
    wavfile.write(path, sr, (np.clip(mix, -1, 1) * 32767).astype(np.int16))


# ---------------------------------------------------------------- automatic cut

def build_timeline(shots, sources, duration, step, seed, order=None, W=1080, H=1920):
    rnd = random.Random(seed)
    colours = list(dict.fromkeys(s["colour"] for s in shots.values()))
    if order:
        unknown = [c for c in order if c not in colours]
        if unknown:
            sys.exit(f"--order names {unknown}, but the shots are {colours}")
        colours = order + [c for c in colours if c not in order]
    views = {}
    for sid, s in shots.items():
        if s["kind"] == "detail":
            views[sid] = {"shot": sid, "anchor": "strip", "fit": "strip"}
        elif s["kind"] in ("full", "profile"):
            views[sid] = dict({"shot": sid, "anchor": "canvas"}, **align_full(sources.get(sid), W, H))
        else:
            views[sid] = {"shot": sid, "anchor": "canvas"}
    by = {c: [s for s in shots.values() if s["colour"] == c] for c in colours}

    def hero(c):
        pool = [s for s in by[c] if s["kind"] == "full"] or [s for s in by[c] if s["kind"] != "detail"] or by[c]
        return pool[0]["id"]

    body_end = duration - 1.0
    phase = (body_end - step) / len(colours)
    events = [{"t": 0.0, "strips": [0, 1, 2], "stagger": 0.08, "view": hero(colours[0])}]
    current = [hero(colours[0])] * 3
    t, k = step * 2, 0
    while t < body_end - step / 2:
        colour = colours[min(int((t - step) / phase), len(colours) - 1)]
        sidx = k % 3
        pool = by[colour]
        if rnd.random() < 0.15 and len(colours) > 1:
            pool = by[rnd.choice([c for c in colours if c != colour])]
        allowed = [s for s in pool if s["id"] != current[sidx] and (s["kind"] != "detail" or sidx == 1)] \
            or [s for s in pool if s["id"] != current[sidx]] or pool
        shot = rnd.choice(allowed)
        if not all(current[j] == shot["id"] for j in range(3) if j != sidx):
            current[sidx] = shot["id"]
            ev = {"t": round(t, 3), "strip": sidx, "view": shot["id"]}
            if sidx == 1 and shot["kind"] != "detail" and rnd.random() < 0.4:
                ev["logo"] = "paper" if np.asarray(sources.get(shot["id"])["thumb"]).mean() < 120 else "ink"
            events.append(ev)
        t += step
        k += 1
    events.append({"t": round(body_end, 3), "strips": [0, 1, 2], "stagger": 0.06,
                   "view": hero(colours[-1]), "logo": "paper"})
    return {"duration": duration, "seed": seed, "views": views, "events": events,
            "sound": {"thumps": [0.0, round(body_end, 3)]}}


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--timeline", help="authored timeline json")
    ap.add_argument("--out", default="out/strips.mp4")
    ap.add_argument("--duration", type=float, default=8.7)
    ap.add_argument("--step", type=float, default=0.25, help="seconds between automatic cuts (0.25 = eighths at 120 BPM)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--order", help="colourway order for the automatic cut, e.g. brown,black,burgundy")
    ap.add_argument("--audio", help="use this audio file instead of the synthesised score")
    ap.add_argument("--no-sound", action="store_true", help="render without any audio track")
    ap.add_argument("--stills", help="comma-separated times: write those frames as JPGs and stop")
    args = ap.parse_args()

    shots = load_shots(args.folder)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.timeline:
        tl = json.loads(Path(args.timeline).read_text())
    else:
        tl = build_timeline(shots, Sources(shots), args.duration, args.step, args.seed,
                            args.order.split(",") if args.order else None)
        out.with_suffix(".timeline.json").write_text(json.dumps(tl, indent=1, ensure_ascii=False))
    reel = Reel(tl, shots)
    W, H, fps = reel.W, reel.H, reel.fps

    if args.stills:
        for ts in args.stills.split(","):
            p = out.with_name(f"{out.stem}_{float(ts):05.2f}s.jpg")
            Image.fromarray(reel.frame(float(ts))).save(p, quality=92)
            print(p)
        return

    with tempfile.TemporaryDirectory() as tmp:
        audio = None
        if args.audio:
            audio = args.audio
        elif not args.no_sound:
            audio = str(Path(tmp) / "score.wav")
            synth_sound(tl, reel.events, audio)
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(fps), "-i", "-"]
        if audio:
            cmd += ["-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p",
                "-r", str(fps), "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n = round(reel.D * fps)
        for f in range(n):
            proc.stdin.write(reel.frame(f / fps).tobytes())
            if f % fps == 0:
                print(f"\r{f / fps:5.1f}s / {reel.D:.1f}s", end="", file=sys.stderr, flush=True)
        proc.stdin.close()
        print(file=sys.stderr)
        if proc.wait() != 0:
            sys.exit("ffmpeg failed")
    print(f"reel -> {out}")


if __name__ == "__main__":
    main()
