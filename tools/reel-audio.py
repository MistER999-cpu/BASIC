#!/usr/bin/env python3
"""Original soundtrack + sound design for tools/reel.py, synthesized from scratch
(no samples, no licensed music), so the brand owns it outright.

120 BPM deep house in A minor, one bar = 2 s = one 60-frame block of the reel:

    bars 1-2   intro: the groove plays muffled and opens as the loading bar
               fills (the music "comes into focus" with the picture); glitch
               bursts stutter and bit-crush it; chime at 100 %; riser + reverse
               cymbal into the drop on the first grid
    bars 3-10  grids: kick, clap, hats, bass, stabs and pluck build in layers;
               shutter clicks on every tile pop, whooshes on every snap,
               a soft swish under each text card, crash on each new grid
    bars 11-12 end card: drums stop, impact + open chord under the logo,
               three plucked notes as the three colourways pop in

Every event time comes from reel.timeline(), the same frames the video uses.
Called by tools/reel.py; standalone:  python3 tools/reel-audio.py out/x.wav
"""
import json
import os
import subprocess
import sys

import numpy as np

SR = 48000
BPM = 120
BEAT = 60 / BPM
STEP = BEAT / 4                      # 16th note
BAR = 4 * BEAT
TAIL = 3.0                           # render past the end so reverb tails exist

rng = np.random.default_rng(20261014)


# ---------------------------------------------------------------- DSP helpers

def t_axis(dur):
    return np.arange(int(round(dur * SR))) / SR


def noise(n):
    return rng.standard_normal(n)


def filt(x, lo=None, hi=None, order=2):
    """Zero-phase Butterworth-magnitude filter in the frequency domain."""
    x = np.asarray(x, np.float64)
    n = x.shape[0]
    pad = int(0.25 * SR)
    N = 1 << int(np.ceil(np.log2(n + pad)))
    f = np.fft.rfftfreq(N, 1 / SR)
    g = np.ones_like(f)
    if hi:
        g /= np.sqrt(1 + (f / hi) ** (2 * order))
    if lo:
        g /= np.sqrt(1 + (lo / np.maximum(f, 1e-6)) ** (2 * order))
    if x.ndim == 1:
        return np.fft.irfft(np.fft.rfft(x, N) * g, N)[:n]
    return np.fft.irfft(np.fft.rfft(x, N, axis=0) * g[:, None], N, axis=0)[:n]


SWEEP_BANK = [160, 260, 420, 680, 1100, 1800, 2900, 4700, 7600, 12000]


def sweep_lp(x, fc):
    """Time-varying low-pass: crossfade a bank of fixed filters by log cutoff.
    fc is a per-sample cutoff curve; values above the bank pass x unfiltered."""
    bank = [filt(x, hi=c, order=2) for c in SWEEP_BANK] + [x]
    edges = np.log(SWEEP_BANK + [24000])
    pos = np.interp(np.log(np.clip(fc, SWEEP_BANK[0], 24000)), edges, np.arange(len(bank)))
    i0 = np.floor(pos).astype(int).clip(0, len(bank) - 2)
    frac = (pos - i0)[:, None] if x.ndim == 2 else pos - i0
    out = np.zeros_like(x)
    for k in range(len(bank) - 1):
        m = i0 == k
        if m.any():
            fr = frac[m]
            out[m] = bank[k][m] * (1 - fr) + bank[k + 1][m] * fr
    return out


def env_adsr(n, a=0.003, d=0.1, s=0.7, r=0.03):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rn = int(r * SR)
    if rn and rn < n:
        e[-rn:] *= np.linspace(1, 0, rn)
    return e


def fade_edges(x, ms=2.0):
    k = max(1, int(ms * SR / 1000))
    x = x.copy()
    x[:k] *= np.linspace(0, 1, k) if x.ndim == 1 else np.linspace(0, 1, k)[:, None]
    x[-k:] *= np.linspace(1, 0, k) if x.ndim == 1 else np.linspace(1, 0, k)[:, None]
    return x


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def saw(freq, n, harmonics=40, phase=0.0):
    """Band-limited sawtooth (additive)."""
    t = np.arange(n) / SR
    k = np.arange(1, max(1, min(harmonics, int(SR / 2 / freq))) + 1)
    out = np.zeros(n)
    for h in k:
        out += np.sin(2 * np.pi * freq * h * t + phase * h) / h
    return out * 0.55


