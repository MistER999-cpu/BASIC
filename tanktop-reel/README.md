# Colourway Reel

Two 9:16 product reels for the sleeveless mock-neck tank top, in four
colourways. Rebuilds the animation grammar of the reference sunglasses video.

- `women` — the tank worn as the outer layer.
- `hijabi` — the tank layered over a fine long-sleeve base with the outer
  piece worn open, which is how the garment sells into that market. The open
  placket frames the product; the contrasting sleeve makes the armhole
  binding read.

Both sets run one identical spec and share the canvas, crop ratio and timing,
so they cut together as one campaign.

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

Shot order in both sets is black → sand → ivory → brown: widest, medium,
tightest, medium, mirroring the reference's wide → profile → macro → flat
scale rhythm.

Each photo sits as a card on a canvas rather than full-bleed. The source
backdrops drift within both sets — `rgb(164,151,143)` against
`rgb(139,126,116)` in `women`, and a cool grey `rgb(141,138,142)` against a
warm `rgb(145,126,107)` in `hijabi` — which would step visibly on every cut
if butted edge to edge. It also gives the hover something to move against.

The `hijabi` ivory still was shot on a noticeably cooler ground than its three
siblings, so it carries per-channel gains in `SETS` that pull it 70% of the
way back to the set's warmth.

## Files

- `render.py` — frame renderer. Timing and motion constants at the top, the
  per-shot crop and colour config in `SETS`.
- `src/<set>/` — the four source stills per set.
- `web/` — live version with a set switcher and sliders for hold, settle
  and hover.
- `tanktop-reel-women.mp4`, `tanktop-reel-hijabi.mp4` — the rendered masters.

## Rebuilding

`render.py <set>` reads four 1080×1920 stills from `src/<set>/` and writes
`frames/<set>/`, then:

    python3 render.py hijabi
    ffmpeg -framerate 30 -i frames/hijabi/f%04d.png -c:v libx264 \
      -pix_fmt yuv420p -crf 17 -preset slow -movflags +faststart \
      tanktop-reel-hijabi.mp4

The set defaults to `women` when no argument is given.

The stills in this repo were recovered from a delivery MP4, so they carry
H.264 compression. Re-run against the original camera files for a cleaner
master.
