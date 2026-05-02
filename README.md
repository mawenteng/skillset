# Skillset - 数据抓取和分析智能体

一个基于 AgentScope 的单智能体多技能架构，专注于网页爬取、内容分析和报告生成。

## 功能特性

- **多技能支持**：集成 4 个数据抓取技能
  - chinacdc: 中国疾控中心数据抓取
  - chinacustoms: 中国海关疫情数据抓取
  - promedmail: ProMED 疾病报告抓取
  - who: WHO 疾病爆发新闻抓取

- **灵活的配置系统**：支持 JSON 配置文件和环境变量
- **丰富的工具库**：HTTP 请求、文件处理、文本处理等
- **可扩展架构**：易于添加新的技能和工具

## 项目结构

```
skillset/
├── AGENTS.md            # 技能调度说明
├── src/
│   ├── agent/           # 智能体主入口
│   │   └── main.py
│   ├── config/          # 配置管理
│   │   ├── types.py     # 配置类型定义
│   │   ├── defaults.py  # 默认配置
│   │   └── loader.py    # 配置加载器
│   ├── skills/          # 技能实现
│   │   ├── AGENTS.md
│   │   ├── chinacdc/
│   │   ├── chinacustoms/
│   │   ├── promedmail/
│   │   └── who/
│   └── tools/           # 通用工具
│       ├── kb_search.py
│       ├── save_to_file.py
│       └── view_file.py
├── KnowledgeBase/       # 知识库
│   └── data/
├── docs/                # 说明文档
└── requirements.txt    # 项目依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.template` 到 `.env` 并配置：

```bash
cp .env.template .env
```

编辑 `.env` 文件：

```env
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PROMED_USER=your_promed_username_or_email
PROMED_PASSWORD=your_promed_password
```

### 3. 运行智能体

```bash
cd src/agent
python main.py
```

## 配置说明

### 配置文件

配置文件位于 `src/config/config.json`（可选），支持以下配置项：

```json
{
  "agent": {
    "name": "Friday",
    "sys_prompt": "你是一个助手...",
    "model": {
      "api_key": "",
      "model_name": "qwen3-max",
      "temperature": 0.7
    },
    "skills": [
      {"path": "../skills/chinacdc", "enabled": true},
      {"path": "../skills/chinacustoms", "enabled": true},
      {"path": "../skills/promedmail", "enabled": true},
      {"path": "../skills/who", "enabled": true}
    ]
  },
  "workspace": {
    "path": "../KnowledgeBase",
    "data_dir": "data",
    "output_dir": "output"
  }
}
```

### 环境变量

- `DASHSCOPE_API_KEY`: 通义千问 API 密钥（必需）
- `DASHSCOPE_BASE_URL`: DashScope 兼容接口基地址（可选，默认已内置）
- `PROMED_USER`: ProMED 登录账号（使用 promedmail 技能时必需）
- `PROMED_PASSWORD`: ProMED 登录密码（使用 promedmail 技能时必需）

## 技能使用

### China CDC 技能

```bash
cd src/skills/chinacdc
pip install -r requirements_chinacdc.txt
python chinacdc_fetch_pdfs.py    # 下载 PDF 报告
python chinacdc_fetch_news.py     # 爬取新闻
```

### China Customs 技能

```bash
cd src/skills/chinacustoms
python chinacustoms_yqzx_fetch.py  # 抓取疫情文章
```

### ProMED 技能

```bash
cd src/skills/promedmail
python promed_fetch_by_click.py  # 抓取 ProMED 报告
```

### WHO 技能

```bash
cd src/skills/who
python who_disease_outbreak_fetch.py  # 抓取 WHO 疾病爆发新闻
```

## 开发指南

### 添加新技能

1. 在 `src/skills/` 下创建技能目录
2. 创建 `SKILL.md` 文件定义技能元数据
3. 实现技能代码
4. 在 `src/config/defaults.py` 中添加技能配置

### 添加新工具

1. 在 `src/tools/` 下创建工具文件
2. 实现工具函数
3. 在 `src/tools/__init__.py` 中导出

## 工作流

技能调度说明定义在项目根目录 `AGENTS.md`，用于描述按需求选择和执行抓取脚本的规则。

示例：完整数据更新流程

```markdown
# Full Data Update Workflow

1. 使用 chinacdc 技能抓取最新数据
2. 使用 chinacustoms 技能抓取海关数据
3. 使用 promedmail 技能抓取 ProMED 报告
4. 使用 who 技能抓取 WHO 数据
5. 整合所有数据
6. 生成综合报告
```

## 依赖项

- agentscope: 核心框架
- requests: HTTP 请求
- beautifulsoup4: HTML 解析
- playwright: 浏览器自动化
- loguru: 日志记录
- pandas: 数据处理
- lancedb: 向量数据库存储
- openai: Embedding 接口客户端（兼容 DashScope）
- langchain: 文本切分工具（可选，未安装时会降级到简易切分）
- pypdf / pdfplumber: PDF 文本提取与转换

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
