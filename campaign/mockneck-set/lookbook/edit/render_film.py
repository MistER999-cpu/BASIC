#!/usr/bin/env python3
"""Render the full BASIC lookbook film (Noir, Chocolat, Burgundy + end card), 1080x1920 @ 24 fps.

    python3 campaign/mockneck-set/lookbook/edit/render_film.py --out film.mp4 [--audio mix.wav] [--stills 10,200]
"""
import os
import sys
import argparse
import subprocess
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_part as rp       # noqa: E402  (chdirs to repo root, sets up look/typo)
import film as FM              # noqa: E402

look, typo = rp.look, rp.typo
W, H, NW, NH, OUT_S = rp.W, rp.H, rp.NW, rp.NH, rp.OUT_S
CREAM, INK = rp.CREAM, typo.INK
ease_out, smooth = rp.ease_out, rp.smooth


def soft_burgundy(f, dh, ks, kv):
    """Shift wine fabric toward the product sheet with a soft weight (no hard mask, so lit folds and
    shadows move together instead of leaving uncorrected patches). Skin and light hair have a high
    G/R ratio and are left alone."""
    f = np.clip(f, 0, 1).astype(np.float32)
    hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV)
    h, sat, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    r, g = f[..., 0], f[..., 1]
    gr = g / (r + 1e-3)
    hd = np.minimum(np.abs(h - 345), 360 - np.abs(h - 345))           # distance from wine hue
    w = (np.clip((0.70 - gr) / 0.14, 0, 1) * np.clip((45 - hd) / 20, 0, 1)
         * np.clip((sat - 0.12) / 0.12, 0, 1) * np.clip((0.88 - v) / 0.15, 0, 1))
    w = cv2.GaussianBlur(w, (0, 0), 2.0)
    hsv[..., 0] = (h + dh * w) % 360
    hsv[..., 1] = np.clip(sat * (1 + (ks - 1) * w), 0, 1)
    hsv[..., 2] = np.clip(v * (1 + (kv - 1) * w), 0, 1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


class Film(rp.Part):
    def __init__(self, spec):
        spec = dict(spec)
        spec.setdefault('title', 'NOIR')
        spec.setdefault('masthead', {})
        super().__init__(spec)
        self._mh_cache = {}
        self._end = None

    # colour: burgundy clips pulled toward the product sheet
    def frame(self, src, s):
        f = super().frame(src, s)
        p = self.spec['burgundy'].get(src)
        if p:
            f = soft_burgundy(f, **p)
        return f

    def _build_logo(self):
        super()._build_logo()

    # one masthead word per segment
    def masthead(self, f, base, seg, s, M):
        mh = seg['masthead']
        key = (mh['word'], mh.get('baseline'))
        if key not in self._mh_cache:
            self.spec['title'] = mh['word']
            self.spec['masthead'] = dict(mh)
            self._build_masthead()
            self._mh_cache[key] = (self.mh_letters, self.mh_shade)
        self.mh_letters, self.mh_shade = self._mh_cache[key]
        self.spec['masthead'] = dict(mh)
        return super().masthead(f, base, seg, s, M)

    def draw_label(self, frame, seg, f):
        self.spec['small_label'] = {'align': seg.get('small_align', 'left')}
        return super().draw_label(frame, seg, f)

    # ------------------------------------------------------------- end card
    def build_end(self):
        plate = np.asarray(Image.open(os.path.join(rp.ROOT, 'campaign', 'mockneck-set', 'lookbook',
                                                    'backdrop-plate.jpg')).convert('RGB')).astype(np.float32) / 255
        ph, pw = plate.shape[:2]
        sc = W / pw
        plate = cv2.resize(plate, (W, int(round(ph * sc))), interpolation=cv2.INTER_LANCZOS4)[:H]
        # match the plate's wall to the graded clips' wall
        wall_ref = np.array(self.spec['backdrop']['N1'], np.float32) / 255 * self.corr['N1']
        wall_plate = np.median(plate[int(H * 0.30):int(H * 0.40), 40:200].reshape(-1, 3), 0)
        plate = np.clip(plate * (wall_ref / wall_plate)[None, None, :], 0, 1)
        self.end_plate = cv2.GaussianBlur(plate, (0, 0), 1.2)
        # three living figures, front poses, frames 4..14 of each master clip
        self.end_figs = []
        for src, cx in (('N1', 236), ('C1', 540), ('B1', 844)):
            M = self.align.get(src, np.eye(3))
            frames = []
            for i in range(4, 15):
                rgb = self.frame(src, i)
                a = self.mask(src, i)
                a = np.clip((a - 0.1) / 0.8, 0, 1)
                a = cv2.erode(a, np.ones((3, 3), np.uint8))
                a = cv2.GaussianBlur(a, (0, 0), 0.9)
                frames.append((rgb, a))
            self.end_figs.append((src, cx, M, frames))
        self.end_scale = 0.55
        self.end_feet = 1296
        # type
        lg = self.logo
        self.end_logo_a = cv2.resize(lg, (int(lg.shape[1] * 1.08), int(lg.shape[0] * 1.08)), interpolation=cv2.INTER_AREA)
        self.end_line = typo.text_layer('NOIR  ·  CHOCOLAT  ·  BURGUNDY', 'sans_med', 22, CREAM, tracking=7,
                                        shadow=0.55, shadow_blur=8)
        self.end_cta = typo.text_layer('DISPONIBLE MAINTENANT', 'sans_med', 25, INK, tracking=10)

    def end_frame(self, f):
        if self._end is None:
            self.build_end()
            self._end = True
        f0 = FM.B(30)
        t = f - f0
        img = self.end_plate.copy()
        # figures
        for k, (src, cx, M, frames) in enumerate(self.end_figs):
            ap = ease_out((t - 2 * k * 4) / 6.0)
            if ap <= 0:
                continue
            ph = (t * 0.45) % (2 * (len(frames) - 1))
            idx = int(ph if ph < len(frames) - 1 else 2 * (len(frames) - 1) - ph)
            rgb, a = frames[idx]
            # native -> master (align) -> scaled into the line-up
            sc = OUT_S * self.end_scale
            feet_native = 1191                      # master feet line (N1)
            Mo = np.array([[sc, 0, cx - sc * 362], [0, sc, self.end_feet - sc * feet_native + (1 - ap) * 24], [0, 0, 1]]) @ M
            rgb_o = cv2.warpAffine(rgb, Mo[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            a_o = cv2.warpAffine(a, Mo[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT) * ap
            # contact shadow
            yy, xx = np.ogrid[0:H, 0:W]
            sh = np.exp(-(((xx - cx - 10) / 120.0) ** 2 + ((yy - self.end_feet) / 14.0) ** 2)) * 0.45 * ap
            img = img * (1 - sh[..., None] * np.array([0.55, 0.58, 0.62], np.float32))
            img = img * (1 - a_o[..., None]) + rgb_o * a_o[..., None]
        # strobe pop as each figure lands
        for k in range(3):
            j = t - 2 * k * 4
            if 0 <= j < 4:
                img = img + (1 - img) * rp.STROBE[j] * 0.8
        img = look.look(img, halation=0.10, bloom=0.03)
        img = img * rp.VIGNETTE
        # slow push-in on the whole card
        push = 1 + 0.035 * smooth(t / (FM.B(36.5) - f0))
        img = rp.affine_out(img, push) if hasattr(rp, 'affine_out') else cv2.warpAffine(
            img, np.float32([[push, 0, (1 - push) * W / 2], [0, push, (1 - push) * H * 0.45]]), (W, H),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        # logo
        lk = ease_out((t - 32) / 7.0)
        if lk > 0:
            a = self.end_logo_a
            h, w = a.shape
            x0, y0 = int(W / 2 - w / 2), int(318 - h / 2 + (1 - lk) * 10)
            sh = cv2.GaussianBlur(a, (0, 0), 6) * 0.45 * lk
            reg = img[y0:y0 + h, x0:x0 + w]
            reg[:] = reg * (1 - sh[..., None])
            col = np.array(CREAM, np.float32) / 255
            reg[:] = reg * (1 - (a * lk)[..., None]) + col * (a * lk)[..., None]
            shine = (t - 64) / 10.0
            if 0 <= shine <= 1:
                yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
                band = np.exp(-((xx + yy * 0.5 - (shine * (w + h) - h * 0.25)) / 24) ** 2)
                reg[:] = reg + (1 - reg) * (band * a)[..., None] * 0.6
        # colour line and CTA
        lay, (tw, th), pad = self.end_line
        k1 = ease_out((t - 40) / 7.0)
        if k1 > 0:
            typo.composite(img, lay, W / 2 - tw / 2 - pad, 452 + (1 - k1) * 8 - pad, k1)
        lay, (tw, th), pad = self.end_cta
        k2 = ease_out((t - 48) / 7.0)
        if k2 > 0:
            typo.composite(img, lay, W / 2 - tw / 2 - pad, 1352 + (1 - k2) * 8 - pad, k2 * 0.92)
        return img


def render(film, f):
    seg = rp.find_seg(film, f)
    if seg is not None and seg.get('kind') == 'end':
        img = film.end_frame(f)
    else:
        img, _ = rp.render(film, f)
    fade = np.clip((film.end - f) / 10.0, 0, 1)
    if fade < 1:
        img = img * smooth(fade)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--audio')
    ap.add_argument('--stills')
    ap.add_argument('--crf', default='15')
    a = ap.parse_args()
    film = Film(FM.FILM)
    if a.stills:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        for st in a.stills.split(','):
            fr = int(st)
            img = look.grain(render(film, fr), fr, amp=0.014)
            cv2.imwrite(a.out.replace('.mp4', f'_f{fr:04d}.jpg'),
                        cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
        return
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(rp.FPS), '-i', '-']
    if a.audio:
        cmd += ['-i', a.audio, '-shortest']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-pix_fmt', 'yuv420p', '-profile:v', 'high',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart']
    if a.audio:
        cmd += ['-c:a', 'aac', '-b:a', '320k', '-ar', '48000']
    cmd += [a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in range(film.end):
        img = look.grain(render(film, fr), fr, amp=0.014)
        proc.stdin.write((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        if fr % 48 == 0:
            print(f'frame {fr}/{film.end}', flush=True)
    proc.stdin.close()
    proc.wait()
    print('wrote', a.out)


if __name__ == '__main__':
    main()
