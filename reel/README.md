# Sliding-garment reel

Puts a train of ghost-mannequin tank cutouts behind the model, travelling right
to left, timed so a garment arrives centred on her at every cut of the base
reel: the garment passing behind her is what triggers the change of look.

    python3 reel/build_mattes.py BASE.mp4 reel/mattes
    python3 reel/build_reel.py --src BASE.mp4 --out out.mp4 \
        --scale 0.17 --pitch 216 --band 0.495 --soften 0.8

Requires `rembg` and `onnxruntime`. The segmentation weights (~179MB) download
on first use to `~/.rembg` and are not kept in the repository.

## How it is put together

Measured off the base reel: 1080x1920, 24fps, nine shots cut every 31 frames,
the model frozen within each shot (0.18-0.89 levels of drift) with her torso
centre at x=315 and only 60px of spread across all nine. So there are nine
mattes, not 278, and the strip advances one pitch per 31 frames.

`SHOT_COLOURS` drives the strip. The garment arriving on a cut is the colourway
of the shot that cut starts, so the sequence is the reel's own, not a repeat.
The train is finite - eight garments, one per cut - so nothing sits behind her
at frame 1 and the strip empties as it runs out.

The strip never resets at a cut: it is one unbroken move and only the model
plate cuts over it. Verified in the rendered file at a constant -7px/frame
across the cuts. The garments are rigid translations; motion-compensating the
reference film left nothing but grain, so there is no cloth simulation in it.

Compositing needs no clean background plate. The base frame passes through
wherever the matte is solid, and the garment is drawn over the base frame
everywhere else.

## Why the matte uses a segmentation model

Keying against the backdrop was tried at length and could not be made to hold.
The backdrop is warm greige and the garments include cream, ivory and sand, so a
pale tank sits a few levels off the wall - while the wall itself carries a
36-level gradient and soft cast shadows. Every threshold that admitted the
shadows punched holes in the pale fabric; every threshold that protected the
fabric swallowed the shadows. The scheme also fed back on itself: excluding a
region removed the evidence it was backdrop, so the estimate drifted and
excluded more, and the backdrop mask slid 85.7% -> 74.9% and kept falling.

ISNet gets every case right first time: pale garments solid, wall shadows
rejected, and the gap between an akimbo arm and the torso left open so the
garment shows through it. Its edge is refined with a guided filter and otherwise
left alone - morphology with square kernels stamps 5-10px stair-steps along the
silhouette, and the strip is clipped by (1 - alpha), so those steps show up as a
ragged edge on the garment behind her.
