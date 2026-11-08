#!/usr/bin/env python3
"""BASIC Essentials - tracksuit ad, v2. Composites every layer, 1080x1920.

    python3 render.py preview 1.0 3.5 8.5 12.8 16.4 19.0   # stills -> out/preview/
    python3 render.py full                                 # -> out/basic_ad_silent.mp4

Structure (20 s, one colourway at a time, each once):
  0.0  cold open - the storm strikes, the BASIC logo forms out of the flash,
       then shrinks into the header while the layout slides in
  1.8  Bordeaux  - 01 L'ENSEMBLE  (what the set is)
  6.6  Chocolat  - 02 LA MATIERE  (the fabric)
 10.8  Noir      - 03 LA COUPE    (the cut)
 15.0  line-up   - the three looks together
 17.4  slate     - logo, tagline, call to action

Layout follows the reference ad: model left; ghost-mannequin outfit, swatches
and copy in a frosted-glass column on the right. Every visual is a pure
function of t, so any frame renders on its own.
"""
import os, sys, subprocess, math, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

from media import read_frames
from keying import ghost_plate, key_dark_on_grey

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(ROOT, *a)

W, H, FPS = 1080, 1920, 30
DUR = 20.0
PLATE_FRAMES = 358                       # storm.mp4 at 24 fps
PLATE_RATE = (PLATE_FRAMES - 1) / 24 / DUR   # plate slowed to span the whole ad

# ---------------------------------------------------------------- timeline
OPEN_END = 1.8
SEGMENTS = [
    dict(key='bordeaux', name='Bordeaux', t0=1.8, t1=6.6, model='M1_bordeaux',
         eyebrow='01  ·  L’ENSEMBLE',
         colour=['un rouge profond,', 'chaleureux et élégant.'],
         detail=['sweat col montant oversize', 'et pantalon large assorti.']),
    dict(key='chocolat', name='Chocolat', t0=6.6, t1=10.8, model='M3_chocolat',
         eyebrow='02  ·  LA MATIÈRE',
         colour=['un brun doux et gourmand,', 'comme un chocolat chaud.'],
         detail=['molleton épais et doux,', 'finition mate.']),
    dict(key='noir', name='Noir', t0=10.8, t1=15.0, model='M2_noir',
         eyebrow='03  ·  LA COUPE',
         colour=['intemporel,', 'il se porte avec tout.'],
         detail=['col montant,', 'épaules tombantes,', 'ourlet arrondi.']),
]
LINEUP_T = 15.0
SLATE_T = 17.4
TAGLINE = 'L’ENSEMBLE D’HIVER'

# (t, strength, bolt) - bolt is ((dx, dy), mirrored) or None. Strong flashes
# sit on the cuts and hide them; the faint ones are distant weather.
FLASHES = [
    (0.14, 0.55, None),                  # the plate opens on its own bolt
    (4.3, 0.16, None),
    (6.6, 1.0, ((-20, -445), False)),
    (10.8, 1.0, ((90, -440), True)),
    (13.1, 0.18, None),
    (15.0, 1.35, ((250, -330), False)),
    (19.1, 0.16, None),
]

ORDER = ['bordeaux', 'chocolat', 'noir']
DOT_RGB = {                       # the garments as they read on screen (median of
    'bordeaux': (0x55, 0x2A, 0x3D),   # each model's torso), so the swatch matches
    'chocolat': (0x58, 0x3B, 0x3C),   # what the viewer is looking at
    'noir':     (0x35, 0x31, 0x38),
}
MODEL_OF = {s['key']: s['model'] for s in SEGMENTS}

# ---------------------------------------------------------------- layout
PANEL = dict(x=576, y=168, w=468, h=1452, r=44)
PCX = PANEL['x'] + PANEL['w'] // 2
GHOST_BOX = (460, 800)
GHOST_TOP = 196
DOT_Y = 1004
DOT_GAP = 90
DOT_D, DOT_D_ACTIVE = 44, 58
TEXT_X = PANEL['x'] + 30
TEXT_W = PANEL['w'] - 60
MODEL_H = 1360
MODEL_FEET = 1734
MODEL_CX = 272
LINEUP_H = 1060
LINEUP_FEET = 1716
HEADER_LOGO = (150, 232, 196)     # centre x, centre y, width
OPEN_LOGO = (540, 800, 640)
SLATE_LOGO = (540, 770, 600)

FONT_DIR = '/usr/share/fonts/opentype/inter/'
SERIF = P('fonts', 'playfair-display-latin-400-italic.woff')
NNBSP = ' '

INK = (24, 22, 26)
INK2 = (52, 50, 56)
MUTED = (118, 116, 124)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------- easing
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def ease_out_cubic(x):
    x = clamp01(x); return 1 - (1 - x) ** 3

def ease_out_expo(x):
    x = clamp01(x); return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)

