# The 24 GB wall, and why it doesn't OOM

## The measurement

The backend prints its own peak at the end of Generate Views:

```
attention_backend:              sdpa
num_rcp_videos:                 4
num_target_videos:              16
fps:                            25/1
peak_vram_allocated_bytes:      25833051582     ->  24.06 GB
peak_vram_reserved_bytes:       29964107776     ->  27.90 GB
total_pipeline_elapsed_seconds: 68963.266       ->  19 h 09 m
```

The 4DAnyone docs say generation "has been reported to use about 24 GB VRAM". That is not a
rough figure — **24.06 GB allocated** at 16 views / 121 frames / turbo / sdpa.

On a 16 GB card that is an 8 GB shortfall, and everything below follows from it.

## Why it doesn't crash

Two mechanisms:

1. **NVIDIA CUDA sysmem fallback** (driver 596.36, on by default). VRAM overflow spills into
   system RAM instead of failing `cudaMalloc`.
2. **System-managed pagefile** backing the commit charge.

So the allocation succeeds, and the GPU spends its time moving memory across PCIe instead of
computing. It degrades; it does not fail.

## How to recognise it

The signature is counter-intuitive — `nvidia-smi` reports **100% utilisation**:

| Signal | Paging | Healthy |
|---|---|---|
| GPU utilisation | 100% | 88–100% |
| **Power draw** | **~49 W** | **144 W** |
| Temperature | 57 °C | 69 °C |
| Process CPU time | 0.2 s per 45 s wall | steadily accumulating |
| VRAM used | 15.5 / 16.3 GB | 2.4 GB |

**Power draw is the reliable tell.** A 5060 Ti doing real diffusion work pulls 150–180 W.
49 W at "100% utilisation" means the GPU is stalled on transfers.

`nvidia-smi` cannot distinguish these. The definitive check is the Windows perf counter:

```powershell
$c = Get-Counter '\GPU Process Memory(*)\Shared Usage','\GPU Process Memory(*)\Dedicated Usage'
$c.CounterSamples | Where-Object { $_.InstanceName -match '<PID>' -and $_.CookedValue -gt 0 } |
  ForEach-Object { "{0}: {1:N2} GB" -f (($_.Path -split '\\')[-1]), ($_.CookedValue/1GB) }
```

During this run:

```
dedicated usage: 14.24 GB     <- VRAM
shared usage:     9.93 GB     <- system RAM used as GPU memory
```

Any large **Shared Usage** means paging, not compute.

## What it costs

| Stage | Duration | Notes |
|---|---|---|
| Model load + source encode | 50 m | ~50× normal |
| RCP denoise, 4 steps | 3 h 37 m | 47 / 66 / 52 / 52 min per step |
| Reference load + encode | 3 h 26 m | **no log output at all** for 3.5 h |
| Target denoise, 4 steps | 14 h 09 m | 3:23 / 3:29 / 3:30 / 3:46 per step |
| Target decode + publish | 52 m | ~2:49 per camera |

Note the 3 h 26 m silence between "Publishing RCP camera 19" and the target stage starting.
Nothing is logged during `reference_encode`. It looks hung. It isn't.

## Memory was stable, not creeping

| | 20:18 | 23:35 | 10:55 next day |
|---|---|---|---|
| Dedicated | 14.24 GB | 15.42 GB | 14.95 GB |
| Shared | 9.93 GB | 10.41 GB | 10.88 GB |
| Process commit (PM) | 45.75 GB | **52.59 GB** | **52.59 GB** |
| Working set | 11.4 GB | 20.83 GB | 21.92 GB |
| System commit free | 16.0 GB | 3.9 GB | 3.9 GB |

Commit headroom collapsed from 16 GB → 3.9 GB during `reference_encode`, which looked alarming
at the time. But **process commit then held at exactly 52.59 GB for 13 hours** — the allocator
reached steady state and stayed there. That plateau, plus surviving the first two target steps,
is what made it reasonable to let the run finish rather than restart.

Interesting detail: the pagefile *shrank* under pressure (19.98 → 14.66 GB allocated, only
0.47 GB in use). The commit was backed by RAM, not by paging to disk.

## Structure of the work

Two progress bars, same shape, very different contents:

```python
# RCP: 4 timesteps, ONE denoise call each, conditioned on 1 source view
for step_index, _ in enumerate(tqdm(denoiser.scheduler.timesteps, desc=f"RCP 1-to-{len(camera_ids)}")):

# Target: 4 timesteps, (num_views / group_size) calls each, conditioned on 5 views
for step_index, groups in enumerate(tqdm(routes, desc=f"Generate {num_views} target views")):
    for view_indices in groups:
        denoise_group(...)
```

With 16 views and `views_per_group="auto"` → 4 (only 4 divides 16 from the valid set `(4, 6)`):

| | bar shows | denoise calls | conditioned on |
|---|---|---|---|
| RCP | 4 | **4** | 1 source view |
| Target | 4 | **16** | **5** views (source + 4 refs) |

Target is 4× the calls, each heavier — `target_sources = cat([source_latents, reference_latents])`.
That is why 14 h vs 3.5 h.

## Levers, in order of usefulness

| Lever | Effect |
|---|---|
| **`num_frames` 121 → 33** | Shrinks the latent stack directly. Must be 4k+1. The only lever that doesn't cost output quality. |
| `enable_rcp` off | Removes a stage and its memory, but the 16 target views then condition on the source alone — worse cross-view consistency, which is exactly what a splat trainer needs. |
| `low_vram` | Tiled VAE encode/decode (`FDANYONE_TILED_VAE=1`). Helps the VAE spike only — **not** the denoiser, which is what actually overflows. |
| `turbo` on | Keep it. 4 steps instead of 24. |

Important caveat on restarting: the result cache key **includes `num_frames`**. The run label is

```python
label = "r" + run_label_for(params)   # sha1(json.dumps(params, sort_keys=True))[:10]
```

and `params` contains `num_frames` whenever it differs from 121. So switching to 33 frames will
**not** reuse any previously computed RCP or target work — it's a clean restart.

## Rule of thumb for this card

**~19 h per Generate Views at 121 frames / 16 views.** Cut `num_frames` to shorten it.

Training is unaffected — 2.4 GB, 144 W, 95 min for 121 frames. Only Generate Views overcommits.
