#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import argparse
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    print("错误: pypdf库未安装。请运行 'pip install pypdf' 安装。")
    exit(1)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# ==========================================
# 知识库：用于修复断行的碎片
# ==========================================

# 常见的断行后半部分（碎片）
FRAGMENTS = [
    "减少综合征", "综合征", "出血热", "病毒病", "禽流感", # 疾病后缀
    "内亚", "和国", "合国", "利亚", "斯坦", "西亚", "兰卡" # 国家后缀
]

# 常见的容易被误判为疾病的国家名前缀
COUNTRY_STARTS = [
    "刚果民主", "刚果共和", "巴布亚", "中非", "多米尼", "波斯尼", 
    "圣文森", "安提瓜", "斯里", "孟加拉", "马来", "巴基"
]

# ==========================================
# 工具函数
# ==========================================

def _clean_text_line(line: str) -> str:
    if not line: return ""
    line = line.strip()
    if line.lower().endswith('.pdf'): return "" 
    # 修复中文间空格
    line = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', line)
    line = line.replace('，', ',').replace('：', ':').replace('；', ';')
    return line

def _identify_header(line: str) -> str:
    clean = line.strip()
    if re.match(r'^\d+(\.\d+)*\s+[\u4e00-\u9fa5].*$', clean):
        level = clean.split()[0].count('.') + 2
        level = min(level, 6)
        return f"{'#' * level} {clean}"
    if clean in ["摘要", "Abstract", "关键词", "Keywords", "结论", "讨论", "参考文献"]:
        return f"## {clean}"
    return None

def _clean_table_fused_text(line: str) -> str:
    if not line: return ""
    line = line.strip()
    line = line.replace('，', ',').replace('：', ':').replace('−', '-').replace('–', '-')
    # 修复粘连的日期
    line = re.sub(r'(\d{4}-\d{1,2}-\d{1,2})(20\d{2}-\d{1,2}-\d{1,2})', r'\1 \2', line)
    line = re.sub(r'([\u4e00-\u9fa5])(\d{4}-\d{1,2}-\d{1,2})', r'\1 \2', line)
    line = re.sub(r'(\d)([\u4e00-\u9fa5])', r'\1 \2', line)
    # 预处理常见的空格问题
    line = line.replace("刚果民主共 ", "刚果民主共")
    return line

def _preprocess_table_rows(raw_lines: list) -> list:
    logical_rows = []
    text_buffer = ""
    header_garbage = ['表1', 'Table', '累计', '病例数', '死亡数', '风险等级', '确诊', '疑似', '统计', '截止日期']
    
    for line in raw_lines:
        clean_line = _clean_table_fused_text(line)
        if not clean_line: continue
        
        # 过滤明显表头
        if '表1' in clean_line and ('风险' in clean_line or 'Table' in clean_line): continue
            
        has_date = re.search(r'\d{4}-\d{1,2}-\d{1,2}', clean_line)
        
        if has_date:
            # 如果缓冲区里有垃圾词，抛弃缓冲区
            if text_buffer and any(k in text_buffer for k in header_garbage):
                full_row = clean_line
            else:
                full_row = (text_buffer + " " + clean_line).strip()
            text_buffer = ""
            logical_rows.append(full_row)
        else:
            if clean_line.startswith("注") or len(clean_line) > 100: continue
            # 如果是纯垃圾行，跳过
            if any(k in clean_line for k in header_garbage) and not re.search(r'[\u4e00-\u9fa5]{2,}', clean_line): 
                continue
            text_buffer += clean_line.strip()
            
    return logical_rows

def _extract_numbers(text: str) -> list:
    text = text.replace(',', '')
    tokens = text.split()
    results = []
    for t in tokens:
        if re.match(r'^\d+(?:/\d+)?$', t) or t in ['-', '+']:
            results.append(t)
    return results

def _is_fragment(text: str) -> bool:
    """判断是否是常见的断行碎片"""
    for f in FRAGMENTS:
        if text.startswith(f): return True
    return False