def ease_out_back(x, s=1.7):
    x = clamp01(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2

def ease_in_out(x):
    x = clamp01(x); return x * x * (3 - 2 * x)

def ease_in_out_cubic(x):
    x = clamp01(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

# ---------------------------------------------------------------- compositing
def over(dst, rgb, a, x, y, opacity=1.0):
    """Alpha-composite rgb (h,w,3 float) with a (h,w float) onto dst at (x,y)."""
    if opacity <= 0.001:
        return
    h, w = a.shape
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    sa = a[y0 - y:y1 - y, x0 - x:x1 - x, None] * opacity
    d = dst[y0:y1, x0:x1]
    d *= (1 - sa)
    if np.ndim(rgb) == 1:
        d += np.asarray(rgb, np.float32) * sa
    else:
        d += rgb[y0 - y:y1 - y, x0 - x:x1 - x] * sa


def screen_add(dst, light, gain, x=0, y=0):
    """Light (h,w) or (h,w,3) in 0..1 screened onto dst - never clips harshly."""
    h, w = light.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    l = light[y0 - y:y1 - y, x0 - x:x1 - x]
    if l.ndim == 2:
        l = l[..., None]
    d = dst[y0:y1, x0:x1]
    d += (255 - d) * np.clip(l * gain, 0, 1)


def rgba_arrays(im):
    arr = np.asarray(im, np.float32)
    return arr[..., :3].copy(), arr[..., 3] / 255.0


def resize_rgba(im, size):
    """Premultiplied resize, so edges never pick up a dark fringe."""
    return im.convert('RGBa').resize(size, Image.LANCZOS).convert('RGBA')


def rounded_mask(w, h, r, ss=4):
    m = Image.new('L', (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=255)
    return np.asarray(m.resize((w, h), Image.LANCZOS), np.float32) / 255.0


def soft_ellipse(w, h, blur):
    pad = int(blur * 3) + 2
    im = Image.new('L', (w + 2 * pad, h + 2 * pad), 0)
    ImageDraw.Draw(im).ellipse([pad, pad, pad + w, pad + h], fill=255)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255.0, pad


def circle(d, rgb, ring=0.0, ss=4):
    """Swatch dot; ring in [0,1] grows the selected outline (own colour, gapped)."""
    gap, rw = 5.0 * ring, 2.6 * ring
    D = int(math.ceil(d + 2 * (gap + rw))) + 8
    im = Image.new('RGBA', (D * ss, D * ss), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    c = D * ss / 2
    if ring > 0.01:
        ro, ri = (d / 2 + gap + rw) * ss, (d / 2 + gap) * ss
        dr.ellipse([c - ro, c - ro, c + ro, c + ro], fill=tuple(rgb) + (255,))
        dr.ellipse([c - ri, c - ri, c + ri, c + ri], fill=(0, 0, 0, 0))
    r = d / 2 * ss
    dr.ellipse([c - r, c - r, c + r, c + r], fill=tuple(rgb) + (255,))
    return rgba_arrays(im.resize((D, D), Image.LANCZOS))


def ring_sprite(d, width, ss=4):
    D = int(math.ceil(d + width)) + 6
    im = Image.new('L', (D * ss, D * ss), 0)
    c, r = D * ss / 2, d / 2 * ss
    ImageDraw.Draw(im).ellipse([c - r, c - r, c + r, c + r], outline=255, width=int(width * ss))
    return np.asarray(im.resize((D, D), Image.LANCZOS), np.float32) / 255.0


def hblur_rgba(rgb, a, px):
    """Horizontal motion blur on a premultiplied sprite."""
    if px < 2:
        return rgb, a
    pm = rgb * a[..., None]
    pm = ndimage.uniform_filter1d(pm, int(px), axis=1, mode='constant')
    a2 = ndimage.uniform_filter1d(a, int(px), axis=1, mode='constant')
    return pm / np.maximum(a2[..., None], 1e-4), a2

# ---------------------------------------------------------------- text
class Text:
    """A line of type that can animate as a whole or letter by letter.

    modes: 'rise' (fade + rise), 'focus' (blur-to-sharp), 'letters'
    (per-glyph fade + rise, staggered), 'type' (glyphs pop in sequence).
    """
    def __init__(self, s, font, size, rgb, x, y, t_in, t_out=None, anchor='l',
                 mode='rise', tracking=0.0, stagger=0.035, rise=16, dur=0.32,
                 shadow=None):
        self.f = ImageFont.truetype(font, size)
        f = self.f
        asc, desc = f.getmetrics()
        n = len(s)
        offs = [f.getlength(s[:i]) + tracking * i for i in range(n)]
        self.width = f.getlength(s) + tracking * max(n - 1, 0)
        pad = 28
        Wd, Hd = int(self.width) + 2 * pad + 4, asc + desc + 2 * pad
        line = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0))
        dr = ImageDraw.Draw(line)
        self.glyphs = []
        for ch, ox in zip(s, offs):
            if ch.strip():
                dr.text((pad + ox, pad), ch, font=f, fill=tuple(rgb) + (255,))
                g = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0))
                ImageDraw.Draw(g).text((pad + ox, pad), ch, font=f, fill=tuple(rgb) + (255,))
                bb = g.getbbox()
                if bb:
                    gr, ga = rgba_arrays(g.crop(bb))
                    self.glyphs.append((bb[0], bb[1], gr, ga))
        if shadow:                                        # (blur, opacity)
            a = line.split()[3].filter(ImageFilter.GaussianBlur(shadow[0]))
            sh = Image.new('RGBA', line.size, (0, 0, 0, 0))
            sh.putalpha(a.point(lambda v: int(v * shadow[1])))
            self.shadow = rgba_arrays(sh)
        else:
            self.shadow = None
        self.line = rgba_arrays(line)
        if mode == 'focus':
            self.blurs = [rgba_arrays(line.filter(ImageFilter.GaussianBlur(r))) for r in (7, 2.5)]
        ox = {'l': 0, 'm': self.width / 2, 'r': self.width}[anchor]
        self.x, self.y = x - ox - pad, y - asc - pad
        self.t_in, self.t_out = t_in, t_out
        self.mode, self.stagger, self.rise, self.dur = mode, stagger, rise, dur

    def active(self, t):
        return t >= self.t_in and (self.t_out is None or t < self.t_out + 0.4)

    def draw(self, frame, t, dx=0.0, dy=0.0):
        if not self.active(t):
            return
        out_op, out_dy = 1.0, 0.0
        if self.t_out is not None and t >= self.t_out:
            k2 = ease_in_out((t - self.t_out) / 0.28)
            out_op, out_dy = 1 - k2, -14 * k2
        x, y = self.x + dx, self.y + dy + out_dy
        if self.mode in ('letters', 'type'):
            done = t - self.t_in > self.stagger * len(self.glyphs) + self.dur
            if done:
                if self.shadow:
                    over(frame, *self.shadow, x, y, out_op)
                over(frame, *self.line, x, y, out_op)
                return
            if self.shadow:
                span = self.stagger * len(self.glyphs) + self.dur
                over(frame, *self.shadow, x, y, out_op * clamp01((t - self.t_in) / span))
            for i, (gx, gy, gr, ga) in enumerate(self.glyphs):
                tt = t - self.t_in - self.stagger * i
                if tt < 0:
                    break
                if self.mode == 'type':
                    k = clamp01(tt / 0.06)
                    over(frame, gr, ga, x + gx, y + gy, k * out_op)
                else:
                    k = ease_out_cubic(tt / self.dur)
                    over(frame, gr, ga, x + gx, y + gy + self.rise * (1 - k), k * out_op)
            return
        k = ease_out_cubic((t - self.t_in) / self.dur)
        ry = self.rise * (1 - k)
        if self.shadow:
            over(frame, *self.shadow, x, y + ry, k * out_op)
        if self.mode == 'focus' and k < 0.999:
            b1, b2 = self.blurs
            if k < 0.5:
                w = k / 0.5
                over(frame, *b1, x, y + ry, (1 - w) * k * out_op * 1.6)
                over(frame, *b2, x, y + ry, w * k * out_op * 1.6)
            else:
                w = (k - 0.5) / 0.5
                over(frame, *b2, x, y + ry, (1 - w) * out_op)
                over(frame, *self.line, x, y + ry, w * out_op)
            return
        over(frame, *self.line, x, y + ry, k * out_op)


