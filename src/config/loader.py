# -*- coding: utf-8 -*-
"""配置加载器。"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from .defaults import (
    get_default_agent_config,
    get_default_agent_scope_config,
    get_default_crawler_config,
    get_default_model_config,
    get_default_workspace_config,
)
from .types import (
    AgentConfig,
    AgentScopeConfig,
    CrawlerConfig,
    ModelConfig,
    WorkspaceConfig,
)


class ConfigLoader:
    """配置加载器。"""

    def __init__(self, config_dir: Optional[Path] = None):
        """初始化配置加载器。

        Args:
            config_dir: 配置文件目录，默认为 src/config/
        """
        if config_dir is None:
            config_dir = Path(__file__).parent
        self.config_dir = config_dir
        self.project_root = config_dir.parent.parent

    def load_env(self, env_file: str = ".env") -> None:
        """加载环境变量。

        Args:
            env_file: 环境变量文件路径
        """
        env_path = self.project_root / env_file
        if env_path.exists():
            load_dotenv(env_path)

    def load_json_config(self, config_file: str) -> Dict[str, Any]:
        """加载 JSON 配置文件。

        Args:
            config_file: 配置文件名

        Returns:
            配置字典
        """
        config_path = self.config_dir / config_file
        if not config_path.exists():
            return {}

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_env_var(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量。

        Args:
            key: 环境变量键
            default: 默认值

        Returns:
            环境变量值
        """
        return os.environ.get(key, default)

    def load_model_config(self, config_dict: Optional[Dict[str, Any]] = None) -> ModelConfig:
        """加载模型配置。

        Args:
            config_dict: 配置字典

        Returns:
            模型配置
        """
        if config_dict is None:
            config_dict = {}

        default_config = get_default_model_config()

        return ModelConfig(
            api_key=config_dict.get("api_key") or self.get_env_var("DASHSCOPE_API_KEY") or default_config.api_key,
            model_name=config_dict.get("model_name", default_config.model_name),
            enable_thinking=config_dict.get("enable_thinking", default_config.enable_thinking),
            stream=config_dict.get("stream", default_config.stream),
            temperature=config_dict.get("temperature", default_config.temperature),
            max_tokens=config_dict.get("max_tokens", default_config.max_tokens),
            top_p=config_dict.get("top_p", default_config.top_p),
        )

    def load_workspace_config(self, config_dict: Optional[Dict[str, Any]] = None) -> WorkspaceConfig:
        """加载工作区配置。

        Args:
            config_dict: 配置字典

        Returns:
            工作区配置
        """
        if config_dict is None:
            config_dict = {}

        default_config = get_default_workspace_config()

        return WorkspaceConfig(
            path=config_dict.get("path", default_config.path),
            data_dir=config_dict.get("data_dir", default_config.data_dir),
            cache_dir=config_dict.get("cache_dir", default_config.cache_dir),
            output_dir=config_dict.get("output_dir", default_config.output_dir),
        )

    def load_agent_config(self, config_dict: Optional[Dict[str, Any]] = None) -> AgentConfig:
        """加载智能体配置。

        Args:
            config_dict: 配置字典

        Returns:
            智能体配置
        """
        if config_dict is None:
            config_dict = {}

        default_config = get_default_agent_config()

        from .types import (
            IdentityConfig,
            MemoryConfig,
            SkillConfig,
            ToolConfig,
        )

        return AgentConfig(
            name=config_dict.get("name", default_config.name),
            sys_prompt=config_dict.get("sys_prompt", default_config.sys_prompt),
            model=self.load_model_config(config_dict.get("model")),
            identity=IdentityConfig(**config_dict["identity"]) if config_dict.get("identity") else default_config.identity,
            memory=MemoryConfig(**config_dict["memory"]) if config_dict.get("memory") else default_config.memory,
            tools=[ToolConfig(**t) for t in config_dict.get("tools", [])] or default_config.tools,
            skills=[SkillConfig(**s) for s in config_dict.get("skills", [])] or default_config.skills,
            max_turns=config_dict.get("max_turns", default_config.max_turns),
            verbose=config_dict.get("verbose", default_config.verbose),
        )

    def load_agent_scope_config(self, config_file: str = "config.json") -> AgentScopeConfig:
        """加载 AgentScope 配置。

        Args:
            config_file: 配置文件名

        Returns:
            AgentScope 配置
        """
        self.load_env()

        config_dict = self.load_json_config(config_file)

        default_config = get_default_agent_scope_config()

        return AgentScopeConfig(
            agent=self.load_agent_config(config_dict.get("agent")),
            workspace=self.load_workspace_config(config_dict.get("workspace")),
            env_file=config_dict.get("env_file", default_config.env_file),
            log_level=config_dict.get("log_level", default_config.log_level),
            debug=config_dict.get("debug", default_config.debug),
        )

    def load_crawler_config(self, config_dict: Optional[Dict[str, Any]] = None) -> CrawlerConfig:
        """加载爬虫配置。

        Args:
            config_dict: 配置字典

        Returns:
            爬虫配置
        """
        if config_dict is None:
            config_dict = {}

        default_config = get_default_crawler_config()

        return CrawlerConfig(
            user_agent=config_dict.get("user_agent", default_config.user_agent),
            timeout=config_dict.get("timeout", default_config.timeout),
            max_retries=config_dict.get("max_retries", default_config.max_retries),
            delay_between_requests=config_dict.get("delay_between_requests", default_config.delay_between_requests),
            respect_robots_txt=config_dict.get("respect_robots_txt", default_config.respect_robots_txt),
        )


# 全局配置加载器实例
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """获取全局配置加载器实例。"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def load_config(config_file: str = "config.json") -> AgentScopeConfig:
    """加载配置的便捷函数。

    Args:
        config_file: 配置文件名

    Returns:
        AgentScope 配置
    """
    loader = get_config_loader()
    return loader.load_agent_scope_config(config_file)
