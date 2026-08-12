#!/usr/bin/env python3
"""把正式交底书 Markdown 导出为 DOCX。

参数：
- 无。

返回：
- 无。

异常：
- 无。
"""
# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations
# 引入参数解析、按路径加载模块、正则、标准输出、ZIP 打包和路径能力。
import argparse
import importlib.util
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

# 引入 XML 转义能力，供标准库回退导出路径安全写入正文文本。
from xml.sax.saxutils import escape

# 固定共享运行时支持模块位置，避免通过改写 sys.path 查找公共工具。
PATH_RUNTIME_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "runtime_support.py"  # 共享运行时支持模块路径

# 固定默认模板路径，供 python-docx 增强路径按需读取页面版式。
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[2] / "assets" / "cn_technical_disclosure_template.docx"  # 默认模板 DOCX 路径

# 预编译 Markdown 标题匹配规则，统一提取标题层级和标题正文。
RE_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")  # Markdown 标题匹配规则

# 预编译 Markdown 无序列表匹配规则，统一识别项目符号行。
RE_BULLET = re.compile(r"^\s*[-*]\s+(.+)$")  # Markdown 无序列表匹配规则

# 预编译 Markdown 有序列表匹配规则，统一识别编号条目行。
RE_ORDERED = re.compile(r"^\s*\d+[.)、]\s+(.+)$")  # Markdown 有序列表匹配规则

# 预编译 Markdown 表格分隔行规则，避免把 `---` 样式行写入正文。
RE_TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")  # Markdown 表格分隔行匹配规则

# 固定 Word 标题层级上限，避免正文标题样式超出最小样式集。
WORD_HEADING_LEVEL_LIMIT = 4  # Word 标题层级上限

# 固定标准库 DOCX 回退导出的 A4 页面宽度。
WORD_PAGE_WIDTH = 11906  # A4 页面宽度

# 固定标准库 DOCX 回退导出的 A4 页面高度。
WORD_PAGE_HEIGHT = 16838  # A4 页面高度

# 固定标准库 DOCX 回退导出的统一页边距。
WORD_PAGE_MARGIN = 1440  # DOCX 页面边距

# 固定标准库 DOCX 回退导出的页眉页脚边距。
WORD_HEADER_FOOTER_MARGIN = 720  # 页眉页脚边距

# 固定正文中的代码块占位文本，提醒评审人在提交前补正式附件内容。
TEXT_ATTACHMENT_PLACEHOLDER = "[代码块或图表示意已移入附件，请在提交前替换为正式内容。]"  # 正文中的附件占位文本

# 固定附件章节标题，集中收纳正文中摘出的代码块和图表示意。
TEXT_ATTACHMENT_TITLE = "附件：待人工转写的代码块与图表示意"  # 附件章节标题

# 固定导出说明标题文本，保证 sidecar 说明文件格式稳定。
TEXT_EXPORT_NOTE_TITLE = "# Export Note"  # 导出说明标题文本

# 按文件路径加载共享运行时支持模块，避免导入期改写解释器搜索路径。
def load_runtime_support_module() -> Any:
    """按路径加载共享运行时支持模块。

    参数：
    - 无。

    返回：
    - `Any`：已经执行源码的共享运行时支持模块对象。

    异常：
    - 支持模块缺失或加载规格不完整时抛出 `ImportError`。
    """

    # 先根据共享模块路径创建加载规格，供后续执行源码。
    obj_runtime_spec = importlib.util.spec_from_file_location("readable_patent_runtime_support", PATH_RUNTIME_SUPPORT)  # 共享运行时支持模块加载规格

    # 在加载规格或加载器缺失时立即终止，避免主流程继续走到空模块对象。
    if obj_runtime_spec is None or obj_runtime_spec.loader is None:

        # 抛出明确阻断原因，提醒调用方先修复公共运行时支持文件。
        raise ImportError("> ERR: [Python] 无法加载 support/runtime_support.py。")

    # 根据有效加载规格创建临时模块对象，供 exec_module 写入工具函数。
    obj_runtime_module = importlib.util.module_from_spec(obj_runtime_spec)  # 已创建但尚未执行源码的运行时支持模块

    # 执行共享运行时支持模块源码，把统一路径工具装入模块对象。
    obj_runtime_spec.loader.exec_module(obj_runtime_module)

    # 把已完成加载的共享模块对象交回导出流程继续复用。
    return obj_runtime_module

# 构造导出入口的参数解析器，统一声明案件目录、输入、输出和模板参数。
def build_parser() -> argparse.ArgumentParser:
    """构造导出入口的命令行参数解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已注册导出参数的解析器对象。

    异常：
    - 无。
    """

    # 先准备解析器说明文本，避免初始化行过长影响阅读。
    str_description = "Export governed disclosure markdown to DOCX."  # 导出入口命令行说明

    # 初始化导出入口解析器，后续逐项注册所有受控参数。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 导出入口参数解析器

    # 注册案件目录参数，允许调用方按正式案件目录自动定位正文草稿。
    obj_parser.add_argument("--case-dir", help="Case directory containing the disclosure draft.")

    # 注册显式输入参数，允许调用方直接指定待导出的 Markdown 文件。
    obj_parser.add_argument("--input", help="Optional markdown path.")

    # 注册显式输出参数，允许调用方覆盖默认导出目录与文件名。
    obj_parser.add_argument("--output", help="Optional DOCX output path.")

    # 注册模板参数，允许调用方覆盖默认模板路径。
    obj_parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="Optional DOCX template path.")

    # 将已经装配完成的解析器对象交给主流程继续解析参数。
    return obj_parser

