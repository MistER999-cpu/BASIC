"""Cut the generated stills off their backdrops into premultiplied RGBA PNGs.

Item flat-lays sit on flat studio sweeps with a soft cast shadow; the reveals
sit on green. Both reduce to the same problem - decide background from a border
estimate - but a cast shadow shares the backdrop's colour and only differs in
lightness, so lightness alone cannot be the test or every shadow survives.
"""
import cv2, numpy as np, os, sys, glob, json

def largest(mask, keep=0.04):
    """Keep every blob within `keep` of the biggest - shoes come in pairs."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n < 2: return mask
    areas = st[1:, cv2.CC_STAT_AREA]
    big = areas.max()
    out = np.zeros_like(mask)
    for i, a in enumerate(areas, 1):
        if a >= big * keep: out[lab == i] = 255
    return out

def refine(mask, r=3):
    k = np.ones((r * 2 + 1,) * 2, np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    return cv2.GaussianBlur(mask, (0, 0), 1.6)

def key_green(bgr):
    """Green screen: the backdrop is the only strongly negative-a* region."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(int)
    a, b = lab[:, :, 1] - 128, lab[:, :, 2] - 128
    # green sits at very low a*; skin, cloth and hair all sit well above it
    fg = ((a > -22) | (b < -18)).astype(np.uint8) * 255
    fg = largest(refine(fg, 4), keep=0.5)
    # de-spill: pull green-dominant pixels back toward their own grey
    out = bgr.astype(float)
    g, rb = out[:, :, 1], np.maximum(out[:, :, 0], out[:, :, 2])
    over = np.clip(g - rb, 0, None)
    out[:, :, 1] = g - over * 0.9
    return out, fg

def key_sweep(bgr):
    """Studio sweep with a soft cast shadow.

    Thresholding on distance-from-backdrop cannot separate the two: a mid-grey
    garment on a white sweep and a shadow on that sweep are both "the backdrop,
    darker", and any threshold that drops one drops the other. So the threshold
    only seeds the decision - it marks pixels that are certainly garment and
    certainly sweep - and GrabCut settles the rest from the full colour
    distributions, where shadow reads as backdrop and grey suede does not.
    """
    H, W = bgr.shape[:2]
    sc = 640 / max(H, W)
    sm = cv2.resize(bgr, (int(W * sc), int(H * sc)), interpolation=cv2.INTER_AREA)
    h, w = sm.shape[:2]

    lab = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB).astype(float)
    m = max(4, min(h, w) // 40)
    bg = np.median(np.concatenate([lab[:m].reshape(-1, 3), lab[-m:].reshape(-1, 3),
                                   lab[:, :m].reshape(-1, 3), lab[:, -m:].reshape(-1, 3)]), axis=0)
    dL = np.abs(lab[:, :, 0] - bg[0])
    dC = np.hypot(lab[:, :, 1] - bg[1], lab[:, :, 2] - bg[2])
    score = np.maximum(dL / 26.0, dC / 9.0)

    gc = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    gc[score > 1.0] = cv2.GC_PR_FGD
    gc[cv2.erode((score > 2.2).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0] = cv2.GC_FGD
    gc[score < 0.45] = cv2.GC_BGD
    gc[:m] = gc[-m:] = cv2.GC_BGD
    gc[:, :m] = gc[:, -m:] = cv2.GC_BGD
    if (gc == cv2.GC_FGD).sum() < 50:            # nothing certain - fall back
        gc[score > 1.0] = cv2.GC_FGD
    try:
        cv2.grabCut(sm, gc, None, np.zeros((1, 65), np.float64),
                    np.zeros((1, 65), np.float64), 5, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        pass
    fg = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    fg = largest(fg)
    ff = fg.copy()
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 255)
    fg = fg | cv2.bitwise_not(ff)

    fg = cv2.resize(fg, (W, H), interpolation=cv2.INTER_LINEAR)
    fg = cv2.GaussianBlur(fg, (0, 0), max(1.2, 1 / sc * 0.5))
    fg = np.clip((fg.astype(float) - 110) * 4 + 128, 0, 255).astype(np.uint8)
    return bgr.astype(float), fg

def run(paths, outdir, mode):
    os.makedirs(outdir, exist_ok=True)
    rep = []
    for p in paths:
        im = cv2.imread(p)
        rgb, a = (key_green if mode == 'green' else key_sweep)(im)
        ys, xs = np.where(a > 8)
        if not len(ys):
            print(f'  !! {os.path.basename(p)}: nothing matted'); continue
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        crop = np.dstack([rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]]).astype(np.uint8)
        name = os.path.splitext(os.path.basename(p))[0] + '.png'
        cv2.imwrite(os.path.join(outdir, name), crop)
        cover = (a > 128).mean()
        rep.append((name, x1 - x0, y1 - y0, round(float(cover), 3)))
        print(f'  {name[:44]:46s} {x1-x0:4d}x{y1-y0:4d}  fill {cover:.1%}')
    return rep

if __name__ == '__main__':
    print('items (studio sweep)')
    run(sorted(glob.glob('assets/video/items/*.jpe*g')), 'assets/video/cut/items', 'sweep')
    print('reveals (green screen)')
    run(sorted(glob.glob('assets/video/reveals/*.jpe*g')), 'assets/video/cut/reveals', 'green')
