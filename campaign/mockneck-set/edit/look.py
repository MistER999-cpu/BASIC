"""Colour pipeline for the BASIC ad: per-shot correction at source resolution, then one
filmic look shared by every frame (tone curve, warm highlights, halation, bloom,
vignette, grain)."""
import numpy as np
import cv2
from scipy import ndimage as nd
from scipy.interpolate import PchipInterpolator

W, H = 1080, 1920

# ---------------------------------------------------------------- per-shot correction
# Stone (limestone) G/R and B/R measured in each clip; we pull them 70% of the way to
# one warm-cream target so the three locations read as one building in one light.
STONE = {'pre': (0.905, 0.836), 'S1': (0.896, 0.803), 'S2': (0.895, 0.805), 'S3': (0.889, 0.794),
         'S4': (0.903, 0.833), 'S5': (0.918, 0.847), 'S6': (0.878, 0.811), 'S7': (0.909, 0.845),
         'S8': (0.908, 0.789), 'S9': (0.920, 0.859)}
TARGET_G, TARGET_B, WB_STRENGTH = 0.900, 0.820, 0.7

# Burgundy in the generated clips drifted redder/lighter than the product sheet
# (sheet: hue 334, clips: 344-350). Shift hue toward the sheet and enrich it.
BURGUNDY = {'S3': dict(dh=-11.0, ks=1.14, kv=1.14), 'S6': dict(dh=-9.0, ks=1.18, kv=1.14),
            'S9': dict(dh=-13.0, ks=1.06, kv=1.25)}
BLACK_SHOTS = {'pre', 'S1', 'S4', 'S7'}
EXPOSURE = {'S5': 1.05, 'S8': 1.0, 'pre': 1.03}


def wb_gains(shot):
    if shot not in STONE:
        return np.ones(3, np.float32)
    g, b = STONE[shot]
    return np.array([1.0, (TARGET_G / g) ** WB_STRENGTH, (TARGET_B / b) ** WB_STRENGTH], np.float32)


def _skin(f):
    r, g = f[..., 0], f[..., 1]
    return (g > 0.62 * r) & (r > 0.27)


def fix_burgundy(f, dh, ks, kv):
    """Shift burgundy fabric toward the product sheet's wine-plum, leaving skin alone."""
    hsv = cv2.cvtColor(np.clip(f, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)       # H in degrees
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    r, g = f[..., 0], f[..., 1]
    skin = nd.binary_dilation(_skin(f), iterations=6)
    m = (((h >= 300) | (h <= 20)) & (s > 0.20) & (v > 0.055) & (v < 0.85) & (g < 0.62 * r) & ~skin)
    m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.5)
    hsv[..., 0] = (h + dh * m) % 360
    hsv[..., 1] = np.clip(s * (1 + (ks - 1) * m), 0, 1)
    hsv[..., 2] = np.clip(v * (1 + (kv - 1) * m), 0, 1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def correct_native(rgb_u8, shot):
    """Per-shot fixes on the 720x1280 source frame. Returns float32 RGB 0-1."""
    f = rgb_u8.astype(np.float32)
    if rgb_u8.dtype == np.uint8:
        f /= 255.0
    f = f * wb_gains(shot)[None, None, :] * EXPOSURE.get(shot, 1.0)
    if shot in BURGUNDY:
        f = fix_burgundy(f, **BURGUNDY[shot])
    if shot in BLACK_SHOTS:
        y = f @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        mx = f.max(2); mn = f.min(2)
        sat = (mx - mn) / (mx + 1e-4)
        m = np.clip((0.32 - y) / 0.12, 0, 1) * np.clip((0.55 - sat) / 0.2, 0, 1)
        m = cv2.GaussianBlur(m, (0, 0), 1.2)[..., None]
        warm = np.array([1.06, 1.0, 0.93], np.float32)            # soft warm-neutral black
        neutral = y[..., None] * warm
        f = f * (1 - 0.72 * m) + neutral * (0.72 * m)
    return np.clip(f, 0, 1)


def upscale(f):
    out = cv2.resize(f, (W, H), interpolation=cv2.INTER_LANCZOS4)
    blur = cv2.GaussianBlur(out, (0, 0), 1.1)
    return np.clip(out + 0.38 * (out - blur), 0, 1)


# ---------------------------------------------------------------- shared filmic look
_curve = PchipInterpolator([0.0, 0.10, 0.25, 0.45, 0.65, 0.85, 1.0],
                           [0.020, 0.082, 0.222, 0.440, 0.668, 0.862, 0.968])
LUT = _curve(np.linspace(0, 1, 2048)).astype(np.float32)


def tone(f):
    idx = np.clip(f * 2047, 0, 2047).astype(np.int32)
    return LUT[idx]


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H * 0.47) / (H * 0.60)) ** 2)
VIGNETTE = (1 - 0.24 * np.clip(_r, 0, 1.6) ** 2.4).clip(0.55, 1).astype(np.float32)[..., None]
del _yy, _xx, _r

_rng = np.random.default_rng(11)
_GRAIN = []
for _ in range(8):
    n = _rng.standard_normal((H, W)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), 0.75)
    n /= n.std()
    _GRAIN.append(n)


def look(f, halation=0.22, bloom=0.06):
    """Shared grade on an output-resolution float frame."""
    f = tone(f)
    y = f @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    w = smoothstep(0.50, 1.0, y)[..., None]
    f = f * (1 + w * np.array([0.030, 0.006, -0.045], np.float32))
    # gentle global desaturation, stronger on greens (potted plants, foliage)
    green = np.clip((f[..., 1] - np.maximum(f[..., 0], f[..., 2])) * 8, 0, 1)
    sat = (0.96 - 0.45 * green)[..., None]
    f = y[..., None] + (f - y[..., None]) * sat
    # halation + bloom, computed at half resolution
    small = cv2.resize(f, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    ys = small @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    hmask = smoothstep(0.70, 1.0, ys)[..., None] * small
    hal = cv2.GaussianBlur(hmask, (0, 0), 9) * np.array([1.0, 0.48, 0.26], np.float32)
    blo = cv2.GaussianBlur(small, (0, 0), 22)
    add = cv2.resize(hal * halation + blo * bloom, (W, H), interpolation=cv2.INTER_LINEAR)
    f = 1 - (1 - f) * (1 - add)                                  # screen
    return np.clip(f, 0, 1)


def vignette(f):
    return f * VIGNETTE


def grain(f, frame_idx, amp=0.017):
    n = _GRAIN[frame_idx % len(_GRAIN)]
    sh = (frame_idx * 37) % 97
    n = np.roll(n, (sh, sh * 3), axis=(0, 1))
    y = f @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    wgt = 0.45 + 2.2 * y * (1 - y)                               # most visible in mids
    return np.clip(f + (n * wgt * amp)[..., None], 0, 1)
