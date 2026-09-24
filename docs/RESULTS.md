# Results and artifact analysis

## Run settings

```
camera_preset   16 views, 1 ring - quick test   (views_per_layer 16, layer_pitches [15])
num_frames      121          start_time 0.0      target_fps auto
turbo           True (4 steps)                   attention sdpa
enable_rcp      True         enable_tcr True     views_per_group auto -> 4
seed            42           pad_short True
train quality   standard (30000 cold + 1000 warm, clean on, advect on)
```

Source: Pexels clip `8066962`, 540×960 @ 25 fps, 199 frames (7.96 s). Frames 0–120 used.

## Timings

| Stage | Duration |
|---|---|
| Conditioning load (16 + 4 videos) | 6 m |
| Model load + source encode | 50 m |
| RCP denoise, 4 steps | 3 h 37 m |
| RCP decode + publish, 4 cams | 9 m |
| Reference load + encode | 3 h 26 m |
| Target denoise, 4 steps × 4 groups | 14 h 09 m |
| Target decode + publish, 16 cams | 52 m |
| **Generate Views** | **19 h 09 m** |
| Export Frameset | 6.5 m (matte 384 s, hull 15.6 s) |
| Train Sequence, 121 frames | 95.3 m |
| **`Prompt executed in`** | **20:55:31** |

## Outputs

```
output/my_shot/
  ply/       121 frames, full SH        2.4 GB    <- SuperSplat / Blender
  splat/     compact player copies      758 MB
  preview/   per-frame PNGs             63 MB
  preview.mp4  121-frame orbit, 1280x704, 3.4 MB
output/turnaround_00001_.mp4
```

## Training behaviour

Frame 0 trains from scratch; every later frame warm-starts from the previous one.

```
frame   0  cold 30000 it  48.49 min  gaussians 148952  cleaned opacity 6827, needle 161, speck 50
frame   1  warm   400 it   0.41 min  gaussians 147408  ...  advected 0 moved, 148952 stayed  refine still
frame 120  warm   400 it   0.38 min  gaussians  56954  ...  advected 0 moved,  57299 stayed  refine still
```

Two things stand out:

**1. Warm frames ran 400 iterations, not the 1000 the header announced.** Every frame reports
`refine still`, which appears to be an early stop when little changes between frames. ~23 s each.

**2. The Gaussian count only ever falls — 149k → 57k, a 62% loss.**

| frame | 0 | 20 | 40 | 60 | 80 | 100 | 120 |
|---|---|---|---|---|---|---|---|
| gaussians | 148,952 | 106,813 | 90,749 | 78,634 | 70,869 | 63,904 | 56,954 |

Per-frame cleanup removes more than warm training adds. The drop is steepest early (2–4k per
frame through frame 10), tapering to 300–400 per frame by the end. Early removals are mostly
low-opacity Gaussians; later ones are increasingly `needle` (thin, stretched) primitives.

Also note **`advected 0 moved` on all 120 frames** — the advection step never moved a single
Gaussian, and `0.0 cm max` displacement throughout.

Net effect: the last frames are reconstructed from ~40% as many primitives as the first. Not a
failure, but late frames are softer, and it shows most in side and back views.

## Artifact analysis

The key question is whether the artifacts come from **view generation** or from **splat
training**. Answered by rendering the splat at angles that match generated cameras exactly.

The preview orbits at 3°/frame, and the generated cameras sit 22.5° apart, so:
frame 30 = 90° (cam 4), frame 60 = 180° (cam 8), frame 90 = 270° (cam 12).

[../images/compare.png](../images/compare.png) — top row: splat render. Bottom row: the
generated views it trained on, same angles. (The middle row is the same cameras taken in the
wrong orbit direction; ignore it.)

**The artifacts are already in the generated views.** The splat reproduces them faithfully.

### From generation (~80% of what you see)

- **The back is pink and streaky.** Camera 8, directly behind, shows a pale pink top with
  vertical streaks. The real garment is plain black.
- **Mottled floral patches on the sides.** Pink, orange and purple blocks painted onto a black top.
- **Views disagree with each other.** Cam 12 has orange-red blobs, cam 4 has lilac blocks and
  white blocky streaks on the arm. Conflicting views get averaged by the trainer into smeared
  colour — and some of that smear bleeds onto the *front*, which is why pink blotches appear
  near the hem in an otherwise clean front view.
- **The long ponytail is invented.** [../images/orig.png](../images/orig.png) shows her hair in
  a bun; the generated back views give her long hair down her back.

### From training (smaller)

- **Teal / orange floaters** near the head and neck. Stray Gaussians where the per-view person
  masks disagree, taking arbitrary colour where no view constrains them. (Not background
  bleed — the original background is a plain off-white wall.)
- **Streaky edges** on arms and hair ends — thin stretched Gaussians. The cleaner removed
  200–350 per frame and still didn't get them all.
- **Softening over the clip** — the Gaussian decline above.

## Why the generation failed this way

[../images/orig.png](../images/orig.png) — the source footage:

- **Plain black top, no texture.** Nothing to carry around to unseen sides; close to the hardest
  possible case for a generator asked to invent a back.
- **She faces the camera the whole clip and never turns.** Every angle beyond ~±45° is a guess.
- **540×960**, below the 720p the pipeline warns about and well below the 1080p recommended.
- Framed hips-up, so there is no lower body — this is also why it passed the shoulder gate.
- The final frame of the clip is solid black (outside the used range here, but trim it if you
  use a later window).

## What would actually improve it

In order of impact:

1. **Footage where the subject turns**, even 90° either way — gives the model real sides and back.
2. **Clothing with texture or contrast** instead of flat black.
3. **1080p source.**
4. **`32 views, 2 rings - full body` preset** — more overlapping views means more agreement for
   the trainer to work from.
5. **Turbo off (24 steps)** — only together with `num_frames=33`, or it is several times a 19 h run.
6. **Try several seeds** at 33 frames and keep the most believable back. Invented regions vary a
   lot by seed, and short runs make this cheap.

Changing *training* settings will not fix the pink back or the patchy sides — those are already
in the views the trainer was handed.
