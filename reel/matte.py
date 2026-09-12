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
SUBJECT_MARGIN = 25          # clearance kept around the subject when
                             # estimating the backdrop; see model_matte
BACKDROP_SPREAD = 0.06       # channel-ratio spread below which a pixel is
BACKDROP_GAIN = 0.08         # backdrop lit differently, not an object
COARSE_SIGMA = 220.0         # wide fallback radius for the backdrop estimate
SUPPORT_FULL = 0.25          # support at which the tight estimate is trusted alone
BG_SIGMA = 20.0                 # radius of the backdrop estimate; 80 bled the
                                # cyc curve into the matte and reported the
                                # whole floor as subject


def guided_filter(guide, p, r=8, eps=1e-4):
    """
    Edge-aware refinement of a coarse matte (He, Sun & Tang).

    Snaps the alpha onto edges that actually exist in the picture. Necessary
    because a residual threshold cannot resolve this footage: skin and pale
    fabric sit only 6-40 above a backdrop whose own noise is 6 +/- 5.5, so the
    boundary ends up carried by the binary core and inherits its blocky
    morphology - and lands up to 12px off the true silhouette.
    """
    mean_I = ndimage.uniform_filter(guide, r)
    mean_p = ndimage.uniform_filter(p, r)
    corr_I = ndimage.uniform_filter(guide * guide, r)
    corr_Ip = ndimage.uniform_filter(guide * p, r)
    var_I = corr_I - mean_I * mean_I
    cov_Ip = corr_Ip - mean_I * mean_p
    a = cov_Ip / (var_I + eps)
    b = mean_p - a * mean_I
    return ndimage.uniform_filter(a, r) * guide + ndimage.uniform_filter(b, r)


def smooth_background(img, bgmask, sigma=None, with_support=False):
    """Gaussian-weighted average over the pixels currently classed as backdrop."""
    if sigma is None:
        sigma = BG_SIGMA          # read at call time so callers can tune it
    m = bgmask.astype(np.float64)
    support = ndimage.gaussian_filter(m, sigma)
    den = np.maximum(support, 1e-6)
    out = np.empty_like(img)
    for c in range(3):
        out[:, :, c] = ndimage.gaussian_filter(img[:, :, c] * m, sigma) / den
    return (out, support) if with_support else out


def two_scale_background(img, bgmask, fine=None, coarse=None):
    """
    Backdrop estimate that stays valid everywhere in the frame.

    A single tight radius is accurate beside the subject but collapses deep
    inside it, where there is no backdrop left to average - and a collapsed
    estimate corrupts both the residual and the channel ratios exactly where
    pale garments need judging. So the tight estimate is blended towards a wide
    one as its support falls away: local accuracy at the silhouette, a defined
    value everywhere else.
    """
    fine = BG_SIGMA if fine is None else fine
    coarse = COARSE_SIGMA if coarse is None else coarse
    near, support = smooth_background(img, bgmask, sigma=fine, with_support=True)
    far = smooth_background(img, bgmask, sigma=coarse)
    wgt = np.clip(support / SUPPORT_FULL, 0.0, 1.0)[:, :, None]
    return near * wgt + far * (1.0 - wgt)


