"""第二版动态图表与文字卡（EP002 起使用）。

相对第一版的改进（对应 EP001 反馈「文字动画不够流畅、图表设计待提升」）：
- 元素先渲染成图层，每帧用双三次插值做亚像素位移与透明度变化，移动不再一像素一像素地跳。
- 缓动改为 easeOutQuint / easeInOutCubic，节奏更柔和；引语用左到右的柔边揭示。
- 背景可用该段场景图的模糊暗化版本并缓慢推近，与前后电影画面连贯；无场景图时用深蓝渐层 + 胶片颗粒。
- 所有内容保持在 y=860 以上（下方留给字幕）。

接口与第一版相同：render_clip(spec, dur, out_mp4, preview_png=None, frames=None)
spec["bg"] 可为图片路径（由 assemble 传入绝对路径）。
"""
import math
import os
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FONT_BOLD, FONT_HEAVY  # noqa: E402
from graphics import wrap  # noqa: E402  复用中文换行与避头规则

W, H, FPS = 1920, 1080, 30
SAFE_BOTTOM = 860
NAVY = (9, 16, 31)
GOLD = (236, 184, 40)
YELLOW = (255, 214, 0)
RED = (226, 64, 64)
WHITE = (246, 244, 238)
MUTED = (168, 176, 192)
LINE = (255, 255, 255, 46)
COLORS = {"w": WHITE, "y": YELLOW, "g": GOLD, "r": RED, "m": MUTED}


# ---------- 缓动 ----------

def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out(x):  # easeOutQuint
    x = clamp01(x)
    return 1 - (1 - x) ** 5


def ease_in_out(x):  # easeInOutCubic
    x = clamp01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def prog(t, start, length=0.9, fn=ease_out):
    return fn((t - start) / length) if length > 0 else float(t >= start)


@lru_cache(maxsize=64)
def font(size, heavy=True):
    return ImageFont.truetype(FONT_HEAVY if heavy else FONT_BOLD, size)


# ---------- 背景 ----------

@lru_cache(maxsize=8)
def _grain():
    rng = np.random.default_rng(3)
    n = rng.normal(0, 1, (H, W)).astype(np.float32)
    a = np.clip(np.abs(n) * 7, 0, 18).astype(np.uint8)
    g = np.full((H, W, 4), 255, np.uint8)
    g[..., 3] = a
    return Image.fromarray(g, "RGBA")


