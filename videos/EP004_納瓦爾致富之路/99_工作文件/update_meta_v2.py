"""EP004 上線後改標題、描述、封面（频道主 2026-10-17 要求用「丟到街頭也能再變有錢」做鉤子）。需在项目根目录运行。
用法: .venv/bin/python videos/EP004_納瓦爾致富之路/99_工作文件/update_meta_v2.py [封面檔名]
只改 snippet 的 title / description，其他欄位（標籤、分類、語言）照舊回寫。
"""
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "tools"))
from googleapiclient.discovery import build  # noqa: E402
from googleapiclient.http import MediaFileUpload  # noqa: E402
from set_no_ai import creds_for, save  # noqa: E402

EP = "videos/EP004_納瓦爾致富之路"
VIDEO_ID = "2bHlbjXOqFE"
cover = sys.argv[1] if len(sys.argv) > 1 else "封面_C_丟到街頭.jpg"

title = open(f"{EP}/07_发布信息/标题.txt", encoding="utf-8").readline().strip()
description = open(f"{EP}/07_发布信息/描述.txt", encoding="utf-8").read().strip()

creds = creds_for("token_manage.json")
save(creds, "token_manage.json")
yt = build("youtube", "v3", credentials=creds)

snip = yt.videos().list(part="snippet", id=VIDEO_ID).execute()["items"][0]["snippet"]
keep = {k: snip[k] for k in ("categoryId", "tags", "defaultLanguage", "defaultAudioLanguage") if k in snip}
yt.videos().update(part="snippet", body={"id": VIDEO_ID, "snippet": {**keep, "title": title, "description": description}}).execute()
yt.thumbnails().set(videoId=VIDEO_ID, media_body=MediaFileUpload(f"{EP}/05_封面/{cover}")).execute()

after = yt.videos().list(part="snippet,status", id=VIDEO_ID).execute()["items"][0]
print("title:", after["snippet"]["title"])
print("desc first line:", after["snippet"]["description"].splitlines()[0][:40])
print("tags:", len(after["snippet"].get("tags", [])), "privacy:", after["status"]["privacyStatus"])
print("thumbnail set:", cover)
