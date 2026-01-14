"""
脚本名称: PDF 自动书签添加工具 (Auto Booker)
功能描述: 
    读取一个格式化的目录文本文件(toc.txt)和一个原始PDF文件，
    根据文本中的缩进层级和页码，自动为PDF添加多级书签(Outlines)，
    并处理物理页码与逻辑页码的偏移量。
实现原理:
    1. 使用 PyPDF2 读取原始 PDF。
    2. 解析 toc.txt，利用正则表达式分离标题和页码，利用缩进判断层级。
    3. 使用栈 (Stack) 结构来管理父子书签关系。
    4. 保存为新的 PDF 文件。
依赖库: PyPDF2 (pip install PyPDF2)
"""

import re
import sys
from PyPDF2 import PdfReader, PdfWriter

def add_bookmarks(pdf_path, toc_path, output_path, page_offset):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    # 将所有页面复制到 writer 对象
    for page in reader.pages:
        writer.add_page(page)

    # 用于存储父书签对象的栈
    # stack[0] 对应 0 缩进 (一级标题)
    # stack[1] 对应 1 缩进 (二级标题) ...
    # parent_stack 存储的是 (bookmark_object, level_index)
    parent_stack = [] 

    with open(toc_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            if not line:
                continue

            # 1. 计算缩进级别 (假设使用4个空格或1个Tab作为一级缩进)
            # 这里的逻辑是计算行首空格数，每4个空格算一级
            indent_size = len(line) - len(line.lstrip())
            level = indent_size // 4  

            # 2. 提取标题和页码
            # 匹配模式：任意文本 + 空格 + 数字(作为页码)
            # strip() 去除首尾空白
            content = line.strip()
            match = re.search(r'^(.*)\s+(\d+)$', content)
            
            if match:
                title = match.group(1).strip()
                page_num_str = match.group(2)
                
                # 3. 计算实际页码
                # 逻辑页码 (书上印的) + 偏移量 = 物理页码 (PDF阅读器里的从0开始的索引)
                # PyPDF2 的 add_outline_item 接受的页码索引从 0 开始
                # 假设: 书中页码 1 是 PDF 的第 24 页，那么 offset 应设为 23
                # 计算公式: (书页码 - 1) + offset
                dest_page_index = (int(page_num_str) - 1) + page_offset

                # 4. 查找父节点
                parent = None
                # 如果当前层级比栈顶层级小或相等，说明上一级结束了，弹出栈顶直到找到父级
                while parent_stack and parent_stack[-1][1] >= level:
                    parent_stack.pop()
                
                if parent_stack:
                    parent = parent_stack[-1][0]

                # 5. 添加书签
                # fit='/Fit' 表示跳转后页面适合窗口宽度
                bookmark = writer.add_outline_item(title, dest_page_index, parent=parent)
                
                # 将当前书签压入栈，作为潜在的父节点
                parent_stack.append((bookmark, level))
                
                print(f"添加书签: {'  '*level} {title} -> Page {dest_page_index+1}")

    # 保存文件
    with open(output_path, 'wb') as f_out:
        writer.write(f_out)
    print(f"\n完成! 文件已保存至: {output_path}")

if __name__ == "__main__":
    # === 配置区域 ===
    INPUT_PDF = r"F:\learn_source\研究生课程\计算机视觉三维重建\机器人学中的状态估计 (（加）蒂莫西·D.巴富特译；高翔，谢晓佳) (Z-Library).pdf"
    TOC_FILE = "toc.txt"
    OUTPUT_PDF = r"F:\learn_source\研究生课程\计算机视觉三维重建\机器人学中的状态估计 (（加）蒂莫西·D.巴富特译；高翔，谢晓佳) (Z-Library1).pdf"
    
    # 关键参数：页码偏移量 (Page Offset)
    # 打开PDF，找到正文第1页，看它是PDF阅读器显示的第几页。
    # 在你提供的文件中，第24页是"第1讲 预备知识" (正文第1页)。
    # 所以偏移量 = 物理页码(24) - 逻辑页码(1) = 23
    PAGE_OFFSET = 16 
    # ================

    add_bookmarks(INPUT_PDF, TOC_FILE, OUTPUT_PDF, PAGE_OFFSET)
