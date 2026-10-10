"""生成 YouTube 频道背景图（横幅）：gpt-image-2 生成底图，程序叠加繁体文字。

规格：2560×1440，≤6MB。所有设备都能看到的安全区是正中间 1546×423，文字只放在这里。

用法:
    .venv/bin/python tools/banner.py -o 频道素材/频道背景图.jpg [--bg 已有底图.png]
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ENV, FONT_BOLD, FONT_HEAVY  # noqa: E402

W, H = 2560, 1440
SAFE_W, SAFE_H = 1546, 423
GOLD = (232, 190, 92)
STYLE = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline", "image_style.txt"),
             encoding="utf-8").read().strip()
PROMPT = (
    "Ultra-wide establishing shot at golden hour: a quiet apartment balcony overlooking a softly lit city skyline, "
    "a small young plant growing in a terracotta pot on the railing in the foreground on the left, an open book and "
    "a cup of coffee on a small wooden table on the right, warm sunrise light. No people. The center of the frame is "
    "calm, uncluttered sky and distant city, slightly darker, leaving space for a title. "
)


def generate(out_path):
    body = {"model": ENV.get("COVER_IMAGE_MODEL", "gpt-image-2"), "prompt": PROMPT + STYLE, "n": 1,
            "size": "1536x1024", "quality": "high"}
    req = urllib.request.Request(
        ENV["ABOAI_BASE_URL"].rstrip("/") + "/images/generations", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {ENV['ABOAI_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=400) as r:
        item = json.load(r)["data"][0]
    data = base64.b64decode(item["b64_json"]) if item.get("b64_json") else urllib.request.urlopen(item["url"]).read()
    open(out_path, "wb").write(data)


def text(draw, xy, s, size, fill, heavy=True, spacing=0):
    f = ImageFont.truetype(FONT_HEAVY if heavy else FONT_BOLD, size)
    w = draw.textlength(s, font=f) + spacing * (len(s) - 1)
    x = xy[0] - w / 2
    for ch in s:
        draw.text((x, xy[1]), ch, font=f, fill=fill, anchor="lm")
        x += draw.textlength(ch, font=f) + spacing


def compose(bg_path, out_path):
    bg = Image.open(bg_path).convert("RGB")
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
    l, t = (bg.width - W) // 2, (bg.height - H) // 2
    img = bg.crop((l, t, l + W, t + H))
    # 安全区后方压暗，保证字清楚
    shade = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shade).rounded_rectangle([(W - SAFE_W) / 2 - 120, (H - SAFE_H) / 2 - 60,
                                            (W + SAFE_W) / 2 + 120, (H + SAFE_H) / 2 + 60], 200, fill=150)
    shade = shade.filter(ImageFilter.GaussianBlur(120))
    img = Image.composite(Image.new("RGB", (W, H), (8, 12, 22)), img, shade)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cy = H / 2
    text(d, (W / 2, cy - 70), "資產增長計劃", 150, (255, 255, 255, 255), spacing=10)
    d.rectangle([W / 2 - 300, cy + 34, W / 2 + 300, cy + 39], fill=GOLD + (255,))
    text(d, (W / 2, cy + 100), "讀懂金錢，讓資產穩穩長大", 64, GOLD + (255,), spacing=4)
    text(d, (W / 2, cy + 175), "好書精讀 · 投資觀念 · 美股與指數", 40, (225, 225, 225, 235), heavy=False, spacing=3)
    sh = layer.split()[3].filter(ImageFilter.GaussianBlur(8))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(sh.point(lambda v: int(v * 0.6)))
    img = img.convert("RGBA")
    img.alpha_composite(shadow, (4, 4))
    img.alpha_composite(layer)
    img.convert("RGB").save(out_path, quality=92)
    print(out_path, f"{os.path.getsize(out_path) / 1e6:.2f} MB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--bg")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    bg = a.bg or os.path.splitext(a.out)[0] + "_底图.png"
    if not a.bg:
        generate(bg)
    compose(bg, a.out)


if __name__ == "__main__":
    main()
