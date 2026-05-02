---
name: chinacustoms
description: "Fetches article text from China Customs Research Center (chinacustoms-strc.cn) epidemic news (yqzx), filters the last 30 days, and merges into one TXT. Use when the user wants to download chinacustoms articles, fetch customs yqzx content, run chinacustoms_yqzx_fetch, or work with chinacustoms-strc.cn/hkzx/zhzx/yqzx."
---

# 海关总署研究中心 - 疫情资讯抓取技能

从海关总署研究中心「疫情资讯」(yqzx) 列表页抓取 30 天内的文章，逐篇请求正文页并提取正文，合并保存为同一 TXT。

## 何时使用本技能

- 用户要**抓取海关疫情资讯**、**下载 chinacustoms 文章**、**运行 chinacustoms 脚本**
- 用户提到 **yqzx**、**chinacustoms-strc.cn**、**海关研究中心**
- 用户要**改抓取天数**、**改列表/正文选择器**、**改输出路径**时，按本技能修改脚本

## 快速执行

```bash
cd chinacustoms
pip install requests beautifulsoup4
python chinacustoms_yqzx_fetch.py
```

依赖：`requests`、`beautifulsoup4`。无需登录、无需浏览器。

## 抓取逻辑（简要）

1. **列表**：请求 `LIST_URL`（yqzx 列表页），用 BeautifulSoup 在右侧内容区（class 含 `listCon_R`/`conRight`/`list.*R`）找所有 `a[href*="yqzx"]` 且以 `.html` 结尾的链接，排除列表页自身 `/yqzx/index.html`。日期从标题正则、或父节点 `li`/`span`/`div` 中解析（支持 `YYYY-MM-DD`、`YYYY.MM.DD`、`YYYY/MM/DD`）。按 href+标题去重。
2. **筛选**：只保留日期在**最近 30 天**内的项（`DAYS` 可改）；无日期条目当前不纳入。
3. **正文**：对每条 `urljoin(BASE_URL, href)` 得到正文页 URL，`requests.get` 拉取 HTML，用 `extract_article_body` 依次尝试选择器（`div.easysite-news-content`、`div.TRS_Editor`、`div.eps-portlet-body` 等），取到长度 >80 的文本则用 `normalize_paragraphs` 整理（句末换行）；若无则回退到 body 去掉 script/style/nav/header/footer 后取文本。
4. **输出**：所有条目按「标题 + URL + 日期 + 正文」写入同一文件 `chinacustoms_yqzx_30days.txt`，多条之间用分隔线区分。

## 配置项（脚本内）

| 变量 | 含义 | 默认 |
|------|------|------|
| `BASE_URL` | 站点根地址 | http://www.chinacustoms-strc.cn |
| `LIST_URL` | 疫情资讯列表页 | .../hkzx/zhzx/yqzx/index.html |
| `DAYS` | 抓取最近几天的文章 | 30 |
| `OUTPUT_TXT` | 输出文件名 | chinacustoms_yqzx_30days.txt |

正文选择器在 `extract_article_body` 中按优先级排列；若站点改版可增删或调整顺序。

## 输出

- 单个 TXT：`chinacustoms/chinacustoms_yqzx_30days.txt`。
- 每条含：`[序号] 标题`、`URL`、`日期`、正文；无日期显示「(无日期)」，抓取失败或未解析到正文会有相应提示。

## 修改时注意

- 列表依赖右侧区 class 正则 `listCon_R|conRight|list.*R` 及 `href` 含 `yqzx` 且 `.html`；排除 `/yqzx/index.html`。
- 正文依赖多个 div 选择器；若新模板使用其他 class，在 `extract_article_body` 的 selector 列表中加入或提前。
