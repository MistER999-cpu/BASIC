#!/usr/bin/env python3
"""Paint the white side stripes off the trainers in a shot.

    python3 survet/destripe.py survet/shots/brown/brown-end.jpg [more ...]
    python3 survet/destripe.py survet/shots/black/black-floor-sit.jpg:0.4:40

Writes survet/retouch/<name>, which the renderer uses in place of the shot;
the original is left alone. Only the trainer area is touched: the band at the
bottom of the model, found the same way the renderer finds her (saturated or
dark against the grey backdrop). Inside it, light low-saturation pixels with
shoe on both sides of them (the stripes, but not the floor beside the shoe)
are filled from the surrounding shoe colour.
"""
import sys, os
import numpy as np
from scipy import ndimage as ndi
from PIL import Image

def subject_mask(rgb):
    r, g, b = [rgb[..., i].astype(float) for i in range(3)]
    mx, mn = rgb.max(-1).astype(float), rgb.min(-1).astype(float)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    return ((sat > 0.16) & (lum < 240)) | (lum < 105), lum, sat

def destripe(path, out, band_frac=0.16, d=14):
    im = np.array(Image.open(path).convert('RGB'))
    h, w, _ = im.shape
    subj, lum, sat = subject_mask(im)
    rows = np.where(subj[:, int(w * .15):int(w * .85)].sum(1) > w * 0.01)[0]
    y1 = rows.max()
    y0 = rows.min()
    top = int(y1 - band_frac * (y1 - y0))
    band = slice(top, min(h, y1 + 12))
    shoe = subj[band]
    light = (lum[band] > 135) & (sat[band] < 0.28)
    # a stripe pixel has shoe on both sides of it along some direction within
    # a stripe's width; floor beside the shoe has shoe on one side only
    def shift(mask, dy, dx):
        out = np.zeros_like(mask)
        H, W = mask.shape
        out[max(dy, 0):H + min(dy, 0), max(dx, 0):W + min(dx, 0)] = \
            mask[max(-dy, 0):H + min(-dy, 0), max(-dx, 0):W + min(-dx, 0)]
        return out
    def reach(mask, dy, dx):
        out = np.zeros_like(mask)
        for k in range(1, d + 1):
            out |= shift(mask, k * dy, k * dx)
        return out
    # the stripes run up the side of the shoe at an angle, so they are crossed
    # horizontally or diagonally; a vertical pair would bridge the floor
    # between a trouser hem and the shoe below it
    enclosed = np.zeros_like(shoe)
    for dy, dx in ((0, 1), (1, 1), (1, -1)):
        enclosed |= reach(shoe, dy, dx) & reach(shoe, -dy, -dx)
    k = ndi.generate_binary_structure(2, 1)
    closed = enclosed | shoe
    stripe = light & enclosed & ~shoe
    # drop tiny specks; stripes are elongated runs
    lab, n = ndi.label(stripe)
    sizes = ndi.sum(stripe, lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.where(sizes >= 25)[0])
    stripe = ndi.binary_dilation(keep, structure=k, iterations=2) & closed
    # fill from the nearest shoe pixel, then soften inside the fill
    src = shoe & ~stripe
    _, (iy, ix) = ndi.distance_transform_edt(~src, return_indices=True)
    reg = im[band].astype(float)
    filled = reg[iy, ix]
    soft = np.stack([ndi.gaussian_filter(filled[..., c], 3) for c in range(3)], -1)
    alpha = ndi.gaussian_filter(stripe.astype(float), 1.2)[..., None]
    reg = reg * (1 - alpha) + soft * alpha
    res = im.copy()
    res[band] = np.clip(reg, 0, 255).astype(np.uint8)
    Image.fromarray(res).save(out, quality=95)
    return int(stripe.sum()), (top, y1)

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    # path[:band[:reach]] - band is the share of her height to search up from
    # her feet (bigger when the shoes are in the foreground), reach the widest
    # stripe in pixels
    for arg in sys.argv[1:]:
        p, *opts = arg.split(':')
        band_frac = float(opts[0]) if opts else 0.16
        d = int(opts[1]) if len(opts) > 1 else 14
        out = os.path.join(here, 'retouch', os.path.basename(p))
        n, band = destripe(p, out, band_frac, d)
        print(f'{os.path.basename(p)}: {n} px retouched in rows {band} -> {os.path.relpath(out)}')
