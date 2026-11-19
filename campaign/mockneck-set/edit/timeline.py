"""Beat-locked edit decision list for the BASIC mock-neck set ad.

Music: first chorus of the supplied track. Chorus downbeat at 56.698 s, 137.694 BPM.
The ad starts 0.75 s before the downbeat (bass drop-out + riser), so beat n lands at
T(n) = 0.75 + n * P seconds of ad time.
"""
FPS = 24
W, H = 1080, 1920
P = 0.43575                 # seconds per beat
DROP_SRC = 56.698           # downbeat in the music file
PRE = 0.75                  # ad time of the downbeat
MUSIC_IN = DROP_SRC - PRE   # music file time at ad time 0
END_BEAT = 64
TAIL = 2.6                  # reverb tail after the last downbeat

def T(beat):
    return PRE + beat * P

DURATION = T(END_BEAT) + TAIL

C = 'campaign/mockneck-set/clips/'
# kind, colour, beat_in, beat_out, source file, src_in, src_out, extra
SHOTS = [
    dict(id='pre', clip=C + 'S7-black-cuff.mp4', colour='noir',      b0=None, b1=0,  src=(3.20, 3.95)),
    dict(id='flip_b', still='burgundy',  colour='burgundy', b0=0,  b1=1),
    dict(id='flip_c', still='chocolat',  colour='chocolat', b0=1,  b1=2),
    dict(id='flip_n', still='noir',      colour='noir',     b0=2,  b1=3),
    dict(id='S1', clip=C + 'S1-black-descent.mp4',       colour='noir',     b0=3,  b1=10, src=(0.45, 3.50)),
    dict(id='S2', clip=C + 'S2-chocolate-hem.mp4',       colour='chocolat', b0=10, b1=15, src=(0.60, 2.78)),
    dict(id='S3', clip=C + 'S3-burgundy-pause.mp4',      colour='burgundy', b0=15, b1=21, src=(0.20, 4.00)),
    dict(id='S4', clip=C + 'S4-black-collar.mp4',        colour='noir',     b0=21, b1=27, src=(0.00, 3.25)),
    dict(id='S5', clip=C + 'S5-chocolate-lean.mp4',      colour='chocolat', b0=27, b1=32, src=(0.40, 3.45)),
    dict(id='S6', clip=C + 'S6-burgundy-turn-fixed.mp4', colour='burgundy', b0=32, b1=40, src=(0.00, 4.00)),
    dict(id='S7', clip=C + 'S7-black-cuff.mp4',          colour='noir',     b0=40, b1=46, src=(0.55, 3.20)),
    dict(id='S8', clip=C + 'S8-chocolate-collar.mp4',    colour='chocolat', b0=46, b1=50, src=(1.00, 3.00)),
    dict(id='S9', clip=C + 'S9-burgundy-walk.mp4',       colour='burgundy', b0=50, b1=56, src=(0.00, 3.35)),
    dict(id='end', still='endcard',   colour=None,       b0=56, b1=None),
]

def shot_times(s):
    t0 = 0.0 if s['b0'] is None else T(s['b0'])
    t1 = DURATION if s['b1'] is None else T(s['b1'])
    return t0, t1

def frame_range(s):
    t0, t1 = shot_times(s)
    return round(t0 * FPS), round(t1 * FPS)

def src_time(s, t):
    """Source-clip time for ad time t inside shot s (constant speed)."""
    t0, t1 = shot_times(s)
    a, b = s['src']
    return a + (t - t0) * (b - a) / (t1 - t0)

if __name__ == '__main__':
    print(f'duration {DURATION:.3f}s  frames {round(DURATION*FPS)}')
    for s in SHOTS:
        t0, t1 = shot_times(s); f0, f1 = frame_range(s)
        sp = ''
        if 'src' in s:
            sp = f"speed {(s['src'][1]-s['src'][0])/(t1-t0):.2f}x"
        print(f"{s['id']:7s} {t0:6.2f}-{t1:6.2f}s  frames {f0:4d}-{f1:4d}  {sp}")
