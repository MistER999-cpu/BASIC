#!/usr/bin/env python3
"""Prepare every layer of the part 2 lookbook slide.

    python3 tools/part2_assets.py

Writes transparent PNGs, the stitched meadow and a manifest to
campaign/part2/assets/. Figures are matted with BiRefNet (rembg,
birefnet-portrait): the flat-backdrop matte in cutout.py cannot separate skin
from a mid-grey sweep. Paintings were made on flat grey with clean edges, so
paint_matte() handles them.
"""
import glob, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import fit_backdrop

SRC = 'campaign/part2'
OUT = 'campaign/part2/assets'

# Filenames say nothing about content; mapped by eye (and generation order).
FIGURES = {
    'f1': 'Woman_posing_in_fashion_editorial_2K_20261018194519.jpg',   # Model A, beige tank
    'f2': 'Woman_walking_runway_in_outfit_2K_20261018194524.jpg',      # Model B, white tee set
    'f3': 'Woman_posing_in_high_fashion_2K_20261018194527.jpg',        # Model A, brown tank
    'f4': 'Woman_posing_in_editorial_photog…_2K_20261018194534.jpg',   # Model B, beige cami set
    'f5': 'Woman_seated_on_ground_2K_20261018194536.jpg',              # Model A, white cami set
    'f6': 'Woman_posing_in_fashion_photograph_2K_20261018194539.jpg',  # Model B, black tee set
}
PAINTINGS = {
    'pampas':  'Painting_pampas_grass_cluster_2K_20261018201229.jpg',
    'callas':  'Painting_white_calla_lilies_2K_20261018201235.jpg',
    'oak':     'Painting_autumn_oak_branch_2K_20261018201237.jpg',
    'roses':   'Painting_antique_garden_roses_2K_20261018201244.jpg',
    'cosmos':  'Painting_white_cosmos_and_daisies_2K_20261018201247.jpg',
    'dahlias': 'Painting_dark_dahlias_on_stems_2K_20261018201250.jpg',
    'grasses': 'Painting_wild_meadow_grasses_2K_20261018201255.jpg',
    'lace':    "Painting_Queen_Anne's_lace_stems_2K_20261018201256.jpg",
    'butterfly_closed': 'Edit_image_1._Show_the_2K_20261018201307.jpg',
}
BUTTERFLY_OPEN = 'Using_image_1_only_as_2K_20261018201304.jpg'
DRIFT_SHEET = 'Painting_botanical_elements_in_grid_2K_20261018202009.jpg'
TILES = ['Green_meadow_and_hazy_sky_2K_20261018203659.jpg',
         'Creating_next_panorama_frame_2K_20261018203703.jpg',
         'Create_next_panorama_frame_2K_20261018203706.jpg',
         'Creating_next_panorama_frame_2K_20261018203708.jpg',
         'Create_continuous_panorama_final…_2K_20261018203711.jpg']
# Measured overlap between consecutive tiles at native width (1536). Only 2->3
# repeats its neighbour exactly (NCC 0.99 at 335px); the others are joined on a
# minimum-error seam inside a 200px band.
OVERLAPS = [200, 335, 200, 200]
SCREEN_H = 1920
# Raised arms put f6's bounding box above her head; the head top is read off the
# cut-out by eye so her body can be scaled to match the others.
HEAD_ROW = {'f6': 431}


def save(im, name, manifest, **meta):
    im.save(f'{OUT}/{name}.png', optimize=True)
    manifest[name] = {'w': im.width, 'h': im.height, **meta}


def rgba(rgb, alpha):
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255).astype(np.uint8),
                                      (np.clip(alpha, 0, 1) * 255).astype(np.uint8)]), 'RGBA')


def figures(manifest, only=None):
    # BiRefNet's ONNX session keeps its memory arena between images and a
    # second 1536x2752 frame pushes past 14 GB; main() runs one figure per process.
    from rembg import new_session, remove
    session = new_session('birefnet-portrait')
    for key, fn in FIGURES.items():
        if only and key not in only:
            continue
        src = Image.open(f'{SRC}/figures/{fn}').convert('RGB')
        im = np.asarray(src, dtype=np.float32)
        a = np.asarray(remove(src, session=session, only_mask=True), dtype=np.float32) / 255
        # drop specks: keep the largest solid component and anything attached to it
        solid = a > 0.5
        lbl, n = ndimage.label(solid)
        if n > 1:
            sizes = ndimage.sum(solid, lbl, range(1, n + 1))
            keep = ndimage.binary_dilation(lbl == (int(np.argmax(sizes)) + 1), iterations=6)
            a = a * keep
        # unmix the grey sweep out of semi-transparent edge pixels (hair, fingers)
        bg = fit_backdrop(im)
        a3 = np.clip(a, 1e-3, 1)[..., None]
        edge = (a > 0.02) & (a < 0.98)
        rgb = np.where(edge[..., None], (im - (1 - a3) * bg) / a3, im)
        ys, xs = np.where(a > 0.5)
        H, W = a.shape
        pad = 6
        box = (int(max(0, xs.min() - pad)), int(max(0, ys.min() - pad)),
               int(min(W, xs.max() + pad + 1)), int(min(H, ys.max() + pad + 1)))
        cut = rgba(rgb, a).crop(box)
        save(cut, key, manifest, frame=[W, H], box=list(box),
             top=int(ys.min()), feet=int(ys.max()), head=HEAD_ROW.get(key, int(ys.min())))
        print(f'  {key}: {cut.size}, top {ys.min() / H:.1%}, feet {ys.max() / H:.1%}')


