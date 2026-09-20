# ONE TANK / FOUR WAYS — asset drop

Filenames matter. The colour token at the end of each name is how plates and
model clips get paired automatically. Use exactly: brown | black | beige | cream

00_source/
  background.jpg          bare 9:16 plate, no stand, no garment (1116x2000)
  product.jpg             product flat-lay (optional, reference only)

01_plates/                the four dressed supports
  plate_brown.jpg
  plate_black.jpg
  plate_beige.jpg
  plate_cream.jpg

02_models/model1/         the non-hijabi model, 4s clips
  m1_brown.mp4            thumb at belt / indigo denim
  m1_black.mp4            arm overhead / pinstripe flares
  m1_beige.mp4            folded arms / brown suede flares
  m1_cream.mp4            hand at throat / charcoal wide-leg

02_models/model2/         the hijabi model, 4s clips
  m2_brown.mp4            jacket edge / brown suede bomber
  m2_black.mp4            cuff turn / grey pinstripe bomber
  m2_beige.mp4            hands clasped / cream bomber
  m2_cream.mp4            hands in pockets / black shirt

03_work/                  my intermediates — do not put anything here
04_output/                finished renders — do not put anything here

## v1 build

04_output/one_tank_v1.mp4 — 1080x1920, 16s, 24fps, no text.

Layout (fractions of frame):
  ground line   0.690
  slot cx       0.11 / 0.31 / 0.69 / 0.88
  slot colour   brown / cream / black / beige
  figure height 410 px (21.4%)
  stand width   20% of frame, casters on the ground line

Timeline:
  stand   brown[0,2) black[2,6) beige[6,10) cream[10,14) brown[14,16)  xf 0.7s
  models  m1[0,4) m2[4,8) m1[8,12) m2[12,16)  xf 0.8s, staggered +0.3s per slot
  each 2s source window ping-ponged to a 94-frame cycle

Scripts: 03_work/matte.py (keying), 03_work/build.py (composite)

## v2 build

04_output/one_tank_v2.mp4 — 1080x1920, 10s, 24fps, no text, 2.9 MB.

Changes from v1:
  - stand colour cycles 3x through brown/black/beige/cream, 0.83s per
    colour, 0.18s dissolves; loops seamlessly
  - both models present in every frame; each slot toggles on its own
    switch list so the mix never aligns
  - keying: achromatic-darkening test rejects cast shadows; 2px erode plus
    normalised-convolution colour fill removes the edge halo
  - exposure matched via clip-backdrop vs plate-backdrop ratio, applied as
    a midtone gamma (1.03-1.32) instead of the earlier broken linear gain
  - tight stand mask, and vignette/grade applied after compositing, which
    removes the bright box that surrounded the stand base
  - window selection vetoes high foot motion (m1_brown's shoe dissolves
    around 0.5s in the source)
  - 1.8% push-in, film grain, global vignette, mild contrast

Scripts: 03_work/matte2.py, 03_work/build2.py

## v3 build

04_output/one_tank_v3.mp4 — 1080x1920, 10s, 24fps, 4.3 MB. Adds branding.

  logo      BASIC ESSENTIALS, 32% frame width, y 5.8%-14.2%
            keyed from the supplied PNG's own alpha channel, ink forced black
  headline  "Un seul pack"     Bodoni Moda 400 roman,  108px, baseline 25.3%
  footer    "plusieurs looks"  Bodoni Moda 400 italic, 110px, baseline 83.6%

Type is composited after the render, so it stays pixel-sharp and does not
ride the push-in. Fonts in 03_work/fonts (Bodoni Moda + Playfair Display,
OFL, via @fontsource on npm, woff2 converted to ttf with fonttools).

Script: 03_work/overlay.py
