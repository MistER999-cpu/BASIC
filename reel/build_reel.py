#!/usr/bin/env python3
"""
Composite the sliding garment strip behind the model.

The strip is a train of ghost-mannequin tank cutouts travelling right to left
at constant velocity. Its speed is chosen so that exactly one garment arrives
centred behind the model on every cut of the base reel - the garment passing
behind her is what triggers the change of look.

Two properties are load-bearing, both taken from the reference film:

  * The strip never resets at a cut. It is one unbroken move across the whole
    clip; only the model plate cuts on top of it. That is most of why the
    reference reads as a single piece rather than a run of stills.

  * The garments are rigid. They translate and nothing else - no flutter, no
    rotation, no scale change. Motion-compensating the reference left only
    grain behind, so there is no cloth simulation anywhere in it.

Compositing needs no clean background plate. Where the model's matte is solid
the base frame passes through untouched; everywhere else the garment is drawn
over the base frame. So the strip appears behind her without the backdrop ever
being reconstructed.
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matte import smooth_background

FF = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'

W, H = 1080, 1920
FPS = 24.0
MODEL_CX = 315                     # measured torso centre, all nine shots
CUTS = [32, 63, 94, 125, 156, 187, 217, 248]
SHOTS = [(1, 31), (32, 62), (63, 93), (94, 124), (125, 155),
         (156, 186), (187, 216), (217, 247), (248, 278)]
NFRAMES = 278
CUT_PERIOD = 31.0                  # frames between cuts (measured: 30-31)

# What the model is wearing in each of the nine shots. The strip is built from
# this, not from a generic repeat: the garment that arrives behind her on a cut
# is the colourway of the shot that cut starts, so the garment passing behind
# her IS the change. Shot 1 is already beige, which is why she is "already
# wearing it" when the first one lands.
SHOT_COLOURS = ['beige', 'beige', 'black', 'brown', 'brown',
                'white', 'beige', 'black', 'white']
PALETTE = ['beige', 'black', 'brown', 'white']


def colour_for(k):
    """Garment k arrives on the cut into shot k+2, so it wears that shot's colour."""
    return SHOT_COLOURS[(k + 1) % len(SHOT_COLOURS)]


def load_garments(scale, soften=0.0, products='assets/products'):
    """Load the cutouts, trim to their alpha bbox, scale to a common height."""
    raw = {}
    for name in PALETTE:
        im = Image.open(os.path.join(products, name + '.png')).convert('RGBA')
        a = np.asarray(im)[:, :, 3]
        ys, xs = np.where(a > 8)
        raw[name] = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    # all four cutouts are the same garment shot identically, so one uniform
    # scale keeps their relative sizes true
    out = {}
    for name in PALETTE:
        im = raw[name]
        nw = max(1, int(round(im.size[0] * scale)))
        nh = max(1, int(round(im.size[1] * scale)))
        sprite = im.resize((nw, nh), Image.LANCZOS)
        if soften > 0:
            # soften each sprite once here rather than the assembled layer every
            # frame; the garments barely overlap, so the result is equivalent
            from scipy import ndimage
            a = np.asarray(sprite).astype(np.float64)
            for c in range(4):
                a[:, :, c] = ndimage.gaussian_filter(a[:, :, c], soften)
            sprite = Image.fromarray(a.round().clip(0, 255).astype(np.uint8), 'RGBA')
        out[name] = sprite
    return out


def garment_positions(frame, pitch):
    """(index, centre_x) for every garment overlapping the frame."""
    # garment k is centred on the model at cut frame CUTS[0] + k*CUT_PERIOD
    t = (frame - CUTS[0]) / CUT_PERIOD
    lo = int(np.floor((0 - MODEL_CX) / pitch + t)) - 1
    hi = int(np.ceil((W - MODEL_CX) / pitch + t)) + 1
    return [(k, MODEL_CX + pitch * (k - t)) for k in range(lo, hi + 1)]


