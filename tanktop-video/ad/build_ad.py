"""BASIC Essentials - 12.6 s vertical ad (1080x1920, 30 fps).

Every cut sits on a 100 BPM grid (1 beat = 18 frames, a 16th = 4.5 frames),
so any 100 BPM track added in Reels/TikTok lands on the edits.

  1. Palette hook   0.0-2.4 s  four colour flashes, one per beat
  2. Split-cut      2.4-7.2 s  full-screen lookbook, bottom-then-top cuts,
                               half-beat cuts then 16ths, crossing models
  3. Offer          7.2-9.6 s  "1 + 1 = 3" builds on the beat, third tank free
  4. End card       9.6-12.6 s hero shot, glass colour cards, logo

Usage: python3 build_ad.py            -> out/basic_ad_9x16.mp4
       python3 build_ad.py 30 150 300 -> stills of those frames in out/stills/
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # tanktop-video/
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
import build as lookbook  # noqa: E402

W, H, FPS = 1080, 1920, 30
BEAT = 18  # frames per beat at 100 BPM
S1, S2, S3, S4, END = 0, 4 * BEAT, 12 * BEAT, 16 * BEAT, 21 * BEAT

COL = {
    "ivoire": (239, 232, 220),
    "sable": (216, 189, 158),
    "chocolat": (78, 48, 34),
    "noir": (24, 23, 22),
}
CREAM = (244, 238, 230)
DEEP = (33, 22, 16)
GREIGE = (154, 140, 128)
ORDER = ["ivoire", "sable", "chocolat", "noir"]
PRODUCT = {"ivoire": "white.png", "sable": "beige.png", "chocolat": "brown.png", "noir": "black.png"}
LOOKBOOK_NAME = {"ivoire": "ivory", "sable": "sand", "chocolat": "chocolate", "noir": "black"}


# ---------------------------------------------------------------- helpers

def ease_out(p, k=3):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** k


def ease_in_out(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def ease_back(p, s=1.6):
    p = min(max(p, 0.0), 1.0) - 1
    return p * p * ((s + 1) * p + s) + 1


def ramp(t, start, length):
    return min(max((t - start) / length, 0.0), 1.0)


_fonts = {}


def font(name, size):
    key = (name, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(HERE, "fonts", name), size)
    return _fonts[key]


SERIF = "InstrumentSerif-Regular.ttf"
SERIF_IT = "InstrumentSerif-Italic.ttf"
SANS = "Inter-Regular.ttf"
SANS_MED = "Inter-Medium.ttf"
SANS_LIGHT = "Inter-Light.ttf"
MONO = "IBMPlexMono-Regular.ttf"


def text(layer, xy, s, f, fill, alpha=1.0, anchor="ls", tracking=0):
    """Draw text on an RGBA layer; tracking in px spreads the letters."""
    if alpha <= 0:
        return
    d = ImageDraw.Draw(layer)
    rgba = tuple(fill[:3]) + (int(255 * alpha),)
    if not tracking:
        d.text(xy, s, font=f, fill=rgba, anchor=anchor)
        return
    width = sum(f.getlength(c) for c in s) + tracking * (len(s) - 1)
    x, y = xy
    if anchor[0] == "m":
        x -= width / 2
    elif anchor[0] == "r":
        x -= width
    for c in s:
        d.text((x, y), c, font=f, fill=rgba, anchor="l" + anchor[1])
        x += f.getlength(c) + tracking


def over(base, layer):
    return Image.alpha_composite(base, layer)


def paste_rgba(base, img, cx, cy, alpha=1.0):
    """Composite an RGBA image centred at (cx, cy) with extra opacity."""
    if alpha <= 0:
        return base
    if alpha < 1:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(img, (int(round(cx - img.width / 2)), int(round(cy - img.height / 2))), img)
    return Image.alpha_composite(base, layer)


def rounded_mask(w, h, r, ss=4):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- assets

class Tanks:
    """Product cutouts, trimmed, resized on demand, with soft floor shadows."""

    def __init__(self):
        self.src = {}
        for name, f in PRODUCT.items():
            im = Image.open(os.path.join(REPO, "assets", "products", f)).convert("RGBA")
            self.src[name] = im.crop(im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
        self.cache = {}

    def get(self, name, height):
        key = (name, int(height))
        if key not in self.cache:
            im = self.src[name]
            h = max(int(height), 2)
            self.cache[key] = im.resize((max(int(im.width * h / im.height), 1), h), Image.LANCZOS)
        return self.cache[key]

    def shadow(self, name, height, blur=28, opacity=0.38):
        key = ("shadow", name, int(height), blur)
        if key not in self.cache:
            im = self.get(name, height)
            pad = blur * 3
            a = Image.new("L", (im.width + 2 * pad, im.height + 2 * pad), 0)
            a.paste(im.getchannel("A"), (pad, pad))
            a = a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * opacity))
            sh = Image.new("RGBA", a.size, (10, 6, 4, 0))
            sh.putalpha(a)
            self.cache[key] = sh
        return self.cache[key]

    def draw(self, base, name, height, cx, cy, alpha=1.0, shadow=True):
        if shadow:
            base = paste_rgba(base, self.shadow(name, height), cx, cy + height * 0.035, alpha)
        return paste_rgba(base, self.get(name, height), cx, cy, alpha)


def load_logo(width, color=CREAM):
    a = Image.open(os.path.join(HERE, "assets", "logo_basic_alpha.png")).convert("L")
    a = a.resize((width, round(a.height * width / a.width)), Image.LANCZOS)
    im = Image.new("RGBA", a.size, color + (0,))
    im.putalpha(a)
    return im


def lookbook_pages():
    """Split-cut pages from the lookbook pipeline, re-framed full screen:
    head near 12% from the top (clear of the Reels header), waist cut at 61%."""
    lookbook.PAGE_W, lookbook.PAGE_H = W, H
    lookbook.SEAM, lookbook.HEAD_MARGIN = 0.61, 230
    pages = {}
    for m in ("A", "B"):
        for (look, half), page in lookbook.model_pages(m).items():
            pages[(m, look, half)] = page.astype(np.uint8)
    return pages, round(lookbook.SEAM * H)


def radial(color, strength=0.10, cy=0.42):
    """Flat colour with a soft studio spot so fields don't look digital."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = ((x - W / 2) / W) ** 2 + ((y - H * cy) / (H * 0.8)) ** 2
    g = 1 + strength * np.exp(-r * 3.2) - strength * 0.6
    return Image.fromarray(np.clip(np.array(color, np.float32) * g[..., None], 0, 255).astype(np.uint8)).convert("RGBA")