# 检查当前环境是否安装 python-docx，供导出后端选择逻辑复用。
def is_python_docx_available() -> bool:
    """检查 python-docx 是否可用。

    参数：
    - 无。

    返回：
    - `bool`：模块规格可用时返回 `True`，否则返回 `False`。

    异常：
    - 无。
    """

    # 直接通过模块规格探测 python-docx，避免导入阶段执行额外副作用。
    obj_docx_spec = importlib.util.find_spec("docx")  # python-docx 模块规格对象

    # 返回模块规格是否存在，供主流程选择增强导出还是标准库回退。
    return obj_docx_spec is not None

# 清洗 Markdown 行内标记，避免导出到 Word 后残留源语法噪声。
def strip_markdown_inline_text(str_text: str) -> str:
    """清洗 Markdown 行内标记并返回纯文本。

    参数：
    - `str_text`：待清洗的原始 Markdown 行文本。

    返回：
    - `str`：移除图片、链接和强调标记后的纯文本。

    异常：
    - 无。
    """

    # 先把 Markdown 图片标记替换成可读占位文本，避免图示信息完全丢失。
    str_clean_text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"[图片：\1]", str_text)  # 替换图片语法后的文本

    # 再把 Markdown 链接降级成文字标签，避免把链接语法原样带进 DOCX。
    str_clean_text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", str_clean_text)  # 替换链接语法后的文本

    # 随后去掉行内代码反引号，只保留其中的实际文本内容。
    str_clean_text = re.sub(r"`([^`]+)`", r"\1", str_clean_text)  # 去掉行内代码标记后的文本

    # 最后去掉常见强调标记，让导出正文保留可阅读文本而非 Markdown 语法。
    str_clean_text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", str_clean_text)  # 去掉强调语法后的文本

    # 返回去除首尾空白后的纯文本，供后续段落构造逻辑继续使用。
    return str_clean_text.strip()

# 把单条 Markdown 表格行转换成线性文本，供最小导出路径稳定保留表格信息。
def normalize_table_row(str_line: str) -> str:
    """把单条 Markdown 表格行转换成线性文本。

    参数：
    - `str_line`：当前 Markdown 表格行原文。

    返回：
    - `str`：当前表格行的线性化文本；分隔行会返回空字符串。

    异常：
    - 无。
    """

    # 先准备单元格纯文本列表，后续逐项记录当前表格行的可读内容。
    list_cells: list[str] = []  # 当前表格行的单元格纯文本列表

    # 顺序遍历当前表格行的原始单元格文本，逐项完成行内 Markdown 清洗。
    for str_cell in str_line.strip().strip("|").split("|"):

        # 把当前单元格清洗成纯文本后收进列表，供后续判断分隔行和拼接正文。
        list_cells.append(strip_markdown_inline_text(str_cell.strip()))

    # 先记录每个单元格是否命中分隔符规则，供整行判断是否为表头分隔线复用。
    list_separator_matches = [bool(RE_TABLE_SEPARATOR.fullmatch(str_cell or "")) for str_cell in list_cells]  # 各单元格的分隔符匹配结果

    # 判断当前行是否只是 `---` 分隔行，避免把分隔符误写入正文。
    bool_is_separator = bool(list_cells) and all(list_separator_matches)  # 当前表格行是否只是分隔符

    # 在当前行仅承担表头分隔职责时直接返回空串，交给上游跳过。
    if bool_is_separator:

        # 用空串通知上游忽略当前分隔行，避免导出无意义横线。
        return ""

    # 把当前表格行拼成 `|` 分隔的线性文本，保留最小可读结构。
    str_table_text = " | ".join(str_cell for str_cell in list_cells if str_cell)  # 当前表格行的线性化文本

    # 将线性化后的表格行文本交回正文解析逻辑继续登记。
    return str_table_text

