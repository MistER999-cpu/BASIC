#!/usr/bin/env python3
"""Sound for the reel: a 120 BPM groove plus sticker foley, locked to the cuts.

    python3 tools/audio.py      # -> build/audio_full.wav, build/audio_sfx.wav

Everything is synthesised here, so the track is cleared for paid ads. The
chords walk down - Fmaj7, Em7, Dm7, Cmaj7 - one bar per season, the
temperature falling with them; the groove drops out for half a beat before
« Jamais. » and resolves on Cmaj9 under the logo.
The music and the foley are written as separate files so the music can be
swapped for a Meta Sound Collection track without losing the slaps.
"""
import json, os, sys
import numpy as np
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
sys.path.insert(0, os.path.join(ROOT, 'tools'))

SR = 48000
DUR = 13.5
BEAT = 0.5
N = int(SR * DUR)
rng = np.random.default_rng(5)


def t_(d):
    return np.arange(int(SR * d)) / SR


def env_exp(d, tau, attack=0.002):
    t = t_(d)
    e = np.exp(-t / tau)
    a = np.clip(t / max(attack, 1e-5), 0, 1)
    return e * a


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype='bandpass', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype='highpass', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype='lowpass', fs=SR, output='sos'), x)


def add(buf, x, t0, gain=1.0, pan=0.0):
    i = int(round(t0 * SR))
    if i >= len(buf):
        return
    x = x[:max(0, len(buf) - i)]
    if i < 0:
        x = x[-i:]
        i = 0
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.414
    buf[i:i + len(x), 1] += x * gain * r * 1.414


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# ---------------------------------------------------------------- drums ----
def kick():
    d = 0.42
    t = t_(d)
    f = 48 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_exp(d, 0.16, 0.001)
    click = hp(rng.standard_normal(len(t)), 2500) * env_exp(d, 0.004, 0.0005) * 0.25
    return np.tanh((body + click) * 1.6) * 0.9


def clap():
    d = 0.4
    n = rng.standard_normal(int(SR * d))
    e = np.zeros_like(n)
    for k, o in enumerate([0.0, 0.009, 0.018]):
        i = int(o * SR)
        seg = env_exp(d, 0.006 if k < 2 else 0.11, 0.0005)[:len(e) - i]
        e[i:i + len(seg)] += seg
    return bp(n * e, 900, 3200) * 0.9


def hat(open_=False):
    d = 0.3 if open_ else 0.08
    n = rng.standard_normal(int(SR * d))
    x = hp(n, 7000) * env_exp(d, 0.09 if open_ else 0.018, 0.0005)
    return x * 0.5


def shaker():
    d = 0.09
    n = rng.standard_normal(int(SR * d))
    t = t_(d)
    e = np.clip(t / 0.012, 0, 1) * np.exp(-t / 0.03)
    return bp(n, 5000, 11000) * e * 0.3


# -------------------------------------------------------------- tonal ------
def ep_note(freq, d=1.2, vel=1.0, bright=1.0):
    """FM electric piano: a tine that softens as it rings."""
    t = t_(d)
    idx = (1.8 * bright) * np.exp(-t / 0.25) + 0.25
    mod = np.sin(2 * np.pi * freq * t) * idx
    car = np.sin(2 * np.pi * freq * t + mod)
    tine = np.sin(2 * np.pi * freq * 14 * t) * np.exp(-t / 0.02) * 0.08 * bright
    e = env_exp(d, 0.55, 0.004)
    return (car + tine) * e * vel


def chord(notes, d=1.2, vel=0.22, bright=1.0):
    out = np.zeros(int(SR * d))
    for k, n in enumerate(notes):
        out += ep_note(midi(n), d, vel * (0.9 if k else 1.0), bright)
    return out


def bass(note, d=0.24):
    f = midi(note)
    t = t_(d)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    e = np.clip(t / 0.004, 0, 1) * np.exp(-t / 0.12)
    return np.tanh(x * e * 1.4) * 0.6


def pad(notes, d, vel=0.06):
    t = t_(d)
    out = np.zeros(len(t))
    for n in notes:
        f = midi(n)
        for det in (-0.08, 0.0, 0.08):
            out += signal.sawtooth(2 * np.pi * f * (1 + det / 100) * t) / 3
    out = lp(out, 1400, 2)
    a = np.clip(t / 0.25, 0, 1) * np.clip((d - t) / 0.4, 0, 1)
    return out * a * vel


