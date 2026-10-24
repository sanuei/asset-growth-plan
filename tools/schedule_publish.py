"""把已上传的私享视频设成定时公开（改 status.publishAt），其他设定原样保留。

用法: .venv/bin/python tools/schedule_publish.py <视频ID> <RFC3339 时间> [--token token_manage.json] [--channel 频道ID]
例如: .venv/bin/python tools/schedule_publish.py b91kjtIEeVk 2026-10-21T20:00:00+08:00 --channel UCq0Mqx6ij7EgVe9v7gJK2dw
需要 https://www.googleapis.com/auth/youtube 权限（token_manage.json，和 tools/set_no_ai.py 共用）；没有或过期时会打开浏览器授权。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from googleapiclient.discovery import build  # noqa: E402

from set_no_ai import WRITABLE, creds_for, save  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("publish_at", help="例如 2026-10-21T20:00:00+08:00（台湾时间 20:00）")
    ap.add_argument("--token", default=os.path.join(ROOT, "token_manage.json"))
    ap.add_argument("--channel", help="预期的频道 ID；授权时选错频道就中止")
    args = ap.parse_args()
    creds = creds_for(args.token)
    yt = build("youtube", "v3", credentials=creds)
    ch = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
    if args.channel and ch["id"] != args.channel:
        raise SystemExit(f"授权的是另一个频道（{ch['id']}），预期 {args.channel}；未做任何修改")
    save(creds, args.token)
    cur = yt.videos().list(part="status", id=args.video_id).execute()["items"][0]["status"]
    status = {k: cur[k] for k in WRITABLE if k in cur}
    status.update(privacyStatus="private", publishAt=args.publish_at)  # 定时公开必须先是私享
    status.setdefault("selfDeclaredMadeForKids", False)
    r = yt.videos().update(part="status", body={"id": args.video_id, "status": status}).execute()
    # 直接看更新的返回值：马上再 list 查，有时还没同步，会显示 publishAt 为空（2026-10-21 遇到）
    print("频道:", ch["snippet"]["title"])
    print("状态:", r["status"]["privacyStatus"], "定时公开:", r["status"].get("publishAt"))


if __name__ == "__main__":
    main()
