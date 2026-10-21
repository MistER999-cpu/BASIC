#!/usr/bin/env python3
"""Render « Du soleil à la neige », the BASIC tank-top reel (1080x1920, 30 fps).

    python3 tools/render.py                       # full render -> build/video.mp4 (silent)
    python3 tools/render.py --stills 0.5,3.2,8.8  # PNG stills -> build/stills/

One chocolate, sable, écru and noir tank top per season. Each season opens on
the tank alone, then the outfit is rebuilt one piece per beat (120 BPM) as a
fresh die-cut sticker. The backgrounds keep moving underneath - sun, sea,
rain, snow - while the stickers stay put, which is what sells the collage.

Text lives between 14% and 65% of the frame height: Instagram's caption and
buttons cover the rest of a Reel ad.
"""
import os, sys, json, math, subprocess, hashlib
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets', 'source')
FONTS = os.path.join(ROOT, 'assets', 'fonts')
STK = os.path.join(ROOT, 'build', 'stickers')
BUILD = os.path.join(ROOT, 'build')

W, H, FPS = 1080, 1920, 30
DUR = 13.5
NB = ' '          # French puts a no-break space before ? ! : ;

INK = np.array([28, 26, 27]) / 255
PAPER = np.array([251, 248, 242]) / 255
ECRU = np.array([239, 232, 220]) / 255

# ---------------------------------------------------------------- timeline --
# 120 BPM, one beat = 0.5 s. Every swap lands on a beat.
SEASONS = [
    dict(key='ete', bg='bg-ete.jpg', t0=0.0, t1=2.5, fx='sun', icon='sun', hook=True,
         steps=[(0.0, 'model-01-chocolat', None, '31°'),
                (1.5, 'model-02-chocolat-manchette', '+ MANCHETTE DORÉE', '31°')]),
    dict(key='fin', bg='bg-fin-ete.jpg', t0=2.5, t1=4.0, fx='sea', icon='sunset', label='Fin d’été',
         steps=[(2.5, 'model-03-sable', None, '26°'),
                (3.0, 'model-04-sable-chemise', '+ CHEMISE EN POPELINE', '24°')]),
    dict(key='aut', bg='bg-automne.jpg', t0=4.0, t1=6.5, fx='rain', icon='rain', label='Automne',
         steps=[(4.0, 'model-05-ecru', None, '19°'),
                (4.5, 'model-06-ecru-blazer', '+ BLAZER EN LAINE', '16°'),
                (5.5, 'model-07-ecru-trench', '+ TRENCH CAMEL', '12°')]),
    dict(key='hiv', bg='bg-hiver.jpg', t0=6.5, t1=9.5, fx='snow', icon='snow', label='Hiver', punch=8.5,
         steps=[(6.5, 'model-08-noir', None, '5°'),
                (7.0, 'model-09-noir-gilet', '+ GILET EN MAILLE', '2°'),
                (7.5, 'model-10-noir-manteau', '+ MANTEAU EN LAINE', '−2°')]),
]
FINAL = dict(t0=9.5, t1=12.0, minis=[9.5, 9.75, 10.0, 10.25], tag1=10.5, tag2=10.75)
END = dict(t0=12.0, t1=DUR)
FINALE_LOOKS = [('model-01-chocolat', 'CHOCOLAT'), ('model-03-sable', 'SABLE'),
                ('model-05-ecru', 'ÉCRU'), ('model-08-noir', 'NOIR')]

# sticker rotation per look: hand-placed, never twice the same
LOOK_ROT = {'model-01-chocolat': -1.2, 'model-02-chocolat-manchette': 0.9,
            'model-03-sable': 1.1, 'model-04-sable-chemise': -0.8,
            'model-05-ecru': -1.0, 'model-06-ecru-blazer': 0.7, 'model-07-ecru-trench': -0.5,
            'model-08-noir': 1.2, 'model-09-noir-gilet': -0.9, 'model-10-noir-manteau': 0.6}

STICKER_TOP = 460      # top of the white die-cut edge, frame px
MARGIN = 40            # extra transparent room around a sticker for its shadow


def events():
    """Every hit the sound design must land on: (time, kind)."""
    ev = []
    for s in SEASONS:
        ev.append((s['t0'], 'cut' if s['t0'] > 0 else 'open'))
        for t, look, tag, temp in s['steps'][1:]:
            ev.append((t, 'slap'))
        if s.get('hook'):
            ev += [(0.10, 'tick'), (0.35, 'tick')]
        if s.get('punch'):
            ev.append((s['punch'], 'punch'))
    ev.append((FINAL['t0'], 'cut'))
    ev += [(t, 'slap') for t in FINAL['minis'][1:]]
    ev += [(FINAL['tag1'], 'tick'), (FINAL['tag2'], 'tick')]
    ev.append((END['t0'], 'end'))
    return sorted(ev)