def pan_st(x, pan):
    th = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(th), x * np.sin(th)], axis=1) * np.sqrt(2)


class Bus:
    def __init__(self, dur):
        self.x = np.zeros((int(round(dur * SR)), 2))

    def add(self, sig, t, gain=1.0, pan=0.0):
        if sig.ndim == 1:
            sig = pan_st(sig, pan)
        i = int(round(t * SR))
        if i >= len(self.x):
            return
        if i < 0:
            sig, i = sig[-i:], 0
        n = min(len(sig), len(self.x) - i)
        self.x[i:i + n] += sig[:n] * gain


def reverb_ir(dur=2.2, decay=0.42, tone=6500, predelay=0.018):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ir = np.stack([noise(n), noise(n)], axis=1) * np.exp(-t / decay)[:, None]
    ir = filt(ir, lo=180, hi=tone)
    ir[: int(predelay * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(axis=0, keepdims=True)) * 0.9


def convolve(x, ir):
    n = len(x) + len(ir)
    N = 1 << int(np.ceil(np.log2(n)))
    X = np.fft.rfft(x, N, axis=0)
    Hh = np.fft.rfft(ir, N, axis=0)
    return np.fft.irfft(X * Hh, N, axis=0)[: len(x)]


def pingpong(x, time=0.375, fb=0.38, repeats=5):
    out = np.zeros_like(x)
    d = int(time * SR)
    mono = x.mean(axis=1)
    for k in range(1, repeats + 1):
        ch = (k + 1) % 2
        if d * k >= len(x):
            break
        out[d * k:, ch] += mono[:-d * k] * fb ** k
    return filt(out, lo=300, hi=3800)


# ---------------------------------------------------------------- instruments

def kick():
    t = t_axis(0.5)
    f = 54 + 110 * np.exp(-t / 0.028) + 60 * np.exp(-t / 0.004)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22)
    knock = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.018) * 0.35   # audible on phone speakers
    click = filt(noise(len(t)) * np.exp(-t / 0.0025), lo=1800) * 0.30
    x = np.tanh(1.9 * (body + knock + click)) / np.tanh(1.9)
    return fade_edges(x * np.minimum(1, t / 0.0012), 8)


def clap():
    t = t_axis(0.45)
    e = np.zeros_like(t)
    for d in (0.0, 0.011, 0.023):
        e += np.where(t >= d, np.exp(-(t - d) / 0.0045), 0)
    e += np.where(t >= 0.03, 0.75 * np.exp(-(t - 0.03) / 0.11), 0)
    return fade_edges(filt(noise(len(t)) * e, lo=850, hi=4200) * 2.2)


def hat(open_=False):
    t = t_axis(0.42 if open_ else 0.09)
    tone = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (317, 471, 563, 742, 891, 1053))
    x = filt(noise(len(t)) * 0.8 + tone * 0.12, lo=7200)
    return fade_edges(x * np.exp(-t / (0.14 if open_ else 0.022)), 3)


def shaker():
    t = t_axis(0.11)
    e = np.minimum(1, t / 0.007) * np.exp(-t / 0.045)
    return fade_edges(filt(noise(len(t)), lo=5200, hi=11000) * e)


def crash(dur=2.6):
    t = t_axis(dur)
    tone = sum(np.sin(2 * np.pi * f * t + rng.random() * 6) for f in (3120, 4370, 5260, 6810, 8150))
    x = filt(noise(len(t)) + tone * 0.15, lo=3600) * np.exp(-t / 0.85)
    return fade_edges(x, 20)


def reverse_cymbal(dur):
    c = crash(dur + 0.1)[: int(dur * SR)][::-1]
    t = t_axis(dur)
    return fade_edges(c * (t / dur) ** 1.5, 4)


def impact():
    t = t_axis(2.0)
    f = 32 + 34 * np.exp(-t / 0.25)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.75)
    thud = filt(noise(len(t)), hi=420) * np.exp(-t / 0.16) * 0.9
    return fade_edges(np.tanh(1.4 * (sub + thud)), 30)


def riser(dur):
    t = t_axis(dur)
    x = noise(len(t)) * (t / dur) ** 2
    fc = 500 * (14000 / 500) ** (t / dur)
    return fade_edges(sweep_lp(filt(x, lo=250), fc), 3)


