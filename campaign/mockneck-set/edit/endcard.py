"""Compose the BASIC Essentials end card: three cut-out looks on the stone wall, logo in the carved panel."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as nd
import os

D = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(D, '..', 'endcard')
REFS = os.path.join(D, '..', 'refs')
FONT = '/usr/share/fonts/opentype/inter/Inter-Light.otf'

W0, H0 = 1116, 2000            # wall plate size
FEET_Y = 1785                  # where every figure's soles land
FIG_H = 1000                   # head-to-sole height of each figure
LOOKS = [                      # (file, centre x, mirror, label)
    ('burgundy-profile.png', 205, False, 'BURGUNDY'),
    ('chocolate-front.png',  558, False, 'CHOCOLATE'),
    ('black-back.png',       915, True,  'BLACK'),
]
INK = (34, 30, 28)

def load_fig(name, mirror):
    im = Image.open(os.path.join(EC, name)).convert('RGBA')
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    a = np.asarray(im).astype(np.float32)
    al = a[..., 3]
    ys, xs = np.nonzero(al > 40)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    im = decontaminate(im)
    s = FIG_H / im.height
    im = im.resize((round(im.width * s), FIG_H), Image.LANCZOS)
    # warm the neutral studio light toward the late-afternoon stone
    a = np.asarray(im).astype(np.float32)
    a[..., 0] *= 1.035; a[..., 1] *= 1.0; a[..., 2] *= 0.94
    a[..., :3] = 255 * (a[..., :3] / 255) ** 0.98
    g = np.linspace(1.06, 0.95, a.shape[1])[None, :, None]
    a[..., :3] *= g
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def decontaminate(im):
    """Kill the grey studio fringe: tighten the matte and pull edge colour from the solid interior."""
    a = np.asarray(im).astype(np.float32)
    al = a[..., 3] / 255
    al = np.clip((al - 0.12) / 0.80, 0, 1)
    al = nd.minimum_filter(al, size=3)
    al = nd.gaussian_filter(al, 0.7)
    solid = al > 0.97
    _, (iy, ix) = nd.distance_transform_edt(~solid, return_indices=True)
    inner = a[iy, ix, :3]
    w = np.clip((0.97 - al) / 0.97, 0, 1)[..., None]
    a[..., :3] = a[..., :3] * (1 - w) + inner * w
    a[..., 3] = al * 255
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def shadows(canvas, fig, x0, y0):
    al = np.asarray(fig)[..., 3].astype(np.float32) / 255
    h, w = al.shape
    sh = np.zeros((H0, W0), np.float32)
    # contact shadow: soft ellipse under the soles
    cy = y0 + h - 6
    xs = np.nonzero(al[-40:].max(0) > 0.5)[0]
    cx, rx = x0 + (xs.min() + xs.max()) / 2, (xs.max() - xs.min()) / 2 + 30
    yy, xx = np.mgrid[0:H0, 0:W0]
    sh += 0.55 * np.clip(1 - (((xx - cx) / rx) ** 2 + ((yy - cy) / 16) ** 2), 0, 1)
    # long floor shadow cast back and to the right (key light from the left)
    flat = Image.fromarray((al * 255).astype(np.uint8)).resize((w, max(1, int(h * 0.16))))
    fl = np.asarray(flat).astype(np.float32) / 255
    fl = nd.affine_transform(fl, [[1, 0], [0, 1]], offset=[0, 0])
    sk = np.zeros((fl.shape[0], w + fl.shape[0] * 2), np.float32)
    for r in range(fl.shape[0]):            # skew: rows further back shift right
        off = int((fl.shape[0] - r) * 2.0)
        sk[r, off:off + w] = fl[r]
    top = cy - sk.shape[0]
    sl = sh[top:cy, x0:x0 + sk.shape[1]]
    sl += 0.22 * sk[:sl.shape[0], :sl.shape[1]]
    sh = nd.gaussian_filter(sh, 6)
    c = np.asarray(canvas).astype(np.float32)
    c[..., :3] *= (1 - sh[..., None] * np.array([0.55, 0.58, 0.62]))
    return Image.fromarray(c.clip(0, 255).astype(np.uint8))

def light_wrap(canvas, fig, x0, y0):
    """Bleed a little of the warm wall into the figure's edge so it sits in the scene."""
    al = np.asarray(fig)[..., 3].astype(np.float32) / 255
    edge = np.clip(al - nd.gaussian_filter(al, 3), 0, 1) * 2.0
    bg = np.asarray(canvas.crop((x0, y0, x0 + fig.width, y0 + fig.height)).filter(ImageFilter.GaussianBlur(12))).astype(np.float32)
    f = np.asarray(fig).astype(np.float32)
    k = np.clip(0.35 * edge, 0, 0.3)[..., None]
    f[..., :3] = f[..., :3] * (1 - k) + bg[..., :3] * k
    return Image.fromarray(f.clip(0, 255).astype(np.uint8))

