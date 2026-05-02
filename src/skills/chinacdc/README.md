# China CDC 数据抓取工具

从中国疾控中心网站抓取疫情相关数据。

## 文件结构

```
chinacdc/
├── SKILL.md                          # 技能说明文档
├── README.md                          # 本文件
├── chinacdc_fetch_pdfs.py            # 下载风险评估报告PDF
├── chinacdc_fetch_news.py             # 爬取疫情新闻并生成Markdown
├── requirements_chinacdc.txt           # Python依赖
└── output/                            # 输出目录
    ├── *.pdf                          # 下载的PDF报告
    └── recent_news.md                 # 生成的Markdown报告
```

## 功能说明

### 1. 下载风险评估报告 PDF（jksj02/jksj03）

从「重点传染病和突发公共卫生事件风险评估报告」栏目下载PDF文件。

**使用方法**：
```bash
pip install -r requirements_chinacdc.txt
python chinacdc_fetch_pdfs.py
```

**输出**：
- PDF文件保存在 `output/` 目录
- 文件命名格式：`jksj02_YYYYMMDD_xxx.pdf`、`jksj03_YYYYMMDD_xxx.pdf`

**配置**：
- `PAGES`：栏目列表（默认jksj02、jksj03）
- `DAYS`：抓取最近几天的报告（默认30天）
- `SAVE_DIR`：保存目录（默认output/）

### 2. 爬取疫情新闻并生成 Markdown（jksj01）

从「全国法定传染病疫情概况」栏目爬取新闻详情，生成Markdown格式报告。

**使用方法**：
```bash
pip install -r requirements_chinacdc.txt
python chinacdc_fetch_news.py
```

**输出**：
- Markdown文件保存在 `output/recent_news.md`
- 包含报告摘要和格式化的统计数据表格

**配置**：
- `days`：抓取最近几天的新闻（默认30天）
- 输出文件名：`recent_news.md`

## 依赖

- Python 3.7+
- requests >= 2.28.0
- beautifulsoup4 >= 4.11.0

## 注意事项

- 无需登录、无需浏览器
- 日期格式必须为 `YYYY-MM-DD`
- 网站改版可能需要更新选择器
