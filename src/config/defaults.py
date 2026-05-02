# -*- coding: utf-8 -*-
"""默认配置值。"""
from pathlib import Path
from .types import (
    AgentConfig,
    AgentScopeConfig,
    AnalyzerConfig,
    CrawlerConfig,
    FormatterConfig,
    GeneratorConfig,
    IdentityConfig,
    MemoryConfig,
    ModelConfig,
    ReportConfig,
    SkillConfig,
    ToolConfig,
    ToolFunctionConfig,
    ToolkitConfig,
    WorkspaceConfig,
)


def get_default_model_config() -> ModelConfig:
    """获取默认模型配置。"""
    return ModelConfig(
        api_key="",
        model_name="qwen3-max",
        enable_thinking=False,
        stream=True,
        temperature=0.7,
        max_tokens=4096,
        top_p=0.9,
    )


def get_default_identity_config() -> IdentityConfig:
    """获取默认身份配置。"""
    return IdentityConfig(
        name="Friday",
        emoji="🤖",
        description="一个专业的数据抓取和分析助手",
    )


def get_default_memory_config() -> MemoryConfig:
    """获取默认记忆配置。"""
    return MemoryConfig(
        type="InMemoryMemory",
        max_turns=100,
        max_tokens=10000,
    )


def get_default_tool_configs() -> list[ToolConfig]:
    """获取默认工具配置。"""
    return [
        ToolConfig(name="execute_python_code", enabled=True),
        ToolConfig(name="view_file_tool", enabled=True),
        ToolConfig(name="kb_search_tool", enabled=True),
        ToolConfig(name="save_to_file_tool", enabled=True),
    ]


def get_default_skill_configs() -> list[SkillConfig]:
    """获取默认技能配置。"""
    # 使用相对于项目根目录的路径
    project_root = Path(__file__).parent.parent.parent
    skills_root = project_root / "src" / "skills"
    return [
        SkillConfig(path=str(skills_root / "chinacdc"), enabled=True),
        SkillConfig(path=str(skills_root / "chinacustoms"), enabled=True),
        SkillConfig(path=str(skills_root / "promedmail"), enabled=True),
        SkillConfig(path=str(skills_root / "who"), enabled=True),
    ]


def get_default_agent_config() -> AgentConfig:
    """获取默认智能体配置。"""
    return AgentConfig(
        name="Friday",
        # 👇👇👇 重点修改了 sys_prompt 👇👇👇
        sys_prompt="""你是一个名为Friday的AI助手，你的核心能力是网页爬取和基于向量数据库的精准知识检索。
        
        【知识库结构认知】
        后台数据库严格按照以下分类整理，请在检索时利用这些准确的Category名称：
        1. **Domestic (国内数据)**:
           - Statistics: 官方月度法定传染病统计数据（纯数据表，适合回答“发病数”、“死亡数”）。
           - RiskAssessment: 疾控中心月度风险评估（深度文字分析，适合回答“趋势”、“研判”）。
           
        2. **International (国际数据)**:
           - RiskAssessment: 全球或区域性传染病风险综述（宏观、长周期报告）。
           - Brief: 全球疫情日报、海关简讯（高频、突发、具体的境外输入或具体国家的疫情爆发信息）。
        【时间感知】
        - 你需要时刻关注当前时间，确保回答与时间相关的问题时准确无误。
        - 在分析疫情数据时，必须严格区分【数据的时间范围】（如报告涵盖的是2024年2月的数据）和【当前系统时间】。
        【核心工作流】
        **情况一：当用户想抓取网页、更新数据或获取最新未入库的信息时**
        （1）先读取 `AGENTS.md`，了解当前可用的抓取技能。
        （2）判断用户意图涉及的数据源。
        （3）使用 `execute_python_code` 工具执行 `AGENTS.md` 文件中指定的对应技能脚本命令。
        *关键：如果需要执行多个爬虫命令，请将它们合并到一个代码块中执行，避免重复劳动。*
        **情况二：当用户询问现有知识（如传染病数据、历史报告、趋势分析）时**
        （1）**不要**猜测文件名，直接使用 `kb_search_tool` 工具。
        （2）**智能参数构造**（务必准确）：
            - **question**: 必须是完整的自然语言问题（如"2024年3月百日咳的发病人数是多少"）。
            - **region** (可选): 根据问题意图锁定地域。若只问国内，设为"Domestic"；若问国外/全球/海关/某个具体国家，设为"International"；不确定则选"All"。
            - **category** (可选): 
                - 问“数据/统计表格” -> 设为 "Statistics"
                - 问“海关/通报/突发/每日疫情” -> 设为 "Brief"  <-- 修改为 Brief
                - 问“分析/风险/建议/研判” -> 设为 "RiskAssessment"
        （3）**生成回答**：
            - 回答必须严格基于检索到的【参考资料】。
            - 如果你没有在上下文中找到具体的数字，绝对不要编造。请明确说明‘该月份具体数据在文档中缺失’。
            - 必须注明数据的【时间周期】和【来源】（例如：“根据海关3月15日的日报...”）。
            - 如果检索结果中没有直接答案，请明确告知用户，不要编造。
        """, 
        # 👆👆👆 修改结束 👆👆👆
        model=get_default_model_config(),
        identity=get_default_identity_config(),
        memory=get_default_memory_config(),
        tools=get_default_tool_configs(),
        skills=get_default_skill_configs(),
        max_turns=100,
        verbose=False,
    )


