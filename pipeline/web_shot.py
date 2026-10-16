"""新闻网页截图：把报道页面截成图片，用在视频的「网页截图卡」（graphics.json type: web）。免费，不调用付费服务。

用法: .venv/bin/python pipeline/web_shot.py videos/EP004_xxx [--force]

输入: <episode>/03_画面素材/网页截图/shots.json
  {"web_crash": {"url": "https://electrek.co/...", "selector": "h1", "scroll": 0}, ...}
  selector（可选）= 先滚动到这个元素（通常是标题 h1），让标题出现在画面上方
  scroll（可选）= 再往下滚的像素（想露出报道里的图片时用）
输出: <episode>/03_画面素材/网页截图/<id>.png（1280×800 视窗、2 倍清晰度）和 sources.json（网址、截图时间，写进描述的资料来源）
本机用已安装的 Google Chrome；云端没有 Chrome 时用 playwright 自带的 Chromium（cloud/setup.sh 会装）。
"""
import argparse
import datetime
import json
import os

from playwright.sync_api import sync_playwright

HIDE = """
[id*="cookie" i],[class*="cookie" i],[id*="consent" i],[class*="consent" i],[class*="newsletter" i],
[class*="paywall" i],[class*="modal" i],[class*="popup" i],[id*="onetrust" i],[class*="banner-ad" i],
iframe[src*="ads"],[aria-modal="true"],[id*="onesignal" i],[class*="onesignal" i],[class*="notification-prompt" i],
[class*="push-prompt" i],[id*="push" i][class*="prompt" i],[class*="slidedown" i],.adsbygoogle,[id*="google_ads" i],[class*="ad-slot" i],[class*="leaderboard" i] { display: none !important; }
html, body { overflow: auto !important; }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    d = os.path.join(args.episode, "03_画面素材/网页截图")
    spec = json.load(open(os.path.join(d, "shots.json"), encoding="utf-8"))
    src_path = os.path.join(d, "sources.json")
    sources = json.load(open(src_path, encoding="utf-8")) if os.path.exists(src_path) else {}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:  # noqa: BLE001  云端没有 Chrome
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=2, locale="en-US",
                                  user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                             "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
        for sid, s in spec.items():
            out = os.path.join(d, sid + ".png")
            if os.path.exists(out) and not args.force:
                continue
            page = ctx.new_page()
            try:
                page.goto(s["url"], wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(s.get("wait", 2500))
                page.add_style_tag(content=HIDE)
                if s.get("selector"):
                    el = page.locator(s["selector"]).first
                    el.wait_for(timeout=8000)
                    # 让标题出现在画面上方约 110px 处
                    page.evaluate("(e) => window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 110)", el.element_handle())
                if s.get("scroll"):
                    page.evaluate("(y) => window.scrollBy(0, y)", s["scroll"])
                page.wait_for_timeout(800)
                page.screenshot(path=out)
                sources[sid] = {"url": s["url"], "captured": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")}
                print("OK  ", sid)
            except Exception as e:  # noqa: BLE001
                print("FAIL", sid, str(e)[:150])
            finally:
                page.close()
        browser.close()
    json.dump(sources, open(src_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