def bass(freq, dur, vel=1.0):
    n = int(dur * SR)
    x = np.sin(2 * np.pi * freq * np.arange(n) / SR) + 0.62 * filt(saw(freq, n, 18), hi=1300)
    x = np.tanh(1.6 * x) * env_adsr(n, a=0.004, d=0.09, s=0.65, r=0.03)
    return fade_edges(x * vel, 3)


def stab(notes, dur=0.34):
    n = int(dur * SR)
    t = np.arange(n) / SR
    left, right = np.zeros(n), np.zeros(n)
    for m in notes:
        for cents, pan in ((-9, -0.6), (0, 0.0), (9, 0.6)):
            v = saw(midi(m) * 2 ** (cents / 1200), n, 28, phase=rng.random() * 6)
            th = (pan + 1) * np.pi / 4
            left += v * np.cos(th)
            right += v * np.sin(th)
    st = np.stack([left, right], axis=1) / (len(notes) * 2)
    st = filt(st, lo=160, hi=3400)
    e = (np.minimum(1, t / 0.003) * np.exp(-t / 0.15))[:, None]
    return fade_edges(st * e, 4)


def pad(notes, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    left, right = np.zeros(n), np.zeros(n)
    for i, m in enumerate(notes):
        for cents, pan in ((-6, -0.5), (6, 0.5)):
            v = saw(midi(m) * 2 ** (cents / 1200), n, 12, phase=rng.random() * 6)
            th = (pan + 1) * np.pi / 4
            left += v * np.cos(th)
            right += v * np.sin(th)
    st = filt(np.stack([left, right], axis=1) / (len(notes) * 2), lo=120, hi=1300)
    e = np.minimum(1, t / 0.5) * (1 + 0.06 * np.sin(2 * np.pi * 0.2 * t))
    rel = int(0.6 * SR)
    if rel < n:
        e[-rel:] *= np.linspace(1, 0, rel)
    return fade_edges(st * e[:, None], 10)


def pluck(freq, dur=0.9, bright=1.0):
    t = t_axis(dur)
    x = (np.sin(2 * np.pi * freq * t) + 0.32 * bright * np.sin(4 * np.pi * freq * t)
         + 0.12 * bright * np.sin(6 * np.pi * freq * t))
    return fade_edges(x * np.minimum(1, t / 0.002) * np.exp(-t / 0.22), 6)


def chime(freq):
    t = t_axis(2.0)
    x = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / d)
            for r, a, d in ((1, 1, 1.1), (2.0, 0.45, 0.7), (2.76, 0.28, 0.45), (5.4, 0.12, 0.25)))
    return fade_edges(x * np.minimum(1, t / 0.002), 20)


def shutter():
    t = t_axis(0.1)
    out = np.zeros(len(t))
    for d, g in ((0.0, 1.0), (0.027, 0.65)):
        tt = np.clip(t - d, 0, None)
        on = t >= d
        out += on * g * (filt(noise(len(t)), lo=1800, hi=7500) * np.exp(-tt / 0.0042)
                         + 0.5 * np.sin(2 * np.pi * 150 * tt) * np.exp(-tt / 0.01))
    return fade_edges(out, 1)


def whoosh(dur=0.24, lo=700, hi=6500):
    t = t_axis(dur)
    p = t / dur
    e = np.sin(np.pi * np.clip(p, 0, 1)) ** 2 * (0.4 + 0.6 * p)
    fc = lo * (hi / lo) ** p
    x = sweep_lp(filt(noise(len(t)), lo=260), fc) * e
    th = (np.clip(p * 1.2 - 0.1, 0, 1) * 0.9 - 0.45 + 1) * np.pi / 4   # drifts left to right
    return fade_edges(np.stack([x * np.cos(th), x * np.sin(th)], axis=1) * np.sqrt(2), 3)


def glitch(dur):
    """Chopped digital junk: square blips, crushed noise, gaps, chirps."""
    n = int(dur * SR)
    out = np.zeros(n)
    i = 0
    while i < n:
        seg = int(rng.uniform(0.007, 0.024) * SR)
        tt = np.arange(seg) / SR
        kind = rng.integers(0, 4)
        if kind == 0:
            s = np.sign(np.sin(2 * np.pi * rng.uniform(180, 2600) * tt)) * 0.55
        elif kind == 1:
            s = np.round(noise(seg) * 3) / 3 * 0.45
        elif kind == 2:
            s = np.zeros(seg)
        else:
            s = np.sin(2 * np.pi * np.cumsum(np.linspace(rng.uniform(300, 900), rng.uniform(1500, 4000), seg)) / SR) * 0.5
        out[i:i + seg] = s[: n - i]
        i += seg
    return fade_edges(filt(out, lo=140, hi=9000), 2)


