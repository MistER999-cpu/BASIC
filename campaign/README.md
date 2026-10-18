# Campaign video — working notes

Analysis and source material for the BASIC video. Generation tools: Nano Banana
2.1 (images) and Omni 1.1 Flash (video). No prompts yet — this file holds what
we know, so the prompt pack can be written once all outfit sets are in.

**Status:** tank, set 1 and set 2 in. Analysis only — no prompts until asked.

## Brand

- Name: BASIC — logo lockup reads `BASIC` / `ESSENTIALS`, black on transparent.
- Line: "The essentials, considered." Eleven styles, muted palette (bone, sand,
  oat, clay, ink). Quiet and editorial rather than trend-driven.
- [`brand/logo.png`](brand/logo.png) — 643×388 RGBA. Soft at full-screen; ask
  for an SVG or a larger export before final render.

## References

Neither is an AI-generated video. Both are 2D compositing: cut-out stills on
layers, moved by keyframes. That means AI makes the assets and the motion is
built in an editor, which keeps the garments exactly as they are.

### A — the folder ([`A-folder.mp4`](references/A-folder.mp4))

5.4s, 720×900 (4:5), 30fps, no audio, white background.
[Contact sheet](references/A-folder-contact-sheet.png).

| Time | What happens |
|---|---|
| 0.0–1.0s | Pink Mac-style folder, label "cosy fall essentials", under a Notes card "FILE → FAVES" (comment-for-template CTA). Cursor glides in, clicks ~0.8s. |
| 1.2–2.5s | Seven products emerge **from behind** the folder (folder is the top layer, so it masks them), fan out staggered, overshoot and settle in a ring. |
| 2.5–5.4s | Static hold. |

Keep: click → burst → settle rhythm; the folder masking the items as they exit.
Drop: the 3s hold (built for screenshots) — about 1s in a video.

### B — the slide ([`B-slide.mp4`](references/B-slide.mp4))

9.9s, 720×1280 (9:16), 60fps, with music.
[Contact sheet](references/B-slide-contact-sheet.png).

One continuous horizontal pan across a single wide panorama:

- Background: real meadow photo, washed-out cream sky, soft overcast light.
- Three full-body model cut-outs standing in the grass, mixed poses (front-on,
  walking, hand on hip).
- Oversized watercolour flowers as foreground layers between the models. Each
  flower repeats the print on the tee beside it — the decoration echoes the
  product.

| Time | What happens |
|---|---|
| 0–0.75s | Hold on model 1 |
| ~2.0s | Eases past model 2 |
| 3.25–3.9s | Settles on model 3, landing on the 3.73s beat |
| 4.25s | Brand name enters on the strongest beat in the track |
| 4.25–9.9s | Pan decelerates onto empty sky, brand name + two butterflies, hold |

The pan eases in and out at each model rather than moving at constant speed.

Audio onsets (`tools/onsets.py`): 0.36, 0.52, 0.69, **1.83**, 3.17, **3.73**,
3.88, **4.25** (strongest), 6.63, 7.87, 9.03s.

## Concept so far (not locked)

About 13s, 9:16. Folder burst → push into the folder → horizontal slide across
the looks → logo on empty sky.

- Folder in brand colours (sand, darker tab, ink label) instead of pink; drawn
  as vector in Figma/Canva rather than generated.
- Slide background: hazy overcast meadow, to match the flat studio light of the
  look photos (golden hour would read as pasted on).
- Foreground decoration tied to each look's colourway instead of a print.
- Slide order light → dark, ending on black next to the black logo.

## Items

### Tank — high mock-neck sleeveless, four colourways

Same model in all four: early 20s, shoulder-length dark brown curly hair,
centre part, olive skin, brown eyes, no-makeup look. Taupe studio backdrop,
flat frontal light, cropped at mid-thigh, identical front-on pose.

| File | Tank | Styled with |
|---|---|---|
| [`1-cream-grey-pinstripe.jpg`](looks/tank/1-cream-grey-pinstripe.jpg) | Cream / ecru | Grey pinstripe pleated wide-leg trousers |
| [`2-beige-brown-suede.jpg`](looks/tank/2-beige-brown-suede.jpg) | Beige | Brown suede five-pocket trousers |
| [`3-brown-raw-denim.jpg`](looks/tank/3-brown-raw-denim.jpg) | Brown | Raw indigo denim, tan leather belt, gold cuff, gold hoops |
| [`4-black-black-pinstripe.jpg`](looks/tank/4-black-black-pinstripe.jpg) | Black | Black pinstripe high-waist straight trousers |

