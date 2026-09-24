import sys, numpy as np
BACK = r"C:\Users\HP\Apps\ComfyUI\custom_nodes\comfyui-splatkit\bin\splat_backend\4DAnyone"
sys.path.insert(0, BACK)
from fdanyone.skeleton.sam3d import motion_from_sam, absolute_incam, project_coco17
R = (r"C:\Users\HP\Apps\ComfyUI\output\splatkit\4danyone\220ba479c4"
     r"\clip_cb7b69460ec5_e26092d28fa2_4876ecbae5c5_59fa45200c50"
     r"\pose\results\8135207-sd_540_960_25fps")
d = np.load(R + r"\sam3d_mhr70_cb7b69460ec5.npz")
abs_kp = absolute_incam(d)
print("absolute_incam z range: %.3f .. %.3f" % (abs_kp[...,2].min(), abs_kp[...,2].max()))
m = motion_from_sam(d, 121)
v = m.observed_keypoints_2d.numpy()
names = ("nose","l-eye","r-eye","l-ear","r-ear","l-shoulder","r-shoulder","l-elbow","r-elbow",
         "l-wrist","r-wrist","l-hip","r-hip","l-knee","r-knee","l-ankle","r-ankle")
W, H = 540, 960
print("\nframe 0 COCO17 projections (W=540 H=960):")
for i, n in enumerate(names):
    x, y = v[0, i, 0], v[0, i, 1]
    ok = (0 <= x < W) and (0 <= y < H)
    print(f"  {n:12s} x={x:8.1f} y={y:8.1f}  {'in ' if ok else 'OUT'}")
inb = (v[...,0] >= 0) & (v[...,0] < W) & (v[...,1] >= 0) & (v[...,1] < H)
print("\nper-joint in-frame fraction across 121 frames:")
for i, n in enumerate(names):
    print(f"  {n:12s} {inb[:, i].mean():.2f}")