def _fix_broken_rows(rows: list) -> list:
    """
    强力修复逻辑：解决断字、错位、粘连
    """
    if not rows: return rows
    cleaned_rows = []
    
    # 1. 第一遍：处理上一行残留的尾巴 (Split & Merge Up)
    # 场景：Row N: "减少综合征 猴痘" -> 把 "减少综合征" 补给 Row N-1，Row N 剩下 "猴痘"
    for i, row in enumerate(rows):
        disease = row[0]
        
        # 检查是否包含碎片，且碎片后面有空格跟了新词
        for frag in FRAGMENTS:
            if frag in disease:
                # 尝试分割： "减少综合征 猴痘"
                pattern = f"^({frag})\s+(.+)$" 
                match = re.match(pattern, disease)
                if match and cleaned_rows:
                    tail, new_head = match.groups()
                    # 补到上一行的疾病名
                    cleaned_rows[-1][0] += tail
                    # 更新当前行
                    row[0] = new_head
                    break
                
                # 尝试分割紧密粘连的情况 (较少见，但防止 "禽流感人感染")
                # 这里比较保守，只处理特定情况
                if disease.startswith("禽流感人感染"):
                    if cleaned_rows: cleaned_rows[-1][0] += "禽流感"
                    row[0] = disease.replace("禽流感", "", 1)
                    break

        cleaned_rows.append(row)
        
    # 2. 第二遍：处理列偏移和纯粹的断行 (Shift & Merge Country)
    # 场景：Row N Disease="刚果民主共", Country="" -> 移到 Country, Disease继承上文
    # 场景：Row N+1 Disease="和国" -> 拼接到 Row N Country
    final_rows = []
    for i, row in enumerate(cleaned_rows):
        disease = row[0]
        country = row[2]
        
        # 2.1 碎片回补检查：如果当前“疾病”其实是上一行国家或疾病的尾巴
        if _is_fragment(disease):
            if final_rows:
                # 优先检查上一行的国家是否残缺
                prev_country = final_rows[-1][2]
                prev_disease = final_rows[-1][0]
                
                # 如果是国家后缀 (如 "和国")
                if disease in ["和国", "合国", "内亚", "利亚"]:
                    final_rows[-1][2] += disease # 补到上一行国家
                    row[0] = "" # 当前行疾病置空 (稍后继承)
                
                # 如果是疾病后缀 (如 "综合征")
                elif disease in ["综合征", "减少综合征", "出血热", "禽流感"]:
                    final_rows[-1][0] += disease # 补到上一行疾病
                    row[0] = ""

        # 重新获取可能被清空的 disease
        disease = row[0]

        # 2.2 国家名误入疾病列检查
        # 如果疾病列看起来像国家 (如 "刚果民主共")
        is_misplaced_country = False
        for start_str in COUNTRY_STARTS:
            if disease.startswith(start_str):
                is_misplaced_country = True
                break
        
        if is_misplaced_country:
            # 把它移到国家列
            # 如果当前国家列已经有值了 (如 "刚果民主共" + "非洲"), 那 "非洲" 是大洲，country 应该是空的
            # 这里简化处理：直接覆盖或拼接
            if not row[2]: 
                row[2] = disease
            else:
                # 如果原本就有国家名，可能是 "刚果民主共 非洲" 这种解析错误，这里暂不处理复杂情况
                row[2] = disease + row[2] 
            row[0] = "" # 腾空疾病列

        # 2.3 疾病列为空时的继承逻辑 (同上处理)
        # CDC表格通常省略同上
        if not row[0] and final_rows:
            row[0] = final_rows[-1][0]
            
        final_rows.append(row)

    return final_rows

def _process_table_block(table_lines: list) -> str:
    if not table_lines: return ""
    
    headers = ["疾病", "大洲", "国家", "起始日期", "截止日期", "病例数", "死亡数", "输入风险", "旅行风险"]
    temp_rows = []
    logical_rows = _preprocess_table_rows(table_lines)
    
    current_disease = ""
    
    for row in logical_rows:
        row = re.sub(r'\s+', ' ', row).strip()
        date_match = list(re.finditer(r'\d{4}-\d{1,2}-\d{1,2}', row))
        if not date_match: continue
        
        first_date_start = date_match[0].start()
        last_date_end = date_match[-1].end()
        name_part = row[:first_date_start].strip()
        data_part = row[last_date_end:].strip()
        
        start_date = date_match[0].group()
        end_date = date_match[1].group() if len(date_match) > 1 else "-"
        
        continents = ['北美洲', '南美洲', '亚洲', '非洲', '欧洲', '大洋洲']
        target_continent = ""
        continent_idx = -1
        for cont in continents:
            idx = name_part.find(cont)
            if idx != -1:
                target_continent = cont
                continent_idx = idx
                break
        
        disease_str = ""
        country_str = ""
        
        if target_continent:
            part_before = name_part[:continent_idx].strip()
            part_after = name_part[continent_idx + len(target_continent):].strip()
            if part_before:
                disease_str = part_before.replace(target_continent, "").strip()
                current_disease = disease_str
            else:
                disease_str = current_disease
            country_str = part_after
        else:
            # 默认假设是国家
            country_str = name_part
            disease_str = current_disease
        
        if disease_str and country_str.startswith(disease_str):
            country_str = country_str.replace(disease_str, "", 1).strip()
            
        for garbage in ['累计', '病例', '死亡', '风险']:
            country_str = country_str.replace(garbage, '')

        numbers = _extract_numbers(data_part)
        risks = re.findall(r'[高中低]', data_part)
        
        cases = numbers[0] if len(numbers) >= 1 else "-"
        deaths = numbers[1] if len(numbers) >= 2 else "-"
        import_risk = risks[-2] if len(risks) >= 2 else "-"
        travel_risk = risks[-1] if len(risks) >= 1 else "-"
        
        temp_rows.append([disease_str, target_continent, country_str, start_date, end_date, cases, deaths, import_risk, travel_risk])

    # 执行强力修复
    final_rows = _fix_broken_rows(temp_rows)

    if not final_rows: return ""
    
    md = []
    md.append("\n| " + " | ".join(headers) + " |")
    md.append("| " + " | ".join([":---"] * len(headers)) + " |")
    for r in final_rows:
        md.append("| " + " | ".join([str(x) for x in r]) + " |")
    return "\n".join(md) + "\n"