def logo(canvas):
    lg = Image.open(os.path.join(REFS, 'logo.png')).convert('RGBA')
    al = np.asarray(lg)[..., 3]
    ys, xs = np.nonzero(al > 20)
    lg = lg.crop((xs.min() - 4, ys.min() - 4, xs.max() + 5, ys.max() + 5))
    target_w = 420                                   # inside the carved panel (x 305-808)
    s = target_w / lg.width
    lg = lg.resize((target_w, round(lg.height * s)), Image.LANCZOS)
    a = np.asarray(lg)[..., 3].astype(np.float32) / 255
    cx, cy = 557, 512                                # centre of the recessed panel
    x0, y0 = cx - lg.width // 2, cy - lg.height // 2
    c = np.asarray(canvas).astype(np.float32)
    # carved look: light catch below-right, ink, faint shadow above-left
    hi = nd.shift(a, (2, 1), order=1); lo = nd.shift(a, (-1, -1), order=1)
    reg = c[y0:y0 + lg.height, x0:x0 + lg.width, :3]
    reg[:] = reg * (1 - 0.18 * hi[..., None]) + 255 * 0.18 * hi[..., None] * 0 + reg * 0.0
    reg[:] = reg + (255 - reg) * (0.10 * np.clip(hi - a, 0, 1))[..., None]
    reg[:] = reg * (1 - 0.25 * np.clip(lo - a, 0, 1))[..., None]
    reg[:] = reg * (1 - 0.9 * a[..., None]) + np.array(INK) * 0.9 * a[..., None]
    return Image.fromarray(c.clip(0, 255).astype(np.uint8))

def labels(canvas):
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(FONT, 25)
    track = 7
    for _, cx, _, text in LOOKS:
        widths = [d.textlength(ch, font=f) for ch in text]
        tw = sum(widths) + track * (len(text) - 1)
        x = cx - tw / 2
        for ch, cw in zip(text, widths):
            d.text((x, 1858), ch, font=f, fill=INK + (215,))
            x += cw + track
    return canvas

def build(out_path, upto=3, with_logo=True, with_labels=True):
    canvas = Image.open(os.path.join(EC, 'wall.jpg')).convert('RGB')
    figs = []
    for name, cx, mirror, _ in LOOKS[:upto]:
        fig = load_fig(name, mirror)
        x0, y0 = int(cx - fig.width / 2), FEET_Y - fig.height
        figs.append((fig, x0, y0))
        canvas = shadows(canvas, fig, x0, y0)
    for fig, x0, y0 in figs:
        fig = light_wrap(canvas, fig, x0, y0)
        canvas.paste(fig, (x0, y0), fig)
    if with_logo:
        canvas = logo(canvas)
    if with_labels:
        canvas = canvas.convert('RGBA'); canvas = labels(canvas).convert('RGB')
    # deliver at 1080x1920
    canvas = canvas.resize((1080, round(1080 * H0 / W0)), Image.LANCZOS).crop((0, 0, 1080, 1920))
    canvas.save(out_path, quality=95)

if __name__ == '__main__':
    build(os.path.join(EC, 'endcard.jpg'))
