#!/usr/bin/env python3
"""Take three product photos, cut them out, and install them as the reels.

    python3 tools/ingest.py assets/incoming          # a folder
    python3 tools/ingest.py shots.zip                # or a zip

Filenames do not matter. Each photo is matted off its backdrop, then the three
are sorted by the mean colour of the garment itself: lightest is white, darkest
is black, the remaining one is brown. All three are written with one shared
crop so the product cannot jump size or position as a reel spins.
"""
import os, sys, zipfile, tempfile, shutil
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import matte, write_rgba

EXT = ('.jpg', '.jpeg', '.png', '.webp', '.avif', '.bmp', '.tif', '.tiff')


def gather(src):
    if os.path.isdir(src):
        files = [os.path.join(src, f) for f in sorted(os.listdir(src))
                 if f.lower().endswith(EXT) and not f.startswith('.')]
        return files, None
    if zipfile.is_zipfile(src):
        tmp = tempfile.mkdtemp(prefix='ingest-')
        with zipfile.ZipFile(src) as z:
            z.extractall(tmp)
        files = []
        for root, _, names in os.walk(tmp):
            if '__MACOSX' in root:
                continue
            files += [os.path.join(root, n) for n in sorted(names)
                      if n.lower().endswith(EXT) and not n.startswith('.')]
        return files, tmp
    if os.path.isfile(src) and src.lower().endswith(EXT):
        return [src], None
    raise SystemExit(f'{src}: not a folder, zip, or image')


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    outdir = 'assets/products'
    args = sys.argv[1:]
    if '--outdir' in args:
        i = args.index('--outdir'); outdir = args[i+1]; del args[i:i+2]

    files, tmp = gather(args[0])
    try:
        if len(files) not in (3, 4):
            raise SystemExit(
                f'expected 3 or 4 product photos, found {len(files)}:\n  ' +
                '\n  '.join(files or ['(none)']))

        shots = []
        for f in files:
            rgb, alpha, bg = matte(f)
            solid = alpha > 0.9
            if solid.sum() < 500:
                raise SystemExit(f'{f}: matte came out essentially empty')
            mean = rgb[solid].mean(axis=0)
            luma = float(0.2126*mean[0] + 0.7152*mean[1] + 0.0722*mean[2])
            ys, xs = np.where(alpha > 0.06)
            shots.append({'src': f, 'rgb': rgb, 'alpha': alpha, 'luma': luma,
                          'mean': mean, 'bbox': (ys.min(), ys.max(), xs.min(), xs.max())})
            print(f'  {os.path.basename(f)[-30:]:<32} rgb'
                  f'({mean[0]:3.0f},{mean[1]:3.0f},{mean[2]:3.0f})  luma {luma:5.1f}'
                  f'  box {xs.max()-xs.min()+1}x{ys.max()-ys.min()+1}')

        # sorted darkest to lightest: black, brown, beige, white
        shots.sort(key=lambda s: s['luma'])
        order = {3: ['black', 'brown', 'white'],
                 4: ['black', 'brown', 'beige', 'white']}[len(shots)]
        for s, n in zip(shots, order):
            s['name'] = n
            warm = s['mean'][0] - s['mean'][2]
            print(f'  {n:<6} <- {os.path.basename(s["src"])[-30:]:<32} warmth R-B {warm:+.0f}')

        # A shared crop rectangle keeps scale but not position: these garments
        # were laid out slightly differently, so their bounding boxes sit up to
        # 38px apart and the reels read as misaligned. Centre each garment's own
        # box in a common canvas instead - same scale, same centreline.
        boxw = max(s['bbox'][3] - s['bbox'][2] + 1 for s in shots)
        boxh = max(s['bbox'][1] - s['bbox'][0] + 1 for s in shots)
        pad = int(round(0.04 * max(boxw, boxh)))
        CW, CH = boxw + 2*pad, boxh + 2*pad

        os.makedirs(outdir, exist_ok=True)
        for s in shots:
            y0, y1, x0, x1 = s['bbox']
            sub_rgb = s['rgb'][y0:y1+1, x0:x1+1]
            sub_a = s['alpha'][y0:y1+1, x0:x1+1]
            h, w = sub_a.shape
            oy, ox = (CH - h) // 2, (CW - w) // 2
            canvas = np.zeros((CH, CW, 4), np.float32)
            canvas[oy:oy+h, ox:ox+w, :3] = sub_rgb
            canvas[oy:oy+h, ox:ox+w, 3] = sub_a * 255
            write_rgba(f'{outdir}/{s["name"]}.png', canvas)
            print(f'    {s["name"]:<6} {w}x{h} centred in {CW}x{CH}')

        marker = os.path.join(outdir, '.STANDIN')
        if os.path.exists(marker):
            os.remove(marker)
            print('\n  placeholder marker cleared - renders are unblocked')
        print(f'  {len(shots)} products -> {outdir}/  (common canvas {CW}x{CH})')
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
