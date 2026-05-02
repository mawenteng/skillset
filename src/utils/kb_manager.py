import os
import json
import re
import sys
import uuid
from pathlib import Path

# === 依赖库 ===
import lancedb
from openai import OpenAI  # 用于生成向量
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from src.config.loader import load_config
from agentscope.model import DashScopeChatModel

# 引入数据库定义
from src.utils.db_schema import DB_PATH, TABLE_NAME, DiseaseReport

# 加载环境变量 (用于 Embedding API)
load_dotenv(project_root / ".env")

# === LangChain 切分工具 (如果没有安装 langchain，请使用 pip install langchain) ===
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
except ImportError:
    print("⚠️ 未检测到 LangChain，使用简易切分模式。建议运行 `pip install langchain`")
    RecursiveCharacterTextSplitter = None
    MarkdownHeaderTextSplitter = None

def extract_description(content, max_length=150):
    """从内容中提取简短描述"""
    clean_content = re.sub(r'#+\s', '', content)
    clean_content = re.sub(r'\n\s*\*\s', '', clean_content)
    clean_content = re.sub(r'\n\s*\d+\.\s', '', clean_content)
    clean_content = re.sub(r'\n{3,}', '\n\n', clean_content)
    sentences = re.split(r'[。！？]', clean_content)
    description = '。'.join(sentences[:3])
    description = description.strip()
    if len(description) > max_length:
        description = description[:max_length] + '...'
    return description if description else "无描述"

def generate_description_with_llm(content, title, max_length=150):
    """使用大模型生成文章描述 (可选开启)"""
    try:
        config = load_config()
        model = DashScopeChatModel(
            api_key=config.agent.model.api_key,
            model_name=config.agent.model.model_name,
            temperature=0.3,
            max_tokens=200
        )
        prompt = f"""请为以下文章生成一个简洁的描述...（略）...文章内容：\n{content[:500]}..."""
        response = model(prompt)
        description = response.text.strip()
        if len(description) > max_length:
            description = description[:max_length] + '...'
        return description
    except Exception as e:
        print(f"使用大模型生成描述时出错: {e}")
        return extract_description(content, max_length)

