# survêt — shot list

Generate these with an image model that takes **reference images** (so the model
and the garment stay identical across shots). Attach the front/back product
photo of the colourway you are generating as the reference.

**Aim for 6–8 shots per colourway (sand, black, brown) = 18–24 images.** The
edit cuts every ~0.12 s, so more variety looks better than more polish.

## Settings for every shot

- **Format:** vertical **9:16**, 2K or larger (e.g. 1152×2048 / 1440×2560)
- **Background:** keep the same clean light-grey/off-white studio sweep as the
  product photos. The word "survêt" sits on top of the images in the tracksuit
  colours, so a busy or coloured background will hide it.
- **Subject centred left-to-right.** Each strip only shows the middle quarter of
  the frame, so anything at the edges is cropped out.
- **One model, one outfit** per image (no collages, no text, no logos).

## Base prompt (paste first, then add one shot line)

> Fashion campaign photo of the same model and the same outfit as the reference
> image: an oversized long-sleeve crew-neck tunic top with side slits, matching
> straight wide-leg trousers, both in [SAND / CHARCOAL BLACK / CHOCOLATE BROWN]
> soft jersey, worn with matching suede trainers. Same face, same curly
> shoulder-length dark hair. Clean light-grey seamless studio background,
> soft even studio light, sharp focus, realistic fabric texture, editorial
> streetwear mood. Vertical 9:16.

## Shot lines

| # | Shot | Add to the prompt |
|---|---|---|
| 1 | **Worm's-eye** | Camera on the floor at her feet, pointing straight up; she towers over the lens, trainers huge in the foreground, looking down at the camera. |
| 2 | **Top-down** | Bird's-eye view from directly above; she looks up into the lens, the trousers and trainers foreshortened below her. |
| 3 | **Walk-in** | Mid-stride walking toward the camera, the tunic's side slit flaring open, trousers swinging, slight motion in the fabric. |
| 4 | **Dutch tilt** | Camera tilted 20°, full body, leaning back with one shoulder, hands relaxed, cool expression. |
| 5 | **Over the shoulder** | Back to the camera, head turned over her shoulder to look straight into the lens. |
| 6 | **Jump** | Caught mid-air at the top of a jump, knees bent, sleeves and hem lifting, trainers off the floor. |
| 7 | **Crouch** | Low streetwear squat on her heels, forearms on her knees, looking up at the lens; camera at her eye level. |
| 8 | **Stretch** | Both arms stretched straight overhead, long sleeves sliding down, the tunic lifting slightly; shot from a low angle. |
| 9 | **Fisheye reach** | Wide-angle close to the lens, one hand reaching toward the camera, playful expression. |
| 10 | **Seated** | Sitting on the studio floor, knees up, one arm hugging her knees, wide trousers draped over the trainers. |
| 11 | **Detail – neckline** | Extreme close-up of the ribbed crew neck and the dropped shoulder seam, chin just in frame. |
| 12 | **Detail – hem** | Close-up of the side slit and hem against the trousers, one hand resting on the hip. |
| 13 | **Detail – sleeve** | Close-up of the long sleeve cuff falling over her hand, fabric texture visible. |
| 14 | **Detail – trainers** | Ground-level close-up of the trouser hem breaking over the trainers, one foot stepping forward. |

Shots 1–10 should be done in **all three colours**. For the close-ups (11–14),
two or three per colour is enough.

**End card (optional):** one calm, full-length, front-facing shot per colour with
the whole body visible and some space above the head. Put the word `end` in its
filename, e.g. `sand-end.jpg`. Without one, the edit uses the front reference
photo.

## Sending them back

Name the files however you like, as long as the colour is clear, e.g.
`sand-01.jpg`, `black-worms-eye.png`. They go into `survet/shots/sand/`,
`survet/shots/black/` and `survet/shots/brown/`.
