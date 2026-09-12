# Colourway Reel

A 9:16 product reel for the sleeveless mock-neck tank top, in four colourways.
Rebuilds the animation grammar of the reference sunglasses video.

## Spec

Measured from the reference, and matched exactly by `render.py`:

| | |
|---|---|
| Output | 1080×1920, 30fps, 8.000s |
| Cut interval | 20 frames (0.6667s) — 90 BPM |
| Transition | hard cut, zero blend frames |
| Structure | 4 images × 3 cycles |
| Active swatch border | `#8E7264` |

Added motion: the image swap stays instantaneous, but the hero card enters
16px low and 12px right and settles over 9 frames, then floats continuously
on a 3.2s sine that runs unbroken across the cuts.

Shot order is black → sand → ivory → brown: widest, medium, tightest, medium,
mirroring the reference's wide → profile → macro → flat scale rhythm.

Each photo sits as a card on a canvas rather than full-bleed. The source
backdrops drift — `rgb(164,151,143)` on the black shot against
`rgb(139,126,116)` on the ivory — which would step visibly on every cut if
butted edge to edge. It also gives the hover something to move against.

## Files

- `render.py` — frame renderer. Tuning constants are at the top.
- `web/` — live version with sliders for hold, settle and hover.
- `tanktop-reel.mp4` — the rendered master.

## Rebuilding

`render.py` reads four 1080×1920 stills and writes `frames/`, then:

    ffmpeg -framerate 30 -i frames/f%04d.png -c:v libx264 \
      -pix_fmt yuv420p -crf 17 -preset slow -movflags +faststart \
      tanktop-reel.mp4

The stills in this repo were recovered from a delivery MP4, so they carry
H.264 compression. Re-run against the original camera files for a cleaner
master.