# 把单行 Markdown 正文登记成线性 block，统一处理标题、列表和普通段落。
def append_text_block(
    list_blocks: list[dict[str, Any]],
    str_line: str,
    str_stripped_line: str,
) -> None:
    """把单行 Markdown 正文登记成线性 block。

    参数：
    - `list_blocks`：当前累计的线性 block 列表。
    - `str_line`：保留原始空白的 Markdown 原始文本行。
    - `str_stripped_line`：去掉首尾空白后的 Markdown 文本行。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 先尝试按 Markdown 标题规则识别当前文本行。
    obj_heading_match = RE_HEADING.match(str_stripped_line)  # 当前文本行的标题匹配结果

    # 在命中标题时直接登记受控层级的标题 block。
    if obj_heading_match:

        # 计算当前标题可映射到 Word 的实际层级，避免超过最小样式集上限。
        int_heading_level = min(len(obj_heading_match.group(1)), WORD_HEADING_LEVEL_LIMIT)  # 当前标题映射后的 Word 层级

        # 清洗标题正文文本，避免行内 Markdown 标记残留到导出结果中。
        str_heading_text = strip_markdown_inline_text(obj_heading_match.group(2))  # 当前标题的纯文本内容

        # 把当前标题加入线性输出序列，供两个导出后端复用同一结构。
        list_blocks.append({"kind": "heading", "text": str_heading_text, "level": int_heading_level})

        # 结束当前函数，避免后续列表和段落分支重复处理标题行。
        return

    # 再按项目符号规则识别当前文本行，覆盖 `-` 和 `*` 样式列表。
    obj_bullet_match = RE_BULLET.match(str_line)  # 当前文本行的无序列表匹配结果

    # 在命中无序列表时登记带项目符号前缀的普通段落 block。
    if obj_bullet_match:

        # 清洗无序列表正文，并补上统一项目符号前缀。
        str_bullet_text = "• " + strip_markdown_inline_text(obj_bullet_match.group(1))  # 当前无序列表的线性化正文

        # 把当前项目符号条目加入线性输出序列。
        list_blocks.append({"kind": "paragraph", "text": str_bullet_text})

        # 结束当前函数，避免后续分支重复处理同一条列表项。
        return

    # 若前面都未命中，这里再判断是否属于带编号的步骤条目。
    obj_ordered_match = RE_ORDERED.match(str_line)  # “1.” 样式步骤条目的匹配结果

    # 在命中有序列表时登记保留序号正文的普通段落 block。
    if obj_ordered_match:

        # 清洗编号列表正文，并保留 `1.` 风格前缀以维持阅读顺序。
        str_ordered_text = strip_markdown_inline_text(str_stripped_line)  # 当前编号列表的线性化正文

        # 把当前编号条目加入线性输出序列。
        list_blocks.append({"kind": "paragraph", "text": str_ordered_text})

        # 结束当前函数，避免后续普通段落逻辑再次写入同一行。
        return

    # 将剩余普通文本行清洗成纯文本段落，供导出正文直接写入。
    str_paragraph_text = strip_markdown_inline_text(str_stripped_line)  # 当前普通正文行的纯文本内容

    # 把当前普通段落加入线性输出序列，形成最终 DOCX 正文内容。
    list_blocks.append({"kind": "paragraph", "text": str_paragraph_text})

# 把已闭合的 fenced code block 转成正文占位和附件正文，避免正文直接嵌入大段源码。
def flush_code_block(
    list_blocks: list[dict[str, Any]],
    list_attachments: list[str],
    list_code_lines: list[str],
) -> None:
    """把已闭合的 fenced code block 转成正文占位和附件正文。

    参数：
    - `list_blocks`：当前累计的线性 block 列表。
    - `list_attachments`：当前累计的附件正文列表。
    - `list_code_lines`：当前代码块收集到的原始正文行列表。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 把代码块正文拼成单段附件文本，供文末附件章节集中收纳。
    str_attachment_text = "\n".join(list_code_lines).strip()  # 当前代码块的附件正文文本

    # 仅在代码块正文非空时才把它记入附件列表。
    if str_attachment_text:

        # 将当前代码块正文收进附件列表，保持与正文出现顺序一致。
        list_attachments.append(str_attachment_text)

    # 在正文当前位置写入附件占位提示，提醒评审人后续人工替换。
    list_blocks.append({"kind": "paragraph", "text": TEXT_ATTACHMENT_PLACEHOLDER})