# ------------------------------------------------------------- typography --
def font(name, size, wght=500, opsz=96):
    f = ImageFont.truetype(os.path.join(FONTS, name), size, layout_engine=ImageFont.Layout.RAQM)
    axes = f.get_variation_axes()
    if len(axes) == 2:
        f.set_variation_by_axes([wght, opsz])
    else:
        f.set_variation_by_axes([wght])
    return f


def run_length(f, s, track):
    if not track:
        return f.getlength(s)
    return sum(f.getlength(c) for c in s) + track * (len(s) - 1)


def draw_run(d, x, y, s, f, fill, track):
    if not track:
        d.text((x, y), s, font=f, fill=fill, anchor='ls')
        return x + f.getlength(s)
    for c in s:
        d.text((x, y), c, font=f, fill=fill, anchor='ls')
        x += f.getlength(c) + track
    return x - track


def supersample_round_rect(w, h, r, k=4):
    m = Image.new('L', (w * k, h * k), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * k - 1, h * k - 1], r * k, fill=255)
    return np.array(m.resize((w, h), Image.LANCZOS), np.float32) / 255


def with_shadow(rgb, a, off=(5, 9), blur=9, op=0.30, margin=28):
    """Premultiplied RGBA with a soft drop shadow baked underneath."""
    h, w = a.shape
    Hc, Wc = h + 2 * margin, w + 2 * margin
    sh = np.zeros((Hc, Wc), np.float32)
    sh[margin + off[1]:margin + off[1] + h, margin + off[0]:margin + off[0] + w] = a
    sh = cv2.GaussianBlur(sh, (0, 0), blur) * op
    out = np.zeros((Hc, Wc, 4), np.float32)
    shade = np.array([0.09, 0.07, 0.06], np.float32)
    out[..., :3] = shade * sh[..., None]
    out[..., 3] = sh
    fg = np.zeros((Hc, Wc, 4), np.float32)
    fg[margin:margin + h, margin:margin + w, :3] = rgb * a[..., None]
    fg[margin:margin + h, margin:margin + w, 3] = a
    out = fg + out * (1 - fg[..., 3:4])
    return out


def strip(runs, fill=PAPER, ink=INK, pad=(30, 18), radius=12, size_ref=None, dot=None):
    """A label-maker strip: paper, text, shadow. runs = [(text, font, tracking)]."""
    asc = max(f.getmetrics()[0] for _, f, _ in runs)
    # cap height of the first font is what the eye centres on
    f0 = runs[0][1]
    cap = f0.getbbox('H', anchor='ls')
    cap_h = -cap[1]
    desc = max(f.getmetrics()[1] for _, f, _ in runs)
    tw = sum(run_length(f, s, tr) for s, f, tr in runs)
    dot_w = 0
    if dot is not None:
        dot_w = int(cap_h * 0.95) + int(cap_h * 0.6)
    w = int(math.ceil(tw + 2 * pad[0] + dot_w))
    h = int(math.ceil(cap_h + 2 * pad[1] + cap_h * 0.55))
    shape = supersample_round_rect(w, h, radius)
    img = Image.new('RGB', (w, h), tuple(int(c * 255) for c in fill))
    d = ImageDraw.Draw(img)
    base = pad[1] + cap_h + cap_h * 0.275
    x = pad[0]
    if dot is not None:
        r = cap_h * 0.475
        cy = base - cap_h / 2
        k = 4
        m = Image.new('RGBA', (int(2 * r * k + 8), int(2 * r * k + 8)), (0, 0, 0, 0))
        md = ImageDraw.Draw(m)
        md.ellipse([4, 4, 4 + 2 * r * k, 4 + 2 * r * k], fill=tuple(int(c * 255) for c in dot) + (255,),
                   outline=(28, 26, 27, 70), width=int(1.4 * k))
        m = m.resize((int(m.width / k), int(m.height / k)), Image.LANCZOS)
        img.paste(m, (int(x), int(cy - m.height / 2)), m)
        x += dot_w
    col = tuple(int(c * 255) for c in ink)
    for s, f, tr in runs:
        x = draw_run(d, x, base, s, f, col, tr)
    rgb = np.array(img, np.float32) / 255
    return with_shadow(rgb, shape)


