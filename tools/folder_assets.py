#!/usr/bin/env python3
"""Cut out the folder layers and the ten flat-lays for the folder burst.

    python3 tools/folder_assets.py

Writes transparent PNGs to campaign/folder/assets/ plus a manifest the scene
reads for sizes. The two folder panels are cropped to one shared rectangle so
they stay registered when the scene stacks them. Set whites and blacks are
pulled onto the tank flat-lays' values (see campaign/README.md) so all ten
files read as one collection.
"""
import json, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import matte

SRC = 'campaign'
OUT = 'campaign/folder/assets'
WHITE, BLACK = (0xEE, 0xE8, 0xEC), (0x26, 0x24, 0x29)
MAX_H = 900   # plenty for a 250px icon that grows to a Quick Look preview

GARMENTS = [
    # (file stem, source, colour target or None)
    ('tank_white',     'flatlays/tank/white.jpg',  None),
    ('tank_beige',     'flatlays/tank/beige.jpg',  None),
    ('tank_brown',     'flatlays/tank/brown.jpg',  None),
    ('tank_black',     'flatlays/tank/black.jpg',  None),
    ('cami-set_white', 'flatlays/set-1/white.jpg', WHITE),
    ('cami-set_beige', 'flatlays/set-1/beige.jpg', None),
    ('cami-set_black', 'flatlays/set-1/black.jpg', BLACK),
    ('tee-set_white',  'flatlays/set-2/white.jpg', WHITE),
    ('tee-set_beige',  'flatlays/set-2/beige.jpg', None),
    ('tee-set_black',  'flatlays/set-2/black.jpg', BLACK),
]


def rgba(rgb, alpha, target=None):
    if target is not None:
        med = np.median(rgb[alpha > 0.99], axis=0)
        rgb = np.clip(rgb * (np.array(target) / med), 0, 255)
    return Image.fromarray(
        np.dstack([rgb.astype(np.uint8), (alpha * 255).astype(np.uint8)]), 'RGBA')


def save(im, name, manifest):
    if im.height > MAX_H:
        im = im.resize((round(im.width * MAX_H / im.height), MAX_H), Image.LANCZOS)
    im.save(f'{OUT}/{name}.png', optimize=True)
    manifest[name] = {'w': im.width, 'h': im.height}


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = {}

    # folder: one shared crop for both panels
    layers = {k: matte(f'{SRC}/folder/source/{k}-panel.jpg') for k in ('back', 'front')}
    boxes = [Image.fromarray((a > 0.02).astype(np.uint8) * 255).getbbox()
             for _, a, _ in layers.values()]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes))
    for k, (rgb, a, _) in layers.items():
        im = rgba(rgb, a).crop(box)
        im.save(f'{OUT}/folder_{k}.png', optimize=True)
        manifest[f'folder_{k}'] = {'w': im.width, 'h': im.height}
    # where the front panel's top edge sits inside the shared crop
    fa = layers['front'][1][box[1]:box[3], box[0]:box[2]] > 0.5
    manifest['folder_front']['top'] = int(np.argmax(fa.any(axis=1)))

    for name, src, target in GARMENTS:
        rgb, a, _ = matte(f'{SRC}/{src}')
        im = rgba(rgb, a, target)
        save(im.crop(im.getbbox()), name, manifest)
        print(f'  {name}')

    with open(f'{OUT}/manifest.json', 'w') as f:
        json.dump(manifest, f, indent=1)
    print(f'  {len(manifest)} layers -> {OUT}/')


if __name__ == '__main__':
    main()
