#!/usr/bin/env python3
"""Original score + sound design for the full BASIC lookbook film (no third-party rights).

90 BPM, locked to film.py's beat grid. Each colourway gets its own key (Noir D minor, Chocolat up a
minor third, Burgundy up a fourth), each block opens with a crash and the bass walks into the next
key; the roll call drops to hats and claps, and the end card lands on a big hit and rings out on Dm9.

    python3 campaign/mockneck-set/lookbook/edit/film_music.py --out mix.wav --sfx-only sfx.wav
"""
import os
import sys
import argparse
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import music_temp as mt          # noqa: E402  instruments + placement
import film as FM                # noqa: E402

am = mt.am
SR = mt.SR
FPS = FM.FPS
SPB = 60.0 / FM.BPM
place = mt.place
rng = np.random.default_rng(31)


def tb(b):
    return FM.B(b) / FPS


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


DM9, BBMAJ7, A7SUS, GM9 = [57, 60, 64, 65], [58, 62, 65, 69], [55, 57, 62, 64], [55, 58, 62, 65]
BLOCK_BEATS = 10


def chords_for(start, key, last):
    """(beat, length, voicing, bass) for a 10-beat colourway block."""
    tail_key = 0 if last else key
    return [(start + 0, 4, [n + key for n in DM9], 38 + key),
            (start + 4, 4, [n + key for n in BBMAJ7], 34 + key),
            (start + 8, 2, [n + tail_key for n in A7SUS], 33 + tail_key)]


def stems(n):
    st = {k: np.zeros((n, 2)) for k in ('kick', 'clap', 'hats', 'shaker', 'sub', 'keys', 'pad', 'fx', 'send')}
    kick_env = np.zeros(n)

    def k(b, vel=1.0):
        place(st['kick'], mt.kick(vel), tb(b))
        i0 = int(tb(b) * SR)
        e = np.exp(-np.arange(int(0.35 * SR)) / (0.12 * SR)) * vel
        seg = kick_env[i0:i0 + len(e)]
        kick_env[i0:i0 + len(e)] = np.maximum(seg, e[:len(seg)])

    blocks = FM.BLOCKS
    # ---- drums through the three colourway blocks
    for bi, (b0, key) in enumerate(blocks):
        for bar in range(0, BLOCK_BEATS, 2):
            k(b0 + bar)
            if bar + 1.5 < BLOCK_BEATS:
                k(b0 + bar + 1.5, 0.8)
        for b in range(1, BLOCK_BEATS, 2):
            x = mt.clap(0.9)
            place(st['clap'], x, tb(b0 + b))
            place(st['send'], x, tb(b0 + b), -6)
        # fill into the next block
        for j, sb in enumerate((9.25, 9.5, 9.75)):
            x = mt.clap(0.45 + 0.15 * j)
            place(st['clap'], x, tb(b0 + sb), -3)
        place(st['fx'], mt.crash(2.2), tb(b0), -2 if bi == 0 else -4)
    # hats: 16ths from the first flicks to the end card, swung, open hat on the "and" of 4
    vel_pat = [1.0, 0.32, 0.62, 0.36]
    b = 1.5
    while b < FM.END_BEAT - 1e-6:
        step = int(round((b % 1) * 4))
        swing = 0.010 if step % 2 else 0.0
        open_ = abs((b % 4) - 3.5) < 1e-6
        place(st['hats'], np.outer(mt.hat(vel_pat[step], open_), [0.82, 1.0]), tb(b) + swing, 0 if not open_ else -4)
        b += 0.25
    b = 2.5
    while b < 28:
        place(st['shaker'], np.outer(mt.shaker(0.8), [1.0, 0.7]), tb(b) + 0.006)
        b += 1.0
    # roll call: clap pickup into the end card
    for sb in (28.75, 29.0, 29.25, 29.5, 29.75):
        place(st['clap'], mt.clap(0.6), tb(sb), -2)

    # ---- harmony
    chords = []
    for bi, (b0, key) in enumerate(blocks):
        chords += chords_for(b0, key, last=(bi == len(blocks) - 1))
    for (b0, ln, voicing, bass) in chords:
        x = mt.epiano([hz(m) for m in voicing], ln * SPB * 0.6, 1.0)
        place(st['keys'], x, tb(b0))
        place(st['send'], x, tb(b0), -4)
        if ln >= 4:
            x = mt.epiano([hz(m) for m in voicing], 0.5 * SPB, 0.65)
            place(st['keys'], x, tb(b0 + 2.5))
        place(st['pad'], mt.pad([hz(m) for m in voicing], ln * SPB, 1.0, 1300 + 120 * b0 / 3), tb(b0))
        for s_, e_ in ((0, 1.5), (1.5, ln)):
            if e_ > s_:
                place(st['sub'], mt.sub(hz(bass), (e_ - s_) * SPB * 0.95, 0.9), tb(b0 + s_))

    # ---- end card: big hit, ring out on Dm9
    E = FM.END_BEAT
    k(E, 1.0)
    k(E + 2, 0.7)
    place(st['fx'], mt.crash(3.0), tb(E), 0)
    final = DM9 + [74]
    x = mt.epiano([hz(m) for m in final], 4.5 * SPB, 1.0)
    place(st['keys'], x, tb(E))
    place(st['send'], x, tb(E), -2)
    place(st['pad'], mt.pad([hz(m) for m in DM9], 6.5 * SPB, 1.0, 1500), tb(E))
    place(st['sub'], mt.sub(hz(38), 4.0 * SPB, 0.9), tb(E))
    place(st['fx'], mt.cymbal_swell(tb(0)), 0.0, 0)
    # duck everything melodic under the kick
    duck = 1 - 0.35 * np.clip(kick_env, 0, 1)
    for key in ('sub', 'keys', 'pad'):
        st[key] *= duck[:, None]
    return st


