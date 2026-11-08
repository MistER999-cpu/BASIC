#!/usr/bin/env python3
"""Tracksuit ad - base edit. Composites every layer and encodes 1080x1920.

    python3 render.py preview 2.5 8.5 12.5     # stills -> out/preview/
    python3 render.py full                     # -> out/tracksuit_ad_base.mp4

Structure follows the reference ad: a model on the left, the ghost-mannequin
outfit top-right, colour dots under it, and a French headline that builds word
by word while model, outfit and active dot swap together on the beat. The
storm sky replaces the reference's plain white backdrop; a frosted-glass column
plays the role of its white card so the dark colourways and the text stay
readable against the clouds.

Every animation is a pure function of t, so any frame can be rendered alone.
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
DUR = 15.0

# ---------------------------------------------------------------- timeline
BEAT = 0.6                      # 100 BPM grid: every swap lands on a beat
SHOTS = [                       # (start, end, colourway)
    (0.0, 3.0, 'prune'),
    (3.0, 4.8, 'choco'),
    (4.8, 6.6, 'noir'),
    (6.6, 7.8, 'prune'),
    (7.8, 9.0, 'choco'),
    (9.0, 10.2, 'noir'),
]
END_CARD = 10.2
LIGHTNING = [                   # (t, strength, bolt offset (dx, dy) or None)
    (6.6, 0.55, (0, 0)),        # card change - the plate opens on its own bolt
    (10.2, 1.35, (250, -330)),  # cut to the line-up, bright enough to hide the cut;
                                # bolt moved into open sky, clear of the heads
    (12.9, 0.35, None),         # distant flicker while the CTA holds
]

ORDER = ['prune', 'choco', 'noir']
DOT_RGB = {                     # the garments as they read on screen (median of
    'prune': (0x55, 0x2A, 0x3D),  # each model's torso) - the swatch should match
    'choco': (0x58, 0x3B, 0x3C),  # what the viewer is looking at, and these
    'noir':  (0x35, 0x31, 0x38),  # separate better than the darker sheet masters
}
MODEL = {'prune': 'M1_prune', 'noir': 'M2_noir', 'choco': 'M3_choco'}

# ---------------------------------------------------------------- layout
PANEL = dict(x=576, y=168, w=468, h=1584, r=44)      # frosted column, right
PCX = PANEL['x'] + PANEL['w'] // 2
GHOST_BOX = (460, 800)                                 # max w, h inside panel
GHOST_TOP = 196
DOT_Y = 1004
DOT_GAP = 90
DOT_D, DOT_D_ACTIVE = 44, 58                           # active also gets a ring
TEXT_X = PANEL['x'] + 30                               # text block left edge
TEXT_W = PANEL['w'] - 60
MODEL_H = 1400                                         # rendered person height
MODEL_FEET = 1734
MODEL_CX = 272                                         # where the torso centres
LINEUP_H = 990                                         # end card person height
CTA_Y = 640                                            # end card pill centre

FONT_DIR = '/usr/share/fonts/opentype/inter/'
NNBSP = ' '                                       # French: espace fine

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

# ---------------------------------------------------------------- compositing
def over(dst, rgb, a, x, y, opacity=1.0):
    """Alpha-composite rgb (h,w,3 float) with a (h,w float) onto dst at (x,y)."""
    if opacity <= 0:
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
    d += rgb[y0 - y:y1 - y, x0 - x:x1 - x] * sa


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


def circle(d, rgb, ring=0.0, ss=4):
    """Anti-aliased swatch dot. ring in [0,1] grows the 'selected' outline:
    a thin ring in the swatch's own colour, separated by a gap - the usual
    e-commerce selected-swatch look, which reads on light glass where a white
    ring would vanish."""
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

# ---------------------------------------------------------------- text
class Text:
    """One line or word: rendered once, then faded/slid in and out over time."""
    def __init__(self, s, font, size, rgb, x, y, t_in, t_out=None, anchor='ls',
                 rise=18, dur=0.24, shadow=None):
        f = ImageFont.truetype(FONT_DIR + font, size)
        self.width = f.getlength(s)
        asc, desc = f.getmetrics()
        pad = 24
        im = Image.new('RGBA', (int(self.width) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pad, pad), s, font=f, fill=tuple(rgb) + (255,))
        if shadow:                                       # (blur, opacity)
            a = im.split()[3].filter(ImageFilter.GaussianBlur(shadow[0]))
            sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
            sh.putalpha(a.point(lambda v: int(v * shadow[1])))
            im = Image.alpha_composite(sh, im)
        self.rgb, self.a = rgba_arrays(im)
        # anchor: 'ls' = left/baseline, 'ms' = centre/baseline, 'rs' = right/baseline
        ox = {'l': 0, 'm': self.width / 2, 'r': self.width}[anchor[0]]
        self.x, self.y = x - ox - pad, y - asc - pad
        self.t_in, self.t_out, self.rise, self.dur = t_in, t_out, rise, dur

    def draw(self, frame, t, dx=0.0):
        if t < self.t_in:
            return
        k = ease_out_cubic((t - self.t_in) / self.dur)
        op, dy = k, self.rise * (1 - k)
        if self.t_out is not None and t >= self.t_out:
            k2 = ease_in_out((t - self.t_out) / 0.18)
            op *= 1 - k2
            dy -= 10 * k2
        over(frame, self.rgb, self.a, self.x + dx, self.y + dy, op)


def build_texts():
    D, L, B, M = 'InterDisplay-Light.otf', 'Inter-Light.otf', 'InterDisplay-Bold.otf', 'Inter-Medium.otf'
    ink, ink2, grey = (20, 20, 22), (44, 44, 48), (150, 150, 156)
    items = []

    # card 1 - staggered headline, as in the reference: three lines that
    # zig-zag (indented / flush / pushed right) rather than sharing one edge.
    # Sized to the widest arrangement that fits the column.
    l1, l2, l3a, l3b = 'douce,', 'essentielle', 'et', 'iconique' + NNBSP + ':'
    ind1, ind3 = 0.20, 0.12                  # indents, as fractions of line 2
    for size in range(76, 40, -1):
        f = ImageFont.truetype(FONT_DIR + D, size)
        w1, w2 = f.getlength(l1), f.getlength(l2)
        w3 = f.getlength(l3a + ' ' + l3b)
        block = max(ind1 * w2 + w1, w2, ind3 * w2 + w3)
        if block <= TEXT_W:
            break
    bx = TEXT_X + (TEXT_W - block) / 2
    y1, lh = 1226, int(size * 1.12)
    t_out1 = 6.36
    x3 = bx + ind3 * w2
    items += [
        Text(l1, D, size, ink, bx + ind1 * w2, y1, 0.75, t_out1),
        Text(l2, D, size, ink, bx, y1 + lh, 1.05, t_out1),
        Text(l3a, D, size, ink, x3, y1 + 2 * lh, 1.35, t_out1),
        Text(l3b, D, size, ink, x3 + w3, y1 + 2 * lh, 1.50, t_out1, anchor='rs'),
    ]
    sub = ['on vous révèle la pièce', 'qui manquait à votre', 'garde-robe d’hiver']
    sy = y1 + 2 * lh + 78
    for i, s in enumerate(sub):
        items.append(Text(s, L, 34, ink2, bx, sy + i * 47, 2.0 + 0.25 * i, t_out1, rise=10))

    # card 2 - the product line: grey word first, then the bold statement
    bs, by, blh = 60, 1232, 70
    items.append(Text('ensemble', B, bs, grey, bx, by, 6.72, 7.24))
    items.append(Text('ensemble', B, bs, ink, bx, by, 7.24, 10.0, rise=0, dur=0.06))
    items.append(Text('oversize à', B, bs, ink, bx, by + blh, 7.30, 10.0))
    items.append(Text('col montant,', B, bs, ink, bx, by + 2 * blh, 7.40, 10.0))
    items.append(Text('évidemment' + NNBSP + '!', L, 42, ink2, bx, by + 3 * blh + 10, 7.75, 10.0, rise=10))

    # end card - white over the storm, centred. Stacked title -> colours ->
    # CTA -> line-up so every word sits inside Instagram's safe area: below
    # the top ~250px (Stories header) and well above the bottom band where
    # Reels and Stories lay the caption and the ad's own CTA button.
    sh = (14, 0.45)
    items.append(Text('1 ensemble.', B, 96, (255, 255, 255), W / 2, 356, 10.62, anchor='ms', shadow=sh))
    items.append(Text('3 couleurs.', B, 96, (255, 255, 255), W / 2, 462, 10.92, anchor='ms', shadow=sh))
    items.append(Text('prune  ·  chocolat  ·  noir', 'InterDisplay-Light.otf', 40, (240, 240, 244),
                      W / 2, 542, 11.30, anchor='ms', shadow=(10, 0.4), rise=10))
    return items

# ---------------------------------------------------------------- assets
class Assets:
    def __init__(self):
        t0 = time.time()
        self.storm_iter = None
        self.storm_idx = -1
        self.storm_frame = None
        self.models, self.torso_x, self.feet_x = {}, {}, {}
        for key, name in MODEL.items():
            im = Image.open(P('build/cutouts', name + '.png')).convert('RGBA')
            arr = np.asarray(im, np.float32)
            # studio light is warm-neutral, the storm is cool: nudge the
            # models toward the plate so they sit in the same weather
            arr[..., :3] *= np.array([0.985, 0.995, 1.025], np.float32)
            im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
            a = arr[..., 3] > 128
            h = a.shape[0]
            # place each model by her torso, not her bounding box - a hand on
            # the hip or a walking stride widens the box to one side
            self.torso_x[key] = np.median(np.where(a[int(h * .30):int(h * .55)])[1]) / a.shape[1]
            self.feet_x[key] = np.median(np.where(a[int(h * .93):])[1]) / a.shape[1]
            self.models[key] = im
        self.model_scale = MODEL_H / max(im.height for im in self.models.values())
        self.ghosts = self.load_ghosts()
        self.bolt, self.bolt_glow = self.load_bolt()
        self._bolts = {}
        self.glow = self.make_glow()
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.glow_end = np.exp(-(((xx - W / 2) / 700) ** 2 + ((yy - 1050) / 760) ** 2))
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
        yy, xx = np.mgrid[0:ph, 0:pw].astype(np.float32)
        diag = (xx / pw * 0.55 + yy / ph)            # 0 at top-left
        self.panel_sheen = np.clip(1 - diag / 0.45, 0, 1) ** 2 * 14
        rng = np.random.default_rng(7)
        self.grain = [rng.normal(0, 2.2, (H, W)).astype(np.float32) for _ in range(6)]
        self.lineup = self.make_lineup_layers()
        self.cta = self.make_cta()
        print(f'assets ready in {time.time() - t0:.1f}s')

    # storm plate, streamed (it is 2 GB decoded)
    def storm(self, t):
        idx = min(int(t * 24 + 1e-6), 357)
        if self.storm_iter is None or idx < self.storm_idx:
            if self.storm_iter is not None:
                self.storm_iter.kill()
            self.storm_iter = subprocess.Popen(
                ['ffmpeg', '-v', 'error', '-i', P('assets/background/storm.mp4'),
                 '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
            self.storm_idx = -1
        while self.storm_idx < idx:
            buf = self.storm_iter.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            self.storm_frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.storm_idx += 1
        return self.storm_frame

    def load_ghosts(self):
        """Key every ghost frame once (cached), at display size."""
        cache = P('build', f'ghosts_{GHOST_BOX[0]}x{GHOST_BOX[1]}.npz')
        if os.path.exists(cache):
            z = np.load(cache)
            return {k: z[k] for k in ORDER}
        print('keying ghost clips (first run only)...')
        out = {}
        crop = (75, 246, 978, 1701)        # union bbox of all three clips + 40px
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
                if k == 'choco':
                    # the brown recolour came out ~16 levels darker than the
                    # master #472E31 measured on the product sheet - lift it
                    rgb = rgb * 1.15 + 8
                rgba = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
                im = resize_rgba(Image.fromarray(rgba, 'RGBA'), size)
                frames.append(np.asarray(im))
            out[k] = np.stack(frames)
        np.savez(cache, **out)
        return out

    def ghost(self, key, t):
        """Ghost frame at time t, looping with a 6-frame crossfade over the seam."""
        clip = self.ghosts[key]
        n, X = len(clip), 6
        period = n - X
        f = t * 24
        if f < period:
            fr = clip[int(f)].astype(np.float32)
        else:
            k = f % period
            if k < X:
                w = k / X
                fr = clip[period + int(k)].astype(np.float32) * (1 - w) + clip[int(k)].astype(np.float32) * w
            else:
                fr = clip[int(k)].astype(np.float32)
        return fr[..., :3], fr[..., 3] / 255.0

    def load_bolt(self):
        """The bolt from the plate's first frame, as an additive light layer."""
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
        glow = ndimage.gaussian_filter(m, 40) * 60
        glow = glow / glow.max()
        return bolt, glow

    def bolt_at(self, dx, dy):
        key = (dx, dy)
        if key not in self._bolts:
            self._bolts[key] = (shifted(self.bolt, dx, dy), shifted(self.bolt_glow, dx, dy))
        return self._bolts[key]

    def make_glow(self):
        """Soft break in the clouds behind the model, so dark fabric reads."""
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        g = np.exp(-(((xx - MODEL_CX) / 470) ** 2 + ((yy - 860) / 820) ** 2))
        return g

    def make_lineup_layers(self):
        """End card: the three looks side by side, M3 in front."""
        s = LINEUP_H / MODEL_H * self.model_scale
        layers = []
        spec = [('prune', 268, 0), ('noir', 822, 0), ('choco', 540, 1)]
        for key, cx, z in spec:
            im = self.models[key]
            im = resize_rgba(im, (int(im.width * s), int(im.height * s)))
            rgb, a = rgba_arrays(im)
            layers.append((key, cx, z, rgb, a))
        return sorted(layers, key=lambda l: l[2])

    def make_cta(self):
        f = ImageFont.truetype(FONT_DIR + 'Inter-Medium.otf', 36)
        label = 'disponible maintenant'
        tw = f.getlength(label)
        pw, ph = int(tw + 96), 92
        m = rounded_mask(pw, ph, ph // 2)
        im = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pw / 2, ph / 2 + 1), label, font=f, fill=(24, 24, 28, 255), anchor='mm')
        trgb, ta = rgba_arrays(im)
        return m, trgb, ta