class Rule:
    """A hairline that draws itself from the left."""
    def __init__(self, x, y, w, rgb, t_in, t_out):
        self.x, self.y, self.w, self.rgb, self.t_in, self.t_out = x, y, w, rgb, t_in, t_out

    def active(self, t):
        return self.t_in <= t < self.t_out + 0.4

    def draw(self, frame, t, dx=0.0, dy=0.0):
        if not self.active(t):
            return
        k = ease_out_cubic((t - self.t_in) / 0.5)
        op = 1 - ease_in_out((t - self.t_out) / 0.28) if t >= self.t_out else 1.0
        ww = max(1, int(self.w * k))
        a = np.full((2, ww), 0.55, np.float32)
        over(frame, np.asarray(self.rgb, np.float32), a, self.x + dx, self.y + dy, op)


def caps(s, size, rgb, x, y, t_in, t_out=None, anchor='l', tracking=None, shadow=None,
         stagger=0.028):
    tr = size * 0.32 if tracking is None else tracking
    return Text(s, FONT_DIR + 'Inter-Medium.otf', size, rgb, x, y, t_in, t_out, anchor,
                mode='type', tracking=tr, stagger=stagger, shadow=shadow)


def fit_size(lines, font, start, max_w):
    for size in range(start, 12, -1):
        f = ImageFont.truetype(font, size)
        if max(f.getlength(l) for l in lines) <= max_w:
            return size
    return 12


def build_texts():
    """Every line of copy with its timing. Per segment: eyebrow (what this
    beat is about), the colour's name, a line on the colour, then the detail."""
    items = []
    light, regular = FONT_DIR + 'Inter-Light.otf', FONT_DIR + 'Inter-Regular.otf'
    for i, s in enumerate(SEGMENTS):
        T = s['t0'] + (0.3 if i == 0 else 0.0)        # first one waits for the slide-in
        out = s['t1'] - 0.34
        ey, ty, cy, ry_, dy = 1130, 1236, 1294, 1372, 1424
        items.append(caps(s['eyebrow'], 20, MUTED, TEXT_X, ey, T + 0.3, out))
        tsize = fit_size([s['name']], SERIF, 98, TEXT_W)
        items.append(Text(s['name'], SERIF, tsize, INK, TEXT_X - 4, ty, T + 0.42, out,
                          mode='letters', stagger=0.045, rise=26, dur=0.42))
        csize = fit_size(s['colour'], light, 31, TEXT_W)
        for j, line in enumerate(s['colour']):
            items.append(Text(line, light, csize, INK2, TEXT_X, cy + j * 41, T + 0.85 + 0.14 * j, out,
                              mode='focus', rise=10, dur=0.45))
        items.append(Rule(TEXT_X, ry_, 56, INK, T + 1.35, out))
        dsize = fit_size(s['detail'], regular, 29, TEXT_W)
        for j, line in enumerate(s['detail']):
            items.append(Text(line, regular, dsize, INK, TEXT_X, dy + j * 40, T + 1.55 + 0.13 * j, out,
                              rise=12, dur=0.36))

    # cold open: tagline under the big logo
    items.append(caps(TAGLINE, 24, WHITE, W / 2, 1040, 0.95, 1.42, anchor='m',
                      shadow=(10, 0.45), stagger=0.03))
    # line-up
    sh = (16, 0.42)
    items.append(Text('Un ensemble.', SERIF, 92, WHITE, W / 2, 360, LINEUP_T + 0.45, SLATE_T - 0.05,
                      anchor='m', mode='letters', stagger=0.04, rise=26, dur=0.45, shadow=sh))
    items.append(Text('Trois couleurs.', SERIF, 92, WHITE, W / 2, 462, LINEUP_T + 0.85, SLATE_T - 0.05,
                      anchor='m', mode='letters', stagger=0.04, rise=26, dur=0.45, shadow=sh))
    items.append(caps('BORDEAUX  ·  CHOCOLAT  ·  NOIR', 21, (240, 240, 244), W / 2, 548,
                      LINEUP_T + 1.35, SLATE_T - 0.05, anchor='m', shadow=(10, 0.4), stagger=0.022))
    # slate
    items.append(caps(TAGLINE, 24, WHITE, W / 2, 1000, SLATE_T + 0.95, None, anchor='m',
                      shadow=(10, 0.4), stagger=0.03))
    return items

# ---------------------------------------------------------------- weather
class Rain:
    """Procedural streaks; positions are a pure function of t."""
    def __init__(self, n, length, speed, alpha, width, blur, seed, angle=9.0):
        rng = np.random.default_rng(seed)
        self.x0 = rng.uniform(-200, W + 200, n)
        self.ph = rng.uniform(0, H + 400, n)
        self.len = rng.uniform(*length, n)
        self.spd = rng.uniform(*speed, n)
        self.alp = rng.uniform(*alpha, n)
        self.width, self.blur = width, blur
        self.tan = math.tan(math.radians(angle))

    def render(self, t):
        im = Image.new('L', (W, H), 0)
        dr = ImageDraw.Draw(im)
        span = H + 400
        y1 = (self.ph + self.spd * t) % span - 200
        y0 = y1 - self.len
        x1 = (self.x0 + y1 * self.tan) % (W + 400) - 200
        x0 = x1 - self.len * self.tan
        for a, b, c, d, al in zip(x0, y0, x1, y1, self.alp):
            dr.line([(a, b), (c, d)], fill=int(al * 255), width=self.width)
        if self.blur:
            im = im.filter(ImageFilter.GaussianBlur(self.blur))
        return np.asarray(im, np.float32) / 255.0


def fractal_noise(h, w, seed, octaves=((90, 1.0), (40, 0.55), (16, 0.3))):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    for sigma, amp in octaves:
        n = ndimage.gaussian_filter(rng.normal(0, 1, (h, w)).astype(np.float32), sigma, mode='wrap')
        acc += amp * n / (n.std() + 1e-6)
    acc = (acc - acc.min()) / (acc.max() - acc.min())
    return acc


