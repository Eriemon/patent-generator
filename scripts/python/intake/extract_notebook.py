#!/usr/bin/env python3
"""Notebook 材料读取支持。"""
from __future__ import annotations
import json
from pathlib import Path
from extract_support import build_parse_error_message
from extract_support import join_nonempty_parts

# 这里统一把 Notebook 单元 source 规整成字符串，降低主流程嵌套层级。
def normalize_cell_source(obj_source: object) -> str:
    """把 Notebook 单元 source 规整成文本。

    参数：
    - `obj_source`：原始 source 字段。

    返回：
    - `str`：规整后的 source 文本。

    异常：
    - 无。
    """

    # 这里把列表形式的 source 合并成完整文本。
    if isinstance(obj_source, list):

        # 这里按原始顺序拼接多段 source 内容。
        return "".join(str(str_item) for str_item in obj_source)

    # 这里在 source 已经是字符串时直接使用。
    if isinstance(obj_source, str):

        # 这里保留原始字符串 source，避免多余格式变化。
        return obj_source

    # 这里对其他异常类型做字符串化兜底，避免整个单元丢失。
    return str(obj_source)

# 这里解析 Notebook 文本，兼顾 Markdown 单元和代码单元阅读。
def extract_ipynb_text(path_file: Path) -> str:
    """提取 Notebook 文本。

    参数：
    - `path_file`：Notebook 文件路径。

    返回：
    - `str`：提取到的文本；解析失败时返回说明文本。

    异常：
    - 无。
    """

    # 这里尝试解析 Notebook JSON 结构，按单元顺序保留上下文。
    try:

        # 这里读取 Notebook 原始 JSON 文本。
        str_notebook_text = path_file.read_text(encoding="utf-8", errors="ignore")  # Notebook 原始 JSON 文本

        # 这里解析 Notebook JSON 结构，供后续逐单元抽取。
        dict_notebook = json.loads(str_notebook_text)  # 供逐单元遍历的 Notebook 数据字典

        # 这里初始化输出片段列表，按单元顺序保存内容。
        list_parts: list[str] = []  # Notebook 文本片段列表

        # 这里逐个处理单元，区分 Markdown 和代码单元。
        for obj_cell in dict_notebook.get("cells", []):

            # 这里跳过非字典单元，避免异常结构中断整条链路。
            if not isinstance(obj_cell, dict):

                # 这里对异常单元结构直接略过，保持解析流程稳健。
                continue

            # 这里读取单元 source，后续统一规整成字符串。
            obj_source = obj_cell.get("source", "")  # 单元原始 source 字段

            # 这里把 source 统一规整成文本，兼容列表与字符串两种格式。
            str_source = normalize_cell_source(obj_source)  # 规整后的单元 source 文本

            # 这里统一清洗 source 两端空白，避免空单元进入结果。
            str_source = str_source.strip()  # 清洗后的 source 文本

            # 这里只保留真正有内容的单元。
            if str_source:

                # 这里根据单元类型生成简洁标题，帮助人工区分内容性质。
                str_cell_type = "Markdown" if obj_cell.get("cell_type") == "markdown" else "Code"  # 单元类型标题

                # 这里把单元标题和正文一起写入结果，保留最小上下文。
                list_parts.append(f"## {str_cell_type} cell\n{str_source}")

        # 这里返回按块拼接后的 Notebook 文本。
        return join_nonempty_parts(list_parts, str_separator="\n\n")

    # 这里把真实解析失败统一映射为稳定提示文本。
    except Exception as exc:

        # 这里返回 Notebook 解析失败提示，供上游继续降级。
        return build_parse_error_message("ipynb", exc)
