"""第二版合成用的画面与字幕函数（script.json 里 "version": 2 时由 assemble.py 调用）。

- scene_clip：Python 逐帧做亚像素推拉镜头（ffmpeg zoompan 会抖动）。
- 网络图片：非 16:9 的照片放在同图模糊背景上，左上角标注作者与授权。
- build_subs：按配音中真实的停顿对齐字幕（对应 EP001「字幕与语音不同步」）。
"""
import json
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import graphics2 as G2  # 导入时会注册 graphics3 的纸张风格卡片
_G2 = G2

W, H, FPS, SR = 1920, 1080, 30, 44100
SRC_W, SRC_H = 2880, 1620
PUNCT = "，。；：、？！"
FONT_BOLD = _G2.FONT_BOLD
FOOTAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "素材库/官方视频")


# ---------- 画面来源 ----------

def find_visual(ep, vid):
    scene = os.path.join(ep, "03_画面素材/场景图", vid + ".png")
    web = os.path.join(ep, "03_画面素材/网络图片", vid + ".jpg")
    if os.path.exists(scene):
        return scene, None
    bg = os.path.join(ep, "03_画面素材/背景", vid + ".png")
    if os.path.exists(bg):
        return bg, None
    if os.path.exists(web):
        src = json.load(open(os.path.join(ep, "03_画面素材/网络图片/sources.json"), encoding="utf-8")).get(vid, {})
        return web, src
    return None, None


def credit_text(src):
    artist = src.get("artist", "").replace("Photograph:", "").strip()
    return f"Photo: {artist[:48]} · {src.get('license', '')} · Wikimedia Commons"