def bell(freq, d=2.2, vel=0.12):
    t = t_(d)
    x = np.sin(2 * np.pi * freq * t + 0.9 * np.sin(2 * np.pi * freq * 3.5 * t) * np.exp(-t / 0.4))
    return x * env_exp(d, 0.7, 0.002) * vel


# ---------------------------------------------------------------- foley ----
def slap_sfx(weight=1.0):
    """A vinyl sticker smacked flat: snap, body, a little paper crackle."""
    d = 0.22
    n = rng.standard_normal(int(SR * d))
    snap = bp(n, 1400, 5200) * env_exp(d, 0.016 * weight, 0.0004)
    t = t_(d)
    f = 95 + 120 * np.exp(-t / 0.02)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 0.05 * weight, 0.0008) * 0.6
    crackle = np.zeros(len(t))
    for _ in range(5):
        i = int(rng.uniform(0.012, 0.07) * SR)
        crackle[i:i + 60] += rng.standard_normal(60) * rng.uniform(0.15, 0.35)
    crackle = bp(crackle, 2500, 9000)
    return np.tanh((snap * 0.9 + body + crackle) * 1.3) * 0.75


def tick_sfx():
    d = 0.09
    n = rng.standard_normal(int(SR * d))
    return bp(n, 2500, 8500) * env_exp(d, 0.012, 0.0003) * 0.55


def whoosh(d=0.32):
    """Air pulled past the lens, swelling into the cut."""
    n = rng.standard_normal(int(SR * d))
    t = t_(d)
    u = t / d
    out = np.zeros_like(n)
    hop = 512
    for i in range(0, len(n), hop):
        seg = n[i:i + hop * 2]
        fc = 350 + 3800 * (u[i] ** 2)
        out[i:i + len(seg)] += bp(seg, fc * 0.6, min(fc * 1.6, SR / 2 - 100), 1) * np.hanning(len(seg))
    e = (u ** 2.2) * np.clip((1 - u) / 0.06, 0, 1)
    return out * e * 0.5


def impact():
    d = 1.6
    t = t_(d)
    f = 34 + 60 * np.exp(-t / 0.08)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 0.55, 0.002)
    n = rng.standard_normal(len(t))
    crash = hp(n, 3000) * env_exp(d, 0.45, 0.001) * 0.18
    return np.tanh((sub * 1.1 + crash) * 1.2)


def riser(d):
    n = rng.standard_normal(int(SR * d))
    t = t_(d)
    x = hp(n, 1500) * (t / d) ** 3 * 0.35
    return x


# ----------------------------------------------------------------- reverb --
def reverb(x, decay=1.4, mix=0.25, pre=0.012):
    L = int(SR * decay)
    t = np.arange(L) / SR
    ir = np.zeros((L, 2))
    for c in range(2):
        n = rng.standard_normal(L)
        ir[:, c] = lp(n, 6000, 1) * np.exp(-t / (decay / 6.9))
    ir[:int(pre * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    wet = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], -1)
    return x + wet * mix


# ------------------------------------------------------------------ score --
CHORDS = [  # (start, end, voicing, bass root)
    (0.0, 2.0, [53, 57, 60, 64], 41),     # Fmaj7
    (2.0, 4.0, [52, 55, 59, 62], 40),     # Em7
    (4.0, 6.0, [50, 53, 57, 60], 38),     # Dm7
    (6.0, 8.0, [48, 52, 55, 59], 36),     # Cmaj7
    (8.0, 9.5, [45, 52, 55, 60], 33),     # Am7 - the break and « Jamais. »
    (9.5, 10.5, [53, 57, 60, 64], 41),    # Fmaj7 - the four colours
    (10.5, 12.0, [55, 59, 62, 64], 43),   # G6
    (12.0, 13.5, [48, 52, 55, 59, 62], 36),  # Cmaj9 - the logo
]


def chord_at(t):
    for a, b, v, r in CHORDS:
        if a <= t < b:
            return v, r
    return CHORDS[-1][2], CHORDS[-1][3]


