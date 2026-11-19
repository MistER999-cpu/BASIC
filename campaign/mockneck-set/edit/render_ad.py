#!/usr/bin/env python3
"""Render the BASIC Essentials mock-neck set ad: 1080x1920, 24 fps, beat-locked.

    python3 campaign/mockneck-set/edit/render_ad.py --out out.mp4 [--audio mix.wav]
           [--frames 0:200] [--stills 0,120,400]
"""
import os
import sys
import argparse
import subprocess
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
os.chdir(ROOT)

import timeline as tl
import look
import typo
from cards import Cards

FPS, W, H = tl.FPS, tl.W, tl.H
T, P = tl.T, tl.P
N = int(round(tl.DURATION * FPS))
SHOT = {s['id']: s for s in tl.SHOTS}
ORDER = [s['id'] for s in tl.SHOTS]
RANGES = {s['id']: tl.frame_range(s) for s in tl.SHOTS}


def ease_out(u):
    u = float(np.clip(u, 0, 1)); return 1 - (1 - u) ** 3


def ease_in(u):
    u = float(np.clip(u, 0, 1)); return u ** 3


def smooth(u):
    u = float(np.clip(u, 0, 1)); return u * u * (3 - 2 * u)


def fb(beat):
    """Frame index of a beat."""
    return int(round(T(beat) * FPS))


# ------------------------------------------------------------------ sources
class Clip:
    def __init__(self, path):
        info = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                               'stream=width,height', '-of', 'csv=p=0', path],
                              capture_output=True, text=True).stdout.strip().split(',')
        w, h = int(info[0]), int(info[1])
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                             capture_output=True).stdout
        self.frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
        self.n = len(self.frames)

    def sample(self, st, speed):
        if speed < 1.08:
            i = int(np.clip(round(st * FPS), 0, self.n - 1))
            return self.frames[i].astype(np.float32) / 255
        ts = st + np.array([0.0, 0.25, 0.5]) * speed / FPS           # 180-degree shutter
        idx = np.clip(np.round(ts * FPS).astype(int), 0, self.n - 1)
        return np.mean([self.frames[i].astype(np.float32) for i in idx], axis=0) / 255


CLIPS = {}


def clip(path):
    if path not in CLIPS:
        CLIPS[path] = Clip(path)
    return CLIPS[path]


def shot_image(sid, t):
    """Graded output-resolution frame of a clip shot at ad time t (time clamped to the shot)."""
    s = SHOT[sid]
    t0, t1 = tl.shot_times(s)
    a, b = s['src']
    speed = (b - a) / (t1 - t0)
    st = a + (t - t0) * speed
    raw = clip(s['clip']).sample(st, speed)
    f = look.correct_native(raw, sid)
    return look.look(look.upscale(f))


def affine(f, scale=1.0, dx=0.0, dy=0.0, cx=W / 2, cy=H / 2):
    if abs(scale - 1) < 1e-4 and abs(dx) < 0.05 and abs(dy) < 0.05:
        return f
    M = np.float32([[scale, 0, (1 - scale) * cx + dx], [0, scale, (1 - scale) * cy + dy]])
    return cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def hblur(f, length):
    L = int(length)
    if L < 3:
        return f
    k = np.ones((1, L), np.float32) / L
    return cv2.filter2D(f, -1, k, borderType=cv2.BORDER_REFLECT)


def zoom_blur(f, amount, n=6):
    acc = np.zeros_like(f)
    for i in range(n):
        acc += affine(f, 1 + amount * i / (n - 1))
    return acc / n


# ------------------------------------------------------------------ events
PUNCH = {0: 0.075, 1: 0.06, 2: 0.06, 3: 0.05, 10: 0.035, 15: 0.035, 27: 0.03, 32: 0.04, 50: 0.035}
FLASH = {0: 0.72, 1: 0.13, 2: 0.13, 3: 0.11, 32: 0.10, 57: 0.07, 58: 0.07, 59: 0.07, 60: 0.20, 64: 0.07}
SHAKE = {0: 15.0, 60: 6.0}
WHIPS = {21: ('S3', 'S4'), 40: ('S6', 'S7')}
LEAK = {46: ('S7', 'S8')}
WIPE_BEAT = 56
_rng = np.random.default_rng(5)
SHAKE_DIR = {b: _rng.uniform(-1, 1, (10, 2)) for b in SHAKE}


def punch_scale(f):
    s = 1.0
    for b, A in PUNCH.items():
        k = f - fb(b)
        if 0 <= k < 14:
            s += A * np.exp(-k / 3.2)
    return s


