# -*- coding: utf-8 -*-
"""
海关总署研究中心 - 疫情资讯
从列表页抓取 30 天内的文章，逐篇拉取正文，合并保存到同一 TXT。

依赖: pip install requests beautifulsoup4
运行: python chinacustoms_yqzx_fetch.py
输出: chinacustoms_yqzx_30days.txt（脚本同目录）
"""
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# 导入知识库管理器
import sys

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.kb_manager import KBManager

BASE_URL = "http://www.chinacustoms-strc.cn"
LIST_URL = "http://www.chinacustoms-strc.cn/hkzx/zhzx/yqzx/index.html"
DAYS = 30
OUTPUT_TXT = "chinacustoms_yqzx_30days.txt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_page(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_list(html):
    """解析列表页：提取 (href, title, date_str)。"""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # 右侧主内容区
    right = soup.find(class_=re.compile(r"listCon_R|conRight|list.*R", re.I))
    if not right:
        right = soup

    # 文章链接：yqzx 下任意 .html，含 .../yqzx/xxx/index.html；排除列表页 /yqzx/index.html
    for a in right.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if "yqzx" not in href or not href.endswith(".html"):
            continue
        # 排除列表页本身（仅 /hkzx/zhzx/yqzx/index.html）
        if re.search(r"/yqzx/index\.html$", href):
            continue
        title = a.get_text(strip=True)
        if not title or len(title) < 2:
            continue

        date_str = None
        # 日期：先从标题提取 2025.12.31 或 2025-12-31
        match = re.search(r"(\d{4})[.-](\d{2})[.-](\d{2})", title)
        if match:
            date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        if not date_str:
            li = a.find_parent("li")
            if li:
                span = li.find("span")
                if span:
                    date_str = span.get_text(strip=True)
                if not date_str:
                    text = li.get_text(strip=True)
                    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
                    if match:
                        date_str = match.group(1)
        if not date_str:
            for parent in [a.find_parent("div"), a.find_parent("p"), a.find_parent("td")]:
                if parent:
                    match = re.search(r"(\d{4}-\d{2}-\d{2})", parent.get_text())
                    if match:
                        date_str = match.group(1)
                        break

        items.append({"href": href, "title": title, "date_str": date_str or ""})

    # 去重：同一 href 保留第一条
    seen = set()
    unique = []
    for it in items:
        k = (it["href"].split("?")[0], it["title"][:50])
        if k in seen:
            continue
        seen.add(k)
        unique.append(it)
    return unique


def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(date_str[:10], fmt).date()
        except ValueError:
            continue
    return None


def filter_within_days(items, days=30, start_date=None):
    if start_date:
        cutoff = start_date
    else:
        cutoff = datetime.now().date() - timedelta(days=days)
    result = []
    for it in items:
        d = parse_date(it["date_str"])
        if d is not None and d >= cutoff:
            result.append(it)
    # 无日期的条目：若列表仅一页，可视为近期，这里保守不纳入；若需纳入可改为 append(it) 当 date_str 为空时
    return result


def extract_article_body(html, page_url):
    """从正文页提取主体文字。"""
    soup = BeautifulSoup(html, "html.parser")
    # 常见正文容器：海关站用 easysite-news-content，eportal 用 TRS_Editor 等
    for selector in [
        "div.easysite-news-content",
        "div.TRS_Editor",
        "div.eps-portlet-body",
        "div.content",
        "div.article",
        "div#content",
        "div.detail",
        "div.main_content",
        "div.articleContent",
        "div.listCon_R",
    ]:
        tag = soup.select_one(selector)
        if tag:
            # 去掉 script/style
            for x in tag.find_all(["script", "style"]):
                x.decompose()
            text = tag.get_text(separator=" ", strip=True)
            if len(text) > 80:
                return normalize_paragraphs(text)
    # 回退：取 body 内大段文本
    body = soup.find("body")
    if body:
        for x in body.find_all(["script", "style", "nav", "header", "footer"]):
            x.decompose()
        text = body.get_text(separator=" ", strip=True)
        if len(text) > 100:
            return normalize_paragraphs(text)
    return ""


