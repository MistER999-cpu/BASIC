#!/usr/bin/env python3
"""BASIC line-up film: one continuous stop-and-go camera move along a grey studio line-up,
after the reference lookbook (same audio, same rests on the beat), built from cut-out stills.

Layers (back to front): seamless grey sweep, hazy back row (parallax 0.62), main row (1.0) with
floor shadows, floating dust, a foreground close-up (1.6). Each main-row model flicks through her
colourways on the beat (flash + punch). Ends on the BASIC logo built from three colour layers.

    python3 campaign/mockneck-set/lineup/edit/render_lineup.py --cut <cutout dir> --audio ref.mp4 --out film.mp4
"""
import os
import sys
import argparse
import subprocess
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'campaign', 'mockneck-set', 'edit'))
os.chdir(ROOT)
import look  # noqa: E402

W, H, FPS = 1080, 1920, 25
DUR = 15.84
N = int(round(DUR * FPS))
T0, P = 0.642, 0.4688                       # beat grid of the reference audio (128 BPM)


def beat(k):
    return T0 + k * P


def smooth(u):
    u = float(np.clip(u, 0, 1)); return u * u * (3 - 2 * u)


def ease_io3(u):
    u = float(np.clip(u, 0, 1)); return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def ease_io5(u):
    u = float(np.clip(u, 0, 1)); return 16 * u ** 5 if u < 0.5 else 1 - (-2 * u + 2) ** 5 / 2


def ease_out3(u):
    u = float(np.clip(u, 0, 1)); return 1 - (1 - u) ** 3


# ------------------------------------------------------------------ camera
SEG = [  # t0, t1, x0, x1, easing
    (0.000, beat(2), -380, 900, ease_out3),
    (beat(2), beat(4), 900, 925, lambda u: u),
    (beat(4), beat(5), 925, 2150, ease_io5),            # whip
    (beat(5), beat(6), 2150, 2165, lambda u: u),
    (beat(6), beat(11), 2165, 3950, ease_io3),          # long glide
    (beat(11), beat(15), 3950, 3990, lambda u: u),
    (beat(15), beat(17), 3990, 5400, ease_io5),         # whip into the close-up
    (beat(17), beat(23), 5400, 5710, ease_io3),
    (beat(23), beat(26), 5710, 7300, ease_io3),
    (beat(26), 99.0, 7300, 7300, lambda u: u),
]
HOLD_ZOOM = [(beat(2), beat(4)), (beat(11), beat(15)), (beat(17), beat(23))]


def cam(t):
    for t0, t1, x0, x1, e in SEG:
        if t0 <= t < t1:
            return x0 + (x1 - x0) * e((t - t0) / (t1 - t0))
    return SEG[-1][3]


def zoom(t):
    z = 1.0
    for a, b in HOLD_ZOOM:
        if a <= t <= b + 0.6:
            z = 1 + 0.035 * smooth((t - a) / (b - a)) * (1 - smooth((t - b) / 0.5))
    return z


# ------------------------------------------------------------------ assets
BG_WALL = np.array([166, 164, 167], np.float32) / 255
BG_FLOOR = np.array([184, 182, 183], np.float32) / 255
_y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
_floor = np.clip((_y - 0.70) / 0.22, 0, 1) ** 1.4
BACKDROP = (BG_WALL * (1 - _floor) + BG_FLOOR * _floor) * (0.97 + 0.03 * np.cos((_y - 0.55) * 3.1))
BACKDROP = np.broadcast_to(BACKDROP, (H, W, 3)).copy()


