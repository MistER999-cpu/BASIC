# Liquid-glass slot reveal

A reusable version of the glass-panel slot-machine product reveal: a frosted,
refracting panel floats over your footage, three reels spin your products
vertically, they land on a matching set, and the winner grows into a hero shot.

Everything is rendered in headless Chromium — real `backdrop-filter` refraction
of your actual footage — then composited and motion-blurred in ffmpeg.

## Requirements

- Node 18+
- `ffmpeg` on `PATH`
- Chromium. Auto-detected under `PLAYWRIGHT_BROWSERS_PATH`, or set `CHROME_PATH`,
  or `npx playwright install chromium`.

```bash
npm install
```

## Use it

1. **Drop in your products.** Transparent PNG cutouts (or SVG) in
   `assets/products/`, shot flat and framed consistently — the reels trust that
   every product sits the same way in its own file.

   ```bash
   npm run products          # rebuilds config.json from that folder
   ```

2. **Drop in your footage** as `assets/base/base.mp4`, or point at it directly.

3. **Render.**

   ```bash
   npm run render -- --base assets/base/base.mp4 \
                     --wordmark "YOUR BRAND" \
                     --winner 2 \
                     --out out/final.mp4
   ```

With no base video it generates a neutral studio plate so you can see the
effect immediately.

### Check before committing to a full render

```bash
npm run verify                      # asserts every reel lands on the winner
npm run preview -- "1,5,9.2,10.5"   # stills at those timestamps -> out/preview/
```

A full 15s 1080×1920 render at 4 subframes takes roughly 8 minutes. Previews
take seconds, so tune there first.

## Tuning

Everything lives in `config.json`.

| Key | What it does |
|---|---|
| `panel.blur` / `saturate` / `brightness` | How hard the glass refracts what's behind it |
| `panel.tint` | Milkiness. Lower = clearer glass |
| `panel.radius` | Corner radius at 1080px wide; scales with output |
| `panel.rimDisplace` / `liquidFreq` | The liquid bend in the edge band. 0 = plain frosted glass |
| `panel.cx` / `cy` / `w` / `h` | Panel placement, as fractions of the frame |
| `reels.loops` | Whole revolutions per reel before it stops. **Integers only** |
| `reels.cellHeight` | Slot window height as a fraction of the panel |
| `reels.cellScale` | Product size inside its cell |
| `timeline.reelStops` | When each reel stops. Stagger these — it's what sells it |
| `hero.w` / `cy` | Size and height of the winning product after the panel dissolves |
| `output.subframes` | Motion blur quality. 1 = none, 4 = good, 6+ = slow |

`reels.loops` must be whole numbers. Fractional values leave the reel
mathematically unable to land on the winner; `npm run verify` catches it.

## How it works

```
base video ──ffmpeg──> plate frames ──┐
                                      ├──> Chromium: plate behind the glass,
products ─────────────────────────────┘    backdrop-filter refracts it live,
                                           reels stepped by setTime(t)
                                                     │
                                      screenshots at fps × subframes
                                                     │
                              ffmpeg tmix ──> accumulation motion blur ──> H.264
```

The reels are stepped deterministically by `window.setTime(t)` — no
`requestAnimationFrame`, no wall clock — so a render is exactly reproducible and
can be resumed or re-run frame-for-frame.

Motion blur is real accumulation, not a directional blur filter: every output
frame is the average of `subframes` renders taken across its exposure, which is
why the spinning products smear the way they do on the way past.

| File | Role |
|---|---|
| `src/scene.html` | The glass panel, reels, hero, packshot, end card |
| `src/slot.js` | Reel physics, landing math, the whole timeline |
| `src/render.mjs` | Steps the scene and screenshots each subframe |
| `src/pipeline.mjs` | ffmpeg extract → render → blur → encode |
| `tools/` | Preview stills, jackpot verification, placeholder products, plate |

## Notes

- The end card and wordmark are yours to set (`--wordmark`, `brand.*` in config).
  Placeholder products in `assets/products/` are generated stand-ins — replace
  them with your own cutouts and delete `tools/make-placeholders.mjs`.
- Audio is copied from the base video untouched. The reference sound design is
  just an ambient pad plus a bright transient on the first spin and on the final
  stop — worth adding on a stagger that matches `timeline.reelStops`.
