"""Mattes for the tracksuit ad: models on green or grey, ghost outfits on grey.

Every key here works from a *clean plate* - an estimate of what the backdrop
looks like behind each pixel - rather than from one global backdrop colour.
The generated studios are not evenly lit (vignetted green, a grey sweep that
falls off toward the floor, soft floor shadows), and judging every pixel
against a single colour either eats hair or keeps a halo.

The clean plate is built by normalised convolution: average only the pixels we
are confident are backdrop, so it follows gradients and floor shadows, and
interpolates smoothly across the subject.
"""
import numpy as np
from scipy import ndimage


def clean_plate(img, bg_mask, sigma):
    """Smooth estimate of the backdrop everywhere, from confident-backdrop pixels."""
    m = bg_mask.astype(np.float32)
    den = ndimage.gaussian_filter(m, sigma)
    out = np.empty_like(img)
    for c in range(3):
        num = ndimage.gaussian_filter(img[..., c] * m, sigma)
        out[..., c] = num / np.maximum(den, 1e-6)
    # far inside a large subject the small kernel sees no backdrop at all;
    # fall back to a much wider estimate there
    weak = den < 0.02
    if weak.any():
        den2 = ndimage.gaussian_filter(m, sigma * 6)
        for c in range(3):
            num2 = ndimage.gaussian_filter(img[..., c] * m, sigma * 6)
            out[..., c] = np.where(weak, num2 / np.maximum(den2, 1e-6), out[..., c])
    return out


def keep_main_subject(alpha, grow=6):
    """Drop specks: keep the largest solid blob, plus the soft fringe around it."""
    solid = alpha > 0.5
    lbl, n = ndimage.label(solid)
    if n == 0:
        return alpha
    sizes = ndimage.sum(solid, lbl, range(1, n + 1))
    main = lbl == (int(np.argmax(sizes)) + 1)
    main = ndimage.binary_dilation(main, iterations=grow)
    return alpha * main


def fill_small_holes(alpha, max_area):
    """Fill pinholes inside the subject, but never a real gap (arm/torso, legs)."""
    solid = alpha > 0.5
    holes = ndimage.binary_fill_holes(solid) & ~solid
    lbl, n = ndimage.label(holes)
    if n:
        sizes = ndimage.sum(holes, lbl, range(1, n + 1))
        small = np.isin(lbl, 1 + np.where(sizes <= max_area)[0])
        alpha = np.where(small, 1.0, alpha)
    return alpha


def unmix(img, plate, alpha, floor=0.06):
    """Remove the backdrop's contribution from edge pixels (kills halos)."""
    a = np.clip(alpha, floor, 1.0)[..., None]
    return np.clip(plate + (img - plate) / a, 0, 255)


