# BASIC — parallax reel builder

Replicates the measured geometry of the reference clip: two flat cut-out layers
scrolling horizontally at different constant speeds over a scrolling plate.
No 3D camera, no easing, no zoom, no cuts. Loops exactly at 480 frames.

## Measured spec (from the reference video)

| | value |
|---|---|
| Output | 1080x1920, 30 fps, 480 frames (16.0 s) |
| NEAR layer | 12 px/frame, strip 5760 px (5.33 screens), 4 slots @ 1440 px |
| FAR layer | 9 px/frame, strip 4320 px (4.00 screens), 4 slots @ 1080 px |
| BACKGROUND | 9 px/frame, strip 4320 px = 4 plates x 1080 px |
| Parallax ratio | near:far = 4:3 |
| FAR figure | head-top y=298, feet y=1613, height 1315 px (68.5% of frame) |
| NEAR figure | crown clipped at top edge, body runs off bottom, ~65-70% frame width |
| Beat cadence | one hero centred every 2.0 s, alternating near/far |

## Usage

Drop files in, then run:

    assets/bg/       bg1.png bg2.png bg3.png bg4.png
    assets/models/   A_near_black.png  A_near_brown.png
                     A_far_beige.png   A_far_ivory.png
                     B_near_black.png  B_near_ivory.png
                     B_far_brown.png   B_far_beige.png

    python3 build.py        ->  out/v1.mp4

Model shots may be raw green-screen JPG/PNG (the script keys and despills them)
or pre-cut RGBA PNGs (alpha is used as-is).

## Tuning knobs (top of build.py)

- `key_green(lo, hi)` — key tightness. Raise `lo` if edges are eaten, lower if green survives.
- `BG_BLUR` — extra softening on the background plate (default 11).
- `NEAR_TOP_Y` — how far the crown is pushed above the top edge.
- `BG_ORDER`, `NEAR_SLOTS`, `FAR_SLOTS` — plate order and beat arrangement.
