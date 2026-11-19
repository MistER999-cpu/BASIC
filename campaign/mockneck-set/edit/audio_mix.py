#!/usr/bin/env python3
"""Sound for the BASIC ad: the chorus of the supplied track, cut on the beat grid, with
synthesised sound design (riser, drop impact, shutter clicks, whooshes, fabric swish,
logo impact and shimmer) and a reverb tail on the last downbeat.

    python3 campaign/mockneck-set/edit/audio_mix.py --music <file> --out mix.wav [--sfx-only sfx.wav]
"""
import os
import sys
import argparse
import subprocess
import numpy as np
from scipy import signal
import pyloudnorm as pyln

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline as tl

SR = 48000
T = tl.T
DUR = tl.DURATION
rng = np.random.default_rng(3)


def load_music(path, start, length):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{start:.4f}', '-t', f'{length:.4f}', '-i', path,
                          '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def db(x):
    return 10 ** (x / 20)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)


def lowpass(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, btype='low', fs=SR, output='sos'), x, axis=0)


def highpass(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, btype='high', fs=SR, output='sos'), x, axis=0)


def pink(n, ch=2):
    w = rng.standard_normal((n, ch))
    f = np.fft.rfftfreq(n, 1 / SR)
    F = np.fft.rfft(w, axis=0)
    F[1:] /= np.sqrt(f[1:, None])
    F[0] = 0
    p = np.fft.irfft(F, n, axis=0)
    return p / (np.abs(p).max() + 1e-9)


def sweep_filter(x, f_start, f_end, q=1.2):
    """Time-varying band-pass via STFT masking (centre glides f_start -> f_end, log)."""
    out = np.zeros_like(x)
    for c in range(x.shape[1]):
        f, t, Z = signal.stft(x[:, c], fs=SR, nperseg=1024, noverlap=768)
        fc = np.geomspace(f_start, f_end, Z.shape[1])
        g = np.exp(-0.5 * (np.log((f[:, None] + 1) / fc[None, :]) / (0.35 * q)) ** 2)
        _, y = signal.istft(Z * g, fs=SR, nperseg=1024, noverlap=768)
        out[:, c] = y[:x.shape[0]] if len(y) >= x.shape[0] else np.pad(y, (0, x.shape[0] - len(y)))
    return out


def pan(x_mono, pos):
    """pos: array of -1..1 per sample (equal power)."""
    a = (pos + 1) * np.pi / 4
    return np.stack([x_mono * np.cos(a), x_mono * np.sin(a)], 1)


# ------------------------------------------------------------------ sound design
def riser(length):
    n = int(length * SR)
    x = pink(n)
    x = sweep_filter(x, 700, 7000, q=1.6)
    e = (np.linspace(0, 1, n) ** 2.6)[:, None]
    return x / (np.abs(x).max() + 1e-9) * e


def impact(length=1.6, f0=70, f1=36, tau=0.42, click=True):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_exp(n, tau)
    body = np.tanh(body * 1.8) / np.tanh(1.8)
    thump = lowpass(rng.standard_normal(n), 140) * env_exp(n, 0.05) * 3.0
    x = body + thump
    if click:
        c = highpass(rng.standard_normal(n), 2500) * env_exp(n, 0.004) * 0.6
        x = x + c
    x = x / (np.abs(x).max() + 1e-9)
    return np.stack([x, x], 1)


def shutter():
    n = int(0.12 * SR)
    x = np.zeros(n)
    for start, dur, amp in [(0.0, 0.004, 1.0), (0.034, 0.006, 0.75)]:
        i0 = int(start * SR); m = int(dur * SR)
        burst = rng.standard_normal(m) * np.exp(-np.arange(m) / (m / 3))
        x[i0:i0 + m] += burst * amp
    x = bandpass(x, 1400, 7500)
    th = np.sin(2 * np.pi * 95 * np.arange(n) / SR) * env_exp(n, 0.012) * 0.35
    x = x / (np.abs(x).max() + 1e-9) + th
    return np.stack([x * 0.9, x], 1)


def whoosh(pre, post, lo=250, hi=4200, pan_from=-0.8, pan_to=0.8, airy=False):
    n_pre, n_post = int(pre * SR), int(post * SR)
    n = n_pre + n_post
    x = pink(n)
    up = sweep_filter(x[:n_pre], lo, hi, q=1.4 if not airy else 2.2)
    down = sweep_filter(x[n_pre:], hi, lo * 1.3, q=1.4 if not airy else 2.2)
    y = np.concatenate([up, down])
    e = np.concatenate([np.linspace(0, 1, n_pre) ** 2.2, np.exp(-np.arange(n_post) / (0.11 * SR))])
    m = y.mean(1) * e
    m = m / (np.abs(m).max() + 1e-9)
    p = np.concatenate([np.linspace(pan_from, 0, n_pre), np.linspace(0, pan_to, n_post)])
    return pan(m, p), n_pre


def swish(length=0.45):
    n = int(length * SR)
    x = pink(n)[:, 0]
    x = bandpass(x, 300, 2200)
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    x = x * e / (np.abs(x * e).max() + 1e-9)
    return pan(x, np.linspace(-0.6, 0.6, n))


def shimmer(length=1.4, base=2600):
    n = int(length * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(9):
        fr = base * (1 + 0.37 * k) * rng.uniform(0.98, 1.02)
        x += np.sin(2 * np.pi * fr * t + rng.uniform(0, 6.28)) * (0.8 ** k)
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * 11 * t)
    a = np.minimum(1, t / 0.04) * np.exp(-t / 0.45)
    x = x * trem * a
    x = highpass(x, 1800)
    x /= np.abs(x).max() + 1e-9
    return pan(x, np.sin(2 * np.pi * 0.7 * t) * 0.6)


