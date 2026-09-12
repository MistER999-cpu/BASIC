#!/usr/bin/env python3
"""
Build a soft alpha matte of the model for each shot of the base reel.

The backdrop is a seamless cyclorama whose wall-to-floor sweep curves across
the frame. Neither a 2D polynomial nor a row-wise median can follow that curve:
a polynomial cannot bend fast enough, and a row median is wrong wherever one
row spans both wall and floor. Both report the entire floor as subject.

So the backdrop is estimated by a masked large-radius blur - a Gaussian-weighted
average over the pixels currently believed to be backdrop. That follows any
smooth shape, curve included, while ignoring whatever is currently classed as
subject, and it is re-estimated on each iteration.

Holes are filled only up to a size limit. The gap between an arm and the torso
in an akimbo pose is a genuine hole the garment strip must show through; only
small specks (pale fabric reading as backdrop) get filled.
"""
import numpy as np
from scipy import ndimage

MAX_HOLE_FRAC = 0.0008          # holes larger than this fraction stay open
BG_SIGMA = 20.0                 # radius of the backdrop estimate; 80 bled the
                                # cyc curve into the matte and reported the
                                # whole floor as subject


def smooth_background(img, bgmask, sigma=None):
    """Gaussian-weighted average over the pixels currently classed as backdrop."""
    if sigma is None:
        sigma = BG_SIGMA          # read at call time so callers can tune it
    m = bgmask.astype(np.float64)
    den = np.maximum(ndimage.gaussian_filter(m, sigma), 1e-6)
    out = np.empty_like(img)
    for c in range(3):
        out[:, :, c] = ndimage.gaussian_filter(img[:, :, c] * m, sigma) / den
    return out


def model_matte(img, iters=5, feather=1.2, soft=(12.0, 40.0)):
    """Returns (alpha, core): a soft 0-1 matte of the model."""
    h, w, _ = img.shape
    bg = np.ones((h, w), bool)
    for _ in range(iters):
        surf = smooth_background(img, bg)
        resid = np.abs(img - surf).sum(2)
        rb = resid[bg]
        med = np.median(rb)
        mad = np.median(np.abs(rb - med)) * 1.4826
        new = resid < med + max(3.0 * mad, 8.0)
        if new.sum() < 0.25 * h * w or (new == bg).all():
            break
        bg = new

    surf = smooth_background(img, bg)
    resid = np.abs(img - surf).sum(2)

    # the backdrop is the part connected to the frame edge
    lab, _ = ndimage.label(bg)
    edge = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
    edge.discard(0)
    bg_connected = np.isin(lab, list(edge)) if edge else bg

    core = ~bg_connected
    core = ndimage.binary_closing(core, np.ones((5, 5)))

    # fill only SMALL enclosed holes; keep akimbo gaps open
    holes = ndimage.binary_fill_holes(core) & ~core
    hlab, hn = ndimage.label(holes)
    if hn:
        sizes = ndimage.sum(holes, hlab, range(1, hn + 1))
        small = np.isin(hlab, [i + 1 for i, s in enumerate(sizes)
                               if s < MAX_HOLE_FRAC * h * w])
        core = core | small

    core = ndimage.binary_opening(core, np.ones((3, 3)))
    lab2, n = ndimage.label(core)
    if n > 1:
        sizes = ndimage.sum(core, lab2, range(1, n + 1))
        core = lab2 == (int(np.argmax(sizes)) + 1)

    lo, hi = soft
    alpha = np.clip((resid - lo) / (hi - lo), 0, 1)
    alpha = np.where(ndimage.binary_erosion(core, np.ones((5, 5))), 1.0, alpha)
    alpha = np.where(ndimage.binary_dilation(core, np.ones((7, 7))), alpha, 0.0)
    return ndimage.gaussian_filter(alpha, feather).astype(np.float32), core