def pill(icon, temp, F):
    """Black temperature pill: line icon + degrees, écru on ink."""
    f = F['temp']
    cap = -f.getbbox('8', anchor='ls')[1]
    tw = f.getlength(temp)
    ic = int(cap * 1.25)
    padx, pady = 26, 20
    gap = 16
    w = int(padx * 2 + ic + gap + tw + 4)
    h = int(cap + 2 * pady + 8)
    shape = supersample_round_rect(w, h, h // 2)
    img = Image.new('RGB', (w, h), (28, 26, 27))
    d = ImageDraw.Draw(img)
    base = (h + cap) / 2
    d.text((padx + ic + gap, base), temp, font=f, fill=(239, 232, 220), anchor='ls')
    icon_img = draw_icon(icon, ic)
    img.paste(icon_img, (padx, int((h - ic) / 2)), icon_img)
    rgb = np.array(img, np.float32) / 255
    return with_shadow(rgb, shape)


def draw_icon(kind, size):
    k = 6
    S = size * k
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (239, 232, 220, 255)
    lw = int(S * 0.075)
    cx = cy = S / 2
    if kind in ('sun', 'sunset'):
        if kind == 'sun':
            r = S * 0.2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=lw)
            for i in range(8):
                a = i * math.pi / 4
                r0, r1 = S * 0.31, S * 0.45
                d.line([cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                        cx + r1 * math.cos(a), cy + r1 * math.sin(a)], fill=c, width=lw)
        else:
            hy = S * 0.66
            r = S * 0.22
            d.arc([cx - r, hy - r, cx + r, hy + r], 180, 360, fill=c, width=lw)
            d.line([S * 0.06, hy, S * 0.94, hy], fill=c, width=lw)
            for a in (-150, -120, -90, -60, -30):
                ar = math.radians(a)
                r0, r1 = S * 0.31, S * 0.43
                d.line([cx + r0 * math.cos(ar), hy + r0 * math.sin(ar),
                        cx + r1 * math.cos(ar), hy + r1 * math.sin(ar)], fill=c, width=lw)
            d.line([S * 0.3, hy + S * 0.14, S * 0.7, hy + S * 0.14], fill=c, width=lw)
    elif kind == 'rain':
        # cloud: three bumps on a flat base
        base = S * 0.56
        d.ellipse([S * 0.14, S * 0.30, S * 0.46, S * 0.62], outline=c, width=lw)
        d.ellipse([S * 0.32, S * 0.16, S * 0.72, S * 0.56], outline=c, width=lw)
        d.ellipse([S * 0.56, S * 0.30, S * 0.88, S * 0.62], outline=c, width=lw)
        # knock out the overlaps so it reads as one outline
        d.rectangle([S * 0.2, S * 0.40, S * 0.82, base], fill=(0, 0, 0, 0))
        d.line([S * 0.24, base + lw / 2, S * 0.80, base + lw / 2], fill=c, width=lw)
        for x in (0.34, 0.52, 0.70):
            d.line([S * x, S * 0.70, S * (x - 0.06), S * 0.88], fill=c, width=lw)
    elif kind == 'snow':
        r = S * 0.44
        for i in range(3):
            a = i * math.pi / 3 + math.pi / 2
            dx, dy = r * math.cos(a), r * math.sin(a)
            d.line([cx - dx, cy - dy, cx + dx, cy + dy], fill=c, width=lw)
            for sgn in (-1, 1):
                ex, ey = cx + sgn * dx * 0.62, cy + sgn * dy * 0.62
                for b in (-0.7, 0.7):
                    bx = math.cos(a + b) * S * 0.12 * sgn
                    by = math.sin(a + b) * S * 0.12 * sgn
                    d.line([ex, ey, ex + bx, ey + by], fill=c, width=int(lw * 0.85))
    return im.resize((size, size), Image.LANCZOS)


def build_fonts():
    return dict(
        hook=font('BodoniModa.ttf', 74, wght=520, opsz=96),
        hook_it=font('BodoniModa-Italic.ttf', 74, wght=520, opsz=96),
        label=font('BodoniModa-Italic.ttf', 90, wght=520, opsz=96),
        punch=font('BodoniModa-Italic.ttf', 150, wght=560, opsz=96),
        tag=font('Jost.ttf', 34, wght=520),
        color=font('Jost.ttf', 30, wght=540),
        temp=font('Jost.ttf', 62, wght=560),
        end1=font('Jost.ttf', 33, wght=500),
        end2=font('Jost.ttf', 31, wght=400),
    )


