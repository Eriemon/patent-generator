#!/usr/bin/env python3
"""根据正式交底书草稿生成本地附图草案与清单。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、按路径加载模块、标准输出和路径能力，供附图入口稳定运行。
import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

# 引入 HTML 转义和正则能力，供 SVG 文本安全输出与正文结构提取逻辑复用。
from html import escape
import re

# 固定共享运行时支持模块路径，避免通过修改 sys.path 导入公共工具。
PATH_RUNTIME_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "runtime_support.py"  # 共享运行时支持模块路径

# 预编译方法步骤匹配规则，提取形如 S101 的方法步骤摘要。
RE_METHOD_STEP = re.compile(r"^(S\d{3,4})：(.+)$", re.M)  # 方法步骤匹配规则

# 预编译系统模块匹配规则，提取模块名称及其对应功能描述。
RE_SYSTEM_MODULE = re.compile(r"^\d+\.\s*([^，,]+模块)[，,]\s*用于\s*(.+)$", re.M)  # 系统模块匹配规则

# 固定模块图切换双列布局的阈值，超过两个模块时启用双列排版。
MODULE_DOUBLE_COLUMN_THRESHOLD = 2  # 模块图双列布局阈值

# 固定模块图单列布局列数，供少量模块场景复用。
MODULE_SINGLE_COLUMN = 1  # 模块图单列布局列数

# 把双列布局的列数单独命名，避免布局判断里反复出现裸常量。
MODULE_DOUBLE_COLUMN = 2  # 多于两个模块时使用的列数值

# 固定模块图画布宽度，兼顾双列布局和标题排版空间。
MODULE_CANVAS_WIDTH = 840  # 模块图画布宽度

# 固定模块框宽度，保证模块标题与功能说明均可读。
MODULE_BOX_WIDTH = 320  # 模块框宽度

# 固定模块框高度，保证标题与副标题两行排版稳定。
MODULE_BOX_HEIGHT = 72  # 模块框高度

# 固定双列布局模块框的水平间距，避免左右模块挤压。
MODULE_GAP_X = 80  # 模块框水平间距

# 固定模块框的垂直间距，给跨行箭头留出可读空间。
MODULE_GAP_Y = 44  # 模块框垂直间距

# 固定模块图画布的顶部基础高度，容纳图题和首行模块。
MODULE_CANVAS_BASE_HEIGHT = 120  # 模块图画布基础高度

# 固定模块图图题横向中心点，保证标题位于画布正中。
MODULE_TITLE_CENTER_X = 420  # 模块图图题横向中心点

# 固定模块图图题纵坐标，保证标题与模块框之间有稳定留白。
MODULE_TITLE_Y = 32  # 模块图图题纵坐标

# 固定模块图图题字号，保证输出图题可读。
MODULE_TITLE_FONT_SIZE = 18  # 模块图图题字号

# 固定双列布局首列左边距，保证模块框不会贴边。
MODULE_DOUBLE_COLUMN_LEFT = 70  # 双列布局首列左边距

# 固定单列布局左边距，保证单列时模块框整体居中。
MODULE_SINGLE_COLUMN_LEFT = 260  # 单列布局左边距

# 固定模块框首行纵向起点，保证图题下方留白稳定。
MODULE_TOP_MARGIN = 62  # 模块框首行纵向起点

# 按文件路径加载共享运行时支持模块，避免在导入期改写解释器模块搜索路径。
def load_runtime_support_module() -> Any:
    """按路径加载共享运行时支持模块。

    参数：
    - 无。

    返回：
    - `Any`：已经执行源码的共享运行时支持模块对象。

    异常：
    - 支持模块缺失或无法加载时抛出 `ImportError`。
    """

    # 先根据共享支持模块文件路径创建模块加载规格。
    obj_spec = importlib.util.spec_from_file_location("readable_patent_runtime_support", PATH_RUNTIME_SUPPORT)  # 共享支持模块加载规格

    # 在加载规格或加载器缺失时立即报错，避免后续空对象异常难以定位。
    if obj_spec is None or obj_spec.loader is None:

        # 抛出明确导入错误，提醒调用方先修复 support/runtime_support.py。
        raise ImportError("> ERR: [Python] 无法加载 support/runtime_support.py。")

    # 根据加载规格创建临时模块对象，供后续执行共享支持源码。
    module_runtime_support = importlib.util.module_from_spec(obj_spec)  # 临时共享支持模块对象

    # 执行共享支持模块源码，把公共文件与时间工具装入模块对象。
    obj_spec.loader.exec_module(module_runtime_support)

    # 返回已完成加载的共享支持模块，供附图入口复用。
    return module_runtime_support

# 构造命令行参数解析器，统一声明案件目录和可选输入草稿参数。
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

        # 截断并清洗当前步骤摘要，避免图中文字过长影响排版。
        str_clean_summary = module_runtime_support.clean_text(str_summary)[:36]  # 当前步骤的清洗摘要

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

        # 截断并清洗模块名称，避免图框标题超宽溢出。
        str_clean_name = module_runtime_support.clean_text(str_name)[:24]  # 当前模块的清洗名称

        # 截断并清洗模块功能描述，避免图框副标题过长影响排版。
        str_clean_function = module_runtime_support.clean_text(str_function)[:40]  # 当前模块的清洗功能描述

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

# 渲染单个 SVG 矩形框，统一输出标题和副标题两层文本。
def render_svg_box(
    int_x: int,
    int_y: int,
    int_width: int,
    int_height: int,
    str_label: str,
    str_subtitle: str,
) -> str:
    """渲染单个 SVG 矩形框。

    参数：
    - `int_x`：矩形框左上角横坐标。
    - `int_y`：矩形框左上角纵坐标。
    - `int_width`：矩形框宽度。
    - `int_height`：矩形框高度。
    - `str_label`：矩形框主标题文本。
    - `str_subtitle`：矩形框副标题文本。

    返回：
    - `str`：单个矩形框的 SVG 片段文本。

    异常：
    - 无。
    """

    # 对主标题文本做 HTML 转义，避免特殊字符破坏 SVG 结构。
    str_safe_label = escape(str_label)  # 已转义的主标题文本

    # 对副标题文本单独做 HTML 转义，确保说明文字同样不会破坏 SVG 结构。
    str_safe_subtitle = escape(str_subtitle)  # 已转义的副标题文本

    # 返回当前矩形框完整 SVG 片段，包含边框、主标题和副标题。
    return (
        f'<rect x="{int_x}" y="{int_y}" width="{int_width}" height="{int_height}" '
        'rx="10" ry="10" fill="white" stroke="black" stroke-width="1.5"/>'
        f'<text x="{int_x + int_width / 2}" y="{int_y + 24}" text-anchor="middle" '
        'font-size="15" font-family="Arial, sans-serif">'
        f"{str_safe_label}</text>"
        f'<text x="{int_x + int_width / 2}" y="{int_y + 48}" text-anchor="middle" '
        'font-size="12" font-family="Arial, sans-serif">'
        f"{str_safe_subtitle}</text>"
    )

# 渲染单条 SVG 箭头连接线，统一使用内置箭头标记。
def render_svg_arrow(int_x1: int, int_y1: int, int_x2: int, int_y2: int) -> str:
    """渲染单条 SVG 箭头连接线。

    参数：
    - `int_x1`：起点横坐标。
    - `int_y1`：起点纵坐标。
    - `int_x2`：终点横坐标。
    - `int_y2`：终点纵坐标。

    返回：
    - `str`：单条箭头连接线的 SVG 片段文本。

    异常：
    - 无。
    """

    # 返回当前箭头连接线完整 SVG 片段，供流程图和模块图共同复用。
    return (
        f'<line x1="{int_x1}" y1="{int_y1}" x2="{int_x2}" y2="{int_y2}" '
        'stroke="black" stroke-width="1.4" marker-end="url(#arrow)"/>'
    )

# 渲染通用 SVG 头部，统一定义画布、箭头标记和白色背景。
def render_svg_header(int_width: int, int_height: int) -> str:
    """渲染通用 SVG 头部。

    参数：
    - `int_width`：画布宽度。
    - `int_height`：画布高度。

    返回：
    - `str`：通用 SVG 头部片段文本。

    异常：
    - 无。
    """

    # 返回当前 SVG 画布头部，统一注入 viewBox、箭头定义和背景矩形。
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int_width}" height="{int_height}" '
        f'viewBox="0 0 {int_width} {int_height}">'
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" '
        'orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="black"/>'
        "</marker></defs>"
        f'<rect x="0" y="0" width="{int_width}" height="{int_height}" fill="white"/>'
    )

# 渲染方法流程图 SVG，按步骤顺序生成竖向节点和连接箭头。
def render_flow_svg(list_steps: list[dict[str, str]]) -> str:
    """渲染方法流程图 SVG。

    参数：
    - `list_steps`：结构化方法步骤列表。

    返回：
    - `str`：方法流程图 SVG 文本。

    异常：
    - 无。
    """

    # 固定方法流程图宽度，保证步骤框与标题有稳定排版。
    int_width = 760  # 方法流程图画布宽度

    # 根据步骤数量计算画布高度，给每个步骤框预留足够垂直空间。
    int_height = 110 + len(list_steps) * 108  # 方法流程图画布高度

    # 先准备 SVG 文本片段列表，后续逐项追加标题、节点与箭头。
    list_parts = [  # 方法流程图 SVG 片段列表
        render_svg_header(int_width, int_height),  # 通用 SVG 头部
        '<text x="380" y="32" text-anchor="middle" font-size="18" font-family="Arial, sans-serif">图 1 方法流程图</text>',  # 图题文本
    ]

    # 固定流程图矩形框横坐标，保证各步骤节点居中对齐。
    int_box_x = 120  # 方法步骤框横坐标

    # 固定流程图矩形框宽度，保证标题和摘要有稳定容纳空间。
    int_box_width = 520  # 方法步骤框宽度

    # 固定流程图矩形框高度，保证标题和副标题两行均可完整显示。
    int_box_height = 68  # 方法步骤框高度

    # 记录上一节点底部纵坐标，供后续箭头连接使用。
    int_previous_bottom = 0  # 上一节点底部纵坐标

    # 按方法步骤顺序逐项渲染节点和连接箭头。
    for int_index, dict_step in enumerate(list_steps):

        # 计算当前步骤框纵坐标，保持各节点等距排布。
        int_box_y = 60 + int_index * 98  # 当前步骤框纵坐标

        # 组装当前步骤框主标题文本，合并步骤编号和摘要。
        str_step_label = f"{dict_step['id']}：{dict_step['summary']}"  # 当前步骤框主标题文本

        # 渲染当前步骤框并追加到 SVG 片段列表。
        list_parts.append(
            render_svg_box(
                int_box_x,
                int_box_y,
                int_box_width,
                int_box_height,
                str_step_label,
                "输入 -> 动作 -> 输出",
            )
        )

        # 从第二个节点开始补充箭头，串起完整的步骤顺序关系。
        if int_index > 0:

            # 渲染上一节点到当前节点的竖向箭头。
            list_parts.append(render_svg_arrow(380, int_previous_bottom, 380, int_box_y))

        # 把当前步骤框底部坐标保存下来，下一轮箭头会从这里继续向下连接。
        int_previous_bottom = int_box_y + int_box_height  # 下一轮箭头起点的纵坐标

    # 追加 SVG 结束标签，形成完整方法流程图文本。
    list_parts.append("</svg>")

    # 返回完整方法流程图 SVG 文本，供案件目录落盘。
    return "\n".join(list_parts)

# 渲染系统模块图 SVG，按模块数量自动切换单列或双列布局。
def render_module_svg(list_modules: list[dict[str, str]]) -> str:
    """渲染系统模块图 SVG。

    参数：
    - `list_modules`：结构化系统模块列表。

    返回：
    - `str`：系统模块图 SVG 文本。

    异常：
    - 无。
    """

    # 在模块多于两个时使用双列布局，减少纵向长度。
    int_columns = MODULE_DOUBLE_COLUMN if len(list_modules) > MODULE_DOUBLE_COLUMN_THRESHOLD else MODULE_SINGLE_COLUMN  # 模块图列数

    # 固定模块图画布宽度，兼顾单列与双列布局的阅读稳定性。
    int_width = MODULE_CANVAS_WIDTH  # 系统模块图画布宽度

    # 读取当前渲染要使用的模块框宽度，保证标题和功能副标题都可读。
    int_box_width = MODULE_BOX_WIDTH  # 当前渲染使用的模块框宽度

    # 读取当前渲染要使用的模块框高度，保证标题和副标题两行排版稳定。
    int_box_height = MODULE_BOX_HEIGHT  # 当前渲染使用的模块框高度

    # 读取当前渲染要使用的水平间距，避免双列布局时模块框相互拥挤。
    int_gap_x = MODULE_GAP_X  # 当前渲染使用的模块框水平间距

    # 读取当前渲染要使用的垂直间距，给跨行箭头留出连接空间。
    int_gap_y = MODULE_GAP_Y  # 当前渲染使用的模块框垂直间距

    # 根据模块数量和列数计算行数，供画布高度估算复用。
    int_rows = (len(list_modules) + int_columns - MODULE_SINGLE_COLUMN) // int_columns  # 模块图总行数

    # 根据行数计算画布高度，保证所有模块框都有稳定空间。
    int_height = MODULE_CANVAS_BASE_HEIGHT + int_rows * (int_box_height + int_gap_y)  # 系统模块图画布高度

    # 先准备系统模块图的 SVG 片段列表，后续逐项追加图题、模块框和箭头。
    list_parts = [  # 系统模块图 SVG 片段列表
        render_svg_header(int_width, int_height),  # 注入模块图专用 SVG 头部与背景
        (
            f'<text x="{MODULE_TITLE_CENTER_X}" y="{MODULE_TITLE_Y}" '
            'text-anchor="middle" '
            f'font-size="{MODULE_TITLE_FONT_SIZE}" '
            'font-family="Arial, sans-serif">'
            "图 2 系统模块图</text>"
        ),  # 模块图标题文本
    ]

    # 记录各模块框左上角坐标，供后续箭头连接逻辑复用。
    list_positions: list[tuple[int, int]] = []  # 模块框坐标列表

    # 按模块顺序逐项渲染模块框并记录其坐标。
    for int_index, dict_module in enumerate(list_modules):

        # 计算当前模块所在行号，供布局定位使用。
        int_row = int_index // int_columns  # 当前模块行号

        # 根据索引计算当前模块落在第几列，后续用它决定横坐标。
        int_column = int_index % int_columns  # 当前模块列号

        # 判断当前模块图是否处于双列布局，后续横坐标逻辑会据此切换左右边距。
        bool_use_double_column = int_columns == MODULE_DOUBLE_COLUMN  # 当前模块图是否使用双列布局

        # 根据布局模式计算当前模块框横坐标。
        if bool_use_double_column:

            # 在双列布局下按照列号和水平间距推导横坐标。
            int_x = MODULE_DOUBLE_COLUMN_LEFT + int_column * (int_box_width + int_gap_x)  # 双列布局下的模块框横坐标

        # 在单列布局下直接使用居中左边距，保证整张图保持稳定居中。
        else:

            # 固定单列布局时的横坐标，让所有模块框保持居中对齐。
            int_x = MODULE_SINGLE_COLUMN_LEFT  # 单列布局模块框的居中横坐标

        # 根据行号计算当前模块框纵坐标。
        int_y = MODULE_TOP_MARGIN + int_row * (int_box_height + int_gap_y)  # 当前模块框纵坐标

        # 记录当前模块框坐标，供后续连接箭头使用。
        list_positions.append((int_x, int_y))

        # 渲染当前模块框并追加到 SVG 片段列表。
        list_parts.append(
            render_svg_box(
                int_x,
                int_y,
                int_box_width,
                int_box_height,
                dict_module["name"],
                dict_module["function"],
            )
        )

    # 按模块顺序补充相邻模块之间的连接箭头。
    for int_index in range(len(list_positions) - 1):

        # 读取当前模块框左上角坐标。
        int_x1, int_y1 = list_positions[int_index]  # 当前模块框左上角坐标

        # 读取下一模块框左上角坐标。
        int_x2, int_y2 = list_positions[int_index + 1]  # 下一模块框左上角坐标

        # 在同一行时绘制水平箭头，更符合模块左右串联的阅读方向。
        if int_y1 == int_y2:

            # 追加当前模块到下一模块的水平箭头。
            list_parts.append(
                render_svg_arrow(
                    int_x1 + int_box_width,
                    int_y1 + int_box_height // 2,
                    int_x2,
                    int_y2 + int_box_height // 2,
                )
            )

        # 在跨行时绘制竖向箭头，保持模块迁移路径可读。
        else:

            # 追加当前模块到底下一行模块的竖向箭头。
            list_parts.append(
                render_svg_arrow(
                    int_x1 + int_box_width // 2,
                    int_y1 + int_box_height,
                    int_x2 + int_box_width // 2,
                    int_y2,
                )
            )

    # 追加 SVG 结束标签，形成完整系统模块图文本。
    list_parts.append("</svg>")

    # 返回完整系统模块图 SVG 文本，供案件目录落盘。
    return "\n".join(list_parts)

# 生成 Mermaid 源文件，便于后续外部渲染或人工细化。
def write_mermaid_files(
    path_output_dir: Path,
    list_steps: list[dict[str, str]],
    list_modules: list[dict[str, str]],
    module_runtime_support: Any,
) -> None:
    """写出 Mermaid 源文件。

    参数：
    - `path_output_dir`：附图输出目录路径。
    - `list_steps`：结构化方法步骤列表。
    - `list_modules`：结构化系统模块列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `None`。

    异常：
    - 文件写入失败时由底层异常上抛。
    """

    # 先准备方法流程图 Mermaid 行列表，固定使用自上而下方向。
    list_step_lines = ["flowchart TD"]  # 方法流程图 Mermaid 行列表

    # 按步骤顺序逐项生成节点定义和顺序箭头。
    for int_index, dict_step in enumerate(list_steps):

        # 固定当前步骤节点编号，保证 Mermaid 文件结构稳定。
        str_node = f"N{int_index}"  # 当前步骤节点编号

        # 追加当前步骤节点定义，保留步骤编号与摘要的组合文本。
        list_step_lines.append(f'  {str_node}["{dict_step["id"]}：{dict_step["summary"]}"]')

        # 从第二个步骤开始补充前后节点关系。
        if int_index > 0:

            # 追加上一节点到当前节点的顺序箭头。
            list_step_lines.append(f"  N{int_index - 1} --> {str_node}")

    # 先准备系统模块图 Mermaid 行列表，固定使用自左向右方向。
    list_module_lines = ["flowchart LR"]  # 系统模块图 Mermaid 行列表

    # 按模块顺序逐项生成节点定义和顺序箭头。
    for int_index, dict_module in enumerate(list_modules):

        # 固定当前模块节点编号，保证 Mermaid 文件结构稳定。
        str_node = f"M{int_index}"  # 当前模块节点编号

        # 追加当前模块节点定义，保留模块名称文本。
        list_module_lines.append(f'  {str_node}["{dict_module["name"]}"]')

        # 从第二个模块开始补充前后节点关系。
        if int_index > 0:

            # 追加上一模块到当前模块的顺序箭头。
            list_module_lines.append(f"  M{int_index - 1} --> {str_node}")

    # 拼出方法流程图 Mermaid 文件路径，保持附图目录命名稳定。
    path_flow_mermaid = path_output_dir / "图1_方法流程图.mmd"  # 方法流程图 Mermaid 文件路径

    # 拼出系统模块图 Mermaid 文件路径，保持附图目录命名稳定。
    path_module_mermaid = path_output_dir / "图2_系统模块图.mmd"  # 系统模块图 Mermaid 文件路径

    # 把方法流程图 Mermaid 文本写入案件目录。
    module_runtime_support.write_text_file(path_flow_mermaid, "\n".join(list_step_lines) + "\n")

    # 把系统模块图 Mermaid 文本写入案件目录。
    module_runtime_support.write_text_file(path_module_mermaid, "\n".join(list_module_lines) + "\n")

# 组装 figures manifest 结构化数据，供 review 和 export 阶段复用。
def build_manifest(
    path_markdown: Path,
    path_flow_svg: Path,
    path_module_svg: Path,
    list_steps: list[dict[str, str]],
    list_modules: list[dict[str, str]],
    module_runtime_support: Any,
) -> dict[str, Any]:
    """构造 figures manifest 结构化数据。

    参数：
    - `path_markdown`：正文草稿路径。
    - `path_flow_svg`：方法流程图 SVG 路径。
    - `path_module_svg`：系统模块图 SVG 路径。
    - `list_steps`：结构化方法步骤列表。
    - `list_modules`：结构化系统模块列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `dict[str, Any]`：figures manifest 结构化数据。

    异常：
    - 无。
    """

    # 提取方法流程图中的步骤编号列表，供 manifest 索引与后续校验复用。
    list_step_ids = [dict_step["id"] for dict_step in list_steps]  # 方法流程图步骤编号列表

    # 提取系统模块图中的模块名称列表，供 manifest 索引与后续校验复用。
    list_module_names = [dict_module["name"] for dict_module in list_modules]  # 系统模块图模块名称列表

    # 返回完整 figures manifest 结构化数据，供 JSON 落盘与后链工具复用。
    return {
        "generated_at": module_runtime_support.iso_now(),
        "source_draft": str(path_markdown.resolve()),
        "figures": [
            {
                "figure_no": "图1",
                "title": "方法流程图",
                "file": path_flow_svg.name,
                "steps": list_step_ids,
            },
            {
                "figure_no": "图2",
                "title": "系统模块图",
                "file": path_module_svg.name,
                "modules": list_module_names,
            },
        ],
    }

# 生成 figures manifest 的 Markdown 摘要文本，便于人工快速审阅。
def render_manifest_markdown(path_markdown: Path) -> str:
    """渲染 figures manifest Markdown 摘要文本。

    参数：
    - `path_markdown`：正文草稿路径。

    返回：
    - `str`：figures manifest Markdown 摘要文本。

    异常：
    - 无。
    """

    # 按固定顺序直接组装摘要 Markdown 文本，输出标题、来源草稿和两条附图摘要。
    return "\n".join(
        [
            "# Figures Manifest",  # 文档标题
            "",  # 标题后的空行
            f"Source draft: `{path_markdown.name}`",  # 来源草稿文件名
            "",  # 来源草稿后的空行
            "- 图1：方法流程图",  # 图1 摘要
            "- 图2：系统模块图",  # 图2 的摘要条目
            "",  # 文档结尾空行
        ]
    )

# 执行附图生成入口，读取正文草稿并落盘 SVG、Mermaid 与 manifest 产物。
def main() -> int:
    """执行附图生成入口。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 找不到正文草稿时抛出 `FileNotFoundError`。
    - 共享支持加载或文件写入失败时由底层异常上抛。
    """

    # 加载共享运行时支持模块，复用正文后链的一致文件与时间工具。
    module_runtime_support = load_runtime_support_module()  # 共享运行时支持模块

    # 解析命令行参数，读取案件目录和可选输入草稿路径。
    namespace_arguments = build_parser().parse_args()  # 附图入口参数对象

    # 解析案件目录绝对路径，确保附图产物固定落在当前案件空间。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 当前案件根目录

    # 在调用方显式给出输入草稿时解析其绝对路径，否则保留空值供自动定位逻辑处理。
    path_input = Path(namespace_arguments.input).resolve() if namespace_arguments.input else None  # 显式指定的输入草稿路径

    # 定位当前案件可用的 disclosure draft，优先使用显式输入路径。
    path_markdown = module_runtime_support.find_disclosure_draft(path_case_dir, path_input)  # 当前案件正文草稿路径

    # 在找不到可用正文草稿时立即报错，避免生成与案件脱节的附图。
    if path_markdown is None or not path_markdown.exists():

        # 抛出明确错误，提醒调用方先完成 disclosure draft 阶段。
        raise FileNotFoundError("> ERR: [Python] 缺少 disclosure draft markdown。")

    # 读取正文草稿全文，供步骤和模块提取逻辑复用。
    str_markdown = path_markdown.read_text(encoding="utf-8")  # 正文草稿 Markdown 全文

    # 提取结构化方法步骤，供方法流程图生成逻辑复用。
    list_steps = extract_method_steps(str_markdown, module_runtime_support)  # 结构化方法步骤列表

    # 提取结构化系统模块，供系统模块图生成逻辑复用。
    list_modules = extract_system_modules(str_markdown, module_runtime_support)  # 结构化系统模块列表

    # 确保附图输出目录存在，后续 SVG、Mermaid 与 manifest 都会落在这里。
    path_output_dir = module_runtime_support.ensure_dir(path_case_dir / "05_figures")  # 附图输出目录

    # 固定方法流程图 SVG 输出路径，保持附图目录命名稳定。
    path_flow_svg = path_output_dir / "图1_方法流程图.svg"  # 方法流程图 SVG 输出路径

    # 固定系统模块图 SVG 输出路径，保持附图目录命名稳定。
    path_module_svg = path_output_dir / "图2_系统模块图.svg"  # 系统模块图 SVG 输出路径

    # 渲染并写出方法流程图 SVG 文本。
    module_runtime_support.write_text_file(path_flow_svg, render_flow_svg(list_steps))

    # 渲染并写出系统模块图 SVG 文本。
    module_runtime_support.write_text_file(path_module_svg, render_module_svg(list_modules))

    # 写出两份 Mermaid 源文件，便于后续增强渲染。
    write_mermaid_files(path_output_dir, list_steps, list_modules, module_runtime_support)

    # 为 manifest 组装调用准备共享支持别名，缩短调用行并保持上下文清晰。
    module_support = module_runtime_support  # build_manifest 调用使用的共享支持模块别名

    # 生成 figures manifest 结构化数据，供 JSON 落盘与后链工具复用。
    dict_manifest = build_manifest(  # figures manifest 结构化结果
        path_markdown,  # 正文草稿路径
        path_flow_svg,  # 方法流程图 SVG 路径
        path_module_svg,  # 系统模块图 SVG 路径
        list_steps,  # 供图1 写入步骤索引的结构化方法步骤列表
        list_modules,  # 供图2 写入模块索引的结构化系统模块列表
        module_support,  # 共享支持模块对象
    )

    # 固定 figures manifest JSON 输出路径，保持后链读取约定稳定。
    path_manifest_json = path_output_dir / "figures_manifest.json"  # figures manifest JSON 输出路径

    # 把 figures manifest JSON 写入案件目录。
    module_runtime_support.write_json_file(path_manifest_json, dict_manifest)

    # 渲染供人工快速审阅的 Markdown 摘要文本。
    str_manifest_markdown = render_manifest_markdown(path_markdown)  # figures manifest Markdown 摘要文本

    # 固定供人工审阅的 Markdown 摘要输出路径，避免与 JSON manifest 混淆。
    path_manifest_markdown = path_output_dir / "figures_manifest.md"  # 附图摘要 Markdown 输出路径

    # 把面向人工的附图摘要 Markdown 写入案件目录。
    module_runtime_support.write_text_file(path_manifest_markdown, str_manifest_markdown)

    # 把 manifest JSON 绝对路径作为机器可读输出写回上游流程。
    sys.stdout.write(str(path_manifest_json.resolve()) + "\n")

    # 返回成功状态码，表示附图相关产物都已完成落盘。
    return 0

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())
