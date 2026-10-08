"""为一期视频批量生成场景图（gpt-image-2，失败时退回 gemini-3.1-flash-image）。

用法: .venv/bin/python pipeline/images_episode.py videos/EP001_xxx [--only sc_a,sc_b] [--force]

输入: <episode>/03_画面素材/场景图/prompts.json
输出: <episode>/03_画面素材/场景图/<id>.png
"""
import argparse
import base64
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ENV  # noqa: E402

FALLBACK_MODEL = "gemini-3.1-flash-image"


def request_image(model, prompt):
    body = {"model": model, "prompt": prompt, "n": 1}
    if model.startswith("gpt-image"):
        body.update(size="1536x1024", quality="auto")  # 不传 quality 时 gpt-image-2 经常返回 500
    req = urllib.request.Request(
        ENV["ABOAI_BASE_URL"].rstrip("/") + "/images/generations",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {ENV['ABOAI_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        item = json.load(r)["data"][0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    return urllib.request.urlopen(item["url"], timeout=120).read()


def generate(sid, prompt, out, force):
    if not force and os.path.exists(out):
        return sid, "skip"
    attempts = [ENV.get("COVER_IMAGE_MODEL", "gpt-image-2")] * 3 + [FALLBACK_MODEL] * 2
    last = None
    for i, model in enumerate(attempts):
        try:
            data = request_image(model, prompt)
            with open(out, "wb") as f:
                f.write(data)
            return sid, f"ok ({model})"
        except (urllib.error.URLError, TimeoutError, KeyError) as e:
            last = e
            time.sleep(2 + 2 * i)
    return sid, f"FAIL {last}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    folder = os.path.join(args.episode, "03_画面素材/场景图")
    spec = json.load(open(os.path.join(folder, "prompts.json"), encoding="utf-8"))
    only = set(args.only.split(",")) if args.only else None
    jobs = [(sid, f"{p} {spec['style']}", os.path.join(folder, f"{sid}.png"))
            for sid, p in spec["scenes"].items() if not only or sid in only]

    failed = []
    with cf.ThreadPoolExecutor(args.workers) as ex:
        for sid, status in ex.map(lambda j: generate(*j, args.force), jobs):
            print(f"{sid}: {status}", flush=True)
            if status.startswith("FAIL"):
                failed.append(sid)
    print("失败:", failed or "无")


if __name__ == "__main__":
    main()
