#!/usr/bin/env python3
"""Cut the model shots into die-cut stickers, all on one shared crop.

    python3 tools/prep.py <selfie_multiclass.tflite>

Every look is cropped to the same box, from just under the lips to a little
below the belt, so the tank top sits on the same pixels in every frame and a
stop-motion swap never jumps. The box is wide enough for the widest coat.

Matting: mediapipe's person mask is soft (it is computed at 256x256), so it is
snapped to the real garment edges with a colour guided filter. Pale and camel
pieces sit close to the taupe backdrop in colour, which is why a plain
backdrop key is not enough here.
"""
import glob, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets', 'source')
OUT = os.path.join(ROOT, 'build', 'stickers')

CROP_TOP, CROP_BOTTOM = 410, 1290     # just under the lips -> a little below the belt
BORDER = 24                            # white die-cut margin, source px
CLOSE = 34                             # bridges notches narrower than ~2*CLOSE
PAD = BORDER + 40                      # room for the border and the shadow


def box(x, r):
    return ndimage.uniform_filter(x, size=2 * r + 1, mode='reflect')


def guided_filter(I, p, r=8, eps=1e-3):
    """He et al. colour guided filter: snaps a soft mask onto image edges."""
    mI = np.stack([box(I[..., c], r) for c in range(3)], -1)
    mp_ = box(p, r)
    cov = np.stack([box(I[..., c] * p, r) for c in range(3)], -1) - mI * mp_[..., None]
    S = np.empty(I.shape[:2] + (3, 3), np.float64)
    for i in range(3):
        for j in range(i, 3):
            v = box(I[..., i] * I[..., j], r) - mI[..., i] * mI[..., j]
            S[..., i, j] = S[..., j, i] = v
    S += eps * np.eye(3)
    a = np.linalg.solve(S.reshape(-1, 3, 3), cov.reshape(-1, 3, 1)).reshape(cov.shape)
    b = mp_ - (a * mI).sum(-1)
    ma = np.stack([box(a[..., c], r) for c in range(3)], -1)
    return (ma * I).sum(-1) + box(b, r)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def fit_backdrop(im, alpha):
    """Quadratic backdrop surface from pixels the mask calls background."""
    h, w, _ = im.shape
    yy, xx = np.mgrid[0:h, 0:w]
    xn, yn = xx / w - .5, yy / h - .5
    sel = alpha < 0.02
    sel[::3, ::3] &= True
    basis = lambda X, Y: np.stack([np.ones_like(X), X, Y, X * X, X * Y, Y * Y], -1)
    A = basis(xn[sel], yn[sel])
    full = basis(xn, yn).reshape(-1, 6)
    out = np.empty_like(im)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, im[..., c][sel], rcond=None)
        out[..., c] = (full @ coef).reshape(h, w)
    return out


def matte(seg, path):
    im8 = np.array(Image.open(path).convert('RGB'))
    res = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=im8))
    person = 1.0 - np.squeeze(res.confidence_masks[0].numpy_view()).astype(np.float64)
    im = im8.astype(np.float64) / 255
    # work on a band around the crop only - it is all the reel ever shows
    y0, y1 = CROP_TOP - 60, CROP_BOTTOM + 60
    I, p = im[y0:y1], person[y0:y1]
    q = guided_filter(I, p, r=8, eps=6e-4)
    a = smoothstep(0.28, 0.72, q)
    # drop specks, keep the figure
    lbl, n = ndimage.label(a > 0.5)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(a), lbl, range(1, n + 1))
        keep = lbl == (int(np.argmax(sizes)) + 1)
        keep = ndimage.binary_dilation(keep, iterations=3)
        a = np.where(keep, a, 0)
    # pull the edge in a hair so no taupe fringe survives against the white
    hard = a > 0.5
    inner = ndimage.binary_erosion(hard, iterations=1)
    a = np.where(inner, 1.0, np.where(hard, a * 0.85, a * 0.35))
    a = np.clip(ndimage.gaussian_filter(a, 0.6), 0, 1)
    full_a = np.zeros_like(person)
    full_a[y0:y1] = a
    # despill: unmix the backdrop out of edge pixels
    bg = fit_backdrop(im, full_a)
    a3 = np.clip(full_a, 1e-3, 1)[..., None]
    edge = (full_a > 0.02) & (full_a < 0.98)
    rgb = np.where(edge[..., None], np.clip(bg + (im - bg) / a3, 0, 1), im)
    return rgb, full_a


