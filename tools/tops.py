#!/usr/bin/env python3
"""Pin the four tank colourways to one silhouette.

    python3 tools/tops.py --indir assets/products --outdir assets/tops

The colourways were generated rather than photographed four times, and they
drift: pairwise silhouette IoU runs 0.94-0.99, with hem widths spread 57px
across a 1091px garment. The pairs cluster - brown/black at 0.988 and
white/beige at 0.977, but only 0.94 across that divide - which is the
signature of two generation seeds rather than one garment.

That drift did not matter for the slot reveal, where reels are in motion. It
matters here: the top slot changes colour and nothing else, so anything else
that moves on the cut reads as a glitch rather than as a colour change.

The four alphas are intersected. Using any single colourway's mask, or their
union, would push the mask past the garment on the others and composite
backdrop into the edge; the intersection can only ever fall inside all four.
It costs beige 5.9%, white 4.2%, brown 2.1% and black 0.9% of area, all of it
in a thin band at the outer edge.
"""
import os, sys, json
import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import probe, read_rgb, write_rgba

ORDER = ['white', 'brown', 'beige', 'black']


def read_rgba(path):
    w, h = probe(path)
    import subprocess
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-frames:v', '1',
                          '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'],
                         capture_output=True).stdout
    if len(raw) != w * h * 4:
        raise SystemExit(f'{path}: decoded {len(raw)} bytes, expected {w*h*4}')
    return np.frombuffer(raw, np.uint8).reshape(h, w, 4).astype(np.float32)


def main():
    args = sys.argv[1:]
    indir, outdir = 'assets/products', 'assets/tops'
    if '--indir' in args:
        i = args.index('--indir'); indir = args[i + 1]; del args[i:i + 2]
    if '--outdir' in args:
        i = args.index('--outdir'); outdir = args[i + 1]; del args[i:i + 2]

    ims = {}
    for name in ORDER:
        p = os.path.join(indir, name + '.png')
        if not os.path.exists(p):
            raise SystemExit(f'missing colourway: {p}')
        ims[name] = read_rgba(p)

    shapes = {v.shape[:2] for v in ims.values()}
    if len(shapes) != 1:
        raise SystemExit(f'colourways are not on one canvas: {shapes}')

    shared = np.ones(next(iter(ims.values())).shape[:2], bool)
    for v in ims.values():
        shared &= (v[..., 3] / 255.0) > 0.5

    lbl, n = ndimage.label(shared)
    sizes = ndimage.sum(shared, lbl, range(1, n + 1))
    shared = lbl == (int(np.argmax(sizes)) + 1)

    # a soft edge on the shared boundary, so the silhouette does not alias
    band = 2
    inner = ndimage.binary_erosion(shared, np.ones((3, 3)), iterations=band)
    alpha = ndimage.gaussian_filter(np.where(shared, 1.0, 0.0), 1.1)
    alpha = np.where(inner, 1.0, alpha)
    alpha = np.where(ndimage.binary_dilation(shared, np.ones((3, 3)),
                                             iterations=band), alpha, 0.0)

    ys, xs = np.nonzero(alpha > 0.06)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1

    os.makedirs(outdir, exist_ok=True)
    manifest = []
    for name in ORDER:
        own = (ims[name][..., 3] / 255.0) > 0.5
        lost = 100 * (1 - shared.sum() / own.sum())
        rgba = np.dstack([ims[name][y0:y1, x0:x1, :3], alpha[y0:y1, x0:x1] * 255])
        dst = os.path.join(outdir, name + '.png')
        write_rgba(dst, rgba)
        manifest.append({'name': name, 'file': dst,
                         'w': int(x1 - x0), 'h': int(y1 - y0),
                         'areaLostPct': round(float(lost), 2)})
        print(f'  {name:6} {x1-x0:4}x{y1-y0:<4}  gives up {lost:4.1f}% of its own mask')

    with open(os.path.join(outdir, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=2)
    print(f'\n  shared silhouette {x1-x0}x{y1-y0} -> {outdir}/')


if __name__ == '__main__':
    main()
