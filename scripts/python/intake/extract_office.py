#!/usr/bin/env python3
"""Office 材料读取支持。"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from extract_support import build_parse_error_message
from extract_support import join_nonempty_parts
from extract_support import load_optional_symbol

# 这里把单个表格行压平成可读文本，方便后续直接并入 DOCX 结果。
def flatten_docx_row(obj_row: Any) -> str:
    """把 DOCX 表格行压平成文本。

    参数：
    - `obj_row`：Word 表格行对象。

    返回：
    - `str`：压平后的表格行文本；整行为空时返回空字符串。

    异常：
    - 无。
    """

    # 这里逐个读取单元格内容，并把换行压成空格。
    list_row_text = [str(obj_cell.text or "").replace("\n", " ").strip() for obj_cell in obj_row.cells]  # 当前表格行的单元格文本列表

    # 这里在整行都为空时返回空字符串，避免后续插入空表格行。
    if not any(list_row_text):

        # 这里显式返回空字符串，让调用方决定是否跳过当前表格行。
        return ""

    # 这里用竖线连接表格行内容，保留列间边界。
    return " | ".join(list_row_text)

# 这里按文档顺序提取 Word 段落和表格内容，供 DOCX 入口函数直接复用。
def collect_docx_parts(obj_document: Any) -> list[str]:
    """收集 DOCX 文本片段。

    参数：
    - `obj_document`：Word 文档对象。

    返回：
    - `list[str]`：按文档顺序收集的文本片段列表。

    异常：
    - 无。
    """

    # 这里初始化文本片段列表，按文档顺序保存抽取结果。
    list_parts: list[str] = []  # DOCX 文本片段列表

    # 这里先逐段读取正文内容。
    for obj_paragraph in obj_document.paragraphs:

        # 这里清洗当前段落文本，避免空白段落进入结果。
        str_paragraph_text = str(obj_paragraph.text or "").strip()  # 当前段落文本

        # 这里只保留真正有内容的正文段落。
        if str_paragraph_text:

            # 这里把非空段落加入结果列表，保持文档原始顺序。
            list_parts.append(str_paragraph_text)

    # 这里继续读取表格字段和实验数据。
    for obj_table in obj_document.tables:

        # 这里逐行展开表格，尽量保留字段顺序。
        for obj_row in obj_table.rows:

            # 这里把表格行压平成单行文本，供统一拼接。
            str_row_text = flatten_docx_row(obj_row)  # 当前表格行文本

            # 这里只保留真正非空的表格行。
            if str_row_text:

                # 这里把有效表格行加入结果列表。
                list_parts.append(str_row_text)

    # 这里返回按原始顺序收集的 Word 文本片段。
    return list_parts

# 这里解析 DOCX 文本，优先提取正文段落和表格字段。
def extract_docx_text(path_file: Path) -> str:
    """提取 DOCX 文本。

    参数：
    - `path_file`：DOCX 文件路径。

    返回：
    - `str`：提取到的文本；依赖缺失或解析失败时返回说明文本。

    异常：
    - 无。
    """

    # 这里先加载 Word 文档构造器，避免未安装依赖时直接崩溃。
    dict_load_result = load_optional_symbol("docx", "Document", "docx")  # Word 依赖加载结果

    # 这里读取依赖加载错误，命中时直接返回统一不可读提示。
    str_error_text = str(dict_load_result["error"] or "")  # 依赖加载错误文本

    # 这里在缺少依赖时立即降级返回，不进入真实解析流程。
    if str_error_text:

        # 这里把依赖问题直接回传给上游，方便清晰提示缺少可选能力。
        return str_error_text

    # 这里拿到 Word 文档构造器，供后续加载真实文档。
    obj_document_factory = dict_load_result["value"]  # Word 文档构造器

    # 这里进入真实解析流程，尽量保留段落和表格中的技术内容。
    try:

        # 这里加载 Word 文档对象，供后续分层提取正文和表格。
        obj_document = obj_document_factory(str(path_file))  # Word 文档对象

        # 这里把 Word 的段落与表格结果合并成统一片段列表。
        list_parts = collect_docx_parts(obj_document)  # 按原始阅读顺序收集的 Word 片段列表

        # 这里返回按行拼接后的 DOCX 文本。
        return join_nonempty_parts(list_parts)

    # 这里把真实解析失败统一映射为稳定提示文本。
    except Exception as exc:

        # 这里返回 DOCX 解析失败提示，供上游继续降级。
        return build_parse_error_message("docx", exc)

# 这里统一读取图形文本，避免 PPTX 主流程里堆叠重复判断。
def read_shape_text(obj_shape: Any) -> str:
    """读取图形文本。

    参数：
    - `obj_shape`：演示文稿中的图形对象。

    返回：
    - `str`：图形文本；无文本时返回空字符串。

    异常：
    - 无。
    """

    # 这里只处理可直接读取文本的图形对象。
    if not hasattr(obj_shape, "text"):

        # 这里对无文本属性的图形直接返回空字符串。
        return ""

    # 这里读取并清洗图形文本，避免空文本占位进入结果。
    return str(obj_shape.text or "").strip()

# 这里按页顺序提取 PPTX 文本，供入口函数直接做统一拼接。
def collect_pptx_parts(obj_presentation: Any) -> list[str]:
    """收集 PPTX 文本片段。

    参数：
    - `obj_presentation`：演示文稿对象。

    返回：
    - `list[str]`：按页顺序收集的文本片段列表。

    异常：
    - 无。
    """

    # 这里初始化文本片段列表，按页顺序保存抽取结果。
    list_parts: list[str] = []  # 幻灯片文本片段列表

    # 这里逐页读取标题和正文文本。
    for int_slide_index, obj_slide in enumerate(obj_presentation.slides, start=1):

        # 这里先写入当前页标题标记，方便人工回看页级上下文。
        list_parts.append(f"# Slide {int_slide_index}")

        # 这里逐个遍历当前页图形对象，只读取带文本的图形。
        for obj_shape in obj_slide.shapes:

            # 这里统一读取图形文本，减少主流程中的分支噪声。
            str_shape_text = read_shape_text(obj_shape)  # 当前图形文本

            # 这里只保留非空图形文本。
            if str_shape_text:

                # 这里把图形文本加入当前页结果，保持阅读顺序近似稳定。
                list_parts.append(str_shape_text)

    # 这里返回按页顺序收集的演示文稿文本片段。
    return list_parts

# 这里解析 PPTX 文本，优先保留每页标题和正文文本。
def extract_pptx_text(path_file: Path) -> str:
    """提取 PPTX 文本。

    参数：
    - `path_file`：PPTX 文件路径。

    返回：
    - `str`：提取到的文本；依赖缺失或解析失败时返回说明文本。

    异常：
    - 无。
    """

    # 这里先加载演示文稿构造器，避免缺少可选依赖时把异常直接抛到上游。
    dict_load_result = load_optional_symbol("pptx", "Presentation", "pptx")  # 供 PPTX 入口使用的依赖加载结果

    # 这里单独提取依赖失败文本，便于后面直接做短路返回。
    str_error_text = str(dict_load_result["error"] or "")  # PowerPoint 依赖失败时直接返回的错误文本

    # 如果演示文稿依赖不可用，本函数就在这里结束并返回统一提示。
    if str_error_text:

        # 这里把依赖问题直接回传给上游，方便提示可选依赖未安装。
        return str_error_text

    # 这里保存演示文稿构造器，后面只负责真正打开文件。
    obj_presentation_factory = dict_load_result["value"]  # 演示文稿构造器

    # 这里进入真实解析流程，逐页读取文本框内容。
    try:

        # 这里加载演示文稿对象，供后续按页提取文本。
        obj_presentation = obj_presentation_factory(str(path_file))  # 演示文稿对象

        # 这里收集演示文稿中的所有有效文本片段。
        list_parts = collect_pptx_parts(obj_presentation)  # 演示文稿文本片段列表

        # 这里返回按段拼接后的 PPTX 文本。
        return join_nonempty_parts(list_parts)

    # 这里把幻灯片解析异常统一收敛成稳定错误文本。
    except Exception as exc:

        # 这里把解析失败信息回传给上游，供后续流程继续降级。
        return build_parse_error_message("pptx", exc)
