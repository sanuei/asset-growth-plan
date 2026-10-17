# 乔布斯传系列 · 文件夹规则

> 制作规格（2026-10-17 定稿）见 `YouTube视频准则.md`「十、《乔布斯传》系列 Shorts 规格」。样板：`第01章_童年/08_Shorts/C01A`、`C01B`。

以后每一章都照这个结构放。找文件时，先找章，再找条。

```
乔布斯传系列/
├── README.md                ← 本文件：文件夹规则
├── 系列计划.md              ← 整个系列的计划（96 条大纲只作参考）
├── 发布记录.md              ← 每条 Shorts 的上传日期、YouTube 链接
├── 原书/                    ← 只在本地，不进 git（有版权）
│   ├── 史蒂夫·乔布斯传（中信2011中译本）.pdf
│   └── 分章文本/ch01.txt … ch41.txt
└── 第01章_童年/             ← 一章一个文件夹：第两位数字章_章名
    ├── 分析.md              ← 开工前的精读分析（故事清单、选择理由、事实核对）
    ├── 03_画面素材/         ← 这一章所有 Shorts 共用
    │   ├── 场景图/          ← AI 插图：prompts.json + <id>.png
    │   └── 网络图片/        ← Commons 照片：web_images.json、sources.json（署名）+ <id>.jpg
    └── 08_Shorts/
        ├── shorts.json      ← 这一章每条 Shorts 的钩子、画面配置
        ├── C01A/            ← 一条 Shorts 一个文件夹
        │   ├── C01A.mp4     ← 成片（不进 git）
        │   ├── C01A.srt     ← 字幕
        │   ├── 发布信息.md  ← 标题（含备选）、描述、标签，写在同一个文件
        │   ├── 01_文案/script.json
        │   ├── 02_配音/
        │   └── 99_工作文件/
        └── C01B/ …
```

## 命名

| 东西 | 规则 | 例子 |
|---|---|---|
| 章文件夹 | `第` + 两位数章号 + `章_` + 原书章名 | `第01章_童年`、`第17章_伊卡洛斯` |
| Shorts 编号 | `C` + 两位数章号 + 字母（这一章的第几条） | `C01A`、`C01B`、`C17C` |
| AI 插图 | 编号字母小写 + `_` + 英文短名 | `a_nursery`、`b_garage` |
| 网络照片 | `web_` + 英文短名 | `web_garage`、`web_apple1` |

- 编号只在文件夹里用，画面上不出现。
- 同一张图在一条 Shorts 里用两次（换取景或推拉方向），在 `shorts.json` 的 visuals 里另起一个名字指向同一个文件（例如 `web_garage2` → `web_garage`），不复制图片文件。
- 竖图不用另外裁成方图：在 `shorts.json` 里用 `fx`、`fy` 指定取景中心。

## 每章流程

1. 精读 `原书/分章文本/chXX.txt`，写 `第XX章_章名/分析.md`。
2. 选好要做的几条，写各自的 `01_文案/script.json`（简体中文、原书译名），逐句回原文核对。
3. 找照片（`web_images.json` → `pipeline/web_images.py`），不够的再写插图提示词（`prompts.json` → `pipeline/images_episode.py`）。
4. 配音：`pipeline/tts_episode.py <章文件夹>/08_Shorts/<编号>`（每条 1 次 MiniMax 请求）。
5. 渲染：`pipeline/shorts_paper.py <章文件夹> <编号…>`（纸张风格模板，2026-10-17 起）。先用 `--stills 1,5,9` 出几张静帧检查，再正式渲染。成片在这一条的文件夹里。
   - `shorts.json` 每条写 `hook`（顶部片名纸条：kicker / title / sub / seal）、`cap_hl`（字幕金色关键词）、`beats`（镜头表）。
   - `beats` 按文案顺序，每个画面写 `at`（念到哪个词时切入）、`img`（插图或 `web_` 照片）、取景 `fx`/`fy`/`scale`/`zoom`，或 `card`（num / note / compare / doc / timeline / route / quote / list / ask），可加 `pops`（label 标签纸条、stamp 红色戳记）。片尾纸条自动加在配音结束后。
   - 节奏：平均 2～2.5 秒一切，单个画面不超过 4 秒（信息卡可到 4～5 秒）。
6. 写 `发布信息.md`（`## 标题` 第一行是正式标题，`## 备选标题`、`## 描述`、`## 标签` 每行一个），上传：
   `.venv/bin/python upload.py <编号文件夹>/<编号>.mp4 --info-file <编号文件夹>/发布信息.md --publish-at <时间>`
   上传后把 YouTube ID 和公开时间加进 `series.json`（`no` 是全系列连续编号），再运行 `.venv/bin/python tools/jobs_series_sync.py`：标题末尾自动加编号「｜001」、同步到 YouTube、加进播放清单。最后更新 `发布记录.md`。
