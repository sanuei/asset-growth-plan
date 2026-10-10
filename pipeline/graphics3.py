"""手作纸张质感的图表与文字卡（EP003 起使用）。

对应频道主要求的「纸张质感、抖动的文字、发光文字，像传统 PR / AE 做出来的亲切效果，不要科技感、不要像 PPT」：
- 一张有纸纹、折痕、不规则边缘和胶带的纸，铺在模糊暗化的场景图上。
- 墨水线条与文字每 3 帧（10 fps）重画一次轻微抖动（boil），柱子、折线、箭头都是「手画」的，带笔压重叠。
- 重点数字用荧光笔划过，并带一点暖色柔光。
- 线条在 2 倍分辨率画布上绘制再缩小，边缘平滑。

接口与 graphics2 相同：DRAW[type](spec, t, dur) -> RGBA 画面；graphics2 末尾会 import 本模块并注册。
所有内容在 y=848 以内（下方 860 起是字幕）。
"""
import math
import os
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graphics2 as G2  # noqa: E402
from graphics import wrap  # noqa: E402

W, H, FPS = G2.W, G2.H, G2.FPS
S = 2                                  # 画布超采样倍数
X0, Y0, X1, Y1 = 150, 54, 1770, 848    # 纸张区域
SW, SH = X1 - X0, Y1 - Y0
LEFT, RIGHT = 240, 1680
PAPER = (244, 237, 221)
INK = (36, 31, 28)
FADE = (116, 104, 90)
RED = (176, 44, 36)
BLUE = (28, 68, 126)
GREEN = (34, 104, 66)
AMBER = (190, 120, 16)
CL = {"ink": INK, "fade": FADE, "red": RED, "blue": BLUE, "green": GREEN, "amber": AMBER}
BOIL = [(-1.0, 0.5), (0.9, -0.7), (0.2, 0.9)]
prog, ease_out, ease_in_out = G2.prog, G2.ease_out, G2.ease_in_out


def col(c):
    return CL.get(c, c) if isinstance(c, str) else tuple(c)


# ---------- 纸张 ----------

@lru_cache(maxsize=1)
def paper():
    pad = 44
    w, h = SW, SH
    rng = np.random.default_rng(5)

    def noise(sc, amp):
        small = rng.normal(0, 1, (max(2, h // sc), max(2, w // sc))).astype(np.float32)
        return np.asarray(Image.fromarray(small).resize((w, h), Image.BICUBIC)) * amp

    base = np.empty((h, w, 3), np.float32)
    base[:] = PAPER
    n = noise(70, 4.0) + noise(16, 2.6) + noise(4, 2.0) + rng.normal(0, 1.8, (h, w)).astype(np.float32)
    base += n[..., None]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ux, uy = xx / w, yy / h
    edge = np.maximum(np.abs(ux - 0.5), np.abs(uy - 0.5)) * 2
    base *= (1 - 0.075 * edge ** 3)[..., None]
    for pos, horizontal in ((0.5, False), (0.5, True)):  # 四折的折痕
        d = (uy - pos) * h if horizontal else (ux - pos) * w
        crease = -5.0 * np.exp(-(d / 2.2) ** 2) + 3.0 * np.exp(-((d - 5) / 4.0) ** 2)
        base += crease[..., None]
    paper_rgb = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    # 不规则边缘
    mask = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    pts = []
    r2 = np.random.default_rng(9)
    for x in range(0, w, 24):
        pts.append((pad + x, pad + r2.normal(0, 1.6)))
    for y in range(0, h, 24):
        pts.append((pad + w + r2.normal(0, 1.6), pad + y))
    for x in range(w, 0, -24):
        pts.append((pad + x, pad + h + r2.normal(0, 1.6)))
    for y in range(h, 0, -24):
        pts.append((pad + r2.normal(0, 1.6), pad + y))
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.9))
    out = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    out.paste(paper_rgb, (pad, pad))
    out.putalpha(mask)
    shadow = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(20)).point(lambda v: int(v * 0.6)))
    sheet = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    sheet.alpha_composite(shadow, (7, 12))
    sheet.alpha_composite(out)
    # 两条胶带
    tape = Image.new("RGBA", (190, 56), (236, 228, 196, 150))
    td = ImageDraw.Draw(tape)
    for k in range(0, 190, 7):
        td.line([k, 0, k - 18, 56], fill=(255, 255, 240, 38), width=2)
    for cx, ang in ((pad + 70, 8), (pad + w - 70, -8)):
        tp = tape.rotate(ang, expand=True, resample=Image.BICUBIC)
        sheet.alpha_composite(tp, (int(cx - tp.width / 2), int(pad - 22 - tp.height / 2 + 24)))
    return sheet, pad


