"""从 Wikimedia Commons 下载可商用的真实图片，并记录作者与授权（网图优先原则）。

用法: .venv/bin/python pipeline/web_images.py videos/EP002_xxx [--force]

输入: <episode>/03_画面素材/网络图片/web_images.json
  {"web_gupta": {"search": "Rajat Kumar Gupta Davos", "match": "Rajat Kumar Gupta"}, ...}
  search = Commons 搜索词；match = 文件名必须包含的文字（避免拿错图）
输出: <episode>/03_画面素材/网络图片/<id>.jpg 和 sources.json（作者、授权、原图链接，用于视频描述署名）
"""
import argparse
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
UA = "AssetGrowthPlan/1.0 (YouTube education channel; image credits recorded)"
# 只接受可商用的授权
ALLOWED = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? [0-9.]+|cc by(-sa)?|no restrictions)", re.I)


def api(params, retries=5):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
            if body.strip():
                return json.loads(body)
        except Exception:  # noqa: BLE001 - 限流或网络抖动时重试
            pass
        time.sleep(3 * (i + 1))
    raise RuntimeError(f"Commons API 无响应: {params}")


def resolve(search, match):
    d = api({"action": "query", "list": "search", "srnamespace": 6, "srlimit": 10, "srsearch": search})
    for r in d["query"]["search"]:
        if match.lower() in r["title"].lower():
            return r["title"]
    raise RuntimeError(f"找不到符合「{match}」的图片（搜索：{search}）")


def info(title):
    d = api({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|size|extmetadata",
             "iiurlwidth": 2400, "iiextmetadatafilter": "LicenseShortName|Artist|Credit|LicenseUrl"})
    page = next(iter(d["query"]["pages"].values()))
    ii = page["imageinfo"][0]
    m = ii.get("extmetadata", {})
    clean = lambda k: re.sub(r"<[^>]+>", "", m.get(k, {}).get("value", "")).strip()  # noqa: E731
    return {
        "title": title, "url": ii.get("thumburl") or ii["url"], "page": ii["descriptionurl"],
        "license": clean("LicenseShortName"), "license_url": clean("LicenseUrl"),
        "artist": re.sub(r"\s+", " ", clean("Artist"))[:120] or "Unknown",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    folder = os.path.join(args.episode, "03_画面素材/网络图片")
    spec = json.load(open(os.path.join(folder, "web_images.json"), encoding="utf-8"))
    src_path = os.path.join(folder, "sources.json")
    sources = json.load(open(src_path, encoding="utf-8")) if os.path.exists(src_path) else {}

    for wid, s in spec.items():
        out = os.path.join(folder, wid + ".jpg")
        if os.path.exists(out) and wid in sources and not args.force:
            print(f"{wid}: skip")
            continue
        try:
            meta = info(resolve(s["search"], s["match"]))
            if not ALLOWED.match(meta["license"]):
                print(f"{wid}: 跳过，授权不可商用（{meta['license']}）")
                continue
            req = urllib.request.Request(meta["url"], headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=120).read()
            img = Image.open(io.BytesIO(data)).convert("RGB")  # 只接受真正的图片
            img.save(out, quality=94)
            sources[wid] = meta
            print(f"{wid}: ok {img.width}x{img.height} | {meta['license']} | {meta['artist'][:40]}")
        except Exception as e:  # noqa: BLE001
            print(f"{wid}: FAIL {e}")
        time.sleep(1.5)
    json.dump(sources, open(src_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