def flash_amount(f):
    v = 0.0
    for b, A in FLASH.items():
        k = f - fb(b)
        if 0 <= k < 5:
            v = max(v, A * [1, 0.5, 0.22, 0.09, 0.03][k])
    return v


def shake_offset(f):
    dx = dy = 0.0
    for b, A in SHAKE.items():
        k = f - fb(b)
        if 0 <= k < 10:
            d = SHAKE_DIR[b][k]
            dx += A * np.exp(-k / 2.6) * d[0]
            dy += A * np.exp(-k / 2.6) * d[1]
    return dx, dy


def apply_flash(f, v):
    if v <= 0.001:
        return f
    tint = np.array([1.0, 0.975, 0.93], np.float32)
    return f + (tint - f) * v


# ------------------------------------------------------------------ text
CREAM, INK = typo.CREAM, typo.INK
CALLOUTS = [
    typo.Callout('DOS ALLONGÉ · CHOCOLAT', 'ourlet arrondi, plus long à l\u2019arrière', (66, 860),
                 [(5.54, (340, 1250)), (6.31, (345, 1208)), (7.07, (345, 1198))], T(11), T(14.4)),
    typo.Callout('COL MONTANT · NOIR', 'le détail signature', (0, 1142),
                 [(10.34, (640, 1080)), (11.32, (610, 1095)), (12.30, (760, 1080))], T(22), T(26.4)),
    typo.Callout('POCHES LATÉRALES · CHOCOLAT', 'discrètes, dans la couture', (66, 780),
                 [(12.95, (520, 1290)), (13.71, (565, 1185)), (14.48, (545, 1175))], T(28), T(31.4)),
    typo.Callout('MANCHES LARGES · NOIR', 'poignets ouverts', (280, 790),
                 [(18.62, (820, 1150)), (19.10, (720, 1180)), (19.49, (580, 1320))], T(41), T(43.1)),
    typo.Callout('JAMBE LARGE · BURGUNDY', 'taille haute, tombé fluide', (0, 958),
                 [(22.97, (650, 1150)), (23.95, (640, 1180)), (24.93, (610, 1150))], T(51), T(54.75)),
]
CALLOUTS[1].lx = 1004 - CALLOUTS[1].bw
CALLOUTS[4].lx = 1004 - CALLOUTS[4].bw
PILLS = [typo.Pill('NOIR', (66, 1186), T(4.5), T(9.4)),
         typo.Pill('BURGUNDY', (66, 1186), T(16), T(19.9)),
         typo.Pill('BURGUNDY', (66, 1186), T(33), T(38.8)),
         typo.Pill('CHOCOLAT', (66, 1186), T(46.6), T(49.5))]

TAG1, _, TPAD = typo.text_layer('Trois teintes.', 'didone_it', 46, CREAM, shadow=0.8, shadow_blur=13, pad=48)
TAG2, _, _ = typo.text_layer('Une seule allure.', 'didone_it', 46, CREAM, shadow=0.8, shadow_blur=13, pad=48)
TAG_Y = 298
TAG_X1 = 70
TAG_X2 = 1010 - (TAG2.shape[1] - 2 * TPAD)
TAG_IN1, TAG_IN2, TAG_OUT = T(4), T(6), T(9.3)


def draw_tagline(f, t):
    if t < TAG_IN1 or t > TAG_OUT + 0.45:
        return f
    out = 1 - np.clip((t - TAG_OUT) / 0.45, 0, 1)
    k1 = ease_out((t - TAG_IN1) / 0.55)
    k2 = ease_out((t - TAG_IN2) / 0.55)
    typo.composite(f, TAG1, TAG_X1 - TPAD + (1 - k1) * -18, TAG_Y - TPAD, k1 * out)
    typo.composite(f, TAG2, TAG_X2 - TPAD + (1 - k2) * 18, TAG_Y - TPAD, k2 * out)
    return f


# ------------------------------------------------------------------ cards
CARDS = None


def flip_image(colour, t, t0):
    f = CARDS.wall.copy()
    f = Cards.put_figure(f, CARDS.solo[colour])
    CARDS.plaque_word(f, colour, reveal=ease_out((t - t0) / 0.14))
    f = look.look(f)
    settle = 1 + 0.05 * (1 - ease_out((t - t0) / P))
    return affine(f, settle)


_END_CACHE = {}
END_T0 = T(WIPE_BEAT)


