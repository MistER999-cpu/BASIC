#!/usr/bin/env python3
"""Render one colourway part of the BASIC lookbook film (1080x1920, 24 fps).

    python3 campaign/mockneck-set/lookbook/edit/render_part.py --part noir --out out.mp4 [--audio mix.wav]
           [--stills 10,60,120]

Effects: locked-framing pose flicks with studio-strobe pops, a masthead title composited behind
the model's head, zoom-dives into detail inserts, blurred pass-by wipes in and out, French
detail labels, one shared film look (tone, halation, grain, vignette).
"""
import os
import sys
import argparse
import subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'campaign', 'mockneck-set', 'edit'))
os.chdir(ROOT)

import parts as P          # noqa: E402
import look                # noqa: E402  shared tone curve, halation, grain
import typo                # noqa: E402  tracked text, compositing

W, H = 1080, 1920
NW, NH = 720, 1280
OUT_S = W / NW
FPS = P.FPS
CREAM = (246, 240, 231)
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
MASK_DIR = os.environ.get('BASIC_MASKS', '/tmp/claude-0/-home-user-BASIC/8e039bbb-0863-56b6-8191-6c4b726ceae0/scratchpad/noirpart/masks')

DIVE_SCALE = [1.0, 1.14, 1.36, 1.72]
DIVE_BLUR = [0.0, 0.025, 0.06, 0.11]
LAND_SCALE = [1.20, 1.08, 1.025, 1.0]
LAND_BLUR = [0.07, 0.03, 0.01, 0.0]
STROBE = [0.11, 0.045, 0.015, 0.0]


def ease_out(u):
    u = float(np.clip(u, 0, 1))
    return 1 - (1 - u) ** 3


def smooth(u):
    u = float(np.clip(u, 0, 1))
    return u * u * (3 - 2 * u)


def S(s, p):
    px, py = p
    return np.array([[s, 0, px * (1 - s)], [0, s, py * (1 - s)], [0, 0, 1]], np.float64)


OUT = np.diag([OUT_S, OUT_S, 1.0])


# ------------------------------------------------------------------ sources
def load_clip(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, NH, NW, 3)


