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

import graphics2 as G2

W, H, FPS, SR = 1920, 1080, 30, 44100
SRC_W, SRC_H = 2880, 1620
PUNCT = "，。；：、？！"
FONT_BOLD = G2.FONT_BOLD


# ---------- 画面来源 ----------

def find_visual(ep, vid):
    scene = os.path.join(ep, "03_画面素材/场景图", vid + ".png")
    web = os.path.join(ep, "03_画面素材/网络图片", vid + ".jpg")
    if os.path.exists(scene):
        return scene, None
    if os.path.exists(web):
        src = json.load(open(os.path.join(ep, "03_画面素材/网络图片/sources.json"), encoding="utf-8")).get(vid, {})
        return web, src
    return None, None


def credit_text(src):
    artist = src.get("artist", "").replace("Photograph:", "").strip()
    return f"Photo: {artist[:48]} · {src.get('license', '')} · Wikimedia Commons"


def prepare_source(path, credit=None):
    """返回 2880x1620 的源图。非 16:9 的照片用同图模糊背景 + 居中原图。"""
    im = Image.open(path).convert("RGB")
    ratio = im.width / im.height
    if abs(ratio - 16 / 9) < 0.12:
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


def clip_frames(path):
    """缓存的片段帧数（中途被打断的片段帧数会不对，需要重做）。"""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=nb_frames",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return -1


def build_clips(ep, visuals, work, force_graphics=False, index_offset=0):
    gspec = json.load(open(os.path.join(ep, "03_画面素材/graphics.json"), encoding="utf-8"))
    clip_dir = os.path.join(work, "clips_v2")
    os.makedirs(clip_dir, exist_ok=True)
    prev_dir = os.path.join(ep, "03_画面素材/图表")
    paths = []
    for i, v in enumerate(visuals, index_offset):
        n = max(1, round((v["start"] + v["dur"]) * FPS) - round(v["start"] * FPS))
        out = os.path.join(clip_dir, f"{i:03d}_{v['id']}_{n}f.mp4")
        paths.append(out)
        path, src = find_visual(ep, v["id"])
        if os.path.exists(out) and (path or not force_graphics) and clip_frames(out) == n:
            continue
        if path:
            scene_clip(path, n, i, out, credit=credit_text(src) if src else None)
        else:
            spec = dict(v.get("spec") or gspec[v["id"]])
            if spec.get("bg"):
                bg_path = find_visual(ep, spec["bg"])[0]
                spec["bg"] = os.path.abspath(bg_path) if bg_path else None  # 背景不是图片（例如章节首个画面是图表卡）时用默认底色
            G2.render_clip(spec, n / FPS, out, preview_png=os.path.join(prev_dir, v["id"] + ".png"), frames=n)
        print(f"  画面 {i + 1}/{len(visuals)} {v['id']} {v['dur']:.1f}s", flush=True)
    return paths


# ---------- 字幕对齐 ----------