class Sprite:
    """A cut-out, scaled once, premultiplied, anchored at its feet (or any point)."""

    def __init__(self, path, scale, mirror=False, blur=0.0, haze=0.0, shadow=True):
        im = np.asarray(Image.open(path).convert('RGBA')).astype(np.float32) / 255
        if mirror:
            im = im[:, ::-1]
        a = im[..., 3]
        a = np.clip((a - 0.06) / 0.88, 0, 1)
        ys, xs = np.nonzero(a > 0.5)
        self.feet_y = float(np.percentile(ys, 99.7)) * scale
        self.cx = float(np.median(xs)) * scale
        h, w = a.shape
        sz = (max(1, int(w * scale)), max(1, int(h * scale)))
        rgb = cv2.resize(im[..., :3], sz, interpolation=cv2.INTER_AREA)
        a = cv2.resize(a, sz, interpolation=cv2.INTER_AREA)
        if blur > 0:
            rgb = cv2.GaussianBlur(rgb * a[..., None], (0, 0), blur)
            a = cv2.GaussianBlur(a, (0, 0), blur)
            rgb = rgb / np.maximum(a[..., None], 1e-4)
        if haze > 0:
            y = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
            rgb = rgb * 0.8 + y[..., None] * 0.2
            rgb = rgb * (1 - haze) + BG_WALL * haze
        self.pm = np.dstack([rgb * a[..., None], a]).astype(np.float32)
        self.h, self.w = a.shape
        self.shadow = None
        if shadow:
            self._make_shadow(a)

    def _make_shadow(self, a):
        h, w = a.shape
        # long soft shadow cast behind-right, plus a tight contact shadow at the feet
        sq = cv2.resize(a, (w, max(2, int(h * 0.10))), interpolation=cv2.INTER_AREA)
        sh_h = sq.shape[0]
        pad = int(w * 0.6)
        canvas = np.zeros((sh_h + 60, w + pad), np.float32)
        for r in range(sh_h):
            off = int((sh_h - r) * 2.4)
            canvas[30 + r, off:off + w] = np.maximum(canvas[30 + r, off:off + w], sq[r])
        canvas = cv2.GaussianBlur(canvas, (0, 0), 9) * 0.20
        foot = a[int(self.feet_y) - 30:int(self.feet_y) + 2].max(0) if int(self.feet_y) - 30 > 0 else a[-30:].max(0)
        xs = np.nonzero(foot > 0.3)[0]
        if len(xs):
            cx, rx = (xs.min() + xs.max()) / 2, (xs.max() - xs.min()) / 2 + 26
            yy, xx = np.mgrid[0:canvas.shape[0], 0:canvas.shape[1]].astype(np.float32)
            canvas += 0.42 * np.clip(1 - (((xx - cx) / rx) ** 2 + ((yy - (30 + sh_h)) / 13) ** 2), 0, 1)
        self.shadow = cv2.GaussianBlur(canvas, (0, 0), 3)
        self.shadow_dy = int(self.feet_y) - (30 + sh_h)

    def draw(self, frame, sx, feet_y, alpha=1.0, punch=1.0):
        """sx: screen x of the figure centre; feet_y: screen y of the soles."""
        pm = self.pm
        if abs(punch - 1) > 1e-3:
            ph, pw = int(self.h * punch), int(self.w * punch)
            pm = cv2.resize(pm, (pw, ph), interpolation=cv2.INTER_LINEAR)
            cx, fy = self.cx * punch, self.feet_y * punch
        else:
            cx, fy = self.cx, self.feet_y
        x0, y0 = int(round(sx - cx)), int(round(feet_y - fy))
        if self.shadow is not None:
            sh = self.shadow
            paste_mul(frame, sh * alpha, int(round(sx - self.cx)), int(round(feet_y - self.feet_y)) + self.shadow_dy)
        paste(frame, pm, x0, y0, alpha)


