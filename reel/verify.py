#!/usr/bin/env python3
"""Check a render against the geometry measured from the reference clip.

    python3 verify.py --test      # against assets/_test placeholders
    python3 verify.py             # against the real assets in assets/
"""
import cv2, numpy as np, sys, os, importlib.util
ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("b", os.path.join(ROOT, "build.py"))
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

def ncc(a, c, maxs=300):
    best = (0, -2.0)
    for s in range(-maxs, 1):
        x, y = (a[-s:], c[:len(c) + s]) if s < 0 else (a, c)
        if len(x) < 80: continue
        x, y = x - x.mean(), y - y.mean()
        d = np.sqrt((x * x).sum() * (y * y).sum())
        if d < 1e-6: continue
        v = float((x * y).sum() / d)
        if v > best[1]: best = (s, v)
    return best

def layer_speed(img, v, row, i=0, j=20):
    g = lambda w: w[row, :, :3].astype(np.float32).mean(axis=1)
    s, sc = ncc(g(b.window(img, v * i, b.W)), g(b.window(img, v * j, b.W)))
    return s / (j - i), sc

print("isolated layer speeds")
bg = b.build_bg()
s, sc = layer_speed(bg, b.BG_V, 900)
print(f"  background {s:+6.2f} px/f  (spec {-b.BG_V:+.2f})  score {sc:.3f}")
far = b.build_layer(b.FAR_SLOTS, b.FAR_STRIP, b.FAR_SPACING, "far", 1323)
s, sc = layer_speed(far, b.FAR_V, 700, 87, 107)
print(f"  far        {s:+6.2f} px/f  (spec {-b.FAR_V:+.2f})  score {sc:.3f}")

print("\nstrip arithmetic")
for n, v, w in (("near", b.NEAR_V, b.NEAR_STRIP), ("far", b.FAR_V, b.FAR_STRIP), ("bg", b.BG_V, b.BG_STRIP)):
    t = v * b.NFRAMES
    print(f"  {n:4s} travel {t:.0f} vs strip {w}  {'wraps exactly' if abs(t-w)<1e-6 else 'MISMATCH'}"
          f"   ({w/b.W:.2f} screens)")

path = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-")
                    else b.OUT)
if os.path.exists(path):
    c = cv2.VideoCapture(path); F = []
    while True:
        ok, f = c.read()
        if not ok: break
        F.append(f)
    sm = lambda f: cv2.cvtColor(cv2.resize(f, (120, 213)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    print(f"\n{os.path.basename(path)}: {len(F)} frames / {len(F)/b.FPS:.2f}s")
    print(f"  loop closure |f0 - f{len(F)-1}| = {np.abs(sm(F[0]) - sm(F[-1])).mean():.2f}"
          f"   (reference clip scored 2.65)")
else:
    print(f"\n(no render at {path} — run build.py first)")
