#!/usr/bin/env python3
"""Fit a pivoting lever to the tracked hand, and emit its angle per frame.

    python3 tools/fit-lever.py out/hand.json 1.90 3.05 > assets/lever.json

The mimed grip traces an arc, so a least-squares circle through the hand
positions during grab-and-pull recovers where the lever's pivot would have to
be and how long its arm is. The handle is then drawn as a rigid rod at that
pivot, and its knob sits in her hand for the whole gesture.
"""
import sys, json
import numpy as np

W, H = 1080, 1920            # work in pixels; x and y are not the same scale

def smooth(v, k=5):
    pad = np.r_[np.repeat(v[0], k//2), v, np.repeat(v[-1], k//2)]
    return np.convolve(pad, np.ones(k)/k, mode='valid')

def fit_pivot(x, y):
    """Search plausible pivots for the one giving the most constant arm length.

    A free circle fit is degenerate here: the mimed arc is shallow enough to be
    almost a straight line, which sends an algebraic fit off to a tiny radius
    with a huge residual. Constraining the pivot to where a machine's lever
    could actually be mounted - below the grip, on the gesture side - and
    scoring by how constant the arm stays recovers a usable lever.
    """
    best = None
    for cx in np.arange(0.00, 0.30, 0.005) * W:
        for cy in np.arange(0.55, 1.00, 0.005) * H:
            r = np.hypot(x - cx, y - cy)
            if not (0.12 * H <= r.mean() <= 0.45 * H):
                continue
            score = r.std() / r.mean()
            if best is None or score < best[0]:
                best = (score, cx, cy, r.mean())
    if best is None:
        raise SystemExit('no plausible pivot found')
    return best[1], best[2], best[3], best[0]

def main():
    track = json.load(open(sys.argv[1]))
    t0, t1 = float(sys.argv[2]), float(sys.argv[3])
    pts = [(r['t'], r['x']*W, r['y']*H) for r in track if r['x'] is not None]
    act = [(t, x, y) for t, x, y in pts if t0 <= t <= t1]
    if len(act) < 6:
        raise SystemExit('not enough tracked frames in the gesture window')

    tx = smooth(np.array([p[1] for p in act]))
    ty = smooth(np.array([p[2] for p in act]))
    cx, cy, R, score = fit_pivot(tx, ty)
    resid = np.hypot(tx - cx, ty - cy) - R

    ang = lambda x, y: float(np.degrees(np.arctan2(x - cx, cy - y)))  # 0 = straight up
    sx = smooth(np.array([p[1] for p in pts]))
    sy = smooth(np.array([p[2] for p in pts]))
    angles = [(pts[i][0], ang(sx[i], sy[i])) for i in range(len(pts))]
    a_act = [a for t, a in angles if t0 <= t <= t1]

    out = {
        'pivot':  {'x': round(cx / W, 5), 'y': round(cy / H, 5)},
        'armPx':  round(float(R), 1),
        'armFrac': round(float(R) / H, 5),
        'fitResidualPx': round(float(np.abs(resid).mean()), 1),
        'angleRest': round(min(a_act), 2),
        'anglePulled': round(max(a_act), 2),
        'track': [{'t': round(t, 4), 'a': round(a, 3)} for t, a in angles],
    }
    print(json.dumps(out, indent=1))
    print(f'pivot ({cx:.0f},{cy:.0f})px  arm {R:.0f}px  '
          f'mean residual {np.abs(resid).mean():.1f}px  '
          f'sweep {min(a_act):.1f}deg -> {max(a_act):.1f}deg  '
          f'(rel. spread {score*100:.1f}%)', file=sys.stderr)

if __name__ == '__main__':
    main()
