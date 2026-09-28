"""Cut the single letters B A S I C out of the BASIC logo and render them as
1080x1920 cards matching the reference layout (cap height = 25% of frame
height, centred), plus a final full-logo card.

The source logo is small (~160px caps), so each glyph is upscaled from its
ink mask and the edges are re-sharpened with a smoothstep around 50% ink.
"""
import os
import numpy as np
import cv2
from PIL import Image

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "logo", "basic_logo_original.png")
OUT = os.path.join(HERE, "logo", "cards")

CAP_FRAC = 0.25      # letter cap height as a fraction of frame height
LOGO_W_FRAC = 0.50   # full-logo width as a fraction of frame width
# Horizontal blur per letter, as a fraction of frame width, mirroring the
# reference's blurred middle letters (T 29px, H 41px at 720px wide).
BLUR = {"A": 29 / 720, "S": 41 / 720, "I": 31 / 720}


def ink_mask():
    im = Image.open(SRC).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return 1.0 - np.asarray(bg.convert("L"), dtype=np.float32) / 255.0


def upscale(ink, scale):
    big = cv2.resize(ink, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), sigmaX=scale * 0.35)
    # Re-sharpen: map ink 0.35..0.65 to 0..1 with a smoothstep (~1.5px edge).
    t = np.clip((big - 0.35) / 0.30, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def letters(ink):
    """Return {letter: (x, y, w, h)} for the five big glyphs, left to right."""
    n, _, stats, _ = cv2.connectedComponentsWithStats((ink > 0.5).astype(np.uint8), 8)
    big = sorted((s for s in stats[1:] if s[3] > ink.shape[0] * 0.3), key=lambda s: s[0])
    assert len(big) == 5, f"expected 5 large glyphs, found {len(big)}"
    return {ch: tuple(int(v) for v in s[:4]) for ch, s in zip("BASIC", big)}, n


def place(glyph, cx, cy):
    """Composite a glyph ink mask onto a white frame centred at (cx, cy)."""
    canvas = np.zeros((H, W), np.float32)
    gh, gw = glyph.shape
    x0, y0 = int(round(cx - gw / 2)), int(round(cy - gh / 2))
    canvas[y0:y0 + gh, x0:x0 + gw] = glyph
    return canvas


def to_png(ink, path, blur=0.0):
    if blur:
        k = int(round(blur * W)) | 1
        ink = cv2.blur(ink, (k, 1), borderType=cv2.BORDER_CONSTANT)
    cv2.imwrite(path, np.round((1.0 - np.clip(ink, 0, 1)) * 255).astype(np.uint8))


def main():
    os.makedirs(OUT, exist_ok=True)
    ink = ink_mask()
    boxes, _ = letters(ink)
    # Shared cap line: use the B/I/C boxes (no swash) for cap top and baseline.
    cap_top = min(boxes[c][1] for c in "BIC")
    baseline = max(boxes[c][1] + boxes[c][3] for c in "BIC")
    scale = CAP_FRAC * H / (baseline - cap_top)
    pad = 4
    for i, ch in enumerate("BASIC", 1):
        x, _, w, _ = boxes[ch]
        # Crop the whole cap band so every letter shares the same vertical
        # placement; mask out neighbouring glyphs that intrude into the box.
        n, lab, _, _ = cv2.connectedComponentsWithStats((ink > 0.02).astype(np.uint8), 8)
        crop_lab = lab[cap_top - pad:baseline + pad, x - pad:x + w + pad]
        crop = ink[cap_top - pad:baseline + pad, x - pad:x + w + pad].copy()
        ids, counts = np.unique(crop_lab[crop_lab > 0], return_counts=True)
        crop[crop_lab != ids[np.argmax(counts)]] = 0
        glyph = upscale(crop, scale)
        frame = place(glyph, W / 2, H / 2)
        to_png(frame, os.path.join(OUT, f"{i:02d}_{ch}.png"))
        if ch in BLUR:
            to_png(frame, os.path.join(OUT, f"{i:02d}_{ch}_blur.png"), BLUR[ch])
    # Full logo card, centred, LOGO_W_FRAC of the frame width.
    ys, xs = np.where(ink > 0.02)
    crop = ink[ys.min() - pad:ys.max() + pad, xs.min() - pad:xs.max() + pad]
    glyph = upscale(crop, LOGO_W_FRAC * W / (xs.max() - xs.min()))
    to_png(place(glyph, W / 2, H / 2), os.path.join(OUT, "99_logo.png"))
    for f in sorted(os.listdir(OUT)):
        print(os.path.join(OUT, f))


if __name__ == "__main__":
    main()
