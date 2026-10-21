#!/usr/bin/env python3
"""Measure how far each generated image drifted from the base, on the face."""
import glob, os
import numpy as np
import cv2

SRC = '/home/user/BASIC/reel/assets/source'
paths = sorted(glob.glob(f'{SRC}/model-*.jpg'))
ref = cv2.imread(paths[0], cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255

# face + jaw + neck: what the prompts locked, and what sits at the crop's top edge
mask = np.zeros_like(ref, np.uint8)
mask[150:470, 380:740] = 255

for p in paths:
    im = cv2.imread(p, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    for mode, name in [(cv2.MOTION_TRANSLATION, 'T'), (cv2.MOTION_AFFINE, 'A')]:
        warp = np.eye(2, 3, dtype=np.float32)
        try:
            cc, warp = cv2.findTransformECC(ref, im, warp, mode,
                (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6), mask, 5)
        except cv2.error as e:
            cc = float('nan')
        sx = np.hypot(warp[0, 0], warp[1, 0]); rot = np.degrees(np.arctan2(warp[1, 0], warp[0, 0]))
        print(f'{os.path.basename(p):34s} {name} cc={cc:.4f} dx={warp[0,2]:+6.1f} dy={warp[1,2]:+6.1f} s={sx:.4f} rot={rot:+.2f}')