def prepare_source(path, credit=None):
    """返回 2880x1620 的源图。非 16:9 的照片用同图模糊背景 + 居中原图；AI 场景图（3:2）直接裁满画面。"""
    im = Image.open(path).convert("RGB")
    ratio = im.width / im.height
    fill = "场景图" in path and 1.3 < ratio < 2.3  # 2026-10-21：插图裁满，不留模糊边条
    if fill or abs(ratio - 16 / 9) < 0.12:
        s = max(SRC_W / im.width, SRC_H / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        out = im.crop(((im.width - SRC_W) // 2, (im.height - SRC_H) // 2, (im.width - SRC_W) // 2 + SRC_W, (im.height - SRC_H) // 2 + SRC_H))
    else:
        s = max(SRC_W / im.width, SRC_H / im.height)
        bg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        bg = bg.crop(((bg.width - SRC_W) // 2, (bg.height - SRC_H) // 2, (bg.width - SRC_W) // 2 + SRC_W, (bg.height - SRC_H) // 2 + SRC_H))
        bg = bg.filter(ImageFilter.GaussianBlur(40))
        bg = Image.fromarray((np.asarray(bg, np.float32) * 0.42).astype(np.uint8))
        fh = int(SRC_H * 0.9)
        fw = round(im.width * fh / im.height)
        if fw > SRC_W * 0.9:
            fw = int(SRC_W * 0.9)
            fh = round(im.height * fw / im.width)
        fg = im.resize((fw, fh), Image.LANCZOS)
        shadow = Image.new("RGBA", (SRC_W, SRC_H), (0, 0, 0, 0))
        x, y = (SRC_W - fw) // 2, (SRC_H - fh) // 2
        ImageDraw.Draw(shadow).rectangle([x + 10, y + 18, x + fw + 10, y + fh + 18], fill=(0, 0, 0, 170))
        out = bg.convert("RGBA")
        out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(28)))
        out.paste(fg, (x, y))
        out = out.convert("RGB")
    return out


def credit_layer(credit):
    f = ImageFont.truetype(FONT_BOLD, 22)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tw = int(d.textlength(credit, font=f))
    lay = Image.new("RGBA", (tw + 28, 40), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([0, 0, tw + 27, 39], 8, fill=(0, 0, 0, 120))
    ld.text((14, 7), credit, font=f, fill=(235, 235, 235, 220))
    return lay


def scene_clip(path, n, mode, out, credit=None):
    src = prepare_source(path)
    cred = credit_layer(credit) if credit else None
    # 四种平稳运动：推近、拉远、左移、右移
    z0, z1, pan = {0: (1.0, 1.08, 0), 1: (1.08, 1.0, 0), 2: (1.06, 1.06, 1), 3: (1.06, 1.06, -1)}[mode % 4]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p = i / max(1, n - 1)
        z = z0 + (z1 - z0) * p
        cw, ch = SRC_W / z, SRC_H / z
        cx = SRC_W / 2 + pan * (SRC_W - cw) / 2 * (2 * p - 1)
        cy = SRC_H / 2
        frame = src.transform((W, H), Image.AFFINE, (cw / W, 0, cx - cw / 2, 0, ch / H, cy - ch / 2), Image.BICUBIC)
        if cred is not None:
            frame = frame.convert("RGBA")
            frame.alpha_composite(cred, (36, 32))
            frame = frame.convert("RGB")
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg 编码失败: {out}")


def footage_clip(f, n, out, ep=None):
    """视频片段：从 start 秒开始取 n 帧，转成 1920x1080 30fps、去掉原声，左上角标注来源。
    src 先找本集 03_画面素材/视频素材/raw/，再找 素材库/官方视频/。y（0～1）= 裁成 16:9 时保留画面的哪个高度。
    片段不够长时往前挪起点；整支素材都不够长时放慢播放。"""
    src = os.path.join(ep, "03_画面素材/视频素材/raw", f["src"]) if ep else ""
    if not os.path.exists(src):
        src = os.path.join(FOOTAGE_DIR, f["src"])
    length = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                  capture_output=True, text=True).stdout.strip())
    dur = n / FPS
    start = f.get("start", 0.0)
    slow = float(f.get("slow", 1.0))
    if dur * (1 / slow) > length - start - 0.3:
        if dur / slow > length - 0.5:
            slow = dur / (length - 0.5)
            start = 0.0
        else:
            start = max(0.0, length - 0.3 - dur / slow)
    credit = f.get("credit", "影片來源：Tesla 官方")
    import hashlib
    cred = os.path.join(os.path.dirname(out), "_credit_" + hashlib.md5(credit.encode()).hexdigest()[:8] + ".png")
    if not os.path.exists(cred):
        credit_layer(credit).save(cred)
    y = float(f.get("y", 0.5))
    zoom = float(f.get("zoom", 1.0))  # >1 时裁掉黑边或拉近
    sw, sh = int(W * zoom), int(H * zoom)
    vf = (f"[0:v]setpts={slow:.4f}*(PTS-STARTPTS),fps={FPS},scale={sw}:{sh}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{y:.3f},format=yuv420p[v0];[v0][1:v]overlay=36:32[v]")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", src, "-i", cred,
                        "-filter_complex", vf, "-map", "[v]", "-frames:v", str(n), "-an",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])


def clip_frames(path):
    """缓存的片段帧数（中途被打断的片段帧数会不对，需要重做）。"""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=nb_frames",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return -1


def _render_one(job):
    kind, args = job
    if kind == "footage":
        footage_clip(*args)
    elif kind == "scene":
        scene_clip(*args[:4], credit=args[4])
    else:
        spec, dur, out, prev, n = args
        G2.render_clip(spec, dur, out, preview_png=prev, frames=n)
    return args[2] if kind != "footage" else args[2]


