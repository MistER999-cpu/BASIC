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
# 1. cut the product shots off their backdrop (one shared crop for all)
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

## Timing is driven by the audio, not guessed

`tools/onsets.py` reports spectral-flux transients. Put the spin start and the
three stops on real onsets — a reel that stops between beats reads as a glitch
rather than a detent. The current `config.json` is locked to this clip's audio:
intro hits at 0.12/0.28/0.41, the spin hit at 2.72, stops at 6.56 / 7.70 / 8.44.
Re-run the tool and update `timeline` if the audio changes.

## Tuning

| Key | What it does |
|---|---|
| `panel.blur` / `saturate` / `brightness` | How hard the glass refracts what's behind it |
| `panel.tint` | Milkiness. Lower = clearer glass |
| `panel.cx` / `cy` / `w` / `h` | Placement, as fractions of the frame |
| `panel.rimDisplace` / `liquidFreq` | The liquid bend in the edge band. 0 = plain frosted glass |
| `reels.targets` | Which product each reel lands on, left to right |
| `reels.starts` | What each reel shows before the spin |
| `reels.loops` | Whole revolutions per reel. **Integers only** |
| `reels.decel` / `creep` | Deceleration shape, and the speed held until the detent catches |
| `reels.cellHeight` / `cellScale` | Slot window height, and product size inside it |
| `timeline.reelStops` | When each reel stops. These are the beats |
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
| `tools/standins.mjs` | **Temporary** placeholder products — delete once real cutouts are in |

Reels are stepped by an explicit `setTime(t)` rather than `requestAnimationFrame`
or the wall clock, so a render is reproducible frame-for-frame.
