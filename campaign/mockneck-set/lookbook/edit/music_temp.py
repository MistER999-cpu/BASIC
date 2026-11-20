#!/usr/bin/env python3
"""Original temp score + sound design for a lookbook part, locked to the part's beat grid.

A minimal 90 BPM fashion beat (kick, clap, swung hats, sub, FM electric piano, soft pad) written
for this edit, so it carries no third-party rights. Sound design follows the cut list: shutter on
every pose flick, whooshes into each zoom-dive, a thump on each landing, pass-by whooshes, a
shimmer under the masthead.

    python3 campaign/mockneck-set/lookbook/edit/music_temp.py --part noir --out mix.wav --sfx-only sfx.wav
"""
import os
import sys
import argparse
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'campaign', 'mockneck-set', 'edit'))

import parts as P                                    # noqa: E402
import audio_mix as am                               # noqa: E402  shared SFX generators

SR = am.SR
FPS = P.FPS
SPB = 60.0 / P.BPM                                   # seconds per beat
rng = np.random.default_rng(21)


def tb(b):
    """Seconds of beat b (beat 0 = first downbeat)."""
    return P.B(b) / FPS


SHIFT = 0


def midi(m):
    return 440.0 * 2 ** ((m + SHIFT - 69) / 12)


def place(buf, x, t, gain_db=0.0):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    i0 = int(round(t * SR))
    if i0 >= len(buf):
        return
    if i0 < 0:
        x = x[-i0:]
        i0 = 0
    i1 = min(len(buf), i0 + len(x))
    buf[i0:i1] += x[:i1 - i0] * am.db(gain_db)


# ------------------------------------------------------------------ instruments
def kick(vel=1.0):
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    f = 47 + 125 * np.exp(-t / 0.030)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.32)
    click = am.highpass(rng.standard_normal(n), 2500) * np.exp(-t / 0.0025) * 0.22
    x = np.tanh((body + click) * 1.7) / np.tanh(1.7)
    return x * vel


def clap(vel=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    env = np.zeros(n)
    for d in (0.0, 0.010, 0.021):
        i = int(d * SR)
        env[i:] += np.exp(-t[:n - i] / 0.006)
    i = int(0.026 * SR)
    env[i:] += 0.55 * np.exp(-t[:n - i] / 0.09)
    x = am.bandpass(rng.standard_normal(n), 950, 5200) * env
    x /= np.abs(x).max() + 1e-9
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.045) * 0.35
    return (x + body) * vel


def hat(vel=1.0, open_=False):
    n = int((0.42 if open_ else 0.09) * SR)
    t = np.arange(n) / SR
    x = am.highpass(rng.standard_normal(n), 7200, order=4)
    x *= np.exp(-t / (0.15 if open_ else 0.020))
    return x / (np.abs(x).max() + 1e-9) * vel


def shaker(vel=1.0):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    x = am.bandpass(rng.standard_normal(n), 3500, 9500)
    x *= np.minimum(1, t / 0.012) * np.exp(-t / 0.035)
    return x / (np.abs(x).max() + 1e-9) * vel