def music():
    buf = np.zeros((N, 2))
    k, c = kick(), clap()
    hc, ho, sh = hat(), hat(True), shaker()
    beats = np.arange(0, 12.0 + 1e-9, BEAT)
    for b in beats:
        if 8.0 <= b < 8.5:           # the drop-out before « Jamais. »
            continue
        half_time = 8.5 <= b < 9.5
        if not half_time or b in (8.5,):
            add(buf, k, b, 0.85 if b >= 2.5 else 0.6)
        beat_in_bar = int(round(b / BEAT)) % 4
        if beat_in_bar in (1, 3) and not half_time and b >= 0.5:
            add(buf, c, b, 0.34, 0.05)
        if not half_time:
            add(buf, ho if beat_in_bar == 3 and b >= 2.5 else hc, b + BEAT / 2, 0.30 if b >= 2.5 else 0.2, 0.3)
    for s in np.arange(0, 12.0, BEAT / 4):
        if 8.0 <= s < 9.5:
            continue
        acc = 1.0 if int(round(s / (BEAT / 4))) % 2 else 0.55
        add(buf, sh, s + (0.012 if int(round(s / (BEAT / 4))) % 2 else 0), 0.20 * acc, -0.35)

    keys = np.zeros((N, 2))
    for a, b, v, r in CHORDS:
        if a >= 12.0:
            add(keys, chord(v, 2.6, 0.24, 0.8), a, 1.0)
            continue
        if 8.0 <= a < 9.5:
            add(keys, pad(v, 1.0, 0.07), 8.5, 1.0)
            continue
        add(keys, chord(v, 1.0, 0.13, 0.6), a, 1.0)
        for off in (0.75, 1.75):
            if a + off < b:
                add(keys, chord(v, 0.5, 0.20, 1.0), a + off, 1.0, 0.1)
    keys = reverb(keys, 1.6, 0.28)

    bs = np.zeros((N, 2))
    for e8 in np.arange(0, 12.0, BEAT / 2):
        if 8.0 <= e8 < 8.5 or 8.75 <= e8 < 9.5:
            continue
        v, r = chord_at(e8)
        step = int(round(e8 / (BEAT / 2))) % 4
        note = r + (12 if step == 2 else 0)
        if step in (0, 2, 3):
            add(bs, bass(note, 0.22 if step else 0.3), e8, 0.5 if step != 3 else 0.32)
    add(bs, bass(24, 1.4), 12.0, 0.45)

    tonal = keys + bs
    tonal[:, :] += 0
    add(tonal, bell(midi(84), 2.6, 0.08), 12.0, 1.0, 0.25)
    add(tonal, bell(midi(91), 2.4, 0.05), 12.18, 1.0, -0.3)

    rise = riser(0.5)
    add(buf, rise, 8.0, 1.0)
    add(buf, impact(), 8.5, 0.55)
    return buf + tonal


def foley(evs):
    buf = np.zeros((N, 2))
    for t, kind in evs:
        if kind == 'slap':
            add(buf, slap_sfx(), t, 0.62, rng.uniform(-0.2, 0.2))
        elif kind == 'tick':
            add(buf, tick_sfx(), t, 0.55, rng.uniform(-0.3, 0.3))
        elif kind == 'cut':
            add(buf, whoosh(0.3), t - 0.3, 0.75)
            add(buf, slap_sfx(1.2), t, 0.72)
        elif kind == 'open':
            add(buf, slap_sfx(1.1), t + 0.01, 0.55)
        elif kind == 'punch':
            add(buf, slap_sfx(1.6), t, 0.9)
        elif kind == 'end':
            add(buf, whoosh(0.4), t - 0.4, 0.5)
    return buf


def duck(music_buf, evs, depth=0.35, dur=0.14):
    g = np.ones(N)
    for t, kind in evs:
        if kind in ('slap', 'cut', 'punch', 'open'):
            i = int(t * SR)
            L = int(dur * SR)
            seg = 1 - depth * np.exp(-np.arange(L) / (L / 3))
            g[i:i + L] = np.minimum(g[i:i + L], seg[:max(0, min(L, N - i))])
    g = signal.savgol_filter(g, 241, 2)
    return music_buf * g[:, None]


def master(x):
    x = hp(x.T, 28).T
    x = np.tanh(x * 1.15) / np.tanh(1.15)
    fade = np.ones(N)
    L = int(0.25 * SR)
    fade[-L:] = np.linspace(1, 0, L) ** 1.5
    x *= fade[:, None]
    x[:int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))[:, None]
    peak = np.abs(x).max()
    return x / peak * 0.89


def write_wav(path, x):
    from scipy.io import wavfile
    wavfile.write(path, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


def main():
    from render import events
    evs = events()
    m = music()
    f = foley(evs)
    full = master(duck(m, evs) * 0.62 + f)
    sfx = master(f * 0.9)
    write_wav(os.path.join(BUILD, 'audio_full_raw.wav'), full)
    write_wav(os.path.join(BUILD, 'audio_sfx_raw.wav'), sfx)
    print('events', len(evs))


if __name__ == '__main__':
    main()
