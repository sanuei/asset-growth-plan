---
name: topic-research
description: 为「資產增長計劃」频道做选题研究：从选题关键词出发，用 vidIQ 查搜索数据、用网络搜索核实时事，按固定公式打分，写入选题看板（网页）。当用户说「跑一次选题」「找选题」「更新选题库」或定时任务触发时使用。
---

# 选题研究

## 输入

- `选题关键词.md`：频道主给的核心关键词（种子）。
- `YouTube视频准则.md`：标题规则（长、利他、吸引点击、不做标题党）、繁体中文。
- `工作日志.md`：已做过的视频和频道主反馈，避免重复选题。
- 选题看板：https://claude.ai/artifact/94yFuzpcBPWDoVWWdAbdCf （数据库集合 `topics`、文档 `meta/summary`）。

## 步骤

1. **读现状**：用 `ArtifactData` 的 `list` 读出 `topics` 全部选题（含状态与 version），以及 `meta/summary`。已存在的选题不要重复新建。
2. **查额度**：调用 `vidiq_balance`。`vidiq_keyword_research` 每次 5 点；单次研究最多用 60 点，额度低于 40 点时只用网络搜索，并在报告里说明。
3. **关键词数据**：对种子关键词和上次发现的新方向，用 `vidiq_keyword_research`（`country: "TW"`）查需求、竞争、增长率。优先查还没有数据、或上次已超过 2 周的词。
4. **时事核查**：对时事类关键词（IPO、财报、监管等）用 `WebSearch` 查最新进展，记录日期与来源链接。日期或数字有冲突时，写进 `risks`，不要挑一个当事实。
5. **生成选题**：每个选题写清楚 `title`（繁体，按标题规则 40～70 字）、`angle`、`category`、`timeliness`（時事/常青）、`deadline`、`keywords`、`why_now`、`risks`、`sources`、`metrics`。
6. **打分**（与看板说明一致）：
   - 需求 = vidIQ volume 分数；用代理词（不是选题本身的词）时打 8 折，并设 `proxy_keyword: true`
   - 低竞争 = 100 − competition
   - 趋势 = 50 + 增长率/4，限制在 0～100；无数据或代理词记 50
   - 频道契合 = 自己判断（受众、深度、系列衔接、合规风险）
   - 总分 = 0.35 需求 + 0.25 低竞争 + 0.15 趋势 + 0.25 契合，四舍五入
   参考实现：`tools/选题研究/2026-10-08.py`。每次研究复制一份新日期的脚本，输出 JSON 到同名文件夹。
7. **写入看板**：用 `ArtifactData` 的 `batch` 一次写入。
   - 新选题：`set`，`status: "候選"`。
   - 已有选题：只 `update` 数据字段（`metrics`、`scores`、`score`、`why_now`、`risks`、`sources`、`deadline`），**绝不改 `status`、`episode`**；每条带上读到的 `if_version`。
   - 过期的时事选题（截止日已过、仍是「候選」）：`update` 加一条 `risks` 说明，不要删除。
   - 更新 `meta/summary`（`last_research`、`method`、`vidiq_credits_used`、`topic_count`）。
8. **记录**：在 `工作日志.md` 当天的段落里写一行研究摘要（新增几个、最高分是哪个），提交并推送（见自动推送规则）。

## 输出给用户

一段简短报告：新增或更新了哪些选题、前 3 名及理由、用了多少 vidIQ 额度、有哪些时事需要尽快做。附看板链接。

## 不要做

- 不编造搜索数据；vidIQ 没有数据就写「无资料」，或标为代理词。
- 不在标题里承诺收益、不点名推荐买卖个股或币种。
- 不改动频道主已经设定的状态。