@lru_cache(maxsize=16)
def marker(w, h, seed=1):
    """荧光笔笔触：边缘略不规则的黄色色块。"""
    w, h = int(w), int(h)
    r = np.random.default_rng(seed)
    im = Image.new("RGBA", (w + 16, h + 16), (0, 0, 0, 0))
    pts = [(8 + r.normal(0, 2), 8 + r.normal(0, 2)), (8 + w / 2, 5 + r.normal(0, 2)), (8 + w + r.normal(0, 3), 9 + r.normal(0, 2)),
           (11 + w + r.normal(0, 3), 8 + h / 2), (8 + w + r.normal(0, 3), 8 + h + r.normal(0, 2)), (8 + w / 2, 11 + h + r.normal(0, 2)),
           (8 + r.normal(0, 2), 8 + h + r.normal(0, 2)), (5 + r.normal(0, 2), 8 + h / 2)]
    ImageDraw.Draw(im).polygon(pts, fill=(255, 214, 20, 150))
    return im.filter(ImageFilter.GaussianBlur(1.4))


@lru_cache(maxsize=96)
def glow_layer(s, size, color, heavy=True):
    lay, pad = G2.text_layer(s, size, color, heavy, 0, False)
    p2 = 34
    big = (lay.width + 2 * p2, lay.height + 2 * p2)
    a = Image.new("L", big, 0)
    a.paste(lay.getchannel("A"), (p2, p2))
    a = a.filter(ImageFilter.GaussianBlur(15)).point(lambda v: min(255, int(v * 0.85)))
    g = Image.merge("RGBA", (Image.new("L", big, 255), Image.new("L", big, 168), Image.new("L", big, 70), a))
    g.alpha_composite(lay, (p2, p2))
    return g, pad + p2


# ---------- 画布（墨水） ----------

class Canvas:
    def __init__(self, ph):
        self.im = Image.new("RGBA", (SW * S, SH * S), PAPER + (0,))
        self.d = ImageDraw.Draw(self.im)
        self.ph, self.sid = ph, 0

    def pt(self, x, y):
        return ((x - X0) * S, (y - Y0) * S)

    def rng(self):
        self.sid += 1
        return np.random.default_rng([self.ph % 100000, self.sid])

    @staticmethod
    def dense(pts, step=22):
        pts = np.asarray(pts, float)
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(1, int(np.hypot(*(b - a)) // step))
            for k in range(1, n + 1):
                out.append(a + (b - a) * k / n)
        return np.array(out)

    def wobble(self, pts, amp):
        pts = self.dense(pts)
        n = len(pts)
        m = max(2, n // 7 + 2)
        r = self.rng()
        wx = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, m), r.normal(0, amp, m))
        wy = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, m), r.normal(0, amp, m))
        return pts + np.stack([wx, wy], 1)

    def line(self, pts, color, width=4.0, amp=1.0, alpha=255, pen=True):
        color = col(color)
        if len(pts) < 2:
            return
        xy = [self.pt(*p) for p in self.wobble(pts, amp)]
        self.d.line(xy, fill=color + (alpha,), width=max(1, int(width * S)), joint="curve")
        if pen:  # 笔压：细一点的第二遍，稍有偏移
            xy2 = [self.pt(*p) for p in self.wobble(pts, amp * 1.3)]
            self.d.line(xy2, fill=color + (int(alpha * 0.45),), width=max(1, int(width * S * 0.55)), joint="curve")

    def poly(self, pts, color, alpha=255):
        self.d.polygon([self.pt(*p) for p in pts], fill=col(color) + (alpha,))

    def fill_rect(self, x0, y0, x1, y1, color, alpha=235, amp=1.2):
        r = self.rng()
        j = lambda: r.normal(0, amp)  # noqa: E731
        self.poly([(x0 + j(), y0 + j()), (x1 + j(), y0 + j()), (x1 + j(), y1 + j()), (x0 + j(), y1 + j())], color, alpha)

    def rect(self, x0, y0, x1, y1, color, width=4.0, amp=1.0, over=7):
        self.line([(x0 - over, y0), (x1 + over, y0)], color, width, amp)
        self.line([(x1, y0 - over), (x1, y1 + over)], color, width, amp)
        self.line([(x1 + over, y1), (x0 - over, y1)], color, width, amp)
        self.line([(x0, y1 + over), (x0, y0 - over)], color, width, amp)

    def circle(self, cx, cy, r, color, width=4.0, amp=1.0, turns=1.07):
        a = np.linspace(-0.5, -0.5 + 2 * math.pi * turns, 40)
        rr = r * (1 + np.linspace(0, 0.06, 40))
        self.line(list(zip(cx + rr * np.cos(a), cy + rr * np.sin(a))), color, width, amp)

    def hatch(self, x0, y0, x1, y1, color, gap=16, alpha=60):
        color = col(color)
        c = x0 + y0
        while c < x1 + y1:
            xa, xb = max(x0, c - y1), min(x1, c - y0)
            if xb > xa:
                self.d.line([self.pt(xa, c - xa), self.pt(xb, c - xb)], fill=color + (alpha,), width=S * 2)
            c += gap

    def marker(self, x0, y0, x1, y1, p=1.0):
        if p <= 0.01 or x1 <= x0:
            return
        self._paste_marker(marker(x1 - x0, y1 - y0), x0, y0, p)

    def _paste_marker(self, m, x0, y0, p):
        w = max(2, int(m.width * p))
        big = m.crop((0, 0, w, m.height)).resize((w * S, m.height * S), Image.BICUBIC)
        self.im.alpha_composite(big, (int((x0 - 8 - X0) * S), int((y0 - 8 - Y0) * S)))

    def arrow(self, x0, y0, x1, y1, color, width=5.0, p=1.0):
        if p <= 0.01:
            return
        xe, ye = x0 + (x1 - x0) * min(p, 1), y0 + (y1 - y0) * min(p, 1)
        self.line([(x0, y0), (xe, ye)], color, width, 1.0)
        if p > 0.9:
            ang = math.atan2(y1 - y0, x1 - x0)
            for s in (-0.5, 0.5):
                self.line([(x1, y1), (x1 - 26 * math.cos(ang + s), y1 - 26 * math.sin(ang + s))], color, width, 0.8, pen=False)

    def finish(self):
        return self.im.reduce(S)