def model_matte(img, iters=6, feather=0.0, soft=(25.0, 150.0)):
    """
    Returns (alpha, core): a soft 0-1 matte of the model.

    The alpha is taken straight from the residual ramp and is never eroded,
    dilated, opened or closed. Morphology with square kernels stamps 5-10px
    stair-steps along the silhouette, and since the garment strip is clipped by
    (1 - alpha) those steps show up as a ragged edge on the garment passing
    behind her. Binary work is confined to deciding which regions are subject at
    all; the boundary itself is left as the source rendered it.

    Thresholds are measured, not guessed: on this footage the backdrop residual
    runs 6.0 +/- 5.5, solid subject reaches ~416, and the anti-aliased edge
    spans 4-6px. A ramp of 20..140 lands the transition across that edge instead
    of saturating inside it.
    """
    h, w, _ = img.shape

    def estimate(mask, first=False):
        # Keep a margin clear of the subject. Without it the subject's own edge
        # and anti-aliased pixels bleed into the estimate: beside dark trousers
        # the backdrop estimate read 180 where the picture was 216, which
        # inflated the residual and pushed the silhouette ~14px wide with blocky
        # edges. With the margin the estimate is flat (208 across the whole row)
        # and the edge lands within 2px of the truth.
        if first:
            return two_scale_background(img, mask)
        safe = ~ndimage.binary_dilation(~mask, np.ones((SUBJECT_MARGIN, SUBJECT_MARGIN)))
        if safe.sum() < 0.10 * h * w:
            safe = mask
        return two_scale_background(img, safe)

    bg = np.ones((h, w), bool)
    for i in range(iters):
        surf = estimate(bg, first=(i == 0))
        resid = np.abs(img - surf).sum(2)
        rb = resid[bg]
        med = np.median(rb)
        mad = np.median(np.abs(rb - med)) * 1.4826
        new = resid < med + max(3.0 * mad, 8.0)
        if new.sum() < 0.25 * h * w or (new == bg).all():
            break
        bg = new

    surf = estimate(bg)
    resid = np.abs(img - surf).sum(2)

    # Reject backdrop that is merely lit slightly differently. A pixel whose
    # three channels are all scaled by nearly the same mild factor is the
    # backdrop under a soft luminance modulation - a wall shadow or a lighting
    # ripple - not an object, and the strip must pass in front of it. Without
    # this, shot 5's wall shadow (ratios 0.95-1.07, spread 0.01-0.04, residual
    # 20-35 against a threshold of 21) is swallowed into the silhouette.
    #
    # The margins are set against the real garments, which all clear them:
    # black reads ratio 0.19, beige spread 0.19, the cream turtleneck mean 1.11.
    # The test is only meaningful where the estimate has real backdrop to
    # average. Deep inside the figure the masked blur has no support and its
    # ratios are meaningless - applied there, it punched a hole through the
    # pale cream trousers and hands of shot 6. Gating on support density keeps
    # the test at the periphery, where a wall shadow lives, and away from the
    # interior, where it can only do damage.
    ratio = img / np.maximum(surf, 1.0)
    spread = ratio.max(2) - ratio.min(2)
    backdrop_like = ((spread < BACKDROP_SPREAD)
                     & (np.abs(ratio.mean(2) - 1) < BACKDROP_GAIN))
    bg = bg | backdrop_like
    resid = np.where(backdrop_like, 0.0, resid)

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

    # Solid inside: fill any interior softness (pale fabric reading close to the
    # backdrop) without touching the boundary. The erosion is deep enough that
    # it cannot reach the silhouette edge.
    interior = ndimage.binary_erosion(core, np.ones((9, 9)))
    alpha = np.maximum(alpha, interior.astype(np.float64))

    # Clear specks in the backdrop. The dilation is wide, so the multiply lands
    # far outside the real edge and never clips the soft ramp.
    keep = ndimage.binary_dilation(core, np.ones((15, 15)))
    alpha = alpha * keep

    # A short guided-filter pass snaps the boundary onto real picture edges.
    # The radius is small on purpose: with an uncontaminated residual the matte
    # is already within a couple of pixels, so this only has to tidy the ramp.
    # A wide radius here smeared the edge over 8px instead of sharpening it.
    guide = img.mean(2) / 255.0
    alpha = np.clip(guided_filter(guide, alpha, r=3, eps=1e-4), 0, 1)
    alpha = np.where(alpha < 0.04, 0.0, alpha)
    alpha = np.where(alpha > 0.96, 1.0, alpha)

    if feather:
        alpha = ndimage.gaussian_filter(alpha, feather)
    return alpha.astype(np.float32), core
