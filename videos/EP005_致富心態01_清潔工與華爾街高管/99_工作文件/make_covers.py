"""EP005 封面两版（用本集插图，不另外生图）。需在项目根目录运行。"""
import os
import sys

sys.path.insert(0, os.getcwd())
import cover  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

EP = "videos/EP005_致富心態01_清潔工與華爾街高管"
ILL = EP + "/03_画面素材/场景图/"
OUT = EP + "/05_封面/"
W, H = 1280, 720

# A：清洁工（右）+ 字（左）
bg = cover.fit_cover(Image.open(ILL + "ill_janitor.png"))
img = cover.darken_text_side(bg, "left")
cover.draw_text(img, ["清潔工", "留下800萬"], ["w", "y"], "left").save(OUT + "封面_A_清潔工800萬.jpg", quality=92)

# B：左右对比（清洁工 vs 豪宅），中间一道纸边，上方大字
left = cover.fit_cover(Image.open(ILL + "ill_read_town.png")).crop((320, 0, 960, 720))
right = cover.fit_cover(Image.open(ILL + "ill_mansion.png")).crop((320, 0, 960, 720))
b = Image.new("RGB", (W, H))
b.paste(left, (0, 0))
b.paste(right, (640, 0))
shade = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(shade)
for y in range(H):
    d.line([(0, y), (W, y)], fill=int(200 * max(0, 1 - y / 420)))
b = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), b, shade)
d = ImageDraw.Draw(b)
d.rectangle([636, 0, 644, H], fill=(244, 237, 221))
img = cover.draw_text(b, ["清潔工 vs 華爾街", "誰更有錢？"], ["w", "r"], "left")
img.save(OUT + "封面_B_清潔工vs華爾街.jpg", quality=92)
print("ok")
