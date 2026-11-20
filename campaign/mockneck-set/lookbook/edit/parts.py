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

CHOCOLAT = dict(
    name='chocolat',
    number='02',
    title='CHOCOLAT',
    key=3,                                   # temp score transposed up a minor third
    clips={
        'C1': C + 'C1-chocolat-poses.mp4',
        'C2': C + 'C2-chocolat-walkin.mp4',
        'C3': C + 'C3-chocolat-plinth.mp4',
        'C4': C + 'C4-chocolat-spin.mp4',
        'C5': C + 'C5-chocolat-hem.mp4',
        'C6': C + 'C6-chocolat-collar.mp4',
    },
    backdrop={'C1': (130, 113, 89), 'C2': (121, 106, 90), 'C3': (111, 91, 71),
              'C4': (119, 102, 82), 'C5': (172, 142, 108), 'C6': (200, 179, 156)},
    reference_backdrop=(131, 113, 90),       # Noir's wall, so the parts match
    reference_clip='C1',
    exposure={'C2': 1.0},
    align={'C1': (0.97, (360, 1200))},        # onto the Noir master figure size
    pivots={'neck': (375, 356), 'hip_right': (464, 705), 'upper': (360, 420), 'bottom': (360, 1280)},
    pass_frames=[42, 44, 46, 48],
    pass_clip='C1',
    masthead=dict(src='C1', mask_dir='C1', baseline=356),
    small_label=dict(align='right'),
    end=268,
    endlogo=(248, 268),
)

CHOCOLAT['segments'] = [
    # 1. pass-by wipe into the slow-motion turn
    dict(kind='clip', f0=0, f1=40, src='C4', s0=0, speed=0.6, zoom=(1.0, 1.06), pivot='upper',
         passin=(0, 8), label=('small', CHOCOLAT['number'], CHOCOLAT['title'], 12, 36)),
    # 2. pose flicks: front, stride, back, look back
    flick(B(2) + 0, 'C1', 4),
    flick(B(2) + 4, 'C1', 44),
    flick(B(2) + 8, 'C1', 52),
    flick(B(2) + 12, 'C1', 67),
    # 3. hold: front into the power stance, masthead behind the hijab, dive to the hip
    dict(kind='clip', f0=B(3), f1=B(5.5), src='C1', s0=8, speed=0.75, masthead=True, dive='hip_right'),
    # 4. hem in silhouette
    dict(kind='clip', f0=B(5.5), f1=B(7.25), src='C5', s0=0, speed=1.0, land=True,
         label=('detail', 'DOS ALLONGÉ', 'ourlet arrondi, plus long à l\u2019arrière')),
    # 5. flicks, last dives into the neck
    flick(B(7.25) + 0, 'C1', 84),
    flick(B(7.25) + 4, 'C1', 54),
    flick(B(7.25) + 8, 'C1', 32, dive='neck'),
    # 6. collar macro under the hijab
    dict(kind='clip', f0=B(8), f1=B(10), src='C6', s0=8, speed=1.0, land=True,
         label=('detail', 'COL MONTANT', 'sous le hijab, le détail signature')),
    # 7. flicks
    flick(B(10) + 0, 'C1', 70),
    flick(B(10) + 4, 'C1', 88),
    # 8. the plinth: sleeves fall open
    dict(kind='clip', f0=B(10.5), f1=B(12), src='C3', s0=50, speed=1.0,
         label=('detail', 'MANCHES LARGES', 'poignets ouverts, tombé ample')),
    # 9. closing flicks
    flick(B(12) + 0, 'C1', 30),
    flick(B(12) + 4, 'C1', 50),
    flick(B(12) + 8, 'C1', 80),
    flick(B(12) + 12, 'C1', 12),
    # 10. floor-level walk-in; her trouser leg wipes the lens into the logo
    dict(kind='clip', f0=B(13), f1=B(15), src='C2', s0=62, speed=1.0, zoom=(1.09, 1.09), pivot='bottom',
         whoosh_at=240),
]

PARTS = {'noir': NOIR, 'chocolat': CHOCOLAT}
