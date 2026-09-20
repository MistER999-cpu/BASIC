# BASIC

This repository holds two things:

- **[`web/`](web) — the BASIC storefront.** Next.js App Router, TypeScript and
  Tailwind. See [`web/README.md`](web/README.md).
- **The liquid-glass slot reveal** — the render pipeline documented below, which
  composites the product colourways onto vertical footage.

- **[`src/outfit.html`](src/outfit.html) — the outfit builder.** The two-slot
  mix-and-match reel documented below the slot reveal.

---

# Outfit builder

Two slots, a fake Google search bar, and a blue chevron either side of each.
Every cut changes exactly one slot, alternating top and bottom, so the
unchanged half anchors the change and the cut reads as styling rather than as
a slide advancing. Four tank colourways and eight bottoms make 15 cuts and 16
states in 10.00s, and advertise 32 outfits while showing 16.

```bash
python3 tools/tops.py                                # tank cutouts -> assets/tops
python3 tools/bottoms.py assets/incoming/bottoms     # bottoms       -> assets/bottoms
npm run outfit                                       # -> out/outfit.mp4
```

Renders in about a minute. There is no motion to blur and no footage to
composite over, so `src/outfit-pipeline.mjs` skips the plate step, runs at
`subframes: 1`, and goes straight from frames to H.264.

## Everything is a hard cut

Measured off the reference clip frame by frame: no easing anywhere, no
crossfade, no slide. A garment swap lands inside a single frame, and the only
other thing that moves is the arrow. It scales to 0.70 for exactly four frames
and snaps back on the cut frame itself — two states, no tween, colour
unchanged while pressed. Only the right arrows are ever pressed; the browse
never goes backwards.

Cuts sit 0.583s apart with a 0.60s opening hold. The reference closes on
0.67s; this one closes on 1.238s, which is what puts eight bottoms on exactly
10.00s and gives the last phrase a beat to sit on.

## Bottoms are scaled by their waistband

The tank colourways share a canvas, so one box fits all four. The bottoms do
not: eight garments from eight sources, at eight arbitrary photographic
scales. Scaling each to fill the slot would stretch a pair of jorts to
trouser length and destroy the one silhouette contrast in the set; scaling by
the widest point would shrink a wide-leg trouser to match a pair of leggings.

`tools/bottoms.py` measures the waistband instead — roughly constant across
women's bottoms — and `config.outfit.json` sets `waistPx`. Lengths then fall
out at true relative scale: the jorts render 137px tall against 482px for the
black pleated trouser. `maxLen` clamps anything that would still overrun the
frame.

Two things that band gets wrong if it is placed carelessly. Measured across
the top 3-11% it runs through belts and pleat cinches — the cream trouser
narrows to 96px at 8% of its height against 183px at its top edge, which made
it read as half again as long per waist as anything else in the set. The top
1-5% is above all of that. And the closing kernel has to stay near 0.8% of the
frame, not the 2.5% the tank matte uses: at 2.5% it bridges the gap between
two trouser legs at the crotch, `binary_fill_holes` floods the gap, and the
garment ships with an opaque wedge of backdrop between its legs.

Carving flooded regions back out afterwards is the obvious fix and is wrong. A
print containing backdrop-coloured pixels loses them — the daisy skirt mattes
into lace, because its scalloped hem connects the white of the print to the
white outside it.

## The four tanks are pinned to one silhouette

The colourways were generated, not photographed four times, and they drift:
pairwise silhouette IoU runs 0.94-0.99, hem widths spread 57px across a 1091px
garment. The pairs cluster — brown/black at 0.988, white/beige at 0.977, but
only 0.94 across that divide — which is two seeds, not one garment.

That drift did not matter for the slot reveal, where the reels are in motion.
Here the top slot changes colour and nothing else, so anything else that moves
on the cut reads as a glitch. `tools/tops.py` intersects the four alphas.
Using any single mask, or their union, would push past the garment on the
others and composite backdrop into the edge; the intersection can only fall
inside all four, at a cost of 5.9% of area on beige down to 0.9% on black, all
of it in a thin band at the outer edge.

## The typing is deterministic

`render.mjs` steps the page with `setTime(t)` and screenshots, so a re-render
has to match the last one frame for frame. Nothing in the typing may touch
`Math.random`: per-character rhythm comes from a hash of the phrase and
character index, weights are normalised so the jitter never changes a phrase's
total duration, and a character following a space gets extra delay because
real typing pauses between words. The caret holds solid while keys are moving
and blinks only while a phrase sits — a caret that blinks through its own
typing reads as a dropped frame.

