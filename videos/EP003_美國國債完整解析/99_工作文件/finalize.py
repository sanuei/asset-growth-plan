"""用章节和图片授权信息，把描述模板填成 07_发布信息/描述.txt 和 credits.txt。"""
import json
import os

EP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = json.load(open(os.path.join(EP, "03_画面素材/网络图片/sources.json"), encoding="utf-8"))
used = ["web_treasury", "web_jackson", "web_wallst", "web_taipei", "web_fed", "web_capitol"]
credits = "\n".join(f"・{src[k]['artist'].replace('Photograph:', '').strip()}，{src[k]['license']}：{src[k]['page']}" for k in used if k in src)
open(os.path.join(EP, "07_发布信息/credits.txt"), "w", encoding="utf-8").write(credits + "\n")
chapters = open(os.path.join(EP, "07_发布信息/chapters.txt"), encoding="utf-8").read().strip()
tpl = open(os.path.join(EP, "07_发布信息/描述_模板.txt"), encoding="utf-8").read()
open(os.path.join(EP, "07_发布信息/描述.txt"), "w", encoding="utf-8").write(tpl.replace("{CHAPTERS}", chapters).replace("{CREDITS}", credits))
print(chapters)
print(credits)
