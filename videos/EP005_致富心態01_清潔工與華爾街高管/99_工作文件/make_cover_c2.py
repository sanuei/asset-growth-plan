import os, sys
sys.path.insert(0, os.getcwd())
import cover
from PIL import Image, ImageDraw, ImageFont
from config import FONT_BOLD
OUT = "videos/EP005_致富心態01_清潔工與華爾街高管/05_封面/"
bg = cover.fit_cover(Image.open(OUT + "封面_C_清潔工臉_bg.png"))
img = cover.darken_text_side(bg, "left")
img = cover.draw_text(img, ["理財靠的", "不是智商"], ["w", "y"], "left", max_size=210, width_frac=0.62)
d = ImageDraw.Draw(img); f = ImageFont.truetype(FONT_BOLD, 26); w = f.getlength("示意圖")
d.rounded_rectangle([1280 - w - 44, 642, 1264, 704], 8, fill=(0, 0, 0)); d.text((1280 - w - 30, 646), "示意圖", font=f, fill=(220, 220, 220))
img.save(OUT + "封面_C2_理財不是智商.jpg", quality=92)
