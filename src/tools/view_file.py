import argparse
import os
import pypdf

def read_pdf(file_path):
    """专门读取 PDF 内容"""
    content = []
    try:
        reader = pypdf.PdfReader(file_path)
        number_of_pages = len(reader.pages)
        
        content.append(f"[系统提示] 这是一个 PDF 文件，共 {number_of_pages} 页。以下是提取的文本内容：\n")
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                content.append(f"--- 第 {i+1} 页 ---")
                content.append(text)
                content.append("") # 空行
            else:
                content.append(f"--- 第 {i+1} 页 (无文本或扫描件) ---")
                
        return "\n".join(content)
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def read_text(file_path):
    """读取普通文本文件 (md, txt, py, etc.)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # 备选编码尝试
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except Exception as e:
            return f"Error decoding text file: {str(e)}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='通用文件阅读器，支持 .md, .txt, .pdf 等')
    parser.add_argument('--path', type=str, required=True, help='文件的完整路径')
    args = parser.parse_args()
    
    file_path = args.path
    
    if not os.path.exists(file_path):
        print(f"Error: 文件不存在 -> {file_path}")
        return

    # 获取文件后缀
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    # 路由逻辑：根据后缀决定用什么方式读
    if ext == '.pdf':
        content = read_pdf(file_path)
    else:
        # 默认都当做文本文件尝试读取 (.md, .txt, .json, .py, .log ...)
        content = read_text(file_path)
        
    print(content)

if __name__ == "__main__":
    main()
