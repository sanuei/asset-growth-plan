"""把一期视频的配音、画面、字幕、背景音乐合成为成片。

用法: .venv/bin/python pipeline/assemble.py videos/EP001_xxx [--preview 60]

输入:
  01_文案/script.json                  段落、画面安排
  02_配音/segments/<pid>.mp3/.json     配音与逐字时间戳
  03_画面素材/场景图/<id>.png          场景图
  03_画面素材/graphics.json            图表与文字卡规格
输出:
  02_配音/voice_full.wav, 02_配音/bgm.wav, 02_配音/mix.wav
  04_字幕/<EP>.srt
  06_成片/<EP>_<标题>.mp4
  07_发布信息/chapters.txt
"""
import argparse
import json
import os
import re
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import graphics as G  # noqa: E402
from config import FONT_BOLD  # noqa: E402

W, H, FPS, SR = 1920, 1080, 30, 44100
LEAD = 0.5            # 片头静音
GAP = 0.35            # 段落间停顿
SECTION_GAP = 0.7     # 章节最后一段后的停顿
TITLE_DUR = 2.4       # 章节标题卡时长
SUB_MAX = 16          # 每行字幕最多字数
SUB_STRIP_Y, SUB_STRIP_H = 860, 220
PUNCT = "，。；：、？！"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"命令失败: {' '.join(cmd[:6])} ...\n{r.stderr[-2000:]}")
    return r.stdout