# ---------- 帧与文字 ----------

class Card:
    def __init__(self, spec, t, dur):
        self.spec, self.t, self.dur = spec, t, dur
        self.ph = int(t * FPS) // 3
        self.fr = G2.background(spec, t, dur)
        dark = Image.new("RGBA", (W, H), (6, 10, 20, 30))
        self.fr.alpha_composite(dark)
        sheet, pad = paper()
        a = prog(t, 0.0, 0.55)
        G2.place(self.fr, sheet, X0 - pad, Y0 - pad, alpha=a, dy=(1 - a) * 26)
        self.cv = Canvas(self.ph)
        self.a_sheet = a

    def blit(self):
        lay = self.cv.finish()
        al = lay.getchannel("A")
        a = self.a_sheet
        if a < 0.999:
            lay.putalpha(al.point(lambda v: int(v * a)))
        self.fr.alpha_composite(lay, (X0, Y0))
        if getattr(self, "heading_text", None):
            self.txt(self.heading_text[0], 52, INK, LEFT, 82, 0.15)

    def txt(self, s, size, color, x, y, start, anchor="l", heavy=True, length=0.7, glow=False, dist=14):
        color = col(color)
        if glow:
            lay, pad = glow_layer(s, size, color, heavy)
        else:
            lay, pad = G2.text_layer(s, size, color, heavy, 0, False)
        w = lay.width - 2 * pad
        ax = {"l": x, "c": x - w / 2, "r": x - w}[anchor]
        a = prog(self.t, start, length)
        bx, by = BOIL[self.ph % 3] if a > 0.99 else (0, 0)
        G2.place(self.fr, lay, ax - pad, y - pad, alpha=a, dy=(1 - a) * dist + by * 0.8, dx=bx * 0.8)
        return w

    def lines(self, s, size, color, x, y, start, anchor="l", heavy=True, gap=1.32, **kw):
        for i, ln in enumerate(s.split("\n")):
            self.txt(ln, size, color, x, y + i * size * gap, start + 0.12 * i, anchor, heavy, **kw)

    def heading(self):
        sp = self.spec
        if sp.get("title"):
            w = G2.font(52, True).getlength(sp["title"])
            p = prog(self.t, 0.5, 0.8, ease_in_out)
            self.cv.line([(LEFT, 154), (LEFT + (w + 8) * p, 154 - 3 * p)], RED, 5, 1.3)
            self.heading_text = (sp["title"], w)
        else:
            self.heading_text = None

    def footer(self):
        if self.spec.get("source"):
            self.txt(self.spec["source"], 24, FADE, LEFT, 806, 0.7, heavy=False, length=1.0)

    def done(self):
        return self.fr


def fit_size(s, size, max_w, heavy=True):
    f = G2.font(size, heavy)
    while size > 28 and f.getlength(s) > max_w:
        size -= 4
        f = G2.font(size, heavy)
    return size