def speech_mask(audio, hop=0.01):
    """10ms 一帧的说话/静音判定。"""
    k = int(SR * hop)
    n = len(audio) // k
    rms = np.sqrt(np.mean(audio[: n * k].reshape(n, k) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms / (rms.max() + 1e-12))
    return db > -38, hop


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
    """把每个标点对齐到最接近的真实停顿，回传每个字元位置的时间（秒）。"""
    onset, offset, gaps = pauses(audio)
    anchors = [(0, onset)]
    used = set()
    est = {pos: (b, e) for pos, b, e in est_times}
    for j, ch in enumerate(text):
        if ch not in PUNCT or j == len(text) - 1:
            continue
        guess = est.get(j, (None, None))[1]
        if guess is None:
            continue
        cand = [(abs((g0 + g1) / 2 - guess), k) for k, (g0, g1) in enumerate(gaps)
                if k not in used and abs((g0 + g1) / 2 - guess) < 0.9 and g0 > anchors[-1][1]]
        if cand:
            _, k = min(cand)
            used.add(k)
            anchors += [(j, gaps[k][0]), (j + 1, gaps[k][1])]
    anchors.append((len(text), offset))
    anchors.sort()
    wts = spoken_weights(text)
    cum = np.concatenate([[0.0], np.cumsum([0.0 if ch in PUNCT else wt for ch, wt in zip(text, wts)])])
    xs = np.array([cum[a] for a, _ in anchors], np.float64)
    ys = np.maximum.accumulate(np.array([b for _, b in anchors], np.float64))
    return lambda i: float(np.interp(cum[min(int(i), len(text))], xs, ys))


def build_subs(paras, split_chunks, clean_sub, sub_max, decode):
    events = []
    for p in paras:
        audio = p["audio"] if "audio" in p else decode(p["mp3"])
        t_at = align_paragraph(p["text"], p["times"], audio)
        for a, b in split_chunks(p["text"]):
            txt = clean_sub(p["text"][a:b])
            if not txt:
                continue
            end_idx = b - 1 if p["text"][b - 1:b] in PUNCT else b
            start = p["start"] + t_at(a) - 0.06  # 略早出现
            end = p["start"] + t_at(end_idx)
            events.append([start, max(end, start + 0.3), txt])
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

    def cut(a, b):
        body_end = b
        while body_end > a and text[body_end - 1] in PUNCT:
            body_end -= 1
        if body_end - a <= sub_max:
            return [(a, b)]
        mid = (a + body_end) / 2
        cands = [k for k in bounds if a + 2 <= k <= body_end - 2]
        k = min(cands, key=lambda k: abs(k - mid)) if cands else int(mid)
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


_DIG = "零一二三四五六七八九"


def _cn_int(n):
    """整数的中文读法（如 1250 → 一千两百五十），只用来估计读音长度。"""
    if n == 0:
        return "零"

    def sec(k):  # 0 < k < 10000
        out, zero = "", False
        for u, name in ((1000, "千"), (100, "百"), (10, "十"), (1, "")):
            d, k = divmod(k, u)
            if d:
                if zero:
                    out += "零"
                    zero = False
                out += ("" if (name == "十" and d == 1 and not out) else _DIG[d]) + name
            elif out:
                zero = True
        return out
    out = ""
    for base, name in ((10 ** 8, "億"), (10 ** 4, "萬")):
        q, n = divmod(n, base)
        if q:
            out += sec(q) + name
    return out + (sec(n) if n else "")


def spoken_weights(text):
    """每个字符对应的「读出来有几个音节」：数字、百分号、英文字母读起来比汉字长，
    按字数平均会让数字多的句子里字幕越来越早或越来越晚。"""
    import re
    w = [1.0] * len(text)
    for m in re.finditer(r"\d[\d,]*(?:\.\d+)?%?|[A-Za-z]+", text):
        tok = m.group(0)
        if tok[0].isdigit():
            body = tok.rstrip("%").replace(",", "")
            ip, _, fp = body.partition(".")
            nxt = text[m.end():m.end() + 1]
            n = len(ip) if (len(ip) == 4 and nxt in ("年", "財")) else len(_cn_int(int(ip)))
            n += (1 + len(fp)) if fp else 0
            n += 3 if tok.endswith("%") else 0
        else:
            n = max(1.0, len(tok) / 2.2) if len(tok) > 1 else 1.6
        for k in range(m.start(), m.end()):
            w[k] = n / (m.end() - m.start())
    return w


def est_times(text, dur):
    """按读音长度（见 spoken_weights）估计每个字的时间（供标点对齐时找最近的停顿）。"""
    wts = spoken_weights(text)
    total = sum(wt for ch, wt in zip(text, wts) if ch not in PUNCT) or 1.0
    times, acc = [], 0.0
    for i, ch in enumerate(text):
        wt = 0.0 if ch in PUNCT else wts[i]
        times.append((i, acc / total * dur, (acc + wt) / total * dur))
        acc += wt
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
        sil, onset, offset = silences(audio)
        pauses_meta = [it for it in items if "pause" in it]
        durs, mids = expected_pauses(items, onset, offset)
        chosen = match_pauses(sil, durs, mids)
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
            est = est_times(p["text"], b - a)
            paras.append({"id": p["id"], "start": t0 + max(0, a - 0.05), "text": p["text"], "times": est, "audio": seg})
            # 段内多个画面：在最接近等分点的标点处切换
            n = len(p["visuals"])
            span = vis_end - start
            cuts = [0.0]
            if n > 1:
                t_at = align_paragraph(p["text"], est, seg)
                stops = [t_at(i) for i, ch in enumerate(p["text"]) if ch in PUNCT]
                for j in range(1, n):
                    target = (b - a) * j / n
                    cuts.append(min(stops, key=lambda x: abs(x - target)) if stops else target)
            cuts.append(span)
            for j, vid in enumerate(p["visuals"]):
                visuals.append({"id": vid, "start": start + cuts[j], "dur": cuts[j + 1] - cuts[j]})
        t = t0 + len(audio) / SR + 0.6
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