Matted flat-lays of all four colourways already exist in
[`assets/products/`](../assets/products) — usable for the folder burst.

Open points:

- Cropped at mid-thigh — the slide needs full-length figures with shoes.
- Same pose ×4 — repetitive in a pan; the reference varies poses.
- "White" reads cream here but cooler in the flat-lay `white.png`. Which is true?
- Only the brown look carries accessories. Intentional?
- Taupe backdrop is close to the beige and brown tanks, which makes cut-outs
  bleed at the edges.

### Set 1 — cami crop top + bike shorts

Matching two-piece in a matte cotton-stretch jersey: cropped cami with thin
spaghetti straps and a soft V/scoop neck, high-rise bike shorts ending
mid-thigh with a centre-front seam. Three colourways: white, beige, black.

Two models:

- **Model A** — shoulder-length dark curly hair, olive skin, brown eyes. Reads
  as the tank model, but smiling and slightly softer in the face; check the
  likeness holds before mixing her across items.
- **Model B** — long straight auburn-brown hair, centre part, fair skin, curvier
  build.

All five: full length, head to toe, barefoot, same pose (weight on one leg,
feet lightly crossed, hands relaxed at the thighs), soft smile. Flat cool
light-grey backdrop, about rgb(168,168,170) — not the tank's warm taupe.

| File | Colour | Model |
|---|---|---|
| [`1-white-model-a.jpg`](looks/set-1/1-white-model-a.jpg) | White | A |
| [`2-beige-model-a.jpg`](looks/set-1/2-beige-model-a.jpg) | Beige | A |
| [`3-black-model-a.jpg`](looks/set-1/3-black-model-a.jpg) | Black | A |
| [`4-beige-model-b.jpg`](looks/set-1/4-beige-model-b.jpg) | Beige | B |
| [`5-black-model-b.jpg`](looks/set-1/5-black-model-b.jpg) | Black | B |

Open points:

- Already full length with feet in frame — ready for the slide as they are,
  unlike the tank looks.
- Barefoot here, while the tank looks will need shoes. Pick one rule for the
  whole video.
- Same pose ×5, as with the tank — the slide wants variation.
- No white on Model B. Intentional, or still to come?
- Beige sits close to both models' skin tones; at slide scale it can read as
  bare skin. Worth weighing against a contrasting background or decoration.
- Grey backdrop contrasts well with all three colours, so cut-outs should be
  clean — except white against grey at the strap edges, which is the closest
  pair.
- Cool grey here vs warm taupe for the tank: once cut out this no longer
  matters, but the two sets were lit slightly differently (this one cooler).

### Set 2 — fitted tee + capri leggings

Matching two-piece in the same matte cotton-stretch jersey: close-fitting
short-sleeve tee with a low scoop/crew neck and narrow binding, hip length;
high-rise capri leggings ending mid-calf, centre-front seam, flat waistband.
Three colourways: white, beige, black. Same two models as set 1.

Same shoot setup as set 1: full length, barefoot, flat cool light-grey
backdrop, soft smile, weight on one leg with feet lightly crossed. The two
black looks are the exception — feet planted apart, a slightly squarer stance.

| File | Colour | Model |
|---|---|---|
| [`1-white-model-a.jpg`](looks/set-2/1-white-model-a.jpg) | White | A |
| [`2-black-model-a.jpg`](looks/set-2/2-black-model-a.jpg) | Black | A |
| [`3-white-model-b.jpg`](looks/set-2/3-white-model-b.jpg) | White | B |
| [`4-beige-model-b.jpg`](looks/set-2/4-beige-model-b.jpg) | Beige | B |
| [`5-black-model-b.jpg`](looks/set-2/5-black-model-b.jpg) | Black | B |

Open points:

- No beige on Model A — the mirror of set 1, where Model B has no white.
- Beige here reads deeper and more mocha/taupe than set 1's nude beige. Same
  dye on screen or two different shades? Decide before they sit side by side.
- Waistbands and hems are consistent across all five.
- White against the grey backdrop is again the weakest cut-out edge.

## Across all three items

| | White / cream | Beige | Brown | Black |
|---|---|---|---|---|
| Tank (tank model) | ✓ cream | ✓ | ✓ | ✓ |
| Set 1 — Model A | ✓ | ✓ | | ✓ |
| Set 1 — Model B | | ✓ | | ✓ |
| Set 2 — Model A | ✓ | | | ✓ |
| Set 2 — Model B | ✓ | ✓ | | ✓ |

