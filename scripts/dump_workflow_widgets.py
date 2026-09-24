import json
d = json.load(open(r"C:\Users\HP\Apps\ComfyUI\user\default\workflows\Mickmumpitz_Video-to-4D-Splat_1-0.json", encoding='utf-8'))
for n in d['nodes']:
    t = n.get('type', '')
    if t in ('MarkdownNote', 'MickmumpitzLabel'):
        continue
    print(f"--- {t}  (id {n['id']}) ---")
    print("   widgets:", n.get('widgets_values'))
