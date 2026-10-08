"""生成 YouTube 封面：gpt-image-2 生成人物 + 背景，程序叠加繁体文字。

用法:
    .venv/bin/python cover.py -o 封面.jpg --prompt "Warren Buffett, smiling, wearing glasses and a suit" \
        --lines 巴菲特 給普通人的 投資建議 --colors w w y [--text-side left]
    .venv/bin/python cover.py -o 封面.jpg --bg 已有背景.png --lines ... --colors ...

颜色代码（每行一个）:
    w = 白字    y = 黄字    r = 红色色块衬白字
"""
import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import ENV, FONT_HEAVY

W, H = 1280, 720
YELLOW = (255, 214, 0)
RED = (225, 30, 40)
MARGIN = 56


def generate_background(prompt, text_side, out_path, retries=4):
    person_side = "right" if text_side == "left" else "left"
    full_prompt = (
        f"{prompt}. Photorealistic portrait for a YouTube thumbnail. "
        f"The person is placed on the {person_side} third of the frame, head and shoulders, "
        f"looking toward the camera. The {text_side} half of the frame is empty dark background "
        "reserved for text. Dark charcoal moody background, dramatic studio lighting, high contrast. "
        "Absolutely no text, letters, numbers, logos or watermarks."
    )
    body = {
        "model": ENV.get("COVER_IMAGE_MODEL", "gpt-image-2"),
        "prompt": full_prompt,
        "n": 1,
        "size": "1536x1024",
        "quality": "auto",  # 不传 quality 时 gpt-image-2 经常返回 500
    }
    req = urllib.request.Request(
        ENV["ABOAI_BASE_URL"].rstrip("/") + "/images/generations",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {ENV['ABOAI_API_KEY']}", "Content-Type": "application/json"},
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.load(r)
            item = resp["data"][0]
            if item.get("b64_json"):
                data = base64.b64decode(item["b64_json"])
            else:
                data = urllib.request.urlopen(item["url"], timeout=120).read()
            with open(out_path, "wb") as f:
                f.write(data)
            return out_path
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code >= 500 and attempt < retries:
                print(f"图片生成返回 {e.code}，重试 {attempt}/{retries - 1}")
                time.sleep(3 * attempt)
                continue
            sys.exit(f"图片生成失败 HTTP {e.code}: {detail}")


def fit_cover(img):
    """居中裁切并缩放到 1280x720。"""
    img = img.convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((left, top, left + W, top + H))


def darken_text_side(img, text_side):
    """文字一侧加渐变暗角，保证文字可读。"""
    grad = Image.new("L", (W, 1))
    for x in range(W):
        t = x / W if text_side == "right" else 1 - x / W
        grad.putpixel((x, 0), int(170 * max(0.0, t - 0.35) / 0.65))
    mask = grad.resize((W, H))
    return Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, mask)


def draw_text(img, lines, colors, text_side):
    max_w = int(W * 0.56) - MARGIN
    size = 150
    while size > 40:
        font = ImageFont.truetype(FONT_HEAVY, size)
        widths = [font.getbbox(line)[2] for line in lines]
        line_h = int(size * 1.22)
        if max(widths) + size * 0.4 <= max_w and line_h * len(lines) <= H - 2 * MARGIN:
            break
        size -= 4
    stroke = max(4, size // 14)
    pad = size // 7
    block_h = line_h * len(lines)
    y = (H - block_h) // 2

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    off = max(3, size // 25)

    for line, color, w in zip(lines, colors, widths):
        x = MARGIN if text_side == "left" else W - MARGIN - w - (2 * pad if color == "r" else 0)
        if color == "r":
            _, top, _, bottom = d.textbbox((x + pad, y), line, font=font)
            vpad = pad * 2 // 3
            box = (x, top - vpad, x + w + 2 * pad, bottom + vpad)
            sd.rectangle([box[0] + off, box[1] + off, box[2] + off, box[3] + off], fill=(0, 0, 0, 150))
            d.rectangle(box, fill=RED)
            d.text((x + pad, y), line, font=font, fill="white")
        else:
            fill = YELLOW if color == "y" else (255, 255, 255)
            sd.text((x + off, y + off), line, font=font, fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
            d.text((x, y), line, font=font, fill=fill, stroke_width=stroke, stroke_fill="black")
        y += line_h

    out = img.convert("RGBA")
    out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(off)))
    out.alpha_composite(layer)
    return out.convert("RGB")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-o", "--out", required=True)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt", help="人物描述（英文效果更好），会自动加构图要求")
    src.add_argument("--bg", help="已有的背景图")
    p.add_argument("--lines", nargs="+", required=True, help="2～3 行繁体文字")
    p.add_argument("--colors", nargs="+", required=True, choices=["w", "y", "r"])
    p.add_argument("--text-side", default="left", choices=["left", "right"])
    args = p.parse_args()

    if len(args.lines) != len(args.colors):
        sys.exit("--lines 和 --colors 数量必须一致")
    if not 2 <= len(args.lines) <= 3:
        print("提醒：准则要求封面 2～3 行文字")

    bg_path = args.bg
    if args.prompt:
        bg_path = args.out.rsplit(".", 1)[0] + "_bg.png"
        print("正在生成背景图…")
        generate_background(args.prompt, args.text_side, bg_path)
        print("背景图已保存:", bg_path)

    img = fit_cover(Image.open(bg_path))
    img = darken_text_side(img, args.text_side)
    img = draw_text(img, args.lines, args.colors, args.text_side)
    img.save(args.out, quality=92)
    print("封面已保存:", args.out)


if __name__ == "__main__":
    main()