# ==========================================
# 核心入口
# ==========================================

def convert_pdf_to_markdown(pdf_path: str, title: str = None) -> str:
    all_lines = []
    extracted = False
    
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() 
                    if text: all_lines.extend(text.split('\n'))
            if all_lines: extracted = True
        except Exception: pass
            
    if not extracted:
        all_lines = []
        try:
            with open(pdf_path, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text: all_lines.extend(text.split('\n'))
        except Exception: pass

    final_content = []
    table_buffer = []
    paragraph_buffer = [] 
    in_table_mode = False
    
    doc_title = title if title else os.path.basename(pdf_path).replace('.pdf', '')
    final_content.append(f"# {doc_title}\n")
    
    i = 0
    while i < len(all_lines):
        line = all_lines[i].strip()
        if not line:
            i += 1
            continue
        if line.endswith('.pdf'): 
            i += 1
            continue

        is_table_start = (re.match(r'^(表|Table)\s*\d+', line) and ('风险' in line or 'Risk' in line)) or \
                         ('疾病' in line and '国家' in line and '病例' in line)
        
        if is_table_start and not in_table_mode:
            if paragraph_buffer:
                final_content.append("\n" + "".join(paragraph_buffer) + "\n")
                paragraph_buffer = []
            in_table_mode = True
            table_buffer.append(line)
            i += 1
            continue

        if in_table_mode:
            header_check = _identify_header(line)
            is_note = line.startswith("注：") or line.startswith("Note:")
            if header_check or is_note or len(table_buffer) > 100:
                md_table = _process_table_block(table_buffer)
                final_content.append(md_table)
                if is_note: final_content.append(f"\n> {line}\n")
                elif header_check: final_content.append(f"\n{header_check}\n")
                table_buffer = []
                in_table_mode = False
            else:
                table_buffer.append(line)
        else:
            header = _identify_header(line)
            if header:
                if paragraph_buffer:
                    final_content.append("\n" + "".join(paragraph_buffer))
                    paragraph_buffer = []
                final_content.append(f"\n{header}\n")
            elif line.startswith("摘要") or line.startswith("Abstract"):
                content = line.replace("摘要", "").replace("Abstract", "").replace(":", "").replace("：", "").strip()
                final_content.append(f"\n## 摘要\n{content}")
            elif line.startswith("关键词") or line.startswith("Keywords"):
                content = line.replace("关键词", "").replace("Keywords", "").replace(":", "").replace("：", "").strip()
                final_content.append(f"\n**关键词**：{content}\n")
            else:
                clean_l = _clean_text_line(line)
                if not clean_l: 
                    i += 1
                    continue
                if (clean_l.startswith(":") or clean_l.startswith("：")) and paragraph_buffer:
                    paragraph_buffer[-1] += clean_l
                elif not paragraph_buffer:
                    paragraph_buffer.append(clean_l)
                else:
                    if paragraph_buffer[-1].endswith(('。', '！', '？', '.', '!', '?', ';', '；')):
                        final_content.append("\n" + "".join(paragraph_buffer))
                        paragraph_buffer = [clean_l]
                    else:
                        paragraph_buffer.append(clean_l)
        i += 1

    if paragraph_buffer: final_content.append("\n" + "".join(paragraph_buffer))
    if table_buffer: 
        md_table = _process_table_block(table_buffer)
        final_content.append(md_table)

    return "\n".join(final_content)

def parse_full_document(pdf_path: str, output_path: str):
    content = convert_pdf_to_markdown(pdf_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 转换完成: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf_path', help='PDF文件路径')
    args = parser.parse_args()
    if os.path.exists(args.pdf_path):
        parse_full_document(args.pdf_path, args.pdf_path.replace('.pdf', '.md'))
