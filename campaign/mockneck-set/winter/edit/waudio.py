#!/usr/bin/env python3
"""Sound for the BASIC winter film: the reference's own section of the supplied track, cut so
beat 0 lands on the first frame, a "freeze" on the last bars (the music is low-passed into the
frost and rings out), and synthesised winter sound design on the edit's events.

    python3 campaign/mockneck-set/winter/edit/waudio.py --cut 20 --music <track.mp3> --out mix.wav [--sfx-only sfx.wav]
"""
import os
import sys
import argparse
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'edit'))
import audio_mix as am      # noqa: E402  shared generators (whoosh, impact, shimmer, reverb, master)
import wedit as E           # noqa: E402  the edit's frame numbers

SR = am.SR
TRACK_START = 5.2112 - 0.010             # beat 0 of the grid, 10 ms early so the transient is whole
rng = np.random.default_rng(41)


def tf(frame):
    return frame / E.FPS


def place(buf, x, t, gain_db=0.0):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    am.place(buf, x, t, gain_db)


def place_peak(buf, x, n_pre, t_peak, gain_db=0.0):
    am.place(buf, x, t_peak - n_pre / SR, gain_db)


# ------------------------------------------------------------------ winter sound design
def ice_tick(f0=3200, tau=0.05):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f0 * t) + 0.5 * np.sin(2 * np.pi * f0 * 2.71 * t) * np.exp(-t / (tau * 0.4))) * np.exp(-t / tau)
    return x / np.abs(x).max()


def airy(length=0.45, lo=2000, hi=9000, pan_from=-0.3, pan_to=0.3):
    n = int(length * SR)
    x = am.bandpass(am.pink(n)[:, 0], lo, hi)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2 * np.linspace(0.6, 1.0, n)
    x = x * e
    return am.pan(x / (np.abs(x).max() + 1e-9), np.linspace(pan_from, pan_to, n))


def crunch(length=0.22):
    """Boot on fresh snow: a dense burst of tiny grains, band-limited, quick attack."""
    n = int(length * SR)
    x = np.zeros(n)
    k = int(380 * length)
    pos = np.sort(rng.integers(0, n - 200, k))
    for p in pos:
        g = rng.uniform(0.2, 1.0) * np.exp(-p / (0.07 * SR))
        m = rng.integers(20, 90)
        x[p:p + m] += rng.standard_normal(m) * g * np.exp(-np.arange(m) / (m / 4))
    x = am.bandpass(x, 700, 7000)
    body = am.lowpass(rng.standard_normal(n), 300) * np.exp(-np.arange(n) / (0.03 * SR)) * 0.6
    x = x + body
    return x / (np.abs(x).max() + 1e-9)


def charm_jingle():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for d in (0.0, 0.055, 0.12):
        i = int(d * SR)
        tt = t[:n - i]
        for fr, tau, a in ((3150, 0.16, 1.0), (4710, 0.11, 0.7), (6330, 0.07, 0.5), (8890, 0.05, 0.35)):
            x[i:] += a * np.sin(2 * np.pi * fr * rng.uniform(0.98, 1.02) * tt + rng.uniform(0, 6)) * np.exp(-tt / tau) \
                * (1 - 0.35 * (d > 0))
    return x / np.abs(x).max()


def rustle(length=0.55):
    n = int(length * SR)
    x = am.bandpass(am.pink(n)[:, 0], 400, 4200)
    mod = 0.6 + 0.4 * np.abs(np.sin(np.linspace(0, 9, n) + rng.uniform(0, 3)))
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.4
    x = x * mod * e
    return am.pan(x / (np.abs(x).max() + 1e-9), np.linspace(0.25, -0.15, n))


def frost_crackle(length):
    """Ice crystallising: granular ticks thickening toward the end, over a rising air sweep."""
    n = int(length * SR)
    out = np.zeros((n, 2))
    t = 0.0
    while t < length:
        dens = 18 + 260 * (t / length) ** 2.2
        t += rng.exponential(1 / dens)
        i = int(t * SR)
        if i >= n - 400:
            break
        m = rng.integers(30, 260)
        g = rng.uniform(0.15, 1.0) * (0.35 + 0.65 * t / length)
        grain = am.highpass(rng.standard_normal(m), 2800) * np.exp(-np.arange(m) / (m / 5)) * g
        p = rng.uniform(-0.9, 0.9)
        a = (p + 1) * np.pi / 4
        out[i:i + m, 0] += grain * np.cos(a)
        out[i:i + m, 1] += grain * np.sin(a)
    out /= np.abs(out).max() + 1e-9
    air = am.sweep_filter(am.pink(n), 900, 7500, q=1.8)
    air = air / (np.abs(air).max() + 1e-9) * (np.linspace(0, 1, n) ** 2.4)[:, None]
    return out * 0.8 + air * 0.55


