#!/usr/bin/env python3
"""Synthesise the ad's sound design, frame-locked to both scenes.

    python3 tools/sfx.py [out.wav]

Everything is generated here from noise and sine partials, so the track is
licence-free and safe for paid placement. Event times mirror the timeline
constants in src/folder/scene.html (T) and src/lookbook/scene.html (CAM,
BLOOM, grow times, LOGO_IN, PERCH_AT); keep them in step if either changes.
"""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
FPS = 30
P1_FRAMES = round(4.75 * FPS + 0.5)      # Math.round(142.5) in the renderer = 143
P2 = P1_FRAMES / FPS                     # part 2 starts here
DUR = P2 + 9.6
rng = np.random.default_rng(7)

mix = np.zeros((int(DUR * SR) + SR, 2), np.float32)


def db(x):
    return 10 ** (x / 20)


def place(sound, t, gain_db=0.0, pan=0.0):
    """Add a mono sound at time t (s), equal-power panned (-1 left .. 1 right)."""
    i = int(round(t * SR))
    if i < 0:
        sound, i = sound[-i:], 0
    s = sound[: max(0, len(mix) - i)] * db(gain_db)
    a = (pan + 1) * np.pi / 4
    mix[i:i + len(s), 0] += s * np.cos(a)
    mix[i:i + len(s), 1] += s * np.sin(a)


def noise(n):
    return rng.standard_normal(n).astype(np.float32)


def band(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos')
    return signal.sosfilt(sos, x).astype(np.float32)


def lowp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'lowpass', fs=SR, output='sos'), x).astype(np.float32)


def env_exp(n, attack, tau):
    t = np.arange(n) / SR
    return (1 - np.exp(-t / max(attack, 1e-4))) * np.exp(-t / tau)


def norm(x):
    return x / (np.abs(x).max() + 1e-9)


# ---- sounds ----------------------------------------------------------------
def key_tick():
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    x = band(noise(n), 2500, 9000) * env_exp(n, 0.0004, 0.004)
    x += 0.25 * np.sin(2 * np.pi * rng.uniform(3800, 4600) * t) * env_exp(n, 0.0002, 0.006)
    return norm(x)


def click():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    down = band(noise(n), 1500, 7000) * env_exp(n, 0.0003, 0.003) + \
        0.5 * np.sin(2 * np.pi * 1900 * t) * env_exp(n, 0.0002, 0.008)
    up = np.zeros(n, np.float32)
    k = int(0.055 * SR)
    up[k:] = 0.45 * down[: n - k]
    return norm(down + up)


def whoosh(dur, f0, f1, peak=0.6):
    """Noise through a band that sweeps f0 -> f1, swelling to peak (0..1 of dur)."""
    n = int(dur * SR)
    x = noise(n + 2048)
    f, tt, Z = signal.stft(x, SR, nperseg=1024)
    u = np.clip(tt / dur, 0, 1)
    centre = f0 * (f1 / f0) ** u
    width = centre * 0.9
    mask = np.exp(-0.5 * ((f[:, None] - centre[None, :]) / width[None, :]) ** 2)
    _, y = signal.istft(Z * mask, SR, nperseg=1024)
    y = y[:n]
    t = np.arange(n) / n
    e = np.where(t < peak, np.sin(np.pi / 2 * t / peak) ** 2, np.cos(np.pi / 2 * (t - peak) / (1 - peak)) ** 2)
    return norm(y * e).astype(np.float32)


def pop():
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    f = 320 + 520 * (1 - np.exp(-t / 0.012))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * env_exp(n, 0.002, 0.022)
    x += 0.15 * band(noise(n), 800, 3000) * env_exp(n, 0.001, 0.01)
    return norm(x)


def tap():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = 190 * np.exp(-t / 0.05) + 95
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.001, 0.03)
    x += 0.35 * band(noise(n), 1200, 5000) * env_exp(n, 0.0005, 0.004)
    return norm(x)


def fwip(dur=0.26):
    n = int(dur * SR)
    x = band(noise(n), 1400, 6500) * env_exp(n, 0.02, 0.07)
    return norm(x)


def thud():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * (70 + 40 * np.exp(-t / 0.03)) * t) * env_exp(n, 0.002, 0.06)
    x += 0.3 * lowp(noise(n), 400) * env_exp(n, 0.001, 0.03)
    return norm(x)


def shimmer(dur=0.9):
    n = int(dur * SR)
    t = np.arange(n) / SR
    air = whoosh(dur, 2500, 8000, peak=0.7) * 0.7
    glints = np.zeros(n, np.float32)
    for f in (1046.5, 1318.5, 1568.0, 2093.0, 2637.0):          # C6 E6 G6 C7 E7
        k = int(rng.uniform(0.15, 0.75) * n)
        m = n - k
        tt = np.arange(m) / SR
        glints[k:] += 0.22 * np.sin(2 * np.pi * f * tt) * env_exp(m, 0.004, 0.35)
    return norm(air + glints)


