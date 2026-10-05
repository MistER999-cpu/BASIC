#!/usr/bin/env python3
"""Beat grid and bar map for a soundtrack, to cut the edit on the music.

    python3 survet/beats.py track.mp3 [--bpm-range 100 140]

Estimates one global tempo (fine for a quantised dance track), fits the grid
phase to the onset envelope, then prints one row per bar with its loudness and
band energies so a segment can be picked that starts on a phrase.
"""
import subprocess, sys, json, os
import numpy as np

SR = 22050
HOP = 256

def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1',
                          '-ar', str(SR), '-f', 's16le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def stft_mag(a, n_fft=2048):
    win = np.hanning(n_fft)
    n = 1 + (len(a) - n_fft) // HOP
    frames = np.lib.stride_tricks.as_strided(a, (n, n_fft), (a.strides[0]*HOP, a.strides[0]))
    return np.abs(np.fft.rfft(frames * win, axis=1)), np.fft.rfftfreq(n_fft, 1/SR)

def main():
    path = sys.argv[1]
    lo_bpm, hi_bpm = 100, 140
    if '--bpm-range' in sys.argv:
        i = sys.argv.index('--bpm-range'); lo_bpm, hi_bpm = float(sys.argv[i+1]), float(sys.argv[i+2])
    a = load(path)
    S, f = stft_mag(a)
    fps = SR / HOP
    logS = np.log1p(100 * S)
    flux = np.maximum(0, np.diff(logS, axis=0)).sum(1)
    flux = np.concatenate([[0], flux])
    flux -= np.convolve(flux, np.ones(32)/32, 'same')
    flux = np.maximum(flux, 0)

    # tempo: autocorrelation of the onset envelope, refined to 0.01 BPM by
    # maximising comb energy over the whole track
    best = None
    for bpm in np.arange(lo_bpm, hi_bpm, 0.01):
        period = 60 / bpm * fps
        idx = np.arange(0, len(flux) - 1, period)
        # phase search per bpm is costly; use the comb's FFT magnitude instead
        k = np.arange(len(flux))
        val = abs(np.sum(flux * np.exp(-2j*np.pi*k/period)))
        if best is None or val > best[0]:
            best = (val, bpm)
    bpm = best[1]
    period = 60 / bpm * fps
    k = np.arange(len(flux))
    phase = np.angle(np.sum(flux * np.exp(-2j*np.pi*k/period)))
    first = (-phase / (2*np.pi)) * period % period          # frames
    beat0 = first / fps + (2048/2)/SR                       # centre of the window
    P = 60 / bpm

    # bar phase: in 4/4 house the downbeat carries the most low-end novelty
    low = (f < 150)
    lowflux = np.maximum(0, np.diff(logS[:, low], axis=0)).sum(1)
    lowflux = np.concatenate([[0], lowflux])
    def at(t, env):
        i = int(round((t - (2048/2)/SR) * fps))
        return env[max(0, i-2):i+3].max() if 0 <= i < len(env) else 0
    nbeats = int((len(a)/SR - beat0) / P)
    scores = [0]*4
    for b in range(nbeats):
        scores[b % 4] += at(beat0 + b*P, flux)
    bar_off = int(np.argmax(scores))
    down0 = beat0 + bar_off * P

    bands = {'sub': (20, 120), 'low': (120, 400), 'mid': (400, 2500), 'high': (2500, 11000)}
    print(f'bpm {bpm:.2f}  beat {P:.4f}s  first beat {beat0:.3f}s  first downbeat {down0:.3f}s')
    print(f'beat-in-bar scores {[round(s,1) for s in scores]}')
    print(f'\n bar   start   rms_dB   ' + '  '.join(f'{b:>5}' for b in bands) + '   onset')
    rows = []
    t = down0
    bar = 0
    while t + 4*P < len(a)/SR:
        i0, i1 = int(t*SR), int((t+4*P)*SR)
        seg = a[i0:i1]
        rms = 20*np.log10(np.sqrt((seg**2).mean()) + 1e-9)
        j0, j1 = int(t*fps), int((t+4*P)*fps)
        e = {b: 10*np.log10((S[j0:j1][:, (f>=lo)&(f<hi)]**2).sum(1).mean() + 1e-9) for b, (lo, hi) in bands.items()}
        on = flux[j0:j1].mean()
        rows.append({'bar': bar, 't': round(t, 3), 'rms': round(float(rms), 1), **{k: round(float(v), 1) for k, v in e.items()}, 'onset': round(float(on), 3)})
        print(f'{bar:4d} {t:7.2f}  {rms:7.1f}   ' + '  '.join(f'{e[b]:5.1f}' for b in bands) + f'   {on:.3f}')
        t += 4*P; bar += 1
    os.makedirs('out', exist_ok=True)
    json.dump({'bpm': bpm, 'beat': P, 'downbeat0': down0, 'bars': rows}, open('out/beats.json', 'w'), indent=1)

if __name__ == '__main__':
    main()
