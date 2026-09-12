#!/usr/bin/env python3
"""
Normalize the studio background across a set of fashion frames.

Stage 1  build a subject mask per image (flood-fill from the borders through
         the plain background, then tighten and feather)
Stage 2  fit a smooth polynomial surface to the background-only pixels
Stage 3  pick a master image; compute a smooth correction field
         C = master_surface / source_surface  and apply it to the whole frame
         (low-frequency, so the subject shifts imperceptibly and consistently
         rather than being hard-swapped against a new background)
Stage 4  optionally hard-replace the background outside the feathered mask
         with the master surface plus matched grain, killing residual mottling

Usage:
    python3 normalize_bg.py out_dir master.png other1.png other2.png ...
    python3 normalize_bg.py --replace out_dir master.png other1.png ...
"""
import sys, os
import numpy as np
from PIL import Image, ImageFilter

DEG = 3

def basis(X, Y, deg=DEG):
    t = [np.ones_like(X)]
    for i in range(1, deg + 1):
        for j in range(0, i + 1):
            t.append((X ** (i - j)) * (Y ** j))
    return np.stack([q.ravel() for q in t], 1)

def subject_mask(img):
    """True where the subject is. Flood-fill the plain background in from the borders."""
    h, w, _ = img.shape
    L = img.mean(2)
    border = np.concatenate([L[0], L[-1], L[:, 0], L[:, -1]])
    bg_lvl = np.median(border)
    # background = close to the border level, in luminance AND not strongly coloured
    sat = img.max(2) - img.min(2)
    flat = (np.abs(L - bg_lvl) < 14) & (sat < 22)
    # flood fill from the border through `flat` so interior look-alike patches
    # (pale trousers, skin) are not mistaken for background
    from collections import deque
    reach = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if flat[y, x]: reach[y, x] = True; dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if flat[y, x]: reach[y, x] = True; dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and flat[ny, nx] and not reach[ny, nx]:
                reach[ny, nx] = True; dq.append((ny, nx))
    subj = ~reach
    # close small holes, then dilate a little so edge pixels and hair count as subject
    m = Image.fromarray((subj * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(5))
    m = m.filter(ImageFilter.MaxFilter(9))
    return np.asarray(m) > 127

def fit_surface(img, bgmask):
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w]
    X = xx / w - 0.5; Y = yy / h - 0.5
    L = img.mean(2)
    use = bgmask & (np.abs(L - np.median(L[bgmask])) < 10)
    A = basis(X, Y)[use.ravel()]
    full = basis(X, Y)
    out = np.zeros_like(img, dtype=np.float64)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, img[:, :, c][use], rcond=None)
        out[:, :, c] = (full @ coef).reshape(h, w)
    return out

def report(name, surf):
    h, w, _ = surf.shape
    L = surf.mean(2)
    def hx(v): return '#%02X%02X%02X' % tuple(int(round(t)) for t in v)
    corners = [L[20,20], L[20,-20], L[-20,20], L[-20,-20]]
    print("  %-28s centre %s  lum %.1f-%.1f  spread %.1f  falloff %.2f%%" % (
        name, hx(surf[h//2, w//2]), L.min(), L.max(), L.max()-L.min(),
        (1 - np.mean(corners) / L[h//2, w//2]) * 100))

def main():
    args = sys.argv[1:]
    replace = False
    if args and args[0] == '--replace':
        replace = True; args = args[1:]
    out_dir, paths = args[0], args[1:]
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(11)

    imgs, masks, surfs = [], [], []
    print("ANALYSING")
    for p in paths:
        a = np.asarray(Image.open(p).convert('RGB')).astype(np.float64)
        sm = subject_mask(a)
        sf = fit_surface(a, ~sm)
        imgs.append(a); masks.append(sm); surfs.append(sf)
        print("  %s  subject %.1f%% of frame" % (os.path.basename(p), sm.mean()*100))
        report(os.path.basename(p), sf)

    # every image is resampled onto the master's surface geometry
    target = surfs[0]
    th, tw, _ = target.shape
    print("\nMASTER: %s" % os.path.basename(paths[0]))

    print("\nCORRECTING")
    for p, a, sm, sf in zip(paths, imgs, masks, surfs):
        h, w, _ = a.shape
        tgt = target
        if (h, w) != (th, tw):
            tgt = np.asarray(Image.fromarray(target.round().clip(0,255).astype(np.uint8))
                             .resize((w, h), Image.LANCZOS)).astype(np.float64)
        C = tgt / np.maximum(sf, 1e-6)          # smooth, close to 1.0
        outi = a * C
        if replace:
            grain = rng.normal(0, 2.8, (h, w, 1))
            bg = tgt + grain
            feather = np.asarray(Image.fromarray((sm*255).astype(np.uint8))
                                 .filter(ImageFilter.GaussianBlur(1.5))).astype(np.float64)/255.
            feather = feather[:, :, None]
            outi = outi * feather + bg * (1 - feather)
        d = rng.random((h, w, 3)) - rng.random((h, w, 3))
        outi = np.clip(outi + d, 0, 255).round().astype(np.uint8)
        name = os.path.splitext(os.path.basename(p))[0] + '_norm.png'
        Image.fromarray(outi).save(os.path.join(out_dir, name))
        shift = (C.mean() - 1) * 100
        print("  %-30s -> %s   mean correction %+.2f%%" % (os.path.basename(p), name, shift))

    print("\nVERIFY")
    for p in paths:
        name = os.path.splitext(os.path.basename(p))[0] + '_norm.png'
        a = np.asarray(Image.open(os.path.join(out_dir, name)).convert('RGB')).astype(np.float64)
        sm = subject_mask(a)
        report(name, fit_surface(a, ~sm))

if __name__ == '__main__':
    main()
