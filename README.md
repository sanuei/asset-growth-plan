# 资产增长计划

理财科普 YouTube 频道「資產增長計劃」的自动化制作与上传工具。

内容规范见 [YouTube视频准则.md](YouTube视频准则.md)。

## 脚本

| 文件 | 作用 |
|---|---|
| `auth_test.py` | YouTube OAuth 授权，生成 `token.json` 并测试频道读取 |
| `upload.py` | 上传视频（默认私享），支持标签、缩略图、定时发布、AI 内容披露 |
| `tts_minimax.py` | MiniMax 语音合成配音 |
| `cover.py` | gpt-image-2 生成人物背景 + 程序叠加繁体文字，输出 1280×720 封面 |
| `config.py` | 读取 `.env` 配置 |

## 环境搭建

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # 然后填入真实密钥
```

还需要：

- 从 Google Cloud 下载 OAuth 桌面客户端的 `client_secret_*.json` 放到本目录，然后运行 `.venv/bin/python auth_test.py` 授权。
- 安装思源黑體繁体版 Bold / Heavy（`SourceHanSansTC-Bold.otf`、`SourceHanSansTC-Heavy.otf`）到 `~/Library/Fonts/`。
- `ffmpeg`（用于合成视频）。

`.env`、`token.json`、`client_secret_*.json` 含密钥，已在 `.gitignore` 中排除，切勿提交。