class Mist:
    """Low cloud drifting through the bottom of frame; wraps seamlessly."""
    def __init__(self, seed, top, strength, speed, contrast):
        self.h = H - top
        self.top, self.strength, self.speed = top, strength, speed
        tex = fractal_noise(self.h, 2 * W, seed)
        self.tex = np.clip((tex - 0.5) * contrast + 0.5, 0, 1)
        y = np.linspace(0, 1, self.h, dtype=np.float32)
        self.grad = (y ** 1.6)[:, None]

    def draw(self, frame, t, opacity=1.0):
        shift = int(self.speed * t) % (2 * W)
        idx = (np.arange(W) + shift) % (2 * W)
        a = self.tex[:, idx] * self.grad * self.strength * opacity
        over(frame, np.array([226, 229, 234], np.float32), a, 0, self.top)


def flash_state(t):
    """Total flash light, bolts to draw, and camera shake for time t."""
    env, bolts, sx, sy = 0.0, [], 0.0, 0.0
    for t0, s, bolt in FLASHES:
        dt = t - t0
        if dt < 0:
            continue
        e = math.exp(-dt / 0.05)
        if dt > 0.11:
            e += 0.6 * math.exp(-(dt - 0.11) / 0.09)
        env += s * e
        if bolt is not None and s * e > 0.002:
            bolts.append((s * e, bolt))
        if s >= 0.5:
            amp = 11 * s * math.exp(-dt / 0.2)
            sx += amp * math.sin(2 * math.pi * 23 * dt + t0)
            sy += amp * 0.6 * math.sin(2 * math.pi * 17 * dt + 2 * t0)
    return env, bolts, sx, sy

