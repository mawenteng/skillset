# -*- coding: utf-8 -*-
"""
中国疾控中心 - 重点传染病和突发公共卫生事件风险评估报告
筛选 30 天内发布的报告并下载 PDF 到当前目录。
"""
import re
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# 导入知识库管理器
import sys
import tempfile

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.kb_manager import KBManager
# 引用新的转换函数
from utils.pdf_to_markdown import convert_pdf_to_markdown

# 配置：多个栏目 (标签, 列表页URL, 基准URL用于拼PDF)
PAGES = [
    ("jksj02", "https://www.chinacdc.cn/jksj/jksj02/", "https://www.chinacdc.cn/jksj/jksj02/"),
    ("jksj03", "https://www.chinacdc.cn/jksj/jksj03/", "https://www.chinacdc.cn/jksj/jksj03/"),
]
DAYS = 30
# 保存到工作区目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAVE_DIR = PROJECT_ROOT / "KnowledgeBase" / "data" / "chinacdc" / "pdfs"  # 输出目录
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_page(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_report_list(html):
    soup = BeautifulSoup(html, "html.parser")
    # 右侧主内容区里的列表
    ul = soup.find("ul", class_="xw_list")
    if not ul:
        return []
    items = []
    for li in ul.find_all("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        href = a.get("href", "").strip()
        if not href or not href.lower().endswith(".pdf"):
            continue
        # 日期在 <span> 里，格式 YYYY-MM-DD
        span = li.find("span")
        date_str = span.get_text(strip=True) if span else ""
        if not date_str:
            continue
        # 标题（链接文字去掉日期部分）
        title = a.get_text(strip=True).replace(date_str, "").strip()
        items.append({"href": href, "date_str": date_str, "title": title})
    return items


def parse_date(date_str):
    """解析 YYYY-MM-DD，失败返回 None"""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def filter_within_days(items, days=30):
    cutoff = datetime.now().date() - timedelta(days=days)
    result = []
    for item in items:
        d = parse_date(item["date_str"])
        if d is not None and d >= cutoff:
            result.append(item)
    return result


def download_pdf(url, filepath):
    r = requests.get(url, headers=HEADERS, timeout=30, stream=True)
    r.raise_for_status()
    with open(filepath, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def main(days=30):
    # 初始化知识库管理器
    kb_dir = PROJECT_ROOT / "KnowledgeBase" / "data"
    manager = KBManager(base_dir=str(kb_dir))
    
    # 定义不同URL对应的保存目录
    URL_TO_DIR = {
        "https://www.chinacdc.cn/jksj/jksj02/": "domestic/02_cdc_risk_assess_monthly",
        "https://www.chinacdc.cn/jksj/jksj03/": "international/03_cdc_global_risk_monthly"
    }
    
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    total_downloaded = 0
    moved_count = 0
    
    for label, list_url, base_url in PAGES:
        print(f"\n===== {label} {list_url} ======")
        print("正在获取列表页:", list_url)
        html = fetch_page(list_url)
        items = parse_report_list(html)
        print(f"解析到 {len(items)} 条报告。")
        if not items:
            print("未找到报告列表，跳过。")
            continue

        filtered = filter_within_days(items, days)
        print(f"其中 {days} 天内的报告: {len(filtered)} 条。")
        if not filtered:
            print("没有符合时间条件的报告。")
            continue

        # 确定目标目录
        target_subdir = URL_TO_DIR.get(list_url, "chinacdc")
        target_dir = kb_dir / target_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"目标保存目录: {target_dir}")

        for item in filtered:
            full_url = urljoin(base_url, item["href"])
            # 生成更易读的文件名：使用标题而不是URL中的basename
            safe_title = re.sub(r'[\/:*?"<>|]', '_', item["title"]).strip()
            safe_title = re.sub(r'\s+', '_', safe_title)[:50]  # 限制长度
            safe_date = item["date_str"].replace("-", "")
            
            print(f"处理: {item['title'][:50]}...")
            
            # 检查是否已在知识库中
            if manager.is_scraped(full_url):
                print(f"  ⚠ 已存在于知识库，跳过")
                continue
            
            try:
                # 创建临时文件保存PDF
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                    temp_pdf_path = temp_pdf.name
                
                # 下载PDF到临时文件
                download_pdf(full_url, temp_pdf_path)
                print(f"  已下载到临时文件")
                
                # 将PDF转换为markdown
                print(f"  正在转换为Markdown...")
                
                # ==========================
                # 修改点：传入 title 参数
                # ==========================
                markdown_content = convert_pdf_to_markdown(temp_pdf_path, title=item["title"])
                
                # 使用知识库管理器保存markdown内容到默认位置
                save_result = manager.save_article(
                    source='chinacdc',
                    content_date=item["date_str"],
                    publish_date=item["date_str"],
                    title=item["title"],
                    url=full_url,
                    content=markdown_content,
                    file_type="text"
                )
                
                if save_result:
                    # 移动文件到目标目录
                    try:
                        filename = manager.get_safe_filename(item["title"], full_url, ".md")
                        source_path = kb_dir / "chinacdc" / filename
                        target_path = target_dir / filename
                        
                        if source_path.exists():
                            import shutil
                            shutil.move(str(source_path), str(target_path))
                            moved_count += 1
                            print(f"  ✓ 已移动到目标目录: {target_dir}")
                        else:
                            print(f"  ⚠ 源文件不存在: {source_path}")
                    except Exception as e:
                        print(f"  ⚠ 移动文件时出错: {e}")
                
                # 清理临时文件
                os.unlink(temp_pdf_path)
                
                total_downloaded += 1
                print(f"  ✓ 已转换并保存为Markdown")
            except Exception as e:
                print(f"  失败: {e}")
                # 确保临时文件被清理
                if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)

    print(f"\n{'='*60}")
    print(f"完成！共转换并保存 {total_downloaded} 个PDF文件为Markdown格式到知识库")
    print(f"移动到指定目录: {moved_count} 个文件")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='抓取中国疾控中心PDF报告')
    parser.add_argument('--days', type=int, default=30, help='抓取最近多少天的报告')
    args = parser.parse_args()
    main(days=args.days)
