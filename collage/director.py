"""Director's cut: the collage finished as a BASIC ad.

    python3 collage/build.py cards          # the 16 cards, if not built yet
    python3 collage/director.py             # -> out/collage/directors_cut.mp4
    python3 collage/director.py --stills    # key frames only -> out/collage/stills/

On top of build.py's cut (same cards, same beat grid, same hold, same
reframing) it adds:

- A film finish on the background layer only: soft luma grain weighted to the
  midtones, and a light vignette. The cards stay clean, which is the contrast
  the reference is built on: grainy film behind, crisp photograph in front.
- A settle on every card: the photo lands 3.5% large and eases to rest over
  five frames, inside a card frame that never moves.
- A colour chip under the card, in the storefront's own colourway names and
  hex values (Bone, Sand, Clay, Ink), changing with every card.
- An end card on the empty studio plate: the four colourways land one per beat
  in a 2x2 grid, then the wordmark, product name and price. It runs from beat
  42, where the film ends, to beat 50, the end of the phrase.

Everything is composited in RGB here. The film is decoded and the result
encoded with the bt709 matrix explicitly, so colours survive the round trip.
"""

import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402

W, H, FPS = B.W, B.H, B.FPS
FONTS = os.path.join(B.ROOT, "fonts")
PLATE = os.path.join(B.ROOT, "base", "plate.jpg")

# Storefront colourways (web/lib/products.ts) keyed by the card-name colour.
COLOURWAYS = {
    "white": ("Bone", (0xF2, 0xEF, 0xE9)),
    "beige": ("Sand", (0xCB, 0xB9, 0x9E)),
    "brown": ("Clay", (0x6B, 0x4A, 0x34)),
    "black": ("Ink", (0x19, 0x16, 0x14)),
}
INK = (0x16, 0x11, 0x0E)
PAPER = (0xF7, 0xF4, 0xEF)
MUTED = (0x5F, 0x57, 0x4F)

GRAIN = 4.0 / 255      # grain amplitude at mid-grey
END_GRAIN = 0.6        # the end card carries type; keep its plate calmer
VIGNETTE = 0.10        # darkening at the corners
SETTLE_FRAMES = 5
SETTLE_SCALE = 0.035

END_BEATS = 50          # the film runs to beat 42; the end card holds to 50
GRID_BEATS = [42, 43, 44, 45]
TITLE_BEAT = 46
LINE_BEAT = 47
GRID = ["13-white-closeup", "06-beige-closeup", "03-brown-closeup", "12-black-closeup"]
AUDIO_FADE = 1.2


def beat_frame(k):
    return int(round((B.DROP - B.MUSIC_START + k * B.BEAT) * FPS))


# ---------------------------------------------------------------- type

def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight is not None:
        f.set_variation_by_axes([min(32, max(14, size)), weight])
    return f


