#!/usr/bin/env python3
"""BASIC Essentials — « Se fondre dans l'hiver »: 15 s Instagram film, 1080x1920 @ 24 fps.

Built on the structure of reference 3: a three-band split screen that fills on the beat with one
script word per band, a walk-past wipe into full-screen shots, the rotated walking shot, the hip
detail, then our two extra scenes (pocket, collar) and a frost end card with the logo.
Cut on the track's 70 BPM grid (beat 0 = first frame).

    python3 campaign/mockneck-set/winter/edit/wedit.py --out film.mp4 [--audio mix.wav] [--stills 0,60,...]
"""
import os
import sys
import argparse
import subprocess
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wlook as L      # noqa: E402
import wfx as X        # noqa: E402

ROOT = X.ROOT
CLIPDIR = os.path.join(ROOT, 'campaign', 'mockneck-set', 'winter', 'clips')
FPS, W, H = 24, 1080, 1920
BEAT = 0.856895                      # 70.02 BPM, measured on the track
FPB = BEAT * FPS


def B(b):
    return int(round(b * FPB))


N_FRAMES = 360                       # 15.0 s

CLIPS = {'W1': 'W1-collar-pockets.mp4', 'W2': 'W2-boots-topdown.mp4', 'W3': 'W3-walk-bag.mp4',
         'S1': 'S1-lookback-wall.mp4', 'S2': 'S2-back-hem.mp4', 'S3': 'S3-fitcheck-pov.mp4',
         'S4': 'S4-stride-landscape.mp4', 'S5': 'S5-hand-hip.mp4', 'X1': 'X1-collar-cold.mp4',
         'X2': 'X2-pocket.mp4'}

# ------------------------------------------------------------------ edit decision list
BANDS = [  # clip, band reveal frame, source frame at reveal, native centre y, word, word centre y
    ('W1', B(0), 2, 650, 'Se fondre', 300),
    ('W2', B(1), 18, 520, 'dans', 958),
    ('W3', B(2), 30, 700, 'l’hiver', 1556),
]
WIPE0, WIPE1 = B(3.5), B(4.5)        # the walk-past: enters on 3.5, gone on 4.5 (whoosh on beat 4)
SHOTS = [  # name, f0, f1, source frame at f0, speed, punch-in, slow push
    ('S1', B(3.5), B(5.5), 44, 1.0, 0.000, 0.040),
    ('S2', B(5.5), B(7), 26, 1.0, 0.045, 0.030),
    ('S3', B(7), B(9), 40, 1.0, 0.040, 0.030),
    ('S4', B(9), B(10), 28, 1.0, 0.000, 0.020),
    ('S5', B(10), B(11), 36, 1.0, 0.050, 0.030),
    ('X2', B(11), B(13), 46, 1.2, 0.050, 0.030),
    ('X1', B(13), B(15), 54, 1.0, 0.040, 0.070),
]
WHIP = B(9)                          # S3 -> S4 rotation whip, on the cymbal of beat 9
POPS = (B(10), B(11))                # exposure pops on the two strongest kicks
FROST0, END, SHINE = B(14), B(15), B(16)
SNOW_K = {'band': 0.75, 'S1': 0.55, 'S2': 0.6, 'S3': 0.4, 'S4': 0.5, 'S5': 0.55, 'X2': 0.55,
          'X1': 0.65, 'end': 0.6}
LOGO_COL = np.array([0.315, 0.072, 0.150], np.float32)       # deep wine, the set's colour on frost


# ------------------------------------------------------------------ sources
class Clips:
    def __init__(self):
        self.raw = {}
        self.cache = {}

    def _load(self, name):
        cap = cv2.VideoCapture(os.path.join(CLIPDIR, CLIPS[name]))
        frames = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
            if name == 'S4':                          # landscape walk, turned like the reference
                f = cv2.rotate(f, cv2.ROTATE_90_CLOCKWISE)
            frames.append(f)
        self.raw[name] = frames

    def get(self, name, idx):
        if name not in self.raw:
            self._load(name)
        fr = self.raw[name]
        idx = float(np.clip(idx, 0, len(fr) - 1))
        i0 = int(np.floor(idx))
        a = idx - i0
        out = self._corr(name, i0)
        if a > 0.08 and i0 + 1 < len(fr):
            out = out * (1 - a) + self._corr(name, i0 + 1) * a
        return out

    def _corr(self, name, i):
        k = (name, i)
        if k not in self.cache:
            if len(self.cache) > 80:
                self.cache.pop(next(iter(self.cache)))
            self.cache[k] = L.correct(self.raw[name][i], name)
        return self.cache[k]


