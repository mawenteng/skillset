---
name: chinacdc
description: "Fetches China CDC (chinacdc.cn) content: 1) Downloads risk assessment report PDFs from jksj02/jksj03 list pages, filtering by last 30 days. 2) Crawls epidemic news from jksj01, extracts details and saves as Markdown. Use when user wants to download chinacdc reports, fetch China CDC PDFs/news, run chinacdc scripts, or work with jksj01/jksj02/jksj03."
---

# China CDC 数据抓取技能

从中国疾控中心网站抓取两类内容：
1. **重点传染病和突发公共卫生事件风险评估报告**（jksj02/jksj03）：下载 PDF 文件
2. **全国法定传染病疫情概况**（jksj01）：爬取新闻详情并生成 Markdown 报告

## 何时使用本技能

- 用户要**下载 chinacdc 报告**、**抓取中国疾控 PDF**、**运行 chinacdc 脚本**
- 用户提到 **jksj01**、**jksj02**、**jksj03**、**chinacdc.cn/jksj**
- 用户要**新增栏目**、**改抓取天数**、**改保存路径**时，按本技能修改脚本
- 用户要获取**全球传染病事件风险评估报告**、**重点传染病和突发公共卫生事件风险评估报告**、**全国法定传染病疫情情况**时

## 快速执行

### 1. 下载全球传染病事件风险评估报告 PDF（jksj02）

```bash
cd chinacdc
pip install -r requirements_chinacdc.txt
python chinacdc_fetch_pdfs.py --days 60
```

### 2. 下载重点传染病和突发公共卫生事件风险评估报告 PDF（jksj03）

```bash
cd chinacdc
pip install -r requirements_chinacdc.txt
python chinacdc_fetch_pdfs.py --days 90
```

### 3. 爬取全国法定传染病疫情情况并生成报告（jksj01）

```bash
cd chinacdc
pip install -r requirements_chinacdc.txt
python chinacdc_fetch_news.py --days 30
```

依赖：`requests`、`beautifulsoup4`。无需登录、无需浏览器。

## 脚本说明

### 1. chinacdc_fetch_pdfs.py

**功能**：下载 jksj02/jksj03 栏目的风险评估报告 PDF

**抓取逻辑**：
1. **列表**：对配置中的每个栏目请求列表页 HTML，用 BeautifulSoup 解析 `ul.xw_list`，取每个 `li` 中的 `<a href="*.pdf">` 与 `<span>` 日期（格式 `YYYY-MM-DD`）。
2. **筛选**：只保留日期在**最近 30 天**内的项（`DAYS` 可改）。
3. **下载**：对每条用 `urljoin(base_url, href)` 得到 PDF 完整 URL，`requests.get(stream=True)` 下载，保存为 `{label}_{YYYYMMDD}_{basename}.pdf`，保存在脚本所在目录（`SAVE_DIR`）。

**配置项**：
| 变量 | 含义 | 默认 |
|------|------|------|
| `PAGES` | 栏目列表，每项 `(标签, 列表页URL, 基准URL)` | jksj02、jksj03 两栏 |
| `DAYS` | 抓取最近几天的报告 | 30 |
| `SAVE_DIR` | 保存目录 | output/ |

**输出**：
- 多个 PDF 文件，命名：`jksj02_20260104_xxx.pdf`、`jksj03_20260115_xxx.pdf` 等
- 所有文件保存在 `output/` 目录

### 2. chinacdc_fetch_news.py

**功能**：爬取 jksj01 栏目的全国法定传染病疫情概况，提取详情并生成 Markdown 报告

**抓取逻辑**：
1. **列表**：请求 `https://www.chinacdc.cn/jksj/jksj01/`，解析 `ul.xw_list`，提取标题（包含日期）、链接
2. **筛选**：只保留日期在**最近 30 天**内的新闻（`days` 参数可改）
3. **详情**：对每条新闻访问详情页，提取正文内容（移除表格）和统计数据表格
4. **保存**：生成 Markdown 格式报告，包含报告摘要和格式化的统计数据表格

**配置项**：
| 变量 | 含义 | 默认 |
|------|------|------|
| `days` | 抓取最近几天的新闻 | 30 |
| 输出文件名 | Markdown 文件名 | `recent_news.md` |

**输出**：
- `recent_news.md`：包含新闻标题、发布日期、原文链接、报告摘要、统计数据表格
- 表格格式化：病名清理（移除数字后缀）、数字添加千位分隔符

**数据结构**：
- 报告摘要：疫情总体情况、甲乙丙类传染病统计
- 统计数据：49种法定传染病的发病数和死亡数

## 修改时注意

### 列表结构依赖
- 依赖 `ul.xw_list` 和 `li > a`、`li > span`；若网站改版，需同步改选择器
- jksj02/jksj03：`li > a[href$=".pdf"]`、`li > span`
- jksj01：`li > a`（标题包含日期）

### 日期格式
- 必须为 `YYYY-MM-DD`，否则解析失败并筛掉

### 表格处理
- chinacdc_fetch_news.py 会先提取表格再提取正文，避免表格数据混入正文
- 表格数据会清理病名中的数字后缀（如"新型冠状病毒感染2" → "新型冠状病毒感染"）
- 数字会格式化为千位分隔符（如"7236052" → "7,236,052"）
