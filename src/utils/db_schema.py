import uuid
from pathlib import Path
import lancedb
from lancedb.pydantic import LanceModel, Vector
from pydantic import Field  # <--- 修正：必须导入这个！

# =================配置区域=================
VECTOR_DIMENSION = 1536 

# 路径配置
PROJECT_ROOT = Path(__file__).resolve().parents[2]
KB_DIR = PROJECT_ROOT / "KnowledgeBase"
DB_PATH = KB_DIR / "lancedb_store"
TABLE_NAME = "disease_reports"
# =========================================

class DiseaseReport(LanceModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())) 
    vector: Vector(1536)
    text: str = Field(default="")
    
    # Metadata
    title: str = Field(default="No Title")
    source: str = Field(default="unknown")
    publish_date: str = Field(default="") 
    report_period: str = Field(default="") 
    url: str = Field(default="")
    file_path: str = Field(default="")
    chunk_index: int = Field(default=0)
    
    # RAG过滤字段
    region: str = Field(default="Unknown")
    category: str = Field(default="Unknown")

    # <--- 建议：加上这个属性，方便后续取值 --->
    @property
    def payload(self):
        """检索时返回给 LLM 的干净数据"""
        return {
            "text": self.text,
            "metadata": {
                "title": self.title,
                "source": self.source,
                "publish_date": self.publish_date,
                "report_period": self.report_period,
                "url": self.url
            }
        }

def init_lancedb(db_path: str = DB_PATH, table_name: str = TABLE_NAME):
    """初始化数据库连接"""
    db_path = Path(db_path)
    db_path.mkdir(parents=True, exist_ok=True)
    
    db = lancedb.connect(str(db_path))
    
    if table_name in db.list_tables():
        tbl = db.open_table(table_name)
    else:
        tbl = db.create_table(table_name, schema=DiseaseReport)
        
    return tbl

if __name__ == "__main__":
    print(f"🚀 Checking Schema at: {DB_PATH}")
    try:
        tbl = init_lancedb()
        print(f"✅ Schema Valid. Table '{TABLE_NAME}' is ready.")
    except Exception as e:
        print(f"❌ Schema Error: {e}")
