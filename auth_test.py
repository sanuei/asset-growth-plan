"""授权并测试 YouTube API 是否可用。

首次运行会打开浏览器让你授权，之后 token 保存在 token.json，不用再授权。
"""
import glob
import os
import stat
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(HERE, "token.json")
# upload: 上传视频；readonly: 仅用于测试时读取频道信息
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        secrets = glob.glob(os.path.join(HERE, "client_secret_*.json"))
        if not secrets:
            sys.exit("找不到 client_secret_*.json")
        flow = InstalledAppFlow.from_client_secrets_file(secrets[0], SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    os.chmod(TOKEN_PATH, stat.S_IRUSR | stat.S_IWUSR)
    return creds


def main():
    youtube = build("youtube", "v3", credentials=get_credentials())
    resp = youtube.channels().list(part="snippet,statistics", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        print("授权成功，但这个 Google 账号下没有 YouTube 频道。")
        return
    for ch in items:
        print("频道名称:", ch["snippet"]["title"])
        print("频道 ID :", ch["id"])
        print("视频数  :", ch["statistics"].get("videoCount"))
    print("API 测试通过。")


if __name__ == "__main__":
    main()
