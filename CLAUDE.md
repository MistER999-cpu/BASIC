# Project memory

## Who
The user is a graphic designer running their own womenswear brand, BASIC
(tagline in `web/lib/site.ts`: "The essentials, considered."). They make
images with **Nano Banana 2.1** and animate them with **Omni 1.1 Flash**.

## Products: two sets, three colors each
Reference photos show the same model (early 20s, warm light-olive skin, dark
brown curly chin-length bob, centre part, barefoot) on a grey studio backdrop.

- **Set 1, Cami Set:** a cropped cami with ~5 mm spaghetti straps, a soft shallow
  V-neck with self-fabric binding, and a hem at the shorts' waistband. High-rise
  biker shorts with a wide flat folded waistband, a centre-front seam and a
  twin-needle hem at mid-thigh. Colors: black, white, warm sand beige.
- **Set 2, Tee Set:** a slim short-sleeve tee with a slightly wide lowered crew
  neck, self-fabric binding, twin-needle sleeve and body hems, and a hem at the
  high hip. High-rise capri leggings with a wide flat waistband and a
  twin-needle hem at mid-calf. Colors: black, white, latte beige (reads a
  touch deeper than Set 1's sand).
- Fabric: matte, opaque cotton-elastane jersey with no logos or pockets.
- Prompt rules: black needs a rim light, white needs "fully opaque" and
  balanced exposure, and beige must be "clearly distinct from skin" (never
  write "nude"). Only front views exist, so avoid back and 360° shots unless
  back photos arrive.

The first general prompt pack is `prompts/two-set-campaign.md`.

## Current job: Instagram ad, "burgundy" video (waiting for the user's cue)
**Do not start any step until the user gives the cue.**

Concept: the same model wears the two outfits at two different times, Set 1
first and Set 2 second. The camera slides from angle to angle and shot to
shot on a **burgundy background**. It must feel **cool and premium**.

Workflow, one step at a time, each on the user's go:
1. Claude writes detailed **Nano Banana 2.1** image prompts for every shot.
2. The user generates all the images. Claude then writes detailed
   **Omni 1.1 Flash** prompts to animate them.
3. The user sends the videos back. Claude edits them into one compact,
   professional **Instagram ad** (9:16) with multiple visual effects and
   sound effects (ffmpeg is available in the container).

An unrequested step 1 draft (16-shot list, burgundy cyclorama set) exists only
as a scratch file. Re-create it only when asked.
