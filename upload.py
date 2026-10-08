"""上传视频到 YouTube（默认私享）。

用法:
    .venv/bin/python upload.py 视频.mp4 --title "标题" [--description "..."]
        [--tags 理财 投资] [--privacy private|unlisted|public]
        [--thumbnail 封面.jpg] [--publish-at 2026-10-10T20:00:00+08:00]

--publish-at 为定时发布：会强制以 private 上传，到点自动公开。
"""
import argparse
import os
import sys
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from auth_test import get_credentials

CATEGORY_FINANCE_EDU = "27"  # 27 = Education；YouTube 没有单独的「理财」分类
RETRIABLE_STATUS = {500, 502, 503, 504}
MAX_RETRIES = 8


def upload(youtube, args):
    status = {
        "privacyStatus": "private" if args.publish_at else args.privacy,
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": args.ai_generated,
    }
    if args.publish_at:
        status["publishAt"] = args.publish_at

    snippet = {
        "title": args.title,
        "description": args.description,
        "tags": args.tags,
        "categoryId": args.category,
    }
    if args.language:
        snippet["defaultLanguage"] = args.language
        snippet["defaultAudioLanguage"] = args.language
    body = {"snippet": snippet, "status": status}
    media = MediaFileUpload(args.video, chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response, retry = None, 0
    while response is None:
        try:
            progress, response = request.next_chunk()
            if progress:
                print(f"上传进度: {int(progress.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS and retry < MAX_RETRIES:
                retry += 1
                wait = 2**retry
                print(f"服务端错误 {e.resp.status}，{wait}s 后重试 ({retry}/{MAX_RETRIES})")
                time.sleep(wait)
            else:
                raise
    return response


def set_thumbnail(youtube, video_id, path):
    youtube.thumbnails().set(
        videoId=video_id, media_body=MediaFileUpload(path)
    ).execute()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--description-file", help="从文件读取描述（覆盖 --description）")
    p.add_argument("--tags", nargs="*", default=[])
    p.add_argument("--tags-file", help="从文件读取标签，每行一个")
    p.add_argument("--language", help="视频语言，例如 zh-Hant")
    p.add_argument("--category", default=CATEGORY_FINANCE_EDU)
    p.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    p.add_argument("--thumbnail")
    p.add_argument("--publish-at", help="RFC3339 时间，例如 2026-10-10T20:00:00+08:00")
    p.add_argument("--ai-generated", action="store_true", help="声明含 AI 生成/合成内容")
    args = p.parse_args()

    if not os.path.isfile(args.video):
        sys.exit(f"找不到视频文件: {args.video}")
    if args.description_file:
        args.description = open(args.description_file, encoding="utf-8").read().strip()
    if args.tags_file:
        args.tags = [t.strip() for t in open(args.tags_file, encoding="utf-8") if t.strip()]

    youtube = build("youtube", "v3", credentials=get_credentials())
    try:
        resp = upload(youtube, args)
    except HttpError as e:
        sys.exit(f"上传失败: {e}")

    vid = resp["id"]
    print("上传完成。")
    print("视频 ID  :", vid)
    print("状态     :", resp["status"]["privacyStatus"])
    print("Studio   :", f"https://studio.youtube.com/video/{vid}/edit")

    if args.thumbnail:
        try:
            set_thumbnail(youtube, vid, args.thumbnail)
            print("缩略图已设置。")
        except HttpError as e:
            print(f"缩略图设置失败（频道可能未验证手机号）: {e}")


if __name__ == "__main__":
    main()
