#!/usr/bin/env python3
"""Sound design for the BASIC ad - all synthesised, nothing to license.

    python3 audio.py            # -> out/soundtrack.wav (loudness-normalised later)

Layers:
  rain     soft and muffled: pink noise with the hiss band rolled off, so it
           reads as rain on a window rather than static
  pad      a warm, low-passed chord bed that moves with each colourway
  thunder  a rounded crack and a long rolling rumble after every strike
  sfx      whooshes on moves, low impacts on cuts, a shimmer when the logo is
           swept, a riser into the line-up, soft pops on the swatches

Every cue is placed from the timeline constants in render.py, so retiming
the picture retimes the sound.
"""
import os
import numpy as np
from scipy import signal
from scipy.io import wavfile

from render import SEGMENTS, FLASHES, LINEUP_T, SLATE_T, DUR, P

SR = 48000
N = int(DUR * SR)
rng = np.random.default_rng(17)


def db(x):
    return 10 ** (x / 20)


def sos_filter(x, kind, f, order=2):
    sos = signal.butter(order, f, kind, fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)


def place(bus, sig, t0):
    """Add a (n,) or (n,2) signal into the stereo bus at time t0."""
    if sig.ndim == 1:
        sig = np.stack([sig, sig], 1)
    s = int(round(t0 * SR))
    if s < 0:
        sig, s = sig[-s:], 0
    e = min(N, s + len(sig))
    if e > s:
        bus[s:e] += sig[:e - s]


def pan(sig, p):
    """Equal-power pan; p in [-1, 1], scalar or per-sample."""
    a = (np.asarray(p) + 1) * np.pi / 4
    return np.stack([sig * np.cos(a), sig * np.sin(a)], 1)


def make_ir(seconds=2.6, lp=5000):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-t / (seconds / 6.9))[:, None]
    ir = sos_filter(ir, 'lowpass', lp)
    ir[: int(0.018 * SR)] = 0                       # pre-delay
    return ir / np.sqrt((ir ** 2).sum(0))


IR = make_ir()


def reverb(sig, wet):
    if sig.ndim == 1:
        sig = np.stack([sig, sig], 1)
    out = np.stack([signal.fftconvolve(sig[:, c], IR[:, c])[: len(sig) + len(IR) - 1]
                    for c in range(2)], 1)
    dry = np.zeros_like(out)
    dry[: len(sig)] = sig
    return dry * (1 - wet) + out * wet


