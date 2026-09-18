"""Measure each reveal so the four can be matched to one camera.

Fitting a cut-out by its bounding box makes an outstretched arm shrink the whole
figure, and a half-body plate scale up to meet a full-length one. Head height
does neither: it is the same for a person whatever they are doing with their
arms, and it is the thing the eye actually reads as camera distance. So measure
the head, and let the scene scale on that and hang every figure from the crown.
"""
import cv2, numpy as np, glob, json, os

def measure(path):
    a = cv2.imread(path, cv2.IMREAD_UNCHANGED)[:, :, 3]
    H, W = a.shape
    solid = (a > 128)
    w = solid.sum(1).astype(float)
    w = cv2.GaussianBlur(w.reshape(-1, 1), (0, 0), 5).ravel()

    top = int(np.argmax(w > W * 0.02))                 # crown
    lim = top + max(20, int(H * 0.32))
    # the head swells to its widest, the neck pinches below it, the shoulders
    # flare out again. Take the widest point of the head, then the narrowest
    # point between it and a third of the way down: that trough is the neck.
    seg = w[top:lim]
    if len(seg) < 12: return None
    crown = int(np.argmax(seg[:max(4, len(seg) // 2)]))
    neck = crown + int(np.argmin(seg[crown:]))
    headH = max(neck, int(H * 0.04))

    # torso centre, not bbox centre - what we want under the canvas midline
    lo, hi = top + headH, min(H, top + headH * 4)
    ys, xs = np.where(solid[lo:hi])
    torsoCx = float(xs.mean() / W) if len(xs) else 0.5

    return {'w': W, 'h': H, 'headTop': int(top), 'headH': int(headH),
            'torsoCx': round(torsoCx, 4), 'heads': round(H / headH, 2)}

out = {}
for p in sorted(glob.glob('assets/video/final/reveals/*.png')):
    k = os.path.splitext(os.path.basename(p))[0]
    out[k] = measure(p)
    m = out[k]
    print(f'{k:14s} {m["w"]}x{m["h"]}  headH {m["headH"]:4d}  '
          f'= {m["heads"]:5.2f} heads tall   torsoCx {m["torsoCx"]}')
json.dump(out, open('tools/paint/reveals.json', 'w'), indent=1)
