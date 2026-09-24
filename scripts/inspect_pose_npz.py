import numpy as np
R = (r"C:\Users\HP\Apps\ComfyUI\output\splatkit\4danyone\220ba479c4"
     r"\clip_cb7b69460ec5_e26092d28fa2_4876ecbae5c5_59fa45200c50"
     r"\pose\results\8135207-sd_540_960_25fps")
d = np.load(R + r"\sam3d_mhr70_cb7b69460ec5.npz")
for k in d:
    print(k, d[k].shape, d[k].dtype)
print("\nimage_size =", d["image_size"])
K = np.asarray(d["intrinsics"], dtype=np.float64)
print("intrinsics shape", K.shape)
print(K if K.ndim == 2 else K[0])
print("\ncam_t[0] =", d["cam_t"][0])
kp = d["keypoints_incam"]
print("keypoints_incam[0] z range: %.3f .. %.3f" % (kp[...,2].min(), kp[...,2].max()))
k2 = d["keypoints_2d"]
print("keypoints_2d shape", k2.shape, "x %.1f..%.1f  y %.1f..%.1f"
      % (k2[...,0].min(), k2[...,0].max(), k2[...,1].min(), k2[...,1].max()))