# 把附件正文统一展开成文末章节，确保两个导出后端看到相同的附件结构。
def append_attachment_blocks(
    list_blocks: list[dict[str, Any]],
    list_attachments: list[str],
) -> None:
    """把附件正文统一展开成文末章节。

    参数：
    - `list_blocks`：当前累计的线性 block 列表。
    - `list_attachments`：正文中摘出的附件正文列表。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 只有在存在附件正文时才需要追加分页和附件章节。
    if not list_attachments:

        # 在没有附件内容时提前返回，避免正文尾部平白新增附件标题。
        return

    # 先加入分页 block，把附件章节与正文主体视觉分隔开。
    list_blocks.append({"kind": "page_break"})

    # 再写入附件章节标题，帮助评审人快速定位需要人工处理的内容。
    list_blocks.append({"kind": "heading", "text": TEXT_ATTACHMENT_TITLE, "level": 1})

    # 按原正文出现顺序逐项展开附件正文，保持回看路径稳定。
    for int_attachment_index, str_attachment_text in enumerate(list_attachments, start=1):

        # 先登记当前附件的小标题，便于文末逐条核对代码块来源。
        list_blocks.append({"kind": "paragraph", "text": f"附件 {int_attachment_index}"})

        # 再按行展开当前附件正文，避免超长整段影响 Word 可读性。
        for str_attachment_line in str_attachment_text.splitlines():

            # 只在当前附件行有实际内容时才把它写入文末章节。
            if str_attachment_line.strip():

                # 截断过长附件行，避免单行源码把页面版式横向撑开。
                str_trimmed_attachment_line = str_attachment_line[:600]  # 当前附件行的受控文本

                # 把当前附件行作为普通段落加入附件章节。
                list_blocks.append({"kind": "paragraph", "text": str_trimmed_attachment_line})

# 统一把 Markdown 解析成线性 block 列表，供两个导出后端共用同一份正文结构。
def collect_markdown_blocks(str_markdown: str) -> list[dict[str, Any]]:
    """把 Markdown 解析成线性 block 列表。

    参数：
    - `str_markdown`：待导出的 Markdown 全文。

    返回：
    - `list[MarkdownBlock]`：按正文顺序整理好的线性 block 列表。

    异常：
    - 无。
    """

    # 先准备线性 block 列表，后续会按正文顺序逐项登记内容。
    list_blocks: list[dict[str, Any]] = []  # Markdown 线性 block 列表

    # 把 Markdown 全文按行拆开，便于顺序扫描标题、表格和代码块。
    list_lines = str_markdown.splitlines()  # Markdown 原始行列表

    # 用行游标控制顺序扫描位置，避免复杂递归解析。
    int_index = 0  # 当前顺序扫描到的 Markdown 行号

    # 用状态位记录当前是否位于 fenced code block 内部。
    bool_in_code_block = False  # 当前是否位于代码块内部

    # 用列表暂存当前代码块正文行，待闭合后统一转入附件章节。
    list_code_lines: list[str] = []  # 当前代码块正文暂存列表

    # 用列表暂存所有附件正文，供扫描结束后集中追加到文末。
    list_attachments: list[str] = []  # 正文中摘出的附件正文列表

    # 顺序扫描 Markdown 各行，持续构造受控的线性正文结构。
    while int_index < len(list_lines):

        # 读取当前原始文本行，供后续判断标题、表格和代码块边界。
        str_line = list_lines[int_index]  # 当前原始 Markdown 行

        # 读取当前去首尾空白后的文本行，便于统一判断空行和 fenced code 标记。
        str_stripped_line = str_line.strip()  # 当前去首尾空白后的 Markdown 行

        # 在命中 fenced code block 边界时切换代码块状态。
        if str_stripped_line.startswith("```"):

            # 在代码块闭合点把已收集正文转入附件并写入正文占位。
            if bool_in_code_block:

                # 把当前已闭合代码块刷新成正文占位和附件正文。
                flush_code_block(list_blocks, list_attachments, list_code_lines)

            # 在遇到新的代码块起始边界时清空代码块正文暂存列表。
            else:

                # 为新的代码块正文重新准备暂存列表，避免污染上一段附件内容。
                list_code_lines = []  # 新代码块的正文暂存列表

            # 翻转代码块状态，让下一轮扫描按新状态继续解析正文。
            bool_in_code_block = not bool_in_code_block  # 切换后的代码块状态

            # 跳过当前 fenced code 边界行，继续扫描下一行正文。
            int_index += 1  # 跳过代码块边界后的下一行游标位置

            # 直接进入下一轮扫描，避免边界行继续落入普通正文分支。
            continue

        # 在代码块内部时仅累计原始文本行，不做标题和列表识别。
        if bool_in_code_block:

            # 把当前代码行加入暂存列表，等待代码块闭合后统一写入附件。
            list_code_lines.append(str_line)

            # 推进行游标到下一行，继续读取代码块正文。
            int_index += 1  # 代码块正文继续扫描后的下一行游标位置

            # 直接进入下一轮扫描，避免代码行被误判为普通正文。
            continue

        # 在普通空白行场景下仅跳过当前行，不生成额外段落。
        if not str_stripped_line:

            # 推进行游标到下一行，保持原始空白只承担段落分隔职责。
            int_index += 1  # 空白行跳过后的下一行游标位置

            # 直接进入下一轮扫描，避免空白行进入正文列表。
            continue

        # 在命中 Markdown 表格时收集连续表格行，并按最小线性格式写入正文。
        if str_stripped_line.startswith("|"):

            # 先准备当前表格段的原始行列表，供后续统一线性化处理。
            list_table_lines: list[str] = []  # 当前连续表格段的原始行列表

            # 持续收集连续表格行，直到遇到非表格行才结束。
            while int_index < len(list_lines) and list_lines[int_index].strip().startswith("|"):

                # 把当前表格原始行加入暂存列表，等待统一线性化。
                list_table_lines.append(list_lines[int_index])

                # 推进行游标到下一行，继续判断是否仍属于同一表格段。
                int_index += 1  # 表格段继续收集后的下一行游标位置

            # 逐条把当前表格段线性化成可阅读的普通段落文本。
            for str_table_line in list_table_lines:

                # 把当前表格行转换成线性文本，必要时过滤纯分隔行。
                str_table_text = normalize_table_row(str_table_line)  # 当前表格行转换后的线性正文

                # 只在当前表格行存在实际正文时才把它写入线性 block 列表。
                if str_table_text:

                    # 把当前表格行作为普通段落登记，保证回退导出也能阅读表格内容。
                    list_blocks.append({"kind": "paragraph", "text": str_table_text})

            # 直接进入下一轮扫描，避免表格段首行再次落入普通正文分支。
            continue

        # 把当前普通文本行登记成标题、列表或普通段落 block。
        append_text_block(list_blocks, str_line, str_stripped_line)

        # 推进行游标到下一行，继续扫描后续 Markdown 内容。
        int_index += 1  # 普通正文处理后的下一行游标位置

    # 在扫描结束时兜底处理未闭合代码块，避免最后一段源码完全丢失。
    if bool_in_code_block:

        # 把末尾未闭合代码块也转入正文占位和附件章节。
        flush_code_block(list_blocks, list_attachments, list_code_lines)

    # 把附件正文统一展开到文末，保持附件结构和顺序稳定。
    append_attachment_blocks(list_blocks, list_attachments)

    # 将完整线性 block 列表交给导出后端继续写入 DOCX。
    return list_blocks

# 把单个线性 block 写入 python-docx 文档对象，供增强导出路径复用。
def append_block_to_document(obj_document: Any, dict_block: dict[str, Any]) -> None:
    """把单个线性 block 写入 python-docx 文档对象。

    参数：
    - `obj_document`：python-docx 的 `Document` 文档对象。
    - `dict_block`：当前待写入的线性正文 block 字典。

    返回：
    - `None`。

    异常：
    - python-docx 写入失败时由底层异常继续上抛。
    """

    # 在当前 block 是分页符时直接追加 Word 分页。
    if dict_block["kind"] == "page_break":

        # 把分页符插入文档流中，为附件章节预留清晰的版面切换点。
        obj_document.add_page_break()

        # 当前分页 block 已完成写入，不需要继续走正文和标题分支。
        return

    # 在当前 block 是标题时按受控层级写入 Word 标题样式。
    if dict_block["kind"] == "heading":

        # 用 Word 原生标题样式写入当前标题正文，提升阅读层次。
        obj_document.add_heading(str(dict_block["text"]), level=int(dict_block["level"]))

        # 当前标题 block 已完成写入，不需要继续落入普通段落分支。
        return

    # 将剩余普通段落 block 直接追加到 Word 正文中。
    obj_document.add_paragraph(str(dict_block["text"]))

# 在存在模板文件时复制其首页版式，避免增强导出路径完全丢失模板页边距设置。
def copy_template_layout(obj_document: Any, path_template: Path | None) -> None:
    """复制模板首页版式设置。

    参数：
    - `obj_document`：当前待写入的 python-docx 文档对象。
    - `path_template`：可选模板 DOCX 路径。

    返回：
    - `None`。

    异常：
    - 读取模板失败时由底层异常继续上抛。
    """

    # 在未提供模板路径或模板文件缺失时直接跳过版式复制。
    if path_template is None or not path_template.exists():

        # 在没有可读取模板时提前返回，让增强导出继续使用默认版式。
        return

    # 只在函数内部导入 python-docx，避免模块导入期强依赖第三方包。
    from docx import Document

    # 读取模板文档对象，准备复制其首页 section 版式。
    obj_template_document = Document(str(path_template))  # 模板 DOCX 文档对象

    # 在模板文档没有 section 时直接跳过版式复制，避免空模板触发越界访问。
    if not obj_template_document.sections:

        # 在模板不提供 section 信息时直接返回默认文档版式。
        return

    # 读取模板首页 section，作为当前导出文档的版式来源。
    obj_template_section = obj_template_document.sections[0]  # 模板首页 section 对象

    # 读取目标文档首页 section，后续把模板版式拷贝到这里。
    obj_target_section = obj_document.sections[0]  # 当前导出文档首页 section 对象

    # 复制模板顶部页边距，保持文档首部留白与模板一致。
    obj_target_section.top_margin = obj_template_section.top_margin  # 目标文档顶部页边距

    # 复制模板底部页边距，保持文档底部留白与模板一致。
    obj_target_section.bottom_margin = obj_template_section.bottom_margin  # 目标文档底部页边距

    # 复制模板左侧页边距，尽量贴近模板既有版式宽度。
    obj_target_section.left_margin = obj_template_section.left_margin  # 目标文档左侧页边距

    # 复制模板右侧页边距，避免正文宽度与模板差异过大。
    obj_target_section.right_margin = obj_template_section.right_margin  # 目标文档右侧页边距

    # 复制模板页眉边距，让页眉位置和模板保持一致。
    obj_target_section.header_distance = obj_template_section.header_distance  # 目标文档页眉边距

    # 复制模板页脚边距，让页脚位置和模板保持一致。
    obj_target_section.footer_distance = obj_template_section.footer_distance  # 目标文档页脚边距

# 构造最小 Word 段落 XML 片段，供标准库 DOCX 回退路径写入正文段落。
def render_word_paragraph_xml(
    str_text: str,
    str_style_id: str | None = None,
) -> str:
    """构造最小 Word 段落 XML 片段。

    参数：
    - `str_text`：待写入段落的纯文本内容。
    - `str_style_id`：可选的 Word 段落样式 ID。

    返回：
    - `str`：单个段落的 Word XML 片段。

    异常：
    - 无。
    """

    # 在传入样式 ID 时构造段落样式 XML，否则保持空字符串。
    str_style_xml = f'<w:pPr><w:pStyle w:val="{str_style_id}"/></w:pPr>' if str_style_id else ""  # 当前段落的样式 XML 片段

    # 返回带可选样式信息的最小 Word 段落 XML。
    return (
        "<w:p>"
        f"{str_style_xml}"
        '<w:r><w:t xml:space="preserve">'
        f"{escape(str_text)}"
        "</w:t></w:r>"
        "</w:p>"
    )

# 构造最小 Word 分页 XML 片段，供标准库 DOCX 回退路径插入分页符。
def render_word_page_break_xml() -> str:
    """构造最小 Word 分页 XML 片段。

    参数：
    - 无。

    返回：
    - `str`：带分页符的最小 Word XML 片段。

    异常：
    - 无。
    """

    # 直接返回带分页符的最小 Word XML 片段。
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'

# 把线性 block 列表转换成最小 document.xml，供标准库 DOCX 回退路径打包写入。
def convert_blocks_to_document_xml(list_blocks: list[dict[str, Any]]) -> str:
    """把线性 block 列表转换成最小 document.xml。

    参数：
    - `list_blocks`：按正文顺序整理好的线性 block 列表。

    返回：
    - `str`：最小可用的 Word document.xml 文本。

    异常：
    - 无。
    """

    # 先准备 Word body XML 片段列表，后续逐项追加正文结构。
    list_body_xml: list[str] = []  # Word body XML 片段列表

    # 顺序遍历线性 block，把标题、普通段落和分页转成 Word XML。
    for dict_block in list_blocks:

        # 在当前 block 是分页符时直接写入分页 XML。
        if dict_block["kind"] == "page_break":

            # 把分页 XML 片段加入 Word body，分隔正文主体与附件章节。
            list_body_xml.append(render_word_page_break_xml())

            # 当前分页 block 已完成转换，直接继续处理下一个 block。
            continue

        # 在当前 block 是标题时按受控层级写入 Heading 样式段落。
        if dict_block["kind"] == "heading":

            # 把当前标题转换成带 Heading 样式的段落 XML。
            list_body_xml.append(
                render_word_paragraph_xml(str(dict_block["text"]), f"Heading{int(dict_block['level'])}")
            )

            # 当前标题 block 已完成转换，直接继续处理下一个 block。
            continue

        # 将普通段落 block 直接转换成正文段落 XML。
        list_body_xml.append(render_word_paragraph_xml(str(dict_block["text"])))

    # 在 block 列表为空时补一个空段落，保证最小 document.xml 结构完整。
    if not list_body_xml:

        # 写入一个空段落兜底，避免最小 DOCX 缺少正文节点。
        list_body_xml.append(render_word_paragraph_xml(""))

    # 组装 section XML，统一声明页面尺寸和页边距。
    str_section_xml = (  # document.xml 结尾的 section XML 片段
        f'<w:sectPr><w:pgSz w:w="{WORD_PAGE_WIDTH}" w:h="{WORD_PAGE_HEIGHT}"/>'
        f'<w:pgMar w:top="{WORD_PAGE_MARGIN}" w:right="{WORD_PAGE_MARGIN}" '
        f'w:bottom="{WORD_PAGE_MARGIN}" w:left="{WORD_PAGE_MARGIN}" '
        f'w:header="{WORD_HEADER_FOOTER_MARGIN}" '
        f'w:footer="{WORD_HEADER_FOOTER_MARGIN}" '
        'w:gutter="0"/></w:sectPr>'
    )

    # 返回完整的最小 document.xml 文本，供 ZIP 打包步骤直接写入。
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'mc:Ignorable="w14 wp14">'
        "<w:body>"
        + "".join(list_body_xml)
        + str_section_xml
        + "</w:body></w:document>"
    )

# 返回最小 Word 样式 XML，供标准库 DOCX 回退路径提供标题样式。
def render_styles_xml() -> str:
    """返回最小 Word 样式 XML。

    参数：
    - 无。

    返回：
    - `str`：覆盖 Normal 到 Heading4 的最小 Word 样式 XML。

    异常：
    - 无。
    """

    # 用多行 XML 文本直接描述最小样式集，避免样式行列表带来过长行和多行赋值噪声。
    str_styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/><w:qFormat/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/><w:qFormat/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/><w:qFormat/><w:rPr><w:b/><w:sz w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading4">
    <w:name w:val="heading 4"/><w:qFormat/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr>
  </w:style>
</w:styles>"""  # 最小 Word 样式 XML 文本

    # 把最小样式 XML 文本交回回退导出路径直接写入 ZIP。
    return str_styles_xml