# ------------------------------------------------------------- compositing --
def place(dst, img, cx, cy, scale=1.0, rot=0.0, opacity=1.0, interp=cv2.INTER_LINEAR):
    """Premultiplied 'over' of img, scaled/rotated about its own centre."""
    if opacity <= 0.002:
        return
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)
    M[0, 2] += cx - w / 2
    M[1, 2] += cy - h / 2
    pts = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float64) @ M.T
    x0 = max(0, int(math.floor(pts[:, 0].min())) - 1)
    y0 = max(0, int(math.floor(pts[:, 1].min())) - 1)
    x1 = min(dst.shape[1], int(math.ceil(pts[:, 0].max())) + 1)
    y1 = min(dst.shape[0], int(math.ceil(pts[:, 1].max())) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    M2 = M.copy()
    M2[0, 2] -= x0
    M2[1, 2] -= y0
    if abs(scale - 1) < 1e-6 and abs(rot) < 1e-6 and float(M[0, 2]).is_integer() and float(M[1, 2]).is_integer():
        out = np.zeros((y1 - y0, x1 - x0, 4), np.float32)
        ox, oy = int(M[0, 2]), int(M[1, 2])
        sx0, sy0 = max(0, x0 - ox), max(0, y0 - oy)
        out[:min(h - sy0, y1 - y0), :min(w - sx0, x1 - x0)] = img[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]
    else:
        out = cv2.warpAffine(img, M2, (x1 - x0, y1 - y0), flags=interp,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    if opacity < 1:
        out *= opacity
    roi = dst[y0:y1, x0:x1]
    roi *= (1 - out[..., 3:4])
    roi += out[..., :3]


def slap(dt, dur=0.34, amp=0.16, spin=5.0):
    """Spring for a sticker being slapped down: big, overshoot, settle."""
    if dt < 0:
        return None
    if dt >= dur:
        return 1.0, 0.0, 1.0
    u = dt / dur
    s = 1 + amp * math.exp(-7 * u) * math.cos(10 * u)
    r = spin * math.exp(-6 * u) * math.cos(8 * u)
    return s, r, min(1.0, dt / 0.045)


def boil(key, frame, amp=1.1, ramp=0.14):
    """Stop-motion life: a tiny hand-placed wobble that changes every 3 frames."""
    h = hashlib.md5(f'{key}:{frame // 3}'.encode()).digest()
    v = [b / 255 * 2 - 1 for b in h[:3]]
    return v[0] * amp, v[1] * amp, v[2] * ramp


# ------------------------------------------------------------------ assets --
class Assets:
    def __init__(self):
        F = build_fonts()
        self.F = F
        meta = json.load(open(os.path.join(STK, 'meta.json')))
        self.pad = meta['pad'] + MARGIN
        self.border = meta['border']
        self.looks = {}
        for name in LOOK_ROT:
            rgba = np.array(Image.open(os.path.join(STK, name + '.png')), np.float32) / 255
            a = rgba[..., 3]
            rgb = rgba[..., :3]
            self.looks[name] = with_shadow(rgb, a, off=(9, 16), blur=15, op=0.36, margin=MARGIN)
        # visible sticker size (die-cut edge), used for layout
        h, w = self.looks['model-01-chocolat'].shape[:2]
        self.look_size = (w, h)
        self.vis_top = self.pad - self.border         # die-cut edge, from image top
        self.vis_h = h - 2 * (self.pad - self.border)

        # backgrounds, linear-ish float in 0..1
        self.bgs = {}
        for s in SEASONS:
            self.bgs[s['key']] = np.array(Image.open(os.path.join(SRC, s['bg'])).convert('RGB'), np.float32) / 255
        self.bgs['studio'] = np.array(Image.open(os.path.join(SRC, 'bg-studio.jpg')).convert('RGB'), np.float32) / 255
        self.sun_prep()

        # tank colours, sampled from the shots themselves for the end-card dots
        self.tank = {}
        for look, nm in FINALE_LOOKS:
            im = np.array(Image.open(os.path.join(SRC, look + '.jpg')).convert('RGB'), np.float32) / 255
            self.tank[nm] = np.median(im[660:820, 480:640].reshape(-1, 3), axis=0)

        # text stickers
        self.hook1 = strip([('Trop froid pour', F['hook'], 0)])
        self.hook2 = strip([('un ', F['hook'], 0), ('débardeur', F['hook_it'], 0), (NB + '?', F['hook'], 0)])
        self.labels = {s['key']: strip([(s['label'], F['label'], 0)], pad=(34, 16))
                       for s in SEASONS if s.get('label')}
        self.punch = strip([('Jamais.', F['punch'], 0)], fill=INK, ink=ECRU, pad=(46, 24), radius=16)
        self.tags = {}
        for s in SEASONS:
            for t, look, tag, temp in s['steps']:
                if tag:
                    self.tags[tag] = strip([(tag, F['tag'], 3.2)], pad=(24, 16), radius=8)
        self.pills = {}
        for s in SEASONS:
            for t, look, tag, temp in s['steps']:
                self.pills[(s['icon'], temp)] = pill(s['icon'], temp, F)
        self.tag1 = strip([('Un débardeur.', F['hook'], 0)])
        self.tag2 = strip([('Toutes les ', F['hook'], 0), ('saisons.', F['hook_it'], 0)])
        self.colortags = {nm: strip([(nm, F['color'], 3.4)], pad=(20, 14), radius=8, dot=self.tank[nm])
                          for _, nm in FINALE_LOOKS}
        self.end_prep()
        self.fx_prep()
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.46) / (H * 0.62)) ** 2)
        self.vignette = (1 - 0.11 * np.clip(r, 0, 1.6) ** 2.4)[..., None].astype(np.float32)
        self.gx, self.gy = xx, yy

    # Été: separate the palm shadows from the wall so they can sway
    def sun_prep(self):
        """Pull the palm shadows off the wall as one smooth field.

        The shadow field is built from a blurred luminance so plaster cracks
        never enter it; dividing it out and multiplying a shifted copy back in
        moves the fronds while every crack in the plaster stays put.
        """
        bg = self.bgs['ete']
        L = bg.mean(-1)
        Lb = cv2.GaussianBlur(L, (0, 0), 5)
        lit = cv2.dilate(Lb, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81)))
        lit = cv2.GaussianBlur(lit, (0, 0), 35)
        Sh = np.clip(1 - Lb / np.maximum(lit, 1e-3), 0, 0.68)
        wall = np.zeros_like(L)
        wall[505:] = 1.0                                 # the wall, below its top edge
        wall = cv2.GaussianBlur(wall, (0, 0), 6)
        Sh = np.clip((Sh - 0.08) / 0.92, 0, 1) * 0.68 / 0.68 * wall
        self.sun_shadow = Sh.astype(np.float32)
        self.sun_lit = np.clip(bg / (1 - Sh[..., None]), 0, 1.4).astype(np.float32)

    def fx_prep(self):
        rng = np.random.default_rng(11)
        def P(n, **kw):
            return {k: (rng.uniform(*v, n) if isinstance(v, tuple) else np.full(n, v)) for k, v in kw.items()}
        self.rain_far = P(260, x=(-200, W + 200), y=(0, H + 300), ln=(34, 64), sp=(1500, 2000), a=(0.10, 0.22))
        self.rain_near = P(30, x=(-200, W + 200), y=(0, H + 600), ln=(150, 240), sp=(2700, 3300), a=(0.14, 0.24))
        self.snow_far = P(330, x=(0, W), y=(0, H + 60), r=(0.9, 2.1), sp=(45, 95), a=(0.55, 0.9),
                          sw=(4, 16), f=(0.15, 0.45), ph=(0, 6.283))
        self.snow_mid = P(120, x=(0, W), y=(0, H + 80), r=(2.2, 3.9), sp=(90, 150), a=(0.75, 0.95),
                          sw=(10, 28), f=(0.15, 0.4), ph=(0, 6.283))
        self.snow_near = P(16, x=(0, W), y=(0, H + 200), r=(10, 19), sp=(170, 260), a=(0.35, 0.62),
                           sw=(20, 50), f=(0.1, 0.3), ph=(0, 6.283))
        # sea glints, in source coords of bg-fin-ete: dense on the sun's path
        n1, n2 = 70, 60
        gx = np.concatenate([rng.normal(185, 55, n1), rng.uniform(0, 1116, n2)])
        gy = np.concatenate([rng.uniform(700, 970, n1), rng.uniform(700, 965, n2)])
        self.glints = dict(x=gx, y=gy, f=rng.uniform(0.7, 1.8, n1 + n2), ph=rng.uniform(0, 6.283, n1 + n2),
                           s=np.concatenate([rng.uniform(5, 13, n1), rng.uniform(3, 7, n2)]),
                           a=np.concatenate([rng.uniform(0.5, 1.0, n1), rng.uniform(0.25, 0.55, n2)]))

    def end_prep(self):
        logo = np.array(Image.open(os.path.join(SRC, 'logo-basic.png')).convert('RGBA'), np.float32) / 255
        a = logo[..., 3] * (1 - logo[..., :3].mean(-1)) ** 0.8   # ink only, like Multiply
        rgb = np.broadcast_to(INK, a.shape + (3,)).astype(np.float32)
        self.logo = np.dstack([rgb * a[..., None], a]).astype(np.float32)
        F = self.F

        def text_line(s, f, track, ink=INK):
            tw = run_length(f, s, track)
            asc, desc = f.getmetrics()
            img = Image.new('L', (int(tw + 8), asc + desc + 8), 0)
            draw_run(ImageDraw.Draw(img), 4, asc + 4, s, f, 255, track)
            a = np.array(img, np.float32) / 255
            rgb = np.broadcast_to(ink, a.shape + (3,)).astype(np.float32)
            return np.dstack([rgb * a[..., None], a]).astype(np.float32)
        self.end_l1 = text_line('LE DÉBARDEUR COL MONTANT', F['end1'], 7.5)
        self.end_l2 = text_line('4 coloris · Lien en bio', F['end2'], 1.2, ink=np.array([92, 84, 78]) / 255)
        self.dots = []
        for _, nm in FINALE_LOOKS:
            k = 4; r = 15
            m = Image.new('RGBA', ((2 * r + 4) * k, (2 * r + 4) * k), (0, 0, 0, 0))
            ImageDraw.Draw(m).ellipse([2 * k, 2 * k, (2 * r + 2) * k, (2 * r + 2) * k],
                                      fill=tuple(int(c * 255) for c in self.tank[nm]) + (255,),
                                      outline=(28, 26, 27, 60), width=int(1.3 * k))
            m = np.array(m.resize((2 * r + 4, 2 * r + 4), Image.LANCZOS), np.float32) / 255
            self.dots.append(np.dstack([m[..., :3] * m[..., 3:4], m[..., 3:4]]).astype(np.float32))


