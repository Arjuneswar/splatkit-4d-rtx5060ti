import sys, os
CUI = r"C:\Users\HP\Apps\ComfyUI"
sys.path.insert(0, CUI)
os.chdir(CUI)
sys.path.insert(0, os.path.join(CUI, "custom_nodes"))
import importlib
m = importlib.import_module("comfyui-splatkit".replace("-", "_")) if False else None
# ComfyUI loads packs by folder name; emulate with importlib machinery
import importlib.util
spec = importlib.util.spec_from_file_location(
    "splatkit_pack", os.path.join(CUI, "custom_nodes", "comfyui-splatkit", "__init__.py"),
    submodule_search_locations=[os.path.join(CUI, "custom_nodes", "comfyui-splatkit")])
mod = importlib.util.module_from_spec(spec)
sys.modules["splatkit_pack"] = mod
spec.loader.exec_module(mod)
keys = sorted(mod.NODE_CLASS_MAPPINGS)
print(f"\nRegistered {len(keys)} SplatKit nodes")
need = ["SplatKit_4DAnyoneExportFrameset","SplatKit_4DAnyoneGenerateViews",
        "SplatKit_4DAnyoneModelLoader","SplatKit_4DAnyonePreviewGrid",
        "SplatKit_PerceptualModelLoader","SplatKit_SequencePlayer","SplatKit_TrainSequence",
        "SplatKit_SplatBackendSetup"]
for k in need:
    print(("  OK   " if k in mod.NODE_CLASS_MAPPINGS else "  MISS ") + k)
