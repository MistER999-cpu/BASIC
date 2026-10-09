#!/usr/bin/env python3
"""Render the BASIC "burgundy" Instagram ad (1080x1920, 24 fps).

Frames are composed in numpy/PIL and piped to ffmpeg; sound effects are
synthesised here and mixed with the music by ffmpeg. Cuts sit on the beat grid
of Kavinsky's "Nightcall" (91.01 BPM, beat 0 = 10.7814 s into the track).

Usage:  python3 tools/ad-edit/render_burgundy_ad.py [--preview]
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AD = os.path.join(ROOT, "assets", "burgundy-ad")
OUT = os.path.join(ROOT, "exports")
W, H, FPS = 1080, 1920, 24
PERIOD = 60 / 91.01
MUSIC_T0 = 10.7814          # song time of timeline beat 0 (groove drops on beat 2)
TOTAL_BEATS = 27
SR = 48000
PREVIEW = "--preview" in sys.argv

CREAM = np.array([243, 234, 224], np.float32) / 255
TARGET_WALL = np.array([0x4A, 0x1C, 0x24], np.float32) / 255

FONT_DIR = "/usr/share/fonts/opentype/inter"
SERIF = "/mnt/skills/examples/canvas-design/canvas-fonts/InstrumentSerif-Italic.ttf"
INTER_MED = os.path.join(FONT_DIR, "Inter-Medium.otf")
INTER_REG = os.path.join(FONT_DIR, "Inter-Regular.otf")


def beat(k):
    return k * PERIOD


def nframes(t):
    return int(round(t * FPS))


def ease_in_out(u):
    return 0.5 - 0.5 * math.cos(math.pi * min(max(u, 0.0), 1.0))


def ease_out(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


# ---------------------------------------------------------------- sources ---

def load_clip(name):
    path = os.path.join(AD, "clips", name + ".mp4")
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 1920, 1080, 3)


def load_still(rel):
    return np.asarray(Image.open(os.path.join(AD, rel)).convert("RGB"))


def wall_mask(f):
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    ratio_g = r / (g + 0.02)
    ratio_b = r / (b + 0.02)
    m = np.clip((ratio_g - 1.45) / 0.35, 0, 1) * np.clip((ratio_b - 1.1) / 0.25, 0, 1)
    return m * np.clip((r - 0.08) / 0.06, 0, 1)


def wall_gain(sample_rgb_u8):
    f = sample_rgb_u8.astype(np.float32) / 255
    m = wall_mask(f) > 0.5
    if m.mean() < 0.3:
        return None
    med = np.median(f[m], axis=0)
    return np.clip(TARGET_WALL / np.maximum(med, 1e-3), 0.78, 1.22)


def transform(src, zoom, ax, ay, rot=0.0, out_w=W, out_h=H):
    """Cover-fit src into out_w x out_h, zoomed around anchor (ax, ay) in [0,1]."""
    sh, sw = src.shape[:2]
    s = max(out_w / sw, out_h / sh) * zoom
    half_w, half_h = out_w / (2 * s), out_h / (2 * s)
    cx = min(max(ax * sw, half_w), sw - half_w)
    cy = min(max(ay * sh, half_h), sh - half_h)
    th = math.radians(rot)
    a, b = math.cos(th) / s, math.sin(th) / s
    d, e = -math.sin(th) / s, math.cos(th) / s
    c = cx - a * out_w / 2 - b * out_h / 2
    f = cy - d * out_w / 2 - e * out_h / 2
    img = Image.fromarray(src).transform((out_w, out_h), Image.AFFINE, (a, b, c, d, e, f),
                                         resample=Image.BICUBIC)
    return np.asarray(img).astype(np.float32) / 255


# ---------------------------------------------------------------- grading ---

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.46) / (H * 0.62)) ** 2)
VIGNETTE = (1 - 0.30 * np.clip(_r, 0, 1.6) ** 2.2)[..., None]
RNG = np.random.default_rng(7)


def grade(f, gain=None, neutral_whites=False, exposure=1.0):
    f = f * exposure
    if gain is not None:
        m = wall_mask(f)[..., None]
        f = f * (1 - m) + f * gain * m
    if neutral_whites:
        lum = f.mean(-1, keepdims=True)
        sat = f.max(-1, keepdims=True) - f.min(-1, keepdims=True)
        w = np.clip((lum - 0.62) / 0.2, 0, 1) * np.clip((0.16 - sat) / 0.08, 0, 1) * 0.75
        f = f * (1 - w) + lum * w
    # gentle filmic contrast with a warm highlight roll-off
    f = np.clip(f, 0, 1)
    f = f + 0.06 * (f - 0.5) * (1 - np.abs(2 * f - 1))
    lum = f.mean(-1, keepdims=True)
    f = f + (lum ** 2) * np.array([0.012, 0.0, -0.014], np.float32)
    f = 0.012 + f * 0.985
    return f


def finish(f):
    f = f * VIGNETTE
    g = RNG.standard_normal((H // 2, W // 2), dtype=np.float32)
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
    lum = f.mean(-1, keepdims=True)
    f = f + g * 0.022 * (0.35 + 0.65 * (1 - np.abs(2 * lum - 1)))
    return np.clip(f, 0, 1)


def hblur(f, px):
    """Continuous horizontal box blur of about px pixels (edge-padded)."""
    k = int(round(px))
    if k < 2:
        return f
    pad = k // 2 + 1
    p = np.pad(f, ((0, 0), (pad, pad), (0, 0)), mode="edge")
    c = np.cumsum(p, axis=1, dtype=np.float32)
    c = np.concatenate([np.zeros_like(c[:, :1]), c], axis=1)
    start = pad - k // 2
    return (c[:, start + k:start + k + W] - c[:, start:start + W]) / k


def hshift(f, px):
    if px == 0:
        return f
    p = abs(px)
    padded = np.pad(f, ((0, 0), (p, p), (0, 0)), mode="edge")
    return padded[:, p - px:p - px + W]


def rgb_split(f, px):
    if px < 1:
        return f
    out = f.copy()
    p = int(px)
    out[:, p:, 0] = f[:, :-p, 0]
    out[:, :-p, 2] = f[:, p:, 2]
    return out


# ------------------------------------------------------------------- text ---

def font(path, size):
    return ImageFont.truetype(path, size)


def text_layer(lines, anchor="ls"):
    """lines: list of (text, font_path, size, tracking_em, x, y, align). Returns RGBA float."""
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    for text, fp, size, track, x, y, align in lines:
        fnt = font(fp, size)
        widths = [d.textlength(ch, font=fnt) for ch in text]
        total = sum(widths) + track * size * (len(text) - 1)
        if align == "center":
            cx = x - total / 2
        elif align == "right":
            cx = x - total
        else:
            cx = x
        for ch, wch in zip(text, widths):
            d.text((cx, y), ch, font=fnt, fill=255, anchor=anchor)
            cx += wch + track * size
    return np.asarray(img).astype(np.float32)[..., None] / 255


def over(f, alpha, color=CREAM, opacity=1.0):
    a = alpha * opacity
    return f * (1 - a) + color * a


def shade(f, y0, y1, strength):
    """Darken a vertical band that fades in from y0 to full at y1 (for text legibility)."""
    ramp = np.clip((yy[:, :1] - y0) / max(y1 - y0, 1), 0, 1)[..., None]
    return f * (1 - strength * ramp)


LOGO = np.asarray(Image.open(os.path.join(ROOT, "assets", "brand", "basic-logo-cream.png")).convert("RGBA"))


def logo_layer(width, cx, cy, scale=1.0, blur=0.0):
    img = Image.fromarray(LOGO)
    w = int(width * scale)
    h = int(LOGO.shape[0] * w / LOGO.shape[1])
    img = img.resize((w, h), Image.LANCZOS)
    if blur > 0.3:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.GaussianBlur(blur))
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(img, (int(cx - w / 2), int(cy - h / 2)), img)
    arr = np.asarray(canvas).astype(np.float32) / 255
    return arr[..., :3], arr[..., 3:]


# ----------------------------------------------------------------- timeline ---

# kind, beats [b0, b1), params
SHOTS = [
    dict(kind="intro", b=(0, 2)),
    dict(kind="clip", name="S1-black-01-wide", b=(2, 4), s_in=0.35, speed=1.12, ramp=0.35,
         z=(1.03, 1.09), a=(0.5, 0.40), act=1, color="Noir"),
    dict(kind="clip", name="S1-black-02-close", b=(4, 5), s_in=1.0, speed=1.25, z=(1.02, 1.06),
         a=(0.5, 0.55), act=1, color="Noir"),
    dict(kind="clip", name="S1-white-01-wide", b=(5, 7), s_in=0.05, speed=1.08, ramp=0.3,
         z=(1.22, 1.26), a=(0.62, 0.44), act=1, color="Blanc", whites=True),
    dict(kind="still", src="omni-crops/S1-white-02-close-crop2.jpg", b=(7, 8), z=(1.02, 1.10),
         a=(0.5, 0.55), drift=(0, -30), act=1, color="Blanc", whites=True, shutter=True),
    dict(kind="still", src="approved/S1-sand-01-wide.jpg", b=(8, 10), z=(1.08, 1.16),
         a=(0.5, 0.36), rot=(2.5, 0.0), act=1, color="Sable", sweep=True, shutter=True),
    dict(kind="still", src="omni-crops/S1-sand-02-close-crop.jpg", b=(10, 11), z=(1.02, 1.09),
         a=(0.45, 0.5), drift=(-25, 0), act=1, color="Sable", shutter=True),
    dict(kind="clip", name="S2-black-01-wide", b=(11, 13), s_in=2.35, speed=1.2,
         z=(1.15, 1.17), a=(0.5, 0.0), act=2, color="Noir"),
    dict(kind="clip", name="S2-black-02-close", b=(13, 14), s_in=0.9, speed=1.3, z=(1.02, 1.06),
         a=(0.5, 0.5), act=2, color="Noir"),
    dict(kind="clip", name="S2-white-01-wide", b=(14, 16), s_in=2.55, speed=1.1,
         z=(1.12, 1.14), a=(0.45, 0.0), act=2, color="Blanc", whites=True),
    dict(kind="clip", name="S2-white-02-close", b=(16, 17), s_in=1.15, speed=1.4, z=(1.02, 1.05),
         a=(0.5, 0.5), act=2, color="Blanc", whites=True),
    dict(kind="clip", name="S2-latte-01-wide", b=(17, 19), s_in=2.0, speed=1.28, z=(1.02, 1.07),
         a=(0.5, 0.42), act=2, color="Latte"),
    dict(kind="clip", name="S2-latte-02-close", b=(19, 21), s_in=2.12, speed=1.4, z=(1.0, 1.03),
         a=(0.5, 0.5), act=2, color="Latte"),
    dict(kind="split", b=(21, 24)),
    dict(kind="logo", b=(24, 27)),
]

WHIPS = {7: +1, 10: -1, 16: +1, 19: -1}     # cut beat -> direction
FLASHES = {2: 1.0, 11: 0.9, 21: 0.7, 24: 0.8}
SPLITS = {11: 14, 21: 8}                     # RGB split px at cut
ACT_TITLES = {1: "01 — CARACO & CYCLISTE", 2: "02 — T-SHIRT & CORSAIRE"}

SPLIT_PANELS = [  # (left still, x anchor, label), (right still, x anchor, label)
    (("approved/S1-black-01-wide.jpg", 0.50, "Noir"), ("approved/S2-black-01-wide.jpg", 0.53, "Noir")),
    (("approved/S1-white-01-wide.jpg", 0.58, "Blanc"), ("approved/S2-white-01-wide.jpg", 0.40, "Blanc")),
    (("approved/S1-sand-01-wide.jpg", 0.52, "Sable"), ("approved/S2-latte-01-wide.jpg", 0.46, "Latte")),
]


# -------------------------------------------------------------- renderers ---

def act_text_layers():
    layers = {}
    for act, title in ACT_TITLES.items():
        layers[("title", act)] = text_layer([(title, INTER_MED, 29, 0.32, 84, 1352, "left")])
    for word in ["Noir", "Blanc", "Sable", "Latte"]:
        layers[("color", word)] = text_layer([(word, SERIF, 96, 0.0, 80, 1462, "left")])
    layers["rule"] = None
    return layers


def draw_rule(f, x0, y, length, opacity, thick=2):
    if length <= 0 or opacity <= 0:
        return f
    f[y:y + thick, int(x0):int(x0 + length)] = (
        f[y:y + thick, int(x0):int(x0 + length)] * (1 - opacity) + CREAM * opacity)
    return f


def render_intro(i, n, cache):
    t = i / FPS
    u = i / max(n - 1, 1)
    plate = cache.setdefault("plate", load_still("background-plate.jpg"))
    f = transform(plate, 1.12 - 0.06 * ease_in_out(u), 0.5, 0.45)
    f = grade(f * 0.62)
    l1 = cache.setdefault("intro1", text_layer([("NOUVELLE COLLECTION", INTER_MED, 30, 0.55, W / 2, 870, "center")]))
    l2 = cache.setdefault("intro2", text_layer([("Deux ensembles. Trois teintes.", SERIF, 76, 0.0, W / 2, 1000, "center")]))
    # flicker-in of the kicker, soft fade of the serif line on beat 1
    fl = 0.0
    if t > 0.12:
        fl = 1.0 if (t > 0.42 or int(t * 30) % 3) else 0.25
    f = over(f, l1, opacity=fl * 0.9)
    o2 = ease_out((t - beat(1)) / 0.35)
    f = over(f, l2, opacity=max(0.0, o2))
    f = draw_rule(f, W / 2 - 40, 915, 80 * ease_out((t - 0.3) / 0.5), 0.7)
    return f


def render_clip(shot, i, n, cache):
    frames = cache.get(shot["name"])
    if frames is None:
        cache.clear_clips()
        frames = cache[shot["name"]] = load_clip(shot["name"])
        cache["gain_" + shot["name"]] = wall_gain(frames[len(frames) // 2])
    dur = n / FPS
    t = i / FPS
    u = i / max(n - 1, 1)
    src_t = shot["s_in"] + t * shot["speed"]
    if shot.get("ramp"):
        src_t += shot["ramp"] * dur * max(0.0, (u - 0.7) / 0.3) ** 2
    pos = min(src_t * 24, len(frames) - 1.001)
    k = int(pos)
    w = pos - k
    src = frames[k] if w < 0.02 else (frames[k] * (1 - w) + frames[k + 1] * w).astype(np.uint8)
    z0, z1 = shot["z"]
    f = transform(src, z0 + (z1 - z0) * ease_in_out(u), *shot["a"])
    return grade(f, gain=cache.get("gain_" + shot["name"]), neutral_whites=shot.get("whites", False))


def render_still(shot, i, n, cache):
    img = cache.setdefault(shot["src"], load_still(shot["src"]))
    u = i / max(n - 1, 1)
    e = ease_in_out(u)
    z0, z1 = shot["z"]
    ax, ay = shot["a"]
    dx, dy = shot.get("drift", (0, 0))
    sh, sw = img.shape[:2]
    ax += dx * e / sw
    ay += dy * e / sh
    r0, r1 = shot.get("rot", (0.0, 0.0))
    f = transform(img, z0 + (z1 - z0) * e, ax, ay, rot=r0 + (r1 - r0) * e)
    key = "gain_" + shot["src"]
    if key not in cache:
        cache[key] = wall_gain(img)
    f = grade(f, gain=cache[key], neutral_whites=shot.get("whites", False))
    if shot.get("sweep"):
        # soft diagonal light sweep travelling across the frame
        pos = -0.4 + 1.8 * e
        band = np.exp(-(((xx / W) * 0.6 + (yy / H) * 0.4 - pos) / 0.12) ** 2)[..., None]
        f = f + band * 0.07 * np.array([1.0, 0.86, 0.74], np.float32)
    return f


def render_split(i, n, cache):
    t = i / FPS
    seg = min(int(t / PERIOD), 2)
    lt = t - seg * PERIOD
    u = lt / PERIOD
    f = np.zeros((H, W, 3), np.float32)
    for side, (rel, ax, _label) in enumerate(SPLIT_PANELS[seg]):
        img = cache.setdefault(rel, load_still(rel))
        z = 1.04 + 0.03 * u
        panel = transform(img, z, ax, 0.42, out_w=W // 2, out_h=H)
        key = "gain_" + rel
        if key not in cache:
            cache[key] = wall_gain(img)
        f[:, side * (W // 2):(side + 1) * (W // 2)] = grade(panel, gain=cache[key], neutral_whites=(seg == 1))
    f = shade(f, 1180, 1560, 0.45)
    # divider line
    f[:, W // 2 - 1:W // 2 + 1] = f[:, W // 2 - 1:W // 2 + 1] * 0.3 + CREAM * 0.7
    top = cache.setdefault("split_top", text_layer([
        ("CARACO & CYCLISTE", INTER_MED, 22, 0.3, W * 0.25, 1395, "center"),
        ("T-SHIRT & CORSAIRE", INTER_MED, 22, 0.3, W * 0.75, 1395, "center")]))
    f = over(f, top, opacity=0.9)
    lw = cache.setdefault(("split_word", seg), text_layer([
        (SPLIT_PANELS[seg][0][2], SERIF, 84, 0.0, W * 0.25, 1500, "center"),
        (SPLIT_PANELS[seg][1][2], SERIF, 84, 0.0, W * 0.75, 1500, "center")]))
    f = over(f, lw, opacity=ease_out(lt / 0.18))
    return f


def render_logo(i, n, cache):
    t = i / FPS
    u = i / max(n - 1, 1)
    plate = cache.setdefault("plate", load_still("background-plate.jpg"))
    f = transform(plate, 1.0 + 0.05 * ease_in_out(u), 0.5, 0.45)
    f = grade(f * 0.78)
    a = ease_out(t / 0.55)
    rgb, al = logo_layer(640, W / 2, 820, scale=1.06 - 0.06 * a, blur=6 * (1 - a))
    f = f * (1 - al * a) + rgb * al * a
    tag = cache.setdefault("tagline", text_layer([("L’essentiel, pensé avec soin.", SERIF, 64, 0.0, W / 2, 1075, "center")]))
    f = over(f, tag, opacity=max(0.0, ease_out((t - beat(1)) / 0.4)))
    cta = cache.setdefault("cta", text_layer([("DÉCOUVREZ LA COLLECTION", INTER_MED, 26, 0.45, W / 2, 1230, "center")]))
    oc = max(0.0, ease_out((t - beat(1.75)) / 0.4))
    f = over(f, cta, opacity=oc * 0.9)
    f = draw_rule(f, W / 2 - 30, 1172, 60 * oc, 0.6)
    return f


class Cache(dict):
    def clear_clips(self):
        for k in [k for k, v in self.items() if isinstance(v, np.ndarray) and v.ndim == 4]:
            del self[k]


def render_video(path):
    cache = Cache()
    act_layers = act_text_layers()
    cuts = [nframes(beat(s["b"][0])) for s in SHOTS] + [nframes(beat(TOTAL_BEATS))]
    total = cuts[-1]
    beat_frames = {k: nframes(beat(k)) for k in range(TOTAL_BEATS + 1)}
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium" if PREVIEW else "slow",
         "-crf", "22" if PREVIEW else "15", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path],
        stdin=subprocess.PIPE)
    prev_word = {}
    for si, shot in enumerate(SHOTS):
        f0, f1 = cuts[si], cuts[si + 1]
        n = f1 - f0
        for i in range(n):
            g = f0 + i
            kind = shot["kind"]
            if kind == "intro":
                f = render_intro(i, n, cache)
            elif kind == "clip":
                f = render_clip(shot, i, n, cache)
            elif kind == "still":
                f = render_still(shot, i, n, cache)
            elif kind == "split":
                f = render_split(i, n, cache)
            else:
                f = render_logo(i, n, cache)

            # whip-pan transitions on the beat grid (before text, so labels stay crisp)
            for kb, d in WHIPS.items():
                fb = beat_frames[kb]
                off = g - fb
                if -3 <= off < 3:
                    amt = (1 - abs(off + 0.5) / 3.5)
                    f = hblur(f, 140 * amt)
                    shift = int(d * 60 * amt * (1 if off < 0 else -1))
                    f = hshift(f, shift)
            # act labels (bottom-left, inside the Reels safe zone)
            if "act" in shot:
                act = shot["act"]
                act_start = min(cuts[j] for j, s in enumerate(SHOTS) if s.get("act") == act)
                act_end = max(cuts[j + 1] for j, s in enumerate(SHOTS) if s.get("act") == act)
                f = shade(f, 1150, 1560, 0.38)
                ta = ease_out((g - act_start) / 8) * min(1.0, (act_end - g) / 3)
                f = over(f, act_layers[("title", act)], opacity=0.92 * ta)
                f = draw_rule(f, 84, 1378, 120 * ease_out((g - act_start) / 10), 0.7 * ta)
                word = shot["color"]
                first = min(cuts[j] for j, s in enumerate(SHOTS) if s.get("act") == act and s.get("color") == word)
                wa = ease_out((g - first) / 5) * min(1.0, (act_end - g) / 3)
                last_same = max(cuts[j + 1] for j, s in enumerate(SHOTS) if s.get("act") == act and s.get("color") == word)
                wa *= min(1.0, (last_same - g) / 2) if last_same < act_end else 1.0
                f = over(f, act_layers[("color", word)], opacity=wa)

            for kb, px in SPLITS.items():
                off = g - beat_frames[kb]
                if 0 <= off < 4:
                    f = rgb_split(f, px * (1 - off / 4))
            for kb, amp in FLASHES.items():
                off = g - beat_frames[kb]
                if 0 <= off < 6:
                    a = amp * math.exp(-off / 1.6)
                    f = f * (1 - a * 0.85) + np.array([1.0, 0.95, 0.9], np.float32) * a * 0.85
            # tiny exposure "pump" on every downbeat
            for kb in range(2, TOTAL_BEATS, 4):
                off = g - beat_frames[kb]
                if 0 <= off < 3:
                    f = f * (1 + 0.05 * (1 - off / 3))
            f = finish(f)
            enc.stdin.write((f * 255 + 0.5).astype(np.uint8).tobytes())
        print(f"shot {si:2d} {shot.get('name', shot.get('src', shot['kind']))}: frames {f0}-{f1}", flush=True)
    enc.stdin.close()
    enc.wait()
    return total


# ------------------------------------------------------------------ audio ---

def onepole_lp(x, cutoff):
    """Time-varying one-pole low-pass; cutoff is an array (Hz) or scalar."""
    cutoff = np.broadcast_to(np.asarray(cutoff, np.float64), x.shape)
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def sfx_track(duration):
    n = int(duration * SR)
    out = np.zeros(n, np.float64)
    rng = np.random.default_rng(3)

    def place(sig, t, gain=1.0):
        s = int(t * SR)
        e = min(n, s + len(sig))
        if s < n and e > s:
            out[s:e] += sig[:e - s] * gain

    # riser over the intro (beats 0 -> 2), cut dead on the drop
    rl = beat(2)
    tt = np.arange(int(rl * SR)) / SR
    noise = rng.standard_normal(len(tt))
    riser = onepole_lp(noise, 300 + 6000 * (tt / rl) ** 2) * (tt / rl) ** 2.2
    riser += 0.25 * np.sin(2 * np.pi * np.cumsum(180 + 700 * (tt / rl) ** 2) / SR) * (tt / rl) ** 3
    place(riser * 0.5, 0.0)

    def boom():
        L = int(1.6 * SR)
        t = np.arange(L) / SR
        freq = 38 + 40 * np.exp(-t * 9)
        body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 2.6)
        click = onepole_lp(rng.standard_normal(L), 2500) * np.exp(-t * 90)
        return body * 0.9 + click * 0.5

    for k in (2, 24):
        place(boom(), beat(k), 0.85)

    def whoosh(length=0.42):
        L = int(length * SR)
        t = np.arange(L) / SR
        env = np.sin(np.pi * t / length) ** 2
        cut = 400 + 5000 * np.sin(np.pi * t / length) ** 3
        return onepole_lp(rng.standard_normal(L), cut) * env

    for k in WHIPS:
        place(whoosh(), beat(k) - 0.24, 0.55)
    place(whoosh(0.5), beat(21) - 0.3, 0.4)

    # glitch stutter on the act break
    for j in range(3):
        L = int(0.05 * SR)
        t = np.arange(L) / SR
        sq = np.sign(np.sin(2 * np.pi * (220 + 160 * j) * t)) * np.exp(-t * 30)
        sq = np.round(sq * 6) / 6
        place(sq * 0.18, beat(11) + j * 0.065)

    def shutter():
        L = int(0.09 * SR)
        t = np.arange(L) / SR
        hp = rng.standard_normal(L)
        hp = hp - onepole_lp(hp, 1800)
        env = np.exp(-t * 160) + 0.7 * np.exp(-np.maximum(t - 0.045, 0) * 170) * (t > 0.045)
        return hp * env

    for s in SHOTS:
        if s.get("shutter"):
            place(shutter(), beat(s["b"][0]) + 0.02, 0.35)

    def tick():
        L = int(0.03 * SR)
        t = np.arange(L) / SR
        return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 160)

    for k in (1, 2, 11, 25, 25.75):
        place(tick(), beat(k), 0.12)
    return out.astype(np.float32)


def write_wav(path, mono):
    st = np.clip(np.stack([mono, mono], 1), -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())


def main():
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, ".tmp")
    os.makedirs(tmp, exist_ok=True)
    video = os.path.join(tmp, "video.mp4")
    total_frames = render_video(video)
    duration = total_frames / FPS
    sfx = os.path.join(tmp, "sfx.wav")
    write_wav(sfx, sfx_track(duration))
    music = os.path.join(AD, "audio", "nightcall.mp3")
    fade = 1.4
    common = ["-map", "0:v", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
              "-movflags", "+faststart", "-shortest"]
    with_music = os.path.join(OUT, "BASIC-burgundy-ad-avec-musique.mp4")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", video, "-ss", str(MUSIC_T0), "-t", str(duration), "-i", music,
         "-i", sfx, "-filter_complex",
         f"[1:a]aresample=48000,afade=t=in:d=0.25,afade=t=out:st={duration - fade}:d={fade},volume=1.0[m];"
         f"[2:a]volume=0.8[s];[m][s]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
         "-map", "[a]", *common, with_music], check=True)
    no_music = os.path.join(OUT, "BASIC-burgundy-ad-sans-musique.mp4")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", video, "-i", sfx, "-filter_complex",
         f"[1:a]afade=t=out:st={duration - fade}:d={fade},loudnorm=I=-18:TP=-1.5[a]",
         "-map", "[a]", *common, no_music], check=True)
    print("wrote", with_music, "and", no_music, f"({duration:.2f}s)")


if __name__ == "__main__":
    main()
