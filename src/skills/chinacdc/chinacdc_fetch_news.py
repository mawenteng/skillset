# -*- coding: utf-8 -*-
"""
爬取中国疾控中心近一个月的新闻详细信息
"""
import os
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time
from pathlib import Path

# 导入知识库管理器
import sys

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.kb_manager import KBManager

def get_news_list():
    """
    获取新闻列表
    """
    url = "https://www.chinacdc.cn/jksj/jksj01/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print(f"正在获取新闻列表: {url}")
    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = response.apparent_encoding or 'utf-8'
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    news_list = []
    xw_list = soup.find('ul', class_='xw_list')
    
    if xw_list:
        lis = xw_list.find_all('li')
        for li in lis:
            a = li.find('a')
            if a:
                title = a.get_text(strip=True)
                href = a.get('href', '')
                
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', title)
                if date_match:
                    publish_date = date_match.group(1)
                    try:
                        publish_date_obj = datetime.strptime(publish_date, '%Y-%m-%d')
                        
                        full_url = url + href if href.startswith('./') else href
                        
                        news_list.append({
                            'title': title,
                            'publish_date': publish_date,
                            'publish_date_obj': publish_date_obj,
                            'url': full_url
                        })
                    except ValueError:
                        continue
    
    print(f"获取到 {len(news_list)} 条新闻")
    return news_list

def filter_recent_news(news_list, days=30):
    """
    筛选近N天的新闻
    
    Args:
        news_list: 新闻列表
        days: 天数
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    recent_news = []
    for news in news_list:
        if news['publish_date_obj'] >= cutoff_date:
            recent_news.append(news)
    
    print(f"近 {days} 天内的新闻: {len(recent_news)} 条")
    return recent_news

def get_detail_page(url):
    """
    获取详情页内容
    
    Args:
        url: 详情页URL
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_div = soup.find('div', class_='content')
        
        if content_div:
            table = content_div.find('table')
            
            if table:
                table.extract()
            
            paragraphs = content_div.find_all('p')
            content_text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            table_data = []
            
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    if row_data:
                        table_data.append(row_data)
            
            return {
                'content': content_text,
                'table': table_data
            }
        
        return None
    except Exception as e:
        print(f"获取详情页失败 {url}: {e}")
        return None

def crawl_recent_news(days=30):
    """
    爬取近N天的新闻详细信息
    
    Args:
        days: 天数
    """
    print(f"\n{'='*60}")
    print(f"开始爬取近 {days} 天的新闻")
    print(f"{'='*60}\n")
    
    news_list = get_news_list()
    recent_news = filter_recent_news(news_list, days)
    
    if not recent_news:
        print("没有找到近期的新闻")
        return []
    
    results = []
    
    for idx, news in enumerate(recent_news, 1):
        print(f"\n[{idx}/{len(recent_news)}] 正在爬取: {news['title']}")
        print(f"发布日期: {news['publish_date']}")
        print(f"URL: {news['url']}")
        
        detail = get_detail_page(news['url'])
        
        if detail:
            news_detail = {
                'title': news['title'],
                'publish_date': news['publish_date'],
                'url': news['url'],
                'content': detail['content'],
                'table_data': detail['table']
            }
            results.append(news_detail)
            print(f"✓ 成功获取详情 (内容长度: {len(detail['content'])} 字符, 表格行数: {len(detail['table'])})")
        else:
            print(f"✗ 获取详情失败")
        
        time.sleep(1)
    
    return results