GAIN = dict(kick=-5.0, clap=-3.0, hats=0.0, shaker=-10.0, sub=-17.0, keys=3.0, pad=-7.0, fx=-12.0, verb=-3.0)


def score(n):
    st = stems(n)
    wet = signal.fftconvolve(st.pop('send'), am.reverb_ir(2.8, 2.3), axes=0)[:n]
    out = wet * am.db(GAIN['verb'])
    for key, x in st.items():
        out += x * am.db(GAIN[key])
    return out


def design(n):
    sfx = np.zeros((n, 2))
    for seg in FM.FILM['segments']:
        t0 = seg['f0'] / FPS
        if seg.get('strobe'):
            place(sfx, am.shutter(), t0, -11 + rng.uniform(-1.5, 1.5))
        if seg.get('dive'):
            w, a = am.whoosh(0.20, 0.16, 300, 5200)
            place(sfx, w, seg['f1'] / FPS - a / SR, -9)
        if seg.get('land'):
            place(sfx, am.impact(0.9, 82, 40, 0.16, click=False), t0, -12)
            place(sfx, am.swish(0.5), t0 + 0.05, -16)
        if seg.get('masthead'):
            place(sfx, am.shimmer(1.3, 3000), t0 + 0.08, -20)
            place(sfx, am.impact(1.2, 60, 34, 0.35, click=False), t0, -13)
        if seg.get('whoosh_at') is not None:
            w, a = am.whoosh(0.30, 0.30, 160, 2800, pan_from=0.9, pan_to=-0.9)
            place(sfx, w, seg['whoosh_at'] / FPS - a / SR, -5)
        if 'passin' in seg:
            a0, a1 = seg['passin']
            w, a = am.whoosh((a1 - a0) / FPS * 0.55, (a1 - a0) / FPS * 0.6, 160, 3000, pan_from=0.9, pan_to=-0.9)
            place(sfx, w, (a0 + (a1 - a0) * 0.5) / FPS - a / SR, -6)
        if seg.get('kind') == 'end':
            e0 = seg['f0']
            place(sfx, am.impact(2.0, 62, 32, 0.6), e0 / FPS, -8)
            for kk in range(3):
                place(sfx, am.shutter(), (e0 + 8 * kk) / FPS, -12)
            place(sfx, am.impact(1.6, 58, 32, 0.5, click=False), (e0 + 32) / FPS, -12)
            place(sfx, am.shimmer(1.5, 3100), (e0 + 32) / FPS + 0.03, -18)
            place(sfx, mt.am.shimmer(1.0, 3900), (e0 + 48) / FPS + 0.03, -22)
            place(sfx, am.shimmer(1.4, 3500), (e0 + 64) / FPS, -18)
    return sfx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--sfx-only')
    a = ap.parse_args()
    dur = FM.FILM['end'] / FPS
    n = int(round(dur * SR))
    mus = score(n)
    sfx = design(n)
    fade = int(0.45 * SR)
    for x in (mus, sfx):
        x[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    mix, _ = am.master(mus + sfx * am.db(-1))
    am.write_wav(a.out, mix)
    import pyloudnorm as pyln
    print(f'mix {dur:.2f}s: {pyln.Meter(SR).integrated_loudness(mix):.1f} LUFS, peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS')
    if a.sfx_only:
        s, _ = am.master(sfx.copy(), target_lufs=-18.0)
        am.write_wav(a.sfx_only, s)
        print('sfx-only written')


if __name__ == '__main__':
    main()
