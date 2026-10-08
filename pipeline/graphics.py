"""动态图表与文字卡渲染器（Pillow 逐帧绘制 → ffmpeg 编码）。

每种卡片是一个函数 draw_<type>(spec, t, dur) -> PIL.Image，t 为当前秒数。
render_clip(spec, dur, out_mp4) 负责逐帧调用并编码。
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FONT_BOLD, FONT_HEAVY  # noqa: E402

W, H, FPS = 1920, 1080, 30
SAFE_BOTTOM = 860  # 以下留给字幕，图表内容不得越过
NAVY = (11, 20, 38)
GOLD = (242, 183, 5)
YELLOW = (255, 214, 0)
RED = (225, 30, 40)
GREEN = (46, 204, 113)
WHITE = (255, 255, 255)
GRAY = (138, 151, 173)
DIM = (60, 72, 96)

_font_cache = {}


def font(size, heavy=False):
    key = (size, heavy)
    if key not in _font_cache:
        from PIL import ImageFont
        _font_cache[key] = ImageFont.truetype(FONT_HEAVY if heavy else FONT_BOLD, size)
    return _font_cache[key]


# ---------- 基础工具 ----------

def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def prog(t, start, length):
    return ease((t - start) / length) if length > 0 else float(t >= start)


def blend(c, a):
    """把颜色和背景按 alpha 混合（用于淡入）。"""
    return tuple(int(NAVY[i] + (c[i] - NAVY[i]) * a) for i in range(3))


_bg = None


def background():
    global _bg
    if _bg is None:
        img = Image.new("RGB", (W, H), NAVY)
        glow = Image.new("RGB", (W, H), (0, 0, 0))
        g = ImageDraw.Draw(glow)
        g.ellipse([W * 0.15, -H * 0.4, W * 0.85, H * 0.7], fill=(40, 52, 80))
        glow = glow.filter(ImageFilter.GaussianBlur(220))
        img = Image.blend(img, glow, 0.55)
        vign = Image.new("L", (W, H), 0)
        ImageDraw.Draw(vign).ellipse([-W * 0.2, -H * 0.3, W * 1.2, H * 1.3], fill=255)
        vign = vign.filter(ImageFilter.GaussianBlur(160))
        img = Image.composite(img, Image.new("RGB", (W, H), (5, 9, 18)), vign)
        _bg = img
    return _bg.copy()


def text_w(d, s, f):
    l, _, r, _ = d.textbbox((0, 0), s, font=f)
    return r - l


def draw_center(d, y, s, f, fill, cx=W // 2):
    l, t, r, b = d.textbbox((0, 0), s, font=f)
    d.text((cx - (r - l) / 2 - l, y - t), s, font=f, fill=fill)


def wrap(d, s, f, max_w):
    """中文按字宽换行，尽量在标点后断行。"""
    lines, cur = [], ""
    for ch in s:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if text_w(d, cur + ch, f) > max_w and cur:
            cut = max((cur.rfind(p) for p in "，。；：、？！」"), default=-1)
            if cut >= len(cur) * 0.5:
                lines.append(cur[: cut + 1])
                cur = cur[cut + 1:] + ch
            else:
                lines.append(cur)
                cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    # 避头：行首的标点挪回上一行
    for i in range(1, len(lines)):
        while lines[i] and lines[i][0] in "，。；：、？！」）》〉":
            lines[i - 1] += lines[i][0]
            lines[i] = lines[i][1:]
    return [l for l in lines if l]


def source_line(d, s, a=1.0):
    if s:
        d.text((90, H - 58), s, font=font(26), fill=blend(GRAY, a))


# ---------- 各类卡片 ----------

def draw_title(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    a_in = prog(t, 0.1, 0.6)
    a_out = 1 - prog(t, dur - 0.5, 0.45)
    a = a_in * a_out
    kicker, title = spec["text"].split("\n", 1)
    draw_center(d, 380, kicker, font(64), blend(GOLD, a))
    lw = int(360 * prog(t, 0.3, 0.8))
    d.rectangle([W // 2 - lw // 2, 480, W // 2 + lw // 2, 486], fill=blend(GOLD, a))
    draw_center(d, 530, title, font(118, True), blend(WHITE, a))
    return img


def draw_quote(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    f = font(spec.get("size", 76), True)
    lines = wrap(d, spec["quote"], f, W - 420)
    lh = int(f.size * 1.45)
    top = (H - lh * len(lines)) // 2 - 30
    qa = prog(t, 0.0, 0.5)
    bar_h = int((lh * len(lines) - (lh - f.size)) * qa)
    d.rectangle([160, top + 6, 170, top + 6 + bar_h], fill=GOLD)  # 左侧金色引用竖线
    hi = spec.get("highlight", [])
    for i, line in enumerate(lines):
        a = prog(t, 0.25 + i * 0.35, 0.5)
        y = top + i * lh + int((1 - a) * 18)
        x = 210
        # 逐段着色：命中 highlight 的词用金色
        segs, rest = [], line
        while rest:
            pos = [(rest.find(h), h) for h in hi if rest.find(h) >= 0]
            if not pos:
                segs.append((rest, WHITE))
                break
            p, h = min(pos)
            if p:
                segs.append((rest[:p], WHITE))
            segs.append((h, YELLOW))
            rest = rest[p + len(h):]
        for s, c in segs:
            d.text((x, y), s, font=f, fill=blend(c, a))
            x += text_w(d, s, f)
    sa = prog(t, 0.4 + len(lines) * 0.35, 0.6)
    if spec.get("author"):
        d.text((210, top + len(lines) * lh + 40), "—— " + spec["author"], font=font(44), fill=blend(GOLD, sa))
    source_line(d, spec.get("source"), sa)
    return img


def draw_bullets(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    items = spec["items"]
    heading = spec.get("heading")
    y = 250 if heading else 300
    if heading:
        draw_center(d, 150, heading, font(70, True), blend(GOLD, prog(t, 0, 0.5)))
    instant = spec.get("instant", 0)  # 前 n 条直接显示（承接上一张卡）
    step = (dur * 0.6) / max(1, len(items) - instant)
    gap = min(180, (SAFE_BOTTOM - y - 96) // max(1, len(items) - 1))
    for i, it in enumerate(items):
        a = 1.0 if i < instant else prog(t, 0.3 + (i - instant) * step, 0.5)
        yy = y + i * gap + int((1 - a) * 20)
        num, text = it if isinstance(it, (list, tuple)) else (None, it)
        x = 300
        if num:
            d.rounded_rectangle([x, yy, x + 96, yy + 96], 18, fill=blend(RED if spec.get("red") else GOLD, a))
            draw_center(d, yy + 10, num, font(64, True), blend(NAVY if not spec.get("red") else WHITE, a), cx=x + 48)
            x += 140
        else:
            d.ellipse([x + 30, yy + 34, x + 58, yy + 62], fill=blend(GOLD, a))
            x += 90
        d.text((x, yy + 8), text, font=font(66, True), fill=blend(WHITE, a))
    source_line(d, spec.get("source"), prog(t, 0.5, 0.5))
    return img


def draw_statement(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    lines = spec["lines"]
    total_h = sum(int(l.get("size", 120) * 1.35) for l in lines)
    y = (H - total_h) // 2
    for i, l in enumerate(lines):
        size = l.get("size", 120)
        a = prog(t, 0.2 + i * l.get("delay", 0.7), 0.5)
        c = {"y": YELLOW, "r": RED, "g": GOLD, "w": WHITE, "gray": GRAY}[l.get("color", "w")]
        draw_center(d, y + int((1 - a) * 20), l["text"], font(size, True), blend(c, a))
        y += int(size * 1.35)
    source_line(d, spec.get("source"), prog(t, 0.5, 0.5))
    return img


def draw_donut(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    cx, cy, r, th = 640, 560, 300, 110
    segs = spec["segments"]
    p = prog(t, 0.2, 1.6)
    start = -90.0
    for s in segs:
        sweep = 360 * s["pct"] / 100 * p
        color = {"g": GOLD, "y": YELLOW, "r": RED, "gray": GRAY, "green": GREEN}[s["color"]]
        if sweep > 0.5:
            d.pieslice([cx - r, cy - r, cx + r, cy + r], start, start + sweep, fill=color)
        start += 360 * s["pct"] / 100
    d.ellipse([cx - r + th, cy - r + th, cx + r - th, cy + r - th], fill=NAVY)
    if spec.get("center"):
        draw_center(d, cy - 40, spec["center"], font(64, True), blend(WHITE, prog(t, 0.6, 0.6)), cx=cx)
    y = 380
    for i, s in enumerate(segs):
        a = prog(t, 0.8 + i * 0.5, 0.5)
        color = {"g": GOLD, "y": YELLOW, "r": RED, "gray": GRAY, "green": GREEN}[s["color"]]
        d.rounded_rectangle([1080, y + 18, 1130, y + 68], 10, fill=blend(color, a))
        d.text((1160, y), f"{s['pct']}%", font=font(96, True), fill=blend(color, a))
        d.text((1160, y + 120), s["label"], font=font(50, True), fill=blend(WHITE, a))
        y += 280
    if spec.get("note"):
        draw_center(d, 165, spec["note"], font(40, True), blend(YELLOW, prog(t, 2.0, 0.6)))
    if spec.get("title"):
        draw_center(d, 90, spec["title"], font(60, True), blend(GOLD, prog(t, 0, 0.5)))
    source_line(d, spec.get("source"), prog(t, 0.5, 0.5))
    return img


def draw_bars(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    if spec.get("title"):
        draw_center(d, 70, spec["title"], font(62, True), blend(GOLD, prog(t, 0, 0.5)))
    bars = spec["bars"]
    vals = [b["value"] for b in bars]
    vmax, vmin = max(0, max(vals)), min(0, min(vals))
    top, bottom = 230, 740
    zero = top + (bottom - top) * vmax / (vmax - vmin) if vmax != vmin else bottom
    scale = (bottom - top) / (vmax - vmin)
    n = len(bars)
    slot = (W - 360) / n
    bw = min(170, slot * 0.6)
    d.line([180, zero, W - 180, zero], fill=DIM, width=3)
    for i, b in enumerate(bars):
        p = prog(t, 0.3 + i * spec.get("stagger", 0.15), 1.2)
        x0 = 180 + slot * i + (slot - bw) / 2
        h = b["value"] * scale * p
        color = {"g": GOLD, "y": YELLOW, "r": RED, "gray": GRAY, "green": GREEN, "dim": DIM}[b.get("color", "gray")]
        y0, y1 = (zero - h, zero) if h >= 0 else (zero, zero - h)
        if abs(h) > 1:
            d.rectangle([x0, y0, x0 + bw, y1], fill=color)
        fmt = b.get("fmt", "{:+.1f}%")
        label = fmt.format(b["value"] * p if spec.get("count", True) else b["value"])
        ly = y0 - 70 if h >= 0 else y1 + 14
        draw_center(d, ly, label, font(48, True), blend(WHITE, min(1, p * 1.5)), cx=x0 + bw / 2)
        name_y = zero - 70 if vmax <= 0 else bottom + 18  # 全为负值时名称放在零轴上方
        draw_center(d, name_y, b["label"], font(40, True), blend(color if b.get("color") in ("g", "y") else WHITE, prog(t, 0.2, 0.5)), cx=x0 + bw / 2)
    if spec.get("note"):
        draw_center(d, 832, spec["note"], font(46, True), blend(YELLOW, prog(t, 1.6, 0.6)))
    source_line(d, spec.get("source"), prog(t, 0.5, 0.5))
    return img


def spread_labels(items, min_gap=44):
    """items: [(y, ...)]，按 y 排序后保证相邻标签间距不小于 min_gap。"""
    items = sorted(items, key=lambda it: it[0])
    for i in range(1, len(items)):
        if items[i][0] - items[i - 1][0] < min_gap:
            items[i] = (items[i - 1][0] + min_gap,) + tuple(items[i][1:])
    return items


def draw_lines(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    if spec.get("title"):
        draw_center(d, 60, spec["title"], font(58, True), blend(GOLD, prog(t, 0, 0.5)))
    xs = spec["x"]
    series = spec["series"]
    allv = [v for s in series for v in s["values"] if v is not None]
    vmin, vmax = min(allv + [spec.get("ymin", min(allv))]), max(allv)
    L, R, T, B = 230, 1560, 190, 740
    def px(i):
        return L + (R - L) * i / (len(xs) - 1)
    def py(v):
        return B - (B - T) * (v - vmin) / (vmax - vmin)
    for gv in spec.get("grid", []):
        d.line([L, py(gv), R, py(gv)], fill=DIM, width=2)
        d.text((L - 150, py(gv) - 24), spec.get("yfmt", "{}").format(gv), font=font(36), fill=GRAY)
    for i, x in enumerate(xs):
        if i % spec.get("xstep", 1) == 0:
            draw_center(d, B + 24, str(x), font(36), GRAY, cx=px(i))
    p = prog(t, 0.3, dur * 0.65)
    upto = p * (len(xs) - 1)
    labels = []
    for s in series:
        color = {"g": GOLD, "y": YELLOW, "r": RED, "gray": GRAY, "green": GREEN}[s.get("color", "gray")]
        width = 9 if s.get("bold") else 4
        pts = []
        for i, v in enumerate(s["values"]):
            if v is None:
                break
            if i <= upto:
                pts.append((px(i), py(v)))
            else:
                prev = s["values"][i - 1]
                frac = upto - (i - 1)
                if frac > 0:
                    pts.append((px(i - 1) + (px(i) - px(i - 1)) * frac, py(prev + (v - prev) * frac)))
                break
        if len(pts) > 1:
            d.line(pts, fill=color, width=width, joint="curve")
        if pts:
            ex, ey = pts[-1]
            d.ellipse([ex - width, ey - width, ex + width, ey + width], fill=color)
            if p >= 0.999 or s.get("bold"):
                cur = s["values"][min(len(s["values"]) - 1, int(upto))]
                lab = s["label"] + (f"  {spec.get('endfmt', '{:.0f}').format(cur)}" if cur is not None else "")
                labels.append((ey - 26, ex + 22, lab, 36 if not s.get("bold") else 44, color))
    for y, x, lab, size, color in spread_labels(labels):
        d.text((x, y), lab, font=font(size, True), fill=color)
    if spec.get("note"):
        draw_center(d, 815, spec["note"], font(46, True), blend(YELLOW, prog(t, dur * 0.75, 0.6)))
    source_line(d, spec.get("source"), prog(t, 0.5, 0.5))
    return img


def draw_counter(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    if spec.get("title"):
        draw_center(d, 120, spec["title"], font(60, True), blend(GOLD, prog(t, 0, 0.5)))
    p = prog(t, spec.get("start", 0.6), spec.get("length", dur * 0.6))
    a, b = spec["from"], spec["to"]
    if spec.get("geometric") and a > 0 and b > 0:
        v = a * (b / a) ** p
    else:
        v = a + (b - a) * p
    draw_center(d, 250, spec.get("left", ""), font(52, True), blend(GRAY, prog(t, 0.2, 0.5)))
    draw_center(d, 360, spec["fmt"].format(v), font(190, True), blend(YELLOW if p > 0.98 else WHITE, prog(t, 0.2, 0.5)))
    draw_center(d, 640, spec.get("right", ""), font(52, True), blend(GRAY, prog(t, 0.2, 0.5)))
    if spec.get("note"):
        draw_center(d, 800, spec["note"], font(64, True), blend(GOLD, prog(t, spec.get("start", 0.6) + spec.get("length", dur * 0.6), 0.6)))
    source_line(d, spec.get("source"), prog(t, 0.5, 0.5))
    return img


def draw_grid(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    cols, rows = 25, 20
    cell, gap = 28, 7
    gw = cols * (cell + gap)
    x0, y0 = (W - gw) // 2 + 380, 150
    swap = spec.get("swap", False)
    p = prog(t, 0.2, 2.2)
    shown = int(cols * rows * p)
    out_set = {13, 77, 151, 240, 333, 402, 488} if swap else set()
    sp = prog(t, 1.0, 1.5) if swap else 0
    for i in range(cols * rows):
        if i >= shown and not swap:
            break
        r, c = divmod(i, cols)
        x, y = x0 + c * (cell + gap), y0 + r * (cell + gap)
        color = GOLD if i < 10 else (110, 128, 160)
        if i in out_set:
            if sp < 0.5:
                color = RED
            else:
                color = GREEN
        d.rounded_rectangle([x, y, x + cell, y + cell], 6, fill=color)
    tx = 150
    d.text((tx, 300), "標普500", font=font(96, True), fill=blend(WHITE, prog(t, 0.2, 0.5)))
    d.text((tx, 440), "500家美國大型公司", font=font(48, True), fill=blend(GOLD, prog(t, 0.5, 0.5)))
    if swap:
        d.text((tx, 580), "■ 移出", font=font(46, True), fill=blend(RED, prog(t, 0.8, 0.5)))
        d.text((tx, 660), "■ 加入", font=font(46, True), fill=blend(GREEN, prog(t, 1.6, 0.5)))
        d.text((tx, 780), "定期調整・汰弱留強", font=font(46, True), fill=blend(WHITE, prog(t, 2.2, 0.5)))
    else:
        d.text((tx, 580), "買一支指數基金", font=font(46, True), fill=blend(WHITE, prog(t, 1.2, 0.5)))
        d.text((tx, 650), "＝ 同時擁有全部", font=font(46, True), fill=blend(WHITE, prog(t, 1.6, 0.5)))
    source_line(d, spec.get("source"), prog(t, 0.5, 0.5))
    return img


def draw_versus(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    a1, a2, a3 = prog(t, 0.2, 0.6), prog(t, 0.9, 0.6), prog(t, 1.6, 0.6)
    L, R = spec["left"], spec["right"]
    draw_center(d, 300, L[0], font(150, True), blend(WHITE, a1), cx=520)
    draw_center(d, 500, L[1], font(52, True), blend(GRAY, a1), cx=520)
    draw_center(d, 360, "VS", font(120, True), blend(RED, a2))
    draw_center(d, 300, R[0], font(150, True), blend(YELLOW, a3), cx=1400)
    draw_center(d, 500, R[1], font(52, True), blend(GRAY, a3), cx=1400)
    if spec.get("note"):
        draw_center(d, 760, spec["note"], font(56, True), blend(GOLD, prog(t, 2.4, 0.6)))
    return img


def draw_price_path(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    pts = spec["points"]  # [(label, price)]
    L, R, T, B = 260, 1660, 240, 740
    vmax = max(p for _, p in pts) * 1.05
    def py(v):
        return B - (B - T) * v / vmax
    xs = [L + (R - L) * i / (len(pts) - 1) for i in range(len(pts))]
    p = prog(t, 0.3, dur * 0.6) * (len(pts) - 1)
    line = []
    for i, (_, v) in enumerate(pts):
        if i <= p:
            line.append((xs[i], py(v)))
        elif i - 1 < p:
            f = p - (i - 1)
            pv = pts[i - 1][1]
            line.append((xs[i - 1] + (xs[i] - xs[i - 1]) * f, py(pv + (v - pv) * f)))
    if len(line) > 1:
        d.line(line, fill=GOLD, width=8, joint="curve")
    for i, (lab, v) in enumerate(pts):
        if i <= p + 0.01:
            c = RED if spec.get("mark") == i else WHITE
            d.ellipse([xs[i] - 14, py(v) - 14, xs[i] + 14, py(v) + 14], fill=c)
            d.text((xs[i] - 60, py(v) - 120 if v > vmax * 0.5 else py(v) + 30), f"${v:g}", font=font(52, True), fill=c)
            draw_center(d, B + 40, lab, font(40, True), GRAY, cx=xs[i])
    if spec.get("title"):
        draw_center(d, 80, spec["title"], font(58, True), blend(GOLD, prog(t, 0, 0.5)))
    source_line(d, spec.get("source"), prog(t, 0.5, 0.5))
    return img


def draw_brand(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    a = prog(t, 0.2, 0.7) * (1 - prog(t, dur - 0.6, 0.5))
    lw = int(700 * prog(t, 0.4, 1.0))
    d.rectangle([W // 2 - lw // 2, 610, W // 2 + lw // 2, 616], fill=blend(GOLD, a))
    draw_center(d, 420, spec.get("text", "資產增長計劃"), font(150, True), blend(WHITE, a))
    if spec.get("sub"):
        draw_center(d, 660, spec["sub"], font(52, True), blend(GOLD, prog(t, 0.9, 0.6) * (1 - prog(t, dur - 0.6, 0.5))))
    return img


def draw_endcard(spec, t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    a = prog(t, 0.2, 0.7)
    draw_center(d, 300, "資產增長計劃", font(140, True), blend(WHITE, a))
    d.rectangle([W // 2 - 350, 490, W // 2 + 350, 496], fill=blend(GOLD, a))
    bw = 520
    ba = prog(t, 0.8, 0.6)
    d.rounded_rectangle([W // 2 - bw // 2, 560, W // 2 + bw // 2, 680], 24, fill=blend(RED, ba))
    draw_center(d, 582, "訂閱頻道", font(68, True), blend(WHITE, ba))
    draw_center(d, 860, "本影片內容僅供教育參考，不構成任何投資建議。", font(40), blend(GRAY, prog(t, 1.2, 0.6)))
    return img


DRAW = {
    "title": draw_title, "quote": draw_quote, "bullets": draw_bullets, "statement": draw_statement,
    "donut": draw_donut, "bars": draw_bars, "lines": draw_lines, "counter": draw_counter,
    "grid": draw_grid, "versus": draw_versus, "price_path": draw_price_path,
    "brand": draw_brand, "endcard": draw_endcard,
}


def render_clip(spec, dur, out_mp4, preview_png=None, frames=None):
    fn = DRAW[spec["type"]]
    n = frames or max(1, round(dur * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
           "-pix_fmt", "yuv420p", out_mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        frame = fn(spec, i / FPS, dur)
        proc.stdin.write(frame.tobytes())
        if preview_png and i == min(n - 1, int(n * 0.85)):
            frame.save(preview_png)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg 编码失败: {out_mp4}")
