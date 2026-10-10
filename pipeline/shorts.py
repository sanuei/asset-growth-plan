"""从已完成的长视频里剪出竖屏 Shorts（1080×1920）。不重新配音，不调用任何付费服务。

用法: .venv/bin/python pipeline/shorts.py videos/EP001_xxx S01 [S02 …] [--preview 秒]

输入: <episode>/08_Shorts/shorts.json（每条 Shorts 的段落范围、钩子文字、画面）
      长视频成片的音轨（人声+配乐）、配音分段（用来重新对齐字幕）
输出: <episode>/08_Shorts/<id>.mp4

画面版式（9:16）：上方钩子大字；中间 1080×1080 画面（场景图缓慢推拉，或为竖屏重新排版的图表）；
下方大字幕（描边+投影，位置避开 Shorts 界面遮挡）；最后 1.8 秒出现订阅提示。
字幕用 pipeline/v2.py 的停顿对齐，所以比 EP001 长视频里的字幕更准。
"""
import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import assemble as A  # noqa: E402
import v2  # noqa: E402
from config import FONT_BOLD, FONT_HEAVY  # noqa: E402

W, H, FPS = 1080, 1920, 30
WIN_Y, WIN = 430, 1080          # 画面窗口：y=430，1080×1080
CAP_Y = 1345                    # 字幕垂直中心
CAP_MAX_W, CAP_CHARS = 980, 12
GOLD, WHITE, MUTED, RED = (232, 190, 92), (255, 255, 255), (170, 178, 195), (214, 72, 72)
NAVY = (14, 22, 40)
FADE = 0.35


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 4


def prog(t, start, dur):
    return min(max((t - start) / dur, 0.0), 1.0)


@lru_cache(maxsize=None)
def font(size, heavy=True):
    return ImageFont.truetype(FONT_HEAVY if heavy else FONT_BOLD, size)