# 使用 python-docx 执行 DOCX 导出，优先提供更自然的 Word 阅读体验。
def export_with_python_docx(
    dict_paths: dict[str, Path | None],
    obj_runtime_module: Any,
) -> str:
    """使用 python-docx 执行 DOCX 导出。

    参数：
    - `dict_paths`：已经解析完成的输入、输出和模板路径集合。
    - `obj_runtime_module`：共享运行时支持模块对象。

    返回：
    - `str`：本次导出模式标识，固定返回 `python-docx`。

    异常：
    - Markdown 读取、DOCX 写入或目录创建失败时由底层异常继续上抛。
    """

    # 只在函数体内部导入 python-docx，避免模块导入阶段要求第三方包必须存在。
    from docx import Document

    # 读取 Markdown 全文，供线性 block 解析逻辑统一处理正文结构。
    str_markdown = dict_paths["path_input"].read_text(encoding="utf-8")  # 回退导出读取到的 Markdown 原文

    # 把 Markdown 全文解析成线性 block 列表，供导出后端逐项写入 Word。
    list_blocks = collect_markdown_blocks(str_markdown)  # 回退导出准备写入 ZIP 的 block 序列

    # 初始化空白 Word 文档对象，作为当前增强导出的正文容器。
    obj_document = Document()  # 当前导出的 Word 文档对象

    # 在提供模板时复制其首页版式，尽量贴近模板设定的页面留白。
    copy_template_layout(obj_document, dict_paths["path_template"])

    # 逐项把线性 block 写入 Word 文档，保持解析顺序与正文顺序一致。
    for dict_block in list_blocks:

        # 把当前 block 追加到 Word 文档中，统一处理标题、段落和分页。
        append_block_to_document(obj_document, dict_block)

    # 确保 DOCX 输出目录存在，避免保存阶段因目录缺失而失败。
    obj_runtime_module.ensure_dir(dict_paths["path_output"].parent)

    # 把当前 Word 文档保存到目标输出路径，形成最终 DOCX 交付件。
    obj_document.save(str(dict_paths["path_output"]))

    # 用模式标识告知上游当前走的是 python-docx 增强导出路径。
    return "python-docx"

