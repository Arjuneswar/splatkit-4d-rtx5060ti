from pathlib import Path
import os
os.chdir(r"C:\Users\HP\Apps\ComfyUI\custom_nodes\comfyui-splatkit")
tracked = set()
for l in open('.tracking', encoding='utf-8'):
    l = l.strip()
    if l:
        tracked.add(l.replace('/', os.sep))
extra = []
root = Path('.')
for p in root.rglob('*'):
    if p.is_dir():
        continue
    rel = str(p.relative_to(root))
    if '__pycache__' in rel or rel == '.tracking':
        continue
    if rel not in tracked:
        extra.append(rel)
print("Untracked/user files:", len(extra))
for e in extra[:50]:
    print("  ", e)