class KBManager:
    def __init__(self, base_dir=None):
        # 如果没有指定base_dir，使用项目根目录下的KnowledgeBase/data
        if base_dir is None:
            base_dir = project_root / "KnowledgeBase" / "data"
        self.base_dir = Path(base_dir)
        self.history_file = self.base_dir / "history_log.json"
        self._ensure_dir(self.base_dir)
        self.history = self._load_history()
        
        # 初始化 Embedding 客户端
        self.embedding_client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL")
        )

    def _ensure_dir(self, path):
        Path(path).mkdir(parents=True, exist_ok=True)

    def _load_history(self):
        if not self.history_file.exists():
            return set()
        try:
            with self.history_file.open('r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            return set()

    def _save_history(self):
        with self.history_file.open('w', encoding='utf-8') as f:
            json.dump(list(self.history), f, indent=2)

    def is_scraped(self, url):
        return url in self.history

    def get_safe_filename(self, title, url, ext=".md"):
        # 直接使用title作为文件名，保持与元数据一致
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
        safe_title = safe_title[:100]  # 增加长度限制以容纳完整标题
        return f"{safe_title}{ext}"

    def _get_embedding(self, text: str):
        """调用 API 生成文本向量"""
        text = text.replace("\n", " ")
        try:
            response = self.embedding_client.embeddings.create(
                input=[text],
                model="text-embedding-v2" 
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️ 向量化失败: {e}")
            return [0.0] * 1536 

    # === 🔥 核心逻辑：智能切分策略 ===
    def _chunk_content_smart(self, content: str, metadata: dict):
        """
        根据文档类别（Category）选择最佳的切分策略。
        """
        category = metadata.get('category', 'Other')
        title = metadata.get('title', '')
        chunks = []

        # ---------------------------------------------------------
        # 策略 1: [Brief] 日报/简报 -> "碎片化正则切分"
        # ---------------------------------------------------------
        if category == 'Brief' or "日报" in title or "简报" in title:
            content_body = re.sub(r'# .*?日报.*?\n', '', content) 
            raw_splits = content_body.split('（来源：')
            
            for i, split in enumerate(raw_splits):
                clean_text = split.strip()
                if len(clean_text) < 10: continue

                if i < len(raw_splits) - 1:
                    clean_text += "（来源：" + raw_splits[i+1].split('）')[0] + "）"
                
                enriched_chunk = (
                    f"【文档类型: 疫情日报】\n"
                    f"【日期: {metadata.get('publish_date')}】\n"
                    f"【标题: {title}】\n"
                    f"--- 内容 ---\n{clean_text}"
                )
                chunks.append(enriched_chunk)

        # ---------------------------------------------------------
        # 策略 2: [Statistics] 统计数据 -> "表格感知切分"
        # ---------------------------------------------------------
        elif category == 'Statistics':
            # 使用表格感知切分，保持表格完整性，长表格拆分为带表头的小表格
            chunks = self._chunk_content_with_table_aware(content, metadata, max_chars=1500)

        # ---------------------------------------------------------
        # 策略 3: [RiskAssessment] 风险评估 -> "Markdown层级切分"
        # ---------------------------------------------------------
        elif category == 'RiskAssessment' and MarkdownHeaderTextSplitter:
            headers_to_split_on = [
                ("#", "Title"),
                ("##", "Section"),
                ("###", "Subsection"),
            ]
            markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            md_docs = markdown_splitter.split_text(content)
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            
            for doc in md_docs:
                header_path = " > ".join(doc.metadata.values())
                sub_splits = text_splitter.split_text(doc.page_content)
                
                for sub_text in sub_splits:
                    final_chunk = f"【章节: {header_path}】\n{sub_text}"
                    chunks.append(final_chunk)
        
        # ---------------------------------------------------------
        # 策略 4: [Fallback] 通用兜底策略
        # ---------------------------------------------------------
        else:
            chunks = self._chunk_markdown_fallback(content)

        return chunks

    # === ✨ 工具方法：表格识别与处理 ===

    def _is_markdown_table(self, line):
        """检测是否是 Markdown 表格行 (基本检测)"""
        stripped = line.strip()
        if not stripped.startswith('|') or not stripped.endswith('|'):
            return False
        cells = [c.strip() for c in stripped[1:-1].split('|')]
        return len(cells) >= 2

    def _is_table_separator(self, line):
        """
        [Fix] 检测是否是表格分隔行（兼容 :---, ---:, :---:）
        修复了之前无法识别带对齐标记的表格的Bug
        """
        stripped = line.strip()
        if not stripped.startswith('|') or not stripped.endswith('|'):
            return False
        
        # 去除首尾的 |
        content = stripped[1:-1]
        # 分割单元格
        cells = content.split('|')
        
        valid_cells = 0
        for cell in cells:
            cell_content = cell.strip()
            if not cell_content: continue # 忽略空单元格
            
            # 必须只包含 - 和 :，且必须包含至少一个 -
            if not re.match(r'^[:\-]+$', cell_content):
                return False
            if '-' not in cell_content:
                return False
            valid_cells += 1
            
        return valid_cells > 0

    def _extract_table_blocks(self, content):
        """提取完整的表格块，返回 [(table_text, start_line, end_line), ...]"""
        lines = content.split('\n')
        table_blocks = []
        in_table = False
        table_start = 0
        table_lines = []
        
        for i, line in enumerate(lines):
            if self._is_markdown_table(line):
                if not in_table:
                    # 只有当下一行也是表格线时，才认为是表格开始（或者是第二行是分隔符）
                    in_table = True
                    table_start = i
                    table_lines = [line]
                else:
                    table_lines.append(line)
            elif in_table:
                # 检查是否是分隔符行（虽然 _is_markdown_table 也会捕获它，但这里做双重保险）
                if self._is_table_separator(line):
                    table_lines.append(line)
                elif line.strip() == '':
                    # 表格结束
                    table_blocks.append(('\n'.join(table_lines), table_start, i - 1))
                    in_table = False
                    table_lines = []
                else:
                    # 遇到非表格行，表格结束
                    table_blocks.append(('\n'.join(table_lines), table_start, i - 1))
                    in_table = False
                    table_lines = []
        
        # 处理文件末尾是表格的情况
        if in_table:
            table_blocks.append(('\n'.join(table_lines), table_start, len(lines) - 1))
        
        return table_blocks

    def _split_long_table(self, table_text, max_rows=15):
        """
        将长表格拆分为多个带表头的小表格
        [Optimization] 默认 max_rows 调整为 15，防止 Token 溢出
        """
        lines = table_text.split('\n')
        if len(lines) <= 2:
            return [table_text]
        
        header_line = lines[0]
        # 智能识别分隔行
        separator_line = ''
        if len(lines) > 1 and self._is_table_separator(lines[1]):
            separator_line = lines[1]
        
        data_lines = lines[2:] if separator_line else lines[1:]
        
        if not data_lines:
            return [table_text]
        
        small_tables = []
        for i in range(0, len(data_lines), max_rows):
            chunk_data = data_lines[i:i + max_rows]
            if separator_line:
                small_table = '\n'.join([header_line, separator_line] + chunk_data)
            else:
                small_table = '\n'.join([header_line] + chunk_data)
            small_tables.append(small_table)
        
        return small_tables

    def _chunk_content_with_table_aware(self, content, metadata, max_chars=1500):
        """表格感知的内容切分，保持表格完整性"""
        
        # [Optimization] 预先分割所有行，避免在循环中重复分割
        all_lines = content.split('\n')
        table_blocks = self._extract_table_blocks(content)
        
        if not table_blocks:
            if RecursiveCharacterTextSplitter:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=max_chars,
                    chunk_overlap=100,
                    separators=["\n\n", "\n#", "\n"]
                )
                return splitter.split_text(content)
            return self._chunk_markdown_fallback(content, max_chars)
        
        chunks = []
        last_end = 0
        
        for table_text, start_line, end_line in table_blocks:
            # 获取表格前的文本块
            before_table_lines = all_lines[last_end:start_line]
            before_table = '\n'.join(before_table_lines).strip()
            
            if before_table:
                if RecursiveCharacterTextSplitter:
                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size=max_chars,
                        chunk_overlap=50,
                        separators=["\n\n", "\n#", "\n"]
                    )
                    text_chunks = splitter.split_text(before_table)
                    chunks.extend(text_chunks)
                else:
                    text_chunks = self._chunk_markdown_fallback(before_table, max_chars)
                    chunks.extend(text_chunks)
            
            # 处理表格部分
            small_tables = self._split_long_table(table_text, max_rows=15)
            for idx, small_table in enumerate(small_tables):
                table_context = (
                    f"【文档类型: 统计表格】\n"
                    f"【日期: {metadata.get('publish_date')}】\n"
                    f"【标题: {metadata.get('title')}】\n"
                    f"【表格部分: {idx + 1}/{len(small_tables)}】\n"
                    f"--- 表格内容 ---\n{small_table}"
                )
                chunks.append(table_context)
            
            last_end = end_line + 1
        
        # 获取表格后的剩余文本
        after_table_lines = all_lines[last_end:]
        after_tables = '\n'.join(after_table_lines).strip()
        
        if after_tables:
            if RecursiveCharacterTextSplitter:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=max_chars,
                    chunk_overlap=50,
                    separators=["\n\n", "\n#", "\n"]
                )
                text_chunks = splitter.split_text(after_tables)
                chunks.extend(text_chunks)
            else:
                text_chunks = self._chunk_markdown_fallback(after_tables, max_chars)
                chunks.extend(text_chunks)
        
        return chunks

    def _chunk_markdown_fallback(self, content, max_chars=800):
        """(备用) 简易切分逻辑，不依赖 LangChain"""
        content = content.replace('\r\n', '\n')
        raw_chunks = re.split(r'(## .*?\n|\n\n)', content)
        final_chunks = []
        current_buffer = ""

        for chunk in raw_chunks:
            if not chunk.strip(): continue
            if len(current_buffer) + len(chunk) < max_chars:
                current_buffer += chunk
            else:
                if current_buffer: final_chunks.append(current_buffer.strip())
                if len(chunk) > max_chars:
                    final_chunks.extend([chunk[i:i+max_chars] for i in range(0, len(chunk), max_chars)])
                    current_buffer = ""
                else:
                    current_buffer = chunk
        if current_buffer: final_chunks.append(current_buffer.strip())
        return final_chunks

    def _save_to_vectordb(self, title, content, source, publish_date, report_period, url, region="Domestic", category="Statistics"):
        """将清洗后的数据存入 LanceDB"""
        print(f"   ↳ 正在同步至向量数据库...")
        
        # 1. 自动推断 Region
        if region == "Domestic": 
             if "全球" in title or "WHO" in source.upper() or "世卫" in title:
                 region = "International"

        # 2. 自动推断并修正 Category
        computed_category = category 
        
        if "风险评估" in title:
            computed_category = "RiskAssessment"
        elif "日报" in title or "简报" in title or "快讯" in title:
            computed_category = "Brief"
        elif "疫情概况" in title or "统计" in title:
            computed_category = "Statistics"
        
        # 3. 调用智能切分
        metadata = {
            "title": title,
            "category": computed_category,
            "publish_date": publish_date
        }
        chunks = self._chunk_content_smart(content, metadata)
        
        data_rows = []
        for chunk in chunks:
            if len(chunk.strip()) < 5: continue 
            
            # 生成向量
            vector = self._get_embedding(chunk)
            
            data_rows.append(DiseaseReport(
                id=str(uuid.uuid4()),
                vector=vector,
                text=chunk,
                title=title,
                source=source,
                report_period=report_period or "Unknown",
                publish_date=publish_date or "Unknown",
                url=url,
                region=region,
                category=computed_category
            ))

        # 4. 写入数据库
        if data_rows:
            try:
                db = lancedb.connect(DB_PATH)
                table = db.create_table(TABLE_NAME, schema=DiseaseReport, exist_ok=True)
                table.add(data_rows)
                print(f"   ✅ 已存入 {len(data_rows)} 个切片 (分类: {computed_category})")
            except Exception as e:
                print(f"   ❌ 向量库写入失败: {e}")

    def save_article(self, source, content_date, publish_date, title, url, content, file_type="text", description=None, report_period=None):
        """
        保存文章：1.存MD文件 2.存入向量库 3.记录历史
        """
        if self.is_scraped(url):
            print(f"[{source}] 跳过已存在: {title}")
            return False

        save_path = self.base_dir / source
        self._ensure_dir(save_path)

        if file_type == "text":
            if description is None:
                description = extract_description(content)

            if report_period is None and content_date:
                try:
                    if len(content_date) >= 7:
                        report_period = content_date[:7]
                except:
                    report_period = "unknown"

            filename = self.get_safe_filename(title, url, ".md")
            full_path = save_path / filename
            
            metadata_lines = [
                f'title: "{title}"',
                f'source: "{source}"',
                f'publish_date: "{publish_date}"',
                f'report_period: "{report_period or "unknown"}"',
                f'url: "{url}"',
                f'description: "{description}"'
            ]
            md_content = "---\n" + "\n".join(metadata_lines) + "\n---\n\n" + f"# {title}\n\n{content}"
            
            with full_path.open('w', encoding='utf-8') as f:
                f.write(md_content)
            print(f"[{source}] 已保存文件: {filename}")

            # 同步存入向量数据库
            self._save_to_vectordb(
                title=title,
                content=content,
                source=source,
                publish_date=publish_date,
                report_period=report_period,
                url=url
            )
        
        self.history.add(url)
        self._save_history()
        return True
