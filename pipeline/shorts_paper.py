"""纸张风格的独立 Shorts（1080×1920），《乔布斯传》系列起使用。

和 shorts.py 的差别（频道主 2026-10-17 看完第一章样片）：
- 与最新长视频同一套视觉语言：顶部纸条片名卡 + 朱红印章 + 逐字浮现的墨字 + 红笔底线；纸张信息卡；纸条片尾。
- 画面「按词切换」：shorts.json 的 beats 写明每个画面在念到哪个词时切入（约 2～2.5 秒一切），
  切换时轻微推近，和配音严格对齐；同一段话里穿插插图、真实照片、数字卡、时间线、文件、路线图。
- 弹出元素（pops）：标签纸条、朱红戳记，跟着关键词出现，配纸张声、盖章声（本地合成，不花钱）。
- 简体字形（Noto Sans CJK SC）。字幕里的数字和指定关键词用金色。

用法: .venv/bin/python pipeline/shorts_paper.py <章文件夹> C01A [C01B …] [--preview 秒] [--stills 1,5,9]
输入: <章文件夹>/08_Shorts/shorts.json（"template": "paper"），<章文件夹>/08_Shorts/<编号>/01_文案/script.json 与配音
输出: <章文件夹>/08_Shorts/<编号>/<编号>.mp4 和 .srt；--stills 只输出指定秒数的静帧到 99_工作文件/stills/
"""
import argparse
import json
import math
import os
import subprocess
import sys
import wave
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import assemble as A  # noqa: E402
import v2  # noqa: E402
from graphics3 import paper_strip, marker  # noqa: E402
from shorts import fix_numbers  # noqa: E402

W, H, FPS = 1080, 1920, 30
SS = 2                                   # 墨线超采样
FONT_H = os.path.expanduser("~/Library/Fonts/NotoSansCJKsc-Black.otf")
FONT_B = os.path.expanduser("~/Library/Fonts/NotoSansCJKsc-Bold.otf")
MAIN_Y, MAIN_H = 345, 1215               # 主画面：y 345～1560
CAP_Y, CAP_W, CAP_CHARS = 1452, 820, 12  # 字幕（避开 Shorts 右侧按钮与底部标题）
END_DUR = 2.8                            # 配音结束后片尾纸条停留
INK, FADE, RED, BLUE = (36, 31, 28), (116, 104, 90), (176, 44, 36), (28, 68, 126)
PAPER = (244, 237, 221)
GOLD, WHITE = (248, 204, 96), (255, 255, 255)
SEAL_RED = (186, 38, 32)
BOIL = [(-1.0, 0.5), (0.9, -0.7), (0.2, 0.9)]
COLORS = {"ink": INK, "fade": FADE, "red": RED, "blue": BLUE, "gold": GOLD, "white": WHITE}


def col(c):
    return COLORS.get(c, c) if isinstance(c, str) else tuple(c)


def clamp(x, a=0.0, b=1.0):
    return min(max(x, a), b)


def ease_out(x):
    return 1 - (1 - clamp(x)) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def prog(t, start, dur):
    return clamp((t - start) / max(dur, 1e-6))


# ---------- 文字 ----------

@lru_cache(maxsize=None)
def font(size, heavy=True):
    return ImageFont.truetype(FONT_H if heavy else FONT_B, int(size))


def tlen(s, size, heavy=True):
    return font(size, heavy).getlength(s)


def fit(s, size, max_w, heavy=True):
    while size > 24 and tlen(s, size, heavy) > max_w:
        size -= 2
    return size


@lru_cache(maxsize=2048)
def text_layer(s, size, fill, heavy=True, stroke=0, shadow=False):
    """回传 (RGBA 图层, 内边距)。文字基线在 pad + size*0.88。"""
    f = font(size, heavy)
    w = int(f.getlength(s)) + 2
    pad = stroke + (16 if shadow else 4)
    img = Image.new("RGBA", (w + 2 * pad, int(size * 1.32) + 2 * pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad + 3, pad + 5), s, font=f, fill=(0, 0, 0, 190), stroke_width=stroke, stroke_fill=(0, 0, 0, 190))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).text((pad, pad), s, font=f, fill=tuple(fill) + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    return img, pad


def put(canvas, layer, x, y, alpha=1.0):
    """把图层左上角放在 (x, y)，可带透明度。"""
    if alpha <= 0.004:
        return
    if alpha < 0.996:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(layer, (int(round(x)), int(round(y))))


def put_text(canvas, s, size, color, x, y, alpha=1.0, anchor="l", heavy=True, stroke=0, shadow=False):
    lay, pad = text_layer(s, size, col(color), heavy, stroke, shadow)
    w = lay.width - 2 * pad
    ax = {"l": x, "c": x - w / 2, "r": x - w}[anchor]
    put(canvas, lay, ax - pad, y - pad, alpha)
    return w


@lru_cache(maxsize=256)
def glow_text(s, size, color):
    lay, pad = text_layer(s, size, color, True)
    p2 = 30
    big = (lay.width + 2 * p2, lay.height + 2 * p2)
    a = Image.new("L", big, 0)
    a.paste(lay.getchannel("A"), (p2, p2))
    a = a.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.55))
    g = Image.merge("RGBA", (Image.new("L", big, 255), Image.new("L", big, 176), Image.new("L", big, 80), a))
    g.alpha_composite(lay, (p2, p2))
    return g, pad + p2


# ---------- 纸、印章、戳记、墨线 ----------

@lru_cache(maxsize=64)
def sheet(w, h, seed=11):
    lay, pad = paper_strip(int(w), int(h), seed)
    return lay, pad