class Part:
    def __init__(self, spec):
        self.spec = spec
        self.clips = {k: load_clip(v) for k, v in spec['clips'].items()}
        self.corr = self._corrections()
        self.align = {k: S(s, p) for k, (s, p) in spec.get('align', {}).items()}
        self.pivots = spec['pivots']
        self.segs = spec['segments']
        self.end = spec['end']
        self._mask_cache = {}
        self._build_masthead()
        self._build_pass()
        self._labels = {}
        self._build_logo()

    def _build_logo(self):
        lg = np.asarray(Image.open(os.path.join(ROOT, 'campaign', 'mockneck-set', 'refs', 'logo.png')).convert('RGBA'))
        al = lg[..., 3].astype(np.float32) / 255
        ys, xs = np.nonzero(al > 0.05)
        al = al[ys.min() - 4:ys.max() + 5, xs.min() - 4:xs.max() + 5]
        w = 430
        h = int(round(al.shape[0] * w / al.shape[1]))
        self.logo = cv2.resize(al, (w, h), interpolation=cv2.INTER_AREA)

    def end_logo(self, f):
        f0, f1 = self.spec['endlogo']
        base = np.zeros((H, W, 3), np.float32)
        u = ease_out((f - f0) / 5.0) * (1 - smooth((f - (f1 - 6)) / 6.0))
        if u <= 0:
            return base
        sc = 1.05 - 0.05 * ease_out((f - f0) / 12.0)
        a = self.logo
        h, w = a.shape
        M = np.float32([[sc, 0, W / 2 - sc * w / 2], [0, sc, H * 0.47 - sc * h / 2]])
        A = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR) * u
        glow = cv2.GaussianBlur(A, (0, 0), 18) * 0.25
        col = np.array(CREAM, np.float32) / 255
        return base + col[None, None, :] * np.clip(A + glow, 0, 1)[..., None]

    def _corrections(self):
        bd = self.spec['backdrop']
        ref = np.array(self.spec.get('reference_backdrop', bd[self.spec['reference_clip']]), np.float64)
        refL = ref @ LUMA
        tg, tb = ref[1] / ref[0], ref[2] / ref[0]
        out = {}
        for k, c in bd.items():
            c = np.array(c, np.float64)
            L = c @ LUMA
            gG = (tg / (c[1] / c[0])) ** 0.7
            gB = (tb / (c[2] / c[0])) ** 0.7
            e = (refL / L) ** (0.5 if L < 150 else 0.3)
            e = self.spec.get('exposure', {}).get(k, e)
            out[k] = np.array([e, e * gG, e * gB], np.float32)
        return out

    def frame(self, src, s):
        clip = self.clips[src]
        s = float(np.clip(s, 0, len(clip) - 1))
        i0 = int(np.floor(s))
        a = s - i0
        f = clip[i0].astype(np.float32)
        if a > 1e-3 and i0 + 1 < len(clip):
            f = f * (1 - a) + clip[i0 + 1].astype(np.float32) * a
        return np.clip(f / 255.0 * self.corr[src][None, None, :], 0, 1)

    def mask(self, src, s):
        """Subject matte (native res), averaged over neighbouring frames to stop edge shimmer."""
        i = int(round(s))
        key = (src, i)
        if key in self._mask_cache:
            return self._mask_cache[key]
        acc, n = None, 0
        for j in (i - 1, i, i + 1):
            p = os.path.join(MASK_DIR, f'{src}_{j:03d}.png')
            if os.path.exists(p):
                m = cv2.imread(p, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
                acc = m if acc is None else acc + m
                n += 1
        m = None if acc is None else cv2.GaussianBlur(acc / n, (0, 0), 1.0)
        self._mask_cache[key] = m
        return m

    # ---------------------------------------------------------- masthead
    def _build_masthead(self):
        word = self.spec['title']
        font_path = typo.FONT['didone']
        target_w = 900
        track = 0.06
        probe = ImageFont.truetype(font_path, 100)
        widths = [probe.getlength(ch) for ch in word]
        em = target_w / (sum(widths) / 100 + track * (len(word) - 1))
        font = ImageFont.truetype(font_path, int(em))
        x = (W - target_w) / 2
        bb = font.getbbox(word[0])
        cap_top = 196
        mh = self.spec.get('masthead', {})
        if 'baseline' in mh:
            cap_top = int(mh['baseline'] - (bb[3] - bb[1]))
        letters = []
        for ch in word:
            img = Image.new('L', (W, H), 0)
            d = ImageDraw.Draw(img)
            d.text((x, cap_top - bb[1]), ch, font=font, fill=255)
            letters.append(np.asarray(img).astype(np.float32) / 255)
            x += font.getlength(ch) + track * em
        self.mh_letters = letters
        cap_h = bb[3] - bb[1]
        y = np.arange(H, dtype=np.float32)
        # printed on the paper: dims with the backdrop's fall-off toward the top
        shade = np.clip(0.74 + 0.20 * (y - cap_top) / max(cap_h, 1), 0.74, 0.95)
        self.mh_shade = shade[:, None, None]

    def masthead(self, f, base, seg, s, M):
        spec = self.spec['masthead']
        f0, f1 = seg['f0'], seg['f1']
        out_k = 1 - smooth((f - (f1 - 7)) / 3.0)
        if out_k <= 0:
            return base
        a = np.zeros((H, W), np.float32)
        for i, L in enumerate(self.mh_letters):
            u = ease_out((f - (f0 + 2 + 2 * i)) / 7.0)
            if u <= 0:
                continue
            dy = (1 - u) * 26
            Li = L if dy < 0.5 else cv2.warpAffine(L, np.float32([[1, 0, 0], [0, 1, dy]]), (W, H))
            a = np.maximum(a, Li * u)
        a *= out_k
        if a.max() <= 0:
            return base
        m = self.mask(spec['mask_dir'], s)
        shadow = 0.0
        if m is not None:
            mo = np.clip(cv2.warpAffine(m, M[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), 0, 1)
            a *= (1 - mo)
            sh = cv2.GaussianBlur(cv2.warpAffine(mo, np.float32([[1, 0, 9], [0, 1, 4]]), (W, H)), (0, 0), 7)
            shadow = (0.55 * sh)[..., None]
        col = (np.array(CREAM, np.float32) / 255)[None, None, :] * self.mh_shade * (1 - shadow)
        return base * (1 - a[..., None]) + col * a[..., None]

    # ---------------------------------------------------------- pass-by
    def _build_pass(self):
        src = self.spec['pass_clip']
        self.pass_figs = []
        for i in self.spec['pass_frames']:
            rgb = self.frame(src, i)
            p = os.path.join(MASK_DIR, f'{src}_{i:03d}.png')
            a = cv2.imread(p, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
            self.pass_figs.append(np.dstack([rgb * a[..., None], a]))       # premultiplied

    def pass_layer(self, k, n=8):
        """Blurred figure crossing the lens right->left. Returns premultiplied RGBA and its centre x."""
        fig = self.pass_figs[k % len(self.pass_figs)]
        travel = W + 1400
        acc = np.zeros((H, W, 4), np.float32)
        subs = 5
        for j in range(subs):
            t = (k + (j + 0.5) / subs) / n
            cx = W + 700 - travel * t
            sc = OUT_S * 3.0
            px, py = 390, 520
            M = np.float32([[sc, 0, cx - sc * px], [0, sc, H * 0.46 - sc * py]])
            acc += cv2.warpAffine(fig, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        acc /= subs
        acc = cv2.GaussianBlur(acc, (0, 0), 11)
        cx_mid = W + 700 - travel * (k + 0.5) / n
        return acc, cx_mid

    # ---------------------------------------------------------- labels
    def label_layer(self, kind, a, b):
        key = (kind, a, b)
        if key in self._labels:
            return self._labels[key]
        if kind == 'small':
            num = typo.text_layer(a, 'sans_med', 25, CREAM, tracking=6, shadow=0.55, shadow_blur=7)
            ttl = typo.text_layer(b, 'sans_med', 25, CREAM, tracking=11, shadow=0.55, shadow_blur=7)
            lay = (num, ttl)
        else:
            ttl = typo.text_layer(a, 'sans_med', 27, CREAM, tracking=8, shadow=0.6, shadow_blur=9)
            sub = typo.text_layer(b, 'garamond_it', 41, CREAM, shadow=0.6, shadow_blur=9)
            lay = (ttl, sub)
        self._labels[key] = lay
        return lay

    def draw_label(self, frame, seg, f):
        lab = seg.get('label')
        if not lab:
            return frame
        kind = lab[0]
        if kind == 'small':
            t_in, t_out = lab[3], lab[4]
        else:
            t_in = lab[3] if len(lab) > 3 else seg['f0'] + 3
            t_out = lab[4] if len(lab) > 4 else seg['f1'] - 1
        if f < t_in or f > t_out + 4:
            return frame
        k_out = 1 - smooth((f - t_out) / 4.0)
        (L1, (w1, h1), p1), (L2, (w2, h2), p2) = self.label_layer(kind, lab[1], lab[2])
        x0 = 72
        if kind == 'small':
            u = ease_out((f - t_in) / 6.0) * k_out
            y = 318
            if self.spec.get('small_label', {}).get('align') == 'right':
                x0 = W - 72 - (w1 + 18 + 46 + 18 + w2)
            dx = (1 - ease_out((f - t_in) / 6.0)) * -14
            typo.composite(frame, L1, x0 + dx - p1, y - p1, u)
            lx = x0 + w1 + 18
            line = int(46 * ease_out((f - t_in - 1) / 6.0))
            if line > 1:
                frame[y + 15:y + 17, int(lx + dx):int(lx + dx + line)] = (
                    frame[y + 15:y + 17, int(lx + dx):int(lx + dx + line)] * (1 - 0.9 * u)
                    + np.array(CREAM, np.float32) / 255 * 0.9 * u)
            typo.composite(frame, L2, lx + 46 + 18 + dx - p2, y - p2, ease_out((f - t_in - 2) / 6.0) * k_out)
            return frame
        y = 1128
        line = int(40 * ease_out((f - t_in) / 5.0) * k_out)
        if line > 1:
            frame[y + 16:y + 18, x0:x0 + line] = frame[y + 16:y + 18, x0:x0 + line] * 0.1 + np.array(CREAM, np.float32) / 255 * 0.9
        u1 = ease_out((f - t_in - 2) / 6.0) * k_out
        u2 = ease_out((f - t_in - 4) / 6.0) * k_out
        typo.composite(frame, L1, x0 + 56 - p1, y + (1 - u1) * 12 - p1, u1)
        typo.composite(frame, L2, x0 - p2, y + 44 + (1 - u2) * 12 - p2, u2 * 0.95)
        return frame


# ------------------------------------------------------------------ frame render
def warp(img, M, blur=0.0, pivot_out=None, K=6):
    flags = cv2.INTER_LANCZOS4
    if blur <= 0:
        return cv2.warpAffine(img, M[:2], (W, H), flags=flags, borderMode=cv2.BORDER_REPLICATE)
    acc = np.zeros((H, W, img.shape[2]), np.float32)
    for j in range(K):
        s = 1 + blur * j / (K - 1)
        Mj = S(s, pivot_out) @ M
        acc += cv2.warpAffine(img, Mj[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return acc / K


def chroma_split(f, amt):
    if amt <= 0.0005:
        return f
    out = f.copy()
    for c, s in ((0, 1 + amt), (2, 1 - amt)):
        M = S(s, (W / 2, H / 2))
        out[..., c] = cv2.warpAffine(f[..., c], M[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W * 0.66)) ** 2 + ((_yy - H * 0.48) / (H * 0.62)) ** 2)
VIGNETTE = (1 - 0.16 * np.clip(_r, 0, 1.7) ** 2.4).clip(0.6, 1).astype(np.float32)[..., None]
del _yy, _xx, _r


def find_seg(part, f):
    for seg in part.segs:
        if seg['f0'] <= f < seg['f1']:
            return seg
    return None


def render(part, f):
    el = part.spec.get('endlogo')
    if el and el[0] <= f < el[1]:
        img = part.end_logo(f)
        return look.look(img, halation=0.10, bloom=0.03), None
    seg = find_seg(part, f)
    if seg is None:
        return np.zeros((H, W, 3), np.float32), None
    k = f - seg['f0']
    n = seg['f1'] - seg['f0']
    s = seg['s0'] + k * seg.get('speed', 1.0)
    src = seg['src']
    img = part.frame(src, s)

    M = part.align.get(src, np.eye(3))
    if 'zoom' in seg:
        z0, z1 = seg['zoom']
        z = z0 + (z1 - z0) * smooth(k / max(n - 1, 1))
        M = S(z, part.pivots[seg.get('pivot', 'upper')]) @ M
    blur, pivot_o = 0.0, None
    ca = 0.0
    if seg.get('dive') and k >= n - 4:
        j = k - (n - 4)
        p = part.pivots[seg['dive']]
        M = S(DIVE_SCALE[j], p) @ M
        blur, pivot_o = DIVE_BLUR[j], (p[0] * OUT_S, p[1] * OUT_S)
        ca = 0.05 * DIVE_BLUR[j]
    if seg.get('land') and k < 4:
        M = S(LAND_SCALE[k], (NW / 2, NH / 2)) @ M
        blur, pivot_o = LAND_BLUR[k], (W / 2, H / 2)
        ca = 0.05 * LAND_BLUR[k]
    Mo = OUT @ M
    base = warp(img, Mo, blur, pivot_o)
    base = np.clip(base + 0.35 * (base - cv2.GaussianBlur(base, (0, 0), 1.1)), 0, 1)

    if seg.get('masthead'):
        base = part.masthead(f, base, seg, s, Mo)

    # pass-by wipes
    for key, newside_is_seg in (('passin', True), ('passout', False)):
        if key in seg:
            a0, a1 = seg[key]
            if a0 <= f < a1:
                kk = f - a0
                lay, cx = part.pass_layer(kk, a1 - a0)
                x = np.arange(W, dtype=np.float32)
                right = np.clip((x - cx) / 240 + 0.5, 0, 1)[None, :, None]   # area the figure has passed
                if newside_is_seg:
                    base = base * right
                else:
                    base = base * (1 - right)
                base = base * (1 - lay[..., 3:4]) + lay[..., :3]
            elif key == 'passout' and f >= a1:
                base = np.zeros_like(base)

    if seg.get('strobe') and k < 4:
        base = base + (1 - base) * STROBE[k] * np.array([1.0, 0.99, 0.97], np.float32)
    base = chroma_split(base, ca)
    base = look.look(base, halation=0.10, bloom=0.03)
    base = base * VIGNETTE
    base = part.draw_label(base, seg, f)
    return base, seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', default='noir')
    ap.add_argument('--out', required=True)
    ap.add_argument('--audio')
    ap.add_argument('--stills')
    ap.add_argument('--crf', default='15')
    a = ap.parse_args()
    part = Part(P.PARTS[a.part])
    if a.stills:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        for st in a.stills.split(','):
            fr = int(st)
            img, _ = render(part, fr)
            img = look.grain(img, fr, amp=0.014)
            cv2.imwrite(a.out.replace('.mp4', f'_f{fr:04d}.jpg'), cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
        return
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-']
    if a.audio:
        cmd += ['-i', a.audio, '-shortest']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-pix_fmt', 'yuv420p', '-profile:v', 'high',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart']
    if a.audio:
        cmd += ['-c:a', 'aac', '-b:a', '320k', '-ar', '48000']
    cmd += [a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in range(part.end):
        img, _ = render(part, fr)
        img = look.grain(img, fr, amp=0.014)
        proc.stdin.write((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        if fr % 48 == 0:
            print(f'frame {fr}/{part.end}', flush=True)
    proc.stdin.close()
    proc.wait()
    print('wrote', a.out)


if __name__ == '__main__':
    main()