def end_image(t):
    fig_k = [ease_out((t - T(57 + i) + 0.04) / 0.24) for i in range(3)]
    logo_k = ease_out((t - T(60)) / 0.30)
    cta_k = ease_out((t - T(62)) / 0.40)
    shine = (t - T(64)) / 0.55
    shine_on = 0 <= shine <= 1
    key = (tuple(round(k, 3) for k in fig_k), round(logo_k, 3), round(cta_k, 3), round(shine, 3) if shine_on else None)
    if key in _END_CACHE:
        g = _END_CACHE[key]
    else:
        f = CARDS.wall.copy()
        for (colour, layer), k in zip(CARDS.trio, fig_k):
            f = Cards.put_figure(f, layer, opacity=k, dy=(1 - k) * 26)
        if logo_k > 0:
            CARDS.plaque_logo(f, reveal=logo_k, shine=shine if shine_on else None)
        if cta_k > 0:
            CARDS.cta_line(f, reveal=cta_k)
        g = look.look(f)
        if len(_END_CACHE) < 400:
            _END_CACHE[key] = g
    g = g.copy()
    push = 1 + 0.045 * smooth((t - END_T0) / (tl.DURATION - END_T0))
    g = affine(g, push, cy=H * 0.45)
    # colour labels above the heads
    for i, (colour, _) in enumerate(CARDS.trio):
        k = ease_out((t - T(61) - i * 0.09) / 0.3)
        lab = CARDS.labels[colour]
        x = W / 2 + (CARDS.trio_x[i] - W / 2) * push - lab.shape[1] / 2
        y = H * 0.45 + (712 - H * 0.45) * push - lab.shape[0] / 2 + (1 - k) * 8
        typo.composite(g, lab, x, y, k)
    return g


# ------------------------------------------------------------------ transitions
def whip(f_idx, beat, a_id, b_id, t):
    k = f_idx - fb(beat)
    shiftA = {-4: -24, -3: -100, -2: -280, -1: -580}
    shiftB = {0: 580, 1: 280, 2: 100, 3: 24}
    blur = {-4: 30, -3: 90, -2: 170, -1: 260, 0: 260, 1: 170, 2: 90, 3: 30}
    if k < 0:
        A = hblur(affine(shot_image(a_id, t), dx=shiftA[k]), blur[k])
        if k == -1:
            B = hblur(affine(shot_image(b_id, t), dx=shiftB[0] + 300), 260)
            A = A * 0.72 + B * 0.28
        return A * (1 + 0.06 * (k + 5) / 4)
    B = hblur(affine(shot_image(b_id, t), dx=shiftB[k]), blur[k])
    if k == 0:
        A = hblur(affine(shot_image(a_id, t), dx=shiftA[-1] - 300), 260)
        B = B * 0.72 + A * 0.28
    return B * (1 + 0.06 * (4 - k) / 4)


def leak_layer(k, intensity):
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    cx1, cy1 = (0.15 + 0.06 * k) * W / 4, 0.30 * H / 4
    cx2, cy2 = (0.75 - 0.04 * k) * W / 4, 0.62 * H / 4
    b1 = np.exp(-(((xx - cx1) / (W / 4 * 0.42)) ** 2 + ((yy - cy1) / (H / 4 * 0.35)) ** 2))
    b2 = np.exp(-(((xx - cx2) / (W / 4 * 0.38)) ** 2 + ((yy - cy2) / (H / 4 * 0.30)) ** 2))
    lay = b1[..., None] * np.array([1.0, 0.62, 0.30], np.float32) + b2[..., None] * np.array([1.0, 0.80, 0.52], np.float32)
    lay = cv2.resize(lay, (W, H), interpolation=cv2.INTER_LINEAR)
    return np.clip(lay * intensity, 0, 1)


def light_leak(f_idx, beat, a_id, b_id, t):
    k = f_idx - fb(beat)
    if k < -2:
        base = shot_image(a_id, t)
    elif k > 2:
        base = shot_image(b_id, t)
    else:
        m = float(np.clip((k + 1.5) / 3.0, 0, 1))
        m = m * m * (3 - 2 * m)
        base = shot_image(a_id, t) * (1 - m) + shot_image(b_id, t) * m
    inten = 1.05 * np.exp(-(k / 3.0) ** 2)
    lay = leak_layer(k, inten)
    return 1 - (1 - base) * (1 - lay)


_FABRIC = None


def fabric_panel():
    global _FABRIC
    if _FABRIC is None:
        s = SHOT['S9']
        g = look.look(look.upscale(look.correct_native(clip(s['clip']).sample(3.0, 1.0), 'S9')))
        crop = g[520:1420, 430:820]
        pan = cv2.resize(crop, (1760, H), interpolation=cv2.INTER_LINEAR)
        pan = hblur(pan, 150)
        xs = np.linspace(-1, 1, pan.shape[1], dtype=np.float32)
        fold = (0.78 + 0.22 * np.cos(xs * np.pi * 1.6)) ** 1.2
        pan = pan * fold[None, :, None]
        alpha = np.clip(np.minimum(np.arange(1760), 1759 - np.arange(1760)) / 150.0, 0, 1).astype(np.float32)
        _FABRIC = (pan, alpha)
    return _FABRIC


