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
使用方法:
    python create_bookmark.py <input_pdf> <toc_file> <output_pdf> <page_offset>
    
    toc.txt 格式示例 (使用空格缩进表示层级):
    第一章 绪论 1
        1.1 背景 2
        1.2 意义 5
    第二章 方法 10
"""

import re
import sys
import os
from math import gcd
from functools import reduce
from PyPDF2 import PdfReader, PdfWriter

# 常量: Tab 转换为多少个空格
TAB_SIZE = 4

def add_bookmarks(pdf_path, toc_path, output_path, page_offset):
    """
    为PDF文件添加书签
    
    参数:
        pdf_path: 输入PDF文件路径
        toc_path: 目录文本文件路径
        output_path: 输出PDF文件路径
        page_offset: 页码偏移量
    """
    # 检查输入文件是否存在
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"输入PDF文件不存在: {pdf_path}")
    if not os.path.isfile(toc_path):
        raise FileNotFoundError(f"目录文件不存在: {toc_path}")
    
    # 检查输出目录是否存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        raise FileNotFoundError(f"输出目录不存在: {output_dir}")
    
    try:
        # 读取PDF文件
        reader = PdfReader(pdf_path)
        
        # 检查PDF是否加密
        if reader.is_encrypted:
            raise ValueError(f"PDF文件已加密，无法处理: {pdf_path}")
        
        total_pages = len(reader.pages)
        print(f"PDF文件总页数: {total_pages}")
        
    except Exception as e:
        raise ValueError(f"无法读取PDF文件 {pdf_path}: {str(e)}")
    
    writer = PdfWriter()

    # 将所有页面复制到 writer 对象
    for page in reader.pages:
        writer.add_page(page)

    # 用于存储父书签对象的栈
    # parent_stack 存储的是 (bookmark_object, level_index)
    parent_stack = [] 

    try:
        with open(toc_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        raise ValueError(f"无法读取目录文件 {toc_path}: {str(e)}")

    # 检测缩进单位
    indent_sizes = []
    for raw_line in lines:
        expanded = raw_line.expandtabs(TAB_SIZE)  # 将Tab转换为空格
        stripped = expanded.lstrip()
        if not stripped:
            continue
        indent_size = len(expanded) - len(stripped)
        if indent_size > 0:
            indent_sizes.append(indent_size)

    # 使用最大公约数 (GCD) 来检测缩进单位，如果没有检测到或GCD太小则使用默认值4
    if indent_sizes:
        indent_unit = reduce(gcd, indent_sizes)
        # 如果GCD为1，则可能是混合缩进或不规则缩进，使用最小缩进作为单位
        if indent_unit == 1:
            indent_unit = min(indent_sizes)
    else:
        indent_unit = 4
    print(f"检测到的缩进单位: {indent_unit} 个空格")

    line_num = 0
    for line in lines:
        line_num += 1
        line = line.rstrip()
        stripped_line = line.strip()
        if not stripped_line:
            continue

        # 1. 计算缩进级别
        expanded = line.expandtabs(TAB_SIZE)  # 将Tab转换为空格
        indent_size = len(expanded) - len(expanded.lstrip())
        level = indent_size // indent_unit

        # 2. 提取标题和页码
        match = re.search(r'^(.*)\s+(\d+)$', stripped_line)
        
        if not match:
            print(f"警告: 第 {line_num} 行格式不正确，已跳过: {stripped_line}")
            continue
            
        title = match.group(1).strip()
        page_num_str = match.group(2)
        
        # 3. 计算实际页码
        # 逻辑页码 (书上印的) + 偏移量 = 物理页码 (PDF阅读器里的从0开始的索引)
        # PyPDF2 的 add_outline_item 接受的页码索引从 0 开始
        dest_page_index = (int(page_num_str) - 1) + page_offset
        
        # 验证页码是否在有效范围内
        if dest_page_index < 0 or dest_page_index >= total_pages:
            print(f"警告: 第 {line_num} 行的页码 {page_num_str} 经偏移计算后得到的页面索引 {dest_page_index} 超出有效范围 [0, {total_pages-1}]，已跳过")
            continue

        # 4. 查找父节点
        parent = None
        while parent_stack and parent_stack[-1][1] >= level:
            parent_stack.pop()
        
        if parent_stack:
            parent = parent_stack[-1][0]

        # 5. 添加书签
        bookmark = writer.add_outline_item(title, dest_page_index, parent=parent)
        
        # 将当前书签压入栈，作为潜在的父节点
        parent_stack.append((bookmark, level))
        
        print(f"添加书签: {'  '*level} {title} -> Page {dest_page_index+1}")

    # 保存文件
    try:
        with open(output_path, 'wb') as f_out:
            writer.write(f_out)
        print(f"\n完成! 文件已保存至: {output_path}")
    except Exception as e:
        raise IOError(f"无法写入输出文件 {output_path}: {str(e)}")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) != 5:
        print("使用方法:")
        print("  python create_bookmark.py <input_pdf> <toc_file> <output_pdf> <page_offset>")
        print("\n参数说明:")
        print("  input_pdf   : 输入的PDF文件路径")
        print("  toc_file    : 目录文本文件路径")
        print("  output_pdf  : 输出的PDF文件路径")
        print("  page_offset : 页码偏移量 (整数)")
        print("\n页码偏移量说明:")
        print("  打开 PDF，找到正文第 1 页，看它在 PDF 阅读器中显示的是第几页。")
        print("  例如：如果 PDF 阅读器显示第 17 页是正文第 1 页，")
        print("  则偏移量 = 物理页码(17) - 逻辑页码(1) = 16")
        print("\ntoc.txt 格式示例 (使用空格缩进表示层级):")
        print("  第一章 绪论 1")
        print("      1.1 背景 2")
        print("      1.2 意义 5")
        print("  第二章 方法 10")
        sys.exit(1)
    
    INPUT_PDF = sys.argv[1]
    TOC_FILE = sys.argv[2]
    OUTPUT_PDF = sys.argv[3]
    
    try:
        PAGE_OFFSET = int(sys.argv[4])
    except ValueError:
        print(f"错误: 页码偏移量必须是整数，当前输入为: {sys.argv[4]}")
        sys.exit(1)
    
    try:
        add_bookmarks(INPUT_PDF, TOC_FILE, OUTPUT_PDF, PAGE_OFFSET)
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)