A = None


def init_worker():
    global A
    cv2.setNumThreads(1)
    A = Assets()


# ------------------------------------------------------------- background --
def bg_affine(zoom, anchor_y=0.46):
    """Source->frame affine: cover-fit, then a slow push-in about the subject."""
    sw, sh = 1116, 2000
    sc = max(W / sw, H / sh) * zoom
    cx_s, cy_s = sw / 2, sh * anchor_y
    cx_f, cy_f = W / 2, H * anchor_y
    return np.array([[sc, 0, cx_f - sc * cx_s], [0, sc, cy_f - sc * cy_s]], np.float64)


def render_bg(key, t, t0, t1, frame):
    u = (t - t0) / max(1e-6, t1 - t0)
    zoom = 1.0 + 0.035 * u
    M = bg_affine(zoom)
    if key == 'ete':
        src = summer_plate(t)
    elif key == 'fin':
        src = sea_plate(t)
    elif key == 'studio':
        src = A.bgs['studio']
        M = bg_affine(1.0 + 0.02 * u)
    else:
        src = A.bgs[key]
    out = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if key == 'ete':
        flare(out, t, M)
    if key == 'fin':
        glints(out, t, M)
    return out, M


def summer_plate(t):
    """Palm shadows swaying in a light breeze; the plaster itself stays still."""
    Sh = A.sun_shadow
    h, w = Sh.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    th_l = 0.010 * math.sin(2 * math.pi * 0.33 * t + 0.4) + 0.004 * math.sin(2 * math.pi * 0.9 * t)
    th_r = 0.010 * math.sin(2 * math.pi * 0.29 * t + 2.1) + 0.004 * math.sin(2 * math.pi * 0.8 * t + 1)
    side = np.where(xx < w / 2, th_l, -th_r).astype(np.float32)
    mapx = xx - side * np.maximum(yy - 505, 0)
    S2 = cv2.remap(Sh, mapx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return np.clip(A.sun_lit * (1 - S2[..., None]), 0, 1)


def sea_plate(t):
    """Gentle swell on the water above the balustrade."""
    src = A.bgs['fin']
    h, w = src.shape[:2]
    if not hasattr(A, '_sea'):
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        wgt = np.clip((yy - 690) / 25, 0, 1) * np.clip((972 - yy) / 12, 0, 1)
        A._sea = (xx, yy, wgt.astype(np.float32))
    xx, yy, wgt = A._sea
    dy = (1.3 * np.sin(xx / 41 + t * 2.6) * np.sin(yy / 17 - t * 1.9)) * wgt
    dx = (0.9 * np.sin(yy / 23 + t * 2.2)) * wgt
    return cv2.remap(src, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def flare(out, t, M):
    """The sun just off the top-right corner breathes a little."""
    sx, sy = 1105, 360
    fx = M[0, 0] * sx + M[0, 2]
    fy = M[1, 1] * sy + M[1, 2]
    k = 0.055 + 0.035 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.7 * t))
    y0, y1 = 0, int(min(H, fy + 520))
    x0 = int(max(0, fx - 620))
    gy, gx = A.gy[y0:y1, x0:], A.gx[y0:y1, x0:]
    d2 = ((gx - fx) ** 2 + (gy - fy) ** 2) / (300 ** 2)
    glow = np.exp(-d2)[..., None] * np.array([1.0, 0.92, 0.78], np.float32) * k
    out[y0:y1, x0:] = 1 - (1 - out[y0:y1, x0:]) * (1 - glow)


