# Background normalizer

Harmonizes the studio background across a set of fashion frames shot (or
generated) separately, so they cut together as one setup.

The problem it solves: frames produced in separate passes drift in background
tone, gradient and vignette even when the subject is right. Correcting that by
re-generating the frame disturbs the subject; correcting it by hard-swapping the
background makes the subject look pasted on.

## How it works

1. Build a subject mask per frame by flood-filling the plain background inward
   from the borders, so interior look-alike regions (pale trousers, skin) are
   not mistaken for background.
2. Fit a smooth degree-3 polynomial surface to the background-only pixels.
   Degree 4 was tested and overfits — it tracks grain and mask edges and makes
   the result worse.
3. Pick a master frame. Compute a smooth correction field
   `C = master_surface / source_surface` and apply it to the whole frame.

Applying the correction to the whole frame rather than the background alone is
deliberate: if one frame's light was warmer, the subject was warmer too. The
field is low-frequency, so the subject receives a uniform tone shift with no
local distortion.

`--replace` additionally hard-replaces the background outside a feathered
subject mask with a clean synthetic surface plus matched grain, removing
residual mottling.

## Usage

    python3 normalize_bg.py OUT_DIR master.png other1.png other2.png ...
    python3 normalize_bg.py --replace OUT_DIR master.png other1.png ...

The first image listed is the master; everything is matched to it. Outputs are
written to `OUT_DIR` as `<name>_norm.png`. The script prints per-frame
background statistics before and after so the correction can be verified.

## Measured behaviour

Validated on four real frames with deliberately mismatched backgrounds
(tone shifts, gradients and vignettes applied):

| Metric                                | Before | After |
| ------------------------------------- | ------ | ----- |
| Mean background disagreement (levels)  | 21.7   | 0.93  |
| Worst-case pixel (levels)              | 40.5   | 4.3   |
| Centre tone disagreement (levels)      | 20.8   | 1.5   |
| Vignette falloff                       | ≤7.5%  | 1.1–2.3% |

Subject integrity: the master frame is unchanged apart from dither
(0.25 levels). Non-master frames receive a uniform tone shift with 1.8–3.8%
spread across the subject and a structural correlation of 0.992–0.999 against
the original.
