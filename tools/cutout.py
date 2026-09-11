#!/usr/bin/env python3
"""Turn product photos on a plain backdrop into transparent, trimmed PNGs.

    python3 tools/cutout.py --outdir assets/products \
        white=shot-white.jpg black=shot-black.jpg brown=shot-brown.jpg

All inputs are cropped to ONE shared bounding box, so every colourway keeps the
same scale and position. That matters: the reels stack these images directly,
and a per-image crop would make the product jump as the reel spins.

Matting works from a heavily smoothed difference-from-backdrop field rather
than a raw colour threshold. A pale colourway can have edge pixels as close to
the backdrop as the backdrop itself, so filling inward from the border leaks
into the garment; the smoothed field stays elevated inside the product even
where local colour matches, and flat near zero on true backdrop.
"""
import subprocess, sys, re, os
import numpy as np
from scipy import ndimage


def probe(path):
    """Dimensions via ffmpeg's own banner - the static build ships no ffprobe."""
    err = subprocess.run(['ffmpeg', '-hide_banner', '-i', path],
                         capture_output=True, text=True).stderr
    m = re.search(r'Stream #.*Video:.*?,\s*(\d+)x(\d+)', err)
    if not m:
        raise SystemExit(f'could not read dimensions of {path}')
    return int(m.group(1)), int(m.group(2))


def read_rgb(path, w, h):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-frames:v', '1',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True).stdout
    if len(raw) != w * h * 3:
        raise SystemExit(f'{path}: decoded {len(raw)} bytes, expected {w*h*3}')
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32)


def write_rgba(path, rgba):
    h, w, _ = rgba.shape
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo',
                          '-pix_fmt', 'rgba', '-s', f'{w}x{h}', '-i', '-',
                          '-frames:v', '1', path], stdin=subprocess.PIPE)
    p.communicate(np.clip(rgba, 0, 255).astype(np.uint8).tobytes())
    if p.returncode:
        raise SystemExit(f'ffmpeg failed writing {path}')


def otsu(x):
    """Threshold that best separates backdrop from product, contrast-agnostic."""
    hist, edges = np.histogram(x, bins=256)
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist).astype(np.float64)
    w1 = w0[-1] - w0
    s = np.cumsum(hist * centers)
    with np.errstate(invalid='ignore', divide='ignore'):
        m0 = s / w0
        m1 = (s[-1] - s) / w1
        between = w0 * w1 * (m0 - m1) ** 2
    return centers[int(np.nanargmax(between))]


def matte(src, tol_lo=10.0, tol_hi=34.0, feather=1.4):
    w, h = probe(src)
    im = read_rgb(src, w, h)

    # backdrop colour from a border ring; median so a stray pixel can't skew it
    ring = np.concatenate([im[:8].reshape(-1, 3), im[-8:].reshape(-1, 3),
                           im[:, :8].reshape(-1, 3), im[:, -8:].reshape(-1, 3)])
    bg = np.median(ring, axis=0)

    dist = np.linalg.norm(im - bg, axis=2)
    smooth = ndimage.gaussian_filter(dist, max(3.0, 0.006 * max(w, h)))

    coarse = smooth > max(tol_lo * 0.5, otsu(smooth))
    # Close notches thinner than a real armhole. A low-contrast colourway can
    # read as backdrop along a shaded edge, carving a gash that reaches the
    # silhouette boundary - fill_holes cannot catch that, closing can.
    k = max(9, int(round(0.025 * max(w, h))) | 1)
    coarse = ndimage.binary_closing(coarse, np.ones((k, k)))
    coarse = ndimage.binary_fill_holes(coarse)

    # keep the product alone, dropping the drop-shadow blob and any specks
    lbl, n = ndimage.label(coarse)
    if n == 0:
        raise SystemExit(f'{src}: nothing found above the backdrop')
    sizes = ndimage.sum(coarse, lbl, range(1, n + 1))
    coarse = lbl == (int(np.argmax(sizes)) + 1)

    # solid interior, soft ramp only in a thin band at the silhouette edge
    band = max(2, int(round(0.004 * max(w, h))))
    inner = ndimage.binary_erosion(coarse, np.ones((3, 3)), iterations=band)
    outer = ndimage.binary_dilation(coarse, np.ones((3, 3)), iterations=band)

    ramp = np.clip((dist - tol_lo) / (tol_hi - tol_lo), 0, 1)
    alpha = np.where(inner, 1.0, np.where(outer, ramp, 0.0))
    alpha = ndimage.gaussian_filter(alpha, feather)
    alpha = np.where(inner, 1.0, alpha)      # feather must not eat the interior
    alpha = np.where(outer, alpha, 0.0)      # nor revive the drop shadow

    # despill: unmix the backdrop out of edge pixels so no halo survives
    a3 = np.clip(alpha, 1e-3, 1)[..., None]
    rgb = np.where(inner[..., None], im, np.clip(bg + (im - bg) / a3, 0, 255))
    return rgb, alpha, bg


def main():
    args = sys.argv[1:]
    outdir = 'assets/products'
    if '--outdir' in args:
        i = args.index('--outdir'); outdir = args[i + 1]; del args[i:i + 2]
    pad = 0.04
    if '--pad' in args:
        i = args.index('--pad'); pad = float(args[i + 1]); del args[i:i + 2]
    jobs = [a.split('=', 1) for a in args if '=' in a]
    if not jobs:
        raise SystemExit(__doc__)

    mattes, boxes = {}, []
    for name, src in jobs:
        rgb, alpha, bg = matte(src)
        ys, xs = np.where(alpha > 0.06)
        if not len(ys):
            raise SystemExit(f'{src}: empty matte')
        boxes.append((ys.min(), ys.max(), xs.min(), xs.max()))
        mattes[name] = (rgb, alpha)
        print(f'  {name:<8} {src}  backdrop rgb({bg[0]:.0f},{bg[1]:.0f},{bg[2]:.0f})'
              f'  bbox {xs.max()-xs.min()+1}x{ys.max()-ys.min()+1}')

    # one shared crop so every colourway keeps identical scale and position
    y0 = min(b[0] for b in boxes); y1 = max(b[1] for b in boxes)
    x0 = min(b[2] for b in boxes); x1 = max(b[3] for b in boxes)
    m = int(round(pad * max(y1 - y0, x1 - x0)))
    H, W = next(iter(mattes.values()))[1].shape
    y0, y1 = max(0, y0 - m), min(H, y1 + 1 + m)
    x0, x1 = max(0, x0 - m), min(W, x1 + 1 + m)

    for name, (rgb, alpha) in mattes.items():
        dst = f'{outdir}/{name}.png'
        write_rgba(dst, np.dstack([rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1] * 255]))
    marker = os.path.join(outdir, '.STANDIN')
    if os.path.exists(marker):
        os.remove(marker)
    print(f'\n  shared crop {x1-x0}x{y1-y0} -> {outdir}/  ({len(mattes)} files)')


if __name__ == '__main__':
    main()
