# Install

What actually had to happen, in order, on a non-portable ComfyUI 0.34.1 running from a conda env.

## 0. Check the version you already have

```bash
cat custom_nodes/comfyui-splatkit/pyproject.toml | head -3
```

If it says **1.1.4 or lower**, you have the panorama→COLMAP release and *none* of the 4D nodes.
The giveaway is that `core/splatting/` and `core/four_d_anyone/` do not exist.

The 4D node classes to look for:

```
SplatKit_4DAnyoneGenerateViews
SplatKit_4DAnyoneExportFrameset
SplatKit_4DAnyoneModelLoader
SplatKit_4DAnyonePreviewGrid
SplatKit_PerceptualModelLoader
SplatKit_TrainSequence
SplatKit_SequencePlayer
SplatKit_SplatBackendSetup
```

Note they are built as `NODE_PREFIX + "..."` from `core/splatting/constants.py`, so grepping for
the literal string `"SplatKit_TrainSequence"` in `nodes/` finds nothing. That is not evidence the
node is missing.

## 1. Upgrade the pack to 1.2.2

ComfyUI must be **closed** — it holds a lock on the `custom_nodes/comfyui-splatkit` folder and
the move will fail with "process cannot access the file" while it runs.

```bash
git clone --depth 1 --branch 1.2.2 https://github.com/mickmumpitz/ComfyUI-SplatKit.git
```

The pack ships a `.tracking` file listing every file it owns, which makes it easy to confirm you
have no local modifications before replacing it:

```bash
python scripts/check_pack_modifications.py   # prints "Untracked/user files: 0" on a clean pack
```

## 2. Host Python requirements

```bash
python -m pip install -r custom_nodes/comfyui-splatkit/requirements.txt
```

These are unpinned and light — `opencv-python`, `trimesh`, `scikit-image`, `click`,
`matplotlib`, `huggingface_hub[hf_xet]`. **No torch pins**, so this is safe to run in an env
shared with other custom nodes. On this machine everything was already satisfied and pip
installed nothing.

## 3. Build the isolated backend

Drop `installer.bat` + `install_splat_backend.py` (from the `4d-backend-installer-0.1.0`
release) into the pack folder. You can skip the `.bat` and call the script directly, which
avoids its interpreter guessing and its `pause`:

```bash
python install_splat_backend.py --pack-root "C:\Users\HP\Apps\ComfyUI\custom_nodes\comfyui-splatkit"
```

Any Python 3.9+ works as the bootstrap — it only reads `core/splatting/runtime.py` and then
builds its own environment with `uv`. It explicitly strips `CONDA_PREFIX`, `VIRTUAL_ENV`,
`PYTHONHOME` and `PYTHONPATH` from the child environment, so running it from a conda env is fine.

What it builds, under `bin/splat_backend/`:

| | |
|---|---|
| Python | 3.11 (downloaded by uv) |
| torch / torchvision | 2.8.0 / 0.23.0, cu128 |
| gsplat | 1.4.0 (SHA-256 pinned prebuilt wheel) |
| Size | 7.7 GB |

It downloads ~7.5 GB, needs 20 GB free, and cleans its ~7.6 GB uv cache on success.

**Verify it passed:**

```
[SplatKit 4D setup] Verifying backend.
CUDA rasterization and backward passed on NVIDIA GeForce RTX 5060 Ti
No broken requirements found.
[SplatKit 4D setup] Ready.
```

That smoke test does a real rasterization *and backward pass* on the GPU, so it proves the
prebuilt gsplat kernels cover your architecture. On Blackwell sm_120 they do.

Full log: [../logs/backend_install.log](../logs/backend_install.log)

### Do not use the one-click installer here

`installer-1.0.0` / `install_splatkit.bat` clones `feature/one-click-install` into a **second**
`ComfyUI-SplatKit` folder alongside your existing one. Use the backend-installer bundle against
the pack you already have.

## 4. Models — about 18 GB

| Destination | Files | Source |
|---|---|---|
| `models/splatkit/4danyone/` | `model.safetensors` (12.3 GB), `Wan2.2_VAE.pth` (2.8 GB), `prompt_context.safetensors`, `Wan22_TI2V_5B_Turbo_lora_rank_64_fp16.safetensors` | `AntResearch/4DAnyone` @ `4c80e87b805a5f8461cf339cdbe2fb4249e585aa` |
| `models/splatkit/4danyone/` | `imagenet-vgg-verydeep-19-conv.safetensors` | same repo @ `7850985888b56aabf09e69480b73248f1a76bcbe`, path `perceptual/` |
| `models/splatkit/birefnet/` | `model.safetensors`, `config.json`, `birefnet.py`, `BiRefNet_config.py` | `ZhengPeng7/BiRefNet` @ `e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4` |
| `models/detection/` | `sam_3d_body_dinov3_bf16.safetensors` (2.8 GB) | `Comfy-Org/sam-3d-body` |

All three repos are public and ungated — no HF login needed.

### `hf download --include` will silently skip files

With `huggingface_hub` 1.28, this:

```bash
hf download AntResearch/4DAnyone --include "a.safetensors" "b.pth" "c.safetensors"
```

consumes only the **first** pattern as `--include`, treats the rest as positional *filenames*,
then warns `Ignoring --include since filenames have been explicitly set` and downloads only the
positional ones. The first file is silently skipped.

This dropped both `model.safetensors` files — including the 12.3 GB main checkpoint — and was
only caught by checking sizes afterwards. **Pass files as positional arguments instead:**

```bash
hf download AntResearch/4DAnyone 4danyone/model.safetensors --revision <rev> --local-dir models/splatkit
```

Setting `--local-dir` to `models/splatkit` is convenient: repo paths already begin with
`4danyone/`, so files land in the right subfolder automatically.

## 5. Workflow

Copy the graph into `user/default/workflows/`. Its 4DAnyone Model Loader widget values already
match the filenames above, so the dropdowns resolve with no manual selection once the models
are in place.

## 6. Restart ComfyUI

Expect 41 registered SplatKit nodes. `SplatKit_SequencePlayer` requires `PromptServer.instance`,
so it only registers under a real ComfyUI run — it will appear missing in a headless import test.

## Notes

- Backend paths are **not** compatible with ComfyUI's `MODEL`/`VAE` sockets. 4DAnyone, the VAE,
  the LoRA, BiRefNet and VGG-19 all load inside the separate backend process. Only SAM 3D Body
  and the splat previews run in ComfyUI itself.
- Extra model roots can be configured in `extra_model_paths.yaml` under `splatkit_4danyone`,
  `splatkit_birefnet`, `splatkit_perceptual`, and the core `detection` key.
- `--rebuild` forces a full environment replacement and preserves the previous working one
  during the upgrade. Keep the installer scripts in the pack folder for this.
