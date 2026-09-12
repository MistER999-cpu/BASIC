"""
Tank top product reel — replica of the reference sunglasses animation.

Grammar taken from the reference video:
  - hard cut between images, no crossfade, no morph
  - exactly 20 frames (0.6667s) per image at 30fps
  - 4 images, 3 cycles = 240 frames = 8.000s
  - fixed thumbnail strip, active thumb marked with a warm brown border

Added per brief: a continuous hover on the hero card, and a lift/shift
settle on each change. The image SWAP stays instantaneous -- only the
card's position reacts, so the cut stays hard.
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter

# ----------------------------------------------------------------- timing
FPS            = 30
HOLD_FRAMES    = 20          # 0.6667s -- matches the reference exactly
CYCLES         = 3
SETTLE_FRAMES  = 9           # lift/shift settle after each cut (0.30s)

# ----------------------------------------------------------------- canvas
W, H       = 1080, 1920
BG         = (244, 239, 233)   # warm cream canvas
BORDER     = (142, 114, 100)   # #8E7264 -- sampled from the reference
CARD_R     = 18

HERO_W, HERO_H = 900, 1125     # 4:5
HERO_X, HERO_Y = 90, 190

THUMB_W, THUMB_H = 198, 248    # 4:5
THUMB_GAP        = 36
THUMB_Y          = 1420
THUMB_X0         = (W - (4 * THUMB_W + 3 * THUMB_GAP)) // 2

# ----------------------------------------------------------------- motion
FLOAT_AMP_Y   = 7.0          # px, continuous hover
FLOAT_PER_Y   = 3.2          # s
FLOAT_AMP_S   = 0.004        # scale breath
FLOAT_PER_S   = 4.7          # s, deliberately not a multiple of the cut

ENTER_DY      = 16.0         # card enters this far LOW, then rises
ENTER_DX      = 12.0         # and this far RIGHT, then shifts into place
ENTER_SCALE   = 0.985

THUMB_LIFT    = 8.0          # active thumb rises
THUMB_SCALE   = 1.05
THUMB_DIM     = 0.72         # inactive opacity

# ----------------------------------------------------------------- sources
# Each shot: (file, crop_top, white_balance_gains).
# crop_top picks the 1080x1350 window out of the 1080x1920 still.
# The gains correct a backdrop that drifts away from the rest of its set --
# None means the still is used as shot.
SETS = {
    "women": [
        ("black.jpg",  60, None),   # widest   -- raised arm
        ("sand.jpg",   80, None),   # medium   -- back turn
        ("ivory.jpg", 220, None),   # tightest -- macro, crossed arms
        ("brown.jpg", 100, None),   # medium   -- hand at collarbone
    ],
    "hijabi": [
        ("black.jpg", 170, None),   # widest   -- both hands holding the shirt open
        ("sand.jpg",  230, None),   # medium   -- suede jacket off one shoulder
        # this still was shot on a cooler grey ground than the other three;
        # pulled 70% of the way back to the set's warmth
        ("ivory.jpg", 200, (1.071, 1.0, 0.905)),
        ("brown.jpg", 140, None),   # medium   -- bomber swept back
    ],
}

SET_NAME = sys.argv[1] if len(sys.argv) > 1 else "women"
if SET_NAME not in SETS:
    raise SystemExit("unknown set %r -- choose from %s" % (SET_NAME, ", ".join(SETS)))
ORDER = SETS[SET_NAME]
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", SET_NAME)
CROP_H = 1350

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames", SET_NAME)


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1],
                                        radius=radius, fill=255)
    return m


def load_cards():
    """Crop each source to 4:5 and pre-render hero + thumb base sizes."""
    heroes, thumbs = [], []
    for fname, top, gains in ORDER:
        im = Image.open(os.path.join(SRC, fname)).convert("RGB")
        im = im.crop((0, top, W, top + CROP_H))
        if gains:
            im = Image.merge("RGB", [ch.point(lambda p, g=g: min(255, int(p * g)))
                                     for ch, g in zip(im.split(), gains)])
        heroes.append(im)
        thumbs.append(im.resize((THUMB_W, THUMB_H), Image.LANCZOS))
    return heroes, thumbs


def make_shadow(size, radius, blur, opacity):
    pad = blur * 3
    s = Image.new("L", (size[0] + pad * 2, size[1] + pad * 2), 0)
    ImageDraw.Draw(s).rounded_rectangle(
        [pad, pad, pad + size[0] - 1, pad + size[1] - 1], radius=radius, fill=opacity)
    return s.filter(ImageFilter.GaussianBlur(blur)), pad


def main():
    os.makedirs(OUT, exist_ok=True)
    heroes, thumbs = load_cards()

    hero_mask  = rounded_mask((HERO_W, HERO_H), CARD_R)
    hero_shadow, hero_pad = make_shadow((HERO_W, HERO_H), CARD_R, 26, 80)

    total = HOLD_FRAMES * len(ORDER) * CYCLES

    for f in range(total):
        t   = f / FPS
        idx = (f // HOLD_FRAMES) % len(ORDER)
        k   = f % HOLD_FRAMES                      # frames since this cut

        # --- settle: 1.0 at the cut, decaying to 0.0
        if k < SETTLE_FRAMES:
            s = 1.0 - ease_out_cubic(k / SETTLE_FRAMES)
        else:
            s = 0.0

        # --- continuous hover, unbroken across cuts
        fy = FLOAT_AMP_Y * math.sin(2 * math.pi * t / FLOAT_PER_Y)
        fs = 1.0 + FLOAT_AMP_S * math.sin(2 * math.pi * t / FLOAT_PER_S + 1.1)

        dx    = ENTER_DX * s
        dy    = ENTER_DY * s + fy
        scale = (ENTER_SCALE + (1 - ENTER_SCALE) * (1 - s)) * fs

        canvas = Image.new("RGB", (W, H), BG)

        # ---------------- hero card
        cw, ch = int(round(HERO_W * scale)), int(round(HERO_H * scale))
        cx = HERO_X + (HERO_W - cw) / 2 + dx
        cy = HERO_Y + (HERO_H - ch) / 2 + dy

        # shadow tracks the card, and deepens as it rises
        lift = (FLOAT_AMP_Y - fy) / (2 * FLOAT_AMP_Y)        # 0..1
        sh = hero_shadow.point(lambda p, m=(0.75 + 0.45 * lift): min(255, int(p * m)))
        canvas.paste((186, 174, 162),
                     (int(cx - hero_pad), int(cy - hero_pad + 10)), sh)

        card = heroes[idx].resize((cw, ch), Image.LANCZOS)
        canvas.paste(card, (int(cx), int(cy)),
                     rounded_mask((cw, ch), CARD_R))

        # ---------------- thumbnail strip
        for i in range(len(ORDER)):
            active = (i == idx)
            # the outgoing thumb drops as the incoming one lifts
            a = (1 - s) if active else (s if i == (idx - 1) % len(ORDER) else 0.0)

            tw = int(round(THUMB_W * (1 + (THUMB_SCALE - 1) * a)))
            th = int(round(THUMB_H * (1 + (THUMB_SCALE - 1) * a)))
            tx = THUMB_X0 + i * (THUMB_W + THUMB_GAP) + (THUMB_W - tw) / 2
            ty = THUMB_Y + (THUMB_H - th) / 2 - THUMB_LIFT * a

            th_im = thumbs[i].resize((tw, th), Image.LANCZOS)
            if a < 1.0:                                   # dim the inactive ones
                dim = THUMB_DIM + (1 - THUMB_DIM) * a
                th_im = Image.blend(Image.new("RGB", (tw, th), BG), th_im, dim)

            canvas.paste(th_im, (int(tx), int(ty)), rounded_mask((tw, th), 10))

            if a > 0.01:                                  # active border
                d = ImageDraw.Draw(canvas, "RGBA")
                pad = 7
                d.rounded_rectangle(
                    [int(tx) - pad, int(ty) - pad,
                     int(tx) + tw + pad - 1, int(ty) + th + pad - 1],
                    radius=15, outline=BORDER + (int(255 * a),), width=3)

        canvas.save(os.path.join(OUT, "f%04d.png" % f))

    print("rendered %d frames of set %r -> %s" % (total, SET_NAME, OUT))


if __name__ == "__main__":
    main()
