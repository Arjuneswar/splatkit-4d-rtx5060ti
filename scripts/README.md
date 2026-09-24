# Diagnostic scripts

Written while debugging the run. **Paths are hardcoded** to this machine's install — edit the
constants at the top of each file before using them elsewhere.

## Which interpreter

Most of these import `fdanyone` (the generator) or decode video, so they need the **backend**
interpreter, not ComfyUI's:

```
C:\Users\HP\Apps\ComfyUI\custom_nodes\comfyui-splatkit\bin\splat_backend\venv\Scripts\python.exe
```

`check_pack_modifications.py`, `dump_workflow_widgets.py` and `node_import_check.py` are the
exceptions — plain Python / ComfyUI's Python.

| Script | Interpreter | What it does |
|---|---|---|
| `framing_diagnostic.py` | backend | Re-runs `analyze_input_framing` against a finished pose dir and reports which of its two conditions fails — mask support vs torso validity. This is what identified the framing gate. |
| `keypoint_bounds.py` | backend | Projects COCO-17 keypoints with the run's own intrinsics and prints per-joint in/out-of-frame flags, plus the in-frame fraction across all frames. |
| `inspect_pose_npz.py` | backend | Dumps the SAM 3D Body npz — array shapes, `image_size`, intrinsics, keypoint depth ranges. Useful for confirming intrinsics match the clip. |
| `compare_render_vs_generated.py` | backend | Renders the splat preview beside the generated views at matched angles. The test that proves whether artifacts came from generation or from training. |
| `extract_clip_frames.py` | backend | Pulls representative frames out of a canonical clip into a contact strip. |
| `check_pack_modifications.py` | any | Diffs the installed pack against its shipped `.tracking` manifest. Prints `Untracked/user files: 0` on a clean pack — run before replacing a pack to be sure nothing local is lost. |
| `dump_workflow_widgets.py` | any | Prints every node's `widgets_values` from a workflow JSON. How the run's settings were read back. Note this reads the **file**, not the live graph in the browser. |
| `node_import_check.py` | ComfyUI's | Headless import of the pack; lists registered node classes. `SplatKit_SequencePlayer` will show missing here because it needs `PromptServer.instance` — that is expected outside a real ComfyUI run. |

## `vendor/`

`install_splat_backend.py` and `installer.bat` from the upstream
`4d-backend-installer-0.1.0` release, kept for reproducibility. Run the `.py` directly with
`--pack-root <pack>` to skip the batch file's interpreter guessing and its `pause`.

## Gotchas worth knowing

- `predict_foreground_masks` is in `fdanyone.foreground`, **not** `fdanyone.skeleton.foreground`.
- It wants the BiRefNet **directory**. Passing `model.safetensors` makes `transformers` treat
  the path as a repo id and raise `HFValidationError`.
- `KEYPOINT_NAMES` is in `fdanyone.skeleton.keypoints`.
- The pack's modules use relative imports (`from ...core...`), and the folder name contains a
  hyphen, so it can't be imported by name. `node_import_check.py` shows the
  `importlib.util.spec_from_file_location` + `submodule_search_locations` pattern that works.
