"""French typography for the BASIC ad: tracked text, frosted feature callouts, plaque
engraving. Everything renders to float RGBA layers composited onto float frames."""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts')
FONT = {
    'didone': os.path.join(FD, 'BodoniModa-Regular.ttf'),
    'didone_med': os.path.join(FD, 'BodoniModa-Medium.ttf'),
    'didone_it': os.path.join(FD, 'BodoniModa-Italic.ttf'),
    'garamond_it': os.path.join(FD, 'CormorantGaramond-Italic.ttf'),
    'sans': '/usr/share/fonts/opentype/inter/Inter-Regular.otf',
    'sans_light': '/usr/share/fonts/opentype/inter/Inter-Light.otf',
    'sans_med': '/usr/share/fonts/opentype/inter/Inter-Medium.otf',
}
CREAM = (246, 240, 231)
INK = (34, 30, 28)
_cache = {}


def font(key, size):
    k = (key, size)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(FONT[key], size)
    return _cache[k]


def text_layer(text, key, size, color, tracking=0, shadow=0.0, shadow_blur=6, pad=24):
    """Render tracked text. Returns float RGBA (h, w, 4) in 0-1 and the text box size."""
    f = font(key, size)
    probe = ImageDraw.Draw(Image.new('L', (8, 8)))
    widths = [probe.textlength(ch, font=f) for ch in text]
    tw = int(sum(widths) + tracking * max(0, len(text) - 1)) + 2
    asc, desc = f.getmetrics()
    th = asc + desc
    Wd, Hd = tw + 2 * pad, th + 2 * pad
    a = Image.new('L', (Wd, Hd), 0)
    d = ImageDraw.Draw(a)
    x = pad
    for ch, cw in zip(text, widths):
        d.text((x, pad), ch, font=f, fill=255)
        x += cw + tracking
    alpha = np.asarray(a).astype(np.float32) / 255
    rgb = np.ones((Hd, Wd, 3), np.float32) * (np.array(color, np.float32) / 255)
    out = np.dstack([rgb, alpha])
    if shadow > 0:
        sa = cv2.GaussianBlur(alpha, (0, 0), shadow_blur) * shadow
        sh = np.dstack([np.zeros((Hd, Wd, 3), np.float32), sa])
        out = over_rgba(sh, out)
    return out, (tw, th), pad


def over_rgba(bottom, top):
    a_t = top[..., 3:4]; a_b = bottom[..., 3:4]
    a = a_t + a_b * (1 - a_t)
    rgb = (top[..., :3] * a_t + bottom[..., :3] * a_b * (1 - a_t)) / np.maximum(a, 1e-5)
    return np.dstack([rgb, a])


def composite(frame, layer, x, y, opacity=1.0):
    """Alpha-composite float RGBA layer onto float RGB frame at integer (x, y)."""
    if opacity <= 0.001:
        return frame
    Hf, Wf = frame.shape[:2]
    h, w = layer.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(Wf, x + w), min(Hf, y + h)
    if x1 <= x0 or y1 <= y0:
        return frame
    L = layer[y0 - y:y1 - y, x0 - x:x1 - x]
    a = L[..., 3:4] * opacity
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - a) + L[..., :3] * a
    return frame


def rounded_mask(w, h, r):
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (r, 0), (w - r - 1, h - 1), 255, -1)
    cv2.rectangle(m, (0, r), (w - 1, h - r - 1), 255, -1)
    for cx, cy in [(r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)]:
        cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 0.8)