def build_clips(ep, visuals, work, force_graphics=False, index_offset=0, workers=4):
    """逐个画面渲染成片段（4 个进程并行，2026-10-21 起）。已有且帧数对的片段直接沿用。"""
    import concurrent.futures as _cf
    gspec = json.load(open(os.path.join(ep, "03_画面素材/graphics.json"), encoding="utf-8"))
    fpath = os.path.join(ep, "03_画面素材/视频素材/footage.json")
    if not os.path.exists(fpath):
        fpath = os.path.join(ep, "03_画面素材/footage.json")
    footage = json.load(open(fpath, encoding="utf-8")) if os.path.exists(fpath) else {}
    clip_dir = os.path.join(work, "clips_v2")
    os.makedirs(clip_dir, exist_ok=True)
    prev_dir = os.path.join(ep, "03_画面素材/图表")
    os.makedirs(prev_dir, exist_ok=True)
    paths, jobs = [], []
    for i, v in enumerate(visuals, index_offset):
        n = max(1, round((v["start"] + v["dur"]) * FPS) - round(v["start"] * FPS))
        out = os.path.join(clip_dir, f"{i:03d}_{v['id']}_{n}f.mp4")
        paths.append(out)
        base = v["id"].split("#", 1)[0]  # 「画面#2」= 同一个素材再用一次（换一段、换取景）
        path, src = find_visual(ep, base)
        is_footage = v["id"] in footage or base in footage
        if not os.path.exists(out) and not force_graphics:
            # 同一画面、同样帧数的旧片段（只是序号变了，例如片头加了画面）：直接沿用，不重新渲染
            import glob as _glob
            old = [p for p in _glob.glob(os.path.join(clip_dir, f"[0-9][0-9][0-9]_{_glob.escape(v['id'])}_{n}f.mp4"))
                   if clip_frames(p) == n]
            if old:
                os.link(old[0], out)
        if os.path.exists(out) and (path or is_footage or not force_graphics) and clip_frames(out) == n:
            continue
        if is_footage:
            jobs.append(("footage", (footage.get(v["id"]) or footage[base], n, out, ep)))
        elif path:
            jobs.append(("scene", (path, n, i, out, credit_text(src) if src else None)))
        else:
            spec = dict(v.get("spec") or gspec.get(v["id"]) or gspec[base])
            if spec.get("bg") in footage:  # 背景指向视频时，取一帧当背景
                still = os.path.join(ep, "03_画面素材/背景", spec["bg"] + ".png")
                if not os.path.exists(still):
                    os.makedirs(os.path.dirname(still), exist_ok=True)
                    f = footage[spec["bg"]]
                    fsrc = os.path.join(ep, "03_画面素材/视频素材/raw", f["src"])
                    if not os.path.exists(fsrc):
                        fsrc = os.path.join(FOOTAGE_DIR, f["src"])
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(f.get("start", 0) + 1.5),
                                    "-i", fsrc, "-frames:v", "1", still], check=True)
            if spec.get("bg"):
                bg_path = find_visual(ep, spec["bg"])[0]
                spec["bg"] = os.path.abspath(bg_path) if bg_path else None  # 背景不是图片（例如图表卡）时用默认底色
            if spec.get("img") and not os.path.isabs(spec["img"]):  # 网页截图卡：相对 03_画面素材/网页截图/
                spec["img"] = os.path.abspath(os.path.join(ep, "03_画面素材/网页截图", spec["img"]))
            jobs.append(("graphic", (spec, n / FPS, out, os.path.join(prev_dir, base + ".png"), n)))
    print(f"  需要渲染 {len(jobs)} 个画面（共 {len(visuals)} 个）", flush=True)
    with _cf.ProcessPoolExecutor(workers) as ex:
        futs = [ex.submit(_render_one, j) for j in jobs]
        for k, fu in enumerate(_cf.as_completed(futs), 1):
            fu.result()
            if k % 10 == 0 or k == len(jobs):
                print(f"  画面 {k}/{len(jobs)}", flush=True)
    return paths


# ---------- 字幕对齐 ----------

_REF = None  # 整条配音的最大帧 RMS；设置后静音判定以它为基准（安静段落里的停顿才不会被漏掉）


