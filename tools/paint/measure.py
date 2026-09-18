"""Locate the interactive regions inside the generated paint-program window."""
import cv2, numpy as np, json, glob

src = sorted(glob.glob('assets/video/ui/*.jpe*g'))[0]
im = cv2.imread(src); H, W = im.shape[:2]
g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
I = lambda r: [int(v) for v in r]

def blobs(mask, lo, hi, ar=None, xr=None):
    n, _, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if not (lo <= a <= hi): continue
        if ar and not (ar[0] <= w / h <= ar[1]): continue
        if xr and not (xr[0] <= x <= xr[1]): continue
        out.append((x, y, w, h))
    return out

op = lambda m, k: cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((k, k), np.uint8))

# canvas - the one huge near-white blob
canvas = max(blobs(op(g > 235, 15), 200_000, W * H), key=lambda r: r[2] * r[3])

# tray slots - mid-grey panels in the column left of the canvas
left = np.zeros_like(g); left[:, :canvas[0]] = 255
slots = sorted(blobs(op((g > 150) & (g < 195) & (left > 0), 9),
                     8_000, 400_000, (0.5, 2.2), (W * .17, canvas[0])), key=lambda r: r[1])

# enter / restart - the two stacked panels under the tool grid. Find the button
# face as the widest unbroken run of its own flat tone across a row that cuts
# through both, then read the rules above, between and below them.
def runs(idx, gap):
    out, seen = [], -10**9
    for v in idx:
        if v - seen > gap: out.append(v)
        seen = v
    return out

row = g[1800, :max(200, slots[0][0])].astype(int)
flat = np.abs(row - np.median(row[row > 180])) < 8
best, run, start = (0, 0), 0, 0
for i, f in enumerate(list(flat) + [False]):
    if f:
        if run == 0: start = i
        run += 1
    else:
        if run > best[1] - best[0]: best = (start, i)
        run = 0
bx0, bx1 = best

# The enter/restart borders are the only dark rows that run the FULL width of
# the button face - the label glyphs darken the middle only, so they screen out.
# The enter/restart borders are the only dark rows that run the FULL width of
# the button face - the label glyphs darken the middle only, so they screen out.
# "enter" is by far the tallest panel in that band, so the widest gap between
# consecutive rules is its body and "restart" is the panel directly beneath.
face = g[1600:2300, bx0 + 10:bx1 - 10]
rule = runs([1600 + i for i, r in enumerate(face) if (r < 160).mean() > 0.85], 12)
k = max(range(len(rule) - 2), key=lambda i: rule[i + 1] - rule[i])
top, mid, bot = rule[k], rule[k + 1], rule[k + 2]
enter   = (bx0, top, bx1 - bx0, mid - top)
restart = (bx0, mid, bx1 - bx0, bot - mid)

# heart - dark outline inside the lower-left of the canvas
cx, cy, cw, ch = canvas
sub = g[cy + int(ch * .78):cy + ch, cx:cx + int(cw * .30)]
hb = max(blobs(op(sub < 140, 3), 300, 60_000), key=lambda r: r[2] * r[3])
heart = (cx + hb[0], cy + int(ch * .78) + hb[1], hb[2], hb[3])

# palette swatches - saturated squares below the columns
hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
low = np.zeros_like(g); low[cy + ch:, :] = 255
sw = sorted(blobs(op(((hsv[:, :, 1] > 40) | (g < 90) | (g > 245)) & (low > 0), 7),
                  3_000, 60_000, (0.6, 1.6)), key=lambda r: (r[1], r[0]))

out = {'src': src, 'w': W, 'h': H, 'canvas': I(canvas), 'slots': [I(s) for s in slots],
       'enter': I(enter), 'restart': I(restart), 'heart': I(heart),
       'swatches': [I(s) for s in sw]}
print(f'image      {W}x{H}')
print(f'canvas     {out["canvas"]}')
print(f'slots      {len(slots)}  pitch {slots[1][1]-slots[0][1]}px  size {slots[0][2]}x{slots[0][3]}')
print(f'enter      {out["enter"]}')
print(f'restart    {out["restart"]}')
print(f'heart      {out["heart"]}')
print(f'swatches   {len(sw)}')
json.dump(out, open('tools/paint/ui.json', 'w'), indent=1)
