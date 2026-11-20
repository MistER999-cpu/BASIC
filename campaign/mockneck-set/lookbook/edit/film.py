"""Edit decision list for the full BASIC lookbook film (all three colourways, ~24.7 s).

90 BPM grid as in parts.py: one beat = 16 frames, a 16th = 4 frames, beat 0 at frame 8.
Noir B0-B10, Chocolat B10-B20, Burgundy B20-B28.75, roll call B28.75-B30, end card B30-B36.5.
"""
from parts import B, C, FPS, BPM, BEAT, ORIGIN  # noqa: F401


def flick(f0, src, s0, dive=None, n=4):
    return dict(kind='clip', f0=f0, f1=f0 + n, src=src, s0=s0, speed=1.0, strobe=True, dive=dive)


FILM = dict(
    name='film',
    clips={
        'N1': C + 'N1-noir-poses.mp4', 'N2': C + 'N2-noir-walkin.mp4', 'N3': C + 'N3-noir-turn.mp4',
        'N4': C + 'N4-noir-collar.mp4', 'N5': C + 'N5-noir-hem.mp4', 'N6': C + 'N6-noir-pocket.mp4',
        'C1': C + 'C1-chocolat-poses.mp4', 'C2': C + 'C2-chocolat-walkin.mp4', 'C3': C + 'C3-chocolat-plinth.mp4',
        'C4': C + 'C4-chocolat-spin.mp4', 'C5': C + 'C5-chocolat-hem.mp4', 'C6': C + 'C6-chocolat-collar.mp4',
        'B1': C + 'B1-burgundy-poses.mp4', 'B2': C + 'B2-burgundy-hairturn.mp4', 'B3': C + 'B3-burgundy-floor.mp4',
        'B4': C + 'B4-burgundy-sleeve.mp4', 'B5': C + 'B5-burgundy-back.mp4',
    },
    backdrop={'N1': (131, 113, 90), 'N2': (130, 113, 90), 'N3': (139, 122, 98), 'N4': (153, 123, 95),
              'N5': (180, 163, 139), 'N6': (183, 164, 141),
              'C1': (130, 113, 89), 'C2': (121, 106, 90), 'C3': (111, 91, 71), 'C4': (119, 102, 82),
              'C5': (172, 142, 108), 'C6': (200, 179, 156),
              'B1': (130, 113, 89), 'B2': (134, 119, 96), 'B3': (161, 143, 121), 'B4': (186, 168, 144),
              'B5': (69, 53, 38)},
    reference_clip='N1',
    exposure={'C2': 1.0, 'B5': 1.06},
    # burgundy shifted toward the product sheet's wine (measured hue/sat per clip -> ~hue 340, S 0.6)
    burgundy={'B1': dict(dh=-16.0, ks=1.30, kv=1.12), 'B2': dict(dh=-22.0, ks=1.24, kv=1.32),
              'B3': dict(dh=-6.0, ks=1.0, kv=1.0), 'B4': dict(dh=-8.0, ks=1.0, kv=0.98),
              'B5': dict(dh=-6.0, ks=0.97, kv=1.0)},
    align={'N2': (0.958, (360, 1192)), 'C1': (0.97, (360, 1200)), 'B1': (1.034, (363, 309))},
    pivots={'upper': (360, 420), 'bottom': (360, 1280),
            'neck_n': (333, 352), 'hip_n': (458, 690),
            'neck_c': (375, 356), 'hip_c': (464, 705),
            'neck_b': (366, 330)},
    pass_frames=[33, 35, 37, 39],
    pass_clip='N1',
    end=B(36.5),
)

L = lambda *a: ('detail',) + a  # noqa: E731