def paste(frame, pm, x0, y0, alpha=1.0):
    h, w = pm.shape[:2]
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    s = pm[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    a = s[..., 3:4] * alpha
    frame[fy0:fy1, fx0:fx1] = frame[fy0:fy1, fx0:fx1] * (1 - a) + s[..., :3] * alpha


def paste_mul(frame, m, x0, y0):
    h, w = m.shape
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    s = m[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    frame[fy0:fy1, fx0:fx1] *= (1 - s[..., None] * np.array([0.58, 0.60, 0.64], np.float32))


# ------------------------------------------------------------------ scene
MAIN_S, MAIN_FEET = 0.80, 1740
BACK_S, BACK_FEET, BACK_P = 0.46, 1445, 0.62
FG_P = 1.6


class Scene:
    def __init__(self, cut):
        c = lambda k: os.path.join(cut, k + '.png')  # noqa: E731
        M = lambda k, mir=False: Sprite(c(k), MAIN_S, mir)  # noqa: E731
        self.main = [  # world x, [(time from, sprite)], spot label
            (900, [(-1, M('L1')), (beat(3), M('L7')), (beat(4), M('L4'))]),
            (2150, [(-1, M('L2')), (beat(6), M('L5'))]),
            (3030, [(-1, M('L1', True))]),
            (3950, [(-1, M('L6')), (beat(13), M('L3'))]),
            (6480, [(-1, M('L7', True))]),
        ]
        self.swaps = sorted({t for _, seq in self.main for t, _ in seq if t > 0})
        Bk = lambda k, mir: Sprite(c(k), BACK_S, mir, blur=1.8, haze=0.28)  # noqa: E731
        self.back = [(-900, Bk('L3', True)), (-150, Bk('L5', False)), (560, Bk('L6', True)), (1400, Bk('L2', True)),
                     (2050, Bk('L7', False)), (2750, Bk('L4', True)), (3500, Bk('L3', False)), (4250, Bk('L5', True)),
                     (4950, Bk('L1', False)), (5550, Bk('L6', False)), (6150, Bk('L2', False))]
        # opening: a big, out-of-focus model sweeping past the lens
        self.open_fg = Sprite(c('L5'), 1.35, True, blur=5.0, shadow=False)
        self.open_wx = -530
        # foreground close-up: the hug, big, cropped by the bottom edge
        self.fg = Sprite(c('X1'), 1.42, shadow=False)
        self.fg_wx = 5400 + (760 - 540) / FG_P      # face lands right of centre at the hold
        self.fg_y = 2950                            # bottom anchor (her hips sit below the frame)
        rng = np.random.default_rng(4)
        n = 90
        self.dust = dict(x=rng.uniform(-1500, 9000, n), y=rng.uniform(0, H, n), p=rng.uniform(0.5, 1.9, n),
                         r=rng.uniform(1.2, 3.6, n), a=rng.uniform(0.05, 0.22, n), vy=rng.uniform(-14, -4, n),
                         ph=rng.uniform(0, 6.28, n))
        self._build_logo()

    def _build_logo(self):
        lg = np.asarray(Image.open(os.path.join(ROOT, 'campaign', 'mockneck-set', 'refs', 'logo.png')).convert('RGBA'))
        a = lg[..., 3].astype(np.float32) / 255
        ys, xs = np.nonzero(a > 0.05)
        a = a[ys.min() - 4:ys.max() + 5, xs.min() - 4:xs.max() + 5]
        w = 640
        self.logo = cv2.resize(a, (w, int(round(a.shape[0] * w / a.shape[1]))), interpolation=cv2.INTER_AREA)

    def sprite_at(self, seq, t):
        cur = seq[0][1]
        for ts, sp in seq:
            if t >= ts:
                cur = sp
        return cur

    def punch(self, t):
        for ts in self.swaps:
            k = (t - ts) * FPS
            if 0 <= k < 7:
                return 1 + 0.045 * np.exp(-k / 2.2)
        return 1.0

    def flash(self, t):
        v = 0.0
        for ts in self.swaps:
            k = (t - ts) * FPS
            if 0 <= k < 5:
                v = max(v, 0.22 * [1, 0.45, 0.18, 0.07, 0.02][int(k)])
        return v

    def compose(self, t):
        cx = cam(t)
        f = BACKDROP.copy()
        for wx, sp in self.back:
            sx = 540 + (wx - cx) * BACK_P
            if -400 < sx < W + 400:
                sp.draw(f, sx, BACK_FEET)
        pn = self.punch(t)
        for wx, seq in self.main:
            sx = 540 + (wx - cx)
            if -700 < sx < W + 700:
                sp = self.sprite_at(seq, t)
                swapped = any(0 <= (t - ts) * FPS < 7 for ts, s2 in seq if ts > 0 and s2 is sp)
                sp.draw(f, sx, MAIN_FEET, punch=pn if swapped else 1.0)
        # dust motes drifting in the light
        d = self.dust
        xs = 540 + (d['x'] - cx) * d['p'] + 18 * np.sin(t * 0.7 + d['ph'])
        ys = (d['y'] + d['vy'] * t) % H
        for x, y, r, a, p in zip(xs, ys, d['r'], d['a'], d['p']):
            if -10 < x < W + 10:
                rr = r * (0.6 + 0.5 * p)
                x0, x1 = int(max(0, x - 3 * rr)), int(min(W, x + 3 * rr + 1))
                y0, y1 = int(max(0, y - 3 * rr)), int(min(H, y + 3 * rr + 1))
                if x1 > x0 and y1 > y0:
                    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
                    g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * rr * rr)) * a
                    f[y0:y1, x0:x1] += (1 - f[y0:y1, x0:x1]) * g[..., None]
        sx = 540 + (self.open_wx - cx) * FG_P
        if -1400 < sx < W + 1400:
            self.open_fg.draw(f, sx, H + 560)
        # foreground close-up
        sx = 540 + (self.fg_wx - cx) * FG_P
        if -1400 < sx < W + 1400:
            self.fg.draw(f, sx, self.fg_y)
        return f, cx