# 使用 Python 标准库直接打包最小 DOCX，作为 python-docx 缺失时的本地回退路径。
def export_with_stdlib_docx(
    dict_paths: dict[str, Path | None],
    obj_runtime_module: Any,
) -> str:
    """使用标准库回退导出 DOCX。

    参数：
    - `dict_paths`：已经解析完成的输入、输出和模板路径集合。
    - `obj_runtime_module`：共享运行时支持模块对象。

    返回：
    - `str`：本次导出模式标识，固定返回 `stdlib-docx`。

    异常：
    - Markdown 读取、ZIP 写入或目录创建失败时由底层异常继续上抛。
    """

    # 从导出输入读取 Markdown 原文，为 ZIP 回退路径准备源文本。
    str_markdown = dict_paths["path_input"].read_text(encoding="utf-8")  # 输入 Markdown 全文

    # 把源文本压平成 block 序列，供最小 DOCX 结构逐项写入正文。
    list_blocks = collect_markdown_blocks(str_markdown)  # 当前 Markdown 的线性 block 列表

    # 确保 DOCX 输出目录存在，避免 ZIP 打包阶段因目录缺失而失败。
    obj_runtime_module.ensure_dir(dict_paths["path_output"].parent)

    # 固定根内容类型清单文本，声明最小 DOCX 包内必需部件的 MIME 类型。
    str_content_types_xml = (  # 根内容类型清单 XML 文本
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        "</Types>"
    )

    # 固定根关系文件文本，把包入口指向主文档部件。
    str_root_relationships_xml = (  # 根关系 XML 文本
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )

    # 先生成标题样式部件文本，供 ZIP 包内 `word/styles.xml` 直接使用。
    str_styles_xml = render_styles_xml()  # 写入 ZIP 的 styles.xml 正文

    # 再渲染 document.xml 文本，供回退路径写入正文主体结构。
    str_document_xml = convert_blocks_to_document_xml(list_blocks)  # 最小 DOCX document.xml 文本

    # 打开目标 DOCX ZIP 文件，逐项写入最小 Office Open XML 结构。
    with zipfile.ZipFile(
        dict_paths["path_output"],
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as obj_zip_file:

        # 写入根内容类型清单，声明最小 DOCX 包的部件类型。
        obj_zip_file.writestr("[Content_Types].xml", str_content_types_xml)

        # 写入根关系文件，把包入口指向主文档部件。
        obj_zip_file.writestr("_rels/.rels", str_root_relationships_xml)

        # 写入最小样式 XML，保证标题层级在 Word 中可读。
        obj_zip_file.writestr("word/styles.xml", str_styles_xml)

        # 写入根据线性 block 生成的 document.xml 文本。
        obj_zip_file.writestr("word/document.xml", str_document_xml)

    # 用模式标识告知上游当前走的是标准库最小 DOCX 回退路径。
    return "stdlib-docx"

# 解析输入、输出和模板路径，统一处理按案件目录自动定位正文草稿的逻辑。
def resolve_paths(
    namespace_arguments: argparse.Namespace,
    obj_runtime_module: Any,
) -> dict[str, Path | None]:
    """解析输入、输出和模板路径。

    参数：
    - `namespace_arguments`：命令行解析后的参数对象。
    - `obj_runtime_module`：共享运行时支持模块对象。

    返回：
    - `dict[str, Path | None]`：输入 Markdown、输出 DOCX 和可选模板路径的封装字典。

    异常：
    - 缺少输入来源时抛出 `ValueError`。
    - 自动定位后的输入草稿缺失时抛出 `FileNotFoundError`。
    """

    # 在调用方显式给出案件目录时解析其绝对路径，否则保留空值。
    path_case_dir = Path(namespace_arguments.case_dir).resolve() if namespace_arguments.case_dir else None  # 案件目录绝对路径

    # 在调用方显式给出输入草稿时解析其绝对路径，否则保留空值供自动定位逻辑处理。
    path_input = Path(namespace_arguments.input).resolve() if namespace_arguments.input else None  # 输入 Markdown 绝对路径

    # 在调用方显式给出模板路径时解析其绝对路径，否则保留空值。
    path_template = Path(namespace_arguments.template).resolve() if namespace_arguments.template else None  # 模板 DOCX 绝对路径

    # 在既未提供输入文件也未提供案件目录时直接报错，避免自动定位无从开始。
    if path_input is None and path_case_dir is None:

        # 抛出明确参数错误，要求调用方至少提供一种正文来源。
        raise ValueError("> ERR: [Python] 请提供 --input 或 --case-dir。")

    # 在未显式提供输入草稿时按案件目录自动定位当前可用正文文件。
    if path_input is None:

        # 通过共享运行时支持模块查找当前案件下最合适的正文草稿。
        path_input = obj_runtime_module.find_disclosure_draft(path_case_dir)  # 自动定位到的正文草稿路径

    # 在最终仍无法获得有效正文草稿时立即报错。
    if path_input is None or not path_input.exists():

        # 抛出明确文件缺失错误，避免后续导出路径对空输入继续工作。
        raise FileNotFoundError("> ERR: [Python] 缺少 disclosure draft markdown。")

    # 在调用方显式给出输出路径时直接解析并使用该绝对路径。
    if namespace_arguments.output:

        # 解析调用方显式指定的 DOCX 输出路径，作为本次最终交付位置。
        path_output = Path(namespace_arguments.output).resolve()  # 显式指定的 DOCX 输出路径

    # 在未显式给出输出路径时按案件导出目录和时间戳自动构造文件名。
    else:

        # 在案件目录尚未明确时从输入 Markdown 的目录结构反推案件根目录。
        if path_case_dir is None:

            # 根据正式案件目录布局从输入文件位置回推出案件根目录。
            path_case_dir = path_input.parent.parent  # 由输入文件位置反推出的案件根目录

        # 确保案件导出目录存在，后续 DOCX 会稳定落到这里。
        path_export_dir = obj_runtime_module.ensure_dir(path_case_dir / "05_exports")  # 当前案件导出目录

        # 基于输入草稿名和当前时间戳自动构造 DOCX 文件名。
        str_output_name = (  # 自动生成的 DOCX 文件名
            f"{obj_runtime_module.sanitize_name(path_input.stem)}_"
            f"{obj_runtime_module.now_timestamp()}.docx"
        )

        # 拼出最终 DOCX 输出路径，保持正式导出目录结构一致。
        path_output = path_export_dir / str_output_name  # 自动构造的 DOCX 输出路径

    # 用字典封装解析结果，减少主流程中的多值拆包复杂度。
    dict_paths = {"path_input": path_input, "path_output": path_output, "path_template": path_template}  # 当前导出流程使用的受控路径集合

    # 将已经解析完成的路径字典交回主流程继续导出。
    return dict_paths

# 生成导出说明 Markdown，记录源文件、导出模式和模板来源，便于回看导出上下文。
def render_export_note(
    path_input: Path,
    str_mode: str,
    path_template: Path | None,
) -> str:
    """渲染导出说明 Markdown 文本。

    参数：
    - `path_input`：输入 Markdown 路径。
    - `str_mode`：实际采用的导出模式标识。
    - `path_template`：可选模板 DOCX 路径。

    返回：
    - `str`：导出说明 Markdown 文本。

    异常：
    - 无。
    """

    # 在存在模板路径时提取模板文件名，否则回退到 `none`。
    str_template_name = path_template.name if path_template else "none"  # 导出说明中展示的模板名称

    # 先准备导出说明文本行列表，后续按固定顺序逐条登记说明内容。
    list_export_note_lines = [TEXT_EXPORT_NOTE_TITLE]  # 导出说明 Markdown 行列表

    # 为标题与正文条目之间补一个空行，保持 sidecar 可读性。
    list_export_note_lines.append("")

    # 登记本次导出的 Markdown 来源文件名，方便后续回看输入材料。
    list_export_note_lines.append(f"- source markdown: `{path_input.name}`")

    # 登记本次实际采用的导出模式，便于判断是否走了标准库回退。
    list_export_note_lines.append(f"- export mode: `{str_mode}`")

    # 登记本次使用的模板名称，便于追溯页面版式来源。
    list_export_note_lines.append(f"- template: `{str_template_name}`")

    # 在说明末尾补一个空行，保持 sidecar 文本结尾结构稳定。
    list_export_note_lines.append("")

    # 拼接导出说明 Markdown 文本，供 sidecar 文件直接写入。
    return "\n".join(list_export_note_lines)

# 执行 DOCX 导出入口，按环境能力在 python-docx 与标准库回退之间选择后端。
def main() -> int:
    """执行 DOCX 导出入口。

    参数：
    - 无。

    返回：
    - `int`：导出成功时返回 `0`。

    异常：
    - 参数无效、输入草稿缺失或导出写入失败时由底层异常继续上抛。
    """

    # 加载共享运行时支持模块，复用统一路径、时间和正文草稿查找工具。
    obj_runtime_module = load_runtime_support_module()  # 共享运行时支持模块对象

    # 解析命令行参数，读取案件目录、输入、输出和模板配置。
    namespace_arguments = build_parser().parse_args()  # 导出入口命令行参数对象

    # 把命令行参数收束成统一路径字典，避免主流程手工分支拼路径。
    dict_paths = resolve_paths(namespace_arguments, obj_runtime_module)  # 主流程共享的输入输出路径字典

    # 在 python-docx 可用时优先走增强导出路径，提升 Word 阅读体验。
    if is_python_docx_available():

        # 执行 python-docx 增强导出，并记录本次导出模式标识。
        str_mode = export_with_python_docx(dict_paths, obj_runtime_module)  # python-docx 增强导出模式标识

    # 在 python-docx 缺失时回退到标准库最小 DOCX 导出路径。
    else:

        # 执行标准库回退导出，并记录本次导出模式标识。
        str_mode = export_with_stdlib_docx(dict_paths, obj_runtime_module)  # 标准库回退导出模式标识

    # 基于输入、模式和模板信息生成导出说明 sidecar 文本。
    str_export_note = render_export_note(dict_paths["path_input"], str_mode, dict_paths["path_template"])  # 导出说明 Markdown 文本

    # 固定导出说明输出路径，保持 DOCX 与 sidecar 一一对应。
    path_export_note = dict_paths["path_output"].with_suffix(".export_note.md")  # 导出说明 Markdown 输出路径

    # 把导出说明写入同目录，便于回看本次导出的来源和模式。
    obj_runtime_module.write_text_file(path_export_note, str_export_note)

    # 把 DOCX 输出绝对路径作为机器可消费的单行结果写回上游流程。
    sys.stdout.write(str(dict_paths["path_output"].resolve()) + "\n")

    # 用零退出码告知调用方当前导出流程已经成功完成。
    return 0

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())

