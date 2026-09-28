"""Render the ON THE MOVE letter cards to match the reference edit.

Font: Unbounded Medium (wght 500), cap height = 25% of frame height,
centred on the glyph's bounding box. T, H and the first E get a horizontal
box blur (measured from the reference: 29 / 41 / 31px at 720px width).
"""
import os
import numpy as np
import cv2
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
VAR_FONT = os.path.join(HERE, "fonts", "Unbounded-Variable.ttf")
STATIC_FONT = os.path.join(HERE, "fonts", "Unbounded-Medium.ttf")
OUT = os.path.join(HERE, "letters")

SEQUENCE = "ONTHEMOVE"
# Horizontal blur width per sequence position, as a fraction of frame width
# (fitted against the reference frames).
BLUR = {2: 29 / 720, 3: 41 / 720, 4: 31 / 720}


def font_path():
    if not os.path.exists(STATIC_FONT):
        instancer.instantiateVariableFont(TTFont(VAR_FONT), {"wght": 500}).save(STATIC_FONT)
    return STATIC_FONT


def render(ch, blur=0.0):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    # Size and vertical position come from the cap height of "H" so round
    # letters keep their natural overshoot; horizontal centre is per glyph.
    probe = ImageFont.truetype(font_path(), 100)
    cap = d.textbbox((0, 0), "H", font=probe)
    size = round(100 * (H * 0.25) / (cap[3] - cap[1]))
    f = ImageFont.truetype(font_path(), size)
    cap = d.textbbox((0, 0), "H", font=f)
    bb = d.textbbox((0, 0), ch, font=f)
    d.text((W / 2 - (bb[0] + bb[2]) / 2, H / 2 - (cap[1] + cap[3]) / 2), ch, font=f, fill=0)
    a = np.array(img)
    if blur:
        k = int(round(blur * W)) | 1
        a = cv2.blur(a, (k, 1), borderType=cv2.BORDER_REPLICATE)
    return a


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for i, ch in enumerate(SEQUENCE):
        path = os.path.join(OUT, f"{i + 1:02d}_{ch}.png")
        cv2.imwrite(path, render(ch, BLUR.get(i, 0.0)))
        print(path)
