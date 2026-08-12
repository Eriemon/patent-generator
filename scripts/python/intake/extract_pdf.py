#!/usr/bin/env python3
"""PDF 材料读取支持。"""
from __future__ import annotations
from pathlib import Path
from extract_support import build_parse_error_message
from extract_support import join_nonempty_parts
from extract_support import load_optional_symbol

# 这里解析 PDF 文本，在依赖可用时尽量保留前若干页正文。
def extract_pdf_text(path_file: Path, int_max_pages: int = 20) -> str:
    """提取 PDF 文本。

    参数：
    - `path_file`：PDF 文件路径。
    - `int_max_pages`：最多提取的页数。

    返回：
    - `str`：提取到的文本；依赖缺失或解析失败时返回说明文本。

    异常：
    - 无。
    """

    # 这里先加载 PDF 阅读器构造器，避免依赖缺失时直接崩溃。
    dict_load_result = load_optional_symbol("pypdf", "PdfReader", "pdf")  # PDF 依赖加载结果

    # 这里读取依赖加载错误，命中时直接返回统一不可读提示。
    str_error_text = str(dict_load_result["error"] or "")  # 依赖加载错误文本

    # 这里在缺少依赖时立即降级返回，不进入真实解析流程。
    if str_error_text:

        # 这里把依赖问题直接回传给上游，方便明确提醒可选依赖缺失。
        return str_error_text

    # 这里拿到 PDF 阅读器构造器，供后续加载真实文件。
    obj_pdf_reader_factory = dict_load_result["value"]  # PDF 阅读器构造器

    # 这里进入真实解析流程，只抽取前若干页以控制成本。
    try:

        # 这里加载 PDF 阅读器对象，供逐页抽取正文。
        obj_pdf_reader = obj_pdf_reader_factory(str(path_file))  # PDF 阅读器对象

        # 这里初始化页面文本列表。
        list_pages: list[str] = []  # PDF 页面文本列表

        # 这里只抽取前若干页，优先覆盖摘要、背景和方案正文。
        for obj_page in obj_pdf_reader.pages[:int_max_pages]:

            # 这里提取当前页正文，并清洗两端空白。
            str_page_text = str(obj_page.extract_text() or "").strip()  # 当前页文本

            # 这里只保留非空页面内容。
            if str_page_text:

                # 这里把有效页文本加入结果列表，供统一拼接。
                list_pages.append(str_page_text)

        # 这里返回按页拼接后的 PDF 文本。
        return join_nonempty_parts(list_pages, str_separator="\n\n")

    # 这里把真实解析失败统一映射为稳定提示文本。
    except Exception as exc:

        # 这里返回 PDF 解析失败提示，供上游继续降级。
        return build_parse_error_message("pdf", exc)