def key_green(img):
    """Chroma key for the generated green-screen models."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    gdom = g - np.maximum(r, b)
    ratio = gdom / np.maximum(g, 1.0)
    confident_bg = (ratio > 0.38) & (g > 35)
    confident_bg = ndimage.binary_erosion(confident_bg, iterations=3)
    plate = clean_plate(img, confident_bg, sigma=18)
    pr, pg, pb = plate[..., 0], plate[..., 1], plate[..., 2]
    gdom_bg = np.maximum(pg - np.maximum(pr, pb), 8.0)
    alpha = 1.0 - np.clip(gdom / gdom_bg, 0, 1)
    alpha = np.clip((alpha - 0.06) / 0.88, 0, 1)
    alpha = keep_main_subject(alpha)
    alpha = fill_small_holes(alpha, max_area=400)
    alpha = ndimage.gaussian_filter(alpha, 0.6)
    rgb = unmix(img, plate, alpha)
    # spill: nothing in these subjects is legitimately green-dominant
    rr, gg, bb = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    rgb[..., 1] = np.minimum(gg, np.maximum(rr, bb) + 4)
    return rgb, alpha


def fit_quadratic_backdrop(img, mask):
    """Least-squares 1,x,y,x^2,xy,y^2 surface per channel over masked pixels."""
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w]
    xn, yn = xx / w - 0.5, yy / h - 0.5
    basis = lambda X, Y: np.stack([np.ones_like(X), X, Y, X * X, X * Y, Y * Y], -1)
    A = basis(xn[mask], yn[mask])
    full = basis(xn, yn).reshape(-1, 6)
    out = np.empty_like(img)
    for c in range(3):
        v = img[..., c][mask]
        coef, *_ = np.linalg.lstsq(A, v, rcond=None)
        res = v - A @ coef
        keep = np.abs(res) < 2.5 * res.std() + 1e-6
        coef, *_ = np.linalg.lstsq(A[keep], v[keep], rcond=None)
        out[..., c] = (full @ coef).reshape(h, w)
    return out


def shoe_hulls(shoe_px, feet_y, min_area=400):
    """Convex outline of each shoe below feet_y, from its unambiguous pixels.

    White leather in shade is the same grey as the sweep, so no per-pixel test
    can tell them apart. But every sneaker here has a warm gum sole and suede
    overlay plus some brightly lit leather, and a sneaker seen from the side is
    close to convex - so the hull of those sure pixels recovers the shaded
    leather without reaching into the floor.
    """
    from scipy.spatial import ConvexHull
    from PIL import Image, ImageDraw
    h, w = shoe_px.shape
    zone = np.zeros_like(shoe_px)
    zone[feet_y:] = shoe_px[feet_y:]
    zone = ndimage.binary_closing(zone, iterations=4)
    lbl, n = ndimage.label(zone)
    hull_mask = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(hull_mask)
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        if len(ys) < min_area:
            continue
        pts = np.stack([xs, ys], 1)
        hull = ConvexHull(pts)
        draw.polygon([tuple(p) for p in pts[hull.vertices]], fill=255)
    return ndimage.binary_erosion(np.asarray(hull_mask) > 0, iterations=1)


def key_grey(img, lo=10.0, hi=42.0, feet_y=None):
    """Difference key for subjects on a neutral grey sweep.

    The sweep is neutral-to-cool everywhere, including its darker floor wedge,
    so "neutral, mid-luminance, not warm" identifies backdrop far more reliably
    than distance from a fitted surface (which the floor wedge breaks). Warmth
    is in turn a strong subject cue: skin, the headscarf, the gum soles and the
    beige suede toe overlay are all warmer than the sweep, even where their
    luminance matches it.
    """
    h, w = img.shape[:2]
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    lum = img.mean(2)
    chroma = img.max(2) - img.min(2)
    warmth = r - b
    # the sweep never gets brighter than its fitted surface, but white sneaker
    # leather does - so cap "backdrop" just above the surface, and allow well
    # below it for the floor wedge
    ring = np.zeros((h, w), bool)
    ring[:40] = ring[-40:] = True
    ring[:, :40] = ring[:, -40:] = True
    surf_lum = fit_quadratic_backdrop(img, ring).mean(2)
    confident_bg = ((chroma < 14) & (warmth < 4) & (lum > surf_lum - 70)
                    & (lum < surf_lum + 8))
    confident_bg = ndimage.binary_opening(confident_bg, iterations=2)
    confident_bg = ndimage.binary_erosion(confident_bg, iterations=3)
    plate = clean_plate(img, confident_bg, sigma=22)
    dist = np.linalg.norm(img - plate, axis=2)
    alpha = np.clip((dist - lo) / (hi - lo), 0, 1)
    alpha = np.maximum(alpha, np.clip((warmth - 5.0) / 8.0, 0, 1))
    if feet_y is not None:
        yy = np.arange(h)[:, None]
        sure_shoe = (alpha > 0.2) & ((warmth > 8) | (lum > surf_lum + 12))
        hulls = shoe_hulls(sure_shoe, feet_y)
        # a raised heel tilts the sole into a curve, and the hull bridges that
        # curve over a sliver of floor. The gum sole is the bottom of the shoe
        # in every column, so nothing below the lowest warm pixel is shoe.
        sole = hulls & (warmth > 8)
        has_sole = sole.any(0)
        lowest = np.where(has_sole, h - 1 - np.argmax(sole[::-1], 0), h)
        hulls &= yy <= lowest[None, :] + 1
        # the trousers cast a thin soft shadow on the floor - too thin to
        # survive into the confident-backdrop set, so it reads as subject.
        # Neutral and darker than the plate, below the hem, outside a shoe:
        # that is floor.
        plate_lum = plate.mean(2)
        shadow = ((yy > feet_y) & (chroma < 16) & (plate_lum - lum > 2)
                  & (plate_lum - lum < 90) & ~hulls)
        alpha = np.where(shadow, 0.0, alpha)
        alpha = np.maximum(alpha, hulls.astype(np.float32))
    alpha = keep_main_subject(alpha)
    alpha = fill_small_holes(alpha, max_area=600)
    alpha = ndimage.gaussian_filter(alpha, 0.7)
    rgb = unmix(img, plate, alpha)
    return rgb, alpha


LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def ghost_plate(frame, ring=60):
    """Backdrop for a ghost clip: the sweep's lighting is constant, so fit it once."""
    h, w = frame.shape[:2]
    m = np.zeros((h, w), bool)
    m[:ring] = m[-ring:] = True
    m[:, :ring] = m[:, -ring:] = True
    return fit_quadratic_backdrop(frame, m)


def key_dark_on_grey(img, plate, lo=14.0, hi=58.0):
    """Ghost outfits: dark fabric on a light grey sweep, keyed on luminance.

    plate is the clip's fitted backdrop (constant lighting), so this is cheap
    enough to run per frame. Every colourway is far darker than the sweep,
    while the outfit's own soft floor shadow is only slightly darker - the
    lo/hi ramp keeps the fabric and drops the shadow.
    """
    lum = img @ LUMA
    plate_lum = plate @ LUMA
    diff = plate_lum - lum
    # solid core: clearly fabric. A cast floor shadow is only 25-55 darker
    # than the sweep, the fabric 100+, so the shadow never makes the core.
    core = diff > hi
    core = ndimage.binary_opening(core, iterations=2)
    core = keep_main_subject(core.astype(np.float32), grow=0) > 0.5
    core = fill_small_holes(core.astype(np.float32), max_area=2500) > 0.5
    # soft ramp only in a thin band at the silhouette, never out on the floor
    inner = ndimage.binary_erosion(core, iterations=2)
    band = ndimage.binary_dilation(core, iterations=3)
    ramp = np.clip((diff - lo) / (hi - lo), 0, 1)
    alpha = np.where(inner, 1.0, np.where(band, ramp, 0.0))
    alpha = ndimage.gaussian_filter(alpha, 0.6)
    alpha = np.where(inner, 1.0, np.where(band, alpha, 0.0))
    rgb = unmix(img, plate, alpha)
    return rgb, alpha