# ---------------------------------------------------------------- scenes

# (tank colour, background colour) - dark and light fields alternate
HOOK = [("ivoire", "chocolat"), ("chocolat", "ivoire"), ("sable", "noir"), ("noir", "sable")]


def scene_hook(f, tanks, bgs):
    i, t = divmod(f - S1, BEAT)
    tank, bg = HOOK[i]
    frame = bgs[bg].copy()
    light_bg = bg in ("ivoire", "sable")
    ink = DEEP if light_bg else CREAM

    p = ease_out(t / 12)
    frame = tanks.draw(frame, tank, 1010 * (1.07 - 0.07 * p), 540, 840 + 40 * (1 - p))

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text(lay, (72, 170), f"0{i + 1} / 04", font(MONO, 30), ink, 0.8)
    text(lay, (W - 72, 170), "DÉBARDEUR COL MONTANT", font(SANS_MED, 24), ink, 0.8, anchor="rs", tracking=5)
    q = ease_out(t / 9)
    # the pairs are chosen so the tank's own colour always reads on its field
    text(lay, (540, 1600 + 60 * (1 - q)), tank, font(SERIF_IT, 250), COL[tank], min(t / 4, 1), anchor="ms")
    return over(frame, lay)


def split_schedule(pages):
    """Rolling bottom-then-top looks. Half-beat cuts for two bars, then
    16ths while the models alternate - the build before the offer."""
    targets = [("A", "chocolat"), ("A", "ivoire"), ("A", "noir"), ("B", "sable"),
               ("B", "chocolat"), ("B", "ivoire"), ("B", "noir"), ("A", "sable"),
               ("B", "chocolat"), ("A", "ivoire"), ("B", "noir"), ("A", "sable")]
    frames = [S2 + 9 * k for k in range(1, 9)]  # 81 ... 144
    k = 1
    while True:
        fr = 8 * BEAT + int(4.5 * k)
        if fr >= S3:
            break
        frames.append(fr)
        k += 1
    cuts = []
    for n, fr in enumerate(frames):
        m, look = targets[n // 2]
        cuts.append((fr, "bot" if n % 2 == 0 else "top", (m, look)))
    return ("A", "sable"), cuts


def scene_split(f, pages, seam, sched, logo_small, grad):
    start, cuts = sched
    top = bot = start
    count = 0
    for fr, half, look in cuts:
        if fr <= f:
            count += 1
            if half == "top":
                top = look
            else:
                bot = look
    arr = np.empty((H, W, 3), np.uint8)
    arr[:seam] = pages[(top[0], LOOKBOOK_NAME[top[1]], "top")][:seam]
    arr[seam:] = pages[(bot[0], LOOKBOOK_NAME[bot[1]], "bot")][seam:]
    frame = over(Image.fromarray(arr).convert("RGBA"), grad)

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.paste(logo_small, (72, 150), logo_small)
    text(lay, (W - 72, 200), f"N°{count + 1:03d}", font(MONO, 30), CREAM, 0.9, anchor="rs")
    text(lay, (68, 1560), top[1], font(SERIF_IT, 170), CREAM, 1.0)
    text(lay, (74, 1625), "DÉBARDEUR COL MONTANT", font(SANS_MED, 26), CREAM, 0.85, tracking=6)
    return over(frame, lay)


def scene_offer(f, tanks, bg):
    t = f - S3
    frame = bg.copy()
    xs = [220, 540, 860]
    flash = max(0.0, 1 - t / 4) * 0.55  # cream hit on the downbeat
    trio = ["sable", "chocolat", "noir"]
    enters = [0, BEAT, 2 * BEAT]
    for x, name, e in zip(xs, trio, enters):
        if t < e:
            continue
        p = (t - e) / 10
        if name == "noir":  # the free one drops in from above
            y = 1030 - 520 * (1 - ease_back(p, 2.2))
        else:
            y = 1030 + 140 * (1 - ease_back(p))
        frame = tanks.draw(frame, name, 440, x, y, min((t - e) / 4, 1))

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    big = font(SERIF, 240)
    tokens = [("1", 220, 0), ("+", 380, BEAT), ("1", 540, BEAT), ("=", 700, 2 * BEAT)]
    for s, x, e in tokens:
        if t >= e:
            q = ease_out((t - e) / 7)
            text(lay, (x, 720 + 50 * (1 - q)), s, big, CREAM, min((t - e) / 3, 1), anchor="ms")
    e3 = 2 * BEAT + 9
    if t >= e3:
        q = ease_back((t - e3) / 8, 2.4)
        s = max(0.01, 0.6 + 0.4 * q)
        g = font(SERIF, max(int(240 * s), 8))
        text(lay, (860, 720), "3", g, CREAM, min((t - e3) / 2, 1), anchor="ms")

    names = font(SERIF_IT, 46)
    for x, name, e in zip(xs, trio, enters):
        if t >= e + 4:
            text(lay, (x, 1325), name, names, CREAM, min((t - e - 4) / 5, 1) * 0.9, anchor="ms")
    e4 = 3 * BEAT
    if t >= e4:
        q = ease_out((t - e4) / 8)
        d = ImageDraw.Draw(lay)
        d.line((540 - 40 * q, 1398, 540 + 40 * q, 1398), fill=CREAM + (200,), width=2)
        text(lay, (540, 1475 + 20 * (1 - q)), "LE TROISIÈME EST OFFERT", font(SANS_MED, 40), CREAM,
             q, anchor="ms", tracking=10)
    frame = over(frame, lay)

    if t >= e3:  # "offert" badge on the free tank
        q = ease_back((t - e3) / 8, 2.0)
        badge = make_badge()
        bw = max(int(badge.width * q), 2)
        b = badge.resize((bw, max(int(badge.height * q), 2)), Image.LANCZOS)
        frame = paste_rgba(frame, b, 930, 832)
    if flash > 0:
        frame = Image.blend(frame, Image.new("RGBA", (W, H), CREAM + (255,)), flash)
    return frame


_badge = None


def make_badge():
    global _badge
    if _badge is None:
        ss = 3
        f = font(SANS_MED, 30 * ss)
        label = "OFFERT"
        tw = sum(f.getlength(c) for c in label) + 6 * ss * (len(label) - 1)
        w, h = int(tw + 64 * ss), 64 * ss
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=CREAM + (255,))
        text(im, (w / 2, h / 2 + 1), label, f, DEEP, anchor="mm", tracking=6 * ss)
        im = im.resize((w // ss, h // ss), Image.LANCZOS).rotate(-8, resample=Image.BICUBIC, expand=True)
        _badge = im
    return _badge


class EndCard:
    CW, CH, GAP, TOP = 190, 250, 18, 1080

    def __init__(self, tanks):
        self.tanks = tanks
        plate = Image.open(os.path.join(HERE, "assets", "hero_sable.png")).convert("RGB")
        self.plate = plate
        y = np.linspace(0, 1, H, dtype=np.float32)
        a = np.clip((y - 0.42) / 0.58, 0, 1)
        a = (a * a * (3 - 2 * a)) * 0.86
        g = np.zeros((H, W, 4), np.uint8)
        g[..., :3] = DEEP
        g[..., 3] = (a[:, None] * 255).astype(np.uint8)
        self.grad = Image.fromarray(g, "RGBA")
        self.mask = rounded_mask(self.CW, self.CH, 28)
        self.x0 = (W - (4 * self.CW + 3 * self.GAP)) // 2
        # card shadow
        pad = 40
        sm = Image.new("L", (self.CW + 2 * pad, self.CH + 2 * pad), 0)
        sm.paste(self.mask, (pad, pad))
        sm = sm.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.35))
        self.shadow = Image.new("RGBA", sm.size, (8, 5, 3, 0))
        self.shadow.putalpha(sm)
        ring = Image.new("L", (self.CW * 4, self.CH * 4), 0)
        ImageDraw.Draw(ring).rounded_rectangle((2, 2, self.CW * 4 - 3, self.CH * 4 - 3), 120, outline=255, width=6)
        self.ring = ring.resize((self.CW, self.CH), Image.LANCZOS)
        hl = np.zeros((self.CH, self.CW), np.float32)
        hl[:] = np.clip(1 - np.linspace(0, 1, self.CH)[:, None] / 0.45, 0, 1)
        self.highlight = hl * 0.16
        self.logo = load_logo(360)

    def plate_at(self, t):
        s = 1 + 0.06 * ease_in_out(t / (END - S4))
        w, h = W / s, H / s
        cx, cy = 540, 760
        box = (cx - w / 2, cy - h * (760 / H), cx + w / 2, cy - h * (760 / H) + h)
        return self.plate.resize((W, H), Image.LANCZOS, box=box).convert("RGBA")

    def card(self, frame, name, x, y, alpha):
        x, y = int(x), int(y)
        pad = 50
        region = frame.crop((x - pad, y - pad, x + self.CW + pad, y + self.CH + pad)).convert("RGB")
        blur = region.filter(ImageFilter.GaussianBlur(22)).crop((pad, pad, pad + self.CW, pad + self.CH))
        g = np.asarray(blur).astype(np.float32)
        g = g * 0.86 + 255 * 0.14
        g = g + (255 - g) * self.highlight[..., None]
        ring = np.asarray(self.ring).astype(np.float32)[..., None] / 255 * 0.45
        g = g * (1 - ring) + 255 * ring
        glass = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")
        glass.putalpha(self.mask.point(lambda v: int(v * alpha)))
        frame = paste_rgba(frame, self.shadow, x + self.CW / 2, y + self.CH / 2 + 14, alpha)
        layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        layer.paste(glass, (x, y), glass)
        frame = Image.alpha_composite(frame, layer)
        return self.tanks.draw(frame, name, 200, x + self.CW / 2, y + self.CH / 2 + 4, alpha, shadow=False)

    def render(self, f):
        t = f - S4
        frame = over(self.plate_at(t), self.grad)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        names = font(SERIF_IT, 42)
        spots = []
        for i, name in enumerate(ORDER):
            e = 6 + 3 * i
            if t < e:
                continue
            p = (t - e) / 12
            x = self.x0 + i * (self.CW + self.GAP)
            y = self.TOP + 90 * (1 - ease_back(p, 1.3))
            a = min((t - e) / 6, 1)
            frame = self.card(frame, name, x, y, a)
            spots.append((x, y))
            text(lay, (x + self.CW / 2, self.TOP + self.CH + 58), name, names, CREAM, a * 0.95, anchor="ms")

        # light sweep across the glass
        if 30 <= t <= 50 and spots:
            pos = -300 + (t - 30) / 20 * 1700
            yy, xx = np.mgrid[0:self.CH, 0:self.CW].astype(np.float32)
            arr = np.asarray(frame).astype(np.float32)
            for x, y in spots:
                x, y = int(x), int(y)
                d = (xx + x - pos) + 0.35 * (yy + y - 1200)
                k = np.exp(-(d / 46) ** 2) * 0.28 * (np.asarray(self.mask).astype(np.float32) / 255)
                sl = arr[y:y + self.CH, x:x + self.CW, :3]
                arr[y:y + self.CH, x:x + self.CW, :3] = sl + (255 - sl) * k[..., None]
            frame = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

        e = 24  # "1 + 1 = 3" pill
        if t >= e:
            q = ease_back((t - e) / 9, 1.8)
            pill = make_pill()
            s = 0.75 + 0.25 * q
            p = pill.resize((max(int(pill.width * s), 2), max(int(pill.height * s), 2)), Image.LANCZOS)
            frame = paste_rgba(frame, p, 540, 1462, min((t - e) / 4, 1))
        e = 30
        if t >= e:
            q = ease_out((t - e) / 8)
            text(lay, (540, 1548 + 16 * (1 - q)), "LE TROISIÈME EST OFFERT", font(SANS_MED, 27), CREAM,
                 q * 0.95, anchor="ms", tracking=8)
        frame = over(frame, lay)

        e = 36  # logo draws on left to right
        if t >= e:
            q = ease_in_out((t - e) / 16)
            logo = self.logo.copy()
            a = np.asarray(logo.getchannel("A")).astype(np.float32)
            edge = q * (logo.width + 120) - 60
            xs = np.arange(logo.width, dtype=np.float32)
            a *= np.clip((edge - xs) / 60, 0, 1)[None, :]
            logo.putalpha(Image.fromarray(a.astype(np.uint8)))
            frame = paste_rgba(frame, logo, 540, 1676 - 12 * (1 - q))
        e = 50
        if t >= e:
            q = ease_out((t - e) / 10)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(lay).line((540 - 22 * q, 1768, 540 + 22 * q, 1768), fill=CREAM + (int(200 * q),), width=2)
            text(lay, (540, 1812), "ESSENTIALS", font(SANS_LIGHT, 24), CREAM, q * 0.9, anchor="ms", tracking=16)
            frame = over(frame, lay)
        return frame


