#!/usr/bin/env python3
"""
Build a soft alpha matte of the model for each shot of the base reel.

This uses a trained segmentation model (ISNet, via rembg) rather than keying
against the backdrop.

The earlier approach estimated the backdrop and classified pixels by how far
they sat from it. On this footage that could not be made to hold. The backdrop
is a warm greige cyclorama, and the garments include cream, ivory and sand; a
pale tank sits only a few levels off the wall, while the wall itself carries a
36-level gradient and soft cast shadows. Every threshold that admitted the
shadows punched holes in the pale fabric, and every threshold that protected
the fabric swallowed the shadows. Worse, the scheme fed back on itself:
excluding a region removed the evidence it was backdrop, so the estimate drifted
and excluded more.

A segmentation model has no such trouble because it recognises a person rather
than measuring a colour distance. On the nine shots it gets every case right
first time - pale garments solid, wall shadows rejected, and the gap between an
akimbo arm and the torso left open so the garment strip shows through it.

The model's edge is then refined with a guided filter so the alpha follows the
picture's own edges, and left otherwise untouched: no erosion, dilation, opening
or closing. Morphology with square kernels stamps 5-10px stair-steps along the
silhouette, and since the strip is clipped by (1 - alpha) those steps show up as
a ragged edge on the garment passing behind her.

The model weights (~179MB) download on first use to ~/.rembg and are not in the
repository.
"""
import numpy as np
from scipy import ndimage

MODEL = 'isnet-general-use'
GUIDE_RADIUS = 3
GUIDE_EPS = 1e-4

_session = None


def _get_session():
    global _session
    if _session is None:
        from rembg import new_session
        _session = new_session(MODEL)
    return _session


def guided_filter(guide, p, r=GUIDE_RADIUS, eps=GUIDE_EPS):
    """Edge-aware refinement of a matte (He, Sun & Tang)."""
    mean_I = ndimage.uniform_filter(guide, r)
    mean_p = ndimage.uniform_filter(p, r)
    var_I = ndimage.uniform_filter(guide * guide, r) - mean_I * mean_I
    cov_Ip = ndimage.uniform_filter(guide * p, r) - mean_I * mean_p
    a = cov_Ip / (var_I + eps)
    b = mean_p - a * mean_I
    return ndimage.uniform_filter(a, r) * guide + ndimage.uniform_filter(b, r)


def model_matte(img, refine=True):
    """
    Returns (alpha, core) for a HxWx3 float array.

    alpha is a soft 0-1 matte of the person; core is its solid interior, kept
    for the callers that report coverage.
    """
    from PIL import Image
    from rembg import remove

    rgb = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    raw = remove(rgb, session=_get_session(),
                 only_mask=True, post_process_mask=False)
    alpha = np.asarray(raw).astype(np.float64) / 255.0

    if refine:
        guide = img.mean(2) / 255.0
        alpha = np.clip(guided_filter(guide, alpha), 0.0, 1.0)
        alpha = np.where(alpha < 0.04, 0.0, alpha)
        alpha = np.where(alpha > 0.96, 1.0, alpha)

    return alpha.astype(np.float32), alpha > 0.5


def smooth_background(img, bgmask, sigma=60.0):
    """
    Gaussian-weighted average over the pixels marked as backdrop.

    Still used by the compositor's per-shot exposure match, which only needs a
    smooth low-frequency field.
    """
    m = bgmask.astype(np.float64)
    den = np.maximum(ndimage.gaussian_filter(m, sigma), 1e-6)
    out = np.empty_like(img)
    for c in range(3):
        out[:, :, c] = ndimage.gaussian_filter(img[:, :, c] * m, sigma) / den
    return out