def paint_matte(path, lo=9.0, hi=30.0, min_part=150):
    """Matte for a painting on a flat grey sweep.

    cutout.matte() keeps only the largest connected shape, which is right for a
    single garment but drops every separate stroke of a painting - plume tips,
    loose petals, the second flower. Here alpha is a soft ramp on the distance
    from the fitted backdrop, and only specks below min_part pixels are removed.
    """
    im = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32)
    bg = fit_backdrop(im)
    dist = ndimage.gaussian_filter(np.linalg.norm(im - bg, axis=2), 0.8)
    a = np.clip((dist - lo) / (hi - lo), 0, 1)
    solid = a > 0.5
    lbl, n = ndimage.label(ndimage.binary_dilation(solid, iterations=2))
    if n:
        sizes = ndimage.sum(solid, lbl, range(1, n + 1))
        a = a * np.isin(lbl, 1 + np.flatnonzero(sizes >= min_part))
    # A pale subject's edge strokes can sit darker than the sweep; against the
    # bright sky they read as a grey outline. Fade edge pixels that are darker
    # than the backdrop when the subject itself is lighter than it.
    lum = lambda x: x @ np.array([0.299, 0.587, 0.114], np.float32)
    ld = ndimage.gaussian_filter(lum(im) - lum(bg), 1.0)
    if np.median(ld[a > 0.9]) > 0:
        a = np.where((a < 0.97) & (ld < 0), a * np.clip(1 + ld / 6, 0, 1), a)
    a3 = np.clip(a, 1e-3, 1)[..., None]
    rgb = np.where((a < 0.98)[..., None], bg + (im - bg) / a3, im)
    return rgb, a