def tick():
    n = int(0.02 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 4200 * t) * np.exp(-t / 0.003)
    return np.stack([x, x], 1)


def reverb_ir(length=3.4, rt60=3.0):
    n = int(length * SR)
    tau = rt60 / 6.91
    ir = rng.standard_normal((n, 2)) * np.exp(-np.arange(n) / (tau * SR))[:, None]
    ir = lowpass(ir, 5200)
    pre = int(0.022 * SR)
    ir = np.concatenate([np.zeros((pre, 2)), ir])
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


def place(buf, x, t, gain_db, align=0):
    i0 = int(round(t * SR)) - align
    if i0 < 0:
        x = x[-i0:]; i0 = 0
    i1 = min(len(buf), i0 + len(x))
    buf[i0:i1] += x[:i1 - i0] * db(gain_db)


def build_sfx(n):
    sfx = np.zeros((n, 2))
    # pre-drop riser into the downbeat, then the drop impact
    place(sfx, riser(T(0) - 0.02), 0.02, -9)
    place(sfx, impact(), T(0), -9)
    # lookbook flips: shutter clicks + small whooshes
    for b in (0, 1, 2):
        place(sfx, shutter(), T(b), -13)
    w, a = whoosh(0.22, 0.18, 400, 5200)
    place(sfx, w, T(3), -8, align=a)
    # location whips
    for b in (21, 40):
        w, a = whoosh(0.34, 0.26, 220, 4800)
        place(sfx, w, T(b), -4, align=a)
    # light leak (airy) and the spin swish
    w, a = whoosh(0.40, 0.35, 900, 6500, pan_from=0.5, pan_to=-0.5, airy=True)
    place(sfx, w, T(46), -9, align=a)
    place(sfx, swish(), 16.30, -8)
    # fabric wipe into the end card
    w, a = whoosh(0.30, 0.30, 160, 2600, pan_from=0.9, pan_to=-0.9)
    place(sfx, w, T(56), -4, align=a)
    # figures arriving, logo impact, shimmer, final shine
    for b in (57, 58, 59):
        place(sfx, shutter(), T(b), -6)
    w, a = whoosh(0.45, 0.05, 300, 3800, pan_from=0.0, pan_to=0.0)
    place(sfx, w, T(60), -12, align=a)
    place(sfx, impact(1.8, 64, 34, 0.5), T(60), -10)
    place(sfx, shimmer(1.5, 2700), T(60) + 0.02, -17)
    place(sfx, shimmer(1.6, 3300), T(64), -14)
    # callout ticks
    for c_in in (T(11), T(22), T(28), T(41), T(51)):
        place(sfx, tick(), c_in + 0.05, -22)
    return sfx


def build_music(path, n):
    end = T(tl.END_BEAT)
    main = load_music(path, tl.MUSIC_IN, end + 0.75)
    out = np.zeros((n, 2))
    i_end = int(end * SR)
    out[:i_end] = main[:i_end]
    # let the last downbeat ring briefly, then hand over to the reverb tail
    hit = main[i_end:i_end + int(0.62 * SR)].copy()
    hit *= np.linspace(1, 0, len(hit))[:, None] ** 1.5
    out[i_end:i_end + len(hit)] += hit
    # reverb send ramps up over the final beat
    send = np.zeros((n, 2))
    i0 = int(T(tl.END_BEAT - 1) * SR)
    send[i0:i_end] = main[i0:i_end] * np.linspace(0, 1, i_end - i0)[:, None]
    send[i_end:i_end + len(hit)] += hit
    wet = signal.fftconvolve(send, reverb_ir(), axes=0)[:n]
    tail_fade = np.clip((DUR - np.arange(n) / SR) / 1.2, 0, 1)[:, None]
    out = out + wet * db(0) * tail_fade
    # tiny fade-in so the first sample does not click
    fi = int(0.03 * SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]
    return out


def master(x, target_lufs=-14.0, ceiling_db=-1.0):
    meter = pyln.Meter(SR)
    loud = meter.integrated_loudness(x)
    x = x * db(target_lufs - loud)
    c = db(ceiling_db)
    # soft-knee limiter on peaks above ~-3 dBFS
    thr = c * 0.82
    mag = np.abs(x)
    over = mag > thr
    x[over] = np.sign(x[over]) * (thr + (c - thr) * np.tanh((mag[over] - thr) / (c - thr)))
    return x, loud


def write_wav(path, x):
    pcm = np.clip(x, -1, 1).astype(np.float32)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                    '-c:a', 'pcm_s24le', path], input=pcm.tobytes(), check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--music', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sfx-only')
    a = ap.parse_args()
    n = int(round(DUR * SR))
    sfx = build_sfx(n)
    music = build_music(a.music, n)
    mix, loud_before = master(music + sfx)
    write_wav(a.out, mix)
    meter = pyln.Meter(SR)
    print(f'mix: {DUR:.2f}s, source loudness {loud_before:.1f} LUFS -> {meter.integrated_loudness(mix):.1f} LUFS, '
          f'peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS')
    if a.sfx_only:
        s, _ = master(sfx * 1.0, target_lufs=-20.0)
        write_wav(a.sfx_only, s)
        print('sfx-only stem written')


if __name__ == '__main__':
    main()
