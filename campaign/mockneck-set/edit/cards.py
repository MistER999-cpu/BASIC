"""Still layers for the hook (one look at a time on the wall) and the animated end card
(all three looks, logo in the carved plaque). Built once, at output resolution."""
import os
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage as nd

import endcard as ec
import look
import typo

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, '..', 'endcard')
REFS = os.path.join(HERE, '..', 'refs')
W, H = 1080, 1920
S = W / ec.W0                     # wall plate -> output scale (crop bottom to 1920)
PLAQUE_C = (557 * S, 512 * S)     # centre of the recessed panel, output coords

FILES = {'burgundy': ('burgundy-profile.png', False), 'chocolat': ('chocolate-front.png', False),
         'noir': ('black-back.png', True)}


def to_out(img, interp=cv2.INTER_AREA):
    out = cv2.resize(img, (W, int(round(ec.H0 * S))), interpolation=interp)
    return out[:H]


def wall():
    im = np.asarray(Image.open(os.path.join(EC, 'wall.jpg')).convert('RGB')).astype(np.float32) / 255
    return to_out(im)


def figure_layer(colour, cx, feet_y, fig_h):
    """Return (rgb, alpha, shadow) full-frame float layers at output res for one look."""
    name, mirror = FILES[colour]
    old_h = ec.FIG_H
    ec.FIG_H = fig_h
    fig = ec.load_fig(name, mirror)
    ec.FIG_H = old_h
    x0, y0 = int(cx - fig.width / 2), feet_y - fig.height
    base = Image.open(os.path.join(EC, 'wall.jpg')).convert('RGB')
    # shadow: render onto a white plate and read back the darkening
    white = Image.new('RGB', base.size, (255, 255, 255))
    shaded = np.asarray(ec.shadows(white, fig, x0, y0)).astype(np.float32) / 255
    shadow = np.clip((1 - shaded[..., 0]) / 0.55, 0, 1)
    wrapped = ec.light_wrap(base, fig, x0, y0)
    canvas_rgb = np.zeros((ec.H0, ec.W0, 3), np.float32)
    canvas_a = np.zeros((ec.H0, ec.W0), np.float32)
    f = np.asarray(wrapped).astype(np.float32) / 255
    if colour == 'burgundy':
        f[..., :3] = look.fix_burgundy(f[..., :3], dh=-8.0, ks=1.12, kv=1.05)
    h, w = f.shape[:2]
    ys0, xs0 = max(0, y0), max(0, x0)
    ys1, xs1 = min(ec.H0, y0 + h), min(ec.W0, x0 + w)
    canvas_rgb[ys0:ys1, xs0:xs1] = f[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, :3]
    canvas_a[ys0:ys1, xs0:xs1] = f[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, 3]
    rgb = to_out(canvas_rgb, cv2.INTER_AREA)
    a = to_out(canvas_a, cv2.INTER_AREA)
    sh = to_out(shadow, cv2.INTER_AREA)
    return dict(rgb=rgb, a=a, shadow=sh)


def logo_alpha(width):
    lg = np.asarray(Image.open(os.path.join(REFS, 'logo.png')).convert('RGBA')).astype(np.float32)
    a = lg[..., 3] / 255
    ys, xs = np.nonzero(a > 0.08)
    a = a[ys.min() - 3:ys.max() + 4, xs.min() - 3:xs.max() + 4]
    hgt = int(round(a.shape[0] * width / a.shape[1]))
    return cv2.resize(a, (width, hgt), interpolation=cv2.INTER_AREA)


class Cards:
    def __init__(self):
        self.wall = wall()
        # hook: one look, centred and larger
        self.solo = {c: figure_layer(c, 558, 1820, 1120) for c in FILES}
        # end card: three looks
        self.trio = [('burgundy', figure_layer('burgundy', 205, ec.FEET_Y, ec.FIG_H)),
                     ('chocolat', figure_layer('chocolat', 558, ec.FEET_Y, ec.FIG_H)),
                     ('noir', figure_layer('noir', 915, ec.FEET_Y, ec.FIG_H))]
        self.trio_x = [205 * S, 558 * S, 915 * S]
        self.logo = logo_alpha(int(398 * S))
        self.words = {
            'burgundy': typo.text_alpha('BURGUNDY', 'didone', 70, tracking=9),
            'chocolat': typo.text_alpha('CHOCOLAT', 'didone', 70, tracking=9),
            'noir': typo.text_alpha('NOIR', 'didone', 70, tracking=12),
        }
        self.word_basic = typo.text_alpha('BASIC  ESSENTIALS', 'sans_light', 17, tracking=9)
        self.labels = {
            'burgundy': typo.text_layer('BURGUNDY', 'sans_med', 24, typo.INK, tracking=8)[0],
            'chocolat': typo.text_layer('CHOCOLAT', 'sans_med', 24, typo.INK, tracking=8)[0],
            'noir': typo.text_layer('NOIR', 'sans_med', 24, typo.INK, tracking=8)[0],
        }
        self.cta = typo.text_alpha('DISPONIBLE MAINTENANT', 'sans_med', 23, tracking=11)

    @staticmethod
    def put_figure(frame, layer, opacity=1.0, dy=0.0):
        if opacity <= 0:
            return frame
        sh = layer['shadow'] * opacity
        frame = frame * (1 - sh[..., None] * np.array([0.55, 0.58, 0.62], np.float32))
        rgb, a = layer['rgb'], layer['a'] * opacity
        if abs(dy) > 0.5:
            M = np.float32([[1, 0, 0], [0, 1, dy]])
            rgb = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_LINEAR)
            a = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR)
        return frame * (1 - a[..., None]) + rgb * a[..., None]

    def plaque_word(self, frame, colour, reveal=1.0):
        a = self.words[colour]
        a2 = self.word_basic
        h, w = a.shape
        x = PLAQUE_C[0] - w / 2
        y = PLAQUE_C[1] - h / 2 - 16
        m = self._reveal(a, reveal)
        typo.engrave(frame, m, x, y)
        h2, w2 = a2.shape
        typo.engrave(frame, self._reveal(a2, reveal), PLAQUE_C[0] - w2 / 2, y + h + 26, strength=0.85)
        return frame

    def plaque_logo(self, frame, reveal=1.0, shine=None):
        a = self.logo
        h, w = a.shape
        x, y = PLAQUE_C[0] - w / 2, PLAQUE_C[1] - h / 2 - 5
        typo.engrave(frame, self._reveal(a, reveal), x, y)
        if shine is not None and 0 <= shine <= 1:
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            band = np.exp(-((xx + yy * 0.5 - (shine * (w + h) - h * 0.25)) / 26) ** 2)
            glow = (band * a)[..., None] * 0.55
            reg = frame[int(y):int(y) + h, int(x):int(x) + w]
            reg[:] = reg + (1 - reg) * glow
        return frame

    def cta_line(self, frame, reveal=1.0, y_centre=321):
        a = self.cta
        h, w = a.shape
        typo.engrave(frame, self._reveal(a, reveal), W / 2 - w / 2, y_centre - h / 2, strength=0.92)
        return frame

    @staticmethod
    def _reveal(a, k):
        if k >= 1:
            return a
        if k <= 0:
            return np.zeros_like(a)
        h, w = a.shape
        edge = k * (w + 60) - 30
        ramp = np.clip((edge - np.arange(w)) / 30.0, 0, 1)[None, :]
        return a * ramp