FILM['segments'] = [
    # ---------------- NOIR -------------------------------------------------------------
    dict(kind='clip', f0=0, f1=B(1.5), src='N3', s0=10, speed=1.0, zoom=(1.07, 1.14), pivot='upper',
         passin=(0, 8), label=('small', '01', 'NOIR', 12, B(1.5) - 3)),
    flick(B(1.5) + 0, 'N1', 1), flick(B(1.5) + 4, 'N1', 34), flick(B(1.5) + 8, 'N1', 54), flick(B(1.5) + 12, 'N1', 86),
    dict(kind='clip', f0=B(2.5), f1=B(4.5), src='N2', s0=24, speed=1.0, dive='hip_n',
         masthead=dict(word='NOIR', mask_dir='N2')),
    dict(kind='clip', f0=B(4.5), f1=B(6), src='N5', s0=60, speed=1.0, land=True,
         label=L('DOS ALLONGÉ', 'ourlet arrondi, plus long à l’arrière')),
    flick(B(6) + 0, 'N1', 58), flick(B(6) + 4, 'N2', 84, dive='neck_n'),
    dict(kind='clip', f0=B(6.5), f1=B(8), src='N4', s0=34, speed=1.0, land=True,
         label=L('COL MONTANT', 'le détail signature')),
    flick(B(8) + 0, 'N1', 88), flick(B(8) + 4, 'N2', 88, dive='hip_n'),
    dict(kind='clip', f0=B(8.5), f1=B(9.75), src='N6', s0=12, speed=1.0, land=True,
         label=L('POCHES LATÉRALES', 'discrètes, dans la couture')),
    # colour jump on the same framing
    flick(B(9.75), 'C1', 4),
    # ---------------- CHOCOLAT ---------------------------------------------------------
    dict(kind='clip', f0=B(10), f1=B(11.5), src='C4', s0=0, speed=0.6, zoom=(1.0, 1.05), pivot='upper',
         label=('small', '02', 'CHOCOLAT', B(10) + 3, B(11.5) - 3), small_align='right'),
    flick(B(11.5) + 0, 'C1', 44), flick(B(11.5) + 4, 'C1', 52), flick(B(11.5) + 8, 'C1', 67), flick(B(11.5) + 12, 'C1', 84),
    dict(kind='clip', f0=B(12.5), f1=B(14.5), src='C1', s0=8, speed=0.75, dive='hip_c',
         masthead=dict(word='CHOCOLAT', mask_dir='C1', baseline=356)),
    dict(kind='clip', f0=B(14.5), f1=B(15.75), src='C5', s0=2, speed=1.0, land=True),
    flick(B(15.75) + 0, 'C1', 88), flick(B(15.75) + 4, 'C1', 32, dive='neck_c'),
    dict(kind='clip', f0=B(16.25), f1=B(17.5), src='C6', s0=8, speed=1.0, land=True,
         label=L('COL MONTANT', 'porté sous le hijab')),
    dict(kind='clip', f0=B(17.5), f1=B(18.75), src='C3', s0=46, speed=1.0,
         label=L('MANCHES LARGES', 'poignets ouverts, tombé ample')),
    dict(kind='clip', f0=B(18.75), f1=B(20), src='C2', s0=66, speed=1.0, zoom=(1.09, 1.09), pivot='bottom',
         whoosh_at=B(20) - 3),
    # ---------------- BURGUNDY ---------------------------------------------------------
    dict(kind='clip', f0=B(20), f1=B(21.5), src='B2', s0=0, speed=0.75, zoom=(1.0, 1.05), pivot='upper',
         label=('small', '03', 'BURGUNDY', B(20) + 3, B(21.5) - 3)),
    flick(B(21.5) + 0, 'B1', 4), flick(B(21.5) + 4, 'B1', 42), flick(B(21.5) + 8, 'B1', 62), flick(B(21.5) + 12, 'B1', 86),
    dict(kind='clip', f0=B(22.5), f1=B(24.25), src='B1', s0=30, speed=0.6, dive='neck_b',
         masthead=dict(word='BURGUNDY', mask_dir='B1')),
    dict(kind='clip', f0=B(24.25), f1=B(25.75), src='B4', s0=34, speed=1.0, land=True,
         label=L('ÉPAULES TOMBANTES', 'coupe oversize, col montant')),
    dict(kind='clip', f0=B(25.75), f1=B(27), src='B3', s0=64, speed=1.0,
         label=L('JAMBE LARGE', 'taille haute, tombé fluide')),
    dict(kind='clip', f0=B(27), f1=B(28.75), src='B5', s0=60, speed=1.0, zoom=(1.0, 1.04), pivot='upper'),
    # ---------------- ROLL CALL --------------------------------------------------------
    flick(B(28.75) + 0, 'N1', 2), flick(B(28.75) + 4, 'C1', 4), flick(B(28.75) + 8, 'B1', 4),
    flick(B(28.75) + 12, 'N1', 54), flick(B(28.75) + 16, 'C1', 52),
    # ---------------- END CARD ---------------------------------------------------------
    dict(kind='end', f0=B(30), f1=B(36.5)),
]

# events the score and sound design hang on
BLOCKS = [(0, 0), (10, 3), (20, 5)]          # (start beat, key shift)
END_BEAT = 30