def sub(freq, dur, vel=1.0):
    n = int((dur + 0.12) * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.18 * np.sin(4 * np.pi * freq * t)
    env = np.minimum(1, t / 0.006) * np.clip(1 - (t - dur) / 0.1, 0, 1)
    return np.tanh(1.4 * x * env) / np.tanh(1.4) * vel


def epiano(freqs, dur, vel=1.0, spread=0.010):
    """FM electric piano chord (1:1 carrier/modulator + a quick 14:1 tine), slight stereo detune."""
    n = int((dur + 1.6) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for i, f in enumerate(freqs):
        off = int(i * spread * SR)                    # gentle strum
        tt = t[:n - off]
        for ch, cents in ((0, -3.0), (1, 3.0)):
            ff = f * 2 ** (cents / 1200)
            I = 2.0 * np.exp(-tt / 0.32) + 0.22
            car = np.sin(2 * np.pi * ff * tt + I * np.sin(2 * np.pi * ff * tt))
            tine = np.sin(2 * np.pi * ff * 14 * tt) * np.exp(-tt / 0.025) * 0.07
            amp = np.minimum(1, tt / 0.004) * np.exp(-tt / 1.15) * np.clip(1 - (tt - dur) / 0.35, 0, 1)
            out[off:, ch] += (car + tine) * amp
    out = am.lowpass(out, 5200)
    return out / len(freqs) * vel


def pad(freqs, dur, vel=1.0, fc=1400.0):
    n = int((dur + 1.2) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for f0 in freqs:
        for det in (-0.006, 0.0, 0.006):
            for ch in (0, 1):
                f = f0 * (1 + det + (0.0015 if ch else -0.0015))
                for h in range(1, 12):
                    fh = f * h
                    if fh > 7000:
                        break
                    out[:, ch] += np.sin(2 * np.pi * fh * t + rng.uniform(0, 6.283)) * (1.0 / h) * np.exp(-fh / fc)
    env = np.minimum(1, t / 0.55) * np.clip(1 - (t - dur) / 0.9, 0, 1)
    out *= env[:, None]
    return out / (np.abs(out).max() + 1e-9) * vel


def cymbal_swell(length):
    n = int(length * SR)
    x = am.highpass(am.pink(n), 5000)
    x *= (np.linspace(0, 1, n) ** 3)[:, None]
    return x / (np.abs(x).max() + 1e-9)


def crash(length=2.0):
    n = int(length * SR)
    t = np.arange(n) / SR
    x = am.highpass(am.pink(n), 3800) * np.exp(-t / 0.7)[:, None]
    return x / (np.abs(x).max() + 1e-9)


# ------------------------------------------------------------------ score
DM9 = [57, 60, 64, 65]          # A3 C4 E4 F4 over D
BBMAJ7 = [58, 62, 65, 69]       # Bb3 D4 F4 A4
GM7 = [55, 58, 62, 65]          # G3 Bb3 D4 F4
A7SUS = [55, 57, 62, 64]        # G3 A3 D4 E4
FINAL = [57, 60, 64, 65, 74]    # Dm9 + D5


GAIN = dict(kick=-5.0, clap=-3.0, hats=0.0, shaker=-10.0, sub=-17.0, keys=3.0, pad=-7.0, fx=-12.0, verb=-3.0)


def stems(n):
    st = {k: np.zeros((n, 2)) for k in ('kick', 'clap', 'hats', 'shaker', 'sub', 'keys', 'pad', 'fx', 'send')}
    kick_env = np.zeros(n)

    def k(b, vel=1.0):
        place(st['kick'], kick(vel), tb(b))
        i0 = int(tb(b) * SR)
        e = np.exp(-np.arange(int(0.35 * SR)) / (0.12 * SR)) * vel
        seg = kick_env[i0:i0 + len(e)]
        kick_env[i0:i0 + len(e)] = np.maximum(seg, e[:len(seg)])

    for b in (0, 2.5):
        k(b)
    for bar in (4, 8):
        for s_ in (0, 1.5, 2.5):
            k(bar + s_)
    k(8 + 3.25, 0.7)
    k(12)
    k(13, 0.85)
    k(14, 0.6)
    k(15, 1.0)
    for b in (1, 3, 5, 7, 9, 11, 13):
        x = clap(0.9 if b != 13 else 0.7)
        place(st['clap'], x, tb(b))
        place(st['send'], x, tb(b), -6)
    vel_pat = [1.0, 0.32, 0.62, 0.36]
    b = 2.0
    while b < 13.0 - 1e-6:
        step = int(round((b % 1) * 4))
        swing = 0.010 if step % 2 else 0.0
        open_ = abs((b % 4) - 3.5) < 1e-6 and b > 4
        place(st['hats'], np.outer(hat(vel_pat[step], open_), [0.82, 1.0]), tb(b) + swing, 0 if not open_ else -4)
        b += 0.25
    b = 4.5
    while b < 12:
        place(st['shaker'], np.outer(shaker(0.8), [1.0, 0.7]), tb(b) + 0.006)
        b += 1.0
    for b0, b1, note in ((0, 2.5, 38), (2.5, 4, 38), (4, 6.5, 38), (6.5, 7.5, 38), (7.5, 8, 36),
                         (8, 10.5, 34), (10.5, 12, 34), (12, 13.5, 31), (13.5, 15, 33), (15, 17, 38)):
        place(st['sub'], sub(midi(note), (b1 - b0) * SPB * 0.95, 0.9), tb(b0))
    for b0, dur, ch, vel in ((0, 1.25, DM9, 1.0), (1.5, 0.5, DM9, 0.7), (4, 1.25, DM9, 1.0), (5.5, 0.5, DM9, 0.7),
                             (7.5, 0.5, BBMAJ7, 0.8), (8, 1.25, BBMAJ7, 1.0), (9.5, 0.5, BBMAJ7, 0.7),
                             (12, 1.4, GM7, 1.0), (13.5, 1.0, A7SUS, 0.85), (15, 2.5, FINAL, 1.0)):
        x = epiano([midi(m) for m in ch], dur * SPB, vel)
        place(st['keys'], x, tb(b0))
        place(st['send'], x, tb(b0), -4)
    for b0, b1, ch, fc in ((0, 4, DM9, 900), (4, 8, DM9, 1300), (8, 12, BBMAJ7, 1800), (12, 13.5, GM7, 2200),
                           (13.5, 15, A7SUS, 2200), (15, 17, FINAL[:4], 1600)):
        place(st['pad'], pad([midi(m) for m in ch], (b1 - b0) * SPB, 1.0, fc), tb(b0))
    place(st['fx'], cymbal_swell(tb(0)), 0.0)
    place(st['fx'], crash(2.2), tb(0), -2)
    place(st['fx'], crash(2.0), tb(8), -4)
    place(st['send'], crash(1.0), tb(15), -8)
    duck = 1 - 0.35 * np.clip(kick_env, 0, 1)
    for key in ('sub', 'keys', 'pad'):
        st[key] *= duck[:, None]
    return st


def score(n, gains=None):
    g = dict(GAIN, **(gains or {}))
    st = stems(n)
    ir = am.reverb_ir(2.6, 2.1)
    wet = signal.fftconvolve(st.pop('send'), ir, axes=0)[:n]
    out = wet * am.db(g['verb'])
    for key, x in st.items():
        out += x * am.db(g[key])
    return out


def design(n):
    """Sound design taken straight from the cut list."""
    sfx = np.zeros((n, 2))
    spec = P.PARTS[PART]
    for seg in spec['segments']:
        t0 = seg['f0'] / FPS
        if seg.get('strobe'):
            place(sfx, am.shutter(), t0, -11 + rng.uniform(-1.5, 1.5))
        if seg.get('dive'):
            land = seg['f1'] / FPS
            w, a = am.whoosh(0.20, 0.16, 300, 5200)
            place(sfx, w, land - a / SR, -9)
        if seg.get('land'):
            place(sfx, am.impact(0.9, 82, 40, 0.16, click=False), t0, -12)
            place(sfx, am.swish(0.5), t0 + 0.05, -16)
        if seg.get('masthead'):
            place(sfx, am.shimmer(1.3, 3000), t0 + 0.08, -20)
            place(sfx, am.impact(1.2, 60, 34, 0.35, click=False), t0, -13)
        if seg.get('whoosh_at') is not None:
            w, a = am.whoosh(0.30, 0.30, 160, 2800, pan_from=0.9, pan_to=-0.9)
            place(sfx, w, seg['whoosh_at'] / FPS - a / SR, -5)
        for key in ('passin', 'passout'):
            if key in seg:
                a0, a1 = seg[key]
                w, a = am.whoosh((a1 - a0) / FPS * 0.55, (a1 - a0) / FPS * 0.6, 160, 3000, pan_from=0.9, pan_to=-0.9)
                place(sfx, w, (a0 + (a1 - a0) * 0.5) / FPS - a / SR, -6)
    # final hit, logo shimmer
    place(sfx, am.impact(2.0, 62, 32, 0.6), tb(15), -9)
    if spec.get('endlogo'):
        place(sfx, am.shimmer(1.0, 3300), spec['endlogo'][0] / FPS + 0.04, -19)
    return sfx


PART = 'noir'


def main():
    global PART
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', default='noir')
    ap.add_argument('--out', required=True)
    ap.add_argument('--sfx-only')
    a = ap.parse_args()
    PART = a.part
    global SHIFT
    SHIFT = P.PARTS[PART].get('key', 0)
    dur = P.PARTS[PART]['end'] / FPS
    n = int(round(dur * SR))
    mus = score(n)
    sfx = design(n)
    fade = int(0.30 * SR)
    for x in (mus, sfx):
        x[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    mix, loud = am.master(mus + sfx * am.db(-1))
    am.write_wav(a.out, mix)
    import pyloudnorm as pyln
    print(f'mix {dur:.2f}s: {pyln.Meter(SR).integrated_loudness(mix):.1f} LUFS, peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS')
    if a.sfx_only:
        s, _ = am.master(sfx.copy(), target_lufs=-18.0)
        am.write_wav(a.sfx_only, s)
        print('sfx-only written')


if __name__ == '__main__':
    main()