def normalize_paragraphs(text):
    """合并多余空白，仅在句末换行，减少碎行。"""
    text = re.sub(r"\s+", " ", text).strip()
    # 在 。！？； 后换行，便于阅读
    text = re.sub(r"([。！？；])\s*", r"\1\n", text)
    return text.strip()


def main(days=30, start_date=None):
    # 初始化知识库管理器
    kb_dir = PROJECT_ROOT / "KnowledgeBase" / "data"
    manager = KBManager(base_dir=str(kb_dir))
    
    # 目标保存目录
    target_dir = kb_dir / "international" / "04_customs_daily_brief"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print("列表页:", LIST_URL)
    try:
        list_html = fetch_page(LIST_URL)
    except Exception as e:
        print("获取列表页失败:", e)
        return

    items = parse_list(list_html)
    print(f"解析到 {len(items)} 条链接。")

    filtered = filter_within_days(items, days, start_date)
    
    if start_date:
        time_range_str = f"{start_date} 至今"
    else:
        time_range_str = f"最近 {days} 天"
    
    print(f"其中 {time_range_str} 的文章: {len(filtered)} 条。")
    if not filtered:
        print("没有符合时间条件的文章。")
        return

    print(f"\n{'='*60}")
    print(f"开始保存 {len(filtered)} 条文章到知识库")
    print(f"目标目录: {target_dir}")
    print(f"{'='*60}\n")

    saved_count = 0
    moved_count = 0
    for i, it in enumerate(filtered, 1):
        full_url = urljoin(BASE_URL, it["href"])
        title = it["title"]
        date_str = it["date_str"] or "(无日期)"
        
        print(f"[{i}/{len(filtered)}] 保存文章: {title}")
        print(f"   发布日期: {date_str}")
        print(f"   URL: {full_url}")
        
        try:
            article_html = fetch_page(full_url)
            body = extract_article_body(article_html, full_url)
            
            if body:
                # 使用知识库管理器保存到默认位置
                current_date = date_str if date_str != "(无日期)" else datetime.now().strftime('%Y-%m-%d')
                save_result = manager.save_article(
                    source='chinacustoms',
                    content_date=current_date,
                    publish_date=current_date,
                    title=title,
                    url=full_url,
                    content=body,
                    file_type="text"
                )
                
                if save_result:
                    saved_count += 1
                    print(f"   ✓ 保存成功到默认位置")
                    
                    # 移动文件到目标目录
                    try:
                        filename = manager.get_safe_filename(title, full_url, ".md")
                        source_path = kb_dir / "chinacustoms" / filename
                        target_path = target_dir / filename
                        
                        if source_path.exists():
                            import shutil
                            shutil.move(str(source_path), str(target_path))
                            moved_count += 1
                            print(f"   ✓ 已移动到目标目录: {target_dir}")
                        else:
                            print(f"   ⚠ 源文件不存在: {source_path}")
                    except Exception as e:
                        print(f"   ⚠ 移动文件时出错: {e}")
                else:
                    print(f"   ⚠ 已存在，跳过")
            else:
                print(f"   ✗ 正文未解析到内容")
        except Exception as e:
            print(f"   ✗ 抓取失败: {e}")
        print()

    print(f"\n{'='*60}")
    print(f"爬取完成！共获取 {len(filtered)} 条文章")
    print(f"保存到知识库: {saved_count} 条")
    print(f"移动到目标目录: {moved_count} 条")
    print(f"目标目录: {target_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='抓取海关总署研究中心疫情资讯')
    parser.add_argument('--days', type=int, default=30, help='抓取最近多少天的文章')
    parser.add_argument('--start-date', type=str, default=None, help='从指定日期开始抓取 (格式: YYYY-MM-DD)')
    args = parser.parse_args()
    
    start_date = None
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"错误: 日期格式不正确，请使用 YYYY-MM-DD 格式")
            exit(1)
    
    main(days=args.days, start_date=start_date)
