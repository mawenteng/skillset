# src/main.py
# -*- coding: utf-8 -*-
"""代理技能示例的主入口点。"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.tool import (
    Toolkit,
    execute_python_code,
    ToolResponse,
)
# 修正相对导入问题
import sys
from pathlib import Path
# 添加src目录到路径
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))
from config import load_config

# ================= 关键路径配置 =================
# 将当前目录(src)加入路径，确保能导入 tools
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# ================= 工具导入 =================
# 1. 导入知识库搜索工具 (直接引用，不再重复编写逻辑)
from tools.kb_search import kb_search_tool

# 2. 导入文件保存工具
from tools.save_to_file import save_to_file_tool

# 3. 导入文件读取底层函数 (用于 view_file_tool)
from tools.view_file import read_pdf, read_text
# ===========================================

# 定义本地的文件查看工具 (保留路径路由逻辑)
def view_file_tool(file_path):
    """
    文件查看工具，支持查看md和PDF文档
    参数:
        file_path: 文件路径
    返回:
        文件内容的ToolResponse对象
    """
    # 检查路径是否是绝对路径，如果不是，则尝试构建完整的绝对路径
    if not os.path.isabs(file_path):
        # 获取项目根目录 (假设 main.py 在 src/ 下)
        project_root = str(Path(__file__).parent.parent)
        
        # 尝试1：使用项目根目录作为基础路径
        abs_path1 = os.path.join(project_root, file_path)
        
        # 尝试2：直接使用KnowledgeBase作为基础路径
        abs_path2 = os.path.join(project_root, "KnowledgeBase", file_path)
        
        # 尝试3：兼容 KnowledgeBase/data
        abs_path3 = os.path.join(project_root, "KnowledgeBase", "data", file_path)
        
        # 检查哪个路径存在
        if os.path.exists(abs_path1):
            file_path = abs_path1
        elif os.path.exists(abs_path2):
            file_path = abs_path2
        elif os.path.exists(abs_path3):
            file_path = abs_path3
    
    if not os.path.exists(file_path):
        return ToolResponse(content=f"错误: 文件不存在 -> {file_path}")
    
    # 获取文件后缀
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    try:
        # 路由逻辑：根据后缀决定用什么方式读
        if ext == '.pdf':
            content = read_pdf(file_path)
        else:
            # 默认都当做文本文件尝试读取 (.md, .txt, .json, .py, .log ...)
            content = read_text(file_path)
        
        # 截断过长的内容，防止撑爆上下文
        if len(content) > 10000:
             content = content[:10000] + "\n...(内容过长已截断)..."
             
        return ToolResponse(content=content)
    except Exception as e:
        return ToolResponse(content=f"读取文件出错: {str(e)}")


async def main() -> None:
    """ReAct 代理示例的主入口点。"""
    config = load_config()
    # 加载环境变量
    if hasattr(config, "env_file") and config.env_file:
        load_dotenv(config.env_file)
    else:
        load_dotenv() # 默认加载 .env

    # 强制设置 Python 环境编码
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    # ================= 工具注册 =================
    toolkit = Toolkit()

    # 1. 注册系统自带的 Python 代码执行工具
    toolkit.register_tool_function(execute_python_code)

    # 2. 注册自定义工具
    toolkit.register_tool_function(kb_search_tool)  # 知识库搜索 (已升级为向量版)
    toolkit.register_tool_function(view_file_tool)  # 文件查看
    toolkit.register_tool_function(save_to_file_tool) # 文件保存

    # 注册配置文件中的其他技能 (如有)
    if hasattr(config.agent, "skills"):
        for skill_config in config.agent.skills:
            if skill_config.enabled:
                toolkit.register_agent_skill(skill_config.path)
    # ===========================================

    # 获取当前时间
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    
    # 构建系统提示词：加入时间感知 + 强制工具使用说明
    sys_prompt_with_time = config.agent.sys_prompt + f"\n\n# 当前上下文\n系统时间: {current_time}\n\n# 关键指令\n1. 遇到询问'数据'、'情况'、'报告'、'历史信息'等问题，**必须优先**调用 `kb_search_tool`。\n2. 只有在需要精确阅读某个具体文件的全文时，才使用 `view_file_tool`。"
    
    agent = ReActAgent(
        name=config.agent.name,
        sys_prompt=sys_prompt_with_time,
        model=DashScopeChatModel(
            api_key=config.agent.model.api_key,
            model_name=config.agent.model.model_name,
            enable_thinking=config.agent.model.enable_thinking,
            stream=config.agent.model.stream,
            temperature=config.agent.model.temperature,
            max_tokens=config.agent.model.max_tokens,
            top_p=config.agent.model.top_p,
        ),
        formatter=DashScopeChatFormatter(),
        toolkit=toolkit,
        memory=InMemoryMemory(),
    )

    print("\033[1;32m代理系统提示:\033[0m")
    print(agent.sys_prompt)
    print("\n")

    print("\033[1;32m🚀 智能体已启动 (集成 LanceDB 向量知识库)\033[0m")
    print("输入 'exit' 或 'quit' 退出。\n")

    while True:
        try:
            # 每次对话更新时间，防止长时间运行时时间不准
            loop_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
            
            user_input = input("\033[1;34mUser: \033[0m").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', '退出']:
                print("\n\033[1;32m再见！\033[0m")
                break
            
            # 将时间信息注入到用户的每一轮消息中，增强时间感知
            user_message = Msg("user", f"[{loop_time}] {user_input}", "user")
            
            print("\033[1;32mFriday: \033[0m", end="", flush=True)
            response = await agent(user_message)
            print()
            
        except KeyboardInterrupt:
            print("\n\n\033[1;32m程序已中断，再见！\033[0m")
            break
        except Exception as e:
            print(f"\n\033[1;31m运行时错误: {e}\033[0m")
            # 只有在调试时才取消下面的注释
            # import traceback
            # traceback.print_exc()
            continue

if __name__ == "__main__":
    asyncio.run(main())
