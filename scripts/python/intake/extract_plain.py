#!/usr/bin/env python3
"""普通文本材料读取支持。"""
from __future__ import annotations
from pathlib import Path
from extract_support import build_unreadable_message

# 这里读取普通文本材料，优先走 UTF-8，再回退到常见中文编码。
def read_plain_text(path_file: Path) -> str:
    """读取普通文本文件。

    参数：
    - `path_file`：待读取文件路径。

    返回：
    - `str`：读取到的文本；失败时返回统一不可读提示。

    异常：
    - 无。
    """

    # 这里先尝试以 UTF-8 读取，覆盖大多数现代研发材料。
    try:

        # 这里直接读取 UTF-8 文本，保持普通材料路径最短。
        return path_file.read_text(encoding="utf-8", errors="ignore")

    # 这里在 UTF-8 读取失败时回退到中文常见编码。
    except Exception:

        # 这里继续尝试 GB18030，提升旧材料和 Windows 导出文件兼容性。
        try:

            # 这里按 GB18030 重新读取，兼容中文历史材料。
            return path_file.read_text(encoding="gb18030", errors="ignore")

        # 这里在两次读取都失败时返回统一不可读提示。
        except Exception as exc:

            # 这里把文件读取失败降级成统一提示文本，不中断整条流水线。
            return build_unreadable_message("text", exc)