def place(nat, zoom=1.0, cx=360.0, cy=640.0, angle=0.0, size=(W, H), centre=None,
          border=cv2.BORDER_REFLECT_101, interp=cv2.INTER_LANCZOS4):
    """Native 720x1280 frame -> output, native point (cx, cy) landing on `centre`."""
    s = (W / 720.0) * zoom
    centre = centre or (size[0] / 2, size[1] / 2)
    M = cv2.getRotationMatrix2D((cx, cy), angle, s)
    M[0, 2] += centre[0] - cx
    M[1, 2] += centre[1] - cy
    return cv2.warpAffine(nat, M, size, flags=interp, borderMode=border)


# ------------------------------------------------------------------ the film
class Film:
    def __init__(self):
        self.clips = Clips()
        self.snow = X.Snow(W, H, seed=7)
        self.snow_rot = X.Snow(H, W, seed=8)           # landscape canvas, turned for the S4 shot
        self.frost = X.Frost(W, H, seed=5)
        self.words = [X.ScriptWord(b[4], 118) for b in BANDS]
        self.logo = X.logo_alpha(640)
        lh, lw = self.logo.shape
        self.logo_noise = X.fractal_noise(lw, lh, 23, cells=(48, 24, 12, 6), weights=(1, 0.6, 0.35, 0.2))
        self._figure = None
        self._end_base = None

    # -------------------------------------------------------------- opening split screen
    def band(self, k, f):
        clip, fr, s0, cy, _, _ = BANDS[k]
        t = f - fr
        nat = self.clips.get(clip, s0 + t)
        zoom = 1 + 0.07 * (1 - X.ease_out(t / 9.0))
        img = place(nat, zoom, 360, cy, size=(W, 640), centre=(540, 320))
        img = L.sharpen(img, 0.3)
        if t < 6:                                       # exposure flash as the band lands
            img = img + (1 - img) * (0.22 if k == 0 else 0.45) * np.exp(-t / 2.2)
        return img

    def split(self, f):
        cv = np.zeros((H, W, 3), np.float32)
        for k, (_, fr, *_r) in enumerate(BANDS):
            if f < fr:
                continue
            t = f - fr
            img = self.band(k, f)
            vis = X.ease_out((t + 1) / 4.0)               # opens from its centre line
            half = int(round(320 * vis))
            cv[k * 640 + 320 - half:k * 640 + 320 + half] = img[320 - half:320 + half]
        cv[639:641] = 0
        cv[1279:1281] = 0
        cv = L.grade(cv)
        for k, (_, fr, _, _, _, wy) in enumerate(BANDS):
            p = (f - fr - 2) / 13.0
            if p > 0:
                cv = self.words[k].composite(cv, 540, wy, min(p, 1.0))
        return cv

    # -------------------------------------------------------------- walk-past wipe
    def figure(self):
        if self._figure is not None:
            return self._figure
        import rembg
        from PIL import Image
        nat = self.clips.get('W3', 40)
        sess = rembg.new_session('isnet-general-use')
        m = rembg.remove(Image.fromarray((nat * 255).astype(np.uint8)), session=sess, only_mask=True)
        a = np.asarray(m).astype(np.float32) / 255
        ys, xs = np.where(a > 0.5)
        cxn = float(np.median(xs))
        cyn = 560.0
        sc = 3.8
        bw = (xs.max() - xs.min()) * sc
        Wc = int(bw + 600)
        M = np.float32([[sc, 0, Wc / 2 - sc * cxn], [0, sc, H / 2 - sc * cyn]])
        rgb = cv2.warpAffine(nat, M, (Wc, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
        al = cv2.warpAffine(a, M, (Wc, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        rgb = L.grade_simple(rgb) * np.array([0.80, 0.80, 0.83], np.float32)
        pre = np.concatenate([rgb * al[..., None], al[..., None]], 2)
        pre = cv2.GaussianBlur(pre, (0, 0), 9)                     # far too close to focus
        pre = cv2.blur(pre, (70, 1))                                 # and moving fast
        al = np.clip(pre[..., 3], 0, 1)
        rgb = pre[..., :3] / np.maximum(pre[..., 3:], 1e-4)
        cov = np.array([al[:, x].min() for x in range(Wc)])
        seam = int(np.argmax(cov))
        print(f'pass figure {Wc}px wide, seam col {seam} min alpha {cov[seam]:.3f}', flush=True)
        self._figure = (rgb.astype(np.float32), al.astype(np.float32), Wc, seam)
        return self._figure

    def wipe(self, f, bg_split, bg_shot):
        rgb, al, Wc, seam = self.figure()
        q = (f - WIPE0 + 0.5) / (WIPE1 - WIPE0)
        left = -Wc + q * (W + Wc)
        sx = left + seam
        xx = np.arange(W, dtype=np.float32)
        m = X.smoothstep(sx + 40, sx - 40, xx)[None, :, None]       # left of the seam: new shot
        img = bg_split * (1 - m) + bg_shot * m
        x0 = int(round(left))
        a0, a1 = max(0, x0), min(W, x0 + Wc)
        if a1 > a0:
            sub_a = al[:, a0 - x0:a1 - x0, None]
            img[:, a0:a1] = img[:, a0:a1] * (1 - sub_a) + rgb[:, a0 - x0:a1 - x0] * sub_a
        return img

    # -------------------------------------------------------------- full-screen shots
    def shot(self, sh, f):
        name, f0, f1, s0, spd, punch, push = sh
        t = f - f0
        src = s0 + t * spd
        nat = self.clips.get(name, src)
        zoom = 1 + punch * (1 - X.ease_out(t / 8.0)) + push * t / (f1 - f0)
        angles = [0.0]
        if name == 'S3' and f >= WHIP - 6:                      # whip out, clockwise
            qa = lambda ff: ((ff - (WHIP - 7)) / 7.0) ** 2      # noqa: E731
            angles = [-55 * qa(f - 0.5 + i / 5) for i in range(6)]
            zoom *= 1 + 0.30 * qa(f)
        if name == 'S4' and t < 6:                              # whip in, still turning clockwise
            qb = lambda tt: max(0.0, 1 - tt / 6.0) ** 2         # noqa: E731
            angles = [55 * qb(t - 0.5 + i / 5) for i in range(6)]
            zoom *= 1 + 0.30 * qb(t)
        if len(angles) > 1:
            img = np.mean([place(nat, zoom, angle=a, interp=cv2.INTER_LINEAR) for a in angles], 0)
        else:
            img = L.sharpen(place(nat, zoom), 0.35)
        if f in range(POPS[0], POPS[0] + 4) or f in range(POPS[1], POPS[1] + 4):
            k = f - (POPS[0] if f < POPS[1] else POPS[1])
            img = img + (1 - img) * 0.16 * np.exp(-k / 1.3)
        return L.grade(img)

    def shot_at(self, f):
        for sh in SHOTS:
            if sh[1] <= f < sh[2]:
                return sh
        return None

    # -------------------------------------------------------------- end card
    def end_base(self):
        if self._end_base is None:
            sh = SHOTS[-1]
            self._end_base = self.shot(sh, sh[2] - 1)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            e = ((xx - W / 2) / 430) ** 2 + ((yy - H * 0.485) / 270) ** 2
            self._calm = X.smoothstep(0.6, 1.6, e)                  # fewer crystals behind the logo
        return self._end_base

    def end_card(self, f):
        base = self.end_base()
        t = f - END
        e = X.ease_out(t / 14.0)
        fr = self.frost
        img = fr.frosted(base, blur=22 + 26 * e, white=0.58 + 0.16 * e, sat=0.75 - 0.35 * e,
                         crystal=fr.crystal * (1 - 0.7 * e * (1 - self._calm)))
        z = 1 + 0.025 * t / (N_FRAMES - END)
        Mz = np.float32([[z, 0, (1 - z) * W / 2], [0, z, (1 - z) * H / 2]])
        img = cv2.warpAffine(np.clip(img, 0, 1), Mz, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        img = img + (1 - img) * (0.40 * np.exp(-t / 3.0))             # the hit on beat 15
        g = fr.glints(t / FPS, 0.55)
        img = 1 - (1 - img) * (1 - g[..., None] * np.array([0.95, 0.98, 1.0], np.float32))
        img = self.draw_logo(img, t)
        return np.clip(img, 0, 1)

    def draw_logo(self, img, t):
        p = t / 11.0
        if p <= 0:
            return img
        a = self.logo
        lh, lw = a.shape
        q = -0.12 + 1.25 * X.ease_in_out(min(p, 1.0))
        rv = X.smoothstep(self.logo_noise - 0.07, self.logo_noise + 0.07, q)
        vis = a * rv
        sc = 1 + 0.03 * (1 - X.ease_out(p))
        sig = 1.4 * (1 - X.ease_out(p))
        cx, cy = W / 2, H * 0.485
        Ms = np.float32([[sc, 0, cx - sc * lw / 2], [0, sc, cy - sc * lh / 2]])
        visw = cv2.warpAffine(vis, Ms, (W, H), flags=cv2.INTER_LINEAR)
        if sig > 0.3:
            visw = cv2.GaussianBlur(visw, (0, 0), sig)
        front = a * (4 * rv * (1 - rv))
        frontw = cv2.warpAffine(front, Ms, (W, H), flags=cv2.INTER_LINEAR)
        # soft lift behind the mark, then the ink
        halo = cv2.GaussianBlur(visw, (0, 0), 16) * 0.18
        img = 1 - (1 - img) * (1 - halo[..., None])
        img = img * (1 - visw[..., None]) + LOGO_COL * visw[..., None]
        sp = cv2.GaussianBlur(frontw, (0, 0), 1.2) * 0.9 + cv2.GaussianBlur(frontw, (0, 0), 6) * 0.6
        img = 1 - (1 - img) * (1 - np.clip(sp, 0, 1)[..., None] * np.array([0.92, 0.97, 1.0], np.float32))
        # light glint across the mark on beat 16
        s = (t - (SHINE - END)) / 11.0
        if 0 <= s <= 1:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            c = -300 + s * (W + 700)
            band = np.exp(-((xx + 0.45 * (yy - cy) - c) / 34) ** 2)
            img = img + (1 - img) * (band * visw)[..., None] * 0.55
        return img

    # -------------------------------------------------------------- per frame
    def frame(self, f):
        tsec = f / FPS
        if f >= END:
            img = self.end_card(f)
            A = self.snow.alpha(tsec, SNOW_K['end'], classes=(0, 1, 2))
        elif f < WIPE0:
            img = self.split(f)
            A = self.snow.alpha(tsec, SNOW_K['band'])
        elif f < WIPE1:
            img = self.wipe(f, self.split(f), self.shot(SHOTS[0], f))
            A = self.snow.alpha(tsec, SNOW_K['band'])
        else:
            sh = self.shot_at(f)
            img = self.shot(sh, f)
            if sh[0] == 'X1' and f >= FROST0:
                p = X.ease_in_out((f - FROST0 + 1) / (END - FROST0))
                img = self.frost.apply(img, p)
            if sh[0] == 'S4':
                A = cv2.rotate(self.snow_rot.alpha(tsec, SNOW_K['S4']), cv2.ROTATE_90_CLOCKWISE)
            else:
                A = self.snow.alpha(tsec, SNOW_K[sh[0]])
        img = X.composite_snow(img, A)
        return L.grain(img, f, amp=0.012)


def to_u8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--audio')
    ap.add_argument('--stills')
    ap.add_argument('--crf', default='16')
    a = ap.parse_args()
    film = Film()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if a.stills:
        for s in a.stills.split(','):
            f = int(s)
            cv2.imwrite(a.out.replace('.mp4', f'_f{f:03d}.jpg'), cv2.cvtColor(to_u8(film.frame(f)), cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
            print('still', f, flush=True)
        return
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-']
    if a.audio:
        cmd += ['-i', a.audio]
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-pix_fmt', 'yuv420p', '-profile:v', 'high',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart']
    if a.audio:
        cmd += ['-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-shortest']
    cmd += [a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(N_FRAMES):
        proc.stdin.write(to_u8(film.frame(f)).tobytes())
        if f % 24 == 0:
            print(f'frame {f}/{N_FRAMES}', flush=True)
    proc.stdin.close()
    proc.wait()
    print('wrote', a.out)


if __name__ == '__main__':
    main()
