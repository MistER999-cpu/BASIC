#!/usr/bin/env python3
"""Matte the tank colourways, reject their cast shadow, pin them to one silhouette.

    python3 tools/tops.py assets/incoming --outdir assets/tops

Two problems that did not matter for the slot reveal and do matter here.

The cast shadow. tools/cutout.py drops the shadow as a separate blob, which
works while the shadow is detached; where it runs along the garment's own edge
it is continuous with it and survives, and the pale colourways ship with an
80px strip of backdrop grey down their right side at full opacity - 3.7% of
the white tank, 3.5% of the beige. Reels in motion hid it. A slot that changes
colour and nothing else does not.

Shadow is the backdrop scaled down, so it is separated here by projection
rather than by distance: s = <im,bg>/<bg,bg> is how bright a pixel is relative
to the backdrop, and the residual im - s*bg is how far its colour is from the
backdrop's regardless of brightness. Shadow has a small residual and s below 1.
A neutral garment also has a small residual, which is why s is bounded below:
the black tank projects to s=0.19 and the brown to 0.29, far under any soft
studio shadow, while the beige survives on residual alone (37 against a
tolerance of 10) because it is warm and the backdrop is cool.

The silhouette drift. The colourways were generated rather than photographed
four times: pairwise IoU runs 0.94-0.99, with the pairs clustering at 0.988
(brown/black) and 0.977 (white/beige) but only 0.94 across that divide. The
four alphas are intersected, then eroded clear of every colourway's despilled
edge band - taking the RGB from one matte and the alpha from another would
otherwise composite the unmixed edge colour at an opacity it was never solved
for, which is a second way to put backdrop grey on the garment.
"""
import os, sys, json
import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import probe, read_rgb, write_rgba, fit_backdrop, otsu

EXT = ('.jpg', '.jpeg', '.png', '.webp', '.avif', '.bmp', '.tif', '.tiff')
ORDER = ['white', 'beige', 'brown', 'black']   # lightest garment to darkest

SHADOW_RESIDUAL = 10.0    # colour distance from the backdrop's own hue
SHADOW_S_LO = 0.45        # darker than this is a dark garment, not a shadow
SHADOW_S_HI = 0.94        # brighter than this is backdrop, already excluded


def shadow_mask(im, bg):
    num = (im * bg).sum(axis=2)
    den = (bg * bg).sum(axis=2)
    s = num / np.maximum(den, 1e-6)
    resid = np.linalg.norm(im - s[..., None] * bg, axis=2)
    return (resid < SHADOW_RESIDUAL) & (s > SHADOW_S_LO) & (s < SHADOW_S_HI), s


def matte_top(src, tol_lo=10.0, tol_hi=34.0, feather=1.4):
    w, h = probe(src)
    im = read_rgb(src, w, h)
    bg = fit_backdrop(im)
    dist = np.linalg.norm(im - bg, axis=2)
    sigma = max(3.0, 0.006 * max(w, h))
    smooth = ndimage.gaussian_filter(dist, sigma)

    shade, _ = shadow_mask(im, bg)
    # the test is per-pixel and noisy one pixel at a time; open it so fabric
    # texture that happens to project like shadow does not perforate the garment
    shade = ndimage.binary_opening(shade, np.ones((5, 5)))

    coarse = smooth > max(tol_lo * 0.5, otsu(smooth))
    k = max(9, int(round(0.025 * max(w, h))) | 1)
    coarse = ndimage.binary_closing(coarse, np.ones((k, k)))
    coarse = ndimage.binary_fill_holes(coarse)
    coarse &= ~shade

    lbl, n = ndimage.label(coarse)
    if n == 0:
        raise SystemExit(f'{src}: nothing found above the backdrop')
    sizes = ndimage.sum(coarse, lbl, range(1, n + 1))
    coarse = lbl == (int(np.argmax(sizes)) + 1)
    coarse = ndimage.binary_fill_holes(coarse)
    coarse = ndimage.binary_erosion(coarse, np.ones((3, 3)),
                                    iterations=int(round(sigma)))

    band = max(2, int(round(0.0015 * max(w, h))))
    inner = ndimage.binary_erosion(coarse, np.ones((3, 3)), iterations=band)
    outer = ndimage.binary_dilation(coarse, np.ones((3, 3)), iterations=band)
    ramp = np.clip((dist - tol_lo) / (tol_hi - tol_lo), 0, 1)
    alpha = np.where(inner, 1.0, np.where(outer, ramp, 0.0))
    alpha = ndimage.gaussian_filter(alpha, feather)
    alpha = np.where(inner, 1.0, alpha)
    alpha = np.where(outer, alpha, 0.0)

    a3 = np.clip(alpha, 1e-3, 1)[..., None]
    rgb = np.where(inner[..., None], im, np.clip(bg + (im - bg) / a3, 0, 255))
    return rgb, alpha, inner, shade.sum() / max(coarse.sum(), 1)


