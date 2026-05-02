---
name: who-disease-outbreak
description: "Fetches WHO Disease Outbreak News list page with Playwright, takes the first N items (default 3), opens each detail URL and extracts article body, then merges into one TXT. Use when the user wants to download WHO outbreak news, run who_disease_outbreak_fetch, or work with who.int/emergencies/disease-outbreak-news."
---

# WHO Disease Outbreak News 抓取技能

从 WHO Disease Outbreak News 列表页用 Playwright 取前 N 条，逐条打开详情页并提取正文，合并保存为同一 TXT。无需登录。

## 何时使用本技能

- 用户要**抓取 WHO 疫情新闻**、**下载 WHO outbreak news**、**运行 who 脚本**
- 用户提到 **who.int**、**Disease Outbreak News**、**disease-outbreak-news**
- 用户要**改抓取条数**、**改列表/详情选择器**、**改输出路径**时，按本技能修改脚本

## 快速执行

```bash
cd who
pip install playwright
playwright install chromium
python who_disease_outbreak_fetch.py
```

有头模式：`HEADLESS=0 python who_disease_outbreak_fetch.py`（或先设环境变量再运行）。

## 抓取逻辑（简要）

1. **列表页**：打开 `https://www.who.int/emergencies/disease-outbreak-news`，等待 Kendo 渲染；用 `a.sf-list-vertical__item` 取列表项，取前 **3** 条（`limit` 在 `get_list_items(page, limit=3)` 可改）。每条取 `href`（相对路径则拼为 `https://www.who.int/...`）、`.sf-list-vertical__title`、`.sf-list-vertical__date`。
2. **详情**：对每条若 `href` 含 `item/` 则 `page.goto(href)` 进入详情页，用 `get_article_content` 依次尝试选择器（`main .sf-content-block`、`main article`、`main`、`article` 等），要求文本长度 >200 且排除导航（前 500 字含 "Health Topics" 且全文较短则跳过）；若无则用 JS 在 body 下找最大文本块（排除含 "Health Topics" 与 "Countries" 的节点、排除含 nav 的节点）。
3. **输出**：所有条目写入同一 TXT：`who_disease_outbreak_YYYYMMDD.txt`，每条含 Title、Date、URL、正文，多条之间用分隔线。无效或未含 `item/` 的链接会写 `[No valid detail URL]` 或 `[Content not captured]`。

## 配置项（脚本内）

| 变量 | 含义 | 默认 |
|------|------|------|
| `URL` | 列表页地址 | who.int/emergencies/disease-outbreak-news |
| `OUT_DIR` | 输出目录 | 脚本所在目录 |
| `limit` | 抓取前几条 | 3（在 `get_list_items(page, limit=3)` 调用处可改） |

列表选择器：`a.sf-list-vertical__item`、`.sf-list-vertical__title`、`.sf-list-vertical__date`。正文选择器在 `get_article_content` 中按优先级排列；若 WHO 改版可增删或调整顺序。

## 输出

- 单个 TXT：`who/who_disease_outbreak_YYYYMMDD.txt`。
- 每条：`Title:`、`Date:`、`URL:`、正文；抓取失败会写 `[Error: ...]`。

## 修改时注意

- 列表依赖 Kendo 渲染的 `a.sf-list-vertical__item`；若页面改版需调整 `get_list_items` 中的选择器。
- 详情链接需含 `item/` 才会 goto；若 WHO 改用其他路径需改该判断。
- 正文依赖 `main .sf-content-block` 等及 JS 最大文本块；若详情页结构变化需调整 `get_article_content`。