_pill = None


def make_pill():
    global _pill
    if _pill is None:
        ss = 3
        f = font(SANS_MED, 44 * ss)
        label = "1 + 1 = 3"
        tw = f.getlength(label)
        w, h = int(tw + 84 * ss), 82 * ss
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=CREAM + (255,))
        text(im, (w / 2, h / 2 + 2), label, f, DEEP, anchor="mm")
        _pill = im.resize((w // ss, h // ss), Image.LANCZOS)
    return _pill


# ---------------------------------------------------------------- main

def main():
    stills = [int(a) for a in sys.argv[1:]]
    tanks = Tanks()
    bgs = {c: radial(COL[c], 0.12 if c in ("chocolat", "noir") else 0.07) for c in COL}
    offer_bg = radial(GREIGE, 0.10, 0.45)
    pages, seam = lookbook_pages()
    sched = split_schedule(pages)
    y = np.linspace(0, 1, H, dtype=np.float32)
    a = np.clip((y - 0.66) / 0.34, 0, 1) ** 1.4 * 0.62
    g = np.zeros((H, W, 4), np.uint8)
    g[..., :3] = DEEP
    g[..., 3] = (a[:, None] * 255).astype(np.uint8)
    split_grad = Image.fromarray(g, "RGBA")
    top = np.clip(1 - y / 0.14, 0, 1) ** 2 * 0.35
    g2 = np.zeros((H, W, 4), np.uint8)
    g2[..., 3] = (top[:, None] * 255).astype(np.uint8)
    split_grad = Image.alpha_composite(split_grad, Image.fromarray(g2, "RGBA"))
    logo_small = load_logo(190)
    end = EndCard(tanks)
    grain = np.random.default_rng(3).normal(0, 1.8, (H, W, 1)).astype(np.float32)  # fixed paper-like grain

    def render(f):
        if f < S2:
            im = scene_hook(f, tanks, bgs)
        elif f < S3:
            im = scene_split(f, pages, seam, sched, logo_small, split_grad)
        elif f < S4:
            im = scene_offer(f, tanks, offer_bg)
        else:
            im = end.render(f)
        arr = np.asarray(im.convert("RGB")).astype(np.float32)
        arr += grain
        return np.clip(arr, 0, 255).astype(np.uint8)

    out = os.path.join(ROOT, "out")
    if stills:
        os.makedirs(os.path.join(out, "stills"), exist_ok=True)
        for f in stills:
            Image.fromarray(render(f)).save(os.path.join(out, "stills", f"f{f:03d}.png"))
        return

    path = os.path.join(out, "basic_ad_9x16.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", path],
        stdin=subprocess.PIPE,
    )
    for f in range(END):
        ff.stdin.write(render(f).tobytes())
    ff.stdin.close()
    ff.wait()
    print(path, f"{END / FPS:.1f}s")


if __name__ == "__main__":
    main()
