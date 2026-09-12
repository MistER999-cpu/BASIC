#!/usr/bin/env python3
"""
Normalize the studio background across a set of fashion frames.

The background is separated from the subject by iterative sigma-clipping
against a fitted surface, so a frame whose backdrop carries a strong gradient
(or whose subject is close to the backdrop in tone) still segments correctly.
A smooth correction field derived from a master frame is then applied to the
whole frame, carrying the subject into the master's light rather than
compositing it against a new background.

Usage:
    python3 normalize_bg.py OUT_DIR master.png other1.png other2.png ...
    python3 normalize_bg.py --bg-only OUT_DIR master.png other1.png ...
    python3 normalize_bg.py --replace OUT_DIR master.png other1.png ...

--bg-only holds the subject at its original values and corrects only the
backdrop. Use it when the subject carries product colour that must not move.
"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage

DEG = 3
SUB = 4           # subsample stride for the least-squares fit


def basis(X, Y, deg=DEG):
    t = [np.ones_like(X)]
    for i in range(1, deg + 1):
        for j in range(0, i + 1):
            t.append((X ** (i - j)) * (Y ** j))
    return np.stack([q.ravel() for q in t], 1)


def _grid(h, w):
    yy, xx = np.mgrid[0:h, 0:w]
    return xx / w - 0.5, yy / h - 0.5


def fit_surface(img, bgmask):
    """Least-squares polynomial surface through the background pixels."""
    h, w, _ = img.shape
    X, Y = _grid(h, w)
    B = basis(X, Y)
    sel = np.zeros((h, w), bool)
    sel[::SUB, ::SUB] = True
    sel &= bgmask
    if sel.sum() < 200:                      # too few samples, use everything
        sel = bgmask.copy()
    rows = B[sel.ravel()]
    out = np.zeros_like(img, dtype=np.float64)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(rows, img[:, :, c][sel], rcond=None)
        out[:, :, c] = (B @ coef).reshape(h, w)
    return out


def subject_mask(img, iters=6):
    """
    True where the subject is.

    Iteratively fits a surface to the current background estimate and clips
    away pixels that sit too far from it. Because the surface models the
    backdrop's own gradient, this works on frames where a fixed threshold
    around the border tone would break apart.
    """
    h, w, _ = img.shape
    bg = np.ones((h, w), bool)
    for _ in range(iters):
        surf = fit_surface(img, bg)
        resid = np.abs(img - surf).sum(2)
        rb = resid[bg]
        med = np.median(rb)
        mad = np.median(np.abs(rb - med)) * 1.4826
        thr = med + max(3.0 * mad, 6.0)
        new = resid < thr
        if new.sum() < 0.04 * h * w:         # clipped too hard, keep previous
            break
        if (new == bg).all():
            break
        bg = new

    # a real backdrop touches the frame edge; interior look-alike regions
    # (pale trousers, skin) must not count as background
    lab, _ = ndimage.label(bg)
    edge = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
    edge.discard(0)
    if edge:
        bg = np.isin(lab, list(edge))

    subj = ~bg
    subj = ndimage.binary_closing(subj, np.ones((5, 5)))
    subj = ndimage.binary_fill_holes(subj)
    subj = ndimage.binary_dilation(subj, np.ones((9, 9)))
    return subj


def stats(surf):
    h, w, _ = surf.shape
    L = surf.mean(2)
    corners = [L[20, 20], L[20, -20], L[-20, 20], L[-20, -20]]
    centre = L[h // 2, w // 2]
    hexs = '#%02X%02X%02X' % tuple(int(round(t)) for t in surf[h // 2, w // 2])
    return hexs, L.min(), L.max(), (1 - np.mean(corners) / centre) * 100


def report(name, surf):
    hexs, lo, hi, fall = stats(surf)
    print("  %-26s centre %s  lum %6.1f-%6.1f  spread %5.1f  falloff %+.2f%%"
          % (name[:26], hexs, lo, hi, hi - lo, fall))


def main():
    args = sys.argv[1:]
    replace = False
    bg_only = False
    while args and args[0].startswith('--'):
        if args[0] == '--replace':
            replace = True
        elif args[0] == '--bg-only':
            bg_only = True
        else:
            print("unknown flag %s" % args[0]); sys.exit(2)
        args = args[1:]
    out_dir, paths = args[0], args[1:]
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(11)

    imgs, masks, surfs = [], [], []
    print("ANALYSING")
    for p in paths:
        a = np.asarray(Image.open(p).convert('RGB')).astype(np.float64)
        sm = subject_mask(a)
        frac = sm.mean() * 100
        if frac > 60:
            print("  !! %s subject mask covers %.1f%% of frame - segmentation "
                  "failed, refusing to correct this frame"
                  % (os.path.basename(p), frac))
            sys.exit(1)
        sf = fit_surface(a, ~sm)
        imgs.append(a); masks.append(sm); surfs.append(sf)
        print("  %-40s subject %5.1f%%" % (os.path.basename(p)[:40], frac))
        report(os.path.basename(p), sf)

    target = surfs[0]
    th, tw, _ = target.shape
    print("\nMASTER: %s" % os.path.basename(paths[0]))

    print("\nCORRECTING")
    for p, a, sm, sf in zip(paths, imgs, masks, surfs):
        h, w, _ = a.shape
        tgt = target
        if (h, w) != (th, tw):
            tgt = np.asarray(Image.fromarray(target.round().clip(0, 255).astype(np.uint8))
                             .resize((w, h), Image.LANCZOS)).astype(np.float64)
        C = tgt / np.maximum(sf, 1e-6)
        if not (0.4 < np.median(C) < 2.5):
            print("  !! %s correction field out of range (median %.3f) - aborting"
                  % (os.path.basename(p), np.median(C)))
            sys.exit(1)
        C = np.clip(C, 0.4, 2.5)
        if bg_only:
            # hold the subject at its original values and correct only the
            # backdrop, so garment colour is not altered by the match
            f = ndimage.gaussian_filter(sm.astype(np.float64), 2.0)[:, :, None]
            C = C * (1.0 - f) + f
        out = a * C
        if replace:
            grain = rng.normal(0, 2.8, (h, w, 1))
            bgpix = tgt + grain
            feather = ndimage.gaussian_filter(sm.astype(np.float64), 1.5)[:, :, None]
            out = out * feather + bgpix * (1 - feather)
        d = rng.random((h, w, 3)) - rng.random((h, w, 3))
        clipped = ((out > 254.5) | (out < 0.5)).mean() * 100
        out = np.clip(out + d, 0, 255).round().astype(np.uint8)
        name = os.path.splitext(os.path.basename(p))[0] + '_norm.png'
        Image.fromarray(out).save(os.path.join(out_dir, name))
        warn = '  ** %.2f%% of pixels clipping' % clipped if clipped > 0.5 else ''
        print("  %-40s -> %-34s median correction %+.2f%%%s"
              % (os.path.basename(p)[:40], name[:34], (np.median(C) - 1) * 100, warn))

    print("\nVERIFY")
    finals = []
    for p in paths:
        name = os.path.splitext(os.path.basename(p))[0] + '_norm.png'
        a = np.asarray(Image.open(os.path.join(out_dir, name)).convert('RGB')).astype(np.float64)
        sf = fit_surface(a, ~subject_mask(a))
        finals.append(sf)
        report(name, sf)

    S = np.stack(finals)
    spread = (S.max(0) - S.min(0))
    print("\n  background agreement across the set: mean %.2f levels, "
          "95th pct %.2f, worst %.2f" % (spread.mean(), np.percentile(spread, 95), spread.max()))


if __name__ == '__main__':
    main()