def decode_mp3(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768


def write_wav(path, data, channels=1):
    data = np.clip(data, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((data * 32767).astype("<i2").tobytes())


def char_times(seg):
    """返回 [(字符位置, 开始秒, 结束秒)]。"""
    out = []
    for s in seg["subtitles"]:
        for w in s.get("timestamped_words") or []:
            out.append((w["word_begin"], w["time_begin"] / 1000, w["time_end"] / 1000))
    return out


# ---------- 时间线 ----------

def build_timeline(ep, script):
    seg_dir = os.path.join(ep, "02_配音/segments")
    t = LEAD
    visuals, audio, chapters, paras = [], [], [], []
    for sec in script["sections"]:
        chapters.append((t if sec["id"] != "s0" else 0.0, sec["chapter"]))
        if sec.get("title_card"):
            spec = {"type": "title", "text": sec["title_card"]}
            if script.get("version", 1) >= 2:
                spec["bg"] = next(v for p in sec["paragraphs"] for v in p["visuals"])
            visuals.append({"id": f"title_{sec['id']}", "start": t, "dur": TITLE_DUR, "spec": spec})
            t += TITLE_DUR
        for i, p in enumerate(sec["paragraphs"]):
            last = i == len(sec["paragraphs"]) - 1
            if "silence" in p:
                dur = p["silence"]
                visuals.append({"id": p["visuals"][0], "start": t, "dur": dur})
                t += dur
                continue
            seg = json.load(open(os.path.join(seg_dir, p["id"] + ".json"), encoding="utf-8"))
            d = seg["extra_info"]["audio_length"] / 1000
            block = d + (SECTION_GAP if last else GAP)
            audio.append((p["id"], t))
            paras.append({"id": p["id"], "start": t, "text": p["text"], "times": char_times(seg),
                          "mp3": os.path.join(seg_dir, p["id"] + ".mp3")})
            # 多个画面：在最接近等分点的标点处切换
            n = len(p["visuals"])
            cuts = [0.0]
            stops = [e for pos, b, e in char_times(seg) if p["text"][pos:pos + 1] in PUNCT]
            for k in range(1, n):
                target = d * k / n
                cuts.append(min(stops, key=lambda x: abs(x - target)) if stops else target)
            cuts.append(block)
            for k, vid in enumerate(p["visuals"]):
                visuals.append({"id": vid, "start": t + cuts[k], "dur": cuts[k + 1] - cuts[k]})
            t += block
    return visuals, audio, chapters, paras, t


# ---------- 字幕 ----------

def split_chunks(text):
    """按标点切成不超过 SUB_MAX 字的字幕块，返回 [(开始位置, 结束位置)]。"""
    pieces, start = [], 0
    for i, ch in enumerate(text):
        if ch in PUNCT:
            pieces.append((start, i + 1))
            start = i + 1
    if start < len(text):
        pieces.append((start, len(text)))
    out = []
    for a, b in pieces:
        body = text[a:b].rstrip(PUNCT)
        while len(body) > SUB_MAX:
            mid = len(body) // 2
            # 不切断数字、英文
            while 0 < mid < len(body) and re.match(r"[0-9A-Za-z.,%$]", body[mid - 1]) and re.match(r"[0-9A-Za-z.,%$]", body[mid]):
                mid += 1
            out.append((a, a + mid))
            a += mid
            body = text[a:b].rstrip(PUNCT)
        out.append((a, b))
    # 合并太短的块
    merged = []
    for a, b in out:
        if merged and len(text[merged[-1][0]:b].rstrip(PUNCT)) <= SUB_MAX and len(text[merged[-1][0]:merged[-1][1]].strip(PUNCT)) <= 3:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return merged


def clean_sub(s):
    s = s.strip().rstrip("，。；：、") or s
    return re.sub(r"[，。；：、]+", " ", s)  # 句中标点改为空格


def build_subs(paras, total):
    events = []
    for p in paras:
        times = {pos: (b, e) for pos, b, e in p["times"]}
        for a, b in split_chunks(p["text"]):
            ts = [times[i] for i in range(a, b) if i in times]
            if not ts:
                continue
            txt = clean_sub(p["text"][a:b])
            if txt:
                events.append([p["start"] + ts[0][0], p["start"] + ts[-1][1], txt])
    for i in range(len(events) - 1):  # 短间隙内延长到下一句，减少闪烁
        if events[i + 1][0] - events[i][1] < 0.35:
            events[i][1] = events[i + 1][0]
    # 太短的字幕：能合并就和下一句合并，否则延长显示并顺延下一句
    MIN_DUR = 0.7
    i = 0
    while i < len(events) - 1:
        a, b, txt = events[i]
        nxt = events[i + 1]
        if b - a < MIN_DUR and nxt[0] - b < 0.35:
            if len(txt) + 1 + len(nxt[2]) <= SUB_MAX:
                events[i] = [a, nxt[1], f"{txt} {nxt[2]}"]
                del events[i + 1]
                continue
            new_b = min(a + MIN_DUR, nxt[1] - 0.6)
            if new_b > b:
                events[i][1] = new_b
                nxt[0] = max(nxt[0], new_b)
        i += 1
    return events


def srt_time(x):
    h, m = int(x // 3600), int(x % 3600 // 60)
    s = x % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"


def render_sub_strip(text, font):
    """按准则：思源黑体 TC 粗体 56px，白字、3px 黑描边、60% 黑投影偏移 2px。"""
    img = Image.new("RGBA", (W, SUB_STRIP_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    l, t, r, b = d.textbbox((0, 0), text, font=font, stroke_width=3)
    x = (W - (r - l)) // 2 - l
    y = int(H * 0.92) - SUB_STRIP_Y - (b - t) - t
    shadow = Image.new("RGBA", (W, SUB_STRIP_H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 153), stroke_width=3, stroke_fill=(0, 0, 0, 153))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(2)))
    ImageDraw.Draw(img).text((x, y), text, font=font, fill="white", stroke_width=3, stroke_fill="black")
    return img


def build_sub_track(events, total, work, out_mov):
    font = ImageFont.truetype(FONT_BOLD, 56)
    sub_dir = os.path.abspath(os.path.join(work, "subs"))  # ffconcat 的相对路径以列表文件为基准，故用绝对路径
    os.makedirs(sub_dir, exist_ok=True)
    blank = os.path.join(sub_dir, "blank.png")
    Image.new("RGBA", (W, SUB_STRIP_H), (0, 0, 0, 0)).save(blank)
    lines, t = ["ffconcat version 1.0"], 0.0
    for i, (a, b, txt) in enumerate(events):
        if a > t:
            lines += [f"file '{blank}'", f"duration {a - t:.3f}"]
        png = os.path.join(sub_dir, f"{i:04d}.png")
        render_sub_strip(txt, font).save(png)
        lines += [f"file '{png}'", f"duration {b - a:.3f}"]
        t = b
    lines += [f"file '{blank}'", f"duration {max(0.1, total - t):.3f}", f"file '{blank}'"]
    lst = os.path.join(work, "subs.ffconcat")
    open(lst, "w", encoding="utf-8").write("\n".join(lines))
    run(["ffmpeg", "-y", "-loglevel", "error", "-safe", "0", "-f", "concat", "-i", lst, "-r", str(FPS),
         "-c:v", "qtrle", "-pix_fmt", "argb", out_mov])


# ---------- 画面 ----------

def scene_clip(img_path, n, mode, out):
    zooms = {
        0: ("1+0.10*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
        1: ("1.10-0.10*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
        2: ("1.08", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),
        3: ("1.08", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),
    }
    z, x, y = (s.format(n=n) for s in zooms[mode % 4])
    vf = (f"scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={W}x{H}:fps={FPS},format=yuv420p")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", img_path, "-vf", vf, "-frames:v", str(n),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-r", str(FPS), out])


def build_clips(ep, visuals, work, force_graphics=False):
    gspec = json.load(open(os.path.join(ep, "03_画面素材/graphics.json"), encoding="utf-8"))
    scene_dir = os.path.join(ep, "03_画面素材/场景图")
    clip_dir = os.path.join(work, "clips")
    os.makedirs(clip_dir, exist_ok=True)
    prev_dir = os.path.join(ep, "03_画面素材/图表")
    paths = []
    for i, v in enumerate(visuals):
        # 帧数按时间线绝对位置取整，避免各片段的舍入误差累积造成音画不同步
        n = max(1, round((v["start"] + v["dur"]) * FPS) - round(v["start"] * FPS))
        out = os.path.join(clip_dir, f"{i:03d}_{v['id']}_{n}f.mp4")
        paths.append(out)
        img = os.path.join(scene_dir, v["id"] + ".png")
        is_scene = os.path.exists(img)
        if os.path.exists(out) and (is_scene or not force_graphics):
            continue
        if is_scene:
            scene_clip(img, n, i, out)
        else:
            spec = v.get("spec") or gspec[v["id"]]
            G.render_clip(spec, n / FPS, out, preview_png=os.path.join(prev_dir, v["id"] + ".png"), frames=n)
        print(f"  画面 {i + 1}/{len(visuals)} {v['id']} {v['dur']:.1f}s", flush=True)
    return paths


def watermark(path):
    f = ImageFont.truetype(FONT_BOLD, 30)
    text = "資產增長計劃"
    l, t, r, b = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=f, stroke_width=1)
    img = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))  # 紧贴文字，才能准确贴右上角
    ImageDraw.Draw(img).text((2 - l, 2 - t), text, font=f, fill=(255, 255, 255, 140), stroke_width=1, stroke_fill=(0, 0, 0, 90))
    img.save(path)


