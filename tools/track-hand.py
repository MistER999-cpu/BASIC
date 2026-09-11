#!/usr/bin/env python3
"""Track the lever hand so the handle can be drawn onto it.

    python3 tools/track-hand.py assets/base/base.mp4 1.0 3.6 > out/hand.json

Finds skin-toned pixels in the gesture side of the frame, ignores the torso by
keeping only the blob nearest the top, and reports its centroid per frame.
"""
import subprocess, sys, json
import numpy as np
from scipy import ndimage

def frames(path, t0, t1, fps, w, h):
    raw = subprocess.run(['ffmpeg','-v','error','-ss',str(t0),'-to',str(t1),
        '-i',path,'-vf',f'fps={fps},scale={w}:{h}','-f','rawvideo',
        '-pix_fmt','rgb24','-'],capture_output=True).stdout
    n = len(raw)//(w*h*3)
    return np.frombuffer(raw,np.uint8)[:n*w*h*3].reshape(n,h,w,3).astype(np.float32)

def main():
    path, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    FPS, W, H = 24, 270, 480                      # quarter res is plenty
    ims = frames(path, t0, t1, FPS, W, H)

    # backdrop from the top strip, which the subject never reaches
    bg = np.median(ims[0][:20].reshape(-1,3), axis=0)

    out = []
    for i, im in enumerate(ims):
        r, g, b = im[...,0], im[...,1], im[...,2]
        mx, mn = im.max(2), im.min(2)
        # skin: warm, reasonably saturated, brighter than the backdrop
        skin = ((r > g) & (g > b) & (r - b > 18) & (mx - mn > 14) &
                (r > 90) & (np.linalg.norm(im - bg, axis=2) > 26))
        # Search only the arm's own corridor. The face is also skin-toned and
        # sits higher than the hand for most of the gesture, so a plain
        # "topmost blob" rule tracks the face instead.
        box = np.zeros_like(skin)
        box[int(H*0.24):int(H*0.64), int(W*0.04):int(W*0.38)] = True
        skin &= box
        skin = ndimage.binary_opening(skin, np.ones((3,3)))

        lbl, n = ndimage.label(skin)
        best = None
        for k in range(1, n+1):
            ys, xs = np.where(lbl == k)
            if len(ys) < 80: continue
            # hand, not forearm: take the upper quarter of the blob
            cut = np.percentile(ys, 25)
            sel = ys <= cut
            if best is None or len(ys) > best[3]:
                best = (ys.mean(), float(xs[sel].mean())/W, float(ys[sel].mean())/H, int(len(ys)))
        t = t0 + i/FPS
        out.append({'t': round(t,4),
                    'x': round(best[1],4) if best else None,
                    'y': round(best[2],4) if best else None,
                    'px': best[3] if best else 0})
    print(json.dumps(out))

if __name__ == '__main__':
    main()
