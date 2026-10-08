"""按段落为一期视频生成 MiniMax 配音 + 句子级时间戳。

用法: .venv/bin/python pipeline/tts_episode.py videos/EP001_xxx [--only p01,p02] [--force]

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    script = json.load(open(os.path.join(args.episode, "01_文案/script.json"), encoding="utf-8"))
    outdir = os.path.join(args.episode, "02_配音/segments")
    os.makedirs(outdir, exist_ok=True)
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
