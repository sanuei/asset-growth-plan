"""《乔布斯传》系列：标题加编号、同步到 YouTube、维护播放清单（频道主 2026-10-17）。需在项目根目录运行。

用法: .venv/bin/python tools/jobs_series_sync.py [--dry-run]

输入: videos/乔布斯传系列/series.json（每条的编号 no、编号 sid、所在章文件夹、YouTube ID）
做的事（重复运行是安全的，已经做过的会跳过）：
1. 每条的 发布信息.md 正式标题末尾加编号：「……｜乔布斯传·第一章｜001 #Shorts」。
2. 把这个标题写到 YouTube（只改 title，描述、标签、分类、语言照旧回写；公开状态和定时不动）。
3. 播放清单不存在就新建（公开），把 ID 写回 series.json；按编号顺序把还没加入的视频加进去。
需要 token_manage.json（youtube 权限）。
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.getcwd(), "tools"))
from googleapiclient.discovery import build  # noqa: E402
from googleapiclient.errors import HttpError  # noqa: E402
from set_no_ai import creds_for, save  # noqa: E402

ROOT = "videos/乔布斯传系列"
NUM_RE = re.compile(r"｜\d{3} #Shorts$")


def numbered(title, no):
    if NUM_RE.search(title):
        return NUM_RE.sub(f"｜{no:03d} #Shorts", title)
    base = title[: -len(" #Shorts")] if title.endswith(" #Shorts") else title
    return f"{base}｜{no:03d} #Shorts"


def update_info_file(path, no):
    lines = open(path, encoding="utf-8").read().split("\n")
    i = lines.index("## 标题") + 1
    old = lines[i].strip()
    new = numbered(old, no)
    if len(new) > 100:
        raise ValueError(f"{path} 标题超过 100 字：{new}")
    lines[i] = new
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg_path = os.path.join(ROOT, "series.json")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    vids = sorted(cfg["videos"], key=lambda v: v["no"])

    titles = {}
    for v in vids:
        info = os.path.join(ROOT, v["chapter"], "08_Shorts", v["sid"], "发布信息.md")
        titles[v["youtube"]] = update_info_file(info, v["no"]) if not args.dry_run else numbered(
            open(info, encoding="utf-8").read().split("## 标题\n", 1)[1].split("\n", 1)[0].strip(), v["no"])
        print(f"{v['no']:03d} {v['sid']}  {titles[v['youtube']]}")
    if args.dry_run:
        return

    creds = creds_for("token_manage.json")
    save(creds, "token_manage.json")
    yt = build("youtube", "v3", credentials=creds)

    # 1) 标题
    items = yt.videos().list(part="snippet", id=",".join(titles)).execute()["items"]
    for it in items:
        sn = it["snippet"]
        want = titles[it["id"]]
        if sn["title"] == want:
            continue
        keep = {k: sn[k] for k in ("categoryId", "tags", "defaultLanguage", "defaultAudioLanguage", "description") if k in sn}
        yt.videos().update(part="snippet", body={"id": it["id"], "snippet": {**keep, "title": want}}).execute()
        print("标题已更新:", it["id"])

    # 2) 播放清单
    pl = cfg["playlist"]
    if not pl.get("id"):
        r = yt.playlists().insert(part="snippet,status", body={
            "snippet": {"title": pl["title"], "description": pl["description"], "defaultLanguage": "zh-Hans"},
            "status": {"privacyStatus": "public"}}).execute()
        pl["id"] = r["id"]
        json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("播放清单已建立:", pl["id"])
    def retry(call, tries=6):
        """新建的播放清单要过几秒才查得到（会先回 404），稍等再试。"""
        for k in range(tries):
            try:
                return call()
            except HttpError as e:
                if e.resp.status != 404 or k == tries - 1:
                    raise
                time.sleep(5 * (k + 1))

    have, token = [], None
    while True:
        r = retry(lambda: yt.playlistItems().list(part="contentDetails", playlistId=pl["id"], maxResults=50, pageToken=token).execute())
        have += [x["contentDetails"]["videoId"] for x in r["items"]]
        token = r.get("nextPageToken")
        if not token:
            break
    for pos, v in enumerate(vids):
        if v["youtube"] in have:
            continue
        retry(lambda: yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": pl["id"], "position": pos,
            "resourceId": {"kind": "youtube#video", "videoId": v["youtube"]}}}).execute())
        print(f"已加入播放清单: {v['no']:03d} {v['sid']}")
    print(f"播放清单: https://www.youtube.com/playlist?list={pl['id']}")


if __name__ == "__main__":
    main()
