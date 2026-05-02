---
name: promedmail
description: "Fetches ProMED (promedmail.org) report full text by logging in, then clicking list items on the homepage so the right panel shows content; clicks \"Read full text\" when present and extracts body into one TXT. Use when the user wants to download ProMED reports, run promed_fetch_by_click, or work with ProMED login and homepage click-based scraping."
---

# ProMED 抓取技能

从 ProMED 首页通过「点击列表项 → 右侧详情」抓取报告正文（不跳转新页面）。需登录；列表无可用详情链接，只能模拟点击取右侧面板内容。

## 何时使用本技能

- 用户要**抓取 ProMED 报告**、**运行 promed 脚本**、**ProMED 登录抓取**
- 用户提到 **promedmail.org**、**ProMED**、**阅读全文**、**右侧详情**
- 用户要**改抓取条数**、**改当天/时间筛选**、**改 .env 或运行方式**时，按本技能修改脚本

## 前置：账号与依赖

- **账号**：在项目根目录或 `promedmail` 同目录建 `.env`（或设环境变量），填写 `PROMED_USER`、`PROMED_PASSWORD`。勿提交 `.env` 到 Git。可参考 `.env.promed.example`。
- **依赖**：`pip install playwright python-dotenv`，再执行 `playwright install chromium`。

## 快速执行

```bash
cd promedmail
python promed_fetch_by_click.py
```

有头模式（观察点击与右侧内容）：`HEADLESS=0 python promed_fetch_by_click.py`（或先 `set HEADLESS=0` / `$env:HEADLESS="0"` 再运行）。

## 抓取逻辑（简要）

1. **登录**：打开 `https://www.promedmail.org/auth/login`，填写 `PROMED_USER`/`PROMED_PASSWORD` 并提交，等待跳离登录页。
2. **首页**：进入 `https://www.promedmail.org/`，等待列表加载。页面为**左右布局**：左侧为 Latest Posts 表格，右侧为详情区；列表行**无可用 href**（Next.js 客户端渲染）。
3. **列表**：用 Playwright 取 `table tbody tr, table tr`，解析每行第一列为日期（如 `Fri Jan 30 2026`）、第二列为标题；跳过表头。只保留**当天**发布的项，再取**前 2 条**（条数在脚本内 `rows = [...][:2]` 可改）。
4. **正文**（不跳转）：对每条——点击该行第二列（标题）→ 等待右侧更新 → 若出现「阅读全文」/「Read full text」等按钮则点击并等待 → 从右侧详情区取正文（先找「阅读全文」所在容器文本，或排除含 "Latest Posts on ProMED" 的最大文本块）。
5. **输出**：所有条目写入同一 TXT：`promed_by_click_YYYYMMDD.txt`，每条含 Title、Date、正文，多条之间用分隔线。

## 配置与可改点（脚本内）

| 项 | 含义 | 说明 |
|----|------|------|
| `BASE` / `LOGIN_PATH` | 站点与登录路径 | 默认 promedmail.org 与 /auth/login |
| `OUT_DIR` | 输出目录 | 脚本所在目录 |
| 抓取条数 | 当天前 N 条 | 当前为 `rows = [...][:2]`，改数字即可 |
| 时间范围 | 仅当天 | 过滤条件 `parse_date(r["date"]) == today`，可改为多天或全部 |

「阅读全文」按钮文案在 `READ_FULL_TEXTS` 中（中英文）；右侧正文提取在 `get_right_panel_text`（选择器与 JS 排除左侧列表）。

## 输出

- 单个 TXT：`promedmail/promed_by_click_YYYYMMDD.txt`。
- 每条：`Title:`、`Date:`、正文；若未取到正文会写 `[No content captured]` 或 `[Error: ...]`。

## 修改时注意

- 登录依赖 `.env` 或环境变量；运行脚本时当前工作目录需能读到 `.env`（若 .env 在项目根，从根目录执行 `python promedmail/promed_fetch_by_click.py` 即可）。
- 列表依赖 `table tr` 及两列（日期、标题）；若首页改版需调整 `get_list_rows`。
- 右侧内容依赖「阅读全文」按钮或排除 "Latest Posts on ProMED" 的文本块；若页面结构变化需调整 `get_right_panel_text` 或 `click_read_full_if_present`。
