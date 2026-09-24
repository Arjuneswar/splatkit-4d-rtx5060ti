# ComfyUI-SplatKit 4D on a 16 GB RTX 5060 Ti — install, diagnosis and results

Field notes from installing [mickmumpitz/ComfyUI-SplatKit](https://github.com/mickmumpitz/ComfyUI-SplatKit)
1.2.2 (video → 4D Gaussian splat, via AntResearch **4DAnyone**) and running it end to end on a
**16 GB Blackwell RTX 5060 Ti** — a card with **8 GB less VRAM than the pipeline asks for**.

It completed. It took **20 h 55 m**. This documents why, plus two failure modes that cost real
time to diagnose and are not obvious from the logs.

**Headline finding:** the docs' "about 24 GB VRAM" is exact, not approximate. The backend
reported `peak_vram_allocated = 25,833,051,582 B = 24.06 GB`. On Windows this does **not** OOM —
WDDM silently pages the ~10 GB overflow to system RAM, so the run degrades to ~50× slower
instead of failing.

---

## Contents

| Doc | What's in it |
|---|---|
| [docs/INSTALL.md](docs/INSTALL.md) | What actually had to be done, including two things the docs get wrong |
| [docs/FRAMING-GATE.md](docs/FRAMING-GATE.md) | `ValueError: No valid frames for input framing analysis` — cause and fix |
| [docs/VRAM-PAGING.md](docs/VRAM-PAGING.md) | The 24 GB measurement, how to recognise paging, what to tune |
| [docs/RESULTS.md](docs/RESULTS.md) | Full stage timings + artifact analysis of the output |
| [docs/HPC-OFFLOAD.md](docs/HPC-OFFLOAD.md) | Running generation on a Linux cluster, training locally |
| [scripts/](scripts/) | Diagnostic scripts written during the debug |
| [logs/](logs/) | Raw logs from the full run |
| [images/](images/) | Frame comparisons referenced by the docs |

---

## Environment

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 5060 Ti, **16 GB**, Blackwell (sm_120) |
| Driver | 596.36 |
| System RAM | 63.8 GB |
| OS | Windows 11 Pro 26200 |
| ComfyUI | 0.34.1 at `C:\Users\HP\Apps\ComfyUI` (manual git install, **not** portable) |
| ComfyUI Python | conda env `comfyui`, Python 3.12.13, torch 2.10.0+cu128 |
| SplatKit backend | isolated venv, Python 3.11 / torch 2.8.0 / cu128 / gsplat 1.4.0 |

The backend is fully self-contained under the node's `bin/`. **Nothing was installed into
ComfyUI's own Python** — the host requirements were already satisfied, so an existing
Trellis2 install in the same env was untouched.

---

## Three things worth knowing before you start

### 1. Version matters more than anything else

SplatKit **≤ 1.1.4 is panorama→COLMAP only**. It contains *none* of the 4D nodes. If
`SplatKit_4DAnyoneGenerateViews` / `SplatKit_TrainSequence` don't exist, you have the wrong
version — the 4D code lives in `core/splatting/` and `core/four_d_anyone/`, added in **1.2.2**.

This cost the first hour: the pack was already installed, so it looked correct.

### 2. gsplat's prebuilt wheel *does* cover Blackwell

The installer's SHA-pinned `gsplat-1.4.0+pt28cu128-cp311-cp311-win_amd64.whl` compiles and runs
on sm_120. The installer's own CUDA smoke test passed:

```
CUDA rasterization and backward passed on NVIDIA GeForce RTX 5060 Ti
No broken requirements found.
```

### 3. Don't use the one-click installer if the pack is already installed

`installer-1.0.0` / `install_splatkit.bat` clones from a **feature branch** into a *second*
`ComfyUI-SplatKit` folder. Use the `4d-backend-installer-0.1.0` bundle against the pack you have.

---

## Two failure modes

### A. `No valid frames for input framing analysis`

Every stage succeeds — SAM 3D Body pose, BiRefNet masks — then the skeleton worker dies.

**Cause:** `analyze_input_framing` requires **both shoulders projected inside the frame** on at
least one frame. A head-and-shoulders close-up fails: the shoulders span the full frame width
and every joint below the neck projects outside.

Measured on the failing clip (540×960):

| Check | Result |
|---|---|
| BiRefNet masks | 121/121 frames, 67% coverage |
| Mask support | 121/121 frames |
| SAM 3D pose | 121 frames, 70 keypoints, conf 1.0 |
| **Torso valid** | **0/121** |

`l-shoulder x = 549.2` in a 540-wide frame — missing by 9 px on every frame.

**Fix:** footage where the subject is framed wider — shoulders at roughly 65–75% of frame width.
Full detail and the diagnostic script: [docs/FRAMING-GATE.md](docs/FRAMING-GATE.md).

### B. Silent VRAM paging

The tell is counter-intuitive: **100% GPU utilisation at ~49 W**.

| Signal | Reading | Meaning |
|---|---|---|
| Dedicated GPU memory | 14.24 GB | VRAM full |
| **Shared usage** | **9.93 GB** | spilled into system RAM |
| Power draw | 49 W (vs 144 W when healthy) | stalled on PCIe transfers |
| CPU time | 0.2 s per 45 s wall | blocked waiting |

Diagnose with:

```powershell
Get-Counter '\GPU Process Memory(*)\Shared Usage'
```

Large `Shared Usage` means paging, not compute. `nvidia-smi` alone will not tell you —
it reports 100% utilisation either way. Full detail: [docs/VRAM-PAGING.md](docs/VRAM-PAGING.md).

---

## Result: it completes

```
Prompt executed in 20:55:31
```

| Stage | Duration |
|---|---|
| Conditioning load (20 videos) | 6 m |
| Model load + source encode | 50 m |
| RCP denoise (4 steps) | 3 h 37 m |
| RCP decode + publish | 9 m |
| Reference load + encode | 3 h 26 m |
| **Target denoise** (4 steps × 4 groups) | **14 h 09 m** |
| Target decode + publish (16 cams) | 52 m |
| **Generate Views total** | **19 h 09 m** |
| Export Frameset | 6.5 m |
| Train Sequence (121 frames) | 95 m |
| **Total** | **20 h 55 m** |

**It never OOMed.** Process commit sat at exactly 52.59 GB for 13 hours with only 3.9 GB of
system commit headroom. Paging degrades here; it does not fail.

**Training is not the problem.** Train Sequence used **2.4 GB** of VRAM at 144 W and finished
121 frames in 95 minutes. Only Generate Views overcommits.

---

## Output quality

See [docs/RESULTS.md](docs/RESULTS.md) for the frame-by-frame analysis. Summary:

The artifacts are **in the generated views, not the training**. Comparing the splat render
against the generated views it trained on, at matched angles
([images/compare.png](images/compare.png)), the invented back and the patchy sides are already
present in the source views.

Root cause is the footage: a static, front-facing clip of a person in a **plain black top**,
at 540×960, who never turns. The model has no information about the back, so it invents one —
in this case a pink, streaky top and a long ponytail on a subject whose hair is in a bun.

No setting recovers a back the camera never saw.

---

## Reproducing the measurements

```bash
# which frames fail the framing gate, and why
python scripts/framing_diagnostic.py

# COCO-17 keypoints projected into the frame, with in/out-of-bounds flags
python scripts/keypoint_bounds.py

# render vs the generated views it trained on, at matched angles
python scripts/compare_render_vs_generated.py
```

These must run under the **backend** interpreter, which has the generator importable:

```
custom_nodes\comfyui-splatkit\bin\splat_backend\venv\Scripts\python.exe
```

---

## Credits

- [ComfyUI-SplatKit](https://github.com/mickmumpitz/ComfyUI-SplatKit) by mickmumpitz — MIT
- [4DAnyone](https://huggingface.co/AntResearch/4DAnyone) by AntResearch
- [BiRefNet](https://huggingface.co/ZhengPeng7/BiRefNet) by ZhengPeng7
- SAM 3D Body via [Comfy-Org/sam-3d-body](https://huggingface.co/Comfy-Org/sam-3d-body)

Test footage is a Pexels stock clip (`8066962`), included here only as extracted frames for
artifact analysis.