def text_rgba(text, fnt, fill, tracking=0.0):
    """Render text with letter-spacing as tracking * font size, like CSS em."""
    size = fnt.size
    advance = [fnt.getlength(ch) + tracking * size for ch in text]
    width = int(math.ceil(sum(advance) - tracking * size)) + 4
    asc, desc = fnt.getmetrics()
    im = Image.new("RGBA", (width, asc + desc + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 2
    for ch, adv in zip(text, advance):
        d.text((x, 2), ch, font=fnt, fill=fill + (255,))
        x += adv
    return np.asarray(im).astype(np.float32) / 255


def chip(colour, height=54, size=21, pad=22):
    name, rgb = COLOURWAYS[colour]
    fg = INK if sum(rgb) > 380 else PAPER
    t = text_rgba(name.upper(), font("Inter[opsz,wght].ttf", size, 560), fg, tracking=0.28)
    w = t.shape[1] + 2 * pad
    im = np.zeros((height, w, 4), np.float32)
    im[..., :3] = np.array(rgb, np.float32) / 255
    im[..., 3] = 1
    y = (height - t.shape[0]) // 2 + 1
    paste(im, t, pad, y)
    return im


def paste(dst, src, x, y):
    """Alpha-over src (RGBA float) onto dst (RGB or RGBA float) at x, y."""
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x0 >= x1 or y0 >= y1:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4]
    region = dst[y0:y1, x0:x1]
    region[..., :3] = s[..., :3] * a + region[..., :3] * (1 - a)
    if dst.shape[2] == 4:
        region[..., 3:4] = a + region[..., 3:4] * (1 - a)


# ---------------------------------------------------------------- film finish

_rng = np.random.default_rng(7)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r2 = ((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2
VIG = (1 - VIGNETTE * np.clip(_r2 / 2, 0, 1) ** 1.5)[..., None]


def grain():
    fine = cv2.GaussianBlur(_rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.75)
    coarse = cv2.resize(_rng.standard_normal((H // 3, W // 3)).astype(np.float32), (W, H),
                        interpolation=cv2.INTER_CUBIC)
    g = fine / 0.37 + 0.3 * coarse
    return g / 1.05


def finish(rgb, strength=1.0):
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    amp = strength * GRAIN * (0.3 + 2.8 * luma * (1 - luma))
    out = rgb + (grain() * amp)[..., None]
    return np.clip(out * VIG, 0, 1)


# ---------------------------------------------------------------- layers

def load_card(name, w=B.CARD_W, h=B.CARD_H):
    im = cv2.imread(os.path.join(B.OUT, "cards", name + ".png"))
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    return cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA) if im.shape[:2] != (h, w) else im


def settled(card, k):
    """The card photo k frames after it lands: 3.5% large, easing to rest."""
    if k >= SETTLE_FRAMES:
        return card
    p = k / SETTLE_FRAMES
    s = 1 + SETTLE_SCALE * (1 - p) ** 3
    h, w = card.shape[:2]
    big = cv2.resize(card, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_CUBIC)
    y0, x0 = (big.shape[0] - h) // 2, (big.shape[1] - w) // 2
    return big[y0:y0 + h, x0:x0 + w]


def reframe(rgb, z):
    if z == 1.0:
        return rgb
    zw, zh = 2 * round(W * z / 2), 2 * round(H * z / 2)
    # Bicubic, not Lanczos: the generated footage is already sharpened, and
    # Lanczos ringing brightens the halo it leaves on dark edges.
    big = cv2.resize(rgb, (zw, zh), interpolation=cv2.INTER_CUBIC)
    x0 = (zw - W) // 2
    return big[zh - H:, x0:x0 + W]


def plate_frame(k, n):
    """The empty cyclorama with a slow push-in across the end card."""
    if not hasattr(plate_frame, "src"):
        im = cv2.cvtColor(cv2.imread(PLATE), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        s = max(W / im.shape[1], H / im.shape[0])
        plate_frame.src = cv2.resize(im, (math.ceil(im.shape[1] * s), math.ceil(im.shape[0] * s)),
                                     interpolation=cv2.INTER_AREA)
    src = plate_frame.src
    z = 1 + 0.04 * (k / max(n - 1, 1))
    ch, cw = H / z, W / z
    cx, cy = src.shape[1] / 2, src.shape[0] / 2
    M = np.array([[cw / W, 0, cx - cw / 2], [0, ch / H, cy - ch / 2]], np.float32)
    return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)


class EndCard:
    CW, CH, GAP_X, CHIP_H, GAP_Y = 380, 475, 20, 44, 30

    def __init__(self):
        bw = 2 * self.CW + self.GAP_X
        self.x0 = (W - bw) // 2
        self.y0 = 360
        self.cards = [load_card(n, self.CW, self.CH) for n in GRID]
        self.chips = [chip(n.split("-")[1], height=self.CHIP_H, size=17, pad=16) for n in GRID]
        self.wordmark = text_rgba("BASIC", font("Inter[opsz,wght].ttf", 34, 520), INK, tracking=0.28)
        self.title = text_rgba("The Ribbed Mock-Neck Tank", font("InstrumentSerif-Regular.ttf", 66), INK)
        self.line = text_rgba("FOUR COLOURWAYS  —  €68", font("Inter[opsz,wght].ttf", 22, 520),
                              MUTED, tracking=0.2)
        self.url = text_rgba("basic.studio", font("Inter[opsz,wght].ttf", 26, 420), INK, tracking=0.02)

    def slot(self, i):
        r, c = divmod(i, 2)
        return (self.x0 + c * (self.CW + self.GAP_X),
                self.y0 + r * (self.CH + self.CHIP_H + self.GAP_Y))

    def draw(self, rgb, f):
        for i, beat in enumerate(GRID_BEATS):
            a = beat_frame(beat)
            if f < a:
                continue
            x, y = self.slot(i)
            rgb[y:y + self.CH, x:x + self.CW] = settled(self.cards[i], f - a)
            paste(rgb, self.chips[i], x, y + self.CH)
        grid_bottom = self.slot(3)[1] + self.CH + self.CHIP_H
        if f >= beat_frame(TITLE_BEAT):
            paste(rgb, self.wordmark, (W - self.wordmark.shape[1]) // 2, 250)
            paste(rgb, self.title, (W - self.title.shape[1]) // 2, grid_bottom + 34)
        if f >= beat_frame(LINE_BEAT):
            y = grid_bottom + 34 + self.title.shape[0] + 14
            paste(rgb, self.line, (W - self.line.shape[1]) // 2, y)
            paste(rgb, self.url, (W - self.url.shape[1]) // 2, y + self.line.shape[0] + 16)


# ---------------------------------------------------------------- render

def decode_base():
    cmd = [B.ffmpeg(), "-v", "error", "-i", B.BASE,
           "-vf", "scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24",
           "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = W * H * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
    p.wait()


def frames():
    segs, n, _ = B.plan()
    total = beat_frame(END_BEATS)
    cards = {name: load_card(name) for name in B.ORDER}
    chips = {c: chip(c) for c in COLOURWAYS}
    bounds = [0] + B.BASE_CUTS + [n]
    end = EndCard()
    base = decode_base()
    for f in range(total):
        if f < n:
            clip = next(k for k in range(len(bounds) - 1) if bounds[k] <= f < bounds[k + 1])
            rgb = finish(reframe(next(base), B.REFRAME[clip]))
            a, _, name = next(s for s in segs if s[0] <= f < s[1])
            rgb[B.CARD_Y:B.CARD_Y + B.CARD_H, B.CARD_X:B.CARD_X + B.CARD_W] = settled(cards[name], f - a)
            paste(rgb, chips[name.split("-")[1]], B.CARD_X, B.CARD_Y + B.CARD_H)
        else:
            rgb = finish(plate_frame(f - n, total - n), END_GRAIN)
            end.draw(rgb, f)
        yield f, rgb
    return total


def render():
    total = beat_frame(END_BEATS)
    dur = total / FPS
    fades = f"afade=t=in:d=0.01,afade=t=out:st={dur - AUDIO_FADE:.3f}:d={AUDIO_FADE}"
    out = os.path.join(B.OUT, "directors_cut.mp4")
    cmd = [B.ffmpeg(), "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-ss", str(B.MUSIC_START), "-t", str(dur), "-i", B.MUSIC,
           "-filter_complex",
           f"[0:v]scale=in_range=pc:out_color_matrix=bt709:out_range=tv,format=yuv420p[v];"
           f"[1:a]{fades},{B.loudnorm(dur, fades)},aresample=48000[a]",
           "-map", "[v]", "-map", "[a]",
           # Grain is costly to encode: uncapped at crf 16 it ran 33 Mbps. The
           # cap keeps it a shareable size; platforms re-encode anyway, and a
           # high-quality master survives that better than a starved one.
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-maxrate", "16M", "-bufsize", "32M",
           "-profile:v", "high", "-tune", "grain",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-t", str(dur), out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f, rgb in frames():
        p.stdin.write((rgb * 255 + 0.5).astype(np.uint8).tobytes())
        if f % 48 == 0:
            print(f"  {f / FPS:5.1f}s / {dur:.1f}s", flush=True)
    p.stdin.close()
    assert p.wait() == 0
    print("wrote", out)


def stills(at):
    d = os.path.join(B.OUT, "stills")
    os.makedirs(d, exist_ok=True)
    want = {int(round(t * FPS)) for t in at}
    for f, rgb in frames():
        if f in want:
            cv2.imwrite(os.path.join(d, f"{f / FPS:06.2f}.png"),
                        cv2.cvtColor((rgb * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
        if f >= max(want):
            break


if __name__ == "__main__":
    if "--stills" in sys.argv:
        stills([0, 0.08, 7.4, 13.9, 19.2, 19.7, 20.2, 20.6, 21.2, 22.6])
    else:
        render()
