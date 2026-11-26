"""Colour pipeline for the BASIC winter film.

Per clip (at the 720x1280 source): white balance the stone/snow to one cool neutral and pull
the burgundy fabric to one wine hue, so ten generated clips read as one morning in one city.
Per frame (at 1080x1920): a cold, soft filmic grade (tone curve, cool split-tone, saturation
that protects the burgundy and skin, cool halation, vignette, grain).
"""
import numpy as np
import cv2
from scipy.interpolate import PchipInterpolator

W, H = 1080, 1920
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)

# ---------------------------------------------------------------- per-clip correction
# Measured on the delivered clips: median G/R and B/R of the low-saturation stone/snow, and
# the median hue / saturation / value of the burgundy fabric.
NEUTRAL = {'S1': (0.990, 0.943), 'S2': (0.995, 0.947), 'S3': (1.010, 1.014), 'S4': (1.005, 0.990),
           'S5': (0.990, 0.943), 'W1': (0.995, 0.947), 'W2': (1.015, 1.010), 'W3': (1.005, 0.990),
           'X1': (0.985, 0.939), 'X2': (0.985, 0.945)}
FABRIC = {'S1': (344, 0.61, 0.19), 'S2': (339, 0.51, 0.31), 'S3': (344, 0.54, 0.22),
          'S4': (346, 0.58, 0.20), 'S5': (343, 0.51, 0.34), 'W1': (338, 0.50, 0.30),
          'W2': (347, 0.55, 0.31), 'W3': (345, 0.58, 0.21), 'X1': (343, 0.54, 0.33),
          'X2': (340, 0.52, 0.35)}
TARGET_GR, TARGET_BR, WB_STRENGTH = 1.000, 1.020, 0.85
TARGET_HUE, TARGET_SAT = 338.0, 0.57
# wide shots came out darker on the fabric than the close-ups; lift them toward one value
FABRIC_V = {'S1': 1.22, 'S4': 1.18, 'W3': 1.18, 'S3': 1.10}
EXPOSURE = {'W1': 1.04}


def wb_gains(clip):
    gr, br = NEUTRAL[clip]
    g = np.array([1.0, (TARGET_GR / gr) ** WB_STRENGTH, (TARGET_BR / br) ** WB_STRENGTH], np.float32)
    return g / float(g @ LUMA)                        # keep the luminance of white


def fix_fabric(f, clip):
    """Soft-weighted hue/sat/value pull of the wine fabric (no hard mask: lit folds and shadows
    move together). Skin has a high G/R ratio and is left alone."""
    hue, sat, _ = FABRIC[clip]
    dh = TARGET_HUE - hue
    ks = float(np.clip(TARGET_SAT / sat, 0.95, 1.12))
    kv = FABRIC_V.get(clip, 1.0)
    hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    gr = f[..., 1] / (f[..., 0] + 1e-3)
    hd = np.minimum(np.abs(h - hue), 360 - np.abs(h - hue))
    w = (np.clip((0.70 - gr) / 0.14, 0, 1) * np.clip((40 - hd) / 18, 0, 1)
         * np.clip((s - 0.15) / 0.12, 0, 1) * np.clip((0.85 - v) / 0.15, 0, 1))
    w = cv2.GaussianBlur(w, (0, 0), 1.6)
    hsv[..., 0] = (h + dh * w) % 360
    hsv[..., 1] = np.clip(s * (1 + (ks - 1) * w), 0, 1)
    hsv[..., 2] = np.clip(v * (1 + (kv - 1) * w), 0, 1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def correct(rgb_u8, clip):
    f = rgb_u8.astype(np.float32) / 255.0
    f = f * wb_gains(clip)[None, None, :] * EXPOSURE.get(clip, 1.0)
    f = fix_fabric(np.clip(f, 0, 1), clip)
    return np.clip(f, 0, 1)


def sharpen(f, amount=0.35, sigma=1.0):
    b = cv2.GaussianBlur(f, (0, 0), sigma)
    return np.clip(f + amount * (f - b), 0, 1)


# ---------------------------------------------------------------- shared winter grade
_curve = PchipInterpolator([0.0, 0.08, 0.25, 0.50, 0.75, 0.92, 1.0],
                           [0.030, 0.088, 0.232, 0.497, 0.762, 0.912, 0.972])
LUT = _curve(np.linspace(0, 1, 2048)).astype(np.float32)


def tone(f):
    return LUT[np.clip(f * 2047, 0, 2047).astype(np.int32)]


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W * 0.64)) ** 2 + ((_yy - H * 0.48) / (H * 0.62)) ** 2)
VIGNETTE = (1 - 0.20 * np.clip(_r, 0, 1.6) ** 2.4).clip(0.6, 1).astype(np.float32)[..., None]
del _yy, _xx, _r

SH_TINT = np.array([-0.020, 0.000, 0.026], np.float32)     # cool shadows
HI_TINT = np.array([-0.012, 0.000, 0.016], np.float32)     # cold white highlights
HAL_TINT = np.array([0.86, 0.93, 1.0], np.float32)


def grade(f, halation=0.10, bloom=0.035, vig=True):
    f = tone(f)
    y = f @ LUMA
    sh = (1 - smoothstep(0.0, 0.45, y))[..., None]
    hi = smoothstep(0.55, 1.0, y)[..., None]
    f = f * (1 + sh * SH_TINT + hi * HI_TINT)
    # cold, slightly muted world; the wine fabric and skin keep their colour
    warm = np.clip((f[..., 0] - np.maximum(f[..., 1], f[..., 2])) * 5.0, 0, 1)
    sat = (0.86 + 0.20 * warm)[..., None]
    y = (f @ LUMA)[..., None]
    f = y + (f - y) * sat
    small = cv2.resize(f, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    ys = small @ LUMA
    hmask = smoothstep(0.72, 1.0, ys)[..., None] * small
    hal = cv2.GaussianBlur(hmask, (0, 0), 10) * HAL_TINT
    blo = cv2.GaussianBlur(small, (0, 0), 24)
    add = cv2.resize(hal * halation + blo * bloom, (W, H), interpolation=cv2.INTER_LINEAR)
    f = 1 - (1 - np.clip(f, 0, 1)) * (1 - add)
    if vig:
        f = f * VIGNETTE
    return np.clip(f, 0, 1)


def grade_simple(f):
    """The grade without the frame-sized passes (vignette, halation): for layers of any size."""
    f = tone(f)
    y = f @ LUMA
    sh = (1 - smoothstep(0.0, 0.45, y))[..., None]
    hi = smoothstep(0.55, 1.0, y)[..., None]
    f = f * (1 + sh * SH_TINT + hi * HI_TINT)
    warm = np.clip((f[..., 0] - np.maximum(f[..., 1], f[..., 2])) * 5.0, 0, 1)
    y = (f @ LUMA)[..., None]
    return np.clip(y + (f - y) * (0.86 + 0.20 * warm)[..., None], 0, 1)


_rng = np.random.default_rng(17)
_GRAIN = []
for _ in range(8):
    n = _rng.standard_normal((H, W)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), 0.8)
    _GRAIN.append(n / n.std())


def grain(f, i, amp=0.013):
    n = np.roll(_GRAIN[i % 8], ((i * 37) % 97, (i * 111) % 89), axis=(0, 1))
    y = f @ LUMA
    return np.clip(f + (n * (0.4 + 2.0 * y * (1 - y)) * amp)[..., None], 0, 1)