def speech_mask(audio, hop=0.01):
    """10ms 一帧的说话/静音判定。"""
    k = int(SR * hop)
    n = len(audio) // k
    rms = np.sqrt(np.mean(audio[: n * k].reshape(n, k) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms / ((_REF or rms.max()) + 1e-12))
    return db > -38, hop


def frame_rms_max(audio, hop=0.01):
    k = int(SR * hop)
    n = len(audio) // k
    return float(np.sqrt(np.mean(audio[: n * k].reshape(n, k) ** 2, axis=1)).max()) if n else 0.0


def pauses(audio):
    """返回 (说话开始, 说话结束, [(停顿开始, 停顿结束)…])，单位秒。"""
    talk, hop = speech_mask(audio)
    idx = np.where(talk)[0]
    if not len(idx):
        return 0.0, len(audio) / SR, []
    onset, offset = idx[0] * hop, (idx[-1] + 1) * hop
    gaps = []
    run_start = None
    for i in range(idx[0], idx[-1] + 1):
        if not talk[i] and run_start is None:
            run_start = i
        elif talk[i] and run_start is not None:
            if (i - run_start) * hop >= 0.07:
                gaps.append((run_start * hop, i * hop))
            run_start = None
    return onset, offset, gaps


def align_paragraph(text, est_times, audio):
    """回传「字元位置 → 秒」函数。

    est_times：每个字的估计开始/结束时间（整章配音时来自 MiniMax 的逐字时间，误差约 0.5 秒以内）。
    每个标点按顺序吸附到附近的真实停顿（音频里 ≥70ms 的静音），再用这些校正点修正其他字的时间。"""
    onset, offset, gaps = pauses(audio)
    n = len(text)
    est_b = [b for _, b, _ in est_times]
    est_e = [e for _, _, e in est_times]
    anchors = [(0, onset)]  # (字元位置, 真实时间)
    k0 = 0
    for j, ch in enumerate(text):
        if ch not in PUNCT or j == n - 1:
            continue
        guess = est_e[j]
        cand = [(abs(g0 - guess), k) for k, (g0, g1) in enumerate(gaps[k0:], k0) if abs(g0 - guess) < 0.8]
        if cand:
            _, k = min(cand)
            anchors += [(j, gaps[k][0]), (j + 1, gaps[k][1])]
            k0 = k + 1
    anchors.append((n, offset))
    # 校正量 = 真实时间 − 估计时间，在校正点之间线性内插
    ax = np.array([a for a, _ in anchors], np.float64)
    est_at = lambda i: est_b[i] if i < n else (est_e[-1] if est_e else offset)  # noqa: E731
    corr = np.array([t - est_at(a) for a, t in anchors], np.float64)
    times = np.array([est_at(i) + np.interp(i, ax, corr) for i in range(n + 1)])
    for a, t in anchors:  # 校正点处用真实时间
        times[a] = t
    times = np.maximum.accumulate(np.clip(times, onset, offset))
    return lambda idx: float(times[min(max(int(round(idx)), 0), n)])


def build_subs(paras, split_chunks, clean_sub, sub_max, decode):
    global _REF
    events = []
    auds = [p["audio"] if "audio" in p else decode(p["mp3"]) for p in paras]
    _REF = max(frame_rms_max(a) for a in auds) or None  # 以整条配音最响的一帧为基准
    for p, audio in zip(paras, auds):
        t_at = align_paragraph(p["text"], p["times"], audio)
        for a, b in split_chunks(p["text"]):
            txt = clean_sub(p["text"][a:b])
            if not txt:
                continue
            end_idx = b - 1 if p["text"][b - 1:b] in PUNCT else b
            start = p["start"] + t_at(a) - 0.06  # 略早出现
            end = p["start"] + t_at(end_idx)
            events.append([start, max(end, start + 0.3), txt])
    _REF = None
    for i in range(len(events) - 1):  # 短空隙内延长到下一句，不推迟下一句
        if 0 < events[i + 1][0] - events[i][1] < 0.3:
            events[i][1] = events[i + 1][0]
        events[i][1] = min(events[i][1], events[i + 1][0])
    i = 0
    while i < len(events) - 1:  # 太短就合并
        a, b, txt = events[i]
        if b - a < 0.6 and len(txt) + 1 + len(events[i + 1][2]) <= sub_max:
            events[i] = [a, events[i + 1][1], f"{txt} {events[i + 1][2]}"]
            del events[i + 1]
            continue
        i += 1
    for i in range(len(events) - 1):  # 合并后再确认不重叠
        events[i][1] = min(events[i][1], events[i + 1][0])
    return events


def sync_report(events, paras, decode, sample=8):
    """抽查：每个段落第一条字幕的开始时间 vs 实际开口时间。"""
    rows = []
    step = max(1, len(paras) // sample)
    for p in paras[::step][:sample]:
        onset, _, _ = pauses(p["audio"] if "audio" in p else decode(p["mp3"]))
        real = p["start"] + onset
        first = min((e for e in events if e[0] >= p["start"] - 0.5), key=lambda e: abs(e[0] - real))
        rows.append((p["id"], round(first[0] - real, 3), first[2]))
    return rows


# ---------- 按词断句 ----------

_cc = None


def word_bounds(text):
    """回传可以断行的位置（词与词之间）。繁体先转简体再用 jieba 分词，字数不变时才采用。"""
    global _cc
    import logging

    import jieba
    from opencc import OpenCC
    jieba.setLogLevel(logging.WARNING)
    _cc = _cc or OpenCC("t2s")
    simp = _cc.convert(text)
    if len(simp) != len(text):
        return set(range(1, len(text)))
    bounds, pos = set(), 0
    for w in jieba.cut(simp):
        pos += len(w)
        bounds.add(pos)
    return bounds


def split_chunks(text, sub_max=16):
    """先按标点切，超过 sub_max 的子句只在词边界、靠近中间处再切。回传 [(开始, 结束)]。"""
    pieces, start, i = [], 0, 0
    while i < len(text):
        if text[i] in PUNCT:
            end = i + 1
            while end < len(text) and text[end] in "」》〉）":  # 结束引号跟着标点走
                end += 1
            pieces.append((start, end))
            start = i = end
            continue
        i += 1
    if start < len(text):
        pieces.append((start, len(text)))
    bounds = word_bounds(text)
    depth = 0  # 书名号、引号内不断行
    for i, ch in enumerate(text):
        if ch in "《「〈":
            depth += 1
        elif ch in "》」〉":
            depth = max(0, depth - 1)
        elif depth > 0:
            bounds.discard(i + 1)
        if depth > 0 and ch in "《「〈":
            bounds.discard(i + 1)

    def bad(k):  # 数字和单位、日期不拆开：数字后面不断行；「10月」「9日」之间不断行
        if 0 < k < len(text):
            if text[k - 1].isdigit() or text[k - 1] in ".%％":
                return True
            if text[k].isdigit() and text[k - 1] in "月年第約约":
                return True
            a, b = text[k - 1:k].strip() or text[k - 2:k - 1], text[k:k + 1].strip() or text[k + 1:k + 2]
            if a.isascii() and a.isalnum() and b.isascii() and b.isalnum():  # 英文名不拆（Model A）
                return True
        return False

    bounds = {k for k in bounds if not bad(k)}

    def cut(a, b):
        body_end = b
        while body_end > a and text[body_end - 1] in PUNCT:
            body_end -= 1
        if body_end - a <= sub_max:
            return [(a, b)]
        mid = (a + body_end) / 2
        cands = [k for k in bounds if a + 2 <= k <= body_end - 2]
        if not cands:
            cands = [k for k in range(a + 2, body_end - 1) if not bad(k)] or [int(mid)]
        k = min(cands, key=lambda k: abs(k - mid))
        return cut(a, k) + cut(k, b)

    out = []
    for a, b in pieces:
        out += cut(a, b)
    merged = []  # 合并太短的块（≤3 字）到前一块
    for a, b in out:
        if merged and len(text[merged[-1][0]:b].rstrip(PUNCT)) <= sub_max and len(text[merged[-1][0]:merged[-1][1]].strip(PUNCT)) <= 3:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return merged


# ---------- 整章配音的时间轴（script.json "version" ≥ 3） ----------

def silences(audio, min_len=0.3):
    talk, hop = speech_mask(audio)
    out, start = [], None
    for i, t in enumerate(talk):
        if not t and start is None:
            start = i
        elif t and start is not None:
            if (i - start) * hop >= min_len:
                out.append((start * hop, i * hop))
            start = None
    idx = np.where(talk)[0]
    first = idx[0] * hop if len(idx) else 0.0
    last = (idx[-1] + 1) * hop if len(idx) else len(audio) / SR
    return [s for s in out if s[0] > first and s[1] < last], first, last


def match_pauses(cands, expected, mids=None, w_time=0.6):
    """从候选停顿里按顺序挑出 len(expected) 个（动态规划）。
    成本 = |时长 − 预期时长| + w_time × |位置 − 预期位置|，避免把句中逗号的停顿当成段落停顿。"""
    n, m = len(cands), len(expected)
    if n < m:
        raise RuntimeError(f"音频里只找到 {n} 个明显停顿，少于预期的 {m} 个")
    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    pick = [[False] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, min(i, m) + 1):
            skip = dp[i - 1][j]
            c0, c1 = cands[i - 1]
            cost = abs((c1 - c0) - expected[j - 1])
            if mids is not None:
                cost += w_time * abs((c0 + c1) / 2 - mids[j - 1])
            take = dp[i - 1][j - 1] + cost
            if take <= skip:
                dp[i][j], pick[i][j] = take, True
            else:
                dp[i][j] = skip
    res, i, j = [], n, m
    while j > 0:
        if pick[i][j]:
            res.append(cands[i - 1])
            j -= 1
        i -= 1
    return res[::-1]


def expected_pauses(items, onset, offset, tail=0.3):
    """按字数估计每个停顿的时长（标记 + 句末自然停顿）与位置。"""
    marks = [it["pause"] for it in items if "pause" in it]
    chars = sum(len(it["text"]) for it in items if "text" in it)
    rate = max(0.05, (offset - onset - sum(marks)) / max(1, chars))
    durs, mids, cur = [], [], onset
    for it in items:
        if "text" in it:
            cur += len(it["text"]) * rate
        else:
            durs.append(it["pause"] + tail)
            mids.append(cur + it["pause"] / 2)
            cur += it["pause"]
    return durs, mids


def spoken_units(pron, word):
    """估计一个字/词实际念出来的音节数：汉字 1，注音（多音字修正）1，英文单词约 1.5，数字按读出的汉字计。"""
    import re
    if word in PUNCT or not pron.strip():
        return 0.0
    n = len(re.findall(r"[\u4e00-\u9fff]", pron))
    n += len(re.findall(r"[ㄅ-ㄩ]+[ˊˇˋ˙ˉ]?", pron))
    n += 1.5 * len(re.findall(r"[A-Za-z]+", pron))
    return max(n, 0.5)


def pick_pauses_by_words(items, para_off, word_t, sil):
    """每个停顿标记 = 前一段最后一个字的结束 ~ 后一段第一个字的开始；在 sil 里按顺序找中点最接近的静音。"""
    out, k0 = [], 0
    for idx, it in enumerate(items):
        if "pause" not in it:
            continue
        prev = next(x for x in reversed(items[:idx]) if "text" in x)
        nxt = next(x for x in items[idx + 1:] if "text" in x)
        end_prev = word_t[para_off[prev["para"]] + len(prev["text"]) - 1][1]
        start_next = word_t[para_off[nxt["para"]]][0]
        target = (end_prev + start_next) / 2
        cand = [(abs((a + b) / 2 - target) - 0.3 * min(b - a, it["pause"]), k)
                for k, (a, b) in enumerate(sil[k0:], k0) if abs((a + b) / 2 - target) < 2.0]
        if not cand:
            return None
        _, k = min(cand)
        out.append(sil[k])
        k0 = k + 1
    return out


def est_times(text, dur, weights=None):
    """估计每个字的时间（供标点对齐时找最近的停顿）。weights = 每个字的音节数，没有时按字数平均。"""
    if weights is None:
        weights = [0.0 if ch in PUNCT else 1.0 for ch in text]
    total = sum(weights) or 1.0
    times, acc = [], 0.0
    for i, w in enumerate(weights):
        times.append((i, dur * acc / total, dur * (acc + w) / total))
        acc += w
    return times


def build_timeline_long(ep, script, lead, title_dur, decode):
    """回传与 assemble.build_timeline 相同的 (visuals, audio, chapters, paras, total)。"""
    seg_dir = os.path.join(ep, "02_配音/segments")
    paras_by_id = {p["id"]: (sec, p) for sec in script["sections"] for p in sec["paragraphs"]}
    first_para_section = {}
    for sec in script["sections"]:
        for p in sec["paragraphs"]:
            if "text" in p:
                first_para_section.setdefault(sec["id"], p["id"])
    visuals, audio_list, chapters, paras = [], [], [], []
    t = lead
    chunk_files = sorted(f for f in os.listdir(seg_dir) if f.startswith("c") and f.endswith(".json"))
    for ci, cf in enumerate(chunk_files):
        meta = json.load(open(os.path.join(seg_dir, cf), encoding="utf-8"))
        items = meta["items"]
        mp3 = os.path.join(seg_dir, cf[:-5] + ".mp3")
        audio = decode(mp3)
        first_pid = next(it["para"] for it in items if "text" in it)
        sec, _ = paras_by_id[first_pid]
        if ci > 0 and sec.get("title_card"):  # 章节卡落在两段音频之间
            chapters.append((t, sec["chapter"]))
            visuals.append({"id": f"title_{sec['id']}", "start": t, "dur": title_dur + 0.5,
                            "spec": {"type": "title", "text": sec["title_card"], "bg": first_visual(sec)}})
            t += title_dur + 0.5
        elif ci == 0:
            chapters.append((0.0, sec["chapter"]))
        # 每个字实际要念几个音节（数字、百分比、英文念得比字数长）：用 MiniMax 返回的 pronounce_word 计算
        # MiniMax 逐字时间（位置以去掉停顿标记后的文字计；「0.74%」这类词会拆成多条，取首尾）
        word_t = {}
        for sub in meta.get("subtitles", []):
            for w in sub.get("timestamped_words") or []:
                wb, we = w["word_begin"], w.get("word_end", w["word_begin"] + 1)
                t0w, t1w = w["time_begin"] / 1000, w["time_end"] / 1000
                if wb in word_t:
                    t0w = min(t0w, word_t[wb][0])
                    t1w = max(t1w, word_t[wb][1])
                for k in range(wb, we):  # 词内各字平均分配
                    f0, f1 = (k - wb) / (we - wb), (k - wb + 1) / (we - wb)
                    word_t[k] = (t0w + (t1w - t0w) * f0, t0w + (t1w - t0w) * f1)
        para_off, pos = {}, 0
        for it in items:
            if "text" in it:
                para_off[it["para"]] = pos
                pos += len(it["text"])
        # 少数字符 MiniMax 不给时间（如「SR-71」的连字号）：用前后字补上，否则整段会退回粗略估计（EP004 字幕挤在一起）
        if word_t and len(word_t) >= pos * 0.95:
            for k in range(pos):
                if k not in word_t:
                    prev = max((j for j in word_t if j < k), default=None)
                    nxt = min((j for j in word_t if j > k), default=None)
                    a_ = word_t[prev][1] if prev is not None else word_t[nxt][0]
                    b_ = word_t[nxt][0] if nxt is not None else a_
                    word_t[k] = (a_, max(a_, b_))
        sil, onset, offset = silences(audio)
        pauses_meta = [it for it in items if "pause" in it]
        durs, mids = expected_pauses(items, onset, offset)
        chosen = match_pauses(sil, durs, mids)
        if word_t and all(k in word_t for k in range(pos)):
            # 有 MiniMax 逐字时间时，用它估计每个停顿标记的位置（误差约 0.5 秒），再找最近的真实静音
            chosen = pick_pauses_by_words(items, para_off, word_t, sil) or chosen
        # 每段话的起止（相对本段音频）
        bounds, k, cursor = {}, 0, onset
        for it in items:
            if "text" in it:
                end = chosen[k][0] if k < len(chosen) else offset
                bounds[it["para"]] = (cursor, end)
            else:
                cursor = chosen[k][1]
                k += 1
        t0 = t
        audio_list.append((cf[:-5], t0))
        k = 0
        for idx, it in enumerate(items):
            if "pause" in it:
                s0, s1 = chosen[k]
                k += 1
                cur = t0 + s0 + 0.25
                for part in it["parts"]:
                    if part["kind"] == "brand":
                        visuals.append({"id": paras_by_id[part["para"]][1]["visuals"][0], "start": cur, "dur": part["sec"]})
                        cur += part["sec"]
                    elif part["kind"] == "title":
                        s = next(x for x in script["sections"] if x["id"] == part["section"])
                        chapters.append((cur, s["chapter"]))
                        end = t0 + s1 - 0.05
                        visuals.append({"id": f"title_{s['id']}", "start": cur, "dur": max(1.5, end - cur),
                                        "spec": {"type": "title", "text": s["title_card"], "bg": first_visual(s)}})
                        cur = end
                    elif part["kind"] == "gap" and any(x["kind"] != "gap" for x in it["parts"]) is False:
                        pass
                continue
            sec, p = paras_by_id[it["para"]]
            a, b = bounds[it["para"]]
            nxt = next((x for x in items[idx + 1:]), None)
            if nxt is None:
                vis_end = t0 + offset + 0.6
            elif "pause" in nxt and any(x["kind"] != "gap" for x in nxt["parts"]):
                vis_end = t0 + chosen[k][0] + 0.25
            else:
                vis_end = t0 + (chosen[k][1] if "pause" in nxt else b) - 0.05
            start = t0 + a - 0.05
            seg = audio[int(max(0, a - 0.05) * SR): int(b * SR) + int(0.1 * SR)]
            off = para_off[it["para"]]
            base = max(0, a - 0.05)
            if all((off + i) in word_t for i in range(len(p["text"]))):
                est = [(i, word_t[off + i][0] - base, word_t[off + i][1] - base) for i in range(len(p["text"]))]
            else:
                est = est_times(p["text"], b - a)
            paras.append({"id": p["id"], "start": t0 + max(0, a - 0.05), "text": p["text"], "times": est, "audio": seg})
            # 段内多个画面：写了「画面@词」的，念到这个词时切入（2026-10-21 起，声音画面要对上）；
            # 没写的在前后两个切点之间、最接近等分点的标点处切换
            n = len(p["visuals"])
            span = vis_end - start
            ids = [v.split("@", 1)[0] for v in p["visuals"]]
            anchors = [v.split("@", 1)[1] if "@" in v else None for v in p["visuals"]]
            cuts = [0.0] + [None] * (n - 1) + [span]
            if n > 1:
                t_at = align_paragraph(p["text"], est, seg)
                pos = 0
                for j in range(1, n):
                    if anchors[j]:
                        ka = p["text"].find(anchors[j], pos)
                        if ka < 0:
                            raise RuntimeError(f"{p['id']}: 找不到切点词「{anchors[j]}」（要按顺序出现在段落里）")
                        cuts[j] = max(0.0, t_at(ka) - 0.12)
                        pos = ka + len(anchors[j])
                stops = [t_at(i) for i, ch in enumerate(p["text"]) if ch in PUNCT]
                j = 1
                while j < n:
                    if cuts[j] is not None:
                        j += 1
                        continue
                    j2 = next(x for x in range(j, n + 1) if cuts[x] is not None)
                    lo, hi = cuts[j - 1], cuts[j2] if j2 < n else (b - a)
                    for m in range(j, j2):
                        target = lo + (hi - lo) * (m - j + 1) / (j2 - j + 1)
                        near = [x for x in stops if lo + 0.8 < x < hi - 0.8]
                        cuts[m] = min(near, key=lambda x: abs(x - target)) if near else target
                    j = j2
                for j in range(1, n + 1):  # 保证每个画面至少 0.6 秒
                    cuts[j] = max(cuts[j], cuts[j - 1] + 0.6) if j < n else cuts[j]
            for j, vid in enumerate(ids):
                visuals.append({"id": vid, "start": start + cuts[j], "dur": cuts[j + 1] - cuts[j]})
        t = t0 + len(audio) / SR + 0.6
        if cf == "c00.json":  # 后加的片头（频道介绍）：对齐到整帧，后面所有画面整帧平移，已渲染的片段可以沿用
            t = math.ceil(t * FPS - 1e-6) / FPS
    # 没有章节卡的章节（如「今日重點」「結尾」）也列进章节，时间取该章第一段开口
    starts = {p["id"]: p["start"] for p in paras}
    have = {name for _, name in chapters}
    for sec in script["sections"]:
        first = next((p["id"] for p in sec["paragraphs"] if "text" in p), None)
        if sec["chapter"] not in have and first in starts:
            chapters.append((starts[first], sec["chapter"]))
    chapters.sort()
    # 画面首尾相接（避免空隙或重叠）
    visuals.sort(key=lambda v: v["start"])
    for i in range(len(visuals) - 1):
        visuals[i]["dur"] = visuals[i + 1]["start"] - visuals[i]["start"]
    visuals[-1]["dur"] = max(visuals[-1]["dur"], t - visuals[-1]["start"])
    if visuals and visuals[0]["start"] > 0:
        visuals[0]["dur"] += visuals[0]["start"]
        visuals[0]["start"] = 0.0
    return visuals, audio_list, chapters, paras, t


def first_visual(sec):
    """章节标题卡的背景：优先用 script.json 里该章的 title_bg，否则取本章第一个画面。"""
    return sec.get("title_bg") or next(v for p in sec["paragraphs"] for v in p.get("visuals", []))