def glints(out, t, M):
    g = A.glints
    e = np.maximum(0, np.sin(2 * np.pi * g['f'] * t + g['ph'])) ** 12 * g['a']
    layer = np.zeros((H, W), np.float32)
    fx = M[0, 0] * g['x'] + M[0, 2]
    fy = M[1, 1] * g['y'] + M[1, 2]
    for x, y, s, v in zip(fx, fy, g['s'], e):
        if v < 0.03:
            continue
        p = (int(round(x * 4)), int(round(y * 4)))
        L = int(s * 4)
        val = float(min(1.0, v))
        cv2.line(layer, (p[0] - L, p[1]), (p[0] + L, p[1]), val, 2, cv2.LINE_AA, shift=2)
        cv2.line(layer, (p[0], p[1] - L // 2), (p[0], p[1] + L // 2), val * 0.8, 2, cv2.LINE_AA, shift=2)
        cv2.circle(layer, p, 6, val, -1, cv2.LINE_AA, shift=2)
    layer = cv2.GaussianBlur(layer, (0, 0), 0.9)
    warm = np.array([1.0, 0.95, 0.82], np.float32)
    out += layer[..., None] * warm
    np.clip(out, 0, 1, out=out)


def rain(t, near):
    P = A.rain_near if near else A.rain_far
    layer = np.zeros((H, W), np.float32)
    slant = 0.16
    span = H + (600 if near else 300)
    y = (P['y'] + P['sp'] * t) % span - (300 if near else 150)
    x = (P['x'] + slant * P['sp'] * t) % (W + 400) - 200
    width = 2 if near else 1
    for xi, yi, ln, a in zip(x, y, P['ln'], P['a']):
        x2, y2 = xi - slant * ln, yi - ln
        cv2.line(layer, (int(xi * 4), int(yi * 4)), (int(x2 * 4), int(y2 * 4)), float(a), width, cv2.LINE_AA, shift=2)
    if near:
        layer = cv2.GaussianBlur(layer, (0, 0), 1.8) * 1.4
    return layer


def snow(t, P, blur=0.0):
    layer = np.zeros((H, W), np.float32)
    y = (P['y'] + P['sp'] * t) % (H + 120) - 60
    x = (P['x'] + P['sw'] * np.sin(2 * np.pi * P['f'] * t + P['ph'])) % W
    for xi, yi, r, a in zip(x, y, P['r'], P['a']):
        cv2.circle(layer, (int(xi * 4), int(yi * 4)), max(1, int(r * 4)), float(a), -1, cv2.LINE_AA, shift=2)
    if blur:
        layer = cv2.GaussianBlur(layer, (0, 0), blur)
    return layer


def add_layer(out, layer, color):
    a = np.clip(layer, 0, 1)[..., None]
    out *= (1 - a)
    out += a * np.asarray(color, np.float32)


# ------------------------------------------------------------------ frames --
def frame_at(i):
    t = i / FPS
    if t >= END['t0']:
        out = end_card(t)
    elif t >= FINAL['t0']:
        out = finale(t, i)
    else:
        out = season_frame(t, i)
    out *= A.vignette
    # film grain: clumpy, luminance only, shared by every layer
    rng = np.random.default_rng(1000 + i)
    g = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
    out += (g * 0.016)[..., None]
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def look_center(scale=1.0, top=STICKER_TOP, cx=W / 2):
    w, h = A.look_size
    return cx, top - A.vis_top * scale + h * scale / 2


def season_frame(t, i):
    s = next(x for x in SEASONS if x['t0'] <= t < x['t1'])
    out, M = render_bg(s['key'], t, s['t0'], s['t1'], i)

    if s['fx'] == 'rain':
        add_layer(out, rain(t, near=False), (0.86, 0.89, 0.92))
    if s['fx'] == 'snow':
        add_layer(out, snow(t, A.snow_far), (0.97, 0.98, 1.0))
        add_layer(out, snow(t, A.snow_mid, blur=0.7), (0.98, 0.99, 1.0))

    k = max(j for j, st in enumerate(s['steps']) if st[0] <= t)
    st_t, look, tag, temp = s['steps'][k]

    # punch: the whole frame kicks for a few frames when « Jamais. » lands
    shake = (0, 0)
    if s.get('punch') is not None and 0 <= t - s['punch'] < 0.14:
        f = int(round((t - s['punch']) * FPS))
        shake = [(0, 0), (9, -6), (-7, 5), (4, -3), (-2, 1)][min(f, 4)]

    cx, cy = look_center()
    sp = slap(t - st_t) if st_t > 0 else (1.0, 0.0, 1.0)
    bx, by, br = boil(look, i)
    sc, rr, op = sp
    place(out, A.looks[look], cx + bx + shake[0], cy + by + shake[1], sc, LOOK_ROT[look] + rr + br, op,
          interp=cv2.INTER_LINEAR if sc != 1.0 else cv2.INTER_CUBIC)

    # top band
    if s.get('hook'):
        for img, t_in, x_left, y, rot in [(A.hook1, 0.10, 78, 330, -2.0), (A.hook2, 0.35, 140, 432, 1.6)]:
            sp = slap(t - t_in, amp=0.22, spin=6)
            if sp:
                bx, by, br = boil(f'hook{t_in}', i, 0.8, 0.12)
                place(out, img, x_left + img.shape[1] / 2 + bx, y + by, sp[0], rot + sp[1] + br, sp[2])
    else:
        img = A.labels[s['key']]
        sp = slap(t - s['t0'] - 0.06, amp=0.2, spin=6)
        if sp:
            bx, by, br = boil('label' + s['key'], i, 0.8, 0.12)
            place(out, img, 78 + img.shape[1] / 2 + bx, 348 + by, sp[0], -2.2 + sp[1] + br, sp[2])

    # temperature pill, top right; it re-slaps whenever the number drops
    pimg = A.pills[(s['icon'], temp)]
    first_k = min(j for j, st in enumerate(s['steps']) if st[3] == temp)
    t_pill = s['steps'][first_k][0] + 0.04
    sp = slap(t - t_pill, amp=0.18, spin=-5) if t_pill > 0.05 else (1.0, 0.0, 1.0)
    if sp is None and first_k > 0:
        # the new number lands a hair after the sticker; hold the old one until then
        pimg = A.pills[(s['icon'], s['steps'][first_k - 1][3])]
        sp = (1.0, 0.0, 1.0)
    if sp is not None:
        bx, by, br = boil('pill' + s['key'], i, 0.8, 0.12)
        place(out, pimg, 1002 - pimg.shape[1] / 2 + bx, 344 + by, sp[0], 3.0 + sp[1] + br, sp[2])

    # what was just added, stuck on the sticker's lower-left corner
    if tag:
        img = A.tags[tag]
        sp = slap(t - st_t - 0.08, amp=0.2, spin=-6)
        if sp:
            rot = -3.0 if k % 2 else 2.2
            bx, by, br = boil('tag' + tag, i, 0.8, 0.12)
            place(out, img, 62 + img.shape[1] / 2 + bx, 1196 + by, sp[0], rot + sp[1] + br, sp[2])

    if s.get('punch') is not None and t >= s['punch']:
        sp = slap(t - s['punch'], dur=0.4, amp=0.34, spin=-8)
        place(out, A.punch, 62 + A.punch.shape[1] / 2 + shake[0], 350 + shake[1], sp[0], -3.5 + sp[1], sp[2])

    if s['fx'] == 'rain':
        add_layer(out, rain(t, near=True), (0.88, 0.91, 0.94))
    if s['fx'] == 'snow':
        add_layer(out, snow(t, A.snow_near, blur=4.5), (1.0, 1.0, 1.0))
    return out


def finale(t, i):
    out, _ = render_bg('studio', t, FINAL['t0'], FINAL['t1'], i)
    sc = 0.48
    pos = [(292, 505), (788, 505), (292, 965), (788, 965)]
    rots = [-2.0, 1.6, 1.2, -1.8]
    vis_w = (A.look_size[0] - 2 * (A.pad - A.border)) * sc
    for (look, nm), (px, top), r0, t_in in zip(FINALE_LOOKS, pos, rots, FINAL['minis']):
        sp = slap(t - t_in, amp=0.2, spin=6)
        if not sp:
            continue
        cx, cy = look_center(sc, top, px)
        bx, by, br = boil('mini' + nm, i, 0.8, 0.12)
        place(out, A.looks[look], cx + bx, cy + by, sc * sp[0], r0 + sp[1] + br, sp[2])
    for (look, nm), (px, top), t_in in zip(FINALE_LOOKS, pos, FINAL['minis']):
        sp = slap(t - t_in - 0.07, amp=0.2, spin=-6)
        if not sp:
            continue
        img = A.colortags[nm]
        x_left = px - vis_w / 2 - 18
        bx, by, br = boil('ctag' + nm, i, 0.8, 0.12)
        place(out, img, x_left + img.shape[1] / 2 + bx, top + 34 + by, sp[0], -2.5 + sp[1] + br, sp[2])
    for img, t_in, x_left, y, rot in [(A.tag1, FINAL['tag1'], 78, 330, -2.0), (A.tag2, FINAL['tag2'], 140, 432, 1.6)]:
        sp = slap(t - t_in, amp=0.22, spin=6)
        if sp:
            bx, by, br = boil(f'final{t_in}', i, 0.8, 0.12)
            place(out, img, x_left + img.shape[1] / 2 + bx, y + by, sp[0], rot + sp[1] + br, sp[2])
    return out


def ease_out(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def end_card(t):
    out = np.empty((H, W, 3), np.float32)
    out[:] = ECRU
    dt = t - END['t0']
    # logo: a quiet scale-in, no sticker treatment - the brand stays clean
    u = ease_out(dt / 0.55)
    place(out, A.logo, W / 2, 800, 0.965 + 0.035 * u, 0, u, interp=cv2.INTER_CUBIC)
    for img, t_in, y in [(A.end_l1, 0.22, 1086), (A.end_l2, 0.34, 1146)]:
        u = ease_out((dt - t_in) / 0.45)
        place(out, img, W / 2, y + 14 * (1 - u), 1.0, 0, u, interp=cv2.INTER_CUBIC)
    for k, d in enumerate(A.dots):
        sp = slap(dt - 0.50 - 0.09 * k, dur=0.3, amp=0.35, spin=0)
        if sp:
            place(out, d, W / 2 + (k - 1.5) * 54, 1232, sp[0], 0, sp[2], interp=cv2.INTER_CUBIC)
    return out


# ------------------------------------------------------------------- main --
def main():
    args = sys.argv[1:]
    if '--stills' in args:
        times = [float(x) for x in args[args.index('--stills') + 1].split(',')]
        os.makedirs(os.path.join(BUILD, 'stills'), exist_ok=True)
        init_worker()
        for tt in times:
            i = int(round(tt * FPS))
            Image.fromarray(frame_at(i)).save(os.path.join(BUILD, 'stills', f't{tt:05.2f}.png'))
            print('still', tt)
        return
    out = os.path.join(BUILD, 'video.mp4')
    n = int(round(DUR * FPS))
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
                           '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-profile:v', 'high',
                           '-level:v', '4.2', '-x264-params', 'aq-mode=3',
                           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                           '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    workers = max(1, (os.cpu_count() or 2))
    with Pool(workers, initializer=init_worker) as pool:
        for k, fr in enumerate(pool.imap(frame_at, range(n), chunksize=2)):
            ff.stdin.write(fr.tobytes())
            if k % 30 == 0:
                print(f'  frame {k}/{n}', flush=True)
    ff.stdin.close()
    ff.wait()
    with open(os.path.join(BUILD, 'events.json'), 'w') as f:
        json.dump(events(), f)
    print('wrote', out)


if __name__ == '__main__':
    main()