def wipe(f_idx, t):
    k = f_idx - fb(WIPE_BEAT)
    left = {-4: 1080, -3: 700, -2: 290, -1: -90, 0: -360, 1: -820, 2: -1260, 3: -1640}[k]
    base = shot_image('S9', t) if k < 0 else end_image(t)
    pan, alpha = fabric_panel()
    x0 = int(left)
    xs0, xs1 = max(0, x0), min(W, x0 + pan.shape[1])
    if xs1 > xs0:
        sl = slice(xs0 - x0, xs1 - x0)
        a = alpha[sl][None, :, None]
        base[:, xs0:xs1] = base[:, xs0:xs1] * (1 - a) + pan[:, sl] * a
    return base


# ------------------------------------------------------------------ frame
def which_shot(f):
    for sid in ORDER:
        a, b = RANGES[sid]
        if a <= f < b:
            return sid
    return ORDER[-1]


def render(f):
    t = f / FPS
    sid = which_shot(f)
    # transitions take over the base image near their cut
    base = None
    for beat, (a_id, b_id) in WHIPS.items():
        if -4 <= f - fb(beat) <= 3:
            base = whip(f, beat, a_id, b_id, t)
    for beat, (a_id, b_id) in LEAK.items():
        if -6 <= f - fb(beat) <= 6:
            base = light_leak(f, beat, a_id, b_id, t)
    if -4 <= f - fb(WIPE_BEAT) <= 3:
        base = wipe(f, t)
    if base is None:
        if sid == 'pre':
            g = shot_image('pre', t)
            k = f - fb(0)                      # negative
            if k >= -4:
                u = (k + 5) / 5.0
                g = zoom_blur(affine(g, 1.04 + 0.10 * ease_in(u)), 0.06 * ease_in(u))
            else:
                g = affine(g, 1.0 + 0.04 * smooth(t / (T(0) - 4 / FPS)))
            base = g
        elif sid.startswith('flip'):
            colour = SHOT[sid]['still']
            base = flip_image(colour, t, T(SHOT[sid]['b0']))
        elif sid == 'end':
            base = end_image(t)
        else:
            base = shot_image(sid, t)
    # punch-in and shake on cuts (not during the end-card push)
    if sid not in ('end',) and not sid.startswith('flip'):
        dx, dy = shake_offset(f)
        base = affine(base, punch_scale(f), dx, dy)
    elif sid.startswith('flip'):
        dx, dy = shake_offset(f)
        base = affine(base, 1.0 + (punch_scale(f) - 1) * 0.6, dx, dy)
    else:
        dx, dy = shake_offset(f)
        base = affine(base, 1.0, dx, dy)
    base = apply_flash(base, flash_amount(f))
    base = look.vignette(base)
    # typography
    base = draw_tagline(base, t)
    for p in PILLS:
        base = p.draw(base, t)
    for c in CALLOUTS:
        base = c.draw(base, t)
    base = look.grain(base, f)
    fade = np.clip((tl.DURATION - t) / 0.45, 0, 1)
    if fade < 1:
        base = base * smooth(fade)
    return np.clip(base, 0, 1)


def main():
    global CARDS
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='campaign/mockneck-set/exports/basic-ad-video.mp4')
    ap.add_argument('--audio')
    ap.add_argument('--frames')
    ap.add_argument('--stills')
    ap.add_argument('--crf', default='15')
    a = ap.parse_args()
    CARDS = Cards()
    if a.stills:
        os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
        for s in a.stills.split(','):
            fr = int(s)
            img = (render(fr) * 255).astype(np.uint8)
            cv2.imwrite(a.out.replace('.mp4', f'_f{fr:04d}.jpg'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        return
    f0, f1 = 0, N
    if a.frames:
        f0, f1 = [int(x) for x in a.frames.split(':')]
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-']
    if a.audio:
        cmd += ['-ss', f'{f0 / FPS:.4f}', '-i', a.audio, '-shortest']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-pix_fmt', 'yuv420p', '-profile:v', 'high',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart']
    if a.audio:
        cmd += ['-c:a', 'aac', '-b:a', '320k', '-ar', '48000']
    cmd += [a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in range(f0, f1):
        img = (render(fr) * 255 + 0.5).astype(np.uint8)
        proc.stdin.write(img.tobytes())
        if fr % 48 == 0:
            print(f'frame {fr}/{f1}', flush=True)
    proc.stdin.close()
    proc.wait()
    print('wrote', a.out)


if __name__ == '__main__':
    main()
