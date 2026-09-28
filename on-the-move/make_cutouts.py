"""Cut the eight final model images out of their backgrounds.

Uses rembg's BiRefNet-portrait model (clean hair edges, keeps bags and
hijabs). Each image runs in its own process because the model needs a lot
of memory. Output: build/cutouts/<name>.png (RGBA).
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def cut(name):
    from PIL import Image
    from rembg import new_session, remove
    session = new_session("birefnet-portrait")
    img = Image.open(os.path.join(HERE, "finals", name + ".jpg")).convert("RGB")
    remove(img, session=session).save(os.path.join(HERE, "build", "cutouts", name + ".png"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cut(sys.argv[1])
    else:
        os.makedirs(os.path.join(HERE, "build", "cutouts"), exist_ok=True)
        for path in sorted(glob.glob(os.path.join(HERE, "finals", "*.jpg"))):
            name = os.path.splitext(os.path.basename(path))[0]
            subprocess.run([sys.executable, __file__, name], check=True)
            print(name)
