import sys, numpy as np
BACK = r"C:\Users\HP\Apps\ComfyUI\custom_nodes\comfyui-splatkit\bin\splat_backend\4DAnyone"
sys.path.insert(0, BACK)

from fdanyone.video import load_canonical_working_clip
from fdanyone.skeleton.sam3d import load as load_sam, motion_from_sam, to_body_geometry
from fdanyone.foreground import predict_foreground_masks
from fdanyone.geometry.framing import (anatomy_samples, project_incam, _inside,
                                       _mask_support, _torso_valid)
from fdanyone.skeleton.keypoints import KEYPOINT_NAMES

R = (r"C:\Users\HP\Apps\ComfyUI\output\splatkit\4danyone\220ba479c4"
     r"\clip_cb7b69460ec5_e26092d28fa2_4876ecbae5c5_59fa45200c50"
     r"\pose\results\8135207-sd_540_960_25fps")
FG = r"C:\Users\HP\Apps\ComfyUI\models\splatkit\birefnet"

clip = load_canonical_working_clip(R + r"\canonical_clip.mp4", R + r"\canonical_clip.json")
npz = R + r"\sam3d_mhr70_cb7b69460ec5.npz"
data = np.load(npz)
print("npz keys:", list(data.keys()))
geometry = to_body_geometry(load_sam(npz, smooth_window=9))
motion = motion_from_sam(data, len(clip.frames))

print("\n--- BiRefNet masks ---")
masks = predict_foreground_masks(clip.rgb_frames, FG, "cuda")
masks = np.asarray(masks)
print("masks:", masks.shape, masks.dtype, "min", masks.min(), "max", masks.max())
cov = (masks >= 64).reshape(masks.shape[0], -1).mean(axis=1)
print("frames with ANY mask pixel >=64:", int((cov > 0).sum()), "/", masks.shape[0])
print("mean coverage: %.4f   max coverage: %.4f" % (cov.mean(), cov.max()))

print("\n--- torso / vitpose ---")
vit = motion.observed_keypoints_2d.detach().cpu().numpy()
print("observed_keypoints_2d:", vit.shape)
print("confidence: min %.3f  max %.3f  mean %.3f" % (vit[...,2].min(), vit[...,2].max(), vit[...,2].mean()))
h, w = masks.shape[1:]
tv = _torso_valid(vit, w, h)
print("torso_valid frames: %d / %d" % (int(tv.sum()), len(tv)))
sh_conf = vit[:, [5,6], 2]
print("shoulder conf mean L %.3f R %.3f" % (sh_conf[:,0].mean(), sh_conf[:,1].mean()))
print("x range %.1f..%.1f (w=%d)  y range %.1f..%.1f (h=%d)"
      % (vit[...,0].min(), vit[...,0].max(), w, vit[...,1].min(), vit[...,1].max(), h))

print("\n--- mask support ---")
K = motion.K_fullimg.detach().cpu().numpy()
anatomy, coords = anatomy_samples(geometry.keypoints_incam, KEYPOINT_NAMES)
axy, adep = project_incam(anatomy, K)
ins = _inside(axy, adep, w, h)
sup = _mask_support(axy, ins, masks)
print("frames with any INSIDE anatomy point:", int(ins.any(axis=1).sum()), "/", ins.shape[0])
print("frames with any SUPPORTED point:    ", int(sup.any(axis=1).sum()), "/", sup.shape[0])
print("anatomy proj x %.1f..%.1f  y %.1f..%.1f  depth %.3f..%.3f"
      % (axy[...,0].min(), axy[...,0].max(), axy[...,1].min(), axy[...,1].max(), adep.min(), adep.max()))
print("\nVALID FRAMES (support AND torso):", int((sup.any(axis=1) & tv).sum()))