def trunc(xs, ys, frac_x):
    """折线只画到横坐标 frac_x 为止，终点按线性插值。"""
    out = [(x, y) for x, y in zip(xs, ys) if x <= frac_x]
    if len(out) < len(xs) and out:
        i = len(out)
        x0, y0, x1, y1 = xs[i - 1], ys[i - 1], xs[i], ys[i]
        out.append((frac_x, y0 + (y1 - y0) * (frac_x - x0) / (x1 - x0)))
    return out


# ---------- 卡片 ----------

def card_counter(spec, t, dur):
    c = Card(spec, t, dur)
    c.heading()
    dec = spec.get("decimals", 0)
    prefix, unit = spec.get("prefix", ""), spec.get("unit", "")
    final = f"{prefix}{spec['value']:,.{dec}f}"
    v = spec["value"] * ease_out((t - 0.5) / 2.0)
    cur = f"{prefix}{v:,.{dec}f}"
    f = G2.font(250, True)
    wf = f.getlength(final)
    fu = G2.font(90, True)
    wu = fu.getlength(unit) + 30 if unit else 0
    x = 960 - (wf + wu) / 2
    ymid = 330
    c.cv.marker(x - 24, ymid + 120, x + wf + 24, ymid + 250, prog(t, 2.6, 0.7, ease_in_out))
    c.blit()
    c.txt(spec["label"], 54, FADE, 960, 190, 0.2, "c")
    c.txt(cur, 250, INK, x, ymid, 0.4, "l", glow=t > 2.6)
    if unit:
        c.txt(unit, 90, RED, x + wf + 30, ymid + 140, 0.9, "l")
    if spec.get("sub"):
        c.lines(spec["sub"], 44, INK, 960, 640, 1.6, "c", heavy=False)
    c.footer()
    return c.done()


def card_compare(spec, t, dur):
    c = Card(spec, t, dur)
    c.heading()
    cols = spec["columns"]
    n = len(cols)
    ops = spec.get("ops", [""] * (n - 1))
    cw = (RIGHT - LEFT) / n
    vy = spec.get("vy", 340)
    for i, cc in enumerate(cols):
        st = 0.35 + 0.6 * i
        cx = LEFT + cw * (i + 0.5)
        if cc.get("box", True):
            c.cv.rect(cx - cw * 0.44, 236, cx + cw * 0.44, 770, FADE, 3, 1.2, over=8) if prog(t, st, 0.6) > 0.02 and spec.get("boxes", False) else None
        if cc.get("hl"):
            vw = G2.font(fit_size(cc["value"], cc.get("size", 130), cw * (0.72 if n > 2 and any(ops) else 0.86)), True).getlength(cc["value"])
            c.cv.marker(cx - vw / 2 - 16, vy + 56, cx + vw / 2 + 16, vy + 150, prog(t, st + 0.6, 0.6, ease_in_out))
    c.blit()
    for i, cc in enumerate(cols):
        st = 0.35 + 0.6 * i
        cx = LEFT + cw * (i + 0.5)
        color = cc.get("color", "ink")
        c.txt(cc["label"], 42, FADE, cx, 250, st, "c")
        size = fit_size(cc["value"], cc.get("size", 130), cw * (0.72 if n > 2 and any(ops) else 0.86))
        c.txt(cc["value"], size, color, cx, vy, st + 0.1, "c", glow=bool(cc.get("hl")) and t > st + 0.7)
        if cc.get("sub"):
            c.lines(cc["sub"], 38, INK, cx, vy + 190, st + 0.35, "c", heavy=False)
        if i < n - 1 and ops[i]:
            c.txt(ops[i], 76, RED, LEFT + cw * (i + 1), vy + 26, st + 0.45, "c")
    c.footer()
    return c.done()


def _bar_layout(items, vmin, vmax, top=270, bottom=720):
    span = vmax - vmin or 1
    zero = bottom - (0 - vmin) / span * (bottom - top)
    return zero, (bottom - top) / span