def logo_hit(dur=2.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (58 + 30 * np.exp(-t / 0.08)) * t) * env_exp(n, 0.004, 0.45)
    pad = np.zeros(n, np.float32)
    for f, a in ((220.0, 1), (277.18, 0.7), (329.63, 0.8), (440.0, 0.5), (554.37, 0.25)):
        vib = 1 + 0.002 * np.sin(2 * np.pi * 4.5 * t)
        pad += a * (np.sin(2 * np.pi * f * vib * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t))
    pad = pad * (1 - np.exp(-t / 0.12)) * np.exp(-t / 1.4)
    return norm(0.8 * boom + 0.55 * norm(pad))


def flutter(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 7.5 * t) ** 8
    fade = np.minimum(1, np.minimum(t / 0.3, (dur - t) / 0.3))
    return norm(band(noise(n), 300, 1400) * am * fade)


def wind(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    brown = np.cumsum(noise(n)) / SR * 60
    brown = signal.sosfilt(signal.butter(1, 20, 'highpass', fs=SR, output='sos'), brown)
    x = lowp(brown, 600) + 0.03 * band(noise(n), 2000, 5000)
    gust = 0.65 + 0.35 * np.sin(2 * np.pi * 0.23 * t + 1) * np.sin(2 * np.pi * 0.11 * t)
    return norm(x * gust).astype(np.float32)


# ---- part 1: the folder ---------------------------------------------------------
for k in range(len("Les BASIC's")):
    place(key_tick(), 0.06 + 0.045 * k, -27, 0.05 * (k - 5) / 5)
place(click(), 0.66, -15, 0.02)
place(click(), 0.86, -15, 0.02)
place(fwip(), 0.95, -21, 0.0)
place(whoosh(0.5, 300, 900), 0.90, -26, 0.0)
cols = {4: [165, 405, 645, 885], 3: [300, 540, 780]}
waves = [1.22, 1.58, 1.94]
for w, count in enumerate([4, 3, 3]):
    for i in range(count):
        launch = waves[w] + i * 0.07
        pan = (cols[count][i] - 540) / 540 * 0.6
        place(pop(), launch, -22, pan * 0.3)
        place(tap(), launch + 0.20 + 0.56 * 0.82, -25, pan)
    place(whoosh(0.45, 600, 2400), waves[w] - 0.02, -27, 0.0)
place(thud(), 2.30, -24, 0.0)
place(click(), 3.36, -15, -0.2)
place(whoosh(0.4, 500, 2600, peak=0.8), 3.53, -20, 0.0)
place(whoosh(0.55, 400, 3000, peak=0.85), 4.20, -19, 0.0)

# ---- part 2: the lookbook -------------------------------------------------------
place(shimmer(0.9), P2 + 0.10, -18, 0.0)
w = wind(9.6)
fade = np.minimum(1, np.minimum(np.arange(len(w)) / SR / 0.8, (9.6 - np.arange(len(w)) / SR) / 0.6))
place(w * fade, P2 + 0.0, -35, 0.0)
moves = [(1.25, 1.85), (2.35, 2.95), (3.45, 4.10), (4.60, 5.30), (5.80, 6.40), (7.05, 7.85)]
for k, (a, b) in enumerate(moves):
    place(whoosh(b - a + 0.15, 250 + 40 * k, 1100 + 80 * k, peak=0.5), P2 + a - 0.05, -24, 0.0)
for g in (0.25, 1.40, 2.55, 3.65, 4.85, 6.0):
    place(fwip(0.3) * 0.6, P2 + g + 0.05, -30, 0.25)
place(flutter(2.3), P2 + 2.6, -35, -0.3)
place(flutter(1.85), P2 + 6.7, -35, 0.3)
place(logo_hit(), P2 + 7.55, -16, 0.0)
place(shimmer(0.7), P2 + 7.95, -26, 0.15)
place(tap() * 0.6, P2 + 8.55, -28, 0.3)

# ---- master ----------------------------------------------------------------------
out = mix[: int(DUR * SR)]
tail = int(0.35 * SR)
out[-tail:] *= np.linspace(1, 0, tail)[:, None]
# a feed ad plays in a noisy scroll: lift the bed ~5 dB under a soft limiter,
# peaks held at -1 dBFS
out = out / np.abs(out).max() * db(-1.5)
out = np.tanh(out * db(5) * 1.2) / 1.2
out = out / np.abs(out).max() * db(-1.0)
rms = 20 * np.log10(np.sqrt((out ** 2).mean()) + 1e-12)
path = sys.argv[1] if len(sys.argv) > 1 else 'campaign/final/sfx.wav'
wavfile.write(path, SR, (out * 32767).astype(np.int16))
print(f'  {path}: {DUR:.3f}s, part 2 at {P2:.4f}s, RMS {rms:.1f} dBFS')
