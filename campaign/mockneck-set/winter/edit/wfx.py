"""Effects for the BASIC winter film: procedural snow, window frost, the script title and the
logo, all deterministic (seeded) so every render is identical."""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
FONT_SCRIPT = os.path.join(ROOT, 'campaign', 'mockneck-set', 'edit', 'fonts', 'PinyonScript-Regular.ttf')
LOGO = os.path.join(ROOT, 'campaign', 'mockneck-set', 'refs', 'logo.png')


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = np.clip(t, 0, 1)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------------------- snow
class Snow:
    """Four depth layers of falling snow in front of the lens (far specks to soft bokeh flakes),
    with wind drift, sway and shutter-length streaks. Falls toward +y of the canvas it renders."""
    CLASSES = [  # n per 1080x1920, radius px, fall px/s, alpha, sway px, sway Hz
        (300, (0.6, 1.1), (55, 95), (0.28, 0.55), 5, (0.20, 0.50)),
        (120, (1.3, 2.3), (130, 210), (0.45, 0.75), 12, (0.20, 0.45)),
        (26, (3.2, 5.6), (300, 440), (0.40, 0.66), 22, (0.15, 0.35)),
        (6, (15, 28), (480, 640), (0.10, 0.17), 30, (0.10, 0.25)),
    ]
    SHUTTER = 1 / 48

    def __init__(self, w, h, seed=7, wind=26.0):
        rng = np.random.default_rng(seed)
        self.w, self.h, self.M = w, h, 80
        area = w * h / (1080 * 1920)
        self.flakes = []
        for ci, (n, rr, vv, aa, sway, ff) in enumerate(self.CLASSES):
            for _ in range(max(1, int(round(n * area)))):
                r = rng.uniform(*rr)
                v = rng.uniform(*vv)
                fl = dict(x0=rng.uniform(0, w + 2 * self.M), y0=rng.uniform(0, h + 2 * self.M), r=r, v=v,
                          a=rng.uniform(*aa), sw=sway * rng.uniform(0.5, 1.0), fr=rng.uniform(*ff),
                          ph=rng.uniform(0, 2 * np.pi), wind=wind * (0.4 + 0.25 * ci) * rng.uniform(0.7, 1.3),
                          cls=ci)
                fl['spr'] = self._sprite(r, v, ci)
                self.flakes.append(fl)

    def _sprite(self, r, v, ci):
        streak = v * self.SHUTTER
        if ci == 3:                                     # soft out-of-focus disc
            R = int(r + streak + 4)
            yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
            d = np.sqrt(xx ** 2 + (yy / (1 + streak / (2 * r))) ** 2)
            s = smoothstep(r, r - 3.5, d) * (0.75 + 0.25 * smoothstep(r * 0.4, r, d))
            return s.astype(np.float32)
        sx = max(0.55, r / 1.7)
        sy = np.sqrt(sx ** 2 + (streak / 2.6) ** 2)
        R = int(np.ceil(3 * sy)) + 1
        yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
        return np.exp(-0.5 * ((xx / sx) ** 2 + (yy / sy) ** 2)).astype(np.float32)

    def alpha(self, t, k=1.0, classes=(0, 1, 2, 3)):
        A = np.zeros((self.h, self.w), np.float32)
        M = self.M
        for fl in self.flakes:
            if fl['cls'] not in classes:
                continue
            y = (fl['y0'] + fl['v'] * t) % (self.h + 2 * M) - M
            x = (fl['x0'] + fl['wind'] * t + fl['sw'] * np.sin(2 * np.pi * fl['fr'] * t + fl['ph'])) \
                % (self.w + 2 * M) - M
            spr = fl['spr']
            R = spr.shape[0] // 2
            xi, yi = int(round(x)), int(round(y))
            x0, y0, x1, y1 = xi - R, yi - R, xi + R + 1, yi + R + 1
            sx0, sy0 = max(0, -x0), max(0, -y0)
            x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(self.w, x1), min(self.h, y1)
            if x1c <= x0c or y1c <= y0c:
                continue
            A[y0c:y1c, x0c:x1c] += spr[sy0:sy0 + (y1c - y0c), sx0:sx0 + (x1c - x0c)] * (fl['a'] * k)
        return np.clip(A, 0, 1)


SNOW_COL = np.array([0.96, 0.975, 1.0], np.float32)


def composite_snow(img, A):
    return img * (1 - A[..., None]) + SNOW_COL * A[..., None]