def ice_bell(base=1046.5):
    n = int(3.2 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for ratio, tau, a in ((1.0, 1.6, 1.0), (2.76, 0.9, 0.55), (5.40, 0.5, 0.35), (8.93, 0.28, 0.22), (2.0, 1.2, 0.3)):
        x += a * np.sin(2 * np.pi * base * ratio * t + rng.uniform(0, 6)) * np.exp(-t / tau)
    x *= np.minimum(1, t / 0.004)
    x /= np.abs(x).max()
    return am.pan(x, np.sin(2 * np.pi * 0.35 * t) * 0.35)


def breath(length=1.0):
    """A soft exhale into cold air: breathy noise with two vowel-ish resonances."""
    n = int(length * SR)
    x = am.pink(n)[:, 0]
    x = 0.6 * am.bandpass(x, 500, 900) + 0.5 * am.bandpass(x, 1200, 2600) + 0.25 * am.highpass(x, 3000)
    t = np.arange(n) / SR
    e = np.minimum(1, t / 0.14) * np.exp(-np.maximum(0, t - 0.14) / 0.32)
    x = x * e
    return am.pan(x / (np.abs(x).max() + 1e-9), np.full(n, 0.05))


def wind(n):
    x = am.pink(n)
    x = am.bandpass(x, 150, 1400)
    t = np.arange(n) / SR
    lfo = 0.55 + 0.25 * np.sin(2 * np.pi * 0.13 * t) + 0.2 * np.sin(2 * np.pi * 0.31 * t + 1.3)
    return x / (np.abs(x).max() + 1e-9) * lfo[:, None]


def build_sfx(n):
    sfx = np.zeros((n, 2))
    send = np.zeros((n, 2))
    # the three bands landing, and their words written on
    for k, (_, fr, *_r) in enumerate(E.BANDS):
        t0 = tf(fr)
        place(sfx, am.shutter(), t0, -13)
        place(sfx, am.impact(0.6, 95, 48, 0.12, click=False), t0, -18)
        x = ice_tick(3000 + 400 * k)
        place(sfx, x, t0 + 0.01, -25)
        place(send, x, t0 + 0.01, -22)
        place(sfx, airy(0.48, pan_from=-0.35 + 0.3 * k, pan_to=0.0 + 0.3 * k), tf(fr + 2), -29)
    # walk-past: big whoosh with cloth and a body passing the lens, peak on beat 4
    w, pre = am.whoosh(0.42, 0.46, 140, 3200, pan_from=-0.95, pan_to=0.95)
    place_peak(sfx, w, pre, tf(E.B(4)), -6)
    place_peak(sfx, am.swish(0.55), int(0.27 * SR), tf(E.B(4)), -15)
    place(sfx, am.impact(0.7, 60, 34, 0.15, click=False), tf(E.B(4)) - 0.02, -20)
    # cuts
    for f in E.C.swish:
        place(sfx, am.swish(0.32), tf(f) - 0.16, -21)
    # rotation whip on beat 9
    w, pre = am.whoosh(0.30, 0.34, 300, 6500, pan_from=0.85, pan_to=-0.85)
    place_peak(sfx, w, pre, tf(E.WHIP), -7)
    place(sfx, am.impact(0.8, 82, 40, 0.18), tf(E.WHIP), -16)
    # boots on snow under the turned walk
    for f in E.C.crunch:
        place(sfx, np.stack([crunch(), crunch() * 0.9], 1), tf(f), -19)
    # bag charm on the hip shot, fabric as the hand goes into the pocket
    place(sfx, charm_jingle(), tf(E.C.charm) + 0.05, -24)
    place(send, charm_jingle(), tf(E.C.charm) + 0.05, -26)
    place(sfx, rustle(0.6), tf(E.C.rustle), -19)
    # her breath in the cold, and the punch-in to her smile
    if E.C.breath is not None:
        x = breath(1.1)
        place(sfx, x, tf(E.C.breath), -23)
        place(send, x, tf(E.C.breath), -24)
    if E.C.jump is not None:
        place(sfx, am.swish(0.30), tf(E.C.jump) - 0.15, -19)
        place(sfx, am.impact(0.6, 90, 45, 0.10, click=False), tf(E.C.jump), -21)
    # frost growing over the last shot, crystallising into the hit on beat 15
    L = tf(E.END) - tf(E.FROST0)
    place(sfx, frost_crackle(L), tf(E.FROST0), -14)
    place(send, frost_crackle(L), tf(E.FROST0), -20)
    tE = tf(E.END)
    place(sfx, am.impact(2.2, 64, 30, 0.6), tE, -9)
    bell = ice_bell()
    place(sfx, bell, tE, -16)
    place(send, bell, tE, -12)
    place(sfx, am.shimmer(1.6, 3200), tE + 0.02, -20)
    for k in range(8):
        tt = tE + 0.04 + rng.uniform(0, 0.42)
        place(sfx, ice_tick(rng.uniform(3800, 6200), 0.03), tt, -28)
    place(sfx, am.shimmer(1.2, 4200), tf(E.SHINE), -21)
    place(send, am.shimmer(1.2, 4200), tf(E.SHINE), -24)
    # cold air under everything, opening up as the music freezes
    wd = wind(n)
    t = np.arange(n) / SR
    g = am.db(-34) + (am.db(-25) - am.db(-34)) * np.clip((t - tf(E.FROST0)) / 1.5, 0, 1)
    sfx += wd * g[:, None]
    return sfx, send


def freeze(music, t0, t1):
    """Low-pass the music from t0 to t1 (frost closing over the sound), STFT masking."""
    out = music.copy()
    i0 = int(t0 * SR)
    seg = music[i0:]
    nper = 2048
    for c in range(2):
        f, tt, Z = signal.stft(seg[:, c], fs=SR, nperseg=nper, noverlap=nper * 3 // 4)
        q = np.clip(tt / (t1 - t0), 0, 1)
        fc = 16000 * (380 / 16000) ** (q ** 0.8)
        gmask = 1 / np.sqrt(1 + (f[:, None] / fc[None, :]) ** 4)
        _, y = signal.istft(Z * gmask, fs=SR, nperseg=nper, noverlap=nper * 3 // 4)
        y = y[:len(seg)]
        if len(y) < len(seg):
            y = np.pad(y, (0, len(seg) - len(y)))
        out[i0:, c] = y
    # 50 ms crossfade into the filtered part
    xf = int(0.05 * SR)
    r = np.linspace(0, 1, xf)[:, None]
    out[i0:i0 + xf] = music[i0:i0 + xf] * (1 - r) + out[i0:i0 + xf] * r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cut', default='20', choices=sorted(E.CUTS))
    ap.add_argument('--music', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sfx-only')
    a = ap.parse_args()
    E.configure(a.cut)
    DUR = E.N_FRAMES / E.FPS
    n = int(round(DUR * SR))
    mus = am.load_music(a.music, TRACK_START, DUR + 0.5)[:n]
    if len(mus) < n:
        mus = np.pad(mus, ((0, n - len(mus)), (0, 0)))
    fi = int(0.010 * SR)
    mus[:fi] *= np.linspace(0, 1, fi)[:, None]
    tS = tf(E.C.freeze)
    mus = freeze(mus, tS, DUR)
    t = np.arange(n) / SR
    mus *= (1 - 0.45 * np.clip((t - tS) / (DUR - tS), 0, 1))[:, None]
    # the frozen music rings out in a long cold reverb
    tail_src = mus.copy()
    tail_src[:int((tS - 0.6) * SR)] = 0
    ir = am.reverb_ir(4.0, 3.6)
    tail = signal.fftconvolve(tail_src, ir, axes=0)[:n]
    # small duck under the walk-past and the logo hit
    duck = np.ones(n)
    for tc, depth, wdt in ((tf(E.B(4)), 0.22, 0.35), (tf(E.END), 0.30, 0.5)):
        duck *= 1 - depth * np.exp(-0.5 * ((t - tc) / wdt) ** 2)
    mus *= duck[:, None]
    sfx, send = build_sfx(n)
    verb = signal.fftconvolve(send, am.reverb_ir(3.2, 2.8), axes=0)[:n]
    mix = mus + tail * am.db(-13) + sfx * am.db(-1) + verb * am.db(-6)
    fo = int(0.35 * SR)
    mix[-fo:] *= (np.linspace(1, 0, fo) ** 1.6)[:, None]
    mix, loud = am.master(mix)
    am.write_wav(a.out, mix)
    import pyloudnorm as pyln
    print(f'mix {DUR:.2f}s: in {loud:.1f} LUFS -> {pyln.Meter(SR).integrated_loudness(mix):.1f} LUFS, '
          f'peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS')
    if a.sfx_only:
        s, _ = am.master(sfx + verb * am.db(-6), target_lufs=-18.0)
        am.write_wav(a.sfx_only, s)


if __name__ == '__main__':
    main()