@lru_cache(maxsize=8)
def _bg_base(path):
    """返回比画面大 8% 的背景底图，供逐帧缓慢推近。"""
    BW, BH = int(W * 1.08), int(H * 1.08)
    if path and os.path.exists(path):
        im = Image.open(path).convert("RGB")
        s = max(BW / im.width, BH / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        im = im.crop(((im.width - BW) // 2, (im.height - BH) // 2, (im.width - BW) // 2 + BW, (im.height - BH) // 2 + BH))
        im = im.filter(ImageFilter.GaussianBlur(26))
        arr = np.asarray(im).astype(np.float32) * 0.34
        tint = np.array(NAVY, np.float32)
        arr = arr * 0.78 + tint * 0.22 * 2.2
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    else:
        y = np.linspace(0, 1, BH)[:, None]
        x = np.linspace(0, 1, BW)[None, :]
        glow = np.exp(-(((x - 0.5) / 0.45) ** 2 + ((y - 0.15) / 0.55) ** 2))
        base = np.stack([NAVY[i] + glow * (28, 34, 48)[i] for i in range(3)], -1)
        im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    # 暗角
    vx = np.linspace(-1, 1, BW)[None, :]
    vy = np.linspace(-1, 1, BH)[:, None]
    v = np.clip(1 - 0.42 * (vx ** 2 + vy ** 2), 0.45, 1)[..., None]
    arr = np.asarray(im).astype(np.float32) * v
    rng = np.random.default_rng(3)  # 胶片颗粒直接烘焙进底图，省去每帧再叠一层
    arr += rng.normal(0, 4.5, arr.shape[:2])[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def background(spec, t, dur):
    base = _bg_base(spec.get("bg"))
    z = 1.0 + 0.04 * ease_in_out(t / max(dur, 0.01))  # 整段缓慢推近 4%
    bw, bh = base.size
    cw, ch = bw / z / 1.08 * 1.0, bh / z / 1.08
    cx, cy = bw / 2, bh / 2
    sx, sy = cw / W, ch / H
    frame = base.transform((W, H), Image.AFFINE, (sx, 0, cx - cw / 2, 0, sy, cy - ch / 2), Image.BICUBIC)
    return frame.convert("RGBA")


# ---------- 图层 ----------

@lru_cache(maxsize=512)  # 同一段文字只排版一次（逐帧重复排版很慢）
def text_layer(text, size, color, heavy=True, spacing=0, shadow=True):
    f = font(size, heavy)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    if spacing:
        widths = [d.textlength(ch, font=f) for ch in text]
        tw = int(sum(widths) + spacing * (len(text) - 1)) + 8
    else:
        tw = int(d.textlength(text, font=f)) + 8
    asc, desc = f.getmetrics()
    th = asc + desc + 8
    pad = 24 if shadow else 4
    layer = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    if shadow:
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        _draw_text(sd, pad + 2, pad + 4, text, f, (0, 0, 0, 150), spacing)
        layer = Image.alpha_composite(layer, sh.filter(ImageFilter.GaussianBlur(8)))
        ld = ImageDraw.Draw(layer)
    _draw_text(ld, pad, pad, text, f, color + (255,) if len(color) == 3 else color, spacing)
    return layer, pad


def _draw_text(d, x, y, text, f, fill, spacing):
    if not spacing:
        d.text((x, y), text, font=f, fill=fill)
        return
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + spacing


def rich_layer(text, size, highlights, base=WHITE, hi=YELLOW):
    """同一行内把 highlights 里的词染成高亮色。"""
    return _rich_layer(text, size, tuple(highlights), base, hi)


@lru_cache(maxsize=256)
def _rich_layer(text, size, highlights, base, hi):
    f = font(size, True)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    segs, rest = [], text
    while rest:
        pos = [(rest.find(h), h) for h in highlights if rest.find(h) >= 0]
        if not pos:
            segs.append((rest, base))
            break
        p, h = min(pos)
        if p:
            segs.append((rest[:p], base))
        segs.append((h, hi))
        rest = rest[p + len(h):]
    tw = int(sum(d.textlength(s, font=f) for s, _ in segs)) + 8
    asc, desc = f.getmetrics()
    pad = 24
    layer = Image.new("RGBA", (tw + pad * 2, asc + desc + 8 + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sd, ld = ImageDraw.Draw(sh), None
    x = pad
    for s, c in segs:
        sd.text((x + 2, pad + 4), s, font=f, fill=(0, 0, 0, 150))
        x += d.textlength(s, font=f)
    layer = Image.alpha_composite(layer, sh.filter(ImageFilter.GaussianBlur(8)))
    ld = ImageDraw.Draw(layer)
    x = pad
    for s, c in segs:
        ld.text((x, pad), s, font=f, fill=c + (255,))
        x += d.textlength(s, font=f)
    return layer, pad


def place(frame, layer, x, y, alpha=1.0, dy=0.0, dx=0.0, wipe=None, scale=1.0):
    """把图层以亚像素精度、透明度、可选揭示遮罩合成到画面上。(x, y) 是图层内容左上角。"""
    if alpha <= 0.003:
        return
    lw, lh = layer.size
    fx, fy = x + dx, y + dy
    ix, iy = math.floor(fx), math.floor(fy)
    sx, sy = fx - ix, fy - iy
    if scale != 1.0:
        cx, cy = lw / 2, lh / 2
        a = 1 / scale
        layer = layer.transform((lw, lh), Image.AFFINE, (a, 0, cx - a * cx - sx, 0, a, cy - a * cy - sy), Image.BICUBIC)
    elif sx or sy:
        layer = layer.transform((lw, lh), Image.AFFINE, (1, 0, -sx, 0, 1, -sy), Image.BICUBIC)
    al = layer.getchannel("A")
    if wipe is not None:  # 左到右柔边揭示，wipe ∈ [0,1]
        soft = 140
        edge = wipe * (lw + soft) - soft
        ramp = np.clip((edge + soft - np.arange(lw)) / soft, 0, 1).astype(np.float32)
        m = Image.fromarray((np.tile(ramp, (lh, 1)) * 255).astype(np.uint8), "L")
        al = Image.fromarray((np.asarray(al, np.float32) * np.asarray(m, np.float32) / 255).astype(np.uint8), "L")
    if alpha < 0.999:
        al = al.point(lambda v: int(v * alpha))
    layer = layer.copy()
    layer.putalpha(al)
    frame.alpha_composite(layer, (ix, iy)) if 0 <= ix and 0 <= iy and ix + lw <= W and iy + lh <= H else _safe_composite(frame, layer, ix, iy)


def _safe_composite(frame, layer, ix, iy):
    x0, y0 = max(0, ix), max(0, iy)
    x1, y1 = min(W, ix + layer.width), min(H, iy + layer.height)
    if x1 <= x0 or y1 <= y0:
        return
    frame.alpha_composite(layer.crop((x0 - ix, y0 - iy, x1 - ix, y1 - iy)), (x0, y0))


def rise(frame, layer, pad, x, y, t, start, length=0.9, dist=26):
    p = prog(t, start, length)
    place(frame, layer, x - pad, y - pad, alpha=p, dy=(1 - p) * dist)


def footer(frame, spec, t):
    if spec.get("source"):
        lay, pad = text_layer(spec["source"], 24, MUTED, heavy=False, shadow=False)
        place(frame, lay, 96 - pad, 806 - pad, alpha=prog(t, 0.6, 1.0) * 0.85)


def fade_out(frame, t, dur, length=0.45):
    a = prog(t, dur - length, length, ease_in_out)
    if a > 0:
        ov = Image.new("RGBA", (W, H), NAVY + (int(255 * a * 0.0),))
        frame.alpha_composite(ov)


def centered_x(layer, pad):
    return (W - (layer.width - 2 * pad)) / 2


# ---------- 卡片 ----------

def card_title(spec, t, dur):
    fr = background(spec, t, dur)
    kicker, title = spec["text"].split("\n", 1)
    out = 1 - prog(t, dur - 0.55, 0.55, ease_in_out)
    k, kp = text_layer(kicker, 46, GOLD, spacing=10)
    place(fr, k, centered_x(k, kp) - kp, 352 - kp, alpha=prog(t, 0.1, 0.8) * out, dy=(1 - prog(t, 0.1)) * 18)
    line_w = 420
    ln = Image.new("RGBA", (line_w, 4), GOLD + (255,))
    place(fr, ln, (W - line_w) / 2, 440, alpha=out, wipe=prog(t, 0.35, 1.0, ease_in_out))
    tl, tp = text_layer(title, 104, WHITE)
    place(fr, tl, centered_x(tl, tp) - tp, 480 - tp, alpha=prog(t, 0.45, 1.0) * out, dy=(1 - prog(t, 0.45, 1.0)) * 30)
    return fr


def card_quote(spec, t, dur):
    fr = background(spec, t, dur)
    size = spec.get("size", 76)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = wrap(d, spec["quote"], font(size), 1460)
    lh = int(size * 1.5)
    block = lh * len(lines)
    top = max(150, (SAFE_BOTTOM - 120 - block) // 2 + 40)
    if spec.get("label"):
        lab, lp = text_layer(spec["label"], 32, GOLD, spacing=6, shadow=False)
        place(fr, lab, 230 - lp, top - 78 - lp, alpha=prog(t, 0.0, 0.8))
    bar = Image.new("RGBA", (8, block - (lh - size)), GOLD + (255,))
    place(fr, bar, 190, top + 10, alpha=prog(t, 0.1, 0.8))
    step = min(0.9, 2.4 / max(1, len(lines)))
    for i, line in enumerate(lines):
        lay, lp = rich_layer(line, size, spec.get("highlight", []))
        st = 0.3 + i * step
        place(fr, lay, 230 - lp, top + i * lh - lp, alpha=prog(t, st, 0.5), wipe=prog(t, st, 1.1, ease_in_out))
    if spec.get("author"):
        au, ap = text_layer("—— " + spec["author"], 40, GOLD, heavy=False)
        rise(fr, au, ap, 230, top + block + 30, t, 0.5 + len(lines) * step)
    footer(fr, spec, t)
    return fr


def card_statement(spec, t, dur):
    fr = background(spec, t, dur)
    items = spec["lines"]
    heights = [int(l.get("size", 110) * 1.42) for l in items]
    y = max(120, (SAFE_BOTTOM - sum(heights)) // 2 + 20)
    st = 0.2
    for l, h in zip(items, heights):
        lay, lp = text_layer(l["text"], l.get("size", 110), COLORS[l.get("color", "w")], heavy=l.get("heavy", True))
        rise(fr, lay, lp, centered_x(lay, lp), y, t, st, 1.0, 30)
        st += l.get("delay", 0.7)
        y += h
    footer(fr, spec, t)
    return fr


def card_bullets(spec, t, dur):
    fr = background(spec, t, dur)
    items = spec["items"]
    instant = spec.get("instant", 0)
    head_y = 150
    if spec.get("heading"):
        hd, hp = text_layer(spec["heading"], 62, GOLD)
        place(fr, hd, 260 - hp, head_y - hp, alpha=prog(t, 0, 0.8) if instant == 0 else 1.0)
    y0 = head_y + 130
    gap = min(150, (SAFE_BOTTOM - 40 - y0) // max(1, len(items)))
    step = (dur * 0.55) / max(1, len(items) - instant)
    for i, it in enumerate(items):
        num, text = it
        y = y0 + i * gap
        is_new = i >= instant
        st = 0.35 + (i - instant) * step
        a = prog(t, st, 0.8) if is_new else 1.0
        dy = (1 - prog(t, st, 0.8)) * 24 if is_new else 0
        badge = Image.new("RGBA", (84, 84), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.ellipse([2, 2, 82, 82], fill=GOLD + (255,))
        bd.text((42, 40), num, font=font(46), fill=NAVY + (255,), anchor="mm")
        hl = is_new and i == len(items) - 1
        place(fr, badge, 260, y, alpha=a, dy=dy)
        lay, lp = text_layer(text, 58, WHITE if (hl or not spec.get("dim_old")) else MUTED)
        place(fr, lay, 380 - lp, y + 6 - lp, alpha=a, dy=dy)
    footer(fr, spec, t)
    return fr


def card_timeline(spec, t, dur):
    fr = background(spec, t, dur)
    if spec.get("title"):
        tt, tp = text_layer(spec["title"], 56, GOLD)
        place(fr, tt, centered_x(tt, tp) - tp, 120 - tp, alpha=prog(t, 0, 0.8))
    events = spec["events"]
    x0, x1, yl = 230, 1690, 470
    p_line = prog(t, 0.3, dur * 0.5, ease_in_out)
    ln = Image.new("RGBA", (x1 - x0, 4), (255, 255, 255, 120))
    place(fr, ln, x0, yl - 2, wipe=p_line)
    n = len(events)
    for i, ev in enumerate(events):
        x = x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5)
        st = 0.3 + dur * 0.5 * (i / max(1, n - 1)) * 0.95
        a = prog(t, st, 0.7)
        color = COLORS[ev.get("color", "g")]
        dot = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        ImageDraw.Draw(dot).ellipse([4, 4, 36, 36], fill=color + (255,), outline=NAVY + (255,), width=4)
        place(fr, dot, x - 20, yl - 20, alpha=a, scale=0.6 + 0.4 * a)
        dl, dp = text_layer(ev["date"], 44, color)
        place(fr, dl, x - (dl.width - 2 * dp) / 2 - dp, yl - 118 - dp, alpha=a, dy=(1 - a) * 16)
        y = yl + 54
        for j, line in enumerate(ev["label"].split("\n")):
            lb, lpad = text_layer(line, 36, WHITE, heavy=j == 0)
            place(fr, lb, x - (lb.width - 2 * lpad) / 2 - lpad, y - lpad, alpha=a, dy=(1 - a) * 16)
            y += 52
    footer(fr, spec, t)
    return fr


def card_gap(spec, t, dur):
    """收入与期待两条曲线：期待永远跑在收入前面（示意）。"""
    fr = background(spec, t, dur)
    if spec.get("title"):
        tt, tp = text_layer(spec["title"], 54, GOLD)
        place(fr, tt, centered_x(tt, tp) - tp, 96 - tp, alpha=prog(t, 0, 0.8))
    L, R, T, B = 300, 1560, 230, 740
    xs = np.linspace(0, 1, 120)
    income = 0.10 + 0.42 * xs
    expect = 0.16 + 0.80 * xs ** 0.85
    p = prog(t, 0.4, dur * 0.55, ease_in_out)
    k = max(2, int(len(xs) * p))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for gy in range(4):
        y = B - (B - T) * gy / 3
        d.line([L, y, R, y], fill=LINE, width=2)
    d.line([L, B, R, B], fill=(255, 255, 255, 110), width=3)
    px = lambda v: L + (R - L) * v  # noqa: E731
    py = lambda v: B - (B - T) * v  # noqa: E731
    poly = [(px(x), py(e)) for x, e in zip(xs[:k], expect[:k])] + [(px(x), py(i)) for x, i in zip(xs[:k][::-1], income[:k][::-1])]
    if len(poly) > 3:
        d.polygon(poly, fill=GOLD + (46,))
    d.line([(px(x), py(v)) for x, v in zip(xs[:k], income[:k])], fill=WHITE + (255,), width=7, joint="curve")
    d.line([(px(x), py(v)) for x, v in zip(xs[:k], expect[:k])], fill=GOLD + (255,), width=7, joint="curve")
    for v, c in ((income[k - 1], WHITE), (expect[k - 1], GOLD)):
        cx, cy = px(xs[k - 1]), py(v)
        d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=c + (255,))
    fr.alpha_composite(layer)
    la = prog(t, 0.4 + dur * 0.55, 0.8)
    for txt, v, c in ((spec.get("label_expect", "期待"), expect[-1], GOLD), (spec.get("label_income", "收入"), income[-1], WHITE)):
        lay, lp = text_layer(txt, 40, c)
        place(fr, lay, R + 28 - lp, py(v) - 30 - lp, alpha=la)
    if spec.get("gap_label"):
        gl, gp = text_layer(spec["gap_label"], 44, YELLOW)
        mid = int(len(xs) * 0.72)
        place(fr, gl, px(xs[mid]) - (gl.width - 2 * gp) / 2 - gp, (py(expect[mid]) + py(income[mid])) / 2 - 30 - gp, alpha=la)
    xl, xp = text_layer(spec.get("x_label", "時間 →"), 32, MUTED, heavy=False, shadow=False)
    place(fr, xl, R - (xl.width - 2 * xp) - xp, B + 18 - xp, alpha=prog(t, 0.3, 0.8))
    footer(fr, spec, t)
    return fr


def card_ladder(spec, t, dur):
    fr = background(spec, t, dur)
    steps = spec["steps"]
    n = len(steps)
    x0, y0, sw, sh = 250, 780, 205, 88
    stp = (dur * 0.6) / n
    for i, s in enumerate(steps):
        st = 0.3 + i * stp
        a = prog(t, st, 0.7)
        x, y = x0 + i * sw, y0 - (i + 1) * sh
        last = i == n - 1
        blk = Image.new("RGBA", (sw - 12, (i + 1) * sh), (0, 0, 0, 0))
        bd = ImageDraw.Draw(blk)
        bd.rectangle([0, 0, sw - 12, (i + 1) * sh], fill=(GOLD + (230,)) if last else (255, 255, 255, 38 + i * 10))
        place(fr, blk, x, y, alpha=a, dy=(1 - a) * 40)
        lay, lp = text_layer(s, 38, NAVY if last else WHITE, shadow=not last)
        place(fr, lay, x + (sw - 12 - (lay.width - 2 * lp)) / 2 - lp, y + 18 - lp, alpha=a, dy=(1 - a) * 40)
    if spec.get("note"):
        nt, np_ = text_layer(spec["note"], 52, YELLOW)
        place(fr, nt, 250 - np_, 150 - np_, alpha=prog(t, 0.3 + n * stp, 0.9), dy=(1 - prog(t, 0.3 + n * stp)) * 20)
    footer(fr, spec, t)
    return fr


def card_flow(spec, t, dur):
    fr = background(spec, t, dur)
    if spec.get("title"):
        tt, tp = text_layer(spec["title"], 54, GOLD)
        place(fr, tt, centered_x(tt, tp) - tp, 130 - tp, alpha=prog(t, 0, 0.8))
    boxes = spec["boxes"]
    n = len(boxes)
    bw, bh, gap = 500, 260, 90
    total = n * bw + (n - 1) * gap
    x0, y0 = (W - total) / 2, 330
    stp = (dur * 0.55) / n
    for i, b in enumerate(boxes):
        st = 0.3 + i * stp
        a = prog(t, st, 0.8)
        x = x0 + i * (bw + gap)
        card = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        last = i == n - 1
        cd.rounded_rectangle([0, 0, bw - 1, bh - 1], 22, fill=(255, 255, 255, 26), outline=(RED if last else GOLD) + (255,), width=3)
        place(fr, card, x, y0, alpha=a, dy=(1 - a) * 30)
        yy = y0 + 46
        for j, line in enumerate(b.split("\n")):
            size = 48 if j == 0 else 31
            lay, lp = text_layer(line, size, (RED if last else WHITE) if j == 0 else MUTED, heavy=j == 0)
            place(fr, lay, x + (bw - (lay.width - 2 * lp)) / 2 - lp, yy - lp, alpha=a, dy=(1 - a) * 30)
            yy += size + 26
        if i < n - 1:
            arrow = Image.new("RGBA", (gap, 40), (0, 0, 0, 0))
            ad = ImageDraw.Draw(arrow)
            ad.line([12, 20, gap - 26, 20], fill=GOLD + (255,), width=5)
            ad.polygon([(gap - 30, 6), (gap - 8, 20), (gap - 30, 34)], fill=GOLD + (255,))
            place(fr, arrow, x + bw, y0 + bh / 2 - 20, alpha=prog(t, st + 0.5, 0.6), wipe=prog(t, st + 0.5, 0.6, ease_in_out))
    footer(fr, spec, t)
    return fr


def card_brand(spec, t, dur):
    fr = background(spec, t, dur)
    out = 1 - prog(t, dur - 0.6, 0.6, ease_in_out)
    tl, tp = text_layer(spec.get("text", "資產增長計劃"), 140, WHITE)
    place(fr, tl, centered_x(tl, tp) - tp, 360 - tp, alpha=prog(t, 0.2, 1.0) * out, scale=0.97 + 0.03 * prog(t, 0.2, 1.4))
    ln = Image.new("RGBA", (640, 4), GOLD + (255,))
    place(fr, ln, (W - 640) / 2, 560, alpha=out, wipe=prog(t, 0.5, 1.1, ease_in_out))
    if spec.get("sub"):
        sb, sp = text_layer(spec["sub"], 44, GOLD, heavy=False)
        place(fr, sb, centered_x(sb, sp) - sp, 600 - sp, alpha=prog(t, 0.9, 0.9) * out)
    return fr


def card_endcard(spec, t, dur):
    fr = background(spec, t, dur)
    tl, tp = text_layer("資產增長計劃", 130, WHITE)
    place(fr, tl, centered_x(tl, tp) - tp, 250 - tp, alpha=prog(t, 0.2, 1.0))
    ln = Image.new("RGBA", (640, 4), GOLD + (255,))
    place(fr, ln, (W - 640) / 2, 440, wipe=prog(t, 0.5, 1.0, ease_in_out))
    btn = Image.new("RGBA", (500, 112), (0, 0, 0, 0))
    bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle([0, 0, 499, 111], 56, fill=RED + (255,))
    bd.text((250, 54), "訂閱頻道", font=font(58), fill=WHITE + (255,), anchor="mm")
    a = prog(t, 0.9, 0.8)
    place(fr, btn, (W - 500) / 2, 500, alpha=a, scale=0.9 + 0.1 * a)
    if spec.get("next"):
        nx, npd = text_layer(spec["next"], 40, GOLD, heavy=False)
        place(fr, nx, centered_x(nx, npd) - npd, 668 - npd, alpha=prog(t, 1.4, 0.8))
    ds, dp = text_layer("本影片內容僅供教育參考，不構成任何投資建議。", 30, MUTED, heavy=False, shadow=False)
    place(fr, ds, centered_x(ds, dp) - dp, 760 - dp, alpha=prog(t, 1.6, 0.8))
    return fr


DRAW = {
    "title": card_title, "quote": card_quote, "statement": card_statement, "bullets": card_bullets,
    "timeline": card_timeline, "gap": card_gap, "ladder": card_ladder, "flow": card_flow,
    "brand": card_brand, "endcard": card_endcard,
}


def render_clip(spec, dur, out_mp4, preview_png=None, frames=None):
    fn = DRAW[spec["type"]]
    n = frames or max(1, round(dur * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
           "-pix_fmt", "yuv420p", out_mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        frame = fn(spec, i / FPS, n / FPS)
        proc.stdin.write(frame.tobytes())
        if preview_png and i == min(n - 1, int(n * 0.85)):
            frame.convert("RGB").save(preview_png)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg 编码失败: {out_mp4}")