def swept_noise(dur, centres, width_oct=0.7, seed=None):
    """Noise through a band-pass whose centre follows `centres` (Hz, sampled
    across the duration). Done in the STFT domain, so it never clicks."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    x = r.normal(0, 1, n)
    f, tt, Z = signal.stft(x, SR, nperseg=1024, noverlap=768)
    c = np.interp(np.linspace(0, 1, Z.shape[1]), np.linspace(0, 1, len(centres)), np.log2(centres))
    lf = np.log2(np.maximum(f, 1.0))[:, None]
    Z *= np.exp(-0.5 * ((lf - c[None, :]) / width_oct) ** 2)
    _, y = signal.istft(Z, SR, nperseg=1024, noverlap=768)
    y = y[:n]
    return y / (np.abs(y).max() + 1e-9)

# ---------------------------------------------------------------- layers
def rain():
    out = np.zeros((N, 2))
    for c in range(2):
        spec = np.fft.rfft(rng.normal(0, 1, N))
        f = np.fft.rfftfreq(N, 1 / SR)
        spec /= np.sqrt(np.maximum(f, 20))           # pink
        x = np.fft.irfft(spec, N)
        x = sos_filter(x, 'highpass', 140)
        x = sos_filter(x, 'lowpass', 2600, order=4)  # no hiss - soft on the ear
        drops = np.zeros(N)
        idx = rng.integers(0, N, int(DUR * 22))
        drops[idx] = rng.uniform(0.2, 1.0, len(idx))
        drops = sos_filter(drops, 'bandpass', [600, 1800])
        x = x / np.abs(x).max() + drops / (np.abs(drops).max() + 1e-9) * 0.18
        out[:, c] = x
    t = np.arange(N) / SR
    gust = 0.88 + 0.12 * np.interp(t, np.linspace(0, DUR, 9), rng.uniform(0, 1, 9))
    fade = np.clip(t / 1.2, 0, 1) * np.clip((DUR - t) / 0.9, 0, 1)
    out *= (gust * fade)[:, None]
    return out / np.sqrt((out ** 2).mean()) * db(-31)


def saw_voice(freq, n, detune_cents=(-7, 0, 7)):
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for k, dc in enumerate(detune_cents):
        f = freq * 2 ** (dc / 1200)
        ph = rng.uniform(0, 2 * np.pi)
        v = np.zeros(n)
        for h in range(1, int(2800 / f) + 1):
            v += np.sin(2 * np.pi * f * h * t + ph * h) / h
        side = (k - 1) * 0.6                          # spread the detuned copies
        out += pan(v, side)
    return out


NOTE = lambda name: 440 * 2 ** ((
    {'C': -9, 'D': -7, 'E': -5, 'F': -4, 'G': -2, 'A': 0, 'Bb': 1, 'B': 2}[name[:-1]]
    + 12 * (int(name[-1]) - 4)) / 12)


def pad():
    """Chord per section: a D minor colour that opens, warms, darkens, resolves."""
    s1, s2, s3 = (s['t0'] for s in SEGMENTS)
    plan = [
        (0.0, s1, ['D2', 'A2', 'D3', 'A3']),
        (s1, s2, ['D3', 'F3', 'A3', 'C4', 'E4']),          # Dm9 - Bordeaux
        (s2, s3, ['Bb2', 'D3', 'F3', 'A3', 'C4']),         # Bbmaj9 - Chocolat
        (s3, LINEUP_T, ['G2', 'D3', 'F3', 'Bb3', 'A3']),   # Gm9 - Noir
        (LINEUP_T, SLATE_T, ['F2', 'C3', 'G3', 'A3', 'E4']),  # Fmaj9 - line-up
        (SLATE_T, DUR, ['D2', 'A2', 'F3', 'A3', 'E4']),    # Dm(add9) - resolve
    ]
    bus = np.zeros((N, 2))
    for a, b, notes in plan:
        start, end = max(a - 0.25, 0), min(b + 0.9, DUR)
        n = int((end - start) * SR)
        t = np.arange(n) / SR
        env = np.clip(t / 0.7, 0, 1) * np.clip((end - start - t) / 0.9, 0, 1)
        chord = sum(saw_voice(NOTE(x), n) / np.sqrt(len(notes)) for x in notes)
        place(bus, chord * env[:, None], start)
    bus = sos_filter(bus, 'lowpass', 1100)
    bus = sos_filter(bus, 'highpass', 60)
    t = np.arange(N) / SR
    bus *= (np.clip(t / 1.5, 0, 1) * np.clip((DUR - t) / 1.0, 0, 1))[:, None]
    bus = reverb(bus, 0.35)[:N]
    return bus / np.sqrt((bus ** 2).mean()) * db(-29)


def thunder(strength, distance, seed):
    r = np.random.default_rng(seed)
    dur = 4.0 + 1.5 * distance
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for c in range(2):
        crack = sos_filter(r.normal(0, 1, n) + (r.uniform(0, 1, n) < 0.015) * r.normal(0, 3, n),
                           'bandpass', [180, 2400 * (1 - 0.6 * distance)])
        crack *= np.exp(-t / (0.3 + 0.3 * distance)) * (1 - np.exp(-t / 0.008)) * (1 - distance)
        brown = np.cumsum(r.normal(0, 1, n))
        brown = sos_filter(brown, 'bandpass', [28, 170 - 70 * distance])
        brown /= np.abs(brown).max() + 1e-9
        roll = 0.45 + 0.55 * np.interp(t, np.linspace(0, dur, int(dur * 3) + 2),
                                       r.uniform(0, 1, int(dur * 3) + 2))
        rumble = brown * roll * (1 - np.exp(-t / 0.15)) * np.exp(-t / (2.4 + 1.5 * distance))
        out[:, c] = crack / (np.abs(crack).max() + 1e-9) * 0.55 + rumble
    out = reverb(out, 0.3)
    return out / np.abs(out).max() * strength


def boom(level, seed, length=1.4, f0=88, f1=40):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.55)
    body = np.tanh(1.6 * body) / np.tanh(1.6)
    r = np.random.default_rng(seed)
    thump = sos_filter(r.normal(0, 1, n), 'lowpass', 220) * np.exp(-t / 0.07)
    s = body + thump / (np.abs(thump).max() + 1e-9) * 0.35
    s = reverb(s, 0.22)
    return s / np.abs(s).max() * level


def whoosh(dur, centres, p_from, p_to, level, seed):
    x = swept_noise(dur, centres, 0.6, seed)
    n = len(x)
    u = np.linspace(0, 1, n)
    env = np.where(u < 0.58, np.sin(u / 0.58 * np.pi / 2) ** 2, np.exp(-(u - 0.58) / 0.16))
    s = pan(x * env, np.linspace(p_from, p_to, n))
    s = reverb(s, 0.2)
    return s / np.abs(s).max() * level


def shimmer(level, seed):
    r = np.random.default_rng(seed)
    n = int(2.4 * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for i, f in enumerate([1174.7, 1760.0, 2349.3, 2637.0, 3520.0]):
        on = r.uniform(0, 0.12)
        tt = np.clip(t - on, 0, None)
        vib = 1 + 0.0018 * np.sin(2 * np.pi * 5.2 * tt + i)
        env = (t >= on) * (1 - np.exp(-tt / 0.02)) * np.exp(-tt / (0.9 - 0.1 * i))
        out += pan(np.sin(2 * np.pi * f * vib * tt) * env / (1 + 0.4 * i), r.uniform(-0.6, 0.6))
    out = sos_filter(out, 'lowpass', 6000)
    out = reverb(out, 0.5)
    return out / np.abs(out).max() * level


def riser(dur, level, seed):
    x = swept_noise(dur, [300, 600, 1400, 3200], 0.7, seed)
    n = len(x)
    u = np.linspace(0, 1, n)
    t = np.arange(n) / SR
    glide = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (1.6 * u)) / SR) * 0.35
    env = u ** 2.2
    env[-int(0.006 * SR):] *= np.linspace(1, 0, int(0.006 * SR))
    s = pan((x + glide) * env, np.sin(2 * np.pi * 0.8 * t) * 0.3)
    return s / np.abs(s).max() * level


def reverse_swell(dur, level, seed):
    r = np.random.default_rng(seed)
    burst = sos_filter(r.normal(0, 1, int(0.08 * SR)), 'lowpass', 3000)
    tail = reverb(burst, 1.0)
    tail = tail[::-1]
    n = int(dur * SR)
    tail = tail[-n:]
    tail *= np.linspace(0, 1, len(tail))[:, None] ** 1.5
    return tail / np.abs(tail).max() * level


def pop(level, f0=760, f1=520):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.012)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.06)
    s = reverb(s, 0.25)
    return s / np.abs(s).max() * level


def tick(level, f=1500):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.012)
    return s * level

# ---------------------------------------------------------------- score
def main():
    bus = np.zeros((N, 2))
    bus += rain()
    bus += pad()

    # thunder after every strike; distant ones arrive late and dull
    for i, (t0, s, bolt) in enumerate(FLASHES):
        distance = 0.0 if s >= 0.5 else 0.8
        delay = 0.04 if distance == 0 else 0.75
        level = db(-5) * min(s, 1.0) if distance == 0 else db(-14)
        place(bus, thunder(level, distance, 100 + i), t0 + delay)

    # cold open: the logo forms, is swept with light, then flies to the header
    place(bus, boom(db(-9), 1), 0.28)
    place(bus, shimmer(db(-19), 2), 0.86)
    for k in range(len('L’ENSEMBLE D’HIVER')):
        place(bus, tick(db(-38), 1500 + 40 * (k % 3)), 0.95 + 0.03 * k)
    place(bus, whoosh(0.6, [400, 1600, 700], 0.2, -0.6, db(-20), 3), 1.36)
    place(bus, whoosh(0.8, [250, 1300, 500], -0.8, 0.5, db(-15), 4), 1.52)
    place(bus, boom(db(-21), 5, 0.9, 70, 45), 2.12)
    for k in range(3):
        place(bus, pop(db(-30), 700 + 60 * k, 500 + 40 * k), 2.02 + 0.08 * k)

    for i, seg in enumerate(SEGMENTS):
        T = seg['t0']
        Tt = T + (0.3 if i == 0 else 0.0)
        if i > 0:                                    # the cut: swell, strike, impact
            place(bus, reverse_swell(0.5, db(-17), 10 + i), T - 0.5)
            place(bus, boom(db(-10), 20 + i), T)
            place(bus, whoosh(0.35, [500, 2200, 900], 0.6, 0.2, db(-22), 30 + i), T - 0.16)
            place(bus, pop(db(-26)), T + 0.04)
        place(bus, whoosh(0.5, [700, 2600, 1100], 0.3, 0.5, db(-27), 40 + i), Tt + 0.40)

    # into the line-up
    place(bus, riser(1.3, db(-14), 50), LINEUP_T - 1.3)
    place(bus, boom(db(-7), 51, 1.8, 95, 36), LINEUP_T)
    for k, t0 in enumerate([LINEUP_T + 0.45, LINEUP_T + 0.85]):
        place(bus, whoosh(0.55, [600, 2400, 1000], -0.3 + 0.6 * k, 0.0, db(-26), 52 + k), t0 - 0.05)
    for k in range(len('BORDEAUX  ·  CHOCOLAT  ·  NOIR')):
        if k % 2 == 0:
            place(bus, tick(db(-40), 1400 + 50 * (k % 4)), LINEUP_T + 1.35 + 0.022 * k)

    # slate
    place(bus, whoosh(0.7, [300, 1100, 400], 0.0, 0.0, db(-20), 60), SLATE_T - 0.05)
    place(bus, reverse_swell(0.4, db(-20), 61), SLATE_T + 0.35 - 0.4)
    place(bus, boom(db(-13), 62, 1.6, 80, 40), SLATE_T + 0.35)
    place(bus, shimmer(db(-17), 63), SLATE_T + 0.95)
    place(bus, pop(db(-24), 820, 560), SLATE_T + 1.42)

    # master: gentle glue, no harsh peaks, short fade so the loop is clean
    t = np.arange(N) / SR
    bus *= np.clip((DUR - t) / 0.35, 0, 1)[:, None]
    bus = sos_filter(bus, 'lowpass', 14000)
    peak = np.abs(bus).max()
    bus = np.tanh(bus / peak * 1.25) / np.tanh(1.25) * db(-1.5)
    os.makedirs(P('out'), exist_ok=True)
    wavfile.write(P('out', 'soundtrack.wav'), SR, (bus * 32767).astype(np.int16))
    print('wrote out/soundtrack.wav')


if __name__ == '__main__':
    main()
