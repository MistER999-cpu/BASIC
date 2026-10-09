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

### Burgundy spec (agreed)
The target is the **iPhone 18 Pro Max "Burgundy"** finish: a deep, muted wine red
with cherry undertones. Apple publishes no hex, so these are approximations:
midtones ~#561427, highlights ≤ #7A2335, shadows ~#2A0710. Light it neutral
(~5600K) so it doesn't drift brown or pink. Matte surface with a faint satin sheen.
Workflow: generate one empty **master background plate** (a seamless
cyclorama), then attach it as the background reference for every later shot.
Variants: low-angle, high-angle floor and out-of-focus close-up plates.

**Approved plate:** `assets/burgundy-ad/background-plate.jpg` (1116×2000).
Sampled colors: wall top #3A0F19, wall centre #652C35, wall right #45131C,
floor pool #8D4B55, floor bottom #431A20. A soft glow sits upper-left on the wall
and a lit floor pool sits left-centre, so the key light comes from front-left.

### Step 1 rules (agreed, in progress)
- The user uploads **the plate + the model photo in the requested set/color** for each prompt.
- **Two images per color:** (1) a medium-wide shot showing the top and bottom but not
  the whole body, and (2) a close-up on one part of the outfit.
- Order: Set 1 (black → white → sand), then Set 2 (black → white → latte).
- **One prompt at a time.** Wait for the user's approval before giving the next one.
- **The plate is a COLOR REFERENCE ONLY, never a backdrop to paste onto.** The first
  attempt came out as a cut-out pasted over the plate, and the user rejected it. Prompts must
  describe a real burgundy paper-sweep studio and re-light the model inside it:
  a cast shadow on the sweep, burgundy bounce on the skin, matching perspective.
  Attach the model photo first and the color swatch second.
- **Approved images** live in `assets/burgundy-ad/approved/`. The approved image for each color
  is the scene/light reference for that color's close-up.
  - S1-black-01-wide: approved (full body, front-left key, shadowless paper sweep look).
  - S1-black-02-close: approved (lips to bust, fingers lifting her left strap, warm rim on the shoulder).
  - S1-white-01-wide: approved (walking toward camera-left, looking back, full body, on the right third).
  - S1-white-02-close: approved (ribcage to thighs, her hand pulling the waistband, centre seam visible).
  - S1-sand-01-wide: approved (low angle from knee height, hands in her curls, rim-lit hair, wall darkening at the top).
  - S1-sand-02-close: approved (seated on the floor, high angle, hand on the thigh hem, no face). **Set 1 stills done.**
- Vary the camera angle between shots so the edit can slide angle to angle.
  **The user asked for MORE CREATIVE angles** (from the sand shots on): low/worm's-eye, overhead,
  Dutch tilt, foreground framing, dramatic perspective. Avoid plain eye-level shots.

### Step 2 rules: Omni 1.1 Flash animation (Set 1 in progress)
- Every clip is **exactly 4 seconds**, 9:16, and uses the approved still as its start frame. **One prompt at a time.**
- **Never reveal the face in shots where it is out of frame** (both close-ups, for example). The camera must not
  tilt or pan up to the face, so the AI never invents one.
- Cool, premium camera moves, chained so the edit flows (shared direction of travel):
  1 black wide: arc left→right + push-in | 2 black close: lateral slide right + strap slip
  3 white wide: truck left with her walk | 4 white close: macro push-in + waistband stretch/snap
  5 sand wide: low-angle crane rise + Dutch roll | 6 sand close: overhead slow rotate + push-in

- **Content filter lesson:** Omni rejected the black close-up prompt that used "sensual", "lips", "breathing",
  skin focus and releasing the strap. Write close-ups as neutral **product detail demos**
  (adjust, smooth, show the clean finish), keep them short and garment-focused, and give a minimal fallback.
- Progress: clip 1 (black wide) approved, clip 2 (black close, v2) approved, clip 3 (white wide) approved.
  Clip 4 (white close) failed Omni's filter 4 times, even with a crop and neutral text. The START IMAGE
  (groin-centred framing plus a hand pulling the waistband) is the trigger. Replacing it with a new still:
  a side-profile waist detail, hand not touching the waistband. For future close-ups, avoid groin-centred framing
  and hands at the waistband or inner thigh; prefer side or profile views.
  The side-profile replacement also failed, so the user chose to **SKIP clip 4** (no white close-up clip). The edit has to
  cover the gap, e.g. with a speed-ramp or a still-frame push on the white wide shot.
  Clip 5 (sand wide) also failed, so the user moved on to the Set 2 stills. Set 1 clips that work so far: 1, 2, 3. Clip 6 is untried.

### Set 2 stills (in progress), designed to be ANIMATION-SAFE for Omni
No groin-centred or crotch-forward framing, no hands at the waistband or inner thigh, no low angles looking up
between the legs, no raised-arm/armpit poses. Latte must read clearly as fabric. Creative but covered angles.
Plan: 1 black wide (high angle from above, stepping toward camera) | 2 black close (side-profile shoulder:
neckline + sleeve hem, chin cropped) | 3 white wide (side-profile walk, telephoto) | 4 white close (floor-level:
mid-calf hem + bare foot stepping) | 5 latte wide (seated on a low burgundy block, low 3/4 angle) |
6 latte close (decided later, garment-safe).
- S2-black-01-wide: approved (high angle, stepping toward camera, floor as background, head to mid-calf).
- S2-black-02-close: approved (shoulder close-up, fingers on the sleeve hem, crew neck binding, chin edge only).

An unrequested step 1 draft (16-shot list, burgundy cyclorama set) exists only
as a scratch file. Re-create it only when asked.
