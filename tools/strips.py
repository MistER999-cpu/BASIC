#!/usr/bin/env python3
"""Paper-strip reel.

Every photo is printed as three horizontal strips of paper, white-bordered and
laid by hand on a lilac table: each strip a little crooked and warped, the
edges overlapping with a soft shadow. Moving to the next photo, its strips are
hard-cut on top of the old ones from the top down, a few frames apart, so for
an instant the frame holds two photos at once. Each photo appears once.

    python3 tools/strips.py assets/strips --timeline assets/strips/ad.json --out out/ad.mp4
    python3 tools/strips.py assets/strips --timeline assets/strips/ad.json --stills 0.2,2.0,10.5
    python3 tools/strips.py assets/strips --out out/reel.mp4          # every shot in the folder, once

Shots are named <colour>_<kind>_<anything>.jpg (kind: full, profile, half,
detail) and are referred to by file stem.

Timeline JSON (all keys optional except sequence):

    sequence   shot stems, in order, each shown once
    period     seconds from one photo's cascade to the next          (1.7)
    stagger    seconds between the three strips of a cascade          (5 frames)
    end_hold   seconds the last photo stays once it is complete       (2.2)
    tilt       {"first": deg, "last": deg, "max": deg}  how crooked prints may lie
    views      {stem: {u, v, z}}  reframe a photo (source point at frame centre, zoom)
    logo       {"on": ["first", "last"], "width": 0.46, "y": 0.47, "colour": "paper"|"ink"}
    sound      {chords, kicks, thumps, chime, levels}   synthesised score and paper foley
    size, fps, seed, table, bands, margin
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
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "assets" / "brand" / "basic-logo.png"

KINDS = ("full", "profile", "half", "detail")
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
PAD = 200                          # edge-extended margin around every source
SLACK = 150                        # how far a crop may run into it

PAPER = (247, 244, 239)            # BASIC paper, for the logo on dark fabric
INK = (22, 17, 14)                 # BASIC ink
PRINT_WHITE = (239, 237, 233)      # the white border of a photo print
SHADOW = np.array([44, 38, 52], np.float32)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


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

    def get(self, sid):
        if sid not in self.cache:
            if sid not in self.shots:
                sys.exit(f"timeline names shot {sid!r}, which is not in the folder")
            a = np.asarray(Image.open(self.shots[sid]["path"]).convert("RGB"))
            h, w = a.shape[:2]
            padded = np.pad(a, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
            self.cache[sid] = {"img": Image.fromarray(padded), "w": w, "h": h}
        return self.cache[sid]


def clamp_window(c, half, size):
    lo, hi = half - SLACK, size - half + SLACK
    return size / 2 if lo > hi else min(max(c, lo), hi)


def view_map(view, src, band_cy, W, H):
    """Print-local point q (origin at the strip centre) -> padded source pixel,
    q / s + k. The three strips of a photo slice one cover-fit frame, so they
    line up wherever the paper lies straight."""
    w, h = src["w"], src["h"]
    s = max(W / w, H / h) * view.get("z", 1.0)
    cx = clamp_window(view.get("u", 0.5) * w, W / 2 / s, w)
    cy = clamp_window(view.get("v", 0.5) * h, H / 2 / s, h) + (band_cy - H / 2) / s
    return s, np.array([cx + PAD, cy + PAD])


# ---------------------------------------------------------------- geometry

def homography(src_pts, dst_pts):
    """3x3 H with H @ (x, y, 1) ~ (u, v, 1) for four point pairs."""
    A, b = [], []
    for (x, y), (u, v) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b += [u, v]
    return np.append(np.linalg.solve(np.array(A, float), np.array(b, float)), 1).reshape(3, 3)


def coeffs(M):
    M = M / M[2, 2]
    return (M[0, 0], M[0, 1], M[0, 2], M[1, 0], M[1, 1], M[1, 2], M[2, 0], M[2, 1])


def translate(x, y):
    return np.array([[1, 0, x], [0, 1, y], [0, 0, 1]], float)


def shift_down(a, n):
    if n <= 0:
        return a
    out = np.zeros_like(a)
    out[n:] = a[:-n]
    return out


def table_texture(W, H, base, seed=1):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1.6, (H, W)).astype(np.float32)
    yy = np.linspace(-1, 1, H)[:, None]
    xx = np.linspace(-1, 1, W)[None, :]
    light = 1 - 0.04 * (xx ** 2 + yy ** 2) / 2
    return np.clip(np.array(base, np.float32)[None, None, :] * light[..., None] + n[..., None], 0, 255)


def load_logo(colour, width, shadow):
    logo = Image.open(LOGO).convert("RGBA")
    logo = logo.crop(logo.getchannel("A").getbbox())
    logo = logo.resize((round(width), round(logo.height * width / logo.width)), Image.LANCZOS)
    a = np.asarray(logo.getchannel("A"), np.float32) / 255
    pad = 40
    A = np.zeros((a.shape[0] + 2 * pad, a.shape[1] + 2 * pad), np.float32)
    A[pad:-pad, pad:-pad] = a
    sh = np.asarray(Image.fromarray((A * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9)),
                    np.float32) / 255
    sh = shift_down(sh, 3) * shadow
    return {"a": A, "sh": sh, "rgb": np.array(PAPER if colour == "paper" else INK, np.float32)}


# ---------------------------------------------------------------- render

class Reel:
    def __init__(self, tl, shots):
        self.tl = tl
        self.W, self.H = tl.get("size", [1080, 1920])
        self.fps = tl.get("fps", 30)
        W, H = self.W, self.H
        self.bands = tl.get("bands") or [[16, 700], [632, 1290], [1222, 1904]]
        self.margin = tl.get("margin", 11)
        self.bleed = 60
        self.table = table_texture(W, H, rgb(tl.get("table", "#A9A5B7")))
        self.sources = Sources(shots)
        self.views = tl.get("views", {})
        self.rnd = random.Random(tl.get("seed", 5))
        self.events, self.overlays, self.D = self.expand(tl)
        self.masks = {}
        self.logos = {}
        self.cache_key, self.cache = None, None

    def expand(self, tl):
        seq = tl["sequence"]
        period = tl.get("period", 1.7)
        stagger = tl.get("stagger", 5 / self.fps)
        tilt = {"first": 0.7, "last": 0.7, "max": 2.8}
        tilt.update(tl.get("tilt", {}))
        events, cascades = [], []
        for i, sid in enumerate(seq):
            t = i * period
            cascades.append(t)
            cap = tilt["first"] if i == 0 else tilt["last"] if i == len(seq) - 1 else tilt["max"]
            for k in range(3):
                events.append(dict(self.place(cap), shot=sid, strip=k, order=len(events),
                                   t=0.0 if i == 0 else t + k * stagger))
        duration = cascades[-1] + 2 * stagger + tl.get("end_hold", 2.2)
        overlays = []
        logo = tl.get("logo")
        if logo:
            on = logo.get("on", ["first", "last"])
            if "first" in on and len(seq) > 1:
                overlays.append(dict(logo, t0=0.0, t1=cascades[1] + stagger))
            if "last" in on:
                overlays.append(dict(logo, t0=cascades[-1] + stagger if len(seq) > 1 else 0.0, t1=duration + 1))
        return events, overlays, duration

    def place(self, cap):
        """How a print lies: crooked by up to `cap` degrees (half the prints nearly
        straight), nudged, and warped a few pixels at each corner like real paper."""
        r = self.rnd
        if cap <= 1.0 or r.random() < 0.45:
            ang = r.uniform(-min(cap, 0.6), min(cap, 0.6))
        else:
            ang = r.choice((-1, 1)) * r.uniform(min(1.4, cap), cap)
        return {"angle": ang, "dx": r.uniform(-18, 18), "dy": r.uniform(-6, 6),
                "warp": [r.uniform(-5, 5) for _ in range(8)]}

    def mask(self, w, h, inset):
        key = (w, h, inset)
        if key not in self.masks:
            m = Image.new("L", (w + 4, h + 4), 0)
            ImageDraw.Draw(m).rectangle((2 + inset, 2 + inset, w + 1 - inset, h + 1 - inset), fill=255)
            self.masks[key] = m
        return self.masks[key]

    def logo(self, spec):
        key = (spec.get("colour", "paper"), spec.get("width", 0.46))
        if key not in self.logos:
            self.logos[key] = load_logo(key[0], key[1] * self.W, spec.get("shadow", 0.45))
        return self.logos[key]

    def visible(self, t):
        """The prints on the table at time t: the newest two per strip, in the
        order they were laid."""
        out = []
        for k in range(3):
            laid = [e for e in self.events if e["strip"] == k and e["t"] <= t + 1e-6]
            out += laid[-2:]
        return sorted(out, key=lambda e: (e["t"], e["order"]))

    def frame(self, t):
        prints = self.visible(t)
        logos = [o for o in self.overlays if o["t0"] <= t + 1e-6 < o["t1"]]
        key = (tuple(e["order"] for e in prints), tuple(id(o) for o in logos))
        if key != self.cache_key:
            canvas = self.table.copy()
            for e in prints:
                self.draw_print(canvas, e)
            for o in logos:
                self.draw_logo(canvas, o)
            self.cache_key, self.cache = key, np.clip(canvas, 0, 255).astype(np.uint8)
        return self.cache

    def draw_print(self, canvas, e):
        W, H, m = self.W, self.H, self.margin
        y0, y1 = self.bands[e["strip"]]
        bcy = (y0 + y1) / 2
        pw, ph = W + 2 * self.bleed, y1 - y0               # photo area of the strip
        PW, PH = pw + 2 * m, ph + 2 * m                   # with its white border
        # where the four corners of the paper land on the table
        th = math.radians(e["angle"])
        ct, st = math.cos(th), math.sin(th)
        cx, cy = W / 2 + e["dx"], bcy + e["dy"]
        local = [(-PW / 2, -PH / 2), (PW / 2, -PH / 2), (PW / 2, PH / 2), (-PW / 2, PH / 2)]
        wj = e["warp"]
        canvas_pts = [(cx + x * ct - y * st + wj[2 * i], cy + x * st + y * ct + wj[2 * i + 1])
                      for i, (x, y) in enumerate(local)]
        Hcl = homography(canvas_pts, local)                # canvas -> print-local
        rx0 = max(0, int(min(p[0] for p in canvas_pts)) - 30)
        rx1 = min(W, int(max(p[0] for p in canvas_pts)) + 31)
        ry0 = max(0, int(min(p[1] for p in canvas_pts)) - 30)
        ry1 = min(H, int(max(p[1] for p in canvas_pts)) + 31)
        if rx1 <= rx0 or ry1 <= ry0:
            return
        size = (rx1 - rx0, ry1 - ry0)
        Hr = Hcl @ translate(rx0, ry0)                     # region pixel -> print-local
        to_mask = translate(PW / 2 + 2, PH / 2 + 2) @ Hr
        outer = np.asarray(self.mask(PW, PH, 0).transform(size, Image.PERSPECTIVE, coeffs(to_mask),
                                                          resample=Image.BILINEAR), np.float32) / 255
        inner = np.asarray(self.mask(PW, PH, m).transform(size, Image.PERSPECTIVE, coeffs(to_mask),
                                                          resample=Image.BILINEAR), np.float32) / 255
        view = self.views.get(e["shot"], {})
        src = self.sources.get(e["shot"])
        s, k = view_map(view, src, bcy, W, H)
        to_src = np.array([[1 / s, 0, k[0]], [0, 1 / s, k[1]], [0, 0, 1]]) @ Hr
        photo = np.asarray(src["img"].transform(size, Image.PERSPECTIVE, coeffs(to_src), resample=Image.BICUBIC),
                           np.float32)
        reg = canvas[ry0:ry1, rx0:rx1]
        # the paper sits a hair above what is under it: a soft shadow along its edges
        o8 = Image.fromarray((outer * 255).astype(np.uint8))
        near = shift_down(np.asarray(o8.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255, 3)
        far = shift_down(np.asarray(o8.filter(ImageFilter.GaussianBlur(11)), np.float32) / 255, 7)
        sh = np.clip(0.22 * near + 0.16 * far, 0, 1)[..., None]
        reg *= 1 - sh
        reg += SHADOW * sh
        paper = np.array(PRINT_WHITE, np.float32)
        col = paper + (photo - paper) * inner[..., None]
        o = outer[..., None]
        reg *= 1 - o
        reg += col * o

    def draw_logo(self, canvas, spec):
        lg = self.logo(spec)
        h, w = lg["a"].shape
        x0 = round(self.W / 2 - w / 2)
        y0 = round(spec.get("y", 0.47) * self.H - h / 2)
        reg = canvas[y0:y0 + h, x0:x0 + w]
        sh = lg["sh"][..., None]
        reg *= 1 - sh
        reg += SHADOW * 0.3 * sh
        a = lg["a"][..., None]
        reg *= 1 - a
        reg += lg["rgb"] * a


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
    ms = np.array([(y[i:i + blk] ** 2).mean(axis=0).sum() for i in range(0, len(y) - blk + 1, hop)])
    ld = -0.691 + 10 * np.log10(np.maximum(ms, 1e-12))
    g = ms[ld > -70]
    if not len(g):
        return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = ms[(ld > -70) & (ld > rel)]
    return float(-0.691 + 10 * np.log10(g.mean()))


def limit(x, sr=48000, ceiling_db=-2.0):
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


def synth_sound(spec, events, D, path, sr=48000):
    """A soft chord bed, a paper slap for every strip that lands, kicks and a chime,
    as stems levelled against each other, then true-peak limited to -14 LUFS."""
    from scipy.signal import butter, sosfilt, fftconvolve
    from scipy.io import wavfile

    n = int(D * sr) + sr
    rng = np.random.default_rng(9)
    T = np.arange(n) / sr
    names = ("pad", "drums", "foley", "fx")
    dry = {k: np.zeros((n, 2)) for k in names}
    send = {k: np.zeros((n, 2)) for k in names}

    def bp(x, lo, hi):
        return sosfilt(butter(2, [lo, hi], btype="band", fs=sr, output="sos"), x)

    def lp(x, f):
        return sosfilt(butter(2, f, btype="low", fs=sr, output="sos"), x)

    def place(stem, sig, t, gain=1.0, pan=0.0, wet=0.0):
        i = int(round(t * sr))
        if i >= n:
            return
        sig = sig[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        for c, g in ((0, l), (1, r)):
            dry[stem][i:i + len(sig), c] += sig * gain * g
            send[stem][i:i + len(sig), c] += sig * gain * g * wet

    chords = spec.get("chords", [])
    for ci, (t0, root, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else D + 0.5
        env = smooth(np.clip(np.clip((T - t0) / 0.45, 0, 1) * np.clip(1 - (T - t1) / 0.7, 0, 1), 0, 1))
        live = env > 0
        tt = T[live]
        phases = rng.uniform(0, 2 * math.pi, len(notes))
        fb = freq(root)
        bass = 0.55 * (np.sin(2 * math.pi * fb * tt) + 0.15 * np.sin(4 * math.pi * fb * tt))
        for side, cents in ((0, 3.0), (1, -3.0)):
            det = 2 ** (cents / 1200)
            v = np.zeros(len(tt))
            for nm, ph in zip(notes, phases):
                f = freq(nm) * det
                v += (np.sin(2 * math.pi * f * tt + ph) + 0.22 * np.sin(4 * math.pi * f * tt + ph)
                      + 0.06 * np.sin(6 * math.pi * f * tt + ph)) / len(notes)
            dry["pad"][live, side] += (v + bass) * env[live]
    for c in range(2):
        dry["pad"][:, c] = lp(dry["pad"][:, c], 1900)
    send["pad"] = dry["pad"] * 0.6

    pans = {0: -0.25, 1: 0.0, 2: 0.25}
    for e in events:
        if e["t"] <= 0:
            continue
        m = int(0.14 * sr)
        tt = np.arange(m) / sr
        env = np.minimum(tt / 0.0015, 1) * np.exp(-tt / rng.uniform(0.018, 0.03))
        flick = bp(rng.normal(0, 1, m), rng.uniform(1400, 2200), rng.uniform(5200, 7500)) * env
        slap = lp(rng.normal(0, 1, m), 520) * np.minimum(tt / 0.001, 1) * np.exp(-tt / 0.012)
        place("foley", 0.55 * flick + 1.3 * slap, e["t"], rng.uniform(0.85, 1.0), pans[e["strip"]], 0.12)

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

    # one room; no lows in it, or two random tails pull the kick and bass to one side
    hp = butter(2, 240, btype="high", fs=sr, output="sos")
    ir_n = int(2.2 * sr)
    ti = np.arange(ir_n) / sr
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


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--timeline", help="timeline json; without one, every shot in the folder, once")
    ap.add_argument("--out", default="out/strips.mp4")
    ap.add_argument("--audio", help="use this audio file instead of the synthesised score")
    ap.add_argument("--no-sound", action="store_true", help="render without an audio track")
    ap.add_argument("--stills", help="comma-separated times: write those frames as JPGs and stop")
    args = ap.parse_args()

    shots = load_shots(args.folder)
    if args.timeline:
        tl = json.loads(Path(args.timeline).read_text())
    else:
        tl = {"sequence": sorted(shots, key=lambda s: (shots[s]["colour"], shots[s]["kind"] != "full", s)),
              "logo": {"on": ["first", "last"]}}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    reel = Reel(tl, shots)
    W, H, fps = reel.W, reel.H, reel.fps

    if args.stills:
        for ts in args.stills.split(","):
            p = out.with_name(f"{out.stem}_{float(ts):05.2f}s.jpg")
            Image.fromarray(reel.frame(float(ts))).save(p, quality=92)
            print(p)
        return

    with tempfile.TemporaryDirectory() as tmp:
        audio = args.audio
        if not audio and not args.no_sound:
            audio = str(Path(tmp) / "score.wav")
            synth_sound(tl.get("sound", {}), reel.events, reel.D, audio)
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(fps), "-i", "-"]
        if audio:
            cmd += ["-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p",
                "-r", str(fps), "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(round(reel.D * fps)):
            proc.stdin.write(reel.frame(f / fps).tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            sys.exit("ffmpeg failed")
    print(f"reel -> {out}  ({reel.D:.2f} s)")


if __name__ == "__main__":
    main()
