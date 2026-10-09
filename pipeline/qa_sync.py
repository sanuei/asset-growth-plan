"""独立检查字幕与语音是否同步：读整条配音音轨，找出每处「开口」时间，和 SRT 每条字幕的开始时间比对。

用法: .venv/bin/python pipeline/qa_sync.py videos/EP002_xxx
判定: 每条字幕开始时间与最近一次开口的差距；|差距| > 0.2 秒视为不同步。
"""
import os
import re
import sys
import wave

import numpy as np


def load_wav(path):
    with wave.open(path) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    return (x.reshape(-1, ch).mean(axis=1) if ch > 1 else x), sr


def onsets(x, sr, hop=0.01, floor_db=-38, min_gap=0.07):
    k = int(sr * hop)
    n = len(x) // k
    rms = np.sqrt(np.mean(x[: n * k].reshape(n, k) ** 2, axis=1) + 1e-12)
    talk = 20 * np.log10(rms / rms.max()) > floor_db
    out, silent_run = [], 999
    for i, t in enumerate(talk):
        if t and silent_run * hop >= min_gap:
            out.append(i * hop)
        silent_run = 0 if t else silent_run + 1
    return np.array(out)


def srt_starts(path):
    starts = []
    for m in re.finditer(r"(\d+):(\d+):(\d+),(\d+) -->", open(path, encoding="utf-8").read()):
        h, mi, s, ms = map(int, m.groups())
        starts.append(h * 3600 + mi * 60 + s + ms / 1000)
    return np.array(starts)


def main():
    ep = sys.argv[1].rstrip("/")
    x, sr = load_wav(os.path.join(ep, "02_配音/voice_full.wav"))
    ons = onsets(x, sr)
    name = os.path.basename(ep).split("_")[0]
    starts = srt_starts(os.path.join(ep, "04_字幕", name + ".srt"))
    diffs = np.array([s - ons[np.argmin(np.abs(ons - s))] for s in starts])
    bad = np.where(np.abs(diffs) > 0.2)[0]
    print(f"字幕 {len(starts)} 条；开口点 {len(ons)} 个")
    print(f"差距：中位数 {np.median(diffs):+.3f}s，平均绝对值 {np.mean(np.abs(diffs)):.3f}s，"
          f"95% 分位 {np.percentile(np.abs(diffs), 95):.3f}s，最大 {np.max(np.abs(diffs)):.3f}s")
    print(f"超过 0.2 秒：{len(bad)} 条（{len(bad) / len(starts):.1%}）")
    for i in bad[:15]:
        print(f"  #{i + 1} @ {starts[i]:.2f}s  差 {diffs[i]:+.2f}s")
    sys.exit(1 if len(bad) / len(starts) > 0.05 else 0)


if __name__ == "__main__":
    main()
