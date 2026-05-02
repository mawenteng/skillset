# -*- coding: utf-8 -*-
"""AgentScope 配置类型定义。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class ModelConfig:
    """模型配置。"""

    api_key: str
    model_name: str
    enable_thinking: bool = False
    stream: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None


@dataclass
class IdentityConfig:
    """智能体身份配置。"""

    name: str
    emoji: Optional[str] = None
    description: Optional[str] = None


@dataclass
class MemoryConfig:
    """记忆配置。"""

    type: str = "InMemoryMemory"
    max_turns: Optional[int] = None
    max_tokens: Optional[int] = None


@dataclass
class ToolConfig:
    """工具配置。"""

    name: str
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillConfig:
    """技能配置。"""

    path: str
    enabled: bool = True
    tools: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """智能体配置。"""

    name: str
    sys_prompt: str
    model: ModelConfig
    identity: Optional[IdentityConfig] = None
    memory: Optional[MemoryConfig] = None
    tools: List[ToolConfig] = field(default_factory=list)
    skills: List[SkillConfig] = field(default_factory=list)
    max_turns: Optional[int] = None
    verbose: bool = False


@dataclass
class WorkspaceConfig:
    """工作区配置。"""

    path: str
    data_dir: str = "data"
    cache_dir: str = "cache"
    output_dir: str = "output"


@dataclass
class AgentScopeConfig:
    """AgentScope 主配置。"""

    agent: AgentConfig
    workspace: WorkspaceConfig
    env_file: str = ".env"
    log_level: str = "INFO"
    debug: bool = False


@dataclass
class SkillMetadata:
    """技能元数据。"""

    name: str
    version: str
    description: str
    author: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    requires_auth: bool = False


@dataclass
class WorkflowConfig:
    """工作流配置。"""

    name: str
    description: str
    steps: List[Dict[str, Any]]
    enabled: bool = True
    retry_on_failure: bool = False
    max_retries: int = 3


@dataclass
class ToolFunctionConfig:
    """工具函数配置。"""

    function_name: str
    enabled: bool = True
    timeout: int = 30
    retry_on_failure: bool = False
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FormatterConfig:
    """格式化器配置。"""

    type: str = "DashScopeChatFormatter"
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolkitConfig:
    """工具包配置。"""

    tool_functions: List[ToolFunctionConfig] = field(default_factory=list)
    agent_skills: List[SkillConfig] = field(default_factory=list)
    formatter: Optional[FormatterConfig] = None


@dataclass
class DataSourceConfig:
    """数据源配置。"""

    name: str
    type: str
    url: Optional[str] = None
    api_key: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportConfig:
    """报告配置。"""

    format: str = "markdown"
    output_dir: str = "reports"
    template_dir: Optional[str] = None
    include_metadata: bool = True
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class CrawlerConfig:
    """爬虫配置。"""

    user_agent: str = "Mozilla/5.0"
    timeout: int = 30
    max_retries: int = 3
    delay_between_requests: float = 1.0
    respect_robots_txt: bool = True


@dataclass
class AnalyzerConfig:
    """分析器配置。"""

    language: str = "zh"
    min_confidence: float = 0.7
    max_tokens: Optional[int] = None
    temperature: float = 0.3


@dataclass
class GeneratorConfig:
    """生成器配置。"""

    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
