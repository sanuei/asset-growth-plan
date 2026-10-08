# 资产增长计划

理财科普 YouTube 频道「資產增長計劃」的自动化制作与上传工具。

**第一次看、或忘了怎么用，先读 [使用手册.md](使用手册.md)。**

| 文档 | 内容 |
|---|---|
| [使用手册.md](使用手册.md) | 整体流程、常用说法、重要链接、文件夹说明、常见问题 |
| [YouTube视频准则.md](YouTube视频准则.md) | 频道规则：语言、标题、字幕、封面、素材、合规 |
| [工作日志.md](工作日志.md) | 按日期记录进展、反馈与待改进 |
| [选题关键词.md](选题关键词.md) | 核心关键词与发散关键词 |
| [选题看板](https://claude.ai/artifact/94yFuzpcBPWDoVWWdAbdCf) | 网页选题库，在这里选定下一期 |

## 选题工具

- 看板源码：`tools/选题看板.html`（已发布为网页，数据存在看板自带的数据库里）。
- 研究流程：`.claude/skills/topic-research/SKILL.md`。对 Claude 说「跑一次选题」即可。
- 每次研究的原始数据与评分脚本：`tools/选题研究/<日期>/`。

## 脚本

| 文件 | 作用 |
|---|---|
| `auth_test.py` | YouTube OAuth 授权，生成 `token.json` 并测试频道读取 |
| `upload.py` | 上传视频（默认私享），支持标签、缩略图、定时发布、AI 内容披露 |
| `tts_minimax.py` | MiniMax 语音合成配音 |
| `cover.py` | gpt-image-2 生成人物背景 + 程序叠加繁体文字，输出 1280×720 封面 |
| `config.py` | 读取 `.env` 配置 |

## 视频制作流水线（`pipeline/`）

每期视频一个文件夹：`videos/EPxxx_标题/`，结构见 `videos/EP001_*/说明.md`。

| 步骤 | 脚本 | 作用 |
|---|---|---|
| 1 | `pipeline/tts_episode.py` | 按 `01_文案/script.json` 逐段配音，附逐字时间戳 |
| 2 | `pipeline/images_episode.py` | 按 `03_画面素材/场景图/prompts.json` 生成场景图 |
| 3 | `pipeline/assemble.py` | 合成：场景图动画、动态图表、章节卡、字幕、背景音乐、响度标准化，导出成片、SRT、章节 |
| — | `pipeline/graphics.py` | 动态图表与文字卡渲染器 |
| — | `pipeline/bgm_synth.py` | 程序合成无版权背景音乐 |

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