def card_bars(spec, t, dur):
    c = Card(spec, t, dur)
    c.heading()
    items = spec["items"]
    vals = [it["value"] for it in items]
    vmax, vmin = spec.get("vmax", max(max(vals), 0)), spec.get("vmin", min(min(vals), 0))
    neg_only = vmax <= 0
    top, bottom = (300, 700) if neg_only else (280, 700)
    zero, k = _bar_layout(items, vmin, vmax, top, bottom)
    n = len(items)
    slot = (RIGHT - LEFT - 60) / n
    bw = slot * 0.56
    c.cv.line([(LEFT, zero), (RIGHT - 20, zero)], INK, 4, 0.8)
    geo = []
    for i, it in enumerate(items):
        cx = LEFT + 30 + slot * (i + 0.5)
        p = prog(t, 0.45 + 0.22 * i, 0.9)
        h = it["value"] * k * p
        y0, y1 = (zero - h, zero) if h >= 0 else (zero, zero - h)
        color = it.get("color", "red" if i in spec.get("hl", []) else "blue")
        if abs(h) > 1:
            c.cv.fill_rect(cx - bw / 2, y0, cx + bw / 2, y1, color, 225, 1.0)
            c.cv.hatch(cx - bw / 2, y0, cx + bw / 2, y1, INK, 18, 46)
            c.cv.line([(cx - bw / 2, y0), (cx + bw / 2, y0), (cx + bw / 2, y1), (cx - bw / 2, y1), (cx - bw / 2, y0)], INK, 3, 0.9, pen=False)
        geo.append((cx, y0, y1, p))
    c.blit()
    for i, (it, (cx, y0, y1, p)) in enumerate(zip(items, geo)):
        st = 0.45 + 0.22 * i
        txt = it.get("text", f"{it['value']}")
        size = fit_size(txt, 52, slot * 0.95)
        vy = (y0 - 84) if it["value"] >= 0 else (y1 + 12)
        c.txt(txt, size, it.get("tcolor") or ("red" if i in spec.get("hl", []) else "ink"),
              cx, vy, st + 0.5, "c", glow=i in spec.get("hl", []) and t > st + 1.2)
        ly = (zero - 70) if neg_only else 736
        c.lines(it["label"], 34, INK, cx, ly if not neg_only else 214, st + 0.2, "c", heavy=False, gap=1.15)
    if spec.get("unit"):
        c.txt(spec["unit"], 32, FADE, LEFT, 176, 0.5, "l", heavy=False)
    c.footer()
    return c.done()


def card_hbars(spec, t, dur):
    c = Card(spec, t, dur)
    c.heading()
    items = spec["items"]
    n = len(items)
    vmax = spec.get("vmax", max(it["value"] for it in items))
    row = min(150 if n <= 3 else 112, 520 / n)
    y0 = 214
    x_bar, max_len = 640, 860
    geo = []
    for i, it in enumerate(items):
        p = prog(t, 0.4 + 0.25 * i, 0.9)
        y = y0 + i * row
        L = it["value"] / vmax * max_len * p
        color = it.get("color", "red" if i in spec.get("hl", []) else "blue")
        if L > 2:
            c.cv.fill_rect(x_bar, y + row * 0.16, x_bar + L, y + row * 0.76, color, 225, 1.0)
            c.cv.hatch(x_bar, y + row * 0.16, x_bar + L, y + row * 0.76, INK, 18, 46)
        geo.append((y, L))
    c.cv.line([(x_bar, y0 - 6), (x_bar, y0 + n * row)], INK, 4, 0.8)
    if spec.get("limit"):
        lx = x_bar + spec["limit"] / vmax * max_len
        c.cv.line([(lx, y0 - 14), (lx, y0 + n * row)], RED, 4, 1.0)
    c.blit()
    for i, (it, (y, L)) in enumerate(zip(items, geo)):
        st = 0.4 + 0.25 * i
        size = fit_size(it["label"], 44, 380)
        c.txt(it["label"], size, INK, x_bar - 30, y + row * 0.18, st, "r", heavy=True)
        if spec.get("inside"):
            c.txt(it.get("text", str(it["value"])), 50, PAPER, x_bar + L - 22, y + row * 0.2, st + 0.6, "r")
        else:
            c.txt(it.get("text", str(it["value"])), 46, "red" if i in spec.get("hl", []) else INK, x_bar + L + 20, y + row * 0.17,
                  st + 0.6, "l", glow=i in spec.get("hl", []) and t > st + 1.3)
    if spec.get("limit_label"):
        lx = x_bar + spec["limit"] / vmax * max_len
        c.txt(spec["limit_label"], 34, RED, lx, y0 + n * row + 8, 1.2, "c")
    c.footer()
    return c.done()


