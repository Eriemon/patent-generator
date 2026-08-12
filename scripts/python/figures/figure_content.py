#!/usr/bin/env python3
"""提取附图正文中的方法步骤与系统模块。"""

# 延迟解析类型注解，保持独立文件规格加载兼容。
from __future__ import annotations

# 标准库提供命令行解析与通用类型标注。
import argparse
from typing import Any

# 复用已登记布局模块中的提取规则和文本规整 helper。
from readable_patent_figure_layout import (
    METHOD_STEP_SUMMARY_MAX_CHARS,
    MODULE_FUNCTION_MAX_CHARS,
    MODULE_NAME_MAX_CHARS,
    RE_METHOD_STEP,

    # 下列规则与 helper 负责正文匹配和附图文本规整。
    RE_SYSTEM_MODULE,
    clip_figure_source_text,
)

# 构造附图入口解析器，保留案件目录和可选输入字段。
def build_parser() -> argparse.ArgumentParser:
    """构造附图入口的命令行解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已注册参数的解析器对象。

    异常：
    - 无。
    """

    # 先准备解析器说明文本，避免初始化语句过长。
    str_description = "Generate governed figure drafts from the disclosure markdown."  # 入口说明文本

    # 初始化当前附图入口的命令行解析器。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 附图入口解析器

    # 注册案件目录参数，确保附图产物固定写回当前案件空间。
    obj_parser.add_argument("--case-dir", required=True)

    # 注册可选输入草稿参数，允许覆盖自动定位的 disclosure draft。
    obj_parser.add_argument("--input", help="Optional disclosure markdown path.")

    # 返回完成参数注册的解析器对象。
    return obj_parser

# 从正文草稿中提取方法步骤摘要，为方法流程图节点生成提供输入。
def extract_method_steps(str_markdown: str, module_runtime_support: Any) -> list[dict[str, str]]:
    """提取方法步骤摘要。

    参数：
    - `str_markdown`：交底书草稿 Markdown 全文。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[dict[str, str]]`：步骤编号和摘要组成的列表；缺失时返回兜底步骤。

    异常：
    - 无。
    """

    # 先准备方法步骤结果列表，后续逐项登记正文中命中的步骤。
    list_steps: list[dict[str, str]] = []  # 方法步骤结果列表

    # 逐项遍历正文中命中的步骤编号与摘要文本。
    for str_step_id, str_summary in RE_METHOD_STEP.findall(str_markdown):

        # 先清洗正文提取出来的步骤摘要，保证附图处理只面对规整后的句子。
        str_summary_text = module_runtime_support.clean_text(str_summary)  # 当前步骤清洗后的原始摘要

        # 再对规整后的步骤摘要做受控截断，避免流程图文本硬截在半句中间。
        str_clean_summary = clip_figure_source_text(str_summary_text, METHOD_STEP_SUMMARY_MAX_CHARS)  # 当前步骤的清洗摘要

        # 组装当前步骤记录，供 SVG 与 Mermaid 渲染逻辑共同复用。
        dict_step_record = {  # 单个方法步骤记录
            "id": str_step_id,  # 步骤编号
            "summary": str_clean_summary,  # 步骤摘要
        }

        # 把当前步骤记录追加到结果列表，保持正文原始顺序。
        list_steps.append(dict_step_record)

    # 在正文没有可用步骤时返回兜底步骤，保证最小附图 smoke 能力。
    if not list_steps:

        # 返回待补充兜底步骤，让附图生成流程仍然可以继续。
        return [{"id": "S101", "summary": "待补充方法流程"}]

    # 返回结构化方法步骤列表，供流程图和清单共同复用。
    return list_steps

# 从正文草稿中提取系统模块摘要，为系统模块图生成提供输入。
def extract_system_modules(str_markdown: str, module_runtime_support: Any) -> list[dict[str, str]]:
    """提取系统模块摘要。

    参数：
    - `str_markdown`：交底书草稿 Markdown 全文。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[dict[str, str]]`：模块名称与功能组成的列表；缺失时返回兜底模块。

    异常：
    - 无。
    """

    # 先准备系统模块结果列表，后续逐项登记正文中命中的模块。
    list_modules: list[dict[str, str]] = []  # 系统模块结果列表

    # 逐项遍历正文中命中的模块名称与功能描述。
    for str_name, str_function in RE_SYSTEM_MODULE.findall(str_markdown):

        # 先清洗正文提取出来的模块名称，保证后续截断不会夹带多余空白。
        str_module_name_text = module_runtime_support.clean_text(str_name)  # 当前模块清洗后的原始名称

        # 再对模块名称做受控截断，保证标题仍能留出功能说明空间。
        str_clean_name = clip_figure_source_text(str_module_name_text, MODULE_NAME_MAX_CHARS)  # 当前模块的清洗名称

        # 先清洗正文提取出来的模块功能说明，避免换行前还带着多余空白。
        str_module_function_text = module_runtime_support.clean_text(str_function)  # 当前模块清洗后的原始功能说明

        # 再对模块功能说明做受控截断，避免说明文字把双列模块框完全撑爆。
        str_clean_function = clip_figure_source_text(str_module_function_text, MODULE_FUNCTION_MAX_CHARS)  # 当前模块的清洗功能描述

        # 组装当前模块记录，供 SVG、Mermaid 和清单共同复用。
        dict_module_record = {  # 单个系统模块记录
            "name": str_clean_name,  # 模块名称
            "function": str_clean_function,  # 模块功能描述
        }

        # 把当前模块记录追加到结果列表，保持正文模块顺序。
        list_modules.append(dict_module_record)

    # 在正文没有可用模块时返回兜底模块，保证最小附图 smoke 能力。
    if not list_modules:

        # 返回待补充兜底模块，让系统图生成流程仍然可以继续。
        return [{"name": "待补充处理模块", "function": "待补充模块功能"}]

    # 返回结构化系统模块列表，供系统图和清单共同复用。
    return list_modules

# 把圆角矩形框的样式参数集中封装，供流程图与模块图绘制共用。
