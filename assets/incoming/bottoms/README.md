# Bottoms drop folder

The eight lower-body garments for the outfit-builder video. Drop the
Nano Banana flat-lay renders here — 2000x2000, garment laid flat on grey,
waistband spanning ~30% of the frame width.

## Naming

Filenames matter here, unlike the tank shots one level up. Those are sorted
automatically by the garment's own colour; there is no equivalent for eight
different silhouettes, so the name carries both the reel order and the
identity:

    1-wide-leg-trouser-black.jpg
    2-slip-skirt-espresso.jpg
    3-straight-denim-mid.jpg
    ...
    8-cargo-sand.jpg

The leading number is the order the garment appears in the reel. Keep it
zero-padded or not, either is fine, but keep it first.

## Why this is a subfolder

`tools/ingest.py` reads the files sitting directly in `assets/incoming/` and
hard-fails on anything other than three or four of them. Subfolders are
ignored, so the four tank colourways above keep working untouched while these
eight live here.

## Checks before uploading

- Waistband horizontal, legs parallel, nothing rotated. A rotated garment gets
  a wider bounding box and lands at the wrong scale in the reel.
- Clear grey margin on all four sides, nothing cropped.
- Pale or grey garments shot against a darker grey, not the default
  RGB(205,203,210) — otherwise the matte has nothing to separate.