# ---------------------------------------------------------------- assets
class Assets:
    def __init__(self):
        t0 = time.time()
        self.plate_proc, self.plate_buf, self.plate_next = None, {}, 0
        self.models, self.torso_x, self.feet_x = {}, {}, {}
        for key, name in MODEL_OF.items():
            im = Image.open(P('build/cutouts', name + '.png')).convert('RGBA')
            arr = np.asarray(im, np.float32).copy()
            arr[..., :3] *= np.array([0.985, 0.995, 1.025], np.float32)   # into the cool storm light
            im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
            a = arr[..., 3] > 128
            h = a.shape[0]
            self.torso_x[key] = np.median(np.where(a[int(h * .30):int(h * .55)])[1]) / a.shape[1]
            self.feet_x[key] = np.median(np.where(a[int(h * .93):])[1]) / a.shape[1]
            self.models[key] = im
        self.model_scale = MODEL_H / max(im.height for im in self.models.values())
        self.ghosts = self.load_ghosts()
        self.bolt, self.bolt_glow = self.load_bolt()
        self._bolts = {}
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.glow = np.exp(-(((xx - MODEL_CX) / 470) ** 2 + ((yy - 900) / 820) ** 2))
        self.glow_end = np.exp(-(((xx - W / 2) / 700) ** 2 + ((yy - 1080) / 760) ** 2))
        r2 = ((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H * 0.47) / (H * 0.66)) ** 2
        self.vignette = (1 - 0.24 * np.clip(r2, 0, 1.6) ** 1.5)[..., None].astype(np.float32)
        pw, ph = PANEL['w'], PANEL['h']
        self.panel_mask = rounded_mask(pw, ph, PANEL['r'])
        inner = rounded_mask(pw - 3, ph - 3, PANEL['r'] - 1)
        ring = self.panel_mask.copy()
        ring[1:-2, 1:-2] -= inner
        self.panel_ring = np.clip(ring, 0, 1)
        pad = 60
        sm = np.zeros((ph + 2 * pad, pw + 2 * pad), np.float32)
        sm[pad:pad + ph, pad:pad + pw] = self.panel_mask
        self.panel_shadow = ndimage.gaussian_filter(sm, 22)
        py, px = np.mgrid[0:ph, 0:pw].astype(np.float32)
        diag = px / pw * 0.55 + py / ph
        self.panel_sheen = np.clip(1 - diag / 0.45, 0, 1) ** 2 * 14
        rng = np.random.default_rng(3)
        self.panel_frost = ndimage.gaussian_filter(rng.normal(0, 1, (ph, pw)), 1.2).astype(np.float32) * 5
        self.grain = [rng.normal(0, 2.2, (H, W)).astype(np.float32) for _ in range(6)]
        self.rain_far = Rain(300, (18, 42), (1300, 1800), (0.10, 0.26), 1, 0.6, seed=21)
        self.rain_near = Rain(46, (90, 170), (2600, 3400), (0.10, 0.20), 3, 2.2, seed=22, angle=11)
        self.mist_back = Mist(31, 1180, 0.55, 22, 1.6)
        self.mist_front = Mist(32, 1400, 0.40, 46, 1.9)
        self.drops = self.make_droplets()
        self.logo = Logo()
        self.lineup = self.make_lineup_layers()
        self.cta = self.make_cta()
        self.pulse = ring_sprite(80, 2.0)
        self.ghost_shadow = soft_ellipse(270, 26, 12)
        print(f'assets ready in {time.time() - t0:.1f}s')

    # -- storm plate, slowed: blend neighbouring source frames
    def _plate_frame(self, i):
        i = min(max(i, 0), PLATE_FRAMES - 1)
        if i in self.plate_buf:
            return self.plate_buf[i]
        if self.plate_proc is None or i < self.plate_next:
            if self.plate_proc is not None:
                self.plate_proc.kill()
            self.plate_proc = subprocess.Popen(
                ['ffmpeg', '-v', 'error', '-i', P('assets/background/storm.mp4'),
                 '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
            self.plate_next, self.plate_buf = 0, {}
        while self.plate_next <= i:
            buf = self.plate_proc.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                return self.plate_buf[max(self.plate_buf)]
            self.plate_buf[self.plate_next] = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            for k in [k for k in self.plate_buf if k < self.plate_next - 2]:
                del self.plate_buf[k]
            self.plate_next += 1
        return self.plate_buf[i]

    def plate(self, t):
        f = t * 24 * PLATE_RATE
        i = int(f)
        w = f - i
        a = self._plate_frame(i).astype(np.float32)
        if w > 0.01 and i + 1 < PLATE_FRAMES:
            a = a * (1 - w) + self._plate_frame(i + 1).astype(np.float32) * w
        return a

    def load_ghosts(self):
        cache = P('build', f'ghosts_v2_{GHOST_BOX[0]}x{GHOST_BOX[1]}.npz')
        if os.path.exists(cache):
            z = np.load(cache)
            return {k: z[k] for k in ORDER}
        print('keying ghost clips (first run only)...')
        out = {}
        crop = (75, 246, 978, 1701)          # union bbox of all three clips + 40px
        cw, ch = crop[2] - crop[0], crop[3] - crop[1]
        s = min(GHOST_BOX[0] / cw, GHOST_BOX[1] / ch)
        size = (int(round(cw * s)), int(round(ch * s)))
        for k in ORDER:
            fr, _ = read_frames(P('assets/ghosts', f'GHOST_{k}.mp4'))
            plate = ghost_plate(fr[0].astype(np.float32))[crop[1]:crop[3], crop[0]:crop[2]]
            frames = []
            for f in fr:
                img = f[crop[1]:crop[3], crop[0]:crop[2]].astype(np.float32)
                rgb, a = key_dark_on_grey(img, plate)
                if k == 'chocolat':
                    # the brown recolour came out ~16 levels darker than the
                    # master #472E31 measured on the product sheet - lift it
                    rgb = rgb * 1.15 + 8
                rgba = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
                frames.append(np.asarray(resize_rgba(Image.fromarray(rgba, 'RGBA'), size)))
            out[k] = np.stack(frames)
        np.savez(cache, **out)
        return out

    def ghost(self, key, ct):
        """Ghost frame at clip time ct (each colourway plays its turn once)."""
        clip = self.ghosts[key]
        f = min(max(ct * 24, 0), len(clip) - 1)
        i = int(f)
        w = f - i
        fr = clip[i].astype(np.float32)
        if w > 0.01 and i + 1 < len(clip):
            fr = fr * (1 - w) + clip[i + 1].astype(np.float32) * w
        return fr[..., :3], fr[..., 3] / 255.0

    def load_bolt(self):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', P('assets/background/storm.mp4'),
                              '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                             capture_output=True, check=True).stdout
        f0 = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32)
        L = f0.mean(2)
        hp = L - ndimage.gaussian_filter(L, 4)
        m = np.zeros_like(L)
        y0, y1, x0, x1 = 450, 760, 400, 760
        m[y0:y1, x0:x1] = np.clip((hp[y0:y1, x0:x1] - 14) / 30, 0, 1)
        m = ndimage.gaussian_filter(m, 0.8)
        bolt = m[..., None] * np.array([235, 232, 255], np.float32)
        glow = ndimage.gaussian_filter(m, 40)
        return bolt, glow / glow.max()

    def bolt_at(self, spec):
        (dx, dy), mirror = spec
        key = (dx, dy, mirror)
        if key not in self._bolts:
            b, g = self.bolt, self.bolt_glow
            if mirror:                             # mirror about the bolt's own centre
                b = shifted(b[:, ::-1], 2 * 580 - W, 0)
                g = shifted(g[:, ::-1], 2 * 580 - W, 0)
            self._bolts[key] = (shifted(b, dx, dy), shifted(g, dx, dy))
        return self._bolts[key]

    def make_droplets(self):
        """Water on the glass: still beads and a few running drops, kept off
        the product's centre and out of the copy."""
        rng = np.random.default_rng(5)
        sprites = {}

        def sprite(r):
            r = round(r * 2) / 2
            if r in sprites:
                return sprites[r]
            ss, D = 4, int(r * 2 + 6)
            im = Image.new('RGBA', (D * ss, D * ss), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            c = D * ss / 2
            R = r * ss
            dr.ellipse([c - R, c - R, c + R, c + R], fill=(255, 255, 255, 34), outline=(40, 44, 52, 70),
                       width=max(1, int(ss * 0.8)))
            dr.ellipse([c - R * 0.55, c + R * 0.15, c + R * 0.55, c + R * 0.75], fill=(255, 255, 255, 46))
            hr = max(R * 0.28, ss * 0.9)
            dr.ellipse([c - R * 0.5 - hr, c - R * 0.5 - hr, c - R * 0.5 + hr, c - R * 0.5 + hr],
                       fill=(255, 255, 255, 210))
            sprites[r] = rgba_arrays(im.resize((D, D), Image.LANCZOS))
            return sprites[r]

        x0, y0, pw, ph = PANEL['x'], PANEL['y'], PANEL['w'], PANEL['h']

        def allowed(x, y):
            in_text = TEXT_X - 10 < x < TEXT_X + TEXT_W + 10 and 1060 < y < 1560
            in_product = PCX - 150 < x < PCX + 150 and GHOST_TOP + 40 < y < GHOST_TOP + 700
            return not in_text and not in_product

        still = []
        while len(still) < 42:
            x = rng.uniform(x0 + 14, x0 + pw - 14)
            y = rng.uniform(y0 + 14, y0 + ph - 14)
            if allowed(x, y):
                still.append((x - x0, y - y0, sprite(rng.uniform(1.6, 5.2))))
        running = []
        for k, (fx, start, speed) in enumerate([(0.06, 1.2, 150), (0.93, 4.0, 120),
                                                (0.10, 8.6, 135), (0.91, 12.2, 140)]):
            running.append((fx * pw, start, speed, sprite(4.2 + k % 2), sprite(1.6)))
        return still, running

    def make_lineup_layers(self):
        s = LINEUP_H / MODEL_H * self.model_scale
        layers = []
        for key, cx, z in [('bordeaux', 268, 0), ('noir', 822, 0), ('chocolat', 540, 1)]:
            im = self.models[key]
            im = resize_rgba(im, (int(im.width * s), int(im.height * s)))
            layers.append((key, cx, z, im))
        return sorted(layers, key=lambda l: l[2])

    def make_cta(self):
        f = ImageFont.truetype(FONT_DIR + 'Inter-Medium.otf', 34)
        label = 'disponible maintenant'
        tw = f.getlength(label)
        pw, ph = int(tw + 96), 88
        m = rounded_mask(pw, ph, ph // 2)
        im = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pw / 2, ph / 2 + 1), label, font=f, fill=INK + (255,), anchor='mm')
        trgb, ta = rgba_arrays(im)
        return m, trgb, ta


class Logo:
    """The BASIC Essentials mark: wordmark, hairline and ESSENTIALS, rendered
    at any width and colour, with a light sweep and a centre-out reveal of the
    lower line."""
    def __init__(self):
        im = Image.open(P('assets/brand/basic_logo.png')).convert('RGBA')
        a = np.asarray(im)[..., 3].astype(np.float32) / 255
        x0, x1, y0, y1 = 85 - 16, 555 + 16, 95 - 16, 314 + 16
        self.alpha = Image.fromarray((a[y0:y1, x0:x1] * 255).astype(np.uint8), 'L')
        self.split = (267 - y0) / (y1 - y0)            # wordmark above, ESSENTIALS below
        self.aspect = (y1 - y0) / (x1 - x0)
        self.cache = {}

    def render(self, width, base_rgb, sweep=None, lower_reveal=1.0, blur=0.0):
        width = int(width)
        key = (width, round(blur, 1))
        if key not in self.cache:
            h = int(width * self.aspect)
            al = self.alpha.resize((width, h), Image.LANCZOS)
            if width > self.alpha.width:
                al = al.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=1))
            if blur > 0.3:
                al = al.filter(ImageFilter.GaussianBlur(blur))
            if len(self.cache) > 40:
                self.cache.clear()
            self.cache[key] = np.asarray(al, np.float32) / 255
        a = self.cache[key].copy()
        h, w = a.shape
        if lower_reveal < 1:
            ys = int(h * self.split)
            xs = np.abs(np.arange(w) - w / 2) / (w / 2)
            a[ys:] *= np.clip((lower_reveal * 1.15 - xs) / 0.15, 0, 1)[None, :]
        rgb = np.empty((h, w, 3), np.float32)
        rgb[:] = base_rgb
        glow = None
        if sweep is not None and -0.3 < sweep < 1.3:
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            u = xx / w + 0.35 * yy / h
            band = np.exp(-((u - sweep * 1.4 + 0.05) / 0.07) ** 2)
            rgb += (255 - rgb) * band[..., None]
            glow = band * a
        return rgb, a, glow

