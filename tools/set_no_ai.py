"""把频道上所有视频的「AI 使用（改变或合成内容）」改成「否」（containsSyntheticMedia=false）。
频道主 2026-10-17 要求。只改这一项，公开状态、定时时间等其他设定原样保留。

用法: .venv/bin/python tools/set_no_ai.py <token_manage.json 路径> [--channel 频道ID] [--dry-run]
（API 读不到这一项的当前值，所以每支都会写一次「否」；回传 None 是正常的。）
需要 https://www.googleapis.com/auth/youtube 权限（token_manage.json）；过期时会打开浏览器重新授权。
"""
import argparse
import glob
import os
import stat

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube"]
WRITABLE = ("privacyStatus", "publishAt", "license", "embeddable", "publicStatsViewable",
            "selfDeclaredMadeForKids", "containsSyntheticMedia")


def creds_for(path):
    creds = Credentials.from_authorized_user_file(path) if os.path.exists(path) else None
    if creds and not creds.valid and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None
    if not (creds and creds.valid):
        secret = glob.glob(os.path.join(os.path.dirname(os.path.abspath(path)), "client_secret_*.json"))[0]
        creds = InstalledAppFlow.from_client_secrets_file(secret, SCOPES).run_local_server(port=0, prompt="consent")
    return creds


def save(creds, path):
    with open(path, "w") as f:
        f.write(creds.to_json())
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("token")
    ap.add_argument("--channel", help="预期的频道 ID；授权时选错频道就中止，不改任何东西")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    creds = creds_for(args.token)
    yt = build("youtube", "v3", credentials=creds)
    ch = yt.channels().list(part="snippet,contentDetails", mine=True).execute()["items"][0]
    print("频道:", ch["snippet"]["title"], ch["id"])
    if args.channel and ch["id"] != args.channel:
        raise SystemExit(f"授权的是另一个频道（{ch['id']}），预期 {args.channel}；未做任何修改，也没覆盖 token")
    save(creds, args.token)
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, tok = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=tok).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok:
            break
    changed = 0
    for k in range(0, len(ids), 50):
        for v in yt.videos().list(part="status,snippet", id=",".join(ids[k:k + 50])).execute()["items"]:
            st = v["status"]
            flag = st.get("containsSyntheticMedia")
            print(f"  {v['id']}  {st['privacyStatus']:8} AI={flag}  {v['snippet']['title'][:40]}")
            if flag is False:
                continue
            body = {k2: st[k2] for k2 in WRITABLE if k2 in st}
            body["containsSyntheticMedia"] = False
            if not args.dry_run:
                yt.videos().update(part="status", body={"id": v["id"], "status": body}).execute()
                changed += 1
    print(f"共 {len(ids)} 支，改成「否」：{changed} 支" + ("（dry-run 未修改）" if args.dry_run else ""))


if __name__ == "__main__":
    main()