def sticker(rgb, alpha, x0, x1):
    """Photo on a white die-cut backing with a rounded, AA'd outline."""
    ph = rgb[CROP_TOP:CROP_BOTTOM, x0:x1]
    pa = alpha[CROP_TOP:CROP_BOTTOM, x0:x1]
    H, W = pa.shape
    Hc, Wc = H + 2 * PAD, W + 2 * PAD
    photo = np.zeros((Hc, Wc, 3)); pal = np.zeros((Hc, Wc))
    photo[PAD:PAD + H, PAD:PAD + W] = ph
    pal[PAD:PAD + H, PAD:PAD + W] = pa

    shape = pal > 0.5
    shape = ndimage.distance_transform_edt(~shape) <= BORDER          # die-cut margin
    shape = ndimage.distance_transform_edt(~shape) <= CLOSE           # close notches...
    shape = ndimage.distance_transform_edt(shape) > CLOSE             # ...back to size
    shape = ndimage.binary_fill_holes(shape)
    # a touch of smoothing so the cut line reads as one confident curve
    sm = ndimage.gaussian_filter(shape.astype(np.float64), 2.5) > 0.5
    sd = ndimage.distance_transform_edt(sm) - ndimage.distance_transform_edt(~sm)
    backing = np.clip(sd + 0.5, 0, 1)

    paper = np.array([253, 252, 249]) / 255.0
    # faint diagonal sheen so the vinyl reads as a physical object
    yy, xx = np.mgrid[0:Hc, 0:Wc]
    sheen = 1.0 + 0.018 * np.cos((xx / Wc * 0.8 + yy / Hc) * np.pi)
    paper_rgb = np.clip(paper[None, None, :] * sheen[..., None], 0, 1)

    out_rgb = paper_rgb * (1 - pal[..., None]) + photo * pal[..., None]
    out_a = np.maximum(backing, pal)
    rgba = np.dstack([out_rgb, out_a])
    return (np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    model = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    opts = vision.ImageSegmenterOptions(
        base_options=mpt.BaseOptions(model_asset_path=model),
        output_confidence_masks=True, output_category_mask=False)
    seg = vision.ImageSegmenter.create_from_options(opts)

    paths = sorted(glob.glob(os.path.join(SRC, 'model-*.jpg')))
    mattes = {}
    xs = []
    for p in paths:
        rgb, a = matte(seg, p)
        name = os.path.basename(p)[:-4]
        mattes[name] = (rgb, a)
        cols = np.where((a[CROP_TOP:CROP_BOTTOM] > 0.5).any(0))[0]
        xs.append((cols.min(), cols.max()))
        print(f'  {name:28s} figure x {cols.min()}..{cols.max()}')

    # one shared crop, centred on the figure axis, wide enough for the widest look
    cx = 558
    half = max(max(cx - a, b - cx) for a, b in xs) + 6
    x0, x1 = cx - half, cx + half
    meta = {'crop': [int(x0), CROP_TOP, int(x1), CROP_BOTTOM], 'pad': PAD, 'border': BORDER}
    for name, (rgb, a) in mattes.items():
        rgba = sticker(rgb, a, x0, x1)
        Image.fromarray(rgba, 'RGBA').save(os.path.join(OUT, f'{name}.png'), optimize=True)
        meta[name] = {'size': [rgba.shape[1], rgba.shape[0]]}
    with open(os.path.join(OUT, 'meta.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    print('crop', meta['crop'], 'sticker', rgba.shape[1], 'x', rgba.shape[0])
    seg.close()


if __name__ == '__main__':
    main()