# ---------------------------------------------------------------- scene
def shifted(layer, dx, dy):
    """layer moved by (dx, dy), zero-filled."""
    out = np.zeros_like(layer)
    h, w = layer.shape[:2]
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = layer[ys, xs]
    return out


def segment_at(t):
    for i, s in enumerate(SEGMENTS):
        if s['t0'] <= t < s['t1']:
            return i, s
    return (0, SEGMENTS[0]) if t < SEGMENTS[0]['t0'] else (len(SEGMENTS) - 1, SEGMENTS[-1])


def grade_plate(plate):
    """A bright storm rather than a night one; slight cool lift in the shadows."""
    out = plate * 0.94 + 14
    out[..., 2] += 4 * (1 - plate[..., 2] / 255)
    return out


def draw_panel(frame, A, dx):
    x, y, pw, ph = PANEL['x'] + dx, PANEL['y'], PANEL['w'], PANEL['h']
    xi = int(round(x))
    pad = 60
    over(frame, np.zeros(3, np.float32), A.panel_shadow * 0.20, xi - pad, y + 18 - pad)
    x0, x1 = max(xi, 0), min(xi + pw, W)
    if x1 <= x0:
        return
    region = frame[y:y + ph, x0:x1]
    small = Image.fromarray(np.clip(region, 0, 255).astype(np.uint8)).resize(
        (max(1, (x1 - x0) // 4), ph // 4), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(9))
    blur = np.asarray(small.resize((x1 - x0, ph), Image.BILINEAR), np.float32)
    tint = np.linspace(0.60, 0.77, ph, dtype=np.float32)[:, None, None]
    glass = blur * 1.06 * (1 - tint) + np.array([250, 250, 252], np.float32) * tint
    sl = slice(x0 - xi, x1 - xi)
    glass += (A.panel_sheen[:, sl] + A.panel_frost[:, sl])[..., None]
    over(frame, glass, A.panel_mask[:, sl], x0, y)
    over(frame, np.full(3, 255, np.float32), A.panel_ring[:, sl] * 0.65, x0, y)


def draw_droplets(frame, A, t, dx):
    still, running = A.drops
    px, py = PANEL['x'] + dx, PANEL['y']
    for x, y, (rgb, a) in still:
        over(frame, rgb, a, px + x - a.shape[1] / 2, py + y - a.shape[0] / 2)
    for x, start, speed, (rgb, a), (trgb, ta) in running:
        tt = t - start
        if tt < 0 or tt > 9:
            continue
        # stick-slip: a drop holds, then lets go - water never slides evenly
        prog = speed * tt + 26 * math.sin(tt * 2.3)
        yy = 60 + prog
        if yy > PANEL['h'] - 30:
            continue
        for k in range(1, 7):                      # beads left behind
            ty = yy - k * 34
            if ty > 40:
                over(frame, trgb, ta, px + x + math.sin(k * 1.7) * 3 - 4, py + ty, 0.8 - k * 0.1)
        over(frame, rgb, a, px + x - a.shape[1] / 2, py + yy - a.shape[0] / 2)


def model_sprite(A, key, scale, rim=0.0, blur_px=0.0):
    im = A.models[key]
    s = A.model_scale * scale
    w, h = int(im.width * s), int(im.height * s)
    rgb, a = rgba_arrays(resize_rgba(im, (w, h)))
    if rim > 0.01:
        # lightning picks out the silhouette
        edge = np.clip(a - ndimage.minimum_filter(a, size=7), 0, 1)
        rgb += (255 - rgb) * (edge * min(rim, 1.0) * 0.85)[..., None]
    if blur_px > 1.5:
        rgb, a = hblur_rgba(rgb, a, blur_px)
    return rgb, a, w, h


def contact_shadow(frame, cx, feet_y, width, strength, opacity=1.0):
    sh, pad = soft_ellipse(int(width), 26, 15)
    over(frame, np.full(3, 30, np.float32), sh * strength, cx - width / 2 - pad, feet_y - 13 - pad, opacity)


def draw_ghost(frame, A, key, ct, flip, dx, sx_intro=1.0, prev=None):
    """flip in [0,1]: 3D card turn between colourways (prev -> key)."""
    if flip < 0.5 and prev is not None:
        k, cct = prev
    else:
        k, cct = key, ct
    rgb, a = A.ghost(k, cct)
    sx = sx_intro * max(abs(math.cos(math.pi * flip)), 0.02)
    h, w = a.shape
    sh, pad = A.ghost_shadow
    over(frame, np.full(3, 40, np.float32), sh * 0.18 * sx, PCX + dx - 135 - pad, GHOST_TOP + h - 6 - pad)
    if sx < 0.999:
        nw = max(2, int(w * sx))
        rgba = np.dstack([rgb, a[..., None] * 255]).astype(np.uint8)
        rgb, a = rgba_arrays(resize_rgba(Image.fromarray(rgba, 'RGBA'), (nw, h)))
        rgb *= 0.72 + 0.28 * sx
    over(frame, rgb, a, PCX + dx - a.shape[1] / 2, GHOST_TOP)


def draw_dots(frame, A, t, active, prev, k, dx, intro):
    for i, key in enumerate(ORDER):
        if key == active:
            d = DOT_D + (DOT_D_ACTIVE - DOT_D) * ease_out_back(k)
        elif key == prev:
            d = DOT_D_ACTIVE - (DOT_D_ACTIVE - DOT_D) * ease_out_cubic(k)
        else:
            d = DOT_D
        d *= intro[i]
        if d < 2:
            continue
        rgb, a = circle(d, DOT_RGB[key], ease_out_cubic(k) if key == active else 0.0)
        cx = PCX + dx + (i - 1) * DOT_GAP
        over(frame, rgb, a, cx - a.shape[1] / 2, DOT_Y - a.shape[0] / 2)
        if key == active and 0 < k < 2.6:           # selection ripple
            pk = clamp01(k / 2.6)
            s = 0.75 + 0.9 * ease_out_cubic(pk)
            ring = A.pulse
            rs = np.asarray(Image.fromarray((ring * 255).astype(np.uint8)).resize(
                (int(ring.shape[1] * s), int(ring.shape[0] * s)), Image.BILINEAR), np.float32) / 255
            over(frame, np.asarray(DOT_RGB[key], np.float32), rs * (1 - pk) * 0.8,
                 cx - rs.shape[1] / 2, DOT_Y - rs.shape[0] / 2)


def logo_layer(frame, A, t):
    """Big in the cold open, a small header through the segments, gone for the line-up."""
    if t >= LINEUP_T + 0.05:
        return
    k_in = ease_out_cubic((t - 0.28) / 0.6)
    if k_in <= 0:
        return
    m = ease_in_out_cubic((t - 1.42) / 0.5)              # FLIP into the header
    cx = OPEN_LOGO[0] + (HEADER_LOGO[0] - OPEN_LOGO[0]) * m
    cy = OPEN_LOGO[1] + (HEADER_LOGO[1] - OPEN_LOGO[1]) * m
    wd = OPEN_LOGO[2] + (HEADER_LOGO[2] - OPEN_LOGO[2]) * m
    wd *= 1.06 - 0.06 * k_in
    blur = 6 * (1 - k_in)
    sweep = (t - 0.85) / 0.6 if t < 1.5 else None
    rgb, a, glow = A.logo.render(wd, (236, 236, 240), sweep, ease_out_cubic((t - 0.62) / 0.55), blur)
    op = k_in * (0.92 if m >= 1 else 1.0)
    if t > LINEUP_T - 0.12:
        op *= 1 - clamp01((t - (LINEUP_T - 0.12)) / 0.12)
    x, y = cx - a.shape[1] / 2, cy - a.shape[0] / 2
    sh = ndimage.gaussian_filter(a, 10) * 0.42
    over(frame, np.zeros(3, np.float32), sh, x, y + 6, op)
    over(frame, rgb, a, x, y, op)
    if glow is not None:
        screen_add(frame, ndimage.gaussian_filter(glow, 8), 0.9 * op, int(x), int(y))


def draw_layout(frame, A, t, texts, env):
    """Model, glass column, ghost outfit, swatches and copy (1.6s - 15s)."""
    i, seg = segment_at(t)
    key, T = seg['key'], seg['t0']
    prev = SEGMENTS[i - 1] if i > 0 else None
    mk = ease_out_expo((t - 1.62) / 0.75)
    mdx = -720 * (1 - mk)
    pdx = 640 * (1 - ease_out_expo((t - 1.70) / 0.75))
    m_vel = 720 * 10 * math.log(2) / 0.75 * 2 ** (-10 * clamp01((t - 1.62) / 0.75)) if mk < 1 else 0
    end_k = clamp01((t - (LINEUP_T - 0.06)) / 0.06)          # tucked under the big flash

    draw_panel(frame, A, pdx)
    # ghost: turns in at the start, card-turns between colourways
    flip, prev_spec = 1.0, None
    if prev is not None and t < T + 0.13:
        flip = clamp01((t - (T - 0.13)) / 0.26)
    for j in range(1, len(SEGMENTS)):
        Tn = SEGMENTS[j]['t0']
        if Tn - 0.13 <= t < Tn:
            flip = (t - (Tn - 0.13)) / 0.26
            key_next = SEGMENTS[j]['key']
            prev_spec = (SEGMENTS[j - 1]['key'], t - SEGMENTS[j - 1]['t0'])
            draw_ghost(frame, A, key_next, 0.0, flip, pdx, 1.0, prev_spec)
            break
    else:
        if prev is not None and t < T + 0.13:
            prev_spec = (prev['key'], t - prev['t0'])
        sx_intro = ease_out_cubic((t - 1.95) / 0.55)
        draw_ghost(frame, A, key, t - T, flip, pdx, sx_intro, prev_spec)

    intro = [ease_out_back((t - 2.0 - 0.08 * j) / 0.3) for j in range(3)]
    dk = (t - T) / 0.18 if i > 0 else (t - 2.25) / 0.25
    draw_dots(frame, A, t, key, prev['key'] if prev else None, dk, pdx, intro)
    for tx in texts:
        if tx.t_in < LINEUP_T and tx.t_in >= 1.6:
            tx.draw(frame, t, pdx)
    draw_droplets(frame, A, t, pdx)                    # on the glass, behind the model
    # model: slow push-in, settle after each cut, rim-lit by the lightning
    push = 1 + 0.025 * ((t - T) / (seg['t1'] - T))
    settle = 0.04 * math.exp(-(t - T) / 0.13) if i > 0 else 0.0
    rgb, a, w, h = model_sprite(A, key, push + settle, rim=env, blur_px=m_vel / FPS * 0.5)
    x = MODEL_CX - A.torso_x[key] * w + mdx
    contact_shadow(frame, x + A.feet_x[key] * w, MODEL_FEET, 360 * push, 0.42, 1 - end_k)
    over(frame, rgb, a, x, MODEL_FEET - h, 1 - end_k)


def draw_endcard(frame, A, t, texts, env):
    te = t - LINEUP_T
    push = 1 + 0.03 * (te / (DUR - LINEUP_T))
    for n, (key, cx, z, im) in enumerate(A.lineup):
        k = ease_out_cubic((te - 0.04 * n) / 0.5)
        w, h = int(im.width * push), int(im.height * push)
        rgb, a = rgba_arrays(resize_rgba(im, (w, h)))
        if env > 0.01:
            edge = np.clip(a - ndimage.minimum_filter(a, size=6), 0, 1)
            rgb += (255 - rgb) * (edge * min(env, 1) * 0.85)[..., None]
        x = cx - A.torso_x[key] * w
        contact_shadow(frame, x + A.feet_x[key] * w, LINEUP_FEET, 300 * push, 0.38)
        over(frame, rgb, a, x, LINEUP_FEET + 50 * (1 - k) - h)
    for tx in texts:
        if LINEUP_T <= tx.t_in < SLATE_T:
            tx.draw(frame, t)


def draw_slate(frame, A, t, texts):
    ts = t - SLATE_T
    k = ease_in_out(ts / 0.6)
    if k > 0:
        small = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).resize((W // 6, H // 6), Image.BILINEAR)
        small = small.filter(ImageFilter.GaussianBlur(4 * k + 0.5))
        blur = np.asarray(small.resize((W, H), Image.BILINEAR), np.float32)
        frame[:] = frame * (1 - k) + blur * k
        frame *= 1 - 0.42 * k
    kl = ease_out_cubic((ts - 0.35) / 0.7)
    if kl > 0:
        wd = SLATE_LOGO[2] * (0.94 + 0.06 * kl)
        sweep = (ts - 0.95) / 0.65
        rgb, a, glow = A.logo.render(wd, (238, 238, 242), sweep, ease_out_cubic((ts - 0.6) / 0.6),
                                     5 * (1 - kl))
        x, y = SLATE_LOGO[0] - a.shape[1] / 2, SLATE_LOGO[1] - a.shape[0] / 2
        over(frame, rgb, a, x, y, kl)
        if glow is not None:
            screen_add(frame, ndimage.gaussian_filter(glow, 9), 0.9 * kl, int(x), int(y))
    for tx in texts:
        if tx.t_in >= SLATE_T:
            tx.draw(frame, t)
    m, trgb, ta = A.cta
    kc = ease_out_back((ts - 1.4) / 0.45)
    if kc > 0.01:
        ph, pw = m.shape
        x, y = W / 2 - pw / 2, 1110 - ph / 2 + 18 * (1 - kc)
        over(frame, np.full(3, 248, np.float32), m * 0.94, x, y, clamp01(kc))
        over(frame, trgb, ta, x, y, clamp01(kc))


def bloom(frame, amount):
    small = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    s = np.asarray(small, np.float32)
    bright = np.clip((s - 165) / 90, 0, 1)
    b = Image.fromarray((bright * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8))
    b = np.asarray(b.resize((W, H), Image.BILINEAR), np.float32) / 255
    frame += (255 - frame) * np.clip(b * amount, 0, 1)


def render_frame(t, A, texts):
    env, bolts, sx, sy = flash_state(t)
    frame = grade_plate(A.plate(t))
    for s, spec in bolts:                                   # bolts live in the sky
        b, g = A.bolt_at(spec)
        frame += b * min(1.0, s * 1.4)
        frame += g[..., None] * np.array([150, 140, 190], np.float32) * s
    screen_add(frame, A.rain_far.render(t), 0.55)
    if t < LINEUP_T:
        if t >= 1.55:
            frame += (255 - frame) * (A.glow[..., None] * 0.36 * ease_out_cubic((t - 1.55) / 0.6))
        A.mist_back.draw(frame, t)
        if t >= 1.6:
            draw_layout(frame, A, t, texts, env)
    else:
        frame += (255 - frame) * (A.glow_end[..., None] * 0.36)
        A.mist_back.draw(frame, t)
        draw_endcard(frame, A, t, texts, env)
    A.mist_front.draw(frame, t)
    screen_add(frame, A.rain_near.render(t), 0.42)
    if t >= SLATE_T:
        draw_slate(frame, A, t, texts)
    logo_layer(frame, A, t)
    for tx in texts:                                       # cold-open tagline
        if tx.t_in < 1.6:
            tx.draw(frame, t)
    if env > 0.02:
        bloom(frame, env * 0.9)
        frame *= 1 + 0.18 * env
        frame += 255 * 0.14 * min(env, 1.5)
    frame *= A.vignette
    frame += A.grain[int(t * FPS) % len(A.grain)][..., None]
    out = np.clip(frame, 0, 255).astype(np.uint8)
    if env > 0.35:                                         # chromatic split on the strike
        k = int(min(env, 1.4) * 4)
        out[..., 0] = np.roll(out[..., 0], k, axis=1)
        out[..., 2] = np.roll(out[..., 2], -k, axis=1)
    if abs(sx) > 0.5 or abs(sy) > 0.5:                     # camera shake, edges clamped
        ys = np.clip(np.arange(H) - int(round(sy)), 0, H - 1)
        xs = np.clip(np.arange(W) - int(round(sx)), 0, W - 1)
        out = out[ys][:, xs]
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    A = Assets()
    texts = build_texts()
    os.makedirs(P('out', 'preview'), exist_ok=True)
    if mode == 'preview':
        times = [float(x) for x in sys.argv[2:]] or [1.0, 3.5, 8.5, 12.8, 16.4, 19.0]
        for t in sorted(times):
            Image.fromarray(render_frame(t, A, texts)).save(P('out', 'preview', f't{t:05.2f}.png'))
            print('preview', t)
        return
    dst = P('out', 'basic_ad_silent.mp4')
    n = int(round(DUR * FPS))
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                            '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', dst],
                           stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(n):
        enc.stdin.write(render_frame(i / FPS, A, texts).tobytes())
        if i % 30 == 0:
            print(f'frame {i}/{n}  {time.time() - t0:.0f}s', flush=True)
    enc.stdin.close()
    enc.wait()
    print('wrote', dst, f'in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