def card_line(spec, t, dur):
    c = Card(spec, t, dur)
    c.heading()
    L, R, T, B = 330, 1640, 250, 712
    series = spec["series"]
    xs_all = [x for s in series for x in s["x"]]
    xmin, xmax = spec.get("xlim", [min(xs_all), max(xs_all)])
    ymin, ymax = spec["ylim"]
    px = lambda x: L + (x - xmin) / (xmax - xmin) * (R - L)  # noqa: E731
    py = lambda y: B - (y - ymin) / (ymax - ymin) * (B - T)  # noqa: E731
    for yt in spec["yticks"]:
        c.cv.line([(L, py(yt)), (R, py(yt))], FADE, 2, 0.9, alpha=90, pen=False)
    c.cv.line([(L, B), (R, B)], INK, 4, 0.8)
    c.cv.line([(L, T - 10), (L, B)], INK, 3, 0.8)
    drawn = spec.get("draw", min(3.4, dur * 0.6))
    p = prog(t, 0.45, drawn, ease_in_out)
    front = xmin + (xmax - xmin) * p
    for s in series:
        pts = trunc(s["x"], s["y"], front)
        xy = [(px(x), py(y)) for x, y in pts]
        if len(xy) > 1 and s.get("fill"):
            c.cv.poly(xy + [(xy[-1][0], B), (xy[0][0], B)], s["color"], 30)
        c.cv.line(xy, s["color"], s.get("width", 6), 1.1)
        if xy and p < 0.999:
            c.cv.circle(xy[-1][0], xy[-1][1], 9, s["color"], 4, 0.5, 1.0)
    for a in spec.get("annot", []):
        ta = 0.45 + drawn * ((a["x"] - xmin) / (xmax - xmin))
        ap = prog(t, ta, 0.5)
        if ap > 0.02:
            x, y = px(a["x"]), py(a["y"])
            c.cv.circle(x, y, 11, a.get("color", "red"), 4, 0.5)
            if a.get("leader", True):
                c.cv.line([(x, y), (x + a.get("dx", 0), y + a.get("dy", -60) + (0 if a.get("dy", -60) > 0 else 8))], a.get("color", "red"), 3, 0.8)
    c.blit()
    for yt in spec["yticks"]:
        c.txt(spec.get("yfmt", "{:.1f}").format(yt), 30, FADE, L - 16, py(yt) - 20, 0.3, "r", heavy=False)
    for xt, lab in spec["xticks"]:
        c.txt(lab, 30, FADE, px(xt), B + 14, 0.3, "c", heavy=False)
    for a in spec.get("annot", []):
        ta = 0.45 + drawn * ((a["x"] - xmin) / (xmax - xmin))
        x, y = px(a["x"]), py(a["y"])
        size = a.get("size", 38)
        nl = len(a["text"].split("\n"))
        dy = a.get("dy", -60)
        top = y + dy - (nl - 1) * size * 1.32 - size * 1.5 if dy < 0 else y + dy + 12
        c.lines(a["text"], size, a.get("color", "red"), x + a.get("dx", 0), top, ta + 0.15, a.get("anchor", "c"),
                length=0.6, glow=bool(a.get("glow")) and t > ta + 0.9)
    for s in series:
        if s.get("label"):
            c.txt(s["label"], 34, s["color"], px(s["x"][-1]) if s.get("label_end") else R, py(s["y"][-1]) - 56 if not s.get("label_below") else py(s["y"][-1]) + 16,
                  0.45 + drawn, "r", length=0.5)
    c.footer()
    return c.done()


def card_curve(spec, t, dur):
    c = Card(spec, t, dur)
    c.heading()
    L, R, T, B = 330, 1620, 260, 690
    cats = spec["cats"]
    n = len(cats)
    ymin, ymax = spec["ylim"]
    px = lambda i: L + 40 + (R - L - 80) * i / (n - 1)  # noqa: E731
    py = lambda y: B - (y - ymin) / (ymax - ymin) * (B - T)  # noqa: E731
    for yt in spec["yticks"]:
        c.cv.line([(L, py(yt)), (R, py(yt))], FADE, 2, 0.9, alpha=90, pen=False)
    c.cv.line([(L, B), (R, B)], INK, 4, 0.8)
    plans = []
    for si, s in enumerate(spec["series"]):
        st = 0.4 + si * 1.9
        p = prog(t, st, 1.5, ease_in_out)
        k = p * (n - 1)
        pts = [(px(i), py(v)) for i, v in enumerate(s["values"]) if i <= k]
        if int(k) < n - 1 and pts:
            f = k - int(k)
            x0, y0 = pts[-1]
            x1, y1 = px(int(k) + 1), py(s["values"][int(k) + 1])
            pts.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
        c.cv.line(pts, s["color"], 7, 1.1)
        for i, v in enumerate(s["values"]):
            if i <= k + 0.01:
                c.cv.circle(px(i), py(v), 9, s["color"], 4, 0.4, 1.0)
        plans.append((s, st))
    c.blit()
    for yt in spec["yticks"]:
        c.txt(f"{yt:.0f}%", 30, FADE, L - 16, py(yt) - 20, 0.3, "r", heavy=False)
    for i, cat in enumerate(cats):
        c.txt(cat, 32, INK, px(i), B + 14, 0.3, "c", heavy=False)
    for s, st in plans:
        for i, v in enumerate(s["values"]):
            ta = st + 1.5 * (i / (n - 1))
            c.txt(f"{v:.2f}%", 30, s["color"], px(i), py(v) + (-52 if s.get("above", True) else 16), ta, "c", length=0.4)
    # 图例（放在标题行右侧）
    for j, (s, st) in enumerate(plans):
        c.txt("— " + s["name"], 38, s["color"], 1230 + j * 220, 92, st + 0.2, "l", length=0.5)
    c.footer()
    return c.done()


