"""黑底胶片风格的章节标题卡（2026-10-21 起，频道主要求取代纸条章节卡）。

效果：纯黑底 + 细纹理 → 小标题（如「第一部」）带两侧细线淡入 → 主标题逐字从模糊中浮现、轻微上浮
→ 金色细线从中间展开 → 整体缓慢推近。全程叠加胶片效果：颗粒、亮度闪烁、片门轻微晃动、
竖向刮痕、灰尘与毛发、暗角，开头有一下暖色漏光。

graphics.json 写法：
  {"type": "ftitle", "label": "第一部", "text": "百萬分之一的運氣", "sub": "（可选）副标题", "size": 118}
  text 可用 \\n 换行；label、sub 可省略。"seed" 可固定胶片瑕疵的随机序列。
接口与 graphics2 相同：DRAW["ftitle"](spec, t, dur) -> RGBA 画面（1920×1080）。
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import graphics2 as G2

W, H, FPS = G2.W, G2.H, G2.FPS
FONT_DIR = os.path.expanduser("~/Library/Fonts")
SERIF_HEAVY = os.path.join(FONT_DIR, "SourceHanSerifTC-Heavy.otf")
SERIF_BOLD = os.path.join(FONT_DIR, "SourceHanSerifTC-Bold.otf")
SERIF_LIGHT = os.path.join(FONT_DIR, "SourceHanSerifTC-Light.otf")
INK = (238, 230, 214)        # 微暖的米白
GOLD = (201, 169, 110)
BG = (10, 9, 8)
BLUR_LEVELS = (14, 9, 5, 2.5, 0)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:  # 没装思源宋体时退回黑体
        return G2.font(size, heavy=True)


@lru_cache(maxsize=4)
def _texture(seed=7):
    """静态纹理：低频斑驳 + 细纤维，亮度很低，叠在黑底上像旧片头的底片。"""
    rng = np.random.default_rng(seed)
    low = rng.normal(0, 1, (H // 24, W // 24)).astype(np.float32)
    low = np.asarray(Image.fromarray(low).resize((W, H), Image.BICUBIC))
    mid = rng.normal(0, 1, (H // 6, W // 6)).astype(np.float32)
    mid = np.asarray(Image.fromarray(mid).resize((W, H), Image.BICUBIC))
    tex = 6.0 + 3.2 * low + 1.6 * mid
    # 细纤维：几十条随机短曲线
    fib = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(fib)
    for _ in range(90):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        pts = [(x, y)]
        ang = rng.uniform(0, math.pi * 2)
        for _ in range(int(rng.integers(3, 8))):
            ang += rng.normal(0, 0.5)
            x += math.cos(ang) * rng.uniform(6, 22)
            y += math.sin(ang) * rng.uniform(6, 22)
            pts.append((x, y))
        d.line(pts, fill=int(rng.integers(6, 16)), width=1)
    tex += np.asarray(fib.filter(ImageFilter.GaussianBlur(0.6)), np.float32)
    # 暗角
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    vign = np.clip(1.0 - 0.55 * r ** 2.2, 0.25, 1.0)
    # 字面斑驳：高频小斑点，让文字像印在旧底片上，不是电脑字
    sp = rng.normal(0, 1, (H // 3, W // 3)).astype(np.float32)
    sp = np.asarray(Image.fromarray(sp).resize((W, H), Image.BICUBIC))
    mottle = np.clip(0.9 + 0.1 * sp + 0.05 * low, 0.62, 1.0)
    return np.clip(tex, 0, 40), vign, mottle


def _glyph_layers(ch, fnt, color):
    """一个字的多个模糊版本（RGBA），逐字浮现时从最模糊过渡到清晰。"""
    pad = 40
    bbox = fnt.getbbox(ch)
    w, h = bbox[2] - bbox[0] + pad * 2, bbox[3] - bbox[1] + pad * 2
    base = Image.new("RGBA", (max(w, 1), max(h, 1)), color + (0,))
    ImageDraw.Draw(base).text((pad - bbox[0], pad - bbox[1]), ch, font=fnt, fill=color + (255,))
    out = []
    for b in BLUR_LEVELS:
        out.append(base.filter(ImageFilter.GaussianBlur(b)) if b else base)
    return out, pad, bbox


@lru_cache(maxsize=16)
def _layout(text, size, label, sub):
    fnt = _font(SERIF_HEAVY, size)
    lines = text.split("\n")
    line_h = int(size * 1.32)
    total_h = line_h * len(lines)
    y0 = int(H * 0.47 - total_h / 2)
    glyphs = []  # (layers, x, y, order)
    order = 0
    for li, line in enumerate(lines):
        adv = [fnt.getlength(c) for c in line]
        tracking = size * 0.06
        lw = sum(adv) + tracking * (len(line) - 1)
        x = W / 2 - lw / 2
        y = y0 + li * line_h
        for c, a in zip(line, adv):
            if c.strip():
                layers, pad, bbox = _glyph_layers(c, fnt, INK)
                glyphs.append((layers, x + bbox[0] - pad, y + bbox[1] - pad, order))
                order += 1
            x += a + tracking
    lab = None
    if label:
        lf = _font(SERIF_BOLD, 38)
        spaced = "　".join(label) if len(label) <= 4 else label
        tw = int(lf.getlength(spaced))
        lab_img = Image.new("RGBA", (tw + 20, 60), GOLD + (0,))
        ImageDraw.Draw(lab_img).text((10, 4), spaced, font=lf, fill=GOLD + (255,))
        lab = (lab_img, W / 2 - (tw + 20) / 2, y0 - 120)
    sb = None
    if sub:
        sf = _font(SERIF_LIGHT, 40)
        tw = int(sf.getlength(sub))
        sub_img = Image.new("RGBA", (tw + 20, 64), INK + (0,))
        ImageDraw.Draw(sub_img).text((10, 4), sub, font=sf, fill=(206, 198, 184, 255))
        sb = (sub_img, W / 2 - (tw + 20) / 2, y0 + total_h + 66)
    return glyphs, order, lab, sb, y0, total_h


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _film_frame(fi, seed):
    """第 fi 帧的胶片瑕疵：颗粒、闪烁、刮痕、灰尘（按帧号可重现）。"""
    rng = np.random.default_rng(seed * 100003 + fi)
    grain = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    grain = np.asarray(Image.fromarray(grain).resize((W, H), Image.BILINEAR))
    flicker = 1.0 + 0.045 * math.sin(fi * 1.7 + seed) + rng.normal(0, 0.02)
    marks = Image.new("L", (W, H), 0)
    dark = Image.new("L", (W, H), 0)
    dm, dd = ImageDraw.Draw(marks), ImageDraw.Draw(dark)
    # 竖向刮痕：按 12 帧一段换位置，段内缓慢漂移
    seg = np.random.default_rng(seed * 7919 + fi // 12)
    for _ in range(int(seg.integers(1, 4))):
        x = seg.uniform(80, W - 80) + (fi % 12) * seg.normal(0, 0.8)
        y0, y1 = seg.uniform(-100, H * 0.4), seg.uniform(H * 0.6, H + 100)
        if seg.random() < 0.7:
            dm.line([(x, y0), (x + seg.normal(0, 3), y1)], fill=int(seg.integers(40, 90)), width=1)
        else:
            dd.line([(x, y0), (x + seg.normal(0, 3), y1)], fill=int(seg.integers(60, 120)), width=2)
    # 灰尘：每帧随机几个亮点/暗点，偶尔一根毛发
    for _ in range(int(rng.integers(2, 9))):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.2, 4.5)
        (dm if rng.random() < 0.6 else dd).ellipse([x - r, y - r, x + r, y + r], fill=int(rng.integers(70, 170)))
    if rng.random() < 0.18:
        x, y = rng.uniform(100, W - 100), rng.uniform(100, H - 100)
        pts, ang = [(x, y)], rng.uniform(0, 6.28)
        for _ in range(6):
            ang += rng.normal(0, 0.6)
            x += math.cos(ang) * 14
            y += math.sin(ang) * 14
            pts.append((x, y))
        (dm if rng.random() < 0.5 else dd).line(pts, fill=int(rng.integers(90, 160)), width=2)
    weave = (rng.normal(0, 0.9), 1.4 * math.sin(fi * 0.21 + seed) + rng.normal(0, 0.5))
    return grain, flicker, np.asarray(marks.filter(ImageFilter.GaussianBlur(0.7)), np.float32), \
        np.asarray(dark.filter(ImageFilter.GaussianBlur(0.9)), np.float32), weave


def card_ftitle(spec, t, dur):
    seed = int(spec.get("seed", 11))
    fi = int(round(t * FPS))
    tex, vign, mottle = _texture()
    glyphs, n, lab, sb, y0, total_h = _layout(spec["text"], int(spec.get("size", 118)),
                                             spec.get("label", ""), spec.get("sub", ""))
    grain, flicker, marks, dark, weave = _film_frame(fi, seed)

    # 文字层（逐字浮现）
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    start, stagger, each = 0.35, min(0.085, 1.4 / max(1, n)), 0.75
    for layers, x, y, k in glyphs:
        p = _ease((t - start - k * stagger) / each)
        if p <= 0:
            continue
        lvl = min(len(layers) - 1, int(p * (len(layers) - 1) + 0.5))
        img = layers[lvl]
        if p < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda a, q=p: int(a * q)))
        layer.alpha_composite(img, (int(round(x)), int(round(y + 14 * (1 - p)))))
    if lab:
        img, x, y = lab
        p = _ease((t - 0.05) / 0.6)
        if p > 0:
            im = img.copy()
            im.putalpha(im.getchannel("A").point(lambda a, q=p: int(a * q)))
            layer.alpha_composite(im, (int(x), int(y + 10 * (1 - p))))
            d = ImageDraw.Draw(layer)
            half = 150 * p
            cy = y + 30
            d.line([(x - 30 - half, cy), (x - 30, cy)], fill=GOLD + (int(170 * p),), width=2)
            d.line([(x + img.width + 30, cy), (x + img.width + 30 + half, cy)], fill=GOLD + (int(170 * p),), width=2)
    # 金色细线从中间展开
    p_line = _ease((t - start - n * stagger - 0.1) / 0.7)
    if p_line > 0:
        d = ImageDraw.Draw(layer)
        half = 210 * p_line
        ly = y0 + total_h + 26
        d.line([(W / 2 - half, ly), (W / 2 + half, ly)], fill=GOLD + (int(200 * p_line),), width=3)
    if sb:
        img, x, y = sb
        p = _ease((t - start - n * stagger - 0.3) / 0.8)
        if p > 0:
            im = img.copy()
            im.putalpha(im.getchannel("A").point(lambda a, q=p: int(a * q)))
            layer.alpha_composite(im, (int(x), int(y)))

    # 整体缓慢推近 + 片门晃动
    z = 1.0 + 0.035 * (t / max(dur, 0.1))
    cx, cy = W / 2 + weave[0], H / 2 + weave[1]
    layer = layer.transform((W, H), Image.AFFINE, (1 / z, 0, cx - W / (2 * z), 0, 1 / z, cy - H / (2 * z)), Image.BICUBIC)
    txt = np.asarray(layer, np.float32)
    a = txt[..., 3:4] / 255.0 * mottle[..., None]

    base = (np.array(BG, np.float32) + tex[..., None]) * 1.0
    # 开头一下暖色漏光，0.6 秒内褪去
    leak = max(0.0, 1 - t / 0.6) ** 2
    if leak > 0:
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        xx = np.linspace(0, 1, W, dtype=np.float32)[None, :]
        glow = np.exp(-((xx - 0.12) ** 2 / 0.05 + (yy - 0.3) ** 2 / 0.2)) * 90 * leak
        base = base + glow[..., None] * np.array([1.0, 0.55, 0.25], np.float32)
    img = base * (1 - a) + txt[..., :3] * a
    img = img * flicker * vign[..., None]
    img += grain[..., None] * 7.5
    img += marks[..., None] * 0.9
    img -= dark[..., None] * 0.55
    # 收尾 0.25 秒淡出到黑，切到下一个画面时不突兀
    fade = min(1.0, max(0.0, (dur - t) / 0.25))
    img *= fade
    out = np.clip(img, 0, 255).astype(np.uint8)
    rgba = np.dstack([out, np.full((H, W), 255, np.uint8)])
    return Image.fromarray(rgba, "RGBA")


G2.DRAW["ftitle"] = card_ftitle