# ---------- 音频 ----------

def build_audio(ep, audio, total, work, seed=7):
    seg_dir = os.path.join(ep, "02_配音/segments")
    n = int(total * SR) + SR
    voice = np.zeros(n, dtype=np.float32)
    for pid, start in audio:
        x = decode_mp3(os.path.join(seg_dir, pid + ".mp3"))
        a = int(start * SR)
        voice[a:a + len(x)] += x[: n - a]
    write_wav(os.path.join(ep, "02_配音/voice_full.wav"), voice)

    bgm_path = os.path.join(ep, "02_配音/bgm.wav")
    if not os.path.exists(bgm_path):
        run([sys.executable, os.path.join(HERE, "bgm_synth.py"), bgm_path, "--seconds", f"{total + 1:.1f}", "--seed", str(seed)])
    with wave.open(bgm_path) as w:
        bgm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32).reshape(-1, 2) / 32768
    bgm = np.pad(bgm, ((0, max(0, n - len(bgm))), (0, 0)))[:n]

    # 人声在时压低背景音乐（约 -22dB），无人声时抬高（约 -12dB），0.4 秒平滑
    def moving_avg(x, k):  # 累加和实现，O(n)
        c = np.cumsum(np.pad(x.astype(np.float64), (k // 2, k - k // 2)))
        return ((c[k:] - c[:-k]) / k)[: len(x)].astype(np.float32)

    active = moving_avg((np.abs(voice) > 0.01).astype(np.float32), int(0.25 * SR)) > 0
    gain = moving_avg(np.where(active, 0.08, 0.25).astype(np.float32), int(0.4 * SR))
    mix = bgm * gain[:, None] + voice[:, None]
    mix_path = os.path.join(ep, "02_配音/mix.wav")
    write_wav(mix_path, mix.reshape(-1), channels=2)
    return mix_path


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--preview", type=float, help="只输出前 N 秒，用于检查")
    ap.add_argument("--force-graphics", action="store_true", help="重新渲染所有图表与文字卡片段")
    args = ap.parse_args()
    ep = args.episode.rstrip("/")
    work = os.path.join(ep, "99_工作文件")
    script = json.load(open(os.path.join(ep, "01_文案/script.json"), encoding="utf-8"))

    if script.get("version", 1) >= 3:  # 整章配音：用音频里的停顿定时间轴
        import v2 as _v2
        visuals, audio, chapters, paras, total = _v2.build_timeline_long(ep, script, LEAD, TITLE_DUR, decode_mp3)
    else:
        visuals, audio, chapters, paras, total = build_timeline(ep, script)
    total += 1.0  # 结尾留白
    visuals[-1]["dur"] += 1.0
    print(f"总时长 {total / 60:.1f} 分钟，画面 {len(visuals)} 个，配音 {len(audio)} 段")

    with open(os.path.join(ep, "07_发布信息/chapters.txt"), "w", encoding="utf-8") as f:
        for t, name in chapters:
            f.write(f"{int(t // 60)}:{int(t % 60):02d} {name}\n")

    v2 = None
    if script.get("version", 1) >= 2:
        import v2  # noqa: F811  第二版：亚像素推拉、网图署名、按停顿对齐字幕
        events = v2.build_subs(paras, v2.split_chunks, clean_sub, SUB_MAX, decode_mp3)
    else:
        events = build_subs(paras, total)
    ep_name = os.path.basename(ep).split("_")[0]
    with open(os.path.join(ep, f"04_字幕/{ep_name}.srt"), "w", encoding="utf-8") as f:
        for i, (a, b, txt) in enumerate(events, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{txt}\n\n")
    print(f"字幕 {len(events)} 条，最长 {max(len(e[2]) for e in events)} 字")

    sub_mov = os.path.join(work, "subs.mov")
    build_sub_track(events, total, work, sub_mov)
    mix = build_audio(ep, audio, total, work, seed=script.get("bgm_seed", 7))
    if v2:
        for pid, off, txt in v2.sync_report(events, paras, decode_mp3):
            print(f"  同步抽查 {pid}: 字幕比开口 {off:+.2f}s「{txt}」")
        clips = v2.build_clips(ep, visuals, work, args.force_graphics)
    else:
        clips = build_clips(ep, visuals, work, args.force_graphics)

    lst = os.path.join(work, "clips.ffconcat")
    open(lst, "w", encoding="utf-8").write("ffconcat version 1.0\n" + "".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
    joined = os.path.join(work, "video_joined.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-safe", "0", "-f", "concat", "-i", lst, "-c", "copy", joined])

    wm = os.path.join(work, "watermark.png")
    watermark(wm)
    title = script["title"]
    out = os.path.join(ep, "06_成片", f"{ep_name}_{title}{'_preview' if args.preview else ''}.mp4")
    out_dur = min(args.preview, total) if args.preview else total
    fc = (f"[0:v][1:v]overlay=0:{SUB_STRIP_Y}:format=auto[v1];"
          f"[v1][2:v]overlay=W-w-40:36[v2];"
          f"[v2]fade=t=in:st=0:d=0.6,fade=t=out:st={total - 1.2:.2f}:d=1.2,format=yuv420p[v];"
          f"[3:a]loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={total - 1.5:.2f}:d=1.5[a]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", joined, "-i", sub_mov, "-loop", "1", "-i", wm, "-i", mix,
         "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{out_dur:.2f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-movflags", "+faststart", out])
    print("成片:", out)


if __name__ == "__main__":
    main()
