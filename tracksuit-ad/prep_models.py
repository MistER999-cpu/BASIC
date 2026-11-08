"""Cut the three hero models out of their studio backdrops -> build/cutouts/*.png"""
import numpy as np
from PIL import Image
from keying import key_green, key_grey

JOBS = [
    ('M1_bordeaux', 'assets/models/M1_bordeaux.jpg', 'green', None),
    ('M2_noir',  'assets/models/M2_noir.jpg',  'grey',  1625),
    ('M3_chocolat', 'assets/models/M3_chocolat.jpg', 'green', None),
]

for name, src, kind, floor_y in JOBS:
    img = np.asarray(Image.open(src).convert('RGB')).astype(np.float32)
    rgb, a = key_green(img) if kind == 'green' else key_grey(img, feet_y=floor_y)
    ys, xs = np.where(a > 0.02)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([rgb, a[..., None] * 255]).astype(np.float32)[y0:y1, x0:x1]
    Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA').save(f'build/cutouts/{name}.png')
    # feet line: lowest row that is mostly opaque, for grounding the shadow later
    solid_rows = np.where((a[y0:y1, x0:x1] > 0.5).sum(1) > 6)[0]
    print(f'{name}: {x1-x0}x{y1-y0} from {img.shape[1]}x{img.shape[0]}, feet at row {solid_rows.max()} of crop')