# ------------------------------------------------------------------------------- noise
def fractal_noise(w, h, seed, cells=(260, 130, 64, 32, 16), weights=(1.0, 0.6, 0.38, 0.24, 0.15)):
    """Sum of smooth value-noise octaves (cell size in px), normalised to 0..1."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    for c, wt in zip(cells, weights):
        g = rng.standard_normal((h // c + 3, w // c + 3)).astype(np.float32)
        g = cv2.resize(g, ((w // c + 3) * c, (h // c + 3) * c), interpolation=cv2.INTER_CUBIC)[c:c + h, c:c + w]
        out += wt * g
    out -= out.min()
    return out / (out.max() + 1e-6)


# ------------------------------------------------------------------------------- frost
class Frost:
    """Frost growing across a cold window from the edges inward, with dendrite crystals."""

    def __init__(self, w=1080, h=1920, seed=5):
        self.w, self.h = w, h
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
        self.noise = fractal_noise(w, h, seed + 1)
        self.field = (r + 0.34 * (self.noise - 0.5)).astype(np.float32)          # ~-0.2 .. 1.15
        self.crystal = self._crystals(rng)
        fine = rng.standard_normal((h, w)).astype(np.float32)
        self.fine = cv2.GaussianBlur(fine, (0, 0), 1.2)
        self.fine /= self.fine.std()
        self.glint_pts = np.stack([rng.uniform(0, w, 260), rng.uniform(0, h, 260)], 1)
        self.glint_ph = rng.uniform(0, 1, 260)

    def _crystals(self, rng):
        """Fern frost: stems grow in from the edges and corners, side branches leave at the ice
        angle (60 deg) alternately, with a finer generation on the larger side branches."""
        w, h = self.w, self.h
        S = 2
        cv = np.zeros((h * S, w * S), np.float32)
        SIXTY = np.radians(60)

        def seg(x, y, nx, ny, val):
            cv2.line(cv, (int(x * S), int(y * S)), (int(nx * S), int(ny * S)), val, 1, cv2.LINE_AA)

        def stem(x, y, ang, length, depth, val):
            step = 4.0
            n = int(length / step)
            side = 1 if rng.random() < 0.5 else -1
            for i in range(n):
                nx, ny = x + step * np.cos(ang), y + step * np.sin(ang)
                seg(x, y, nx, ny, val)
                if depth > 0 and i > 1 and i % 2 == 0:
                    rem = (n - i) * step
                    sub = rem * rng.uniform(0.28, 0.46)
                    if sub > 5:
                        stem(nx, ny, ang + side * SIXTY * rng.uniform(0.9, 1.1), sub, depth - 1, val * 0.85)
                    side = -side
                x, y = nx, ny
                ang += rng.normal(0, 0.035)

        cx, cy = w / 2, h / 2
        for _ in range(120):
            if rng.random() < 0.35:                              # corners grow the densest ferns
                x = rng.choice([rng.uniform(-10, 160), rng.uniform(w - 160, w + 10)])
                y = rng.choice([rng.uniform(-10, 220), rng.uniform(h - 220, h + 10)])
            else:
                e = rng.integers(4)
                x, y = [(rng.uniform(0, w), rng.uniform(-8, 20)), (rng.uniform(0, w), rng.uniform(h - 20, h + 8)),
                        (rng.uniform(-8, 20), rng.uniform(0, h)), (rng.uniform(w - 20, w + 8), rng.uniform(0, h))][e]
            ang = np.arctan2(cy - y, cx - x) + rng.normal(0, 0.6)
            stem(x, y, ang, rng.uniform(70, 260), 2, rng.uniform(0.55, 1.0))
        c = cv2.resize(cv, (w, h), interpolation=cv2.INTER_AREA)
        c = np.clip(c * 1.5, 0, 1)
        glow = cv2.GaussianBlur(c, (0, 0), 2.5)
        return np.clip(0.75 * c + 0.9 * glow, 0, 1).astype(np.float32)

    def coverage(self, p, soft=(0.11, 0.05)):
        """p 0..1 growth progress -> coverage 0..1 per pixel (soft, fog-like front)."""
        thr = 1.18 - 1.60 * p
        return smoothstep(thr - soft[0], thr + soft[1], self.field)

    def frosted(self, img, strength=1.0, blur=22, white=0.58, crystal=None, sat=0.75):
        small = cv2.resize(img, (self.w // 2, self.h // 2), interpolation=cv2.INTER_AREA)
        b = cv2.GaussianBlur(small, (0, 0), blur / 2)
        b = cv2.resize(b, (self.w, self.h), interpolation=cv2.INTER_LINEAR)
        y = (b @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
        b = y + (b - y) * sat
        tint = np.array([0.91, 0.94, 0.97], np.float32)
        wv = (white * strength * (0.88 + 0.24 * self.noise))[..., None]
        fr = 1 - (1 - b) * (1 - wv * tint)
        cr = self.crystal if crystal is None else crystal
        fr = fr + (cr * 0.30 * strength)[..., None] * np.array([0.97, 0.99, 1.0], np.float32)
        fr = fr + (self.fine * 0.008)[..., None]
        return np.clip(fr, 0, 1)

    def apply(self, img, p):
        C = self.coverage(p)
        if C.max() <= 0:
            return img
        thr = 1.18 - 1.60 * p
        cry = self.crystal * smoothstep(thr - 0.02, thr + 0.14, self.field)   # ice trails the fog
        fr = self.frosted(img, crystal=cry)
        rim = 4 * C * (1 - C)
        out = img * (1 - C[..., None]) + fr * C[..., None]
        return np.clip(out + (rim * 0.06)[..., None] * np.array([0.95, 0.98, 1.0], np.float32), 0, 1)

    def glints(self, t, strength=1.0):
        """Twinkling points on the frost (for the end card)."""
        G = np.zeros((self.h, self.w), np.float32)
        for (x, y), ph in zip(self.glint_pts, self.glint_ph):
            v = np.sin(2 * np.pi * (t * 0.9 + ph)) ** 16
            if v < 0.05:
                continue
            xi, yi = int(x), int(y)
            if 3 <= xi < self.w - 3 and 3 <= yi < self.h - 3:
                G[yi, xi] += v
        G = cv2.GaussianBlur(G, (0, 0), 1.3) * 9
        star = cv2.GaussianBlur(G, (0, 0), 5) * 2.2
        return np.clip((G + star) * strength, 0, 1)


# ------------------------------------------------------------------------------- script title
class ScriptWord:
    """One word of the title in the reference's white copperplate script, written on with a
    slanted soft wipe that follows the italic, de-blurring as it lands."""
    SLANT = np.tan(np.radians(20))

    def __init__(self, text, size_px, ss=2):
        font = ImageFont.truetype(FONT_SCRIPT, size_px * ss)
        bb = font.getbbox(text)
        pad = 60 * ss
        im = Image.new('L', (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), 0)
        ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=font, fill=255)
        a = np.asarray(im).astype(np.float32) / 255
        a = cv2.resize(a, (a.shape[1] // ss, a.shape[0] // ss), interpolation=cv2.INTER_AREA)
        ys, xs = np.where(a > 0.02)
        self.ink = (xs.min(), xs.max(), ys.min(), ys.max())
        self.a = a
        self.h, self.w = a.shape
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        self.u = xx + (self.h / 2 - yy) * self.SLANT          # slanted wipe coordinate
        self.u0 = self.ink[0] - self.h * 0.5 * self.SLANT - 10
        self.u1 = self.ink[1] + self.h * 0.5 * self.SLANT + 10

    def layer(self, p):
        """p 0..1 write-on progress -> (alpha, glow)."""
        if p <= 0:
            return None
        feather = 0.16 * (self.u1 - self.u0)
        e = self.u0 - feather + ease_in_out(p) * (self.u1 - self.u0 + 2 * feather)
        rv = np.clip((e - self.u) / feather, 0, 1)
        a = self.a * rv
        sig = 2.6 * (1 - ease_out(p))
        if sig > 0.25:
            a = cv2.GaussianBlur(a, (0, 0), sig)
        return a * min(1.0, p * 3.0)

    def composite(self, img, cx, cy, p, opacity=1.0):
        a = self.layer(p)
        if a is None or opacity <= 0:
            return img
        a = a * opacity
        x0 = int(round(cx - (self.ink[0] + self.ink[1]) / 2))
        y0 = int(round(cy - (self.ink[2] + self.ink[3]) / 2))
        H, W = img.shape[:2]
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + self.w), min(H, y0 + self.h)
        if xb <= xa or yb <= ya:
            return img
        sub = a[ya - y0:yb - y0, xa - x0:xb - x0]
        reg = img[ya:yb, xa:xb]
        sh = cv2.GaussianBlur(np.roll(sub, 3, axis=0), (0, 0), 7) * 0.42
        reg *= (1 - sh[..., None])
        glow = cv2.GaussianBlur(sub, (0, 0), 12) * 0.22
        reg[:] = 1 - (1 - reg) * (1 - glow[..., None])
        col = np.array([0.985, 0.98, 0.97], np.float32)
        reg[:] = reg * (1 - sub[..., None]) + col * sub[..., None]
        return img


# ------------------------------------------------------------------------------- logo
def logo_alpha(width_px):
    """The BASIC ESSENTIALS mark, cropped to its ink and resampled with crisp edges."""
    a = np.asarray(Image.open(LOGO).convert('RGBA'))[..., 3].astype(np.float32) / 255
    ys, xs = np.where(a > 0.08)
    m = 6
    a = a[max(0, ys.min() - m):ys.max() + m + 1, max(0, xs.min() - m):xs.max() + m + 1]
    sc = width_px / (a.shape[1] - 2 * m)
    big = cv2.resize(a, (int(a.shape[1] * sc * 4), int(a.shape[0] * sc * 4)), interpolation=cv2.INTER_CUBIC)
    big = smoothstep(0.30, 0.70, big)
    out = cv2.resize(big, (int(a.shape[1] * sc), int(a.shape[0] * sc)), interpolation=cv2.INTER_AREA)
    return np.clip(out, 0, 1).astype(np.float32)