def card_stack(spec, t, dur):
    c = Card(spec, t, dur)
    c.heading()
    parts = spec["parts"]
    total = sum(p["value"] for p in parts)
    x0, x1, y0, y1 = LEFT + 20, RIGHT - 20, 360, 470
    segs, x = [], x0
    p_all = prog(t, 0.4, 1.8, ease_in_out)
    for i, pt in enumerate(parts):
        w = (x1 - x0) * pt["value"] / total
        segs.append((x, x + w))
        x += w
    reveal = x0 + (x1 - x0) * p_all
    for i, (pt, (a, b)) in enumerate(zip(parts, segs)):
        if reveal > a:
            e = min(b, reveal)
            color = pt.get("color", ["blue", "red", "green", "amber", "fade"][i % 5])
            c.cv.fill_rect(a, y0, e, y1, color, 225, 0.9)
            c.cv.hatch(a, y0, e, y1, INK, 18, 46)
            c.cv.line([(a, y0), (e, y0), (e, y1), (a, y1), (a, y0)], INK, 3, 0.8, pen=False)
    if spec.get("bracket"):
        c.cv.line([(x0, 505), (x0, 520), (x1, 520), (x1, 505)], FADE, 3, 0.8)
    c.blit()
    if spec.get("headline"):
        c.txt(spec["headline"], spec.get("hsize", 64), INK, 960, 214, 0.2, "c")
    rows = [0, 0]
    last_end = [-1e9, -1e9]
    for i, (pt, (a, b)) in enumerate(zip(parts, segs)):
        cx = (a + b) / 2
        r = 0 if cx - last_end[0] > 230 else (1 if cx - last_end[1] > 230 else 0)
        last_end[r] = cx
        ly = 500 + r * 150
        st = 0.9 + 0.4 * i
        color = pt.get("color", ["blue", "red", "green", "amber", "fade"][i % 5])
        c.txt(pt["text"], 58, color, cx, ly, st, "c", glow=bool(pt.get("hl")) and t > st + 0.8)
        c.lines(pt["label"], 34, INK, cx, ly + 70, st + 0.15, "c", heavy=False, gap=1.15)
    if spec.get("note"):
        c.lines(spec["note"], 40, INK, 960, 700, 2.4, "c", heavy=False)
    c.footer()
    return c.done()


def _box_text(c, x, y, w, h, text, sub, color, st):
    lines = text.split("\n")
    size = fit_size(max(lines, key=len), 56, w - 40)
    ty = y + h / 2 - len(lines) * size * 0.66 - (20 if sub else 0)
    c.lines(text, size, color, x + w / 2, ty, st + 0.2, "c", gap=1.25)
    if sub:
        c.lines(sub, 32, FADE, x + w / 2, ty + len(lines) * size * 1.3 + 8, st + 0.45, "c", heavy=False, gap=1.2)


def card_pflow(spec, t, dur):
    c = Card(spec, t, dur)
    c.heading()
    boxes = spec["boxes"]
    n = len(boxes)
    gap = 96
    bw = (RIGHT - LEFT - gap * (n - 1)) / n
    by, bh = spec.get("by", 280), spec.get("bh", 290)
    for i, b in enumerate(boxes):
        st = 0.4 + 0.75 * i
        p = prog(t, st, 0.8, ease_in_out)
        if p > 0.02:
            x = LEFT + i * (bw + gap)
            color = b.get("color", "blue")
            xe = x + bw * p
            c.cv.fill_rect(x, by, xe, by + bh, color, 26, 1.0)
            c.cv.rect(x, by, xe, by + bh, color, 5, 1.2, over=6 if p > 0.95 else 0)
        if i < n - 1:
            c.cv.arrow(LEFT + i * (bw + gap) + bw + 14, by + bh / 2, LEFT + (i + 1) * (bw + gap) - 14, by + bh / 2, RED, 6, prog(t, st + 0.55, 0.5))
    c.blit()
    for i, b in enumerate(boxes):
        st = 0.4 + 0.75 * i
        x = LEFT + i * (bw + gap)
        _box_text(c, x, by, bw, bh, b["text"], b.get("sub"), b.get("color", "blue"), st)
    if spec.get("note"):
        c.lines(spec["note"], 44, INK, 960, spec.get("ny", 640), 0.4 + 0.75 * n, "c", heavy=False)
    c.footer()
    return c.done()