@lru_cache(maxsize=32)
def seal(ch, size=120, seed=3):
    """朱红方印，中间反白一个字（简体字形）。"""
    r = np.random.default_rng(seed)
    big = size * 2
    im = Image.new("RGBA", (big + 40, big + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    for k in range(40):
        a = 2 * math.pi * k / 40
        c, s_ = math.cos(a), math.sin(a)
        rad = big / 2 / max(abs(c), abs(s_)) * (1 + r.normal(0, 0.012))
        pts.append((20 + big / 2 + c * rad * 0.94, 20 + big / 2 + s_ * rad * 0.94))
    d.polygon(pts, fill=SEAL_RED + (238,))
    f = font(int(big * 0.62 / max(1, len(ch)) ** 0.5), True)
    tw = f.getlength(ch)
    asc, desc = f.getmetrics()
    d.text((20 + (big - tw) / 2, 20 + (big - asc - desc) / 2 + big * 0.02), ch, font=f, fill=(0, 0, 0, 0))
    hole = Image.fromarray(((r.random((big + 40, big + 40)) > 0.93) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    a = np.asarray(im.getchannel("A"), np.float32) * (1 - np.asarray(hole, np.float32) / 255 * 0.55)
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im.resize((size + 20, size + 20), Image.LANCZOS)


@lru_cache(maxsize=32)
def stamp(text, size=110, seed=5):
    """红色长方形戳记（双边框 + 字），带盖印不均的斑驳。"""
    r = np.random.default_rng(seed)
    f = font(size, True)
    tw = f.getlength(text)
    w, h = int(tw + size * 0.9), int(size * 1.55)
    big = Image.new("RGBA", (w * 2 + 40, h * 2 + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    c = SEAL_RED + (235,)
    d.rounded_rectangle([20, 20, 20 + w * 2, 20 + h * 2], 18, outline=c, width=14)
    d.rounded_rectangle([44, 44, w * 2 - 4, h * 2 - 4], 10, outline=c, width=5)
    f2 = font(size * 2, True)
    asc, desc = f2.getmetrics()
    d.text((20 + w - tw, 20 + h - (asc + desc) / 2 + 6), text, font=f2, fill=c)
    hole = Image.fromarray(((r.random(big.size[::-1]) > 0.9) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))
    a = np.asarray(big.getchannel("A"), np.float32) * (1 - np.asarray(hole, np.float32) / 255 * 0.6)
    big.putalpha(Image.fromarray(a.astype(np.uint8)))
    return big.resize((w + 20, h + 20), Image.LANCZOS)


def wobble(pts, amp, seed):
    pts = np.asarray(pts, float)
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(np.hypot(*(b - a)) // 18))
        out += [a + (b - a) * k / n for k in range(1, n + 1)]
    pts = np.array(out)
    n = len(pts)
    m = max(2, n // 7 + 2)
    r = np.random.default_rng(seed)
    wx = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, m), r.normal(0, amp, m))
    wy = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, m), r.normal(0, amp, m))
    return pts + np.stack([wx, wy], 1)


class Ink:
    """超采样墨线画布（尺寸 w×h，最后缩小合成）。每条线有自己的抖动节奏（4～7 帧不等）。"""

    def __init__(self, w, h, frame):
        self.w, self.h, self.frame, self.k = w, h, frame, 0
        self.im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def seed(self):
        self.k += 1
        per = (4, 5, 6, 7)[self.k % 4]
        return [((self.frame + self.k * 13) // per) % 9973, self.k]

    def line(self, pts, color, width=5.0, amp=1.0, alpha=255, p=1.0):
        pts = np.asarray(pts, float)
        if p < 1:  # 只画前 p 比例（沿折线长度）
            seg = np.hypot(*np.diff(pts, axis=0).T)
            L = seg.sum() * clamp(p)
            out, acc = [pts[0]], 0.0
            for a, b, s in zip(pts[:-1], pts[1:], seg):
                if acc + s >= L:
                    out.append(a + (b - a) * ((L - acc) / max(s, 1e-6)))
                    break
                out.append(b)
                acc += s
            pts = np.array(out)
        if len(pts) < 2 or p <= 0.01:
            return
        color = col(color)
        xy = [(x * SS, y * SS) for x, y in wobble(pts, amp, self.seed())]
        self.d.line(xy, fill=color + (alpha,), width=max(1, int(width * SS)), joint="curve")
        xy2 = [(x * SS, y * SS) for x, y in wobble(pts, amp * 1.3, self.seed())]
        self.d.line(xy2, fill=color + (int(alpha * 0.42),), width=max(1, int(width * SS * 0.55)), joint="curve")

    def ellipse(self, cx, cy, rx, ry, color, width=6.0, p=1.0):
        a = np.linspace(-2.2, -2.2 + 2 * math.pi * 1.08, 48)
        rr = 1 + np.linspace(0, 0.07, 48)
        self.line(list(zip(cx + rx * rr * np.cos(a), cy + ry * rr * np.sin(a))), color, width, 1.4, p=p)

    def check(self, x, y, s, color, p=1.0):
        self.line([(x, y), (x + s * 0.35, y + s * 0.4), (x + s, y - s * 0.55)], color, 7, 0.9, p=p)

    def cross(self, x, y, s, color, p=1.0):
        self.line([(x, y - s / 2), (x + s, y + s / 2)], color, 7, 0.9, p=clamp(p * 2))
        self.line([(x + s, y - s / 2), (x, y + s / 2)], color, 7, 0.9, p=clamp(p * 2 - 1))

    def done(self):
        return self.im.reduce(SS)


# ---------- 素材 ----------

class Assets:
    def __init__(self, ep):
        self.ep = ep
        p = os.path.join(ep, "03_画面素材/网络图片/sources.json")
        self.sources = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

    @lru_cache(maxsize=64)
    def img(self, name):
        if name.startswith("web_"):
            path = os.path.join(self.ep, "03_画面素材/网络图片", name + ".jpg")
        else:
            path = os.path.join(self.ep, "03_画面素材/场景图", name + ".png")
        im = Image.open(path).convert("RGB")
        if max(im.size) > 2200:
            k = 2200 / max(im.size)
            im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        return im

    def credit(self, name):
        s = self.sources.get(name)
        if not s:
            return None
        artist = s.get("credit_name") or s["artist"].split(",")[0].replace("based on File:", "").strip()
        return f"照片：{artist} · {s['license']} · Wikimedia Commons"

    @lru_cache(maxsize=64)
    def backdrop(self, name):
        """整屏背景：同一张图放大、强模糊、压暗，加暗角。"""
        im = self.img(name)
        k = max(W / im.width, H / im.height)
        im = im.resize((math.ceil(im.width * k), math.ceil(im.height * k)), Image.BILINEAR)
        l, t = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(40))
        arr = np.asarray(im, np.float32) * 0.30 + np.array((14, 12, 11), np.float32) * 0.4
        yy = np.linspace(-1, 1, H)[:, None]
        xx = np.linspace(-1, 1, W)[None, :]
        arr *= np.clip(1 - 0.45 * (xx ** 2 * 0.6 + yy ** 2), 0.4, 1)[..., None]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


@lru_cache(maxsize=1)
def main_mask():
    """主画面的上下渐隐（上 70px、下 330px），让图片融进背景、字幕压在暗处。"""
    a = np.ones((MAIN_H, W), np.float32)
    top, bot = 70, 330
    a[:top] *= np.linspace(0, 1, top)[:, None] ** 1.2
    a[-bot:] *= np.linspace(1, 0, bot)[:, None] ** 1.6
    return Image.fromarray((a * 255).astype(np.uint8))


@lru_cache(maxsize=1)
def grains():
    r = np.random.default_rng(3)
    out = []
    for _ in range(3):
        n = r.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        g = Image.fromarray(np.clip(128 + n * 40, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
        lay = Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 14)))
        out.append(lay)
    return out


def view(img, cfg, t, dur):
    """Ken Burns：按主画面比例裁切，scale 放大取景（特写），zoom in/out 缓慢推拉，pan 水平移动。
    匀速推拉（每秒约 2.5%，频道主 10/17：缩放要流畅，不要忽快忽慢）；t、dur 是这张图整段连续出现的时间。"""
    p = clamp(t / max(dur, 0.1))
    rate = cfg.get("rate", 0.025)
    z = cfg.get("scale", 1.0) * (1 + rate * (t if cfg.get("zoom", "in") == "in" else max(dur, 0.1) - t))
    aspect = W / MAIN_H
    if img.width / img.height > aspect:
        ch = img.height
        cw = ch * aspect
    else:
        cw = img.width
        ch = cw / aspect
    cw, ch = cw / z, ch / z
    cx = (cfg.get("fx", 0.5) + cfg.get("pan", 0.0) * (p - 0.5)) * img.width
    cy = cfg.get("fy", 0.5) * img.height
    x0 = clamp(cx - cw / 2, 0, img.width - cw)
    y0 = clamp(cy - ch / 2, 0, img.height - ch)
    return img.transform((W, MAIN_H), Image.AFFINE, (cw / W, 0, x0, 0, ch / MAIN_H, y0), Image.BICUBIC).convert("RGBA")


# ---------- 纸张信息卡（画在主画面区域，W×MAIN_H 的透明图层） ----------

def place_sheet(layer, content, cx, cy, t, ang=-1.2, delay=0.0):
    """纸张带着轻微旋转落下（0.35 秒），再固定。content 是已画好内容的纸（含 pad）。"""
    a = ease_out(prog(t, delay, 0.32))
    if a <= 0:
        return
    rot = ang - 3.5 * (1 - a)
    im = content.rotate(rot, expand=True, resample=Image.BICUBIC)
    put(layer, im, cx - im.width / 2, cy - im.height / 2 - 60 * (1 - a), a)


def card_num(sp, t, dur, frame):
    big, sub = sp["big"], sp.get("sub", "")
    bsize = fit(big, sp.get("size", 220), 860)
    w = int(max(tlen(big, bsize) + 170, tlen(sub, 56) + 130, 760))
    h = int(bsize * 1.25 + (130 if sub else 40) + 64)
    base, pad = sheet(w, h, 31)
    c = base.copy()
    color = col(sp.get("color", "red"))
    g, gp = glow_text(big, bsize, color)
    k = (frame + sum(map(ord, big))) // 6
    jx, jy = (BOIL[k % 3][0] * 0.8, BOIL[(k + 1) % 3][1] * 0.8) if t > 0.9 else (0, 0)
    bw = tlen(big, bsize)
    a = ease_out(prog(t, 0.18, 0.35))
    put(c, g, pad + (w - bw) / 2 - gp + jx, pad + 34 - gp + jy + (1 - a) * 18, a)
    if sub:
        put_text(c, sub, 56, INK, pad + w / 2, pad + bsize * 1.25 + 46, ease_out(prog(t, 0.45, 0.4)), "c")
    if sp.get("circle", True):
        ink = Ink(c.width, c.height, frame)
        ink.ellipse(pad + w / 2, pad + 34 + bsize * 0.62, bw / 2 + 50, bsize * 0.62, RED, 6, p=ease_in_out(prog(t, 0.55, 0.55)))
        c.alpha_composite(ink.done())
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    place_sheet(lay, c, W / 2, sp.get("y", 430), t, sp.get("ang", -1.5))
    return lay


def card_note(sp, t, dur, frame):
    lines = sp["text"].split("\n")
    size = sp.get("size", 92)
    size = min(size, min(fit(l, size, 900) for l in lines))
    w = int(max(max(tlen(l, size) for l in lines) + 150, tlen(sp.get("kicker", ""), 46) + 150, 760))
    h = int((104 if sp.get("kicker") else 44) + len(lines) * size * 1.36 + 64)
    base, pad = sheet(w, h, 41)
    c = base.copy()
    y = pad + 36
    if sp.get("kicker"):
        put_text(c, sp["kicker"], 46, FADE, pad + 75, y, ease_out(prog(t, 0.2, 0.4)))
        y += 96
    hl = sp.get("hl")
    for i, ln in enumerate(lines):
        st = 0.3 + 0.22 * i
        if hl and hl in ln:
            k = ln.find(hl)
            x0 = pad + 75 + tlen(ln[:k], size)
            m = marker(int(tlen(hl, size) + 16), int(size * 0.72), 3 + i)
            pm = ease_in_out(prog(t, st + 0.45, 0.5))
            if pm > 0.01:
                mw = max(2, int(m.width * pm))
                c.alpha_composite(m.crop((0, 0, mw, m.height)), (int(x0 - 16), int(y + size * 0.42)))
        put_text(c, ln, size, col(sp.get("color", "ink")), pad + 75, y, ease_out(prog(t, st, 0.35)))
        y += size * 1.36
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    place_sheet(lay, c, W / 2, sp.get("y", 430), t, sp.get("ang", 1.2))
    return lay


def card_compare(sp, t, dur, frame):
    rows = sp["rows"]  # [左标签, 右内容, "ok"/"no"]
    w, rh = 980, 152
    h = int((112 if sp.get("title") else 40) + len(rows) * rh + 40)
    base, pad = sheet(w, h, 51)
    c = base.copy()
    ink = Ink(c.width, c.height, frame)
    y = pad + 36
    if sp.get("title"):
        put_text(c, sp["title"], 50, FADE, pad + 60, y, ease_out(prog(t, 0.15, 0.4)))
        y += 104
    for i, (lab, val, mark) in enumerate(rows):
        st = 0.3 + i * min(0.75, dur * 0.6 / max(1, len(rows)))
        a = ease_out(prog(t, st, 0.35))
        put_text(c, lab, 52, FADE, pad + 60, y + 22, a)
        vs = fit(val, 78, 520)
        put_text(c, val, vs, RED if mark == "no" else INK, pad + 270, y + 10, a)
        pm = prog(t, st + 0.35, 0.4)
        if mark == "ok":
            ink.check(pad + 840, y + 62, 80, BLUE, pm)
        else:
            ink.cross(pad + 840, y + 58, 74, RED, pm)
        if i < len(rows) - 1:
            ink.line([(pad + 50, y + rh - 14), (pad + w - 50, y + rh - 14)], FADE, 2.5, 0.7, 120, p=a)
        y += rh
    c.alpha_composite(ink.done())
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    place_sheet(lay, c, W / 2, sp.get("y", 470), t, sp.get("ang", -1.0))
    return lay


def card_doc(sp, t, dur, frame):
    w, h = 880, 960
    base, pad = sheet(w, h, 61)
    c = base.copy()
    ink = Ink(c.width, c.height, frame)
    title = sp["title"]
    put_text(c, title, 92, INK, pad + w / 2, pad + 64, ease_out(prog(t, 0.2, 0.4)), "c")
    tw = tlen(title, 92)
    pl = ease_in_out(prog(t, 0.45, 0.4))
    ink.line([(pad + w / 2 - tw / 2 - 20, pad + 196), (pad + w / 2 + tw / 2 + 20, pad + 194)], INK, 3.5, 0.6, p=pl)
    ink.line([(pad + w / 2 - tw / 2 - 20, pad + 207), (pad + w / 2 + tw / 2 + 20, pad + 206)], INK, 2.0, 0.6, p=pl)
    y = pad + 262
    for i, ln in enumerate(sp["body"].split("\n")):
        put_text(c, ln, 66, INK, pad + 80, y, ease_out(prog(t, 0.55 + 0.25 * i, 0.35)))
        y += 98
    y = pad + h - 280
    for i, name in enumerate(sp.get("sign", [])):
        st = 1.2 + 0.5 * i
        ink.line([(pad + 80, y + 70), (pad + w - 80, y + 70)], FADE, 2.5, 0.5, 150, p=ease_out(prog(t, st - 0.3, 0.3)))
        lay, lp = text_layer(name, 60, BLUE, False)
        rp = ease_in_out(prog(t, st, 0.45))
        if rp > 0:
            cw = max(1, int(lay.width * rp))
            c.alpha_composite(lay.crop((0, 0, cw, lay.height)), (int(pad + 110 - lp), int(y - 10 - lp)))
        y += 126
    if sp.get("note"):
        put_text(c, sp["note"], 26, FADE, pad + w - 40, pad + h - 52, 0.9, "r", heavy=False)
    c.alpha_composite(ink.done())
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    place_sheet(lay, c, W / 2, sp.get("y", 560), t, sp.get("ang", 1.6))
    return lay


def card_timeline(sp, t, dur, frame):
    rows = sp["rows"]  # [日期, 事件]
    hl = set(sp.get("hl", []))
    w, rh = 960, 172
    h = int(80 + len(rows) * rh + 20)
    base, pad = sheet(w, h, 71)
    c = base.copy()
    ink = Ink(c.width, c.height, frame)
    x_line = pad + 110
    y0 = pad + 70
    span = sp.get("span", dur * 0.78)
    sts = [0.25 + span * i / max(1, len(rows) - 1) * 0.92 for i in range(len(rows))]
    lp = ease_in_out(prog(t, 0.2, span))
    ink.line([(x_line, y0), (x_line, y0 + (len(rows) - 1) * rh + 10)], INK, 4.5, 0.8, p=lp)
    for i, (date, ev) in enumerate(rows):
        y = y0 + i * rh
        a = ease_out(prog(t, sts[i], 0.35))
        color = RED if i in hl else INK
        if a > 0.05:
            ink.ellipse(x_line, y + 4, 15, 15, color, 6, p=a)
        put_text(c, date, 64, color, x_line + 60, y - 40, a)
        put_text(c, ev, 54, INK if i not in hl else RED, x_line + 60, y + 40, a, heavy=i in hl)
    c.alpha_composite(ink.done())
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    place_sheet(lay, c, W / 2, sp.get("y", 520), t, sp.get("ang", -1.0))
    return lay


def card_route(sp, t, dur, frame):
    w, h = 980, 700
    base, pad = sheet(w, h, 81)
    c = base.copy()
    ink = Ink(c.width, c.height, frame)
    ax, ay, bx, by = pad + 180, pad + 220, pad + 800, pad + 440
    a1 = ease_out(prog(t, 0.2, 0.35))
    ink.ellipse(ax, ay, 14, 14, RED, 7, p=a1)
    put_text(c, sp["a"][0], 68, INK, ax - 70, ay - 168, a1)
    put_text(c, sp["a"][1], 42, FADE, ax - 70, ay - 80, a1)
    pp = ease_in_out(prog(t, 0.45, max(0.6, dur * 0.35)))
    pts = []
    for k in range(40):
        u = k / 39
        mx, my = (ax + bx) / 2, min(ay, by) - 150
        pts.append(((1 - u) ** 2 * ax + 2 * (1 - u) * u * mx + u * u * bx, (1 - u) ** 2 * ay + 2 * (1 - u) * u * my + u * u * by))
    n = int(len(pts) * pp)
    for k in range(0, max(0, n - 1), 3):  # 虚线
        ink.line(pts[k:k + 3], RED, 5, 0.6)
    if pp > 0.97:
        ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
        for s in (-0.5, 0.5):
            ink.line([(bx, by), (bx - 34 * math.cos(ang + s), by - 34 * math.sin(ang + s))], RED, 6, 0.6)
    a2 = ease_out(prog(t, 0.45 + max(0.6, dur * 0.35), 0.35))
    put_text(c, sp["b"][0], fit(sp["b"][0], 68, 640), INK, bx + 50, by + 6, a2, "r")
    put_text(c, sp["b"][1], 42, FADE, bx + 50, by + 92, a2, "r")
    if sp.get("label"):
        put_text(c, sp["label"], fit(sp["label"], 54, 880), RED, pad + w / 2, pad + h - 96, a2, "c")
    c.alpha_composite(ink.done())
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    place_sheet(lay, c, W / 2, sp.get("y", 480), t, sp.get("ang", 1.0))
    return lay


def card_quote(sp, t, dur, frame):
    lines = sp["text"].split("\n")
    size = sp.get("size", 96)
    size = min(size, min(fit(l, size, 800) for l in lines))
    w = int(max(max(tlen(l, size) for l in lines) + 220, 760))
    h = int(150 + len(lines) * size * 1.4 + 130)
    base, pad = sheet(w, h, 91)
    c = base.copy()
    put_text(c, "「", 170, RED, pad + 20, pad + 0, ease_out(prog(t, 0.15, 0.3)))
    hl = sp.get("hl")
    y = pad + 130
    for i, ln in enumerate(lines):
        st = 0.3 + 0.3 * i
        if hl and hl in ln:
            k = ln.find(hl)
            x0 = pad + 120 + tlen(ln[:k], size)
            m = marker(int(tlen(hl, size) + 16), int(size * 0.72), 7)
            pm = ease_in_out(prog(t, st + 0.5, 0.5))
            if pm > 0.01:
                c.alpha_composite(m.crop((0, 0, max(2, int(m.width * pm)), m.height)), (int(x0 - 16), int(y + size * 0.42)))
        put_text(c, ln, size, INK, pad + 120, y, ease_out(prog(t, st, 0.35)))
        y += size * 1.4
    by = sp.get("by", "")
    if by:
        put_text(c, by, 46, FADE, pad + w - (190 if sp.get("seal") else 80), y + 30, ease_out(prog(t, 0.9, 0.4)), "r")
    if sp.get("seal"):
        sp_ = prog(t, 1.1, 0.22)
        if sp_ > 0:
            sl = seal(sp["seal"], 96, 4)
            sc = 1 + 0.5 * (1 - sp_) ** 2
            sl2 = sl.resize((int(sl.width * sc), int(sl.height * sc)), Image.BICUBIC)
            put(c, sl2, pad + w - 96 - sl2.width / 2, y + 58 - sl2.height / 2, min(1, sp_ * 1.6))
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    place_sheet(lay, c, W / 2, sp.get("y", 480), t, sp.get("ang", -1.2))
    return lay


def card_list(sp, t, dur, frame):
    items = sp["items"]
    w, rh = 940, 140
    h = int((112 if sp.get("title") else 40) + len(items) * rh + (130 if sp.get("foot") else 30))
    base, pad = sheet(w, h, 101)
    c = base.copy()
    ink = Ink(c.width, c.height, frame)
    y = pad + 36
    if sp.get("title"):
        put_text(c, sp["title"], 50, FADE, pad + 70, y, ease_out(prog(t, 0.1, 0.35)))
        y += 106
    span = sp.get("span", dur * 0.6)
    for i, it in enumerate(items):
        st = 0.2 + span * i / max(1, len(items))
        a = ease_out(prog(t, st, 0.3))
        ink.line([(pad + 70, y + 22), (pad + 130, y + 22), (pad + 130, y + 82), (pad + 70, y + 82), (pad + 70, y + 20)], INK, 4, 0.6, p=a)
        ink.check(pad + 76, y + 48, 66, RED, prog(t, st + 0.2, 0.3))
        isz = fit(it, 78, w - 220)  # 长的条目自动缩字，不超出纸张
        put_text(c, it, isz, INK, pad + 176, y + 2 + (78 - isz) * 0.5, a)
        y += rh
    if sp.get("foot"):
        fa = ease_out(prog(t, 0.2 + span + 0.1, 0.35))
        put_text(c, sp["foot"], 76, RED, pad + w / 2, y + 14, fa, "c")
    c.alpha_composite(ink.done())
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    place_sheet(lay, c, W / 2, sp.get("y", 480), t, sp.get("ang", 1.0))
    return lay


def card_ask(sp, t, dur, frame):
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    q = sp["q"]
    put_text(lay, q, fit(q, 74, 980), WHITE, W / 2, 210, ease_out(prog(t, 0.05, 0.35)), "c", stroke=5, shadow=True)
    opts = sp["opts"]
    for i, o in enumerate(opts):
        s = fit(o, 132, 380)
        base, pad = sheet(460, 270, 111 + i)
        c = base.copy()
        put_text(c, o, s, INK, pad + 230, pad + 135 - s * 0.66, 1.0, "c")
        a = ease_out(prog(t, 0.25 + 0.2 * i, 0.35))
        im = c.rotate((-3 if i == 0 else 3), expand=True, resample=Image.BICUBIC)
        cx = W / 2 + (-262 if i == 0 else 262) + (-120 if i == 0 else 120) * (1 - a)
        put(lay, im, cx - im.width / 2, 470 - im.height / 2, a)
    put_text(lay, sp.get("mid", "还是"), 62, GOLD, W / 2, 430, ease_out(prog(t, 0.6, 0.3)), "c", stroke=5, shadow=True)
    if sp.get("foot"):
        put_text(lay, sp["foot"], 56, WHITE, W / 2, 700, ease_out(prog(t, 0.9, 0.4)), "c", stroke=4, shadow=True)
    return lay


def card_end(sp, t, dur, frame):
    """片尾纸条（与长视频同款）：朱红「订」印 + 小字 + 两行大字 + 红笔底线。"""
    lay = Image.new("RGBA", (W, MAIN_H), (0, 0, 0, 0))
    kick = sp.get("kicker", "如果这个故事打动了你")
    l1, l2 = sp.get("line1", "订阅，一起读完"), sp.get("line2", "《乔布斯传》")
    bs = 92
    w, h = int(max(tlen(l1, bs), tlen(l2, bs)) + 330), 400
    base, pad = sheet(w, h, 121)
    c = base.copy()
    ink = Ink(c.width, c.height, frame)
    x0 = pad + 260
    put_text(c, kick, 44, FADE, x0, pad + 50, ease_out(prog(t, 0.35, 0.4)))
    for row, (ln, color) in enumerate(((l1, INK), (l2, RED))):
        x = x0
        for i, ch in enumerate(ln):  # 逐字浮现
            p = ease_out(prog(t, 0.45 + 0.25 * row + 0.04 * i, 0.3))
            put_text(c, ch, bs, color, x, pad + 120 + row * 128 + (1 - p) * 18, p)
            x += tlen(ch, bs)
    ul = ease_in_out(prog(t, 1.0 + 0.04 * len(l2), 0.5))
    yl = pad + 120 + 128 + bs * 1.22
    ink.line([(x0 - 4, yl), (x0 + tlen(l2, bs) + 6, yl - 4)], RED, 7, 1.0, 235, p=ul)
    c.alpha_composite(ink.done())
    sp_ = prog(t, 0.3, 0.22)
    if sp_ > 0:
        sl = seal(sp.get("seal", "订"), 150, 6)
        sc = 1 + 0.55 * (1 - sp_) ** 2
        sl2 = sl.resize((int(sl.width * sc), int(sl.height * sc)), Image.BICUBIC)
        put(c, sl2, pad + 135 - sl2.width / 2, pad + h / 2 - sl2.height / 2, min(1, sp_ * 1.6))
    place_sheet(lay, c, W / 2, sp.get("y", 500), t, -1.4)
    return lay


CARDS = {"num": card_num, "note": card_note, "compare": card_compare, "doc": card_doc, "timeline": card_timeline,
         "route": card_route, "quote": card_quote, "list": card_list, "ask": card_ask, "end": card_end}


# ---------- 弹出元素（相对主画面坐标） ----------

def pop_layer(pop, t, frame):
    """label：纸条从左侧滑入；stamp：红色戳记「盖」下去。t 为弹出后的秒数。回传 (图层, x, y) 或 None。"""
    if t < 0:
        return None
    kind = pop.get("kind", "label")
    if kind == "stamp":
        st = stamp(pop["text"], pop.get("size", 104), pop.get("seed", 5))
        p = prog(t, 0, 0.16)
        sc = 1 + 0.9 * (1 - p) ** 2
        im = st.rotate(pop.get("rot", -10), expand=True, resample=Image.BICUBIC)
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
        a = min(1, p * 1.8)
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        return im, pop["x"] - im.width / 2, pop["y"] - im.height / 2
    size = pop.get("size", 52)
    color = col(pop.get("color", "ink"))
    tw = tlen(pop["text"], size)
    base, pad = sheet(int(tw + 70), int(size * 1.7), 131 + len(pop["text"]))
    c = base.copy()
    put_text(c, pop["text"], size, color, pad + 35, pad + size * 0.32, 1.0)
    im = c.rotate(pop.get("rot", -2.0), expand=True, resample=Image.BICUBIC)
    a = ease_out(prog(t, 0, 0.28))
    x = pop.get("x", 40) - 80 * (1 - a) if pop.get("from", "left") == "left" else pop.get("x", 40) + 80 * (1 - a)
    if pop.get("anchor") == "r":
        x -= im.width
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im, x, pop.get("y", 60)


# ---------- 顶部片名纸条 ----------

class Hook:
    def __init__(self, spec):
        self.kicker, self.title, self.sub = spec.get("kicker", ""), spec["title"], spec.get("sub", "")
        self.seal = spec.get("seal")
        self.ts = fit(self.title, 78, 790 if self.seal else 930)
        self.ss = fit(self.sub, 52, 790 if self.seal else 930) if self.sub else 0
        self.left = 170 if self.seal else 60
        w = int(max(tlen(self.title, self.ts), tlen(self.sub, self.ss) if self.sub else 0) + self.left + 70)
        self.w, self.h = min(w, 1036), 286 if self.sub else 214
        self.base, self.pad = sheet(self.w, self.h, 141)
        self.static = None

    def layer(self, t, frame):
        if self.static is not None and t > 1.6:
            return self.static
        pad = self.pad
        c = self.base.copy()
        ink = Ink(c.width, c.height, frame)  # 定格时沿用当下这一帧，不跳变
        x0 = pad + self.left
        if self.kicker:
            put_text(c, self.kicker, 34, FADE, x0, pad + 24, ease_out(prog(t, 0.3, 0.4)))
        y = pad + 66
        x = x0
        for i, ch in enumerate(self.title):
            p = ease_out(prog(t, 0.4 + 0.035 * i, 0.28))
            put_text(c, ch, self.ts, INK, x, y + (1 - p) * 16, p)
            x += tlen(ch, self.ts)
        ul = ease_in_out(prog(t, 0.55 + 0.035 * len(self.title), 0.45))
        ink.line([(x0 - 4, y + self.ts * 1.2), (x0 + tlen(self.title, self.ts) + 6, y + self.ts * 1.2 - 4)], RED, 6, 0.9, 230, p=ul)
        if self.sub:
            put_text(c, self.sub, self.ss, RED, x0, y + self.ts * 1.42, ease_out(prog(t, 0.9, 0.4)))
        c.alpha_composite(ink.done())
        if self.seal:
            sp = prog(t, 0.25, 0.22)
            if sp > 0:
                sl = seal(self.seal, 100, 2)
                sc = 1 + 0.55 * (1 - sp) ** 2
                sl2 = sl.resize((int(sl.width * sc), int(sl.height * sc)), Image.BICUBIC)
                put(c, sl2, pad + 92 - sl2.width / 2, pad + self.h / 2 - sl2.height / 2, min(1, sp * 1.6))
        a = ease_out(prog(t, 0.0, 0.35))
        im = c.rotate(-1.0 - 3.0 * (1 - a), expand=True, resample=Image.BICUBIC)
        out = Image.new("RGBA", (W, MAIN_Y + 20), (0, 0, 0, 0))
        put(out, im, W / 2 - im.width / 2, (MAIN_Y + 20) / 2 - im.height / 2 - 6 - 50 * (1 - a), a)
        if t > 1.6:
            self.static = out
        return out


# ---------- 字幕 ----------

@lru_cache(maxsize=512)
def caption(s, hl):
    """白字黑边；数字与关键词金色。hl 为以「|」分隔的关键词。"""
    size = fit(s, 72, CAP_W)
    keys = [k for k in hl.split("|") if k]
    colors = [WHITE] * len(s)
    for k in keys:
        i = s.find(k)
        while i >= 0:
            for j in range(i, i + len(k)):
                colors[j] = GOLD
            i = s.find(k, i + 1)
    for i, ch in enumerate(s):
        if ch.isdigit() or (ch in ",.%" and 0 < i < len(s) - 1 and s[i - 1].isdigit()):
            colors[i] = GOLD
    f = font(size, True)
    w = int(f.getlength(s)) + 2
    pad = 22
    img = Image.new("RGBA", (w + 2 * pad, int(size * 1.4) + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad + 3, pad + 6), s, font=f, fill=(0, 0, 0, 200), stroke_width=8, stroke_fill=(0, 0, 0, 200))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    d = ImageDraw.Draw(img)
    x = pad
    for ch, c in zip(s, colors):
        d.text((x, pad), ch, font=f, fill=c + (255,), stroke_width=7, stroke_fill=(10, 8, 6, 255))
        x += f.getlength(ch)
    return img


# ---------- 音效（本地合成） ----------

def sfx_track(n, events, sr):
    out = np.zeros(n, np.float32)
    r = np.random.default_rng(1)
    for t0, kind in events:
        a = int(t0 * sr)
        if kind == "stamp":
            L = int(0.32 * sr)
            tt = np.arange(L) / sr
            body = np.sin(2 * math.pi * 62 * tt) * np.exp(-tt / 0.07) * 0.38
            nz = r.normal(0, 1, L).astype(np.float32)
            nz = np.convolve(nz, np.ones(12) / 12, "same") * np.exp(-tt / 0.025) * 0.32
            x = body + nz
        elif kind == "paper":
            L = int(0.34 * sr)
            tt = np.arange(L) / sr
            nz = r.normal(0, 1, L).astype(np.float32)
            nz = nz - np.convolve(nz, np.ones(40) / 40, "same")  # 去掉低频，留下纸的「沙」声
            env = np.sin(math.pi * np.clip(tt / 0.34, 0, 1)) ** 2
            x = nz * env * 0.075
        else:  # tick
            L = int(0.05 * sr)
            tt = np.arange(L) / sr
            x = np.sin(2 * math.pi * 1900 * tt) * np.exp(-tt / 0.008) * 0.12
        b = min(n, a + len(x))
        if a < n:
            out[a:b] += x[: b - a]
    return out


def mix_sfx(mix_path, out_path, events):
    with wave.open(mix_path) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32).reshape(-1, ch) / 32768
    s = sfx_track(len(x), events, sr)
    x = x + s[:, None]
    with wave.open(out_path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return out_path


# ---------- 主流程 ----------

def word_clock(paras):
    """回传 find(phrase) → 该词开口的绝对秒数（按出现顺序往后找）。"""
    tats = [v2.align_paragraph(p["text"], p["times"], p["audio"]) for p in paras]
    cur = [0, 0]   # 下一个画面从这里往后找
    mark = [0, 0]  # 当前画面开口的位置：它的弹出元素从这里往后找（不推进 cur）

    def find(phrase, pop=False):
        pi, ci = mark if pop else cur
        while pi < len(paras):
            k = paras[pi]["text"].find(phrase, ci)
            if k >= 0:
                if not pop:
                    cur[0], cur[1] = pi, k + 1
                    mark[0], mark[1] = pi, k
                return paras[pi]["start"] + tats[pi](k)
            pi, ci = pi + 1, 0
        raise ValueError(f"文案里找不到「{phrase}」（beats 要按文案顺序写）")
    return find


def build(ep, sid, spec):
    sdir = os.path.join(ep, "08_Shorts", sid)
    script = json.load(open(os.path.join(sdir, "01_文案/script.json"), encoding="utf-8"))
    _vis, aud, _ch, paras, _t = v2.build_timeline_long(sdir, script, 0.15, A.TITLE_DUR, A.decode_mp3)
    last = paras[-1]
    voice_end = last["start"] + len(last["audio"]) / A.SR
    total = voice_end + END_DUR
    find = word_clock(paras)
    beats = []
    for b in spec["beats"]:
        start = 0.0 if not beats else find(b["at"]) - 0.06
        pops = []
        for p in b.get("pops", []):
            pops.append({**p, "t0": find(p["at"], pop=True) - 0.04 if p.get("at") else start + p.get("delay", 0.15)})
        beats.append({**b, "start": start, "pops": pops})
    beats.append({"img": beats[-1].get("img"), "dim": 0.62, "card": {"type": "end", **spec.get("end", {})},
                  "start": voice_end + 0.15, "pops": []})
    frame_keys = ("fx", "fy", "scale", "zoom", "pan", "rate")
    for i, b in enumerate(beats):
        b["end"] = beats[i + 1]["start"] if i + 1 < len(beats) else total
        prev = beats[i - 1] if i else None
        # 没写图、或沿用上一张图且没写取景：同一个镜头继续推拉（上面盖卡片），不重新开始
        if prev and (not b.get("img") or (b["img"] == prev["img"] and not any(k in b for k in frame_keys))):
            b["img"] = prev["img"]
            for k in frame_keys:
                if k in prev:
                    b[k] = prev[k]
            b["seg"] = prev["seg"]
        else:
            b["seg"] = i
    seg_start, seg_end = {}, {}
    for b in beats:
        seg_start.setdefault(b["seg"], b["start"])
        seg_end[b["seg"]] = b["end"]
    for i, b in enumerate(beats):
        b["seg_start"], b["seg_dur"] = seg_start[b["seg"]], seg_end[b["seg"]] - seg_start[b["seg"]]
        dim = b.get("dim", 0.55 if b.get("card") else 0.0)
        b["dim"] = dim
        b["dim_from"] = beats[i - 1]["dim"] if i and beats[i - 1]["seg"] == b["seg"] else dim
    events = v2.build_subs(paras, lambda tx: v2.split_chunks(tx, CAP_CHARS), A.clean_sub, CAP_CHARS, A.decode_mp3)
    events = fix_numbers([[a, b, s] for a, b, s in events])
    return sdir, aud, beats, events, total


def render(ep, sid, spec, preview=None, stills=None):
    sdir, aud, beats, events, total = build(ep, sid, spec)
    assets = Assets(ep)
    hook = Hook(spec["hook"])
    hl = "|".join(spec.get("cap_hl", []))
    grain = grains()
    mask = main_mask()
    print(f"{sid}: {total:.1f} 秒，画面 {len(beats)} 个（平均 {total / len(beats):.2f} 秒一切），字幕 {len(events)} 条", flush=True)

    def main_at(b, t_abs):
        img = assets.img(b["img"])
        m = view(img, b, t_abs - b["seg_start"], b["seg_dur"])
        # 盖卡片时画面在 0.3 秒内平滑压暗，不要一下子变黑
        dim = b["dim_from"] + (b["dim"] - b["dim_from"]) * ease_in_out((t_abs - b["start"]) / 0.3)
        if dim > 0.003:
            m = Image.blend(m, Image.new("RGBA", m.size, (12, 10, 9, 255)), dim)
        return m

    def frame_at(t, f):
        idx = max(i for i, b in enumerate(beats) if b["start"] <= t + 1e-6)
        b = beats[idx]
        tb = t - b["start"]
        fr = assets.backdrop(b["img"]).copy()
        m = main_at(b, t)
        if idx > 0 and tb < 0.12 and beats[idx - 1]["seg"] != b["seg"]:  # 换镜头：0.12 秒交叉淡化，不额外缩放
            m = Image.blend(main_at(beats[idx - 1], t), m, ease_in_out(tb / 0.12))
        shake = 0  # 不再整屏抖动（频道主 10/17）
        mm = m.copy()
        mm.putalpha(mask)
        fr.alpha_composite(mm, (int(shake), MAIN_Y))
        if b.get("credit", True) and b["img"].startswith("web_") and not b.get("card"):
            cr = assets.credit(b["img"])
            if cr:
                put_text(fr, cr, 22, (215, 210, 200), 40, MAIN_Y + MAIN_H - 395, 0.85, heavy=False, shadow=True)
        if b.get("card"):
            cd = CARDS[b["card"]["type"]](b["card"], tb, b["end"] - b["start"], f)
            fr.alpha_composite(cd, (int(shake), MAIN_Y))
        for p in b["pops"]:
            r = pop_layer(p, t - p["t0"], f)
            if r:
                im, x, y = r
                put(fr, im, x + shake, MAIN_Y + y)
        fr.alpha_composite(hook.layer(t, f), (0, 0))
        cue = next((e for e in events if e[0] <= t < e[1]), None)
        if cue and not (b.get("card", {}).get("type") == "end"):
            ci = caption(cue[2], hl)
            put(fr, ci, W / 2 - ci.width / 2, CAP_Y - ci.height / 2, ease_out(prog(t, cue[0], 0.08)))
        fr.alpha_composite(grain[(f // 2) % 3])
        return fr.convert("RGB")

    if stills:
        out_dir = os.path.join(sdir, "99_工作文件/stills")
        os.makedirs(out_dir, exist_ok=True)
        for s in stills:
            frame_at(s, int(s * FPS)).save(os.path.join(out_dir, f"{sid}_{s:05.1f}.jpg"), quality=88)
        print("静帧:", out_dir)
        return

    # 音频：人声 + 背景音乐（重新按长度生成）+ 纸张声、盖章声
    work = os.path.join(sdir, "99_工作文件")
    os.makedirs(work, exist_ok=True)
    bgm = os.path.join(sdir, "02_配音/bgm.wav")
    if os.path.exists(bgm):
        with wave.open(bgm) as w:
            if w.getnframes() / w.getframerate() < total + 0.5:
                os.remove(bgm)
    mix = A.build_audio(sdir, aud, total, work, seed=spec.get("bgm_seed", 7), gains=tuple(spec.get("bgm_gain", (0.07, 0.22))))
    # 音效只留三种时刻（频道主 10/17：音效太多）：开场纸条落下 + 盖印、红色戳记、片尾盖印。信息卡、标签不发声。
    sfx = [(0.0, "paper"), (0.25, "stamp")]
    for b in beats[1:]:
        if b.get("card", {}).get("type") == "end":
            sfx.append((b["start"] + 0.3, "stamp"))
        for p in b["pops"]:
            if p.get("kind") == "stamp":
                sfx.append((p["t0"], "stamp"))
    mix = mix_sfx(mix, os.path.join(sdir, "02_配音/mix_sfx.wav"), sfx)

    out = os.path.join(sdir, f"{sid}.mp4")
    n = round((min(preview, total) if preview else total) * FPS)
    fc = f"[1:a]afade=t=in:st=0:d=0.08,afade=t=out:st={total - 0.5:.2f}:d=0.5,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-t", f"{total:.3f}", "-i", mix, "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-frames:v", str(n),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(n):
        proc.stdin.write(np.asarray(frame_at(f / FPS, f)).tobytes())
        if f % 300 == 0:
            print(f"  {f}/{n}", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 失败")
    with open(os.path.join(sdir, f"{sid}.srt"), "w", encoding="utf-8") as fh:
        for i, (a, b, s) in enumerate(events, 1):
            fh.write(f"{i}\n{A.srt_time(a)} --> {A.srt_time(b)}\n{s}\n\n")
    print("输出:", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter")
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--preview", type=float)
    ap.add_argument("--stills", help="只输出这些秒数的静帧，例如 1,5,9")
    args = ap.parse_args()
    ep = args.chapter.rstrip("/")
    cfg = json.load(open(os.path.join(ep, "08_Shorts/shorts.json"), encoding="utf-8"))
    stills = [float(x) for x in args.stills.split(",")] if args.stills else None
    for sid in args.ids:
        render(ep, sid, cfg[sid], args.preview, stills)


if __name__ == "__main__":
    main()