def align(shots, pad=24):
    """Put every colourway on one canvas, centred on its own garment.

    The four shots are not even the same size - one is 2048x2068 against
    2048x2048 for the rest - and the garment does not sit identically within
    each frame. Intersecting the alphas of misaligned shots would carve the
    silhouette down to wherever they happen to overlap. Centring each
    garment's own bounding box preserves scale, which is what has to survive,
    and discards position, which carries nothing here.
    """
    boxes = []
    for s in shots:
        ys, xs = np.nonzero(s['alpha'] > 0.5)
        boxes.append((ys.min(), ys.max(), xs.min(), xs.max()))
    halfH = max(max(cy - y0, y1 - cy) for (y0, y1, _, _), cy
                in zip(boxes, [(b[0] + b[1]) / 2 for b in boxes]))
    halfW = max(max(cx - x0, x1 - cx) for (_, _, x0, x1), cx
                in zip(boxes, [(b[2] + b[3]) / 2 for b in boxes]))
    H = int(2 * halfH) + 2 * pad
    W = int(2 * halfW) + 2 * pad

    for s, (y0, y1, x0, x1) in zip(shots, boxes):
        cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
        for key, fill in (('rgb', 0.0), ('alpha', 0.0), ('inner', False)):
            src = s[key]
            dst = np.zeros((H, W) + src.shape[2:], dtype=src.dtype)
            dst[...] = fill
            sy0, sx0 = cy - H // 2, cx - W // 2
            ty0, tx0 = max(0, -sy0), max(0, -sx0)
            sy0, sx0 = max(0, sy0), max(0, sx0)
            hh = min(H - ty0, src.shape[0] - sy0)
            ww = min(W - tx0, src.shape[1] - sx0)
            dst[ty0:ty0 + hh, tx0:tx0 + ww] = src[sy0:sy0 + hh, sx0:sx0 + ww]
            s[key] = dst


def main():
    args = sys.argv[1:]
    outdir = 'assets/tops'
    if '--outdir' in args:
        i = args.index('--outdir'); outdir = args[i + 1]; del args[i:i + 2]
    src = args[0] if args else 'assets/incoming'
    files = [os.path.join(src, f) for f in sorted(os.listdir(src))
             if f.lower().endswith(EXT) and not f.startswith('.')]
    if len(files) != len(ORDER):
        raise SystemExit(f'expected {len(ORDER)} colourway photos in {src}, found {len(files)}')

    shots = []
    for f in files:
        rgb, alpha, inner, shadeFrac = matte_top(f)
        lum = (rgb[inner] @ [0.2126, 0.7152, 0.0722]).mean() if inner.any() else 0
        shots.append({'src': f, 'rgb': rgb, 'alpha': alpha, 'inner': inner,
                      'lum': float(lum), 'shade': float(shadeFrac)})

    # filenames carry nothing; the garment's own brightness orders them
    shots.sort(key=lambda s: -s['lum'])
    for name, s in zip(ORDER, shots):
        s['name'] = name
        print(f'  {name:6} {os.path.basename(s["src"])[:42]:42}'
              f'  luma {s["lum"]:5.1f}  shadow rejected {100*s["shade"]:4.1f}%')

    align(shots)

    shared = np.ones(shots[0]['alpha'].shape, bool)
    for s in shots:
        shared &= s['alpha'] > 0.5
    lbl, n = ndimage.label(shared)
    sizes = ndimage.sum(shared, lbl, range(1, n + 1))
    shared = lbl == (int(np.argmax(sizes)) + 1)

    # stand the shared boundary clear of every colourway's despilled edge band,
    # so the alpha we apply only ever lands on untouched garment RGB
    clear = np.ones_like(shared)
    for s in shots:
        clear &= s['inner']
    shared &= clear
    shared = ndimage.binary_opening(shared, np.ones((5, 5)))

    inner = ndimage.binary_erosion(shared, np.ones((3, 3)), iterations=2)
    alpha = ndimage.gaussian_filter(np.where(shared, 1.0, 0.0), 1.1)
    alpha = np.where(inner, 1.0, alpha)
    alpha = np.where(ndimage.binary_dilation(shared, np.ones((3, 3)), iterations=2),
                     alpha, 0.0)

    ys, xs = np.nonzero(alpha > 0.06)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1

    os.makedirs(outdir, exist_ok=True)
    manifest = []
    for s in shots:
        own = s['alpha'] > 0.5
        lost = 100 * (1 - shared.sum() / own.sum())
        write_rgba(os.path.join(outdir, s['name'] + '.png'),
                   np.dstack([s['rgb'][y0:y1, x0:x1], alpha[y0:y1, x0:x1] * 255]))
        manifest.append({'name': s['name'], 'src': os.path.basename(s['src']),
                         'file': f'{outdir}/{s["name"]}.png',
                         'w': int(x1 - x0), 'h': int(y1 - y0),
                         'areaLostPct': round(float(lost), 2)})
        print(f'  {s["name"]:6} gives up {lost:4.1f}% of its own mask to the shared silhouette')

    with open(os.path.join(outdir, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=2)
    print(f'\n  shared silhouette {x1-x0}x{y1-y0} -> {outdir}/')


if __name__ == '__main__':
    main()
