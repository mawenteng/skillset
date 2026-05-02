from pathlib import Path

from agentscope.tool import ToolResponse

# === 配置报告保存的目录 ===
# 基于项目根目录计算输出路径，避免硬编码绝对路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_OUTPUT_DIR = PROJECT_ROOT / "KnowledgeBase" / "output"

def save_to_file_tool(filename: str, content: str):
    """
    将文本内容保存到本地文件。
    Args:
        filename: 文件名，建议使用 .md 或 .txt 后缀 (例如: "2025年鼠疫风险评估报告.md")
        content: 要保存的完整文本内容
    """
    print(f"Agent 正在尝试保存文件: {filename}")

    # 1. 确保输出目录存在
    try:
        REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return ToolResponse(content=f"错误: 无法创建目录 {REPORT_OUTPUT_DIR}: {e}")

    # 2. 清洗文件名 (防止包含非法字符)
    # 去除路径分隔符，强制只存从 REPORT_OUTPUT_DIR 下
    safe_filename = Path(filename.strip().strip('"').strip("'")).name

    # 如果 Agent 忘了加后缀，默认加 .md
    if '.' not in safe_filename:
        safe_filename += ".md"

    full_path = REPORT_OUTPUT_DIR / safe_filename

    # 3. 写入文件
    try:
        with full_path.open('w', encoding='utf-8') as f:
            f.write(content)

        return ToolResponse(
            content=f"文件已成功保存！\n路径: {full_path}\n大小: {len(content)} 字符"
        )
    except Exception as e:
        return ToolResponse(content=f"保存文件失败: {e}")
