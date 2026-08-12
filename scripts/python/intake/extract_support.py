#!/usr/bin/env python3
"""材料抽取共享支持。"""
from __future__ import annotations
import importlib
from typing import Any

# 这里统一生成可选依赖缺失时的返回文本，保证上游能稳定识别失败格式。
def build_unreadable_message(str_format_name: str, exc: Exception) -> str:
    """构造依赖缺失或格式不可读提示。

    参数：
    - `str_format_name`：材料格式名称。
    - `exc`：触发失败的异常对象。

    返回：
    - `str`：统一格式的不可读提示文本。

    异常：
    - 无。
    """

    # 这里返回统一失败格式，便于上游稳定识别降级原因。
    return (
        f"[{str_format_name} unreadable: install optional office dependencies via "
        f"requirements.txt; {exc}]"
    )

# 这里统一生成解析失败提示，保证不同格式返回相同的错误边界。
def build_parse_error_message(str_format_name: str, exc: Exception) -> str:
    """构造解析失败提示。

    参数：
    - `str_format_name`：材料格式名称。
    - `exc`：触发失败的异常对象。

    返回：
    - `str`：统一格式的解析失败提示文本。

    异常：
    - 无。
    """

    # 这里返回统一解析失败文本，方便上游统一记录和解释。
    return f"[{str_format_name} parse error: {exc}]"

# 这里统一加载可选依赖符号，避免每种材料格式都重复写一套导入逻辑。
def load_optional_symbol(str_module_name: str, str_symbol_name: str, str_format_name: str) -> dict[str, Any]:
    """加载可选依赖中的目标符号。

    参数：
    - `str_module_name`：模块名称。
    - `str_symbol_name`：模块内目标符号名称。
    - `str_format_name`：材料格式名称。

    返回：
    - `dict[str, Any]`：包含 `value` 和 `error` 的结果字典。

    异常：
    - 无。
    """

    # 这里先尝试导入可选依赖模块。
    try:

        # 这里按模块名动态导入依赖，避免源文件携带类型忽略注释。
        obj_module = importlib.import_module(str_module_name)  # 动态导入得到的模块对象

    # 这里在依赖缺失时返回统一不可读提示。
    except Exception as exc:

        # 这里把依赖缺失信息放进统一结果字典，供调用方直接返回。
        return {
            "value": None,
            "error": build_unreadable_message(str_format_name, exc),
        }

    # 这里确认模块中确实存在目标符号，避免调用期再爆出属性错误。
    if not hasattr(obj_module, str_symbol_name):

        # 这里构造符号缺失异常，沿用统一不可读提示格式。
        exc_missing_symbol = AttributeError(f"missing symbol: {str_symbol_name}")  # 依赖符号缺失异常

        # 这里返回符号缺失结果，供调用方直接降级。
        return {
            "value": None,
            "error": build_unreadable_message(str_format_name, exc_missing_symbol),
        }

    # 这里读取目标依赖符号，供后续具体格式解析函数使用。
    obj_symbol = getattr(obj_module, str_symbol_name)  # 依赖模块中的目标符号

    # 这里返回成功加载结果，调用方可以继续进入真实解析流程。
    return {
        "value": obj_symbol,
        "error": None,
    }

# 这里统一拼接抽取到的非空文本片段，避免每个解析器重复写清洗逻辑。
def join_nonempty_parts(list_parts: list[str], str_separator: str = "\n") -> str:
    """拼接非空文本片段。

    参数：
    - `list_parts`：原始文本片段列表。
    - `str_separator`：片段拼接分隔符。

    返回：
    - `str`：拼接后的文本结果。

    异常：
    - 无。
    """

    # 这里初始化清洗后的文本片段列表。
    list_clean_parts: list[str] = []  # 去空白后的有效文本片段

    # 这里逐个过滤空文本和纯空白片段。
    for str_part in list_parts:

        # 这里统一去掉片段首尾空白，避免拼接后出现多余空行。
        str_clean_part = str(str_part or "").strip()  # 清洗后的单个文本片段

        # 这里只保留真正有内容的片段。
        if str_clean_part:

            # 这里保存有效文本片段，供统一拼接输出。
            list_clean_parts.append(str_clean_part)

    # 这里按指定分隔符拼接有效文本片段。
    return str_separator.join(list_clean_parts)

# 这里在输出过长时统一截断文本，避免单个材料把 JSON 和 Markdown 撑爆。
def truncate_text(str_text: str, int_max_chars: int) -> str:
    """按字符上限截断文本。

    参数：
    - `str_text`：原始文本。
    - `int_max_chars`：允许保留的最大字符数。

    返回：
    - `str`：原文或截断后的文本。

    异常：
    - 无。
    """

    # 这里在未超过上限时直接返回原文，避免无意义复制。
    if len(str_text) <= int_max_chars:

        # 这里保留完整文本，供后续盘点和事实抽取使用。
        return str_text

    # 这里在超长场景下追加统一截断提示。
    return str_text[:int_max_chars] + "\n[... truncated by material_extract.extract_text ...]"
