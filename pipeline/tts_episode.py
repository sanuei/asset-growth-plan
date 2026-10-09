"""按段落为一期视频生成 MiniMax 配音 + 句子级时间戳。

用法: .venv/bin/python pipeline/tts_episode.py videos/EP001_xxx [--only p01,p02] [--force]

两种模式：
- long（script.json "version" ≥ 3 的默认）：按章节把段落拼成一大段，一次合成，段落之间用 <#秒数#> 停顿标记。
  一期通常只需 1～2 次请求，语气连贯，费用与逐段相同（按字数计费）。输出 segments/c01.mp3、c01.json …
- paragraph（旧集数）：逐段合成，输出 segments/p01.mp3 …

输入: <episode>/01_文案/script.json
输出: <episode>/02_配音/segments/<pid>.mp3 和 <pid>.json（句子时间戳，毫秒）
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ENV  # noqa: E402

API_URL = "https://api.minimax.cn/v1/t2a_v2"
# 多音字修正：原文/拼音
PRONUNCIATION = ["增長/(zeng1)(zhang3)", "傳記/(zhuan4)(ji4)", "記載/(ji4)(zai3)"]


def synth(text):
    body = {
        "model": ENV.get("TTS_MODEL", "speech-2.8-hd"),
        "text": text,
        "stream": False,
        "voice_setting": {"voice_id": ENV["TTS_VOICE"], "speed": float(ENV.get("TTS_SPEED", "1.0")), "vol": 1, "pitch": 0},
        "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3", "channel": 1},
        "language_boost": "Chinese",
        "pronunciation_dict": {"tone": PRONUNCIATION},
        "subtitle_enable": True,
        "subtitle_type": "word",
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {ENV['MINIMAX_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.load(r)
    base = resp.get("base_resp", {})
    if base.get("status_code") != 0:
        raise RuntimeError(f"合成失败: {base}")
    audio = bytes.fromhex(resp["data"]["audio"])
    subs = []
    sub_url = resp["data"].get("subtitle_file")
    if sub_url:
        with urllib.request.urlopen(sub_url, timeout=120) as r:
            subs = json.load(r)
    return audio, subs, resp.get("extra_info", {})


def run_one(pid, text, outdir, force):
    mp3, js = os.path.join(outdir, f"{pid}.mp3"), os.path.join(outdir, f"{pid}.json")
    if not force and os.path.exists(mp3) and os.path.exists(js):
        return pid, "skip", None
    for attempt in range(1, 5):
        try:
            audio, subs, info = synth(text)
            with open(mp3, "wb") as f:
                f.write(audio)
            with open(js, "w", encoding="utf-8") as f:
                json.dump({"text": text, "subtitles": subs, "extra_info": info}, f, ensure_ascii=False, indent=1)
            return pid, "ok", info.get("audio_length")
        except (urllib.error.URLError, RuntimeError, TimeoutError) as e:
            if attempt == 4:
                return pid, f"FAIL {e}", None
            time.sleep(3 * attempt)


# 整段合成用的停顿（秒）。章节之间的停顿要留出章节卡的时间。
PARA_PAUSE = 0.6
SECTION_PAUSE = 0.9
TITLE_CARD = 2.4
CHUNK_CHARS = 2800  # MiniMax 建议单次 3000 字以内


def build_chunks(script):
    """回传 [{"id": "c01", "items": [{"para": id, "text": ...} | {"pause": 秒, "parts": [...]}]}]
    parts 记录合并前的每段停顿：{"kind": "gap|title|brand", "sec": 秒, "section"/"para": id}"""
    chunks, cur, size = [], [], 0

    def pause(kind, sec, **ids):
        return {"pause": sec, "parts": [{"kind": kind, "sec": sec, **ids}]}

    for sec in script["sections"]:
        sec_chars = sum(len(p.get("text", "")) for p in sec["paragraphs"])
        if cur and size + sec_chars > CHUNK_CHARS:  # 只在章节边界拆
            chunks.append(cur)
            cur, size = [], 0
        if cur:
            if sec.get("title_card"):
                cur.append(pause("title", round(SECTION_PAUSE + TITLE_CARD, 2), section=sec["id"]))
            else:
                cur.append(pause("gap", SECTION_PAUSE))
        for p in sec["paragraphs"]:
            if "silence" in p:
                cur.append(pause("brand", p["silence"], para=p["id"]))
                continue
            if cur and "text" in cur[-1]:
                cur.append(pause("gap", PARA_PAUSE))
            cur.append({"para": p["id"], "text": p["text"]})
            size += len(p["text"])
    if cur:
        chunks.append(cur)
    out = []
    for i, items in enumerate(chunks, 1):
        merged = []  # 相邻停顿合并成一个（MiniMax 不接受连续停顿标记）
        for it in items:
            if "pause" in it and merged and "pause" in merged[-1]:
                prev = merged[-1]
                parts = [x for x in prev["parts"] + it["parts"] if x["kind"] != "gap"] or prev["parts"]
                merged[-1] = {"pause": round(sum(x["sec"] for x in parts), 2), "parts": parts}
            else:
                merged.append(it)
        while merged and "pause" in merged[0]:
            merged.pop(0)
        while merged and "pause" in merged[-1]:
            merged.pop()
        out.append({"id": f"c{i:02d}", "items": merged})
    return out


def chunk_text(items):
    return "".join(it["text"] if "text" in it else f"<#{it['pause']:.2f}#>" for it in items)


def run_long(script, outdir, force):
    total_ms, failed = 0, []
    for ch in build_chunks(script):
        mp3, js = os.path.join(outdir, ch["id"] + ".mp3"), os.path.join(outdir, ch["id"] + ".json")
        if not force and os.path.exists(mp3) and os.path.exists(js):
            print(f"{ch['id']}: skip")
            continue
        text = chunk_text(ch["items"])
        for attempt in range(1, 5):
            try:
                audio, subs, info = synth(text)
                open(mp3, "wb").write(audio)
                json.dump({"text": text, "items": ch["items"], "subtitles": subs, "extra_info": info},
                          open(js, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                ms = info.get("audio_length", 0)
                total_ms += ms
                n = sum(1 for it in ch["items"] if "text" in it)
                print(f"{ch['id']}: ok {ms / 1000:.1f}s，{n} 段，{len(text)} 字（含停顿标记）", flush=True)
                break
            except (urllib.error.URLError, RuntimeError, TimeoutError) as e:
                if attempt == 4:
                    failed.append(ch["id"])
                    print(f"{ch['id']}: FAIL {e}")
                time.sleep(3 * attempt)
    print(f"本次合成 {total_ms / 1000:.1f}s；失败: {failed or '无'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--mode", choices=["long", "paragraph"])
    args = ap.parse_args()

    script = json.load(open(os.path.join(args.episode, "01_文案/script.json"), encoding="utf-8"))
    outdir = os.path.join(args.episode, "02_配音/segments")
    os.makedirs(outdir, exist_ok=True)
    mode = args.mode or ("long" if script.get("version", 1) >= 3 else "paragraph")
    if mode == "long":
        run_long(script, outdir, args.force)
        return
    only = set(args.only.split(",")) if args.only else None
    jobs = [(p["id"], p["text"]) for s in script["sections"] for p in s["paragraphs"]
            if "text" in p and (not only or p["id"] in only)]

    total_ms, failed = 0, []
    with cf.ThreadPoolExecutor(args.workers) as ex:
        for pid, status, ms in ex.map(lambda j: run_one(*j, outdir, args.force), jobs):
            print(f"{pid}: {status}" + (f" {ms / 1000:.1f}s" if ms else ""), flush=True)
            total_ms += ms or 0
            if status.startswith("FAIL"):
                failed.append(pid)
    print(f"本次合成 {total_ms / 1000:.1f}s；失败: {failed or '无'}")


if __name__ == "__main__":
    main()