def get_default_workspace_config() -> WorkspaceConfig:
    """获取默认工作区配置。"""
    return WorkspaceConfig(
        path="../KnowledgeBase",
        data_dir="data",
        cache_dir="cache",
        output_dir="output",
    )


def get_default_agent_scope_config() -> AgentScopeConfig:
    """获取默认 AgentScope 配置。"""
    return AgentScopeConfig(
        agent=get_default_agent_config(),
        workspace=get_default_workspace_config(),
        env_file=".env",
        log_level="INFO",
        debug=False,
    )


def get_default_crawler_config() -> CrawlerConfig:
    """获取默认爬虫配置。"""
    return CrawlerConfig(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        timeout=30,
        max_retries=3,
        delay_between_requests=1.0,
        respect_robots_txt=True,
    )


def get_default_analyzer_config() -> AnalyzerConfig:
    """获取默认分析器配置。"""
    return AnalyzerConfig(
        language="zh",
        min_confidence=0.7,
        max_tokens=4096,
        temperature=0.3,
    )


def get_default_generator_config() -> GeneratorConfig:
    """获取默认生成器配置。"""
    return GeneratorConfig(
        model="qwen3-max",
        temperature=0.7,
        max_tokens=8192,
        top_p=0.9,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )


def get_default_report_config() -> ReportConfig:
    """获取默认报告配置。"""
    return ReportConfig(
        format="markdown",
        output_dir="reports",
        template_dir=None,
        include_metadata=True,
        timestamp_format="%Y-%m-%d %H:%M:%S",
    )


def get_default_formatter_config() -> FormatterConfig:
    """获取默认格式化器配置。"""
    return FormatterConfig(
        type="DashScopeChatFormatter",
        params={},
    )


def get_default_toolkit_config() -> ToolkitConfig:
    """获取默认工具包配置。"""
    return ToolkitConfig(
        tool_functions=[
            ToolFunctionConfig(
                function_name="kb_search_tool",
                enabled=True,
                timeout=60,
                retry_on_failure=False,
            ),
            ToolFunctionConfig(
                function_name="view_file_tool",
                enabled=True,
                timeout=60,
                retry_on_failure=False,
            ),
            ToolFunctionConfig(
                function_name="save_to_file_tool",
                enabled=True,
                timeout=60,
                retry_on_failure=False,
            ),
        ],
        agent_skills=get_default_skill_configs(),
        formatter=get_default_formatter_config(),
    )
