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
