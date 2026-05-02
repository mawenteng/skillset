# src/tools/kb_search.py
import os
import sys
from pathlib import Path
import lancedb
from openai import OpenAI
from agentscope.tool import ToolResponse
from dotenv import load_dotenv

# 引入 Schema
try:
    # 尝试直接导入 (如果在同一包下)
    from utils.db_schema import DiseaseReport, DB_PATH, TABLE_NAME
except ImportError:
    # 尝试从上级目录导入 (如果作为脚本运行)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.db_schema import DiseaseReport, DB_PATH, TABLE_NAME

# 加载环境变量
root_dir = Path(__file__).parent.parent.parent
load_dotenv(os.path.join(root_dir, '.env'))

# 初始化 Embedding 客户端
embedding_client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
)
EMBEDDING_MODEL = "text-embedding-v2"

def get_query_embedding(text: str):
    """获取查询词向量"""
    text = text.replace("\n", " ")
    try:
        response = embedding_client.embeddings.create(input=[text], model=EMBEDDING_MODEL)
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding Error: {e}")
        return [0.0] * 1536

def search_kb(question: str, region: str = "All", category: str = "All", top_k=5):
    """
    底层搜索函数：支持向量语义搜索 + 元数据过滤
    """
    if not os.path.exists(DB_PATH):
        return []

    db = lancedb.connect(DB_PATH)
    try:
        table = db.open_table(TABLE_NAME)
    except FileNotFoundError:
        return []

    # 1. 生成向量
    query_vector = get_query_embedding(question)

    # 2. 构建过滤条件 (SQL Where Clause)
    # 这里的逻辑必须与 System Prompt 中的分类定义对齐
    filters = []
    
    # 地域过滤
    if region and region not in ["All", "None", ""]:
        filters.append(f"region = '{region}'")
        
    # 类别过滤
    if category and category not in ["All", "None", ""]:
        filters.append(f"category = '{category}'")
    
    where_clause = " AND ".join(filters) if filters else None

    print(f"\n🔎 [RAG搜索] 关键词: '{question}'")
    print(f"   [过滤条件] Region: {region}, Category: {category} -> SQL: {where_clause if where_clause else 'No Filter'}")

    # 3. 执行搜索
    search_query = table.search(query_vector).metric("cosine").limit(top_k)
    
    if where_clause:
        search_query = search_query.where(where_clause) # 关键：应用过滤
        
    results = search_query.to_pydantic(DiseaseReport)
    return results

def kb_search_tool(question: str, region: str = "All", category: str = "All", top_k: int = 50):
    """
    [AgentScope工具] 知识库语义搜索。
    
    Args:
        question: 搜索的具体问题或关键词。
        region: (可选) 地域筛选。可选值: "Domestic"(国内), "International"(国际), "All"(不限)。默认为 "All"。
        category: (可选) 类型筛选。
                  - "Statistics": 官方统计数据表格。
                  - "RiskAssessment": 深度风险评估报告(含全球和国内)。
                  - "Brief": 每日疫情简报、海关通报、突发疫情信息。
                  - "All": 不限。
                  默认为 "All"。
        top_k: (可选) 返回结果数量。默认为 50。
    """
    try:
        # 1. 默认值处理
        if region is None: region = "All"
        if category is None: category = "All"
        if top_k is None: top_k = 50

        # 2. 自动纠错映射 (关键步骤！防止Agent传错)
        # 如果Agent习惯性传了旧名字，这里强制转成数据库里的新名字
        category_mapping = {
            "DailyBriefing": "Brief",
            "GlobalRiskAssessment": "RiskAssessment",
            "Briefing": "Brief"
        }
        if category in category_mapping:
            print(f"⚠️ [自动修正] 将分类 '{category}' 修正为 '{category_mapping[category]}'")
            category = category_mapping[category]

        # 3. 调用搜索
        results = search_kb(question, region, category, top_k)
        
        if not results:
            return ToolResponse(content=f"知识库搜索完成，但在过滤条件(Region={region} | Category={category})下未找到关于'{question}'的相关信息。")

        # 4. 格式化输出
        output = f"🔍 检索结果 (筛选条件: Region={region} | Category={category} | 数量={len(results)})：\n\n"
        for i, item in enumerate(results):
            # 显示来源标签，方便 LLM 判断
            tag_info = f"[{item.region} | {item.category}]"
            # 如果有日期就显示日期
            date_info = f"({item.publish_date})" if item.publish_date and item.publish_date != "Unknown" else ""
            
            output += f"--- [资料 {i+1} {tag_info} {date_info}] ---\n"
            output += f"标题: {item.title}\n"
            # 根据不同类别设置不同的预览长度
            preview_len = 400 if item.category == "Brief" else 300
            output += f"内容摘要: {item.text.strip()[:preview_len]}...\n\n"
            
        return ToolResponse(content=output)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ToolResponse(content=f"搜索工具执行异常: {str(e)}")