def save_to_markdown(data, filename='recent_news.md'):
    """
    保存数据到Markdown文件
    
    Args:
        data: 数据
        filename: 文件名
    """
    # 保存到指定目录
    output_dir = PROJECT_ROOT / "KnowledgeBase" / "data" / "domestic" / "01_cdc_stats_monthly"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = output_dir / filename
    
    md_content = []
    
    md_content.append("# 中国疾控中心疫情数据报告\n")
    md_content.append(f"**爬取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_content.append(f"**报告数量**: {len(data)} 条\n")
    md_content.append("---\n")
    
    for idx, news in enumerate(data, 1):
        md_content.append(f"## {idx}. {news['title']}\n")
        md_content.append(f"**发布日期**: {news['publish_date']}\n")
        md_content.append(f"**原文链接**: {news['url']}\n")
        md_content.append("---\n")
        
        md_content.append("### 报告摘要\n")
        md_content.append(f"{news['content']}\n")
        
        if news['table_data']:
            md_content.append("\n### 统计数据\n")
            
            def clean_disease_name(name):
                import re
                return re.sub(r'\d+$', '', name).strip()
            
            def clean_header(name):
                import re
                return re.sub(r'\d+$', '', name).strip()
            
            def format_number(num_str):
                try:
                    num = int(num_str)
                    return f"{num:,}"
                except ValueError:
                    return num_str
            
            header_row = news['table_data'][0]
            md_content.append(f"| {clean_disease_name(header_row[0])} | {clean_header(header_row[1])} | {clean_header(header_row[2])} |\n")
            md_content.append("|------|--------|--------|\n")
            
            for row in news['table_data'][1:]:
                if len(row) >= 3:
                    disease = clean_disease_name(row[0])
                    cases = format_number(row[1])
                    deaths = format_number(row[2])
                    md_content.append(f"| {disease} | {cases} | {deaths} |\n")
        
        md_content.append("\n---\n\n")
    
    with filepath.open('w', encoding='utf-8') as f:
        f.writelines(md_content)
    
    print(f"Markdown文档已保存到: {filepath}")

def main(days=30):
    # 初始化知识库管理器
    kb_dir = PROJECT_ROOT / "KnowledgeBase" / "data"
    manager = KBManager(base_dir=str(kb_dir))
    
    # 目标保存目录
    target_dir = kb_dir / "domestic" / "01_cdc_stats_monthly"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    results = crawl_recent_news(days=days)
    
    if results:
        print(f"\n{'='*60}")
        print(f"开始保存 {len(results)} 条新闻到知识库")
        print(f"{'='*60}\n")
        
        saved_count = 0
        moved_count = 0
        for idx, news in enumerate(results, 1):
            print(f"[{idx}/{len(results)}] 保存新闻: {news['title']}")
            print(f"   发布日期: {news['publish_date']}")
            print(f"   URL: {news['url']}")
            
            # 构建完整内容（包含表格数据）
            full_content = news['content']
            if news['table_data']:
                full_content += "\n\n### 统计数据\n\n"
                # 添加表格内容
                header_row = news['table_data'][0]
                full_content += f"| {header_row[0]} | {header_row[1]} | {header_row[2]} |\n"
                full_content += "|------|--------|--------|\n"
                for row in news['table_data'][1:]:
                    if len(row) >= 3:
                        full_content += f"| {row[0]} | {row[1]} | {row[2]} |\n"
            
            # 使用知识库管理器保存到默认位置
            save_result = manager.save_article(
                source='chinacdc',
                content_date=news['publish_date'],
                publish_date=news['publish_date'],
                title=news['title'],
                url=news['url'],
                content=full_content,
                file_type="text"
            )
            
            if save_result:
                saved_count += 1
                print(f"   ✓ 保存成功到默认位置")
                
                # 移动文件到目标目录
                try:
                    # 生成文件名
                    filename = manager.get_safe_filename(news['title'], news['url'], ".md")
                    source_path = kb_dir / "chinacdc" / filename
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
            print()
        
        print(f"\n{'='*60}")
        print(f"爬取完成！共获取 {len(results)} 条新闻")
        print(f"保存到知识库: {saved_count} 条")
        print(f"移动到目标目录: {moved_count} 条")
        print(f"目标目录: {target_dir}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='抓取中国疾控中心新闻')
    parser.add_argument('--days', type=int, default=30, help='抓取最近多少天的新闻')
    args = parser.parse_args()
    main(days=args.days)
