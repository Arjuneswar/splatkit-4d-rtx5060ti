"""Render vs the generated views it trained on, at matched camera angles.

This is the test that separates "the splat trainer produced artifacts" from "the artifacts were
already in the generated views". If the bottom row shows the same pink back / patchy sides as
the top row, training reproduced them faithfully and the problem is upstream in generation.

The preview orbits at `orbit_speed` degrees per frame (default 3.0, see
core/splatting/training/cli.py), and generated cameras sit 360/views_per_ring apart. With 16
views that is 22.5 deg, so:

    preview frame 30 -> 90 deg  -> camera 4
    preview frame 60 -> 180 deg -> camera 8
    preview frame 90 -> 270 deg -> camera 12

The orbit may run the opposite way round from the camera numbering, so both the direct and the
mirrored mapping are rendered and you pick whichever lines up.

Run with the BACKEND interpreter, which has imageio available:
    bin/splat_backend/venv/Scripts/python.exe
"""

import numpy as np
import imageio.v2 as iio
from PIL import Image

# --- edit these three -------------------------------------------------------
PREVIEW = r"C:\Users\HP\Apps\ComfyUI\output\my_shot\preview.mp4"
DENSE = (r"C:\Users\HP\Apps\ComfyUI\output\splatkit\4danyone\220ba479c4"
         r"\clip_46caf6b86019_e26092d28fa2_4876ecbae5c5_59fa45200c50"
         r"\fdanyone\8066962-sd_540_960_25fps@r8e9a3c926f\videos\dense")
OUT = "compare.png"
# ----------------------------------------------------------------------------

VIEWS_PER_RING = 16
ORBIT_SPEED = 3.0
TILE = (352, 640)

# (preview frame, camera id) pairs at 90 / 180 / 270 degrees
PAIRS = [(30, 4), (60, 8), (90, 12)]


def generated(camera_id: int, frame: int) -> np.ndarray:
    return iio.get_reader(f"{DENSE}\\{camera_id:02d}.mp4").get_data(frame)


def row(images) -> np.ndarray:
    return np.concatenate(
        [np.asarray(Image.fromarray(im).resize(TILE)) for im in images], axis=1)


def main() -> None:
    preview = iio.get_reader(PREVIEW)
    rendered = [preview.get_data(f) for f, _ in PAIRS]
    direct = [generated(c, f) for f, c in PAIRS]
    mirrored = [generated((VIEWS_PER_RING - c) % VIEWS_PER_RING, f) for f, c in PAIRS]

    sheet = np.concatenate([row(rendered), row(direct), row(mirrored)], axis=0)
    Image.fromarray(sheet).save(OUT)

    angles = ", ".join(f"{f * ORBIT_SPEED:.0f}deg" for f, _ in PAIRS)
    print(f"wrote {OUT}")
    print(f"  row 1: splat render at {angles}")
    print(f"  row 2: generated cams {[c for _, c in PAIRS]}")
    print(f"  row 3: generated cams {[(VIEWS_PER_RING - c) % VIEWS_PER_RING for _, c in PAIRS]}"
          f"  (mirrored orbit direction)")


if __name__ == "__main__":
    main()
