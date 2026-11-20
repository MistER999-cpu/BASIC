"""Edit decision lists for the BASIC lookbook film, one part per colourway.

Grammar (after the reference lookbook): locked-off full-body pose flicks on 16th notes,
a full-body hold, and detail inserts (hem, collar, pocket/cuff) entered by a zoom-dive.
Everything sits on a 90 BPM grid: one beat = 16 frames at 24 fps, a 16th = 4 frames.
Frame 8 is the first downbeat (B0); frames 0-7 are the pass-by pickup.
"""

FPS = 24
BPM = 90
BEAT = 16                  # frames per beat at 90 BPM / 24 fps
ORIGIN = 8                 # frame of beat 0


def B(b):
    return int(round(ORIGIN + BEAT * b))


C = 'campaign/mockneck-set/lookbook/clips/'


def flick(f0, src, s0, dive=None, n=4):
    return dict(kind='clip', f0=f0, f1=f0 + n, src=src, s0=s0, speed=1.0, strobe=True, dive=dive)


NOIR = dict(
    name='noir',
    number='01',
    title='NOIR',
    clips={
        'N1': C + 'N1-noir-poses.mp4',
        'N2': C + 'N2-noir-walkin.mp4',
        'N3': C + 'N3-noir-turn.mp4',
        'N4': C + 'N4-noir-collar.mp4',
        'N5': C + 'N5-noir-hem.mp4',
        'N6': C + 'N6-noir-pocket.mp4',
    },
    # backdrop colour measured in each clip (top-left wall patch, RGB)
    backdrop={'N1': (131, 113, 90), 'N2': (130, 113, 90), 'N3': (139, 122, 98),
              'N4': (153, 123, 95), 'N5': (180, 163, 139), 'N6': (183, 164, 141)},
    reference_clip='N1',
    # full-body clips are scaled onto N1's framing so the jump cuts snap (scale, pivot in native px)
    align={'N2': (0.958, (360, 1192))},
    # native-px pivots
    pivots={'neck': (333, 352), 'hip_right': (458, 690), 'upper': (360, 420)},
    pass_frames=[33, 35, 37, 39],         # N1 profile frames used for the blurred pass-by
    pass_clip='N1',
    masthead=dict(src='N2', f0=56, f1=96, mask_dir='N2'),
    end=268,
    endlogo=(248, 268),
)

NOIR['segments'] = [
    # 1. pass-by wipe from black into the turn; the turn is under it from frame 0
    dict(kind='clip', f0=0, f1=40, src='N3', s0=10, speed=1.0, zoom=(1.07, 1.15), pivot='upper',
         passin=(0, 8), label=('small', NOIR['number'], NOIR['title'], 12, 36)),
    # 2. pose flicks (front, profile, back, three-quarter) on 16ths
    flick(B(2) + 0, 'N1', 1),
    flick(B(2) + 4, 'N1', 34),
    flick(B(2) + 8, 'N1', 54),
    flick(B(2) + 12, 'N1', 86),
    # 3. full-body hold with the masthead, dives into the hem
    dict(kind='clip', f0=B(3), f1=B(5.5), src='N2', s0=16, speed=1.0, masthead=True, dive='hip_right'),
    # 4. hem detail: back longer than front
    dict(kind='clip', f0=B(5.5), f1=B(7.25), src='N5', s0=52, speed=1.0, land=True,
         label=('detail', 'DOS ALLONGÉ', 'ourlet arrondi, plus long à l’arrière')),
    # 5. flicks, last one dives into the neck
    flick(B(7.25) + 0, 'N1', 58),
    flick(B(7.25) + 4, 'N1', 40),
    flick(B(7.25) + 8, 'N2', 84, dive='neck'),
    # 6. collar: hand slides away, jump cut to the clean collar
    dict(kind='clip', f0=B(8), f1=B(9.25), src='N4', s0=34, speed=1.0, land=True,
         label=('detail', 'COL MONTANT', 'le détail signature', B(8) + 4, B(10) - 2)),
    dict(kind='clip', f0=B(9.25), f1=B(10), src='N4', s0=78, speed=1.0,
         label=('detail', 'COL MONTANT', 'le détail signature', B(8) + 4, B(10) - 2)),
    # 7. flicks, last one dives into the pocket
    flick(B(10) + 0, 'N1', 88),
    flick(B(10) + 4, 'N2', 88, dive='hip_right'),
    # 8. pocket and cuff
    dict(kind='clip', f0=B(10.5), f1=B(12), src='N6', s0=10, speed=1.0, land=True,
         label=('detail', 'POCHES LATÉRALES', 'manches larges, poignets ouverts')),
    # 9. closing flicks
    flick(B(12) + 0, 'N1', 36),
    flick(B(12) + 4, 'N1', 60),
    flick(B(12) + 8, 'N1', 6),
    flick(B(12) + 12, 'N1', 90),
    # 10. final gaze, slowed, wiped out to black by the pass-by
    dict(kind='clip', f0=B(13), f1=NOIR['end'], src='N3', s0=76, speed=0.6, zoom=(1.0, 1.06), pivot='upper',
         passout=(B(14.5), B(15))),
]

PARTS = {'noir': NOIR}
