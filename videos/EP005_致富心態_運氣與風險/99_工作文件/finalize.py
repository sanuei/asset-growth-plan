"""把章节和素材署名填进描述模板，输出 07_发布信息/描述.txt 和 credits.txt。只列片中真正用到的素材。"""
import json
import os

EP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
script = json.load(open(os.path.join(EP, "01_文案/script.json"), encoding="utf-8"))
used = {v.split("@")[0].split("#")[0] for s in script["sections"] for p in s["paragraphs"] for v in p["visuals"]}

lines = []
photos = json.load(open(os.path.join(EP, "03_画面素材/网络图片/sources.json"), encoding="utf-8"))
for k, s in photos.items():
    if k in used:
        who = (s.get("credit_name") or s.get("artist", "")).replace("Photograph:", "").strip()[:60]
        lines.append(f"・{who[:32]}（{s['license']}）{s['page'].replace('https://', '')}")
footage = json.load(open(os.path.join(EP, "03_画面素材/视频素材/footage.json"), encoding="utf-8"))
commons = json.load(open(os.path.join(EP, "03_画面素材/视频素材/raw/commons.json"), encoding="utf-8"))
seen = set()
for k, f in footage.items():
    if k not in used:
        continue
    for c in commons.values():
        if c["file"] == f["src"] and c["file"] not in seen:
            seen.add(c["file"])
            lines.append(f"・{c['artist'][:32]}（{c['license']}）{c['page'].replace('https://', '')}")
credits = "\n".join(lines)
open(os.path.join(EP, "07_发布信息/credits.txt"), "w", encoding="utf-8").write(credits + "\n")
chapters = open(os.path.join(EP, "07_发布信息/chapters.txt"), encoding="utf-8").read().strip()
tpl = open(os.path.join(EP, "07_发布信息/描述_模板.txt"), encoding="utf-8").read()
desc = tpl.replace("{CHAPTERS}", chapters).replace("{CREDITS}", credits)
assert len(desc) <= 4900, f"描述 {len(desc)} 字，超过 YouTube 的 5000 字上限"  # 2026-10-21 上传时因为超长被拒
open(os.path.join(EP, "07_发布信息/描述.txt"), "w", encoding="utf-8").write(desc)
print("描述字数", len(desc))
print(chapters)
print(credits)
