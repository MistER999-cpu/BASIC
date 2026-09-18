"""Draw the Win95 pointing-hand cursor as real pixel art.

Authored on a small grid and scaled up with nearest-neighbour, so the staircase
edges are genuine pixels rather than a smooth vector pretending to be one.
"""
import cv2, numpy as np, os

G, UP = (44, 34), 10          # grid h,w  and  upscale factor

HAND = [(12, 1), (16, 1), (16, 13), (18, 12), (20, 12), (21, 13), (21, 15),
        (23, 13), (25, 13), (26, 14), (26, 16), (28, 15), (30, 15), (31, 16),
        (31, 31), (29, 37), (26, 42), (13, 42), (9, 37), (4, 27), (3, 24),
        (4, 22), (6, 22), (9, 26), (11, 28), (12, 26)]

CUFF = [(11, 36), (27, 36), (27, 43), (11, 43)]

def draw():
    h, w = G
    pts = np.array(HAND, np.int32)
    lay = np.zeros((h, w, 4), np.uint8)
    cv2.fillPoly(lay, [pts], (255, 255, 255, 255))
    cv2.fillPoly(lay, [np.array(CUFF, np.int32)], (176, 205, 222, 255))
    cv2.polylines(lay, [pts], True, (0, 0, 0, 255), 1)
    big = cv2.resize(lay, (w * UP, h * UP), interpolation=cv2.INTER_NEAREST)
    # one hard pixel-grid outline pass so the silhouette reads at any size
    a = (big[:, :, 3] > 0).astype(np.uint8)
    ring = cv2.dilate(a, np.ones((3, 3), np.uint8), iterations=UP // 5) - a
    big[ring > 0] = (0, 0, 0, 255)
    return big

os.makedirs('assets/video/final/ui', exist_ok=True)
for name in ('cursor-rest',):
    im = draw()
    cv2.imwrite(f'assets/video/final/ui/{name}.png', im)
    print(f'{name}.png  {im.shape[1]}x{im.shape[0]}')
