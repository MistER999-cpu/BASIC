# BASIC — parallax reel builder

Replicates the measured geometry of the reference clip: two flat cut-out layers
scrolling horizontally at different constant speeds over a scrolling plate.
No 3D camera, no easing, no zoom, no cuts. Loops exactly at 480 frames.

## Measured spec (from the reference video)

| | value |
|---|---|
| Output | 1080x1920, 30 fps, 450 frames (15.0 s), H.264 |
| NEAR layer | 12.8 px/frame, strip 5760 px (5.33 screens), 4 slots @ 1440 px |
| FAR layer | 9.6 px/frame, strip 4320 px (4.00 screens), 4 slots @ 1080 px |
| BACKGROUND | 9.6 px/frame, strip 4320 px = 4 plates x 1080 px |
| Parallax ratio | near:far = 4:3 |
| FAR figure | head-top y=298, feet y=1613, height 1315 px (68.5% of frame) |
| NEAR figure | crown clipped at top edge, body runs off bottom, ~65-70% frame width |
| Beat cadence | one hero centred every 1.875 s, alternating near/far |
| Model coverage | 59.4% of frame on average (reference: ~59%) |

Each layer's travel over the loop equals its own strip width, so all three wrap
exactly at frame 450 with no crossfade.

## Adaptations from the reference

The supplied poses are wider than the reference's — near shots are bbox aspect
0.58 against the reference's 0.396, far shots run 36-66% of frame width against
18-24%. Height-fitting the near layer alone would push it past the frame edges
and bury the far model, so:

- the near layer is width-capped at 88% of frame, tuned so model coverage lands
  on the reference's measured ~59%;
- its trouser band is stretched vertically to reach the bottom edge, since every
  near shot ends in trousers whose vertical fall takes the stretch invisibly;
- the background gets a small gain so its empty field lands on the reference's
  measured #E9E9E8.

## Usage

Drop files in, then run:

    assets/bg/       bg1 bg2 bg3 bg4   (the colour wave, in order)
    assets/models/   A_near_black  A_near_brown  A_far_beige  A_far_ivory
                     B_near_black  B_near_ivory  B_far_brown  B_far_beige

    python3 build.py        ->  out/v1.mp4

Model shots may be raw green-screen JPG/PNG (the script keys and despills them)
or pre-cut RGBA PNGs (alpha is used as-is).

## Tuning knobs (top of build.py)

- `key_green(lo, hi)` — key tightness. Raise `lo` if edges are eaten, lower if green survives.
- `BG_BLUR` — extra softening on the background plate (default 11).
- `NEAR_TOP_Y` — how far the crown is pushed above the top edge.
- `BG_ORDER`, `NEAR_SLOTS`, `FAR_SLOTS` — plate order and beat arrangement.