class Callout:
    """A feature callout: dot on the garment, a hairline leader, and a frosted label with a
    spaced-caps title and an italic French subtitle."""

    def __init__(self, title, subtitle, label_xy, anchors, t_in, t_out):
        self.title, _, self.tpad = text_layer(title, 'sans_med', 25, CREAM, tracking=5)
        self.sub, _, self.spad = text_layer(subtitle, 'garamond_it', 33, CREAM)
        tw = self.title.shape[1] - 2 * self.tpad
        sw = self.sub.shape[1] - 2 * self.spad
        self.bw = int(max(tw, sw) + 2 * 26)
        self.bh = 104
        self.lx, self.ly = label_xy
        self.anchors = anchors            # [(t, (x, y)), ...]
        self.t_in, self.t_out = t_in, t_out
        self.mask = rounded_mask(self.bw, self.bh, 16)

    def anchor(self, t):
        ts = [a[0] for a in self.anchors]
        xs = [a[1][0] for a in self.anchors]
        ys = [a[1][1] for a in self.anchors]
        return float(np.interp(t, ts, xs)), float(np.interp(t, ts, ys))

    def draw(self, frame, t):
        if t < self.t_in or t > self.t_out + 0.25:
            return frame
        k_in = np.clip((t - self.t_in) / 0.34, 0, 1)
        k_out = 1 - np.clip((t - self.t_out) / 0.22, 0, 1)
        vis = min(1.0, k_out)
        dot_k = np.clip(k_in / 0.3, 0, 1)
        line_k = np.clip((k_in - 0.2) / 0.45, 0, 1)
        lab_k = np.clip((k_in - 0.45) / 0.55, 0, 1)
        ease = lambda u: 1 - (1 - u) ** 3
        ax, ay = self.anchor(t)
        x0, y0 = self.lx, self.ly + (1 - ease(lab_k)) * 14
        x1, y1 = x0 + self.bw, y0 + self.bh
        # leader end: closest point on the label box
        ex = np.clip(ax, x0 + 14, x1 - 14)
        ey = y0 if ay < y0 else (y1 if ay > y1 else ay)
        if y0 <= ay <= y1:
            ex = x0 if ax < x0 else x1
        overlay = np.zeros(frame.shape[:2], np.float32)
        if line_k > 0:
            px = ax + (ex - ax) * ease(line_k)
            py = ay + (ey - ay) * ease(line_k)
            cv2.line(overlay, (int(ax * 4), int(ay * 4)), (int(px * 4), int(py * 4)), 1.0, 2, cv2.LINE_AA, shift=2)
        if dot_k > 0:
            r = 7 * ease(dot_k)
            cv2.circle(overlay, (int(ax * 4), int(ay * 4)), int(r * 4), 1.0, -1, cv2.LINE_AA, shift=2)
            cv2.circle(overlay, (int(ax * 4), int(ay * 4)), int((r + 7) * 4), 0.55, 2, cv2.LINE_AA, shift=2)
        if line_k > 0 or dot_k > 0:
            a = (overlay * vis)[..., None]
            shadow = cv2.GaussianBlur(overlay, (0, 0), 3)[..., None] * 0.35 * vis
            frame = frame * (1 - shadow)
            frame = frame * (1 - a) + np.array(CREAM, np.float32) / 255 * a
        if lab_k > 0:
            xi, yi = int(x0), int(y0)
            reg = frame[yi:yi + self.bh, xi:xi + self.bw]
            if reg.shape[0] == self.bh and reg.shape[1] == self.bw:
                pad = 40
                big = frame[max(0, yi - pad):yi + self.bh + pad, max(0, xi - pad):xi + self.bw + pad]
                blur = cv2.GaussianBlur(big, (0, 0), 16)
                oy, ox = yi - max(0, yi - pad), xi - max(0, xi - pad)
                frost = blur[oy:oy + self.bh, ox:ox + self.bw] * 0.58 + np.array([0.035, 0.028, 0.022], np.float32)
                m = (self.mask * ease(lab_k) * vis)[..., None]
                reg[:] = reg * (1 - m) + frost * m
                # hairline border
                edge = (self.mask - cv2.erode(self.mask, np.ones((3, 3), np.uint8))).clip(0, 1)[..., None]
                reg[:] = reg * (1 - edge * 0.35 * ease(lab_k) * vis) + np.array(CREAM, np.float32) / 255 * edge * 0.35 * ease(lab_k) * vis
                frame[yi:yi + self.bh, xi:xi + self.bw] = reg
                o = ease(lab_k) * vis
                composite(frame, self.title, xi + 26 - self.tpad, yi + 14 - self.tpad, o)
                composite(frame, self.sub, xi + 26 - self.spad, yi + 46 - self.spad, o * 0.92)
        return frame


class Pill:
    """Small frosted colour tag, e.g. 'BURGUNDY'."""

    def __init__(self, text, xy, t_in, t_out):
        self.txt, (tw, th), self.pad = text_layer(text, 'sans_med', 22, CREAM, tracking=7)
        self.bw, self.bh = tw + 2 * 22, 50
        self.x, self.y = xy
        self.t_in, self.t_out = t_in, t_out
        self.mask = rounded_mask(self.bw, self.bh, 25)

    def draw(self, frame, t):
        if t < self.t_in or t > self.t_out + 0.2:
            return frame
        k = np.clip((t - self.t_in) / 0.3, 0, 1) * (1 - np.clip((t - self.t_out) / 0.2, 0, 1))
        k = 1 - (1 - k) ** 3
        xi, yi = int(self.x), int(self.y + (1 - k) * 10)
        reg = frame[yi:yi + self.bh, xi:xi + self.bw]
        big = frame[yi - 30:yi + self.bh + 30, xi - 30:xi + self.bw + 30]
        frost = cv2.GaussianBlur(big, (0, 0), 14)[30:30 + self.bh, 30:30 + self.bw] * 0.56 + 0.03
        m = (self.mask * k)[..., None]
        reg[:] = reg * (1 - m) + frost * m
        frame[yi:yi + self.bh, xi:xi + self.bw] = reg
        composite(frame, self.txt, xi + 22 - self.pad, yi + 12 - self.pad, k)
        return frame


def engrave(frame, alpha, x, y, ink=INK, strength=1.0):
    """Cut an alpha mask into stone: dark ink, a light catch below-right, shadow above-left."""
    h, w = alpha.shape
    xi, yi = int(round(x)), int(round(y))
    reg = frame[yi:yi + h, xi:xi + w]
    a = alpha * strength
    hi = np.roll(np.roll(a, 2, 0), 1, 1)
    lo = np.roll(np.roll(a, -1, 0), -1, 1)
    reg[:] = reg + (1 - reg) * (0.16 * np.clip(hi - a, 0, 1))[..., None]
    reg[:] = reg * (1 - 0.28 * np.clip(lo - a, 0, 1))[..., None]
    ink = np.array(ink, np.float32) / 255
    reg[:] = reg * (1 - 0.9 * a[..., None]) + ink * 0.9 * a[..., None]
    frame[yi:yi + h, xi:xi + w] = reg
    return frame


def text_alpha(text, key, size, tracking=0):
    lay, (tw, th), pad = text_layer(text, key, size, (255, 255, 255), tracking=tracking, pad=6)
    a = lay[..., 3]
    ys, xs = np.nonzero(a > 0.02)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
