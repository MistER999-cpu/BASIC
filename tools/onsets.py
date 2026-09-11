#!/usr/bin/env python3
"""Find the transients in a clip's audio, so reel stops can be placed on them.

    python3 tools/onsets.py assets/base/base.mp4

Prints onset times with strengths plus a coarse energy map. Pick the spin start
and the three reel stops from the strong onsets and put them in config.json's
timeline - a stop that lands off the beat reads as a glitch, not a detent.
"""
import subprocess, sys
import numpy as np

SR = 22050

def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn',
                          '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                         capture_output=True).stdout
    if not raw:
        raise SystemExit(f'no audio decoded from {path}')
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def onsets(a, n_fft=1024, hop=256, ratio=2.2, floor=0.10, min_gap=0.12):
    win = np.hanning(n_fft)
    n = 1 + (len(a) - n_fft) // hop
    S = np.abs(np.fft.rfft(np.stack([a[i*hop:i*hop+n_fft] * win for i in range(n)]), axis=1))
    flux = np.maximum(0, np.diff(S, axis=0)).sum(axis=1)
    flux /= flux.max() + 1e-9
    t = (np.arange(len(flux)) * hop + n_fft / 2) / SR

    w = 40
    local = np.array([flux[max(0, i-w):i+w].mean() for i in range(len(flux))])
    out = []
    for i in range(2, len(flux) - 2):
        if flux[i] > local[i] * ratio and flux[i] > floor and flux[i] == max(flux[i-2:i+3]):
            if not out or t[i] - out[-1][0] > min_gap:
                out.append((float(t[i]), float(flux[i])))
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    a = load(sys.argv[1])
    print(f'duration {len(a)/SR:.2f}s   peak {20*np.log10(np.abs(a).max()+1e-9):.1f} dBFS\n')

    found = onsets(a)
    print(f'{len(found)} onsets:')
    for tt, v in found:
        bar = '#' * int(round(v * 40))
        print(f'  {tt:6.3f}s  {v:.3f}  {bar}')

    print('\n  t     rms_dB  centroidHz')
    w = SR // 4
    for i in range(0, len(a) - w + 1, w):
        s = a[i:i+w]
        rms = np.sqrt((s**2).mean()) + 1e-9
        S = np.abs(np.fft.rfft(s * np.hanning(len(s))))
        f = np.fft.rfftfreq(len(s), 1/SR)
        print(f'{i/SR:6.2f} {20*np.log10(rms):7.1f} {(S*f).sum()/(S.sum()+1e-9):9.0f}')


if __name__ == '__main__':
    main()