# ------------------------------------------------------------------ logo
def draw_logo(f, sc, t):
    a0 = beat(26)
    if t < a0:
        return f
    lg = sc.logo
    h, w = lg.shape
    cx, cy = 540, 930
    cols = [(beat(26), (34, 33, 36)), (beat(27), (84, 50, 40)), (beat(28), (108, 34, 58)), (beat(29), (30, 27, 26))]
    col, tb = cols[0][1], cols[0][0]
    for tt, cc in cols:
        if t >= tt:
            col, tb = cc, tt
    k = (t - tb) * FPS
    punch = 1 + 0.05 * np.exp(-k / 2.0)
    intro = ease_out3((t - a0) / 0.45)
    scale = (1.14 - 0.14 * intro) * punch * (1 + 0.025 * smooth((t - a0) / (DUR - a0)))
    a = lg
    if intro < 0.98:
        a = cv2.GaussianBlur(lg, (0, 0), 0.1 + 9 * (1 - intro))
    stamp(f, a, cx, cy, np.array(col, np.float32) / 255, intro, scale)
    if k < 3 and t > a0 + 0.05:
        f += (1 - f) * 0.10 * (1 - k / 3)
    merge = beat(29)
    shine = (t - merge - 0.10) / 0.7
    if 0 <= shine <= 1:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        band = np.exp(-((xx + yy * 0.6 - (shine * (w + h) - h * 0.3)) / 30) ** 2)
        stamp(f, lg * band, cx, cy, np.array([1, 1, 1], np.float32), 0.5, scale)
    return f


def stamp(f, a, cx, cy, col, alpha, scale=1.0, mode='over'):
    if abs(scale - 1) > 1e-3:
        a = cv2.resize(a, (int(a.shape[1] * scale), int(a.shape[0] * scale)), interpolation=cv2.INTER_LINEAR)
    h, w = a.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    reg = f[y0:y0 + h, x0:x0 + w]
    m = (a * alpha)[..., None]
    if mode == 'multiply':
        reg[:] = reg * (1 - m) + reg * col * m
    else:
        reg[:] = reg * (1 - m) + col * m


# ------------------------------------------------------------------ frame
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W * 0.7)) ** 2 + ((_yy - H * 0.5) / (H * 0.62)) ** 2)
VIG = (1 - 0.13 * np.clip(_r, 0, 1.6) ** 2.2).astype(np.float32)[..., None]
del _yy, _xx, _r


def render(sc, fr):
    t = fr / FPS
    v = abs(cam(t + 0.5 / FPS) - cam(t - 0.5 / FPS))       # px per frame on the main row
    nsub = int(np.clip(np.ceil(v / 10.0), 1, 9))
    if nsub > 1:
        acc = np.zeros((H, W, 3), np.float32)
        for k in range(nsub):
            ts = t + (k / (nsub - 1) - 0.5) * 0.5 / FPS      # 180-degree shutter
            acc += sc.compose(ts)[0]
        f = acc / nsub
    else:
        f = sc.compose(t)[0]
    z = zoom(t)
    if abs(z - 1) > 1e-4:
        M = np.float32([[z, 0, (1 - z) * W / 2], [0, z, (1 - z) * H * 0.55]])
        f = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    fl = sc.flash(t)
    if fl > 0:
        f = f + (1 - f) * fl
    f = draw_logo(f, sc, t)
    f = look.look(np.clip(f, 0, 1), halation=0.06, bloom=0.02)
    f = f * VIG
    f = look.grain(f, fr, amp=0.012)
    end = (DUR - t) * FPS
    if end < 4:
        f = f * max(0.0, end / 4)
    return np.clip(f, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cut', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--audio')
    ap.add_argument('--stills')
    a = ap.parse_args()
    sc = Scene(a.cut)
    if a.stills:
        for s in a.stills.split(','):
            fr = int(s)
            img = (render(sc, fr) * 255).astype(np.uint8)
            cv2.imwrite(a.out.replace('.mp4', f'_f{fr:04d}.jpg'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        return
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-']
    if a.audio:
        cmd += ['-i', a.audio, '-map', '0:v', '-map', '1:a', '-af', f'afade=t=out:st={DUR - 0.18:.2f}:d=0.18', '-t', f'{DUR:.2f}']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart']
    if a.audio:
        cmd += ['-c:a', 'aac', '-b:a', '256k', '-ar', '48000']
    cmd += [a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in range(N):
        proc.stdin.write((render(sc, fr) * 255 + 0.5).astype(np.uint8).tobytes())
        if fr % 50 == 0:
            print(f'frame {fr}/{N}', flush=True)
    proc.stdin.close()
    proc.wait()
    print('wrote', a.out)


if __name__ == '__main__':
    main()