def card_plist(spec, t, dur):
    c = Card(spec, t, dur)
    items = spec["items"]
    n = len(items)
    top = 214
    row = min(118, (800 - top) / n)
    size = 54 if n <= 5 else 46
    step = min(0.9, dur * 0.55 / max(n, 1))
    for i in range(n):
        st = 0.5 + i * step
        if prog(t, st, 0.5) > 0.02:
            c.cv.circle(LEFT + 44, top + i * row + row * 0.38, 34, RED, 5, 1.0)
    if spec.get("heading"):
        wh = G2.font(62, True).getlength(spec["heading"])
        ph_ = prog(t, 0.4, 0.8, ease_in_out)
        c.cv.line([(LEFT, 160), (LEFT + (wh + 8) * ph_, 157)], RED, 5, 1.3)
    c.blit()
    if spec.get("heading"):
        c.txt(spec["heading"], 62, INK, LEFT, 84, 0.1)
    for i, it in enumerate(items):
        st = 0.5 + i * step
        c.txt(str(it[0]), 40, RED, LEFT + 44, top + i * row + row * 0.38 - 28, st, "c")
        c.txt(it[1], size, INK, LEFT + 110, top + i * row + row * 0.38 - size * 0.62, st + 0.1)
        if len(it) > 2:
            c.txt(it[2], 30, FADE, RIGHT, top + i * row + row * 0.38 - 18, st + 0.3, "r", heavy=False)
    c.footer()
    return c.done()


def card_ptimeline(spec, t, dur):
    c = Card(spec, t, dur)
    c.heading()
    ev = spec["events"]
    n = len(ev)
    x0, x1, yl = 340, 1580, 470
    p = prog(t, 0.4, dur * 0.5, ease_in_out)
    c.cv.line([(x0 - 60, yl), (x0 - 60 + (x1 - x0 + 120) * p, yl)], INK, 5, 1.0)
    for i in range(n):
        x = x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5)
        if prog(t, 0.4 + dur * 0.5 * i / max(1, n - 1) * 0.95, 0.6) > 0.05:
            color = ev[i].get("color", "blue")
            c.cv.circle(x, yl, 18, color, 6, 0.8)
    c.blit()
    for i, e in enumerate(ev):
        x = x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5)
        st = 0.4 + dur * 0.5 * i / max(1, n - 1) * 0.95
        c.txt(e["date"], 52, e.get("color", "blue"), x, yl - 120, st, "c", glow=bool(e.get("hl")) and t > st + 0.8)
        c.lines(e["label"], 38, INK, x, yl + 50, st + 0.2, "c", gap=1.3)
    c.footer()
    return c.done()


def card_pquote(spec, t, dur):
    c = Card(spec, t, dur)
    size = spec.get("size", 62)
    f = G2.font(size, True)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = wrap(d, spec["quote"], f, 1240)
    y0 = 290
    lh = size * 1.45
    hs = spec.get("highlight", [])
    for i, ln in enumerate(lines):
        for h in hs:
            k = ln.find(h)
            if k >= 0:
                xa = 960 - f.getlength(ln) / 2 + f.getlength(ln[:k])
                c.cv.marker(xa - 6, y0 + i * lh + 8, xa + f.getlength(h) + 6, y0 + i * lh + size * 1.18,
                            prog(t, 1.2 + 0.4 * i, 0.7, ease_in_out))
    c.blit()
    c.txt(spec["label"], 40, RED, LEFT, 92, 0.1)
    c.txt("「", 160, RED, LEFT - 14, 160, 0.2)
    for i, ln in enumerate(lines):
        c.txt(ln, size, INK, 960, y0 + i * lh, 0.5 + 0.45 * i, "c", length=0.8)
    if spec.get("note"):
        c.txt(spec["note"], 44, BLUE, 960, y0 + len(lines) * lh + 36, 0.5 + 0.45 * len(lines), "c")
    c.footer()
    return c.done()


DRAW = {
    "counter": card_counter, "compare": card_compare, "bars": card_bars, "hbars": card_hbars, "line": card_line,
    "curve": card_curve, "stack": card_stack, "pflow": card_pflow, "plist": card_plist, "ptimeline": card_ptimeline,
    "pquote": card_pquote,
}
G2.DRAW.update(DRAW)
