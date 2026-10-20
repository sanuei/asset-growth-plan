"""EP005 封面第二轮（频道主：要放真人脸，最好是有名的人）。需在项目根目录运行。
C：写实清洁工人脸（AI 生成，角落标「示意圖」，避免被当成里德本人）。
D：甘迺迪真实照片（公有领域，JFK 图书馆）+「出身，決定你怎麼看錢」。"""
import os
import sys

sys.path.insert(0, os.getcwd())
import cover  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from config import FONT_BOLD  # noqa: E402

EP = "videos/EP005_致富心態01_清潔工與華爾街高管"
OUT = EP + "/05_封面/"


def tag(img, text):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_BOLD, 26)
    w = f.getlength(text)
    d.rounded_rectangle([1280 - w - 44, 676 - 34, 1280 - 16, 704], 8, fill=(0, 0, 0))
    d.text((1280 - w - 30, 646), text, font=f, fill=(220, 220, 220))
    return img


# C：加「示意圖」
c = Image.open(OUT + "封面_C_清潔工臉.jpg").convert("RGB")
tag(c, "示意圖").save(OUT + "封面_C_清潔工臉.jpg", quality=92)

# D：甘迺迪照片放右侧，左侧暗底写字
ph = Image.open(EP + "/03_画面素材/网络图片/web_jfk.jpg").convert("RGB")
s = 760 / ph.height
ph = ph.resize((round(ph.width * s), 760), Image.LANCZOS)
bg = Image.new("RGB", (1280, 720), (10, 10, 12))
x0 = 1280 - ph.width + 10
m = np.clip(np.arange(ph.width) / 160, 0, 1)[None, :].repeat(ph.height, 0)
arr = (np.asarray(ph, np.float32) * m[..., None] + 10 * (1 - m[..., None])).astype(np.uint8)
bg.paste(Image.fromarray(arr).crop((0, 20, ph.width, 740)), (x0, 0))
img = cover.draw_text(bg, ["出身，", "決定你怎麼看錢"], ["w", "y"], "left")
tag(img, "John F. Kennedy · 公有領域").save(OUT + "封面_D_甘迺迪出身.jpg", quality=92)
print("ok")
