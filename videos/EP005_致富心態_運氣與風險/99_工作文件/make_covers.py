"""封面：真实照片（Commons，CC BY 2.0）放右侧，左侧深色渐层 + 程序叠字。在项目根目录运行。"""
import os
import sys

sys.path.insert(0, os.getcwd())
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

import cover  # noqa: E402
from config import FONT_BOLD  # noqa: E402

EP = "videos/EP005_致富心態_運氣與風險/"
OUT = EP + "05_封面/"
W, H = 1280, 720


def photo_right(path, focus_y=0.28, width=640):
    """照片按高度铺满右侧，左边缘羽化融进黑底；整体压暗一点、加点颗粒，和片中胶片调子一致。"""
    im = Image.open(path).convert("RGB")
    s = max(H / im.height * 1.15, width / im.width)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    top = int((im.height - H) * focus_y)
    left = max(0, (im.width - width) // 2)
    im = im.crop((left, top, left + width, top + H))
    bg = Image.new("RGB", (W, H), (8, 8, 10))
    mask = Image.new("L", (width, H), 255)
    feather = int(width * 0.2)  # 只羽化照片最左边 20%，脸在右侧，不被黑色盖住
    ramp = np.clip(np.arange(width) / feather, 0, 1) ** 1.6
    mask = Image.fromarray((np.tile(ramp, (H, 1)) * 255).astype(np.uint8))
    bg.paste(im, (W - width, 0), mask)
    arr = np.asarray(bg, np.float32)
    arr += np.random.default_rng(3).normal(0, 6, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def credit(img, text):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_BOLD, 18)
    w = f.getlength(text)
    d.text((24, H - 30), text, font=f, fill=(150, 150, 150))  # 黑底左下角，不压在人物上
    return img


def cutout_right(png, height=820, x_right=40, top=-10):
    """抠好的人物（rembg birefnet-portrait，本机运行）放在纯黑底右侧，和前几期封面一样是黑背景。"""
    im = Image.open(png).convert("RGBA")
    s = height / im.height
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    bg = Image.new("RGBA", (W, H), (8, 8, 10, 255))
    bg.alpha_composite(im, (W - im.width - x_right, top))
    arr = np.asarray(bg.convert("RGB"), np.float32)
    arr += np.random.default_rng(3).normal(0, 4, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# 2026-10-21 频道主：人物背景改成黑色，和之前的封面一致 → 先抠图（05_封面/gates_cutout.png）再放黑底
base = cutout_right(OUT + "gates_cutout.png", height=1000, x_right=60, top=10)  # 频道主选的版本：填满中间，头顶留约 28px 不被切
opts = {
    "封面_D_有錢人不願承認": (["有錢人", "最不願", "承認的事"], ["w", "y", "y"]),
}
for name, (lines, colors) in opts.items():
    img = cover.draw_text(base.copy(), lines, colors, "left", max_size=122)  # 与 EP003、EP004 一致：字号 122、左边距 56、三行时首行 y=138
    credit(img, "Photo: DFID · CC BY 2.0").save(OUT + name + ".jpg", quality=92)
print("ok")