# ---------------------------------------------------------------- scene
def shot_at(t):
    for i, (a, b, k) in enumerate(SHOTS):
        if a <= t < b:
            return i, a, b, k
    return len(SHOTS) - 1, SHOTS[-1][0], SHOTS[-1][1], SHOTS[-1][2]


def lightning_env(t):
    """Flash envelope (a strike and one re-strike) and the bolts to draw."""
    env, bolts = 0.0, []
    for t0, s, offset in LIGHTNING:
        dt = t - t0
        if dt < 0 or s <= 0:
            continue
        e = math.exp(-dt / 0.05)
        if dt > 0.11:
            e += 0.6 * math.exp(-(dt - 0.11) / 0.09)
        env += s * e
        if offset is not None and s * e > 0.001:
            bolts.append((s * e, offset))
    return env, bolts


def shifted(layer, dx, dy):
    """layer moved by (dx, dy), zero-filled - for re-placing the bolt."""
    out = np.zeros_like(layer)
    h, w = layer.shape[:2]
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = layer[ys, xs]
    return out


def grade_storm(plate):
    """Lift the plate a touch - a bright storm, not a night one."""
    f = plate.astype(np.float32)
    return f * 0.94 + 14


def draw_panel(frame, A, dx, opacity=1.0):
    x, y, pw, ph = PANEL['x'] + dx, PANEL['y'], PANEL['w'], PANEL['h']
    xi = int(round(x))
    # drop shadow, then frosted glass sampled from what is behind it
    pad = 60
    sh = A.panel_shadow * 0.20 * opacity
    over(frame, np.zeros(sh.shape + (3,), np.float32), sh, xi - pad, y + 18 - pad)
    x0, x1 = max(xi, 0), min(xi + pw, W)
    if x1 <= x0:
        return
    region = frame[y:y + ph, x0:x1]
    small = Image.fromarray(np.clip(region, 0, 255).astype(np.uint8)).resize(
        (max(1, (x1 - x0) // 4), ph // 4), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(9))
    blur = np.asarray(small.resize((x1 - x0, ph), Image.BILINEAR), np.float32)
    # milkier toward the text at the bottom, clearer at the top so the storm
    # still moves behind the outfit - plus a faint diagonal sheen
    tint = np.linspace(0.60, 0.76, ph, dtype=np.float32)[:, None, None]
    glass = blur * 1.06 * (1 - tint) + np.array([250, 250, 252], np.float32) * tint
    glass += A.panel_sheen[:, x0 - xi:x1 - xi, None]
    m = A.panel_mask[:, x0 - xi:x1 - xi]
    over(frame, glass, m, x0, y, opacity)
    ring = A.panel_ring[:, x0 - xi:x1 - xi]
    over(frame, np.full(ring.shape + (3,), 255, np.float32), ring * 0.65, x0, y, opacity)


def contact_shadow(frame, cx, feet_y, width, strength, opacity=1.0):
    """Soft ellipse under the shoes, so the models stand on the mist."""
    sw = int(width)
    sh_img = Image.new('L', (sw + 80, 120), 0)
    ImageDraw.Draw(sh_img).ellipse([40, 47, sw + 40, 73], fill=255)
    sh = np.asarray(sh_img.filter(ImageFilter.GaussianBlur(15)), np.float32) / 255 * strength
    over(frame, np.full(sh.shape + (3,), 30, np.float32), sh, cx - sw / 2 - 40, feet_y - 60, opacity)


def draw_model(frame, A, key, scale, dx, opacity=1.0):
    im = A.models[key]
    s = A.model_scale * scale
    w, h = int(im.width * s), int(im.height * s)
    rgb, a = rgba_arrays(resize_rgba(im, (w, h)))
    x = MODEL_CX - A.torso_x[key] * w + dx
    y = MODEL_FEET - h
    contact_shadow(frame, x + A.feet_x[key] * w, MODEL_FEET, 360 * scale, 0.42, opacity)
    over(frame, rgb, a, x, y, opacity)


def draw_ghost(frame, A, t, key, prev_key, flip, dx, scale_x=1.0):
    """The floating outfit. flip in [0,1]: 3D card turn swapping colourways."""
    k = key if flip >= 0.5 else prev_key
    rgb, a = A.ghost(k, t)
    sx = scale_x * max(abs(math.cos(math.pi * flip)), 0.02)
    h, w = a.shape
    if sx < 0.999:
        nw = max(2, int(w * sx))
        rgba = np.dstack([rgb, a[..., None] * 255]).astype(np.uint8)
        im = resize_rgba(Image.fromarray(rgba, 'RGBA'), (nw, h))
        rgb, a = rgba_arrays(im)
        rgb *= 0.72 + 0.28 * sx                         # edge-on reads darker
    x = PCX + dx - a.shape[1] / 2
    over(frame, rgb, a, x, GHOST_TOP)


def draw_dots(frame, active, prev, k, dx, intro):
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
        ring = ease_out_cubic(k) if key == active else 0.0
        rgb, a = circle(d, DOT_RGB[key], ring)
        cx = PCX + dx + (i - 1) * DOT_GAP
        over(frame, rgb, a, cx - a.shape[1] / 2, DOT_Y - a.shape[0] / 2)


def render_frame(t, A, texts):
    frame = grade_storm(A.storm(t))
    env, bolts = lightning_env(t)
    # the bolt and its glow live in the sky, behind everything else
    for strength, (dx, dy) in bolts:
        bolt, glow = A.bolt_at(dx, dy)
        frame += bolt * min(1.0, strength * 1.4)
        frame += glow[..., None] * np.array([150, 140, 190], np.float32) * strength

    if t < END_CARD:
        idx, ts, te, key = shot_at(t)
        prev_key = SHOTS[idx - 1][2] if idx > 0 else key
        # the break in the clouds behind the model
        frame += (255 - frame) * (A.glow[..., None] * 0.36)
        # intro: model from the left, glass column from the right
        mdx = -660 * (1 - ease_out_expo(t / 0.7))
        pdx = 600 * (1 - ease_out_expo((t - 0.08) / 0.7))
        draw_panel(frame, A, pdx)
        # ghost: flips in during the intro, card-turns on every swap
        intro_sx = ease_out_cubic((t - 0.2) / 0.5)
        flip, fk, fp = 1.0, key, prev_key
        for j in range(1, len(SHOTS)):
            tsw = SHOTS[j][0]
            if tsw - 0.12 <= t < tsw + 0.12:
                flip = (t - (tsw - 0.12)) / 0.24
                fk, fp = SHOTS[j][2], SHOTS[j - 1][2]
        draw_ghost(frame, A, t, fk, fp, flip if flip < 1 else 1.0, pdx, intro_sx)
        # dots
        intro = [ease_out_back((t - 0.42 - 0.08 * i) / 0.3) for i in range(3)]
        dk = (t - ts) / 0.18 if idx > 0 else (t - 0.66) / 0.25
        draw_dots(frame, key, prev_key if idx > 0 else None, dk, pdx, intro)
        for tx in texts:
            if tx.t_in < END_CARD:
                tx.draw(frame, t, pdx)
        # model: slow push-in through the shot, small settle on each cut
        push = 1 + 0.022 * ((t - ts) / (te - ts))
        pop = 0.022 * math.exp(-(t - ts) / 0.09) if idx > 0 else 0.0
        draw_model(frame, A, key, push + pop, mdx)
    else:
        te = t - END_CARD
        frame += (255 - frame) * (A.glow_end[..., None] * 0.36)
        push = 1 + 0.025 * (te / (DUR - END_CARD))
        # the line-up is already standing when the flash clears, rising the
        # last few pixels into place - a slow fade would read as a ghost
        for n, (key, cx, z, rgb, a) in enumerate(A.lineup):
            k = ease_out_cubic((te - 0.04 * n) / 0.5)
            op = 1.0
            h, w = a.shape
            hh, ww = int(h * push), int(w * push)
            rgba = np.dstack([rgb, a[..., None] * 255]).astype(np.uint8)
            rgb2, a2 = rgba_arrays(resize_rgba(Image.fromarray(rgba, 'RGBA'), (ww, hh)))
            x = cx - A.torso_x[key] * ww
            feet = 1716 + 50 * (1 - k)
            contact_shadow(frame, x + A.feet_x[key] * ww, 1716, 300 * push, 0.38, op)
            over(frame, rgb2, a2, x, feet - hh, op)
        for tx in texts:
            if tx.t_in >= END_CARD:
                tx.draw(frame, t)
        # call to action
        m, trgb, ta = A.cta
        k = ease_out_back((te - 1.7) / 0.4)
        if k > 0.01:
            ph, pw = m.shape
            x, y = W / 2 - pw / 2, CTA_Y - ph / 2 + 20 * (1 - k)
            over(frame, np.full((ph, pw, 3), 250, np.float32), m * 0.92, x, y, clamp01(k))
            over(frame, trgb, ta, x, y, clamp01(k))

    # the flash itself lights everything, models included
    if env > 0.001:
        frame *= 1 + 0.22 * env
        frame += 255 * 0.16 * min(env, 1.5)
    # one grain over everything ties the cutouts, the glass and the plate together
    frame += A.grain[int(t * FPS) % len(A.grain)][..., None]
    return np.clip(frame, 0, 255).astype(np.uint8)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    A = Assets()
    texts = build_texts()
    os.makedirs(P('out', 'preview'), exist_ok=True)
    if mode == 'preview':
        times = [float(x) for x in sys.argv[2:]] or [2.6, 8.4, 12.5]
        for t in sorted(times):
            img = render_frame(t, A, texts)
            Image.fromarray(img).save(P('out', 'preview', f't{t:05.2f}.png'))
            print('preview', t)
        return
    dst = P('out', 'tracksuit_ad_base_silent.mp4')
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
