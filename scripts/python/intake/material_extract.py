#!/usr/bin/env python3
"""研究材料文本抽取入口。"""
from __future__ import annotations
from pathlib import Path
from extract_notebook import extract_ipynb_text
from extract_office import extract_docx_text
from extract_office import extract_pptx_text
from extract_pdf import extract_pdf_text
from extract_plain import read_plain_text
from extract_support import truncate_text

# 这里登记需要专用解析器的材料后缀，避免入口函数堆叠大量条件分支。
SPECIALIZED_EXTRACTORS = dict(  # 只覆盖需要专用抽取流程的后缀映射表
    docx=extract_docx_text,  # 负责 Word 段落和表格抽取
    pptx=extract_pptx_text,  # 负责逐页读取演示文稿文本
    pdf=extract_pdf_text,  # 负责按页提取 PDF 正文
    ipynb=extract_ipynb_text,  # 负责保留 Notebook 单元上下文
)

# 这里统一抽取文本，屏蔽不同材料格式之间的解析差异。
def extract_text(path_file: Path, int_max_chars: int = 200_000) -> str:
    """提取文件文本内容。

    参数：
    - `path_file`：待提取的文件路径。
    - `int_max_chars`：允许保留的最大字符数。

    返回：
    - `str`：提取到的文本；超长时自动截断。

    异常：
    - 无。
    """

    # 这里统一获取小写后缀名，供后续分派给对应解析器。
    str_suffix_key = path_file.suffix.lower().lstrip(".")  # 用于查找解析器的后缀键

    # 这里按后缀选择专用解析器，未命中时回退到普通文本读取。
    obj_extractor = SPECIALIZED_EXTRACTORS.get(str_suffix_key, read_plain_text)  # 本次材料使用的解析器

    # 这里执行选中的解析器，得到当前材料的原始文本。
    str_text = obj_extractor(path_file)  # 当前材料的抽取文本

    # 这里统一对输出长度做收敛，避免单个材料过大。
    return truncate_text(str_text, int_max_chars)
