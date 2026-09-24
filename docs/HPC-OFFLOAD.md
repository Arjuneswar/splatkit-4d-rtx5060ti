# Running generation on an HPC, training locally

Generate Views is the only stage that overcommits a 16 GB card. Moving just that stage to a
cluster and keeping training local is attractive — training already runs comfortably at 2.4 GB.

**Status: designed from the source, not yet executed.** SplatKit's installer is Windows-only and
the docs state Linux backend setup is unsupported. The reasoning below is why it should
nonetheless work.

## Why it should work

- **The generator is a standalone CLI.** `vendored/4danyone/inference.py` takes ordinary
  arguments (see signature below) and is driven by `fire`.
- **No Windows-specific code in the generator.** A grep for `win32`, `msvcrt`,
  `platform.system`, `os.name ==` and `.exe` across `vendored/4danyone/` returns nothing. The
  platform branches live in SplatKit's own process-handling layer
  (`core/splatting/runner.py`, `backend.py`), which handles both.
- **Generation does not need gsplat.** gsplat is the Windows-only prebuilt wheel, and only
  *training* uses it.
- **Requirements are plain pip packages** — torch 2.8, torchvision 0.23, transformers, kornia,
  timm 0.9.12, hydra, av, opencv. Nothing platform-locked.
- **Multi-GPU is supported** via `gpu_ids`.

## Handoff points

SplatKit has no "load a generation result from elsewhere" node. Two options:

**A. Frameset handoff (recommended).** Run generation *and* `export_splat_frameset.py` on the
cluster, copy the frameset back, load it with **Load Frameset** → **Train Sequence**.
`SplatKit_LoadFrameset` takes a plain folder string and is documented to accept
"compatible datasets from other producers". No hash matching needed.

**B. Result-cache handoff.** Generate Views skips work when
`(result_dir / "metadata.json").is_file()`, printing `reusing generated views`. You would have
to place the result at exactly `<data_dir>/fdanyone/<stem>@<label>`, where `label` is a SHA-1
over a params dict including `runtime_id`, all model file hashes and the local `model_dir`
path. Getting that right from outside is fiddly — an attempt to reproduce the hash offline did
not match. If you want this route, queue Generate Views locally, read the label from the log
line `generating N views for ... (rXXXXXXXXXX, ...)`, cancel, and use that label.

Option A avoids all of it.

## Files to copy to the cluster

| What | From |
|---|---|
| Generator | `custom_nodes/comfyui-splatkit/vendored/4danyone/` |
| Exporter | `custom_nodes/comfyui-splatkit/tools/export_splat_frameset.py` |
| Generator models | `models/splatkit/4danyone/` — checkpoint, VAE, prompt context, Turbo LoRA |
| Matting models | `models/splatkit/birefnet/` — all 4 files |
| Input video | your clip |
| **Pose npz** | `output/splatkit/4danyone/<timeline>/clip_<digest>_.../pose/results/<stem>/sam3d_mhr70_<digest>.npz` |

Bringing the **pose npz** means SAM 3D Body never needs to exist on the cluster — the
skeleton worker accepts it via `--sam3d_npz` and logs
`Using SAM 3D Body pose supplied by the caller`. Compute it locally first (it takes ~90 s) by
running the graph until generation starts, then cancel.

## Environment

Python 3.11, torch 2.8 built for the cluster's CUDA 12.x, then:

```bash
pip install -r requirements.txt     # from vendored/4danyone/
```

## Generate 32 views

`32 views, 2 rings - full body` = **16 views per ring at pitches 15° and 35°**
(`CAMERA_PRESETS` maps it to `(16, "15,35")` — the number in the preset name is the total).

```bash
python inference.py \
  --video_path clip.mp4 \
  --data_dir work \
  --model_dir models/4danyone \
  --checkpoint_path models/4danyone/model.safetensors \
  --vae_path models/4danyone/Wan2.2_VAE.pth \
  --prompt_context_path models/4danyone/prompt_context.safetensors \
  --turbo_lora_path models/4danyone/Wan22_TI2V_5B_Turbo_lora_rank_64_fp16.safetensors \
  --foreground_model_dir models/birefnet \
  --sam3d_npz sam3d_mhr70_<digest>.npz \
  --views_per_layer 16 \
  --layer_pitches "[15,35]" \
  --enable_rcp True --enable_tcr True --enable_turbo True \
  --seed 42 --pad_short True \
  --gpu_ids "[0]"
```

Full parameter list is the `inference()` signature in `inference.py`. Notable ones:

```
views_per_layer   must be divisible by 4 or 6
layer_pitches     each between -15 and 45
views_per_group   auto picks 6 when possible, else 4
start_yaw         0 faces the person
yaw_span          360 = full orbit, end angle excluded
```

The docstring notes the input video must contain **at least 121 usable frames**; `pad_short`
covers shorter clips.

## Export the frameset

```bash
python export_splat_frameset.py \
  --backend-root <path to 4danyone> \
  --foreground-model-dir models/birefnet \
  --result-dir <result dir printed above> \
  --out-root framesets \
  --frames 0:120 \
  --batch 8 \
  --device cuda:0 \
  --pose-npz sam3d_mhr70_<digest>.npz
```

`--pose-npz` is what writes `skeleton.npz` into the frameset, which the trainer's warm-start
and advection read.

## Back on the workstation

1. Copy the frameset folder into `ComfyUI/output/splatkit/framesets/`.
2. Graph: **Load Frameset** (folder = that path) → **Train Sequence** → **Sequence Player**.

Keeping it under `output/` also satisfies SplatKit's path restriction, which limits free-form
path widgets to ComfyUI's own input/output/temp/models folders on public-listening servers.

## Expectations

- **VRAM:** 16 views peaked at 24.06 GB. 32 views needs more — use ≥40 GB, ideally an 80 GB
  A100/H100. With no paging the wall-clock should be hours, not the 19 h seen here, but this
  hasn't been measured.
- **Local training with 32 cameras:** twice the images per frame, so longer than the 95 min
  measured at 16 cameras. Memory should still be comfortable — 16 cameras used 2.4 GB.
- **It will not fix the invented back.** More views improve *consistency between* generated
  angles, reducing patchy smearing. They cannot recover information the camera never captured.
