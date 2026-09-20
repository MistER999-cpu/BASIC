#!/usr/bin/env python3
"""Matte the lower-body garments and record how wide each waistband is.

    python3 tools/bottoms.py assets/incoming/bottoms --outdir assets/bottoms

Two things differ from tools/cutout.py, which mattes the tank colourways.

No shared crop. That tool crops every input to one box so a colourway cannot
shift as a reel spins; these are eight different garments sourced from eight
different places, so a shared box would only preserve the arbitrary scale of
whichever photo was framed widest. Each garment is trimmed to its own box and
the scene scales it by the waistband measurement written into the manifest, so
a pair of shorts stays short next to a wide-leg trouser.

A closing kernel of 0.8% of the frame rather than 2.5%. At the tank's 2.5% the
kernel is wide enough to bridge the gap between two trouser legs at the crotch;
binary_fill_holes then floods the gap and the garment ships with an opaque
wedge of backdrop between its legs. Narrowing the kernel leaves the gap open to
the frame edge, so it is never a hole to fill in the first place.

Carving flooded regions back out afterwards looks like the obvious fix and is
not: a garment whose print contains backdrop-coloured pixels loses them. The
daisy skirt here mattes into lace, because its scalloped hem connects the white
of the print to the white outside it.
"""
import os, sys, json
import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import probe, read_rgb, write_rgba, fit_backdrop, otsu

EXT = ('.jpg', '.jpeg', '.png', '.webp', '.avif', '.bmp', '.tif', '.tiff')


def matte_bottom(src, tol_lo=10.0, tol_hi=34.0, feather=1.2):
    w, h = probe(src)
    im = read_rgb(src, w, h)
    bg = fit_backdrop(im)
    dist = np.linalg.norm(im - bg, axis=2)
    sigma = max(2.0, 0.004 * max(w, h))
    smooth = ndimage.gaussian_filter(dist, sigma)

    th = max(tol_lo * 0.5, otsu(smooth))
    coarse = smooth > th
    k = max(5, int(round(0.008 * max(w, h))) | 1)
    coarse = ndimage.binary_closing(coarse, np.ones((k, k)))

    filled = ndimage.binary_fill_holes(coarse)
    lbl, n = ndimage.label(filled)
    if n == 0:
        raise SystemExit(f'{src}: nothing found above the backdrop')
    sizes = ndimage.sum(filled, lbl, range(1, n + 1))
    filled = lbl == (int(np.argmax(sizes)) + 1)

    coarse = ndimage.binary_erosion(filled, np.ones((3, 3)),
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
    return rgb, alpha


def waistband(alpha, lo=0.01, hi=0.05):
    """Median garment width across the band just below the top edge.

    Every bottom has a waist and they are all roughly the same width on a
    body, so this is the one measurement that puts a mini skirt, a pair of
    jorts and a wide-leg trouser at their true relative sizes. Measuring the
    widest point instead would shrink a wide-leg trouser to match a pair of
    leggings; measuring height would stretch the jorts to trouser length.

    The band is the top 1-5% and not the top 3-11%, because a belt or a
    pleated front cinches narrower than the waistband above it. The cream
    trouser here dips to 96px at 8% of its height against 178px at its top
    edge, and measuring through that dip made it read as half again as long
    per waist as every other garment in the set.
    """
    solid = alpha > 0.5
    ys, _ = np.nonzero(solid)
    y0, y1 = ys.min(), ys.max()
    H = y1 - y0
    widths = []
    for y in range(int(y0 + lo * H), max(int(y0 + hi * H), int(y0 + lo * H) + 1)):
        on = np.nonzero(solid[y])[0]
        if len(on):
            widths.append(on.max() - on.min() + 1)
    return float(np.median(widths)) if widths else float('nan')


def main():
    args = sys.argv[1:]
    outdir = 'assets/bottoms'
    if '--outdir' in args:
        i = args.index('--outdir'); outdir = args[i + 1]; del args[i:i + 2]
    if not args:
        raise SystemExit(__doc__)
    src = args[0]
    files = [os.path.join(src, f) for f in sorted(os.listdir(src))
             if f.lower().endswith(EXT) and not f.startswith('.')]
    if not files:
        raise SystemExit(f'{src}: no images')

    os.makedirs(outdir, exist_ok=True)
    manifest = []
    for f in files:
        rgb, alpha = matte_bottom(f)
        ys, xs = np.nonzero(alpha > 0.06)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        rgb, alpha = rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]
        waist = waistband(alpha)

        slug = os.path.splitext(os.path.basename(f))[0]
        slug = ''.join(c if c.isalnum() else '-' for c in slug.lower())
        slug = '-'.join(p for p in slug.split('-') if p)[:40].rstrip('-')
        dst = os.path.join(outdir, slug + '.png')
        write_rgba(dst, np.dstack([rgb, alpha * 255]))

        H, W = alpha.shape
        manifest.append({'src': os.path.basename(f), 'file': dst,
                         'w': int(W), 'h': int(H), 'waist': round(waist, 1),
                         'lengthPerWaist': round(H / waist, 3)})
        print(f'  {slug[:38]:38} {W:4}x{H:<4}  waist {waist:6.1f}px'
              f'  length/waist {H/waist:5.2f}')

    with open(os.path.join(outdir, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=2)
    print(f'\n  {len(manifest)} garments -> {outdir}/')


if __name__ == '__main__':
    main()