def build_strip(frame, garments, pitch, band_cy):
    """RGBA layer holding the whole train at this frame."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for k, cx in garment_positions(frame, pitch):
        im = garments[colour_for(k)]
        x = int(round(cx - im.size[0] / 2))
        y = int(round(band_cy - im.size[1] / 2))
        if x > W or x + im.size[0] < 0:
            continue
        layer.alpha_composite(im, (x, y))
    return np.asarray(layer).astype(np.float32)


CORR_SIGMA = 200.0   # see background_corrections


def background_corrections(mattes, nshots):
    """
    One smooth gain field per shot, bringing every shot's backdrop onto the
    same exposure. The shots were generated in separate passes and can drift;
    correcting the whole frame (not just the backdrop) carries the subject with
    it, which is what makes an underexposed shot match rather than look pasted.

    The radius here is far wider than the matte's. The matte needs a tight
    radius to hug the figure, but at that radius the masked blur has no
    backdrop left to average deep inside the silhouette: the estimate collapses
    to zero, the gain slams into its clip rail and paints artefacts across the
    model. The gain field only has to be low-frequency, so a wide radius keeps
    it defined behind her (measured gain inside the figure: 0.94-1.03 at 200,
    against 0.91-2.50 at 20).
    """
    backs = []
    for i in range(1, nshots + 1):
        key = os.path.join(mattes, 'shot%d_key.png' % i)
        alpha = np.asarray(Image.open(os.path.join(mattes, 'shot%d_alpha.png' % i))
                           .convert('L')).astype(np.float32) / 255.0
        img = np.asarray(Image.open(key).convert('RGB')).astype(np.float64)
        backs.append(smooth_background(img, alpha < 0.5, sigma=CORR_SIGMA))
    ref = np.median(np.stack(backs), axis=0)
    out = []
    for b in backs:
        c = ref / np.maximum(b, 1e-6)
        out.append(np.clip(c, 0.4, 2.5).astype(np.float32))
    return out


def shot_of(frame):
    for i, (a, b) in enumerate(SHOTS):
        if a <= frame <= b:
            return i
    return len(SHOTS) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--mattes', default='reel/mattes')
    ap.add_argument('--out', required=True)
    ap.add_argument('--scale', type=float, default=0.135,
                    help='scale factor applied to the trimmed cutouts')
    ap.add_argument('--pitch', type=float, default=None,
                    help='centre-to-centre spacing in px; default 1.35x garment width')
    ap.add_argument('--band', type=float, default=0.52,
                    help='vertical centre of the strip as a fraction of frame height')
    ap.add_argument('--soften', type=float, default=0.6)
    ap.add_argument('--opacity', type=float, default=1.0)
    ap.add_argument('--no-match-bg', action='store_true',
                    help='skip the per-shot exposure match')
    ap.add_argument('--frames', default=None, help='e.g. 16,47,109 to render stills only')
    ap.add_argument('--stills-dir', default='reel/stills')
    args = ap.parse_args()

    garments = load_garments(args.scale, args.soften)
    gw = garments[PALETTE[0]].size[0]
    pitch = args.pitch if args.pitch else gw * 1.35
    band_cy = args.band * H
    speed = pitch / CUT_PERIOD                       # px per frame
    print("garment %dx%d px  pitch %.0f px  speed %.1f px/frame = %.0f px/s (%.1f%% width/s)"
          % (gw, garments[PALETTE[0]].size[1], pitch, speed, speed * FPS, speed * FPS / W * 100))
    print("strip order at the cuts: " + " -> ".join(colour_for(k) for k in range(-1, 8)))

    alphas = [np.asarray(Image.open(os.path.join(args.mattes, 'shot%d_alpha.png' % i))
                         .convert('L')).astype(np.float32)[:, :, None] / 255.0
              for i in range(1, len(SHOTS) + 1)]

    corr = None
    if not args.no_match_bg:
        corr = background_corrections(args.mattes, len(SHOTS))
        for i, c in enumerate(corr, 1):
            g = float(np.median(c))
            if abs(g - 1) > 0.01:
                print("  shot %d exposure matched: %+.1f%%" % (i, (g - 1) * 100))

    if args.frames:
        os.makedirs(args.stills_dir, exist_ok=True)
        for f in [int(x) for x in args.frames.split(',')]:
            base = grab_frame(args.src, f)
            if corr is not None:
                base = np.clip(base * corr[shot_of(f)], 0, 255)
            Image.fromarray(composite(base, alphas[shot_of(f)],
                                      build_strip(f, garments, pitch, band_cy),
                                      args.opacity)).save(
                os.path.join(args.stills_dir, 'f%03d.png' % f))
        print("wrote stills to", args.stills_dir)
        return

    dec = subprocess.Popen([FF, '-loglevel', 'error', '-i', args.src,
                            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                           stdout=subprocess.PIPE, bufsize=10 ** 8)
    enc = subprocess.Popen([FF, '-y', '-loglevel', 'error',
                            '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                            '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
                            '-i', args.src, '-map', '0:v', '-map', '1:a?',
                            '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
                            '-pix_fmt', 'yuv420p', '-c:a', 'copy',
                            '-shortest', args.out],
                           stdin=subprocess.PIPE)
    nbytes = W * H * 3
    for f in range(1, NFRAMES + 1):
        buf = dec.stdout.read(nbytes)
        if len(buf) < nbytes:
            break
        base = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        if corr is not None:
            base = np.clip(base * corr[shot_of(f)], 0, 255)
        out = composite(base, alphas[shot_of(f)],
                        build_strip(f, garments, pitch, band_cy),
                        args.opacity)
        enc.stdin.write(out.tobytes())
        if f % 40 == 0:
            print("  frame %d/%d" % (f, NFRAMES), flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print("wrote", args.out)


def grab_frame(src, f):
    p = subprocess.run([FF, '-loglevel', 'error', '-ss', str((f - 1) / FPS),
                        '-i', src, '-frames:v', '1', '-f', 'rawvideo',
                        '-pix_fmt', 'rgb24', '-'], capture_output=True)
    return np.frombuffer(p.stdout[:W * H * 3], np.uint8).reshape(H, W, 3)


def composite(base, model_alpha, strip, opacity):
    """base where the model is; garment-over-base everywhere else."""
    b = base.astype(np.float32)
    sa = strip[:, :, 3:4] / 255.0 * opacity
    over = b * (1 - sa) + strip[:, :, :3] * sa
    out = b * model_alpha + over * (1 - model_alpha)
    return out.round().clip(0, 255).astype(np.uint8)


if __name__ == '__main__':
    main()