- 14 looks in total. Brown exists only in the tank.
- Two shoots: the tank on warm taupe, cropped at mid-thigh, styled with real
  trousers and shoes-to-be; sets 1 and 2 on cool grey, full length, barefoot,
  matching two-pieces. They will need one shared rule (shoes, framing, grade)
  to sit in the same video.
- Every look uses essentially the same front-on pose.
- Beige varies across items: tank, set 1 and set 2 each read as a slightly
  different shade.

## Still needed

- Music track (all timing goes on its beats)
- Final folder contents
- CTA wording, if any
- Logo as SVG or a larger PNG

## Flat-lays (for the folder burst)

Prompts: [`prompts/flatlays.md`](prompts/flatlays.md). Masters in beige, white
and black recoloured from them.

| Item | Status | Files |
|---|---|---|
| Tank | Approved | [`flatlays/tank/`](flatlays/tank) — white, beige, brown, black |
| Set 1 | Approved, colour fix in post | [`flatlays/set-1/`](flatlays/set-1) — white, beige, black |
| Set 2 | Approved, colour fix in post | [`flatlays/set-2/`](flatlays/set-2) — white, beige, black |

Set 1 review (measured with `tools/cutout.py`):

- Construction matches the model photos: thin straps, shallow V neckline,
  straight cropped hem, flat waistband, centre-front seam, mid-thigh length.
- Alignment across the three colours: silhouette overlap 95–98%, tighter than
  the tank set (95%). The recolour method worked.
- Framing matches the tanks: garment spans 7–94% of frame height (tanks 8–93%).
- Beige `#D3B1A0` against a `#D8B5A2` target — on target.
- White `#E5DADD` is dimmer and pinker than the tank's `#EEE8EC`; black
  `#383036` reads charcoal next to the tank's `#262429`. Both corrected in post
  with a per-channel gain at cut-out time — no regeneration needed.
- Cami hem sits just above the waistband rather than overlapping it. Reads as
  one outfit; consistent across all three, so kept.
- Cut-out: strap loops fixed in `tools/cutout.py` (enclosed backdrop is now
  cleared; tank mattes unchanged pixel for pixel). The shadowed top of the slot
  between the legs still keeps a small sliver — touch up by hand only if it
  shows at folder size.

Set 2 review:

- Scoop neck with binding, short sleeves, slim shaped body, mid-calf leggings —
  matches the model photos. No centre-front seam on the leggings (the model
  photos have one); invisible at folder size.
- Alignment across colours 96–98%; framing 7–94% of height, same as the rest.
- Beige `#B38C79` against a `#B68F7C` target — on target.
- White `#E3DBDA` and black `#373033` have the same drift as set 1 and get the
  same correction to the tank values.

## Part 1 — folder burst (rendered)

[`folder/folder-burst.mp4`](folder/folder-burst.mp4) — 5.0s, 1080×1920, 30fps,
8-sample motion blur, no audio yet.

| Time | Beat |
|---|---|
| 0.0s | Folder already dropping in; name types itself "Les BASIC’s" |
| 0.66 / 0.86s | Click selects (blue Finder highlight), double-click opens |
| 0.9–1.4s | Front flap tilts open on its hinge; folder glides up to make room |
| 1.22 / 1.58 / 1.94s | Three waves out of the pocket: tank ×4, cami set ×3, tee set ×3 |
| ~2.8s | All ten settled in a colour-sorted grid; flap closes. "Les BASIC’s" is the only text on screen |
| 3.36s | Cursor selects `tank_beige` |
| 3.55–3.93s | Quick Look window springs open from the icon |
| 4.25–4.70s | Quick Look expands to full screen — the handover to part 2 |

Rebuild:

```bash
python3 tools/folder_assets.py          # cut-outs -> campaign/folder/assets/
node src/folder/render.mjs --stills 0.7,1.3,2.9   # quick check -> out/folder-stills/
node src/folder/render.mjs              # full render (~3 min)
```

Timings are one table at the top of `src/folder/scene.html` (`T`). The cursor
is drawn in code; the folder panels are the generated images in
`folder/source/`, cut out on one shared canvas so they stay registered.
To land on music, move `click2`, `waves` and `qlOpen` onto the beats.