def text_img(s, size, fill, heavy=True, stroke=0, shadow=False, spacing=0):
    """回传 (RGBA 图, 内边距)。"""
    f = font(size, heavy)
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    w = int(sum(d.textlength(c, font=f) for c in s) + spacing * max(len(s) - 1, 0))
    pad = stroke + (14 if shadow else 4)
    img = Image.new("RGBA", (w + pad * 2, int(size * 1.5) + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        x = pad
        for c in s:
            sd.text((x + 3, pad + size * 0.75 + 4), c, font=f, fill=(0, 0, 0, 170), anchor="ls", stroke_width=stroke)
            x += d.textlength(c, font=f) + spacing
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
    x = pad
    for c in s:
        d.text((x, pad + size * 0.75), c, font=f, fill=fill + (255,), anchor="ls",
               stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
        x += d.textlength(c, font=f) + spacing
    return img, pad


def fit_size(s, size, max_w, heavy=True):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    while size > 30 and d.textlength(s, font=font(size, heavy)) > max_w:
        size -= 2
    return size


def paste_center(canvas, layer, pad, cx, cy, alpha=1.0):
    if alpha <= 0:
        return
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.split()[3].point(lambda v: int(v * alpha)))
    canvas.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


# ---------- 背景与画面窗口 ----------

def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    l, t = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((l, t, l + w, t + h))


def make_bg(img):
    bg = cover(img.convert("RGB"), W, H).filter(ImageFilter.GaussianBlur(46))
    arr = np.asarray(bg, np.float32) * 0.34 + np.array(NAVY, np.float32) * 0.3
    yy = np.linspace(-1, 1, H)[:, None]
    xx = np.linspace(-1, 1, W)[None, :]
    arr *= (1 - 0.35 * np.clip(xx ** 2 + yy ** 2 - 0.2, 0, 1))[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def plain_bg():
    return make_bg(Image.new("RGB", (64, 64), NAVY))


@lru_cache(maxsize=None)
def window_mask():
    m = Image.new("L", (WIN * 2, WIN * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, WIN * 2 - 1, WIN * 2 - 1], 72, fill=255)
    return m.resize((WIN, WIN), Image.LANCZOS)


def scene_window(img, fx, t, dur, mode):
    """Ken Burns：从中心窗口方形取景，缓慢推近或拉远。"""
    p = ease_out(t / max(dur, 0.1)) * 0.6 + (t / max(dur, 0.1)) * 0.4
    zoom = 1.0 + 0.10 * (p if mode == "in" else 1 - p)
    side = img.height / zoom
    cx = fx * img.width
    x0 = min(max(cx - side / 2, 0), img.width - side)
    y0 = (img.height - side) / 2
    k = side / WIN
    return img.transform((WIN, WIN), Image.AFFINE, (k, 0, x0, 0, k, y0), resample=Image.BICUBIC)


# ---------- 竖屏图表卡片 ----------

def panel():
    arr = np.zeros((WIN, WIN, 3), np.float32) + np.array(NAVY, np.float32)
    arr += (26 * (1 - np.linspace(0, 1, WIN)))[:, None, None]  # 轻微上亮下暗
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


def card_quote(spec, t):
    fr = panel()
    segs = spec["lines"]
    gold = set(spec.get("highlight", []))
    y = 120
    for i, line in enumerate(segs):
        a = ease_out(prog(t, 0.25 + 0.55 * i, 0.55))
        x = 96
        for part in line:
            hi = part in gold
            layer, pad = text_img(part, 88, GOLD if hi else WHITE)
            if a > 0:
                lay = layer.copy()
                lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
                fr.alpha_composite(lay, (int(x - pad), int(y - pad + (1 - a) * 22)))
            d = ImageDraw.Draw(Image.new("L", (1, 1)))
            x += d.textlength(part, font=font(88))
        y += 135
    bar = Image.new("RGBA", (10, int(120 * len(segs) + 10)), GOLD + (255,))
    fr.alpha_composite(bar.crop((0, 0, 10, int(bar.height * ease_out(prog(t, 0.1, 1.2))))), (60, 125))
    src, sp = text_img(spec["source"], 38, MUTED, heavy=False)
    lay = src.copy()
    lay.putalpha(lay.split()[3].point(lambda v: int(v * ease_out(prog(t, 3.0, 0.8)))))
    fr.alpha_composite(lay, (int(96 - sp), 990))
    return fr


def card_donut(spec, t):
    fr = panel()
    big = 3
    R, th = 270, 96
    cx, cy = WIN // 2, 350
    ring = Image.new("RGBA", (WIN * big, 620 * big), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    box = [(cx - R) * big, (cy - R - 70) * big, (cx + R) * big, (cy + R - 70) * big]
    d.ellipse(box, outline=(60, 70, 92, 255), width=th * big)
    ang = -90
    sweep = ease_out(prog(t, 0.2, 1.6))
    for seg in spec["segments"]:
        span = 360 * seg["pct"] / 100 * sweep
        col = GOLD if seg["color"] == "g" else (130, 140, 160)
        if span > 0.5:
            d.arc(box, ang, ang + span - 1.5, fill=col + (255,), width=th * big)
        ang += 360 * seg["pct"] / 100
    fr.alpha_composite(ring.resize((WIN, 620), Image.LANCZOS), (0, 0))
    main = spec["segments"][0]
    num, pad = text_img(f"{main['pct']}%", 150, WHITE)
    paste_center(fr, num, pad, cx, cy - 70, ease_out(prog(t, 0.8, 0.8)))
    y = 630
    for i, seg in enumerate(spec["segments"]):
        a = ease_out(prog(t, 1.2 + 0.5 * i, 0.6))
        col = GOLD if seg["color"] == "g" else (130, 140, 160)
        dot = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
        ImageDraw.Draw(dot).ellipse([4, 4, 46, 46], fill=col + (int(255 * a),))
        fr.alpha_composite(dot, (110, y + 12))
        lab, lp = text_img(f"{seg['pct']}%　{seg['label']}", 52, WHITE, heavy=False)
        paste_center(fr, lab, lp, 190 + lab.width / 2 - lp, y + 38, a)
        y += 100
    return fr


def card_bars(spec, t):
    fr = panel()
    title, tp = text_img(spec["title"], fit_size(spec["title"], 50, 960), WHITE, heavy=False)
    paste_center(fr, title, tp, WIN / 2, 100, ease_out(prog(t, 0.1, 0.6)))
    base, maxh, bw = 640, 400, 300
    maxv = max(b["value"] for b in spec["bars"])
    n = len(spec["bars"])
    xs = [WIN / 2] if n == 1 else [WIN / 2 - 230, WIN / 2 + 230]
    d = ImageDraw.Draw(fr)
    d.line([(100, base), (WIN - 100, base)], fill=(90, 100, 124, 255), width=4)
    for b, cx in zip(spec["bars"], xs):
        g = 1.0 if b.get("pre") else ease_out(prog(t, b.get("delay", 0.3), 1.3))
        h = maxh * b["value"] / maxv * g
        col = GOLD if b["color"] == "g" else RED
        if h > 1:
            d.rounded_rectangle([cx - bw / 2, base - h, cx + bw / 2, base], 18, fill=col + (255,))
            val, vp = text_img(b["final"] if g >= 0.999 else b["fmt"].format(b["value"] * g), 50, WHITE)
            paste_center(fr, val, vp, cx, base - h - 48)
        lab, lp = text_img(b["label"], 52, WHITE, heavy=False)
        paste_center(fr, lab, lp, cx, base + 60)
    if spec.get("note"):
        nt, npad = text_img(spec["note"], 60, GOLD)
        paste_center(fr, nt, npad, WIN / 2, 785, ease_out(prog(t, spec.get("note_at", 2.6), 0.8)))
    src, sp = text_img(spec["source"], 34, MUTED, heavy=False)
    paste_center(fr, src, sp, WIN / 2, 1035, 0.9)
    return fr


CARDS = {"quote": card_quote, "donut": card_donut, "bars": card_bars}


# ---------- 文字层 ----------

def hook_layer(lines):
    layer = Image.new("RGBA", (W, 400), (0, 0, 0, 0))
    brand, bp = text_img("資產增長計劃", 38, GOLD, spacing=8)
    layer.alpha_composite(brand, (int(W / 2 - brand.width / 2), 40))
    y = 150
    for i, s in enumerate(lines):
        size = fit_size(s, 88, 960)
        img, pad = text_img(s, size, WHITE if i == 0 else GOLD, stroke=4, shadow=True)
        layer.alpha_composite(img, (int(W / 2 - img.width / 2), int(y - pad)))
        y += 112
    return layer


@lru_cache(maxsize=None)
def caption_img(s):
    size = fit_size(s, 78, CAP_MAX_W, heavy=False)
    return text_img(s, size, WHITE, heavy=False, stroke=7, shadow=True)


def cta_layer():
    s = "訂閱「資產增長計劃」，每天學一點"
    img, pad = text_img(s, fit_size(s, 46, 940), WHITE, heavy=False, shadow=True)
    pill = Image.new("RGBA", (img.width + 80, 100), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle([0, 0, pill.width - 1, 99], 50, fill=RED + (235,))
    pill.alpha_composite(img, (40, int(50 - img.height / 2)))
    return pill


def fix_numbers(events):
    """字幕不要把数字和后面的单位切开（例如「10」「月6日」→「」「10月6日」）。"""
    for i in range(len(events) - 1):
        a, b = events[i], events[i + 1]
        m = re.search(r"[\d.]+$", a[2])
        if m and m.start() > 0 and b[2] and not re.match(r"[\d\s，。、？！]", b[2][0]):
            digits = m.group()
            a[2], b[2] = a[2][:m.start()].rstrip(), digits + b[2]
            shift = min(0.12 * len(digits), (a[1] - a[0]) * 0.4)
            b[0] = max(a[0] + 0.3, b[0] - shift)
            a[1] = min(a[1], b[0])
    return events

# ---------- 主流程 ----------

def load_scenes(ep, spec, vis, c0, c1):
    """把长视频时间轴里落在范围内的画面，换成竖屏版画面。"""
    sdir = os.path.join(ep, "03_画面素材/场景图")
    out = []
    for v in vis:
        a, b = max(v["start"], c0), min(v["start"] + v["dur"], c1)
        if b - a < 0.25 or v["id"] not in spec["visuals"]:
            continue
        cfg = spec["visuals"][v["id"]]
        item = {"start": a - c0, "end": b - c0, "cfg": cfg}
        if "img" in cfg:
            item["img"] = Image.open(os.path.join(sdir, cfg["img"] + ".png")).convert("RGB")
        out.append(item)
    out[0]["start"] = 0.0
    out[-1]["end"] = c1 - c0
    for i in range(len(out) - 1):  # 首尾相接
        out[i]["end"] = out[i + 1]["start"]
    return out


def render(ep, sid, spec, preview=None):
    script = json.load(open(os.path.join(ep, "01_文案/script.json"), encoding="utf-8"))
    if script.get("version", 1) >= 3:  # 整章配音：时间轴来自音频里的停顿
        vis, _aud, _ch, paras, _t = v2.build_timeline_long(ep, script, A.LEAD, A.TITLE_DUR, A.decode_mp3)
    else:
        vis, _aud, _ch, paras, _t = A.build_timeline(ep, script)
    ids = spec["paras"]
    sel = [p for p in paras if ids[0] <= p["id"] <= ids[1]]
    seg_dir = os.path.join(ep, "02_配音/segments")
    last = sel[-1]
    if "audio" in last:  # 整章配音版本
        last_dur = len(last["audio"]) / A.SR
    else:
        last_dur = json.load(open(os.path.join(seg_dir, last["id"] + ".json"), encoding="utf-8"))["extra_info"]["audio_length"] / 1000
    c0 = sel[0]["start"] - 0.1
    c1 = sel[-1]["start"] + last_dur + 0.35
    total = c1 - c0
    events = v2.build_subs(sel, lambda t: v2.split_chunks(t, CAP_CHARS), A.clean_sub, CAP_CHARS, A.decode_mp3)
    events = fix_numbers([[a - c0, b - c0, txt] for a, b, txt in events])
    scenes = load_scenes(ep, spec, vis, c0, c1)
    print(f"{sid}: {total:.1f} 秒，字幕 {len(events)} 条，画面 {len(scenes)} 个", flush=True)

    bgs, last_bg = [], None
    for s in scenes:
        if "img" in s:
            last_bg = make_bg(s["img"])
        bgs.append(last_bg or plain_bg())
    for i, s in enumerate(scenes):  # 开头就是图表时借用后面的背景
        if bgs[i] is None:
            bgs[i] = plain_bg()
    hook = hook_layer(spec["hook"])
    cta = cta_layer()
    mask = window_mask()

    def window_at(s, t_abs):
        t = t_abs - s["start"]
        cfg = s["cfg"]
        if "img" in s:
            return scene_window(s["img"], cfg.get("fx", 0.5), t, s["end"] - s["start"], cfg.get("zoom", "in")).convert("RGBA")
        return CARDS[cfg["card"]](cfg, t)

    out = os.path.join(ep, "08_Shorts", f"{sid}.mp4")
    n_total = round((min(preview, total) if preview else total) * FPS)
    audio_src = glob.glob(os.path.join(ep, "06_成片", "*.mp4"))
    audio_src = [p for p in audio_src if "preview" not in p][0]
    fc = (f"[1:a]afade=t=in:st=0:d=0.12,afade=t=out:st={total - 0.4:.2f}:d=0.4,"
          f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-ss", f"{c0:.3f}", "-t", f"{total:.3f}", "-i", audio_src,
           "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-frames:v", str(n_total),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(n_total):
        t = f / FPS
        idx = max(i for i, s in enumerate(scenes) if s["start"] <= t + 1e-6)
        s = scenes[idx]
        bg, win = bgs[idx], window_at(s, t)
        k = t - s["start"]
        if idx > 0 and k < FADE:  # 与上一个画面交叉淡入
            a = k / FADE
            prev = scenes[idx - 1]
            bg = Image.blend(bgs[idx - 1], bg, a)
            win = Image.blend(window_at(prev, t), win, a)
        fr = bg.convert("RGBA")
        sh = Image.new("RGBA", (WIN + 80, WIN + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([40, 52, WIN + 40, WIN + 52], 72, fill=(0, 0, 0, 150))
        fr.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)), (-40, WIN_Y - 40))
        fr.paste(win.convert("RGB"), (0, WIN_Y), mask)
        h = hook.copy()
        h.putalpha(h.split()[3].point(lambda v: int(v * ease_out(prog(t, 0.15, 0.7)))))
        fr.alpha_composite(h, (0, 0))
        cue = next((e for e in events if e[0] <= t < e[1]), None)
        if cue:
            img, pad = caption_img(cue[2])
            a = prog(t, cue[0], 0.1)
            paste_center(fr, img, pad, W / 2, CAP_Y, a)
        if t > total - 1.9:
            paste_center(fr, cta, 0, W / 2, 1635, ease_out(prog(t, total - 1.9, 0.5)))
        proc.stdin.write(np.asarray(fr.convert("RGB")).tobytes())
        if f % 150 == 0:
            print(f"  {f}/{n_total}", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 失败")
    with open(os.path.join(ep, "08_Shorts", f"{sid}.srt"), "w", encoding="utf-8") as fh:
        for i, (a, b, txt) in enumerate(events, 1):
            fh.write(f"{i}\n{A.srt_time(a)} --> {A.srt_time(b)}\n{txt}\n\n")
    print("输出:", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--preview", type=float)
    args = ap.parse_args()
    ep = args.episode.rstrip("/")
    cfg = json.load(open(os.path.join(ep, "08_Shorts/shorts.json"), encoding="utf-8"))
    for sid in args.ids:
        render(ep, sid, cfg[sid], args.preview)


if __name__ == "__main__":
    main()