def ui_tick():
    t = t_axis(0.05)
    x = (np.sin(2 * np.pi * 2100 * t) + 0.4 * np.sin(2 * np.pi * 3150 * t)) * np.exp(-t / 0.007)
    return fade_edges(x, 1)


def swish(dur=0.3, reverse=False):
    t = t_axis(dur)
    p = t / dur
    e = (p ** 2 if not reverse else (1 - p) ** 2) * np.sin(np.pi * p)
    x = filt(noise(len(t)), lo=2200, hi=9000) * e
    return fade_edges(x, 3)


def bitcrush(x, bits, keep):
    """Quantize to `bits` and sample-and-hold every `keep` samples."""
    q = 2 ** (bits - 1)
    y = np.round(x * q) / q
    idx = (np.arange(len(y)) // keep) * keep
    return y[idx]


# ---------------------------------------------------------------- arrangement

# chords: (bass midi, upper voicing) -- Am9, Fmaj9, Cmaj9, G6/9
AM9 = (33, [60, 64, 67, 71])
FM9 = (29, [57, 60, 64, 67])
CM9 = (36, [59, 62, 64, 67])
G69 = (31, [59, 62, 64, 69])
PROG = [AM9, FM9, CM9, G69]


def chord_for_bar(b):
    if b < 2 or b >= 10:
        return AM9
    return PROG[(b - 2) % 4]


def render(ev, wav_path):
    total = ev["total"]
    dur = total + TAIL
    drums, bassb, music, fx = Bus(dur), Bus(dur), Bus(dur), Bus(dur)
    verb_send, delay_send = Bus(dur), Bus(dur)
    end_t = ev["end"]["start"]                      # 20.0: drums stop here
    drop_t = ev["grids"][0]["start"]                # 4.0: first grid
    n_bars = int(round(end_t / BAR))                # 10 bars of groove (2 muffled)

    K, CL, HC, HO, SH = kick(), clap(), hat(False), hat(True), shaker()
    kick_times = []

    for b in range(n_bars):
        b0 = b * BAR
        root, voicing = chord_for_bar(b)
        grid_bar = b - 2                              # 0..7 once the grids start
        for beat in range(4):
            tb = b0 + beat * BEAT
            # leave a hole before each big moment: the drop and the end card
            if abs(tb - (drop_t - BEAT)) < 1e-6 or abs(tb - (end_t - BEAT)) < 1e-6:
                continue
            drums.add(K, tb, 0.85)
            kick_times.append(tb)
            if beat in (1, 3):
                drums.add(CL, tb, 0.58, pan=0.05)
                verb_send.add(CL, tb, 0.22)
        for s in range(16):
            ts = b0 + s * STEP
            if ts >= end_t - BEAT and b == n_bars - 1:
                break
            if s % 4 == 2 and grid_bar >= 0:
                drums.add(HO, ts, 0.24 * (1.0 if s != 14 else 0.85), pan=0.3)
            if s % 2 == 1 and grid_bar >= 2:
                drums.add(HC, ts, 0.15 * (1.0 if s % 4 == 3 else 0.7), pan=-0.35)
            if grid_bar >= 4:
                drums.add(SH, ts, 0.09 * (1.0 if s % 4 == 2 else 0.6), pan=0.45)
        # bass: offbeat root + a pushed fifth
        for s, semis, length, vel in ((2, 0, 0.19, 1.0), (6, 0, 0.19, 0.95), (10, 0, 0.19, 1.0),
                                      (11, 7, 0.09, 0.55), (14, 0, 0.19, 0.95)):
            ts = b0 + s * STEP
            if ts >= end_t - BEAT and b == n_bars - 1:
                continue
            bassb.add(bass(midi(root + 12 + semis), length, vel), ts, 0.5)
        # stabs from the second grid, plucked arpeggio from the third
        if grid_bar >= 2:
            for s in (3, 10):
                st = stab(voicing)
                music.add(st, b0 + s * STEP, 0.48)
                delay_send.add(st, b0 + s * STEP, 0.22)
                verb_send.add(st, b0 + s * STEP, 0.25)
        if grid_bar >= 4:
            arp = [voicing[3] + 12, voicing[2] + 12, voicing[1] + 12, voicing[3] + 12, voicing[0] + 12, voicing[2] + 12]
            for s, m in zip((0, 3, 6, 8, 11, 14), arp):
                p = pluck(midi(m), 0.6, 0.8)
                music.add(p, b0 + s * STEP, 0.20, pan=0.4 if s % 2 else -0.4)
                delay_send.add(p, b0 + s * STEP, 0.10)
                verb_send.add(p, b0 + s * STEP, 0.12)
        # pad under everything
        music.add(pad(voicing, BAR + 0.5), b0, 0.22)
        verb_send.add(pad(voicing, BAR + 0.5), b0, 0.06)

    # ---- intro: muffled groove opening with the loading bar, glitch stutters
    intro = ev["intro"]
    t_all = np.arange(len(drums.x)) / SR
    prog_t = [p[0] for p in intro["progress"]]
    prog_v = [p[1] for p in intro["progress"]]
    pct = np.interp(t_all, prog_t, prog_v)
    fc = 230 * (1100 / 230) ** (pct / 100)
    rv0, rv1 = intro["reveal"]
    open_ = (t_all >= rv1) & (t_all < drop_t)
    fc[open_] = 1100 * (13000 / 1100) ** ((t_all[open_] - rv1) / (drop_t - rv1)) ** 2
    fc[t_all >= drop_t] = 24000
    muffle = np.where(t_all < drop_t, 0.62 + 0.38 * (t_all / drop_t) ** 3, 1.0)[:, None]

    # sidechain: bass and music duck under every kick
    sc = np.zeros(len(t_all))
    for tk in kick_times:
        i = int(tk * SR)
        seg = np.exp(-np.arange(min(int(0.4 * SR), len(sc) - i)) / SR / 0.11)
        sc[i:i + len(seg)] = np.maximum(sc[i:i + len(seg)], seg)
    duck_bass = (1 - 0.65 * sc)[:, None]
    duck_music = (1 - 0.45 * sc)[:, None]

    verb = convolve(verb_send.x, reverb_ir())
    delay = pingpong(delay_send.x)
    groove = drums.x + bassb.x * duck_bass + (music.x + delay) * duck_music + verb * 0.55
    groove = sweep_lp(groove, fc) * muffle

    for s, e, amt in intro["bursts"] + [(rv0, rv1, 1.0)]:
        i0, i1 = int(s * SR), int(e * SR)
        sl = max(int(STEP / 2 * SR), 1)
        chunk = groove[i0:i0 + sl].copy()
        rep = np.tile(chunk, (int(np.ceil((i1 - i0) / sl)) + 1, 1))[: i1 - i0]
        bits = int(7 - 3 * amt)
        rep = np.stack([bitcrush(rep[:, c], bits, 4 + int(6 * amt)) for c in range(2)], axis=1)
        groove[i0:i1] = fade_edges(rep, 2) * 0.9
        fx.add(glitch(e - s + 0.02), s - 0.01, 0.30 + 0.15 * amt, pan=rng.uniform(-0.3, 0.3))
    for tk in intro["ticks"]:
        fx.add(glitch(0.035), tk, 0.18, pan=rng.uniform(-0.4, 0.4))
    for tp, _ in intro["progress"][1:]:
        fx.add(ui_tick(), tp, 0.05, pan=0.1)
    fx.add(chime(midi(81)), intro["complete"], 0.10)
    fx.add(chime(midi(88)), intro["complete"] + 0.07, 0.08)
    verb_tail = Bus(dur)
    verb_tail.add(chime(midi(88)), intro["complete"] + 0.07, 0.10)
    fx.add(reverse_cymbal(drop_t - 2.9), 2.9, 0.30)
    fx.add(riser(drop_t - rv0), rv0, 0.16)
    fx.add(whoosh(0.26), intro["exit"][0] - 0.02, 0.26)

    # ---- grids: shutter on each pop, whoosh on each snap, card swish, crashes
    for k, g in enumerate(ev["grids"]):
        fx.add(crash(), g["start"], 0.24 if k == 0 else 0.13)
        if k == 0:
            fx.add(impact(), g["start"], 0.55)
        for i, tp in enumerate(g["pops"]):
            fx.add(shutter(), tp - 0.003, 0.30, pan=(-0.35, 0.35, -0.35, 0.35)[i])
        for i, ts in enumerate(g["snaps"]):
            fx.add(whoosh(0.16, 900, 7000), ts - 0.08, 0.22)
        fx.add(swish(0.28), g["card_in"] - 0.12, 0.10)
        fx.add(ui_tick(), g["card_in"] + 0.10, 0.04)
        fx.add(swish(0.26, reverse=True), g["card_out"], 0.06)
        x0, x1 = g["exit"]
        fx.add(whoosh(x1 - x0 + 0.06, 600, 9000), x0 - 0.03, 0.22)
        if k < len(ev["grids"]) - 1:
            fx.add(reverse_cymbal(0.55), x1 - 0.55, 0.13)

    # ---- end card: impact + open chord, glitch hit on the logo, three notes
    end = ev["end"]
    fx.add(reverse_cymbal(0.9), end_t - 0.9, 0.24)
    fx.add(impact(), end_t, 0.62)
    fx.add(crash(3.2), end_t, 0.18)
    chord = pad(AM9[1] + [72, 76], total - end_t + 1.0)
    music.x[:] = 0
    music.add(chord, end_t, 0.75)
    music.add(stab(AM9[1] + [69], 0.6), end_t, 0.42)
    bed = Bus(dur)                      # drum-free groove: hats, shaker, echoing stabs
    for b in range(int(round((total - end_t) / BAR))):
        b0 = end_t + b * BAR
        for s in range(16):
            ts = b0 + s * STEP
            if s % 4 == 2:
                bed.add(HO, ts, 0.22, pan=0.3)
            if s % 2 == 1:
                bed.add(SH, ts, 0.10, pan=0.45)
        for s in (6, 14):
            st = stab(AM9[1], 0.3)
            bed.add(st, b0 + s * STEP, 0.42)
            for k in range(1, 4):                       # dotted-eighth ping-pong echoes
                bed.add(st, b0 + s * STEP + k * 0.375, 0.42 * 0.38 ** k, pan=(-0.5, 0.5)[k % 2])
    music.x += filt(bed.x, lo=200)
    bassb.x[:] = 0
    bassb.add(bass(midi(45), 2.4, 1.0) * np.exp(-np.arange(int(2.4 * SR)) / SR / 0.9), end_t, 0.45)
    fx.add(glitch(0.07), end["logo"] + 1 / 30, 0.16)
    for i, (ts, m) in enumerate(zip(end["swatches"], (81, 84, 88))):
        p = pluck(midi(m), 1.2, 0.6)
        fx.add(p, ts, 0.16, pan=(-0.35, 0.0, 0.35)[i])
        verb_tail.add(p, ts, 0.16)
    fx.add(ui_tick(), end["cta"], 0.04)
    tail_verb = convolve(music.x * 0.5 + verb_tail.x, reverb_ir(3.0, 0.7, 5200, 0.03))

    end_i = int(end_t * SR)
    mix = groove.copy()
    mix[end_i - 240:end_i] *= np.linspace(1, 0, 240)[:, None]   # groove hands over to the impact
    mix[end_i:] = 0
    mix += fx.x + (music.x + bassb.x) * (t_all >= end_t)[:, None] + tail_verb * 0.6

    # ---- master: gentle glue, fades, trim to the picture
    mix = mix[: int(round(total * SR))]
    mix = filt(mix, lo=28)
    mix = np.tanh(1.15 * mix / max(np.abs(mix).max(), 1e-9) * 1.4) / np.tanh(1.15 * 1.4)
    fo = int(0.5 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    mix = fade_edges(mix, 3)
    mix *= 10 ** (-1.0 / 20) / np.abs(mix).max()
    pcm = (mix * 32767).astype(np.int16)

    import wave
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return wav_path


def mux(video, wav, out, target_lufs=-14.0):
    """Two-pass EBU R128 loudness to Instagram's -14 LUFS, AAC 48 kHz, faststart."""
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", wav, "-af",
         f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    m = json.loads(probe[probe.rindex("{"): probe.rindex("}") + 1])
    af = (f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:measured_I={m['input_i']}:"
          f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
          f"aresample=48000")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav, "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
         "-shortest", "-movflags", "+faststart", out], check=True)
    return out


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import importlib.util
    spec = importlib.util.spec_from_file_location("reel", os.path.join(os.path.dirname(__file__), "reel.py"))
    reel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reel)
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(reel.ROOT, "out", "basic-reel-audio.wav")
    print(render(reel.timeline(), out))
