"""美式漫画风格的频道背景图（2026-10-17 起，与视频插图同风格）。

底图：Abo AI 生成，风格用 pipeline/image_style_comic.txt；文字：仿章节标题卡的撕边纸条 + 朱红印章 + 红笔底线。
规格：2560×1440；所有设备都能看到的安全区是正中间 1546×423，纸条和文字只放在这里。

用法:
    .venv/bin/python tools/banner_comic.py -o 频道素材/频道背景图_漫画.jpg [--bg 已有底图.png]
    .venv/bin/python tools/set_banner.py 频道素材/频道背景图_漫画.jpg
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import graphics2 as G2  # noqa: E402
import graphics3 as G3  # noqa: E402
from images_episode import generate  # noqa: E402

W, H = 2560, 1440
SAFE_W, SAFE_H = 1546, 423
STYLE = open(os.path.join(ROOT, "pipeline", "image_style_comic.txt"), encoding="utf-8").read().strip()
PROMPT = (
    "Ultra-wide panoramic establishing illustration at golden hour: the Taipei city skyline with Taipei 101 in the far "
    "distance, warm sunset clouds; on the far left foreground a large old banyan tree on a hill whose leaves catch the "
    "light like small gold coins; on the far right foreground a wooden desk on a balcony with a stack of old books, an "
    "open ledger notebook, a fountain pen, a coffee cup and a young plant growing in a terracotta pot; a few birds in "
    "the sky. No people. The middle band of the image is calm open sky and distant city, uncluttered, leaving space "
    "for a title. "
)
TITLE, TAG = "資產增長計劃", "讀懂金錢，讓資產穩穩長大"
SUB = "名人投資故事 · 金錢觀念 · 美股與指數"


def compose(bg_path, out_path):
    bg = Image.open(bg_path).convert("RGB")
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
    l, t = (bg.width - W) // 2, (bg.height - H) // 2
    img = bg.crop((l, t, l + W, t + H)).convert("RGBA")
    # 纸条后方略压暗，让纸条浮起来
    shade = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shade).rounded_rectangle([(W - SAFE_W) / 2, (H - SAFE_H) / 2, (W + SAFE_W) / 2, (H + SAFE_H) / 2], 120, fill=110)
    img.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), (10, 12, 20)).split(), shade.filter(ImageFilter.GaussianBlur(90)))))

    sw, sh = 1380, 340
    strip, pad = G3.paper_strip(sw, sh, seed=31)
    ink = Image.new("RGBA", strip.size, (0, 0, 0, 0))
    seal = G3.seal("資", 190)
    ink.alpha_composite(seal, (pad + 70, int(pad + sh / 2 - seal.height / 2)))
    x0 = pad + 330
    tl, tp = G2.text_layer(TITLE, 150, G3.INK, True, 12, False)
    ink.alpha_composite(tl, (x0 - tp, pad + 38 - tp))
    tw = tl.width - 2 * tp
    # 红笔底线（两遍、轻微起伏）
    cv = Image.new("RGBA", (ink.width * 2, ink.height * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(cv)
    rr = np.random.default_rng(5)
    xs = np.linspace(x0 - 8, x0 + tw + 14, 30)
    ys = pad + 228 - np.linspace(0, 8, 30) + rr.normal(0, 1.2, 30)
    d.line([(a * 2, b * 2) for a, b in zip(xs, ys)], fill=G3.RED + (235,), width=18, joint="curve")
    d.line([(a * 2, (b + 4) * 2) for a, b in zip(xs, ys + rr.normal(0, 1.4, 30))], fill=G3.RED + (110,), width=9, joint="curve")
    ink.alpha_composite(cv.resize(ink.size, Image.LANCZOS))
    gl, gp = G2.text_layer(TAG, 56, G3.RED, True, 4, False)
    ink.alpha_composite(gl, (x0 - gp, pad + 250 - gp))
    card = Image.new("RGBA", strip.size, (0, 0, 0, 0))
    card.alpha_composite(strip)
    card.alpha_composite(ink)
    card = card.rotate(-1.5, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(card, (int(W / 2 - card.width / 2), int(H / 2 - card.height / 2 - 20)))
    # 纸条两端的胶带
    tape = G3._tape().resize((230, 66))
    for cx, ang in ((W / 2 - sw / 2 + 40, 10), (W / 2 + sw / 2 - 40, -10)):
        tr = tape.rotate(ang, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(tr, (int(cx - tr.width / 2), int(H / 2 - sh / 2 - tr.height / 2 - 6)))
    # 副标：纸条下方、仍在安全区内
    sl, sp = G2.text_layer(SUB, 40, (246, 240, 226), False, 3, True)
    img.alpha_composite(sl, (int(W / 2 - (sl.width - 2 * sp) / 2 - sp), int(H / 2 + sh / 2 + 4 - sp)))
    img.convert("RGB").save(out_path, quality=92)
    print(out_path, f"{os.path.getsize(out_path) / 1e6:.2f} MB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--bg")
    a = ap.parse_args()
    bg = a.bg or os.path.splitext(a.out)[0] + "_底图.png"
    if not a.bg and not os.path.exists(bg):
        print(generate("banner", PROMPT + STYLE, bg, False))
    compose(bg, a.out)


if __name__ == "__main__":
    main()