One font size is fitted to the longest phrase at build time. Resizing
mid-phrase to make a long one fit would be visible on every character.

---

# Liquid-glass slot reveal

A frosted, refracting glass panel floats over vertical footage; three reels spin
product colourways vertically and stop one at a time, each on its own colour, so
the payoff is the full range sitting side by side. Nothing follows the last stop
— the clip ends on the landed reels.

Everything renders in headless Chromium, so `backdrop-filter` refracts the
actual footage rather than faking it with a static blur. ffmpeg then accumulates
subframes into real motion blur and muxes the original audio back untouched.

## Requirements

- Node 18+, Python 3 with `numpy` and `scipy`
- `ffmpeg` on `PATH`
- Chromium: auto-detected under `PLAYWRIGHT_BROWSERS_PATH`, or set `CHROME_PATH`,
  or `npx playwright install chromium`

```bash
npm install
```

## Use it

```bash
# 1. install the product shots - filenames do not matter
python3 tools/ingest.py assets/incoming      # a folder, or a .zip

#    (tools/cutout.py is the same thing with explicit names, if you prefer)
python3 tools/cutout.py --outdir assets/products \
    white=shots/white.jpg black=shots/black.jpg brown=shots/brown.jpg

# 2. drop the footage in
cp your-clip.mp4 assets/base/base.mp4

# 3. find the beats to stop the reels on
python3 tools/onsets.py assets/base/base.mp4

# 4. put those times in config.json -> timeline, then
npm run verify      # asserts each reel lands on its intended colour
npm run render
```

A 9.5s 1080×1920 render at 4 subframes takes about 4 minutes. Previews take
seconds, so tune there first:

```bash
npm run preview -- "0.3,4,6.7,8.6"     # stills at those times -> out/preview/
```

## The handle

The model mimes pulling a slot lever — she reaches at ~1.8s, her fingers close
at 2.1–2.5s, and the fist pulls down through 3.0s. A handle is drawn onto that
gesture:

```bash
python3 tools/track-hand.py assets/base/base.mp4 1.0 3.6 > out/hand.json
python3 tools/fit-lever.py out/hand.json 1.90 3.05 > assets/lever.json
```

`track-hand.py` follows skin tone inside the arm's corridor — the face is also
skin-toned and sits higher than the hand for most of the gesture, so a plain
"topmost blob" rule tracks the face instead. `fit-lever.py` then fits the pivot
a lever would need to trace that arc.

Two notes on the fit. A free circle fit is degenerate here: the mimed arc is
shallow enough to be nearly a straight line, which sends an algebraic fit off to
a 75px arm with 33% residual — hence the constrained pivot search. And the best
fit lands at the frame edge, where the rod reads as a streak across the corner
rather than a handle, so `lever.pivotOverride` mounts it to the glass panel
instead. That costs about 5% arm-length variation, invisible on a glowing rod,
and buys a handle that belongs to the interface.

The knob is drawn on the tracked hand directly, so the grip stays convincing
even where the rigid-arm assumption drifts.

## Timing is driven by the audio, not guessed

`tools/onsets.py` reports spectral-flux transients. Put the spin start and the
three stops on real onsets — a reel that stops between beats reads as a glitch
rather than a detent. The current `config.json` is locked to this clip's audio:
intro hits at 0.12/0.28/0.41 and stops at 6.56 / 7.70 / 8.44. The spin starts on
the 3.042s onset (strength 0.881) because that is where the lever bottoms out —
not the 2.72s hit, which falls mid-pull.
Re-run the tool and update `timeline` if the audio changes.

## Tuning

