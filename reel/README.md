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

- near figures are anchored to a fixed crown-to-thigh height (`NEAR_FIG_H`, 1820px)
  so all four sit at the same anatomical scale whatever their arm spread. 1820 is
  the largest value that keeps the widest pose inside `NEAR_MAX_W` (95% of frame),
  which is what guarantees a near model's hands stay in frame on her beat;
- their trouser band is stretched vertically to reach the bottom edge, since every
  near shot ends in trousers whose vertical fall takes the stretch invisibly;
- the background gets a small gain so its empty field lands on the reference's
  measured #E9E9E8.

## Key settings

`key_green` runs a full green clamp with lo=6 / hi=45. These were picked by
measuring residual green in the soft alpha band across the whole set: they take
A_far_ivory's edge from +6.8 to +3.6 and remove the dark outline that looser
settings leave along light garments. Nothing in the wardrobe is green, so a full
clamp is safe. `fix_edge_colour` then rebuilds colour in the semi-transparent
band from each pixel's nearest opaque neighbour, so anti-aliasing survives but
the despilled fringe does not.

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
