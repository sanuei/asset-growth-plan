"""用 MiniMax 语音合成生成配音。

用法:
    .venv/bin/python tts_minimax.py "要朗读的文字" -o out.mp3
        [--voice Chinese_deep_voiced_male_nv1] [--model speech-2.8-hd] [--speed 1.0] [--emotion calm]
    .venv/bin/python tts_minimax.py -f 文案.txt -o out.mp3
"""
import argparse
import json
import sys
import urllib.request

from config import ENV

API_URL = "https://api.minimax.cn/v1/t2a_v2"


def load_key():
    if "MINIMAX_API_KEY" not in ENV:
        sys.exit(".env 里找不到 MINIMAX_API_KEY")
    return ENV["MINIMAX_API_KEY"]


def synthesize(text, voice, model, speed, emotion, fmt="mp3"):
    voice_setting = {"voice_id": voice, "speed": speed, "vol": 1, "pitch": 0}
    if emotion:
        voice_setting["emotion"] = emotion
    body = {
        "model": model,
        "text": text,
        "stream": False,
        "voice_setting": voice_setting,
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": fmt, "channel": 1},
        "language_boost": "Chinese",
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {load_key()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.load(r)
    base = resp.get("base_resp", {})
    if base.get("status_code") != 0:
        sys.exit(f"合成失败: {base}")
    return bytes.fromhex(resp["data"]["audio"]), resp.get("extra_info", {})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="?")
    p.add_argument("-f", "--file")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--voice", default=ENV.get("TTS_VOICE", "Chinese_deep_voiced_male_nv1"))
    p.add_argument("--model", default=ENV.get("TTS_MODEL", "speech-2.8-hd"))
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--emotion")
    args = p.parse_args()

    text = open(args.file, encoding="utf-8").read() if args.file else args.text
    if not text:
        sys.exit("请提供文字或 -f 文案文件")

    audio, info = synthesize(text, args.voice, args.model, args.speed, args.emotion)
    with open(args.out, "wb") as f:
        f.write(audio)
    print(f"已保存 {args.out}，时长 {info.get('audio_length', 0) / 1000:.1f}s，计费字符 {info.get('usage_characters')}")


if __name__ == "__main__":
    main()
