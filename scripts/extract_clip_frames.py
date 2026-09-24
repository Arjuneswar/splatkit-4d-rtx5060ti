import sys
BACK = r"C:\Users\HP\Apps\ComfyUI\custom_nodes\comfyui-splatkit\bin\splat_backend\4DAnyone"
sys.path.insert(0, BACK)
from fdanyone.video import load_canonical_working_clip
from PIL import Image
import numpy as np
R = (r"C:\Users\HP\Apps\ComfyUI\output\splatkit\4danyone\220ba479c4"
     r"\clip_cb7b69460ec5_e26092d28fa2_4876ecbae5c5_59fa45200c50"
     r"\pose\results\8135207-sd_540_960_25fps")
clip = load_canonical_working_clip(R + r"\canonical_clip.mp4", R + r"\canonical_clip.json")
out = r"C:\Users\HP\AppData\Local\Temp\claude\C--Users-HP-Documents-Claude\a1e36c92-11cc-47d8-998a-ba155c9d371d\scratchpad"
strip = np.concatenate([clip.rgb_frames[i] for i in (0, 60, 120)], axis=1)
Image.fromarray(strip).save(out + r"\frames.png")
print("saved", strip.shape)