def paintings(manifest):
    for key, fn in PAINTINGS.items():
        rgb, a = paint_matte(f'{SRC}/watercolour/{fn}')
        im = rgba(rgb, a)
        save(im.crop(im.getbbox()), key, manifest)
        print(f'  {key}: {im.getbbox()}')

    # butterfly: body strip plus two wings, so the wings can flap about the body
    rgb, a = paint_matte(f'{SRC}/watercolour/{BUTTERFLY_OPEN}')
    im = rgba(rgb, a)
    x0, y0, x1, y1 = im.getbbox()
    im = im.crop((x0, y0, x1, y1))
    A = np.asarray(im)[..., 3].astype(float)
    cx = int(round((A.sum(0) * np.arange(A.shape[1])).sum() / A.sum()))
    body = max(6, int(0.035 * im.width))
    wl = im.crop((0, 0, cx - body // 2, im.height))
    wr = im.crop((cx + body // 2, 0, im.width, im.height))
    bd = im.crop((cx - body // 2, 0, cx + body // 2, im.height))
    save(wl, 'bfly_wing_l', manifest)
    save(wr, 'bfly_wing_r', manifest)
    save(bd, 'bfly_body', manifest)
    manifest['bfly'] = {'w': im.width, 'h': im.height, 'cx': int(cx), 'body': int(body)}
    print(f'  butterfly: {im.size}, axis x={cx}')

    # drifting pieces: one component each
    rgb, a = paint_matte(f'{SRC}/watercolour/{DRIFT_SHEET}')
    lbl, n = ndimage.label(ndimage.binary_dilation(a > 0.3, iterations=4))
    sizes = ndimage.sum(np.ones_like(a), lbl, range(1, n + 1))
    order = [i + 1 for i in np.argsort(sizes)[::-1][:6]]
    pieces = []
    for i in order:
        ys, xs = np.where(lbl == i)
        pieces.append((ys.min(), xs.min(), i))
    pieces.sort()          # reading order: top row left to right, then bottom row
    pieces = sorted(pieces[:3], key=lambda p: p[1]) + sorted(pieces[3:], key=lambda p: p[1])
    for k, (_, _, i) in enumerate(pieces):
        m = (lbl == i)
        im = rgba(rgb, a * m)
        save(im.crop(im.getbbox()), f'drift{k + 1}', manifest)
    print(f'  drift pieces: {len(pieces)} of {n} components')


def seam_mask(A, B):
    """0 where the overlap takes A, 1 where it takes B, along a minimum-error path."""
    d = ndimage.gaussian_filter(np.abs(A - B).sum(2), 2)
    H, W = d.shape
    cost = d.copy()
    for y in range(1, H):
        prev = cost[y - 1]
        left = np.r_[np.inf, prev[:-1]]
        right = np.r_[prev[1:], np.inf]
        cost[y] += np.minimum(np.minimum(left, prev), right)
    path = np.empty(H, int)
    path[-1] = int(np.argmin(cost[-1]))
    for y in range(H - 2, -1, -1):
        x = path[y + 1]
        lo, hi = max(0, x - 1), min(W, x + 2)
        path[y] = lo + int(np.argmin(cost[y, lo:hi]))
    m = (np.arange(W)[None, :] >= path[:, None]).astype(np.float32)
    return ndimage.gaussian_filter(m, 6)


def panorama(manifest):
    tiles = [np.asarray(Image.open(f'{SRC}/panorama/{t}').convert('RGB'), dtype=np.float32)
             for t in TILES]
    H, W = tiles[0].shape[:2]
    # even out exposure drift: match each tile's per-channel mean to tile 1
    ref = tiles[0].reshape(-1, 3).mean(0)
    tiles = [t * (ref / t.reshape(-1, 3).mean(0)) for t in tiles]
    total = W * len(tiles) - sum(OVERLAPS)
    pano = np.zeros((H, total, 3), np.float32)
    pano[:, :W] = tiles[0]
    x = W
    for t, ov in zip(tiles[1:], OVERLAPS):
        start = x - ov
        m = seam_mask(pano[:, start:x], t[:, :ov])[..., None]
        pano[:, start:x] = pano[:, start:x] * (1 - m) + t[:, :ov] * m
        pano[:, x:x + W - ov] = t[:, ov:]
        x += W - ov
    scale = SCREEN_H / H
    out = Image.fromarray(np.clip(pano, 0, 255).astype(np.uint8)).resize(
        (round(total * scale), SCREEN_H), Image.LANCZOS)
    # One more screen of meadow for the logo stretch: the last tile mirrored
    # about the right edge, which continues it with no seam at all.
    arr = np.asarray(out)
    tail = round(W * scale)
    out = Image.fromarray(np.concatenate([arr, arr[:, -tail:][:, ::-1]], axis=1))
    out.save(f'{OUT}/meadow.jpg', quality=93)
    manifest['meadow'] = {'w': out.width, 'h': out.height, 'horizon': round(0.634 * SCREEN_H)}
    print(f'  meadow: {out.size}')


def handoff(manifest):
    """Part 1 ends on Quick Look full screen: the beige tank flat-lay, object-fit
    contain inside a 120px inset on #F2F2F4. Part 2 starts on that exact frame."""
    src = Image.open('campaign/folder/assets/tank_beige.png')
    src.save(f'{OUT}/ql_flatlay.png', optimize=True)
    bw, bh = 1080 - 240, 1920 - 240
    s = min(bw / src.width, bh / src.height)
    w, h = src.width * s, src.height * s
    manifest['ql_flatlay'] = {'w': w, 'h': h, 'x': 120 + (bw - w) / 2, 'y': 120 + (bh - h) / 2}


def write_manifest(path, manifest):
    text = json.dumps(manifest, indent=1)      # serialise first: a bad value must not truncate the file
    with open(path + '.tmp', 'w') as f:
        f.write(text)
    os.replace(path + '.tmp', path)


def main():
    os.makedirs(OUT, exist_ok=True)
    path = f'{OUT}/manifest.json'
    manifest = json.load(open(path)) if os.path.exists(path) else {}
    args = sys.argv[1:] or ['panorama', 'paintings', 'figures']
    if args[0] == 'figures' and len(args) > 1:          # a single figure, in-process
        figures(manifest, only=args[1:])
        write_manifest(path, manifest)
        return
    for step in args:
        print(step)
        if step == 'figures':                            # one fresh process per figure
            import subprocess
            for key in FIGURES:
                subprocess.run([sys.executable, __file__, 'figures', key], check=True)
            manifest.update(json.load(open(path)))
            continue
        globals()[step](manifest)
        write_manifest(path, manifest)


if __name__ == '__main__':
    main()
