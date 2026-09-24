# Logs

| File | Contents |
|---|---|
| `comfyui_full_run.log` | Every SplatKit line from the whole session — the two framing-gate failures, then the full 20 h 55 m successful run. |
| `backend_install.log` | Backend build: uv venv, torch/gsplat install, the CUDA smoke test passing on the 5060 Ti, `pip check`, cache clean. |
| `dl_models.log` | First model download pass — the one where `hf download --include` silently skipped two files. |
| `dl_missing.log` | Re-fetch of the two skipped `model.safetensors` files as positional arguments. |
| `watch_final.log` | Target camera publishing plus the final metrics block with `peak_vram_allocated_bytes`. |
| `watch_train.log` | Tail of Train Sequence through frame 120 and `done: 121 frame(s) in 95.3 min`. |
