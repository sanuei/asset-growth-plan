"""程序合成无版权背景音乐：温暖的氛围铺底 + 稀疏钢琴音色。

用法: .venv/bin/python pipeline/bgm_synth.py 输出.wav --seconds 800 [--seed 7]
"""
import argparse
import wave

import numpy as np

SR = 44100
# 和弦进行（MIDI 音高）：Cmaj9 - Am9 - Fmaj7 - Gsus
CHORDS = [
    [48, 55, 59, 62, 64],
    [45, 52, 55, 59, 60],
    [41, 48, 52, 57, 60],
    [43, 50, 55, 57, 62],
]
CHORD_SEC = 8.0


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pad_note(freq, dur, rng):
    t = np.arange(int(dur * SR)) / SR
    sig = np.zeros_like(t)
    for detune in (-0.12, 0.0, 0.12):
        f = freq * 2 ** (detune / 12)
        phase = rng.uniform(0, 2 * np.pi)
        sig += np.sin(2 * np.pi * f * t + phase) + 0.25 * np.sin(4 * np.pi * f * t + phase)
    env = np.minimum(1, t / 2.5) * np.minimum(1, (dur - t) / 2.5)
    return sig * np.clip(env, 0, 1) / 3


def piano_note(freq, dur=4.0):
    t = np.arange(int(dur * SR)) / SR
    sig = sum(a * np.sin(2 * np.pi * freq * k * t) * np.exp(-t * (1.6 + 1.2 * k))
              for k, a in ((1, 1.0), (2, 0.45), (3, 0.18), (4, 0.08)))
    attack = np.minimum(1, t / 0.008)
    return sig * attack


def reverb(x, seconds=2.8, mix=0.35, rng=None):
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return (1 - mix) * x + mix * wet


def lowpass(x, cutoff=2200):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # 单极点低通，柔化高频
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seconds", type=float, required=True)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    total = int(args.seconds * SR)
    left, right = np.zeros(total + SR * 10), np.zeros(total + SR * 10)
    step = int(CHORD_SEC * SR)
    for ci, start in enumerate(range(0, total, step)):
        chord = CHORDS[ci % len(CHORDS)]
        for m in chord:
            note = pad_note(hz(m), CHORD_SEC + 3.0, rng) * 0.16
            pan = rng.uniform(0.35, 0.65)
            note = note[: len(left) - start]  # 最后一个和弦会超出总长
            left[start:start + len(note)] += note * (1 - pan)
            right[start:start + len(note)] += note * pan
        # 稀疏钢琴：每个和弦 2～3 个音，落在和弦高八度
        for k in rng.choice(4, size=rng.integers(2, 4), replace=False):
            m = chord[rng.integers(1, len(chord))] + 12
            t0 = start + int((k * 2.0 + rng.uniform(0, 0.3)) * SR)
            note = piano_note(hz(m)) * 0.09
            pan = rng.uniform(0.3, 0.7)
            left[t0:t0 + len(note)] += note[: len(left) - t0] * (1 - pan)
            right[t0:t0 + len(note)] += note[: len(right) - t0] * pan

    left, right = left[:total], right[:total]
    left, right = reverb(lowpass(left), rng=rng), reverb(lowpass(right), rng=rng)
    fade = int(4 * SR)
    for ch in (left, right):
        ch[:fade] *= np.linspace(0, 1, fade)
        ch[-fade:] *= np.linspace(1, 0, fade)
    stereo = np.stack([left, right], axis=1)
    stereo *= 0.5 / np.max(np.abs(stereo))
    with wave.open(args.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype("<i2").tobytes())
    print("saved", args.out, f"{args.seconds:.0f}s")


if __name__ == "__main__":
    main()