| Key | What it does |
|---|---|
| `panel.blur` / `saturate` / `brightness` | How hard the glass refracts what's behind it |
| `panel.tint` | Milkiness. Lower = clearer glass |
| `panel.cx` / `cy` / `w` / `h` | Placement, as fractions of the frame |
| `panel.rimDisplace` / `liquidFreq` | The liquid bend in the edge band. 0 = plain frosted glass |
| `reels.targets` | Which product each reel lands on, left to right |
| `reels.colorShift` | A settled reel breathing between two finishes: `{reel, to, delay, period}` |
| `reels.starts` | What each reel shows before the spin |
| `reels.loops` | Whole revolutions per reel. **Integers only** |
| `reels.decel` / `creep` | Deceleration shape, and the speed held until the detent catches |
| `reels.cellHeight` / `cellScale` | Slot window height, and product size inside it |
| `timeline.reelStops` | When each reel stops. These are the beats |
| `timeline.leverIn` / `leverPull` / `leverOut` | Handle appears, is pulled, springs back |
| `lever.pivotOverride` | Where the handle is mounted. Omit to use the fitted pivot |
| `fx.launchGain` / `stopGain` | Impact bloom on the launch and on each detent |
| `fx.shakePx` / `sweepDur` | Panel kick, and the light sweep down a landed cell |
| `output.subframes` | Motion blur quality. 1 = none, 4 = good, 6+ = slow |

Two constraints the code enforces, because both fail silently otherwise:

- **`reels.loops` must be whole numbers.** A fractional count leaves the reel
  mathematically unable to land on its target; it is floored and asserted.
- **`reels.targets` must be in range**, and `npm run verify` hit-tests the
  settled reels against them.

### Why a velocity profile instead of an easing curve

A power-law ease crawls asymptotically into its stop. With only three colourways
that means the final colour is already sitting in the window a second before the
beat it is meant to land on, and the stop reads as nothing happening. `slot.js`
integrates a velocity that decays to a minimum creep speed instead, so the reel
is visibly turning right up to the hit where the detent catches it dead. The
integral over the spin is exactly `travel`, so it still lands on the target cell
to the pixel.

### Why the cutout works from a smoothed difference field

A pale colourway can have edge pixels as close to the backdrop as the backdrop
itself, so filling inward from the image border leaks into the garment and
carves a transparent gash. `cutout.py` thresholds a heavily smoothed
difference-from-backdrop field instead: inside the product it stays elevated
even where local colour matches, and flat near zero on true backdrop. All inputs
share one crop so the product cannot jump between colourways as a reel spins.

## Layout

| File | Role |
|---|---|
| `src/scene.html` | The glass panel and the three reels |
| `src/slot.js` | Reel velocity, landing math, timeline |
| `src/render.mjs` | Steps the scene via `setTime(t)` and captures each subframe |
| `src/pipeline.mjs` | plate frames → render → tmix blur → H.264 + original audio |
| `tools/cutout.py` | Product shots → transparent PNGs, shared crop |
| `tools/onsets.py` | Audio transients to place the stops on |
| `tools/verify.mjs` | Asserts each reel lands on its target |
| `tools/preview.mjs` | Stills at chosen timestamps |
| `tools/track-hand.py` | Follows the lever hand through the gesture |
| `tools/fit-lever.py` | Fits the handle's pivot and arm to that arc |
| `tools/standins.mjs` | **Temporary** placeholder products — delete once real cutouts are in |

## Getting photos into the project

Images pasted into a chat may arrive as vision input rather than as files, in
which case there is nothing on disk to matte. Two routes that always produce a
real file:

- **Zip them.** A `.zip` is not an image, so it uploads as a file.
  `python3 tools/ingest.py shots.zip`
- **Commit them.** Drop them in `assets/incoming/` on GitHub, then pull.

`tools/ingest.py` sorts three or four photos by the garment's own mean colour —
darkest to lightest is black, brown, beige, white — so whatever the files are
called, they land in the right reel.

Two things it handles that a naive crop does not:

- **Alignment.** A shared crop rectangle preserves scale but not position.
  These garments were laid out slightly differently, so their bounding boxes sit
  up to 38px apart and the reels read as visibly out of line. Each garment's own
  box is centred in a common canvas instead — same scale, same centreline.
- **Uneven backdrops.** One shot falls off from rgb(211,208,215) at the
  top-left to rgb(167,163,171) at the bottom-right. Against a single median
  colour that dark corner reads as far from the backdrop as the garment does,
  and the whole frame mattes as foreground. The backdrop is fitted as a
  quadratic surface per channel so the falloff is tracked.

## Placeholders cannot ship by accident

`tools/standins.mjs` leaves an `assets/products/.STANDIN` marker and the
pipeline refuses to render while it exists. Running `tools/cutout.py` on real
photographs clears it. Placeholders look plausible at reel size, which is
exactly how one ends up in a delivered cut.

Reels are stepped by an explicit `setTime(t)` rather than `requestAnimationFrame`
or the wall clock, so a render is reproducible frame-for-frame.
