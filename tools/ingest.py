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
        if len(files) != 3:
            raise SystemExit(
                f'expected 3 product photos, found {len(files)}:\n  ' +
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
            print(f'  {os.path.basename(f):<34} garment rgb'
                  f'({mean[0]:3.0f},{mean[1]:3.0f},{mean[2]:3.0f})  luma {luma:5.1f}')

        # lightest is white, darkest is black, the middle one is brown
        shots.sort(key=lambda s: s['luma'])
        names = ['black', 'brown', 'white']
        for s, n in zip(shots, names):
            s['name'] = n

        warm = shots[1]['mean'][0] - shots[1]['mean'][2]
        print(f'\n  black  <- {os.path.basename(shots[0]["src"])}')
        print(f'  brown  <- {os.path.basename(shots[1]["src"])}   (warmth R-B = {warm:+.0f})')
        print(f'  white  <- {os.path.basename(shots[2]["src"])}')
        if warm < 8:
            print('  NOTE: the middle photo is not obviously warm; check the '
                  'brown assignment above before rendering.')

        # one shared crop across all three
        y0 = min(s['bbox'][0] for s in shots); y1 = max(s['bbox'][1] for s in shots)
        x0 = min(s['bbox'][2] for s in shots); x1 = max(s['bbox'][3] for s in shots)
        pad = int(round(0.04 * max(y1-y0, x1-x0)))
        H, W = shots[0]['alpha'].shape
        y0, y1 = max(0, y0-pad), min(H, y1+1+pad)
        x0, x1 = max(0, x0-pad), min(W, x1+1+pad)

        os.makedirs(outdir, exist_ok=True)
        for s in shots:
            write_rgba(f'{outdir}/{s["name"]}.png',
                       np.dstack([s['rgb'][y0:y1, x0:x1], s['alpha'][y0:y1, x0:x1]*255]))

        marker = os.path.join(outdir, '.STANDIN')
        if os.path.exists(marker):
            os.remove(marker)
            print('\n  placeholder marker cleared - renders are unblocked')
        print(f'  shared crop {x1-x0}x{y1-y0} -> {outdir}/')
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
