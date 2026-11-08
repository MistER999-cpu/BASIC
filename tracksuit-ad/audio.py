#!/usr/bin/env python3
"""Rain and thunder bed for the ad, synthesised so there is nothing to license.

    python3 audio.py            # -> out/ambience.wav

Thunder lands just after each flash in render.py (light arrives before sound),
the opening strike included. It is an ambience layer: a music track goes on
top of it in the edit, or replaces it.
"""
import os
import numpy as np
from scipy import signal
from scipy.io import wavfile

from render import LIGHTNING, DUR, P

SR = 48000
rng = np.random.default_rng(11)


def band(x, lo=None, hi=None, order=4):
    if lo and hi:
        sos = signal.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos')
    elif lo:
        sos = signal.butter(order, lo, 'highpass', fs=SR, output='sos')
    else:
        sos = signal.butter(order, hi, 'lowpass', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def smooth_noise(n, rate_hz):
    """Slow random wobble in [0,1] for rolling thunder and gusts."""
    k = max(2, int(n / SR * rate_hz) + 2)
    pts = rng.uniform(0, 1, k)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)


def rain(n):
    out = np.zeros((n, 2))
    for c in range(2):
        hiss = band(rng.normal(0, 1, n), 500, 9000) * 0.35
        body = band(rng.normal(0, 1, n), 150, 900) * 0.22
        # individual drops: sparse clicks, each a tiny damped burst
        drops = np.zeros(n)
        idx = rng.integers(0, n, int(n / SR * 55))
        drops[idx] = rng.uniform(0.3, 1.0, len(idx)) * rng.choice([-1, 1], len(idx))
        drops = band(drops, 1800, 7000, order=2) * 2.2
        gust = 0.85 + 0.15 * smooth_noise(n, 0.6)
        out[:, c] = (hiss + body + drops) * gust
    return out


def thunder(n, t0, strength, distance):
    """A crack and a rolling rumble starting at t0 seconds."""
    out = np.zeros((n, 2))
    start = int(t0 * SR)
    if start >= n:
        return out
    m = n - start
    t = np.arange(m) / SR
    for c in range(2):
        crack_env = np.exp(-t / (0.08 + 0.12 * distance)) * (1 - np.exp(-t / 0.004))
        crackle = (rng.uniform(0, 1, m) < 0.02) * rng.normal(0, 1, m)
        crack = band(rng.normal(0, 1, m) * 0.5 + crackle * 3, 300, 6000 * (1 - 0.7 * distance))
        brown = np.cumsum(rng.normal(0, 1, m))
        brown -= band(brown, hi=8, order=2)                 # keep it from drifting
        rumble = band(brown, 25, 180 - 80 * distance) * 0.06
        roll = 0.45 + 0.55 * smooth_noise(m, 3.0)
        rumble_env = (1 - np.exp(-t / 0.09)) * np.exp(-t / (1.8 + 1.4 * distance))
        sig = crack * crack_env * (1 - distance) * 0.9 + rumble * rumble_env * roll
        out[start:, c] = sig * strength
    return out


def main():
    n = int(DUR * SR)
    mix = rain(n)
    mix /= np.abs(mix).max()
    mix *= 10 ** (-16 / 20)                                 # rain bed around -16 dBFS peak
    # the plate opens on its own bolt; then every flash the renderer adds
    events = [(0.0, 0.9, 0.0)] + [(t, min(s, 1.0), 0.0 if off is not None else 0.75)
                                  for t, s, off in LIGHTNING]
    th = np.zeros_like(mix)
    for t0, s, dist in events:
        delay = 0.12 + 0.9 * dist
        th += thunder(n, t0 + delay, s, dist)
    th /= np.abs(th).max()
    mix += th * 10 ** (-5 / 20)
    fade = int(0.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mix[:int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
    peak = np.abs(mix).max()
    mix *= 10 ** (-1 / 20) / peak
    os.makedirs(P('out'), exist_ok=True)
    wavfile.write(P('out', 'ambience.wav'), SR, (mix * 32767).astype(np.int16))
    print('wrote out/ambience.wav', f'{DUR}s')


if __name__ == '__main__':
    main()
