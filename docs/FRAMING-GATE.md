# `ValueError: No valid frames for input framing analysis`

## The error

```
File "fdanyone/skeleton/pipeline.py", line 265, in build_skeleton_conditioning
  input_framing = analyze_input_framing(
File "fdanyone/geometry/framing.py", line 309, in analyze_input_framing
  raise ValueError("No valid frames for input framing analysis.")
```

Surfaced in ComfyUI as:

```
BackendError: backend exited with code 1
```

## Why it's confusing

Everything before it *succeeds*, loudly:

```
[SplatKit] Canonical clip written to ... (121 frames)
SAM3D body inference: 100%|████████████| 121/121 [01:24<00:00, 1.43it/s]
[SplatKit] body pose: 121 frames, 70 keypoints -> ...sam3d_mhr70_....npz
[SplatKit] Using SAM 3D Body pose supplied by the caller (121 frames)
```

Pose estimation worked. Masking worked. Nothing in the log points at the input video.

## The actual gate

In `fdanyone/geometry/framing.py`, a frame counts as valid only if **both** hold:

```python
valid = np.flatnonzero(support[frame_index])
if valid.size and torso_valid[frame_index]:
    bottoms[frame_index] = ...
valid_frames = np.isfinite(bottoms)
if not valid_frames.any():
    raise ValueError("No valid frames for input framing analysis.")
```

1. **`support`** — projected anatomy points land inside the dilated BiRefNet mask
2. **`torso_valid`** — from `_torso_valid()`:

```python
shoulders = valid[:, 5] & valid[:, 6]          # BOTH shoulders
torso = shoulders & (valid[:, 11] | valid[:, 12])
return shoulders if float(torso.mean()) < 0.5 else torso
```

where `valid` requires confidence ≥ 0.3 **and** the keypoint inside the frame:

```python
valid = ((detector[..., 2] >= 0.3)
         & (detector[..., 0] >= 0) & (detector[..., 0] < width)
         & (detector[..., 1] >= 0) & (detector[..., 1] < height))
```

Both shoulders are required. There is no fallback.

## Measurement on the failing clip

540×960 head-and-shoulders talking-head portrait.

```
--- BiRefNet masks ---
masks: (121, 960, 540) uint8 min 0 max 255
frames with ANY mask pixel >=64: 121 / 121
mean coverage: 0.6775   max coverage: 0.6871

--- torso / vitpose ---
observed_keypoints_2d: (121, 17, 3)
confidence: min 1.000  max 1.000  mean 1.000
torso_valid frames: 0 / 121
x range -103.9..701.4 (w=540)  y range 327.5..2089.2 (h=960)

--- mask support ---
frames with any SUPPORTED point: 121 / 121

VALID FRAMES (support AND torso): 0
```

Masks fine. Support fine. Confidence is 1.0 everywhere — so it is purely the **bounds** check.

Per-joint, frame 0:

```
  nose         x=   273.1 y=   410.3  in
  l-eye        x=   334.3 y=   345.8  in
  r-eye        x=   212.1 y=   342.8  in
  l-ear        x=   384.9 y=   398.9  in
  r-ear        x=   154.0 y=   396.0  in
  l-shoulder   x=   549.2 y=   714.9  OUT   <-- frame is 540 wide
  r-shoulder   x=     9.3 y=   723.9  in
  l-elbow      x=   634.2 y=  1064.8  OUT
  r-elbow      x=   -45.1 y=  1069.4  OUT
  l-hip        x=   403.4 y=  1379.1  OUT   <-- frame is 960 tall
  l-knee       x=   415.7 y=  1836.1  OUT
  l-ankle      x=   419.3 y=  2089.2  OUT
```

In-frame fraction across all 121 frames:

```
  nose 1.00   l-eye 1.00   r-eye 1.00   l-ear 1.00   r-ear 1.00
  l-shoulder 0.00   r-shoulder 0.99
  everything below the shoulders: 0.00
```

The left shoulder misses by **9.2 px** on every frame, so `valid[:,5] & valid[:,6]` is false
everywhere and `torso_valid.sum() == 0`.

## Root cause

4DAnyone reconstructs a **whole human body**. SAM 3D Body correctly fits a full skeleton, but
in a tight close-up the fitted body is so large relative to the frame that everything below the
collarbone projects outside a 960 px tall image. The shoulders span 100% of frame width.

The intrinsics are not wrong — `fx = fy = 1101.45`, `cx = 270`, `cy = 480`, exactly right for
540×960, and `image_size = [960, 540]` matches.

## Fix

Use footage where the subject is framed wider:

- **Both shoulders comfortably inside frame** — aim for shoulders at ~65–75% of frame width
  (this clip was at 100%)
- Half body or full body
- 9:16 portrait, one person staying roughly in place
- ≥720p; 1080p recommended (the pipeline warns below 720p)

Swapping to a half-body clip cleared the gate immediately with no other changes.

## What not to bother with

Pillarboxing or zooming out ~25% will push the shoulders inside the frame and pass the check.
It is not worth it: the framing would still be classified `close_up` with near-zero visible
body, so the generator would hallucinate the entire body below the neck from nothing.

Note the analysis *does* have a `close_up` label and there is even a
`32 views, 2 rings - upper body / talking` preset — but the gate runs first and is about the
**input** framing, not the view plan.

## Reproducing

[`../scripts/framing_diagnostic.py`](../scripts/framing_diagnostic.py) re-runs the exact
analysis against a finished pose directory, and
[`../scripts/keypoint_bounds.py`](../scripts/keypoint_bounds.py) prints the per-joint table.
Both need the backend interpreter.

Gotchas when writing your own:

- `predict_foreground_masks` lives in `fdanyone.foreground`, **not** `fdanyone.skeleton.foreground`
- it expects the BiRefNet **directory**, not the `.safetensors` path — passing the file makes
  `transformers` treat it as a repo id and raises `HFValidationError`
- `KEYPOINT_NAMES` is in `fdanyone.skeleton.keypoints`
