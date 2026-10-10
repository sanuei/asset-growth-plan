"""上传频道背景图（横幅）。

需要「管理频道」权限（youtube），和上传视频用的 token.json 分开存在 token_manage.json。
第一次运行会打开浏览器授权，请选择要设置的频道。上传前会核对频道 ID 和 .env 的 YOUTUBE_CHANNEL_ID 一致。

用法:
    .venv/bin/python tools/set_banner.py 频道素材/频道背景图.jpg
"""
import glob
import os
import stat
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from config import ENV  # noqa: E402

TOKEN_PATH = os.path.join(ROOT, "token_manage.json")
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def credentials():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES) if os.path.exists(TOKEN_PATH) else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        secrets = glob.glob(os.path.join(ROOT, "client_secret_*.json"))
        flow = InstalledAppFlow.from_client_secrets_file(secrets[0], SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    os.chmod(TOKEN_PATH, stat.S_IRUSR | stat.S_IWUSR)
    return creds


def main():
    path = sys.argv[1]
    yt = build("youtube", "v3", credentials=credentials())
    ch = yt.channels().list(part="brandingSettings,snippet", mine=True).execute()["items"][0]
    if ch["id"] != ENV["YOUTUBE_CHANNEL_ID"]:
        sys.exit(f"授权的频道是「{ch['snippet']['title']}」({ch['id']})，不是 .env 里的频道，已停止。")
    url = yt.channelBanners().insert(media_body=MediaFileUpload(path, mimetype="image/jpeg")).execute()["url"]
    branding = ch["brandingSettings"]  # 保留原有的频道设置，只改背景图
    branding.setdefault("image", {})["bannerExternalUrl"] = url
    yt.channels().update(part="brandingSettings", body={"id": ch["id"], "brandingSettings": branding}).execute()
    print(f"已设置「{ch['snippet']['title']}」的频道背景图")


if __name__ == "__main__":
    main()
