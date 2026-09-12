#!/usr/bin/env python3
"""Extract one full-resolution key frame per shot and build its model matte."""
import os, sys, subprocess, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matte import model_matte

FF = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
SRC = sys.argv[1]
OUT = sys.argv[2]
FPS = 24.0
SHOTS = [(1,31),(32,62),(63,93),(94,124),(125,155),(156,186),(187,216),(217,247),(248,278)]

os.makedirs(OUT, exist_ok=True)
for i, (a, b) in enumerate(SHOTS, 1):
    mid = (a + b) // 2
    key = os.path.join(OUT, 'shot%d_key.png' % i)
    subprocess.run([FF, '-y', '-loglevel', 'error', '-ss', str((mid - 1) / FPS),
                    '-i', SRC, '-frames:v', '1', key], check=True)
    img = np.asarray(Image.open(key).convert('RGB')).astype(np.float64)
    alpha, core = model_matte(img)
    Image.fromarray((alpha * 255).round().astype(np.uint8)).save(
        os.path.join(OUT, 'shot%d_alpha.png' % i))
    print("shot %d  frames %3d-%3d  key frame %3d  matte covers %5.2f%% of frame"
          % (i, a, b, mid, core.mean() * 100))
json.dump({'shots': SHOTS, 'fps': FPS}, open(os.path.join(OUT, 'shots.json'), 'w'))
