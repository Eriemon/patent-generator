#!/usr/bin/env python3
"""渲染附图 SVG、PNG 与 Mermaid 资产。"""

# 延迟解析类型注解，保持独立文件规格加载兼容。
from __future__ import annotations

# 标准库提供环境、文本包装、路径与通用类型能力。
import os
import textwrap
from html import escape
from pathlib import Path
from typing import Any

# 复用资产模块中的样式对象与 Mermaid 写盘 helper。
from readable_patent_figure_assets import (
    build_arrowprops,
    build_rounded_box_patch,
    write_mermaid_files,
)

# 复用已登记布局模块中的几何常量和 helper。
from readable_patent_figure_layout import (
    FIGURE_ARROW_COLOR,
    FIGURE_ARROW_LINEWIDTH,
    FIGURE_ARROW_STYLE,
    FIGURE_BOX_EDGE_COLOR,
    FIGURE_BOX_FACE_COLOR,
    FIGURE_BOX_LINEWIDTH,

    # 附图全局样式和输出精度控制 SVG 与 PNG 的一致视觉层级。
    FIGURE_BOX_STYLE,
    FIGURE_PLOT_DPI,
    FIGURE_TITLE_FONT_SIZE,
    FIGURE_TITLE_TOP_MARGIN,
    FLOW_ARROW_CENTER_X,

    # 流程图箭头与框体几何常量共同限定节点连接位置。
    FLOW_ARROW_EDGE_PADDING,
    FLOW_ARROW_OFFSET_Y,
    FLOW_BOX_HALF_HEIGHT,
    FLOW_BOX_HEIGHT,
    FLOW_BOX_LEFT,

    # 流程图画布和步骤间距决定纵向布局的可读范围。
    FLOW_BOX_WIDTH,
    FLOW_CANVAS_BASE_HEIGHT,
    FLOW_CANVAS_WIDTH,
    FLOW_FIRST_STEP_OFFSET,
    FLOW_SVG_BOX_GAP,

    # 流程图文字常量限制摘要换行、行距和最大显示行数。
    FLOW_SVG_BOX_HEIGHT,
    FLOW_TEXT_FONT_SIZE,
    FLOW_TEXT_LINE_SPACING,
    FLOW_TEXT_MAX_LINES,
    FLOW_TEXT_WRAP_WIDTH,

    # 流程图坐标范围保证标题、框体和箭头共用同一坐标系。
    FLOW_TITLE_CENTER_X,
    FLOW_X_AXIS_LIMIT,
    FLOW_Y_AXIS_SCALE,
    MODULE_BOX_WIDTH,
    MODULE_CANVAS_BASE_HEIGHT,

    # 模块图列数和水平位置常量控制单双列布局切换。
    MODULE_CANVAS_WIDTH,
    MODULE_DOUBLE_COLUMN,
    MODULE_DOUBLE_COLUMN_LEFT,
    MODULE_DOUBLE_COLUMN_THRESHOLD,
    MODULE_FUNCTION_MAX_LINES,

    # 模块功能文本和框间距约束双列场景下的排版密度。
    MODULE_FUNCTION_WRAP_WIDTH,
    MODULE_GAP_X,
    MODULE_GAP_Y,
    MODULE_NAME_MAX_LINES,
    MODULE_NAME_WRAP_WIDTH,

    # Matplotlib 模块图画布常量提供行高与整体尺寸基准。
    MODULE_PLOT_BASE_HEIGHT,
    MODULE_PLOT_CANVAS_WIDTH,
    MODULE_PLOT_ROW_HEIGHT,
    MODULE_SINGLE_COLUMN,
    MODULE_SINGLE_COLUMN_LEFT,

    # 模块图标题与框体坐标固定 SVG 和 PNG 的视觉对应关系。
    MODULE_SVG_BOX_HEIGHT,
    MODULE_TITLE_CENTER_X,
    MODULE_TITLE_FONT_SIZE,
    MODULE_TITLE_Y,
    MODULE_TOP_MARGIN,

    # 模块图坐标缩放和 Pillow 箭头参数覆盖无 matplotlib 回退路径。
    MODULE_X_AXIS_LIMIT,
    MODULE_Y_AXIS_SCALE,
    PILLOW_ARROW_BASE_OFFSET,
    PILLOW_ARROW_HALF_WIDTH,
    PILLOW_ARROW_MARGIN,

    # Pillow 箭头尖端和正文尺寸常量保证低依赖环境输出清晰。
    PILLOW_ARROW_TIP_LENGTH,
    PILLOW_BODY_FONT_SIZE,
    PILLOW_BOTTOM_MARGIN,
    PILLOW_BOX_GAP,
    PILLOW_BOX_HEIGHT,

    # Pillow 框体、画布与水平边距构成回退图的基础几何。
    PILLOW_BOX_RADIUS,
    PILLOW_CANVAS_WIDTH,
    PILLOW_HORIZONTAL_MARGIN,
    PILLOW_LINE_WIDTH,
    PILLOW_TEXT_SPACING,

    # Pillow 图题参数和 SVG 字体栈保持中文文本可读。
    PILLOW_TITLE_CENTER_Y,
    PILLOW_TITLE_FONT_SIZE,
    PILLOW_TITLE_HEIGHT,
    SVG_FONT_FAMILY_STACK,
    build_png_cjk_font_properties,

    # 布局 helper 复用框体坐标与模块连线计算，避免渲染器重复实现。
    build_svg_box_position_record,
    draw_module_png_boxes,
    draw_module_png_connections,
    draw_pillow_vertical_arrow,
    find_preferred_cjk_font_path,
    resolve_module_grid_position,
    wrap_figure_text,
)

# SVG 流程图画布和标题坐标保持独立导出尺寸稳定。
FLOW_SVG_CANVAS_WIDTH = 760  # SVG 流程图画布宽度

# 基础高度覆盖图题和首个步骤框顶部留白。
FLOW_SVG_BASE_HEIGHT = 96  # SVG 流程图基础高度

# 标题中心与步骤框中心共用同一纵向轴线。
FLOW_SVG_TITLE_CENTER_X = 380  # SVG 流程图标题中心横坐标

# 标题纵坐标固定在画布顶部留白区域。
FLOW_SVG_TITLE_Y = 32  # SVG 流程图标题纵坐标

# 标题字号与模块 SVG 标题保持清晰层级。
FLOW_SVG_TITLE_FONT_SIZE = 18  # SVG 流程图标题字号

# SVG 步骤框几何和箭头缩放参数控制节点落位。
FLOW_SVG_BOX_X = 120  # SVG 步骤框左边界

# 步骤框宽度为中文摘要保留稳定换行空间。
FLOW_SVG_BOX_WIDTH = 520  # SVG 步骤框宽度

# 首框纵坐标位于图题区域下方。
FLOW_SVG_FIRST_BOX_Y = 60  # 首个 SVG 步骤框纵坐标

# 箭头留白沿用布局模块的单位并换算到 SVG 像素。
FLOW_SVG_ARROW_PADDING_SCALE = 10  # SVG 箭头边缘留白缩放倍数

# 模块连接线与框边缘错开少量像素，避免视觉粘连。
SVG_CONNECTOR_EDGE_GAP = 2  # SVG 连接线与框边缘的留白

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

    # 先按换行拆出主标题文本行，便于流程图和模块图共享多行框体渲染。
    list_label_lines = [str_line.strip() for str_line in str_label.splitlines() if str_line.strip()]  # 主标题文本行列表

    # 再按换行拆出副标题文本行，供功能说明多行渲染复用。
    list_subtitle_lines = [str_line.strip() for str_line in str_subtitle.splitlines() if str_line.strip()]  # 副标题文本行列表

    # 先准备当前矩形框的基础 SVG 片段，保证多行文本逻辑不会影响边框输出。
    list_parts = [
        f'<rect x="{int_x}" y="{int_y}" width="{int_width}" height="{int_height}" '
        'rx="10" ry="10" fill="white" stroke="black" stroke-width="1.5"/>'
    ]  # 当前矩形框 SVG 片段列表

    # 依次登记主标题和副标题的字体规格，便于后续统一做纵向居中排版。
    # 先为主标题生成字号规格列表，保持标题和说明的字号来源清晰分离。
    list_label_specs = [(str_line, 15) for str_line in list_label_lines]  # 主标题文本行规格列表

    # 再为副标题生成字号规格列表，保证说明文字统一使用较小字号。
    list_subtitle_specs = [(str_line, 12) for str_line in list_subtitle_lines]  # 副标题文本行规格列表

    # 最后再合并两组文本规格，供后续统一做盒内纵向居中排版。
    list_line_specs = [*list_label_specs, *list_subtitle_specs]  # 盒内文本行规格列表

    # 在当前框体没有可见文本时直接返回边框片段，避免后续居中计算出现空列表。
    if not list_line_specs:

        # 返回仅包含边框的 SVG 片段，保持调用方行为稳定。
        return "".join(list_parts)

    # 固定 SVG 文本行间距，保证多行标题与说明均匀分布在框体中部。
    int_line_gap = 18  # SVG 框体文本行间距

    # 先计算第一行中心线的纵坐标，保证多行文本整体相对框体纵向居中。
    float_start_y = int_y + int_height / 2 - ((len(list_line_specs) - 1) * int_line_gap) / 2  # 第一行文本中心纵坐标

    # 逐行写入当前矩形框文本，让多行标题和说明真正进入框体内部。
    for int_index, tuple_line_spec in enumerate(list_line_specs):

        # 解包当前文本内容和字号，供 SVG 文本节点直接复用。
        str_line, int_font_size = tuple_line_spec  # 当前文本行内容和字号

        # 计算当前文本行的纵坐标，保证行间距与整体居中关系稳定。
        float_line_y = float_start_y + int_index * int_line_gap  # 当前文本行中心纵坐标

        # 追加当前 SVG 文本节点，统一声明中文友好的字体族栈。
        list_parts.append(
            f'<text x="{int_x + int_width / 2}" y="{float_line_y}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="{int_font_size}" '
            f'font-family="{SVG_FONT_FAMILY_STACK}">{escape(str_line)}</text>'
        )

    # 返回完整矩形框 SVG 片段，包含边框和所有文本行。
    return "".join(list_parts)

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
    int_width = FLOW_SVG_CANVAS_WIDTH  # 方法流程图画布宽度

    # 固定流程图矩形框横坐标，保证各步骤节点居中对齐。
    int_box_x = FLOW_SVG_BOX_X  # 方法步骤框横坐标

    # 固定流程图矩形框宽度，保证标题和摘要有稳定容纳空间。
    int_box_width = FLOW_SVG_BOX_WIDTH  # 方法步骤框宽度

    # 固定流程图矩形框高度，保证三行中文摘要也能真正进入框内。
    int_box_height = FLOW_SVG_BOX_HEIGHT  # 方法步骤框高度

    # 根据步骤数量计算画布高度，给更高的多行步骤框和箭头预留空间。
    int_height = FLOW_SVG_BASE_HEIGHT + len(list_steps) * (int_box_height + FLOW_SVG_BOX_GAP)  # 方法流程图画布高度

    # 先准备 SVG 文本片段列表，后续逐项追加标题、节点与箭头。
    list_parts = [  # 方法流程图 SVG 片段列表
        render_svg_header(int_width, int_height),  # 通用 SVG 头部
        (
            f'<text x="{FLOW_SVG_TITLE_CENTER_X}" y="{FLOW_SVG_TITLE_Y}" '
            f'text-anchor="middle" font-size="{FLOW_SVG_TITLE_FONT_SIZE}" '
            f'font-family="{SVG_FONT_FAMILY_STACK}">图 1 方法流程图</text>'
        ),  # 图题文本
    ]

    # 记录上一节点底部纵坐标，供后续箭头连接使用。
    int_previous_bottom = 0  # 上一节点底部纵坐标

    # 按方法步骤顺序逐项渲染节点和连接箭头。
    for int_index, dict_step in enumerate(list_steps):

        # 计算当前步骤框纵坐标，保持更高的多行步骤框之间仍有稳定留白。
        int_box_y = FLOW_SVG_FIRST_BOX_Y + int_index * (int_box_height + FLOW_SVG_BOX_GAP)  # 当前步骤框纵坐标

        # 先整理当前步骤编号和摘要的拼接文本，供 SVG 换行 helper 按盒内宽度复用。
        str_step_source_text = f"{dict_step['id']}：{dict_step['summary']}"  # 当前步骤框待换行原文

        # 再包装当前步骤摘要，确保中文长句会真正落在 SVG 框体内部。
        list_step_label_lines = wrap_figure_text(str_step_source_text, FLOW_TEXT_WRAP_WIDTH, FLOW_TEXT_MAX_LINES)  # 当前步骤框主标题文本行列表

        # 把已经换行的步骤文本拼成单段多行字符串，供 SVG 框体直接写入主标题区域。
        str_step_label = "\n".join(list_step_label_lines)  # 当前步骤框的多行 SVG 标题段落

        # 渲染当前步骤框并追加到 SVG 片段列表。
        list_parts.append(
            render_svg_box(
                int_box_x,
                int_box_y,
                int_box_width,
                int_box_height,
                str_step_label,
                "",
            )
        )

        # 从第二个节点开始补充箭头，串起完整的步骤顺序关系。
        if int_index > 0:

            # 渲染上一节点到当前节点的竖向箭头。
            list_parts.append(
                render_svg_arrow(
                    FLOW_SVG_TITLE_CENTER_X,
                    int_previous_bottom + FLOW_ARROW_EDGE_PADDING * FLOW_SVG_ARROW_PADDING_SCALE,
                    FLOW_SVG_TITLE_CENTER_X,
                    int_box_y - FLOW_ARROW_EDGE_PADDING * FLOW_SVG_ARROW_PADDING_SCALE,
                )
            )

        # 把当前步骤框底部坐标保存下来，下一轮箭头会从这里继续向下连接。
        int_previous_bottom = int_box_y + int_box_height  # 下一轮箭头起点的纵坐标

    # 追加 SVG 结束标签，形成完整方法流程图文本。
    list_parts.append("</svg>")

    # 返回完整方法流程图 SVG 文本，供案件目录落盘。
    return "\n".join(list_parts)

# 渲染两个相邻 SVG 模块框之间的边缘锚点箭头。
def render_module_svg_connector(
    dict_current_box: dict[str, int],
    dict_next_box: dict[str, int],
) -> str:
    """按同行或跨行关系渲染模块连接箭头。

    参数：
    - `dict_current_box`：当前模块框边界坐标。
    - `dict_next_box`：下一模块框边界坐标。

    返回：
    - `str`：连接两个模块框的 SVG 箭头片段。
    """

    # 同行模块沿蛇形阅读方向连接左右边缘。
    if dict_current_box["top"] == dict_next_box["top"]:

        # 左到右场景从当前右边缘接入下一模块左边缘。
        if dict_current_box["center_x"] < dict_next_box["center_x"]:

            # 返回避开两个框体内部的水平箭头。
            return render_svg_arrow(
                dict_current_box["right"] + SVG_CONNECTOR_EDGE_GAP,
                dict_current_box["center_y"],
                dict_next_box["left"] - SVG_CONNECTOR_EDGE_GAP,
                dict_next_box["center_y"],
            )

        # 右到左场景从当前左边缘接入下一模块右边缘。
        return render_svg_arrow(
            dict_current_box["left"] - SVG_CONNECTOR_EDGE_GAP,
            dict_current_box["center_y"],
            dict_next_box["right"] + SVG_CONNECTOR_EDGE_GAP,
            dict_next_box["center_y"],
        )

    # 跨行模块沿各自中心线连接上下边缘。
    return render_svg_arrow(
        dict_current_box["center_x"],
        dict_current_box["bottom"] + SVG_CONNECTOR_EDGE_GAP,
        dict_next_box["center_x"],
        dict_next_box["top"] - SVG_CONNECTOR_EDGE_GAP,
    )

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

    # 在模块多于两个时切到双列布局，减少整张模块图的纵向长度。
    int_columns = MODULE_DOUBLE_COLUMN if len(list_modules) > MODULE_DOUBLE_COLUMN_THRESHOLD else MODULE_SINGLE_COLUMN  # 模块图列数

    # 根据模块数量和列数推算实际行数，供画布高度估算复用。
    int_rows = (len(list_modules) + int_columns - MODULE_SINGLE_COLUMN) // int_columns  # 模块图总行数

    # 依据行数生成模块图 SVG 高度，保证高框体和跨行箭头都能落在画布内。
    int_height = MODULE_CANVAS_BASE_HEIGHT + int_rows * (MODULE_SVG_BOX_HEIGHT + MODULE_GAP_Y)  # 系统模块图画布高度

    # 先准备系统模块图的 SVG 片段列表，后续逐项追加图题、模块框和箭头。
    list_parts = [  # 系统模块图 SVG 片段列表
        render_svg_header(MODULE_CANVAS_WIDTH, int_height),  # 注入模块图专用 SVG 头部与背景
        (
            f'<text x="{MODULE_TITLE_CENTER_X}" y="{MODULE_TITLE_Y}" '
            'text-anchor="middle" '
            f'font-size="{MODULE_TITLE_FONT_SIZE}" '
            f'font-family="{SVG_FONT_FAMILY_STACK}">'
            "图 2 系统模块图</text>"
        ),  # 模块图标题文本
    ]

    # 记录各模块框边界坐标，供后续箭头连接逻辑复用。
    list_box_positions: list[dict[str, int]] = []  # 模块框边界坐标列表

    # 按模块顺序逐项渲染模块框并记录其坐标。
    for int_index, dict_module in enumerate(list_modules):

        # 先保存当前模块在蛇形路径中的成对坐标结果，避免 SVG 布局阶段重复调用解析 helper。
        tuple_grid_position = resolve_module_grid_position(int_index, int_columns)  # 当前模块在 SVG 中的蛇形坐标二元组

        # 先拆出蛇形坐标的纵向槽位，后续只用它推导当前模块落在哪一行。
        int_row = tuple_grid_position[0]  # 当前模块的 SVG 行索引

        # 再拆出蛇形坐标的横向槽位，后续据此决定当前模块落在左列还是右列。
        int_column = tuple_grid_position[1]  # 当前模块的 SVG 列索引

        # 根据布局模式计算当前模块框横坐标。
        if int_columns == MODULE_DOUBLE_COLUMN:

            # 在双列布局下按照列号和水平间距推导横坐标。
            int_x = MODULE_DOUBLE_COLUMN_LEFT + int_column * (MODULE_BOX_WIDTH + MODULE_GAP_X)  # 双列布局下的模块框横坐标

        # 在单列布局下直接使用居中左边距，保证整张图保持稳定居中。
        else:

            # 固定单列布局时的横坐标，让所有模块框保持居中对齐。
            int_x = MODULE_SINGLE_COLUMN_LEFT  # 单列布局模块框的居中横坐标

        # 根据行号计算当前模块框纵坐标。
        int_y = MODULE_TOP_MARGIN + int_row * (MODULE_SVG_BOX_HEIGHT + MODULE_GAP_Y)  # 当前模块框纵坐标

        # 先包装模块标题，避免名称在双列 SVG 模块图中横向外溢。
        list_module_name_lines = wrap_figure_text(dict_module["name"], MODULE_NAME_WRAP_WIDTH, MODULE_NAME_MAX_LINES)  # 当前模块框标题文本行列表

        # 再把标题文本行拼成多行段落，供当前模块框直接复用。
        str_module_name = "\n".join(list_module_name_lines)  # 当前模块框标题文本

        # 先提取当前模块功能说明原文，便于后续受控换行调用保持短行可读。
        str_module_function_source = dict_module["function"]  # 当前模块功能说明原文

        # 先收拢 SVG 说明文本的每行宽度约束，避免后续包装调用行超出长度门限。
        int_wrap_chars = MODULE_FUNCTION_WRAP_WIDTH  # SVG 说明每行字符上限

        # 再收拢 SVG 说明文本的最大行数，保证副标题区域不会把模块框继续撑高。
        int_line_limit = MODULE_FUNCTION_MAX_LINES  # SVG 说明允许的最大行数

        # 再包装功能说明文本，让双列 SVG 框体里的副标题也能稳定落框。
        list_module_function_lines = wrap_figure_text(str_module_function_source, int_wrap_chars, int_line_limit)  # 说明行列表

        # 把功能说明文本行合并成单段副标题字符串，供模块框作为说明区正文直接渲染。
        str_module_function = "\n".join(list_module_function_lines)  # 当前模块框功能说明文本

        # 先构造当前 SVG 模块框的边界记录，供后续边缘锚点箭头复用。
        dict_box_position = build_svg_box_position_record(int_x, int_y, MODULE_BOX_WIDTH, MODULE_SVG_BOX_HEIGHT)  # 当前模块框边界坐标记录

        # 把当前 SVG 模块框边界记录登记到列表，供后续相邻模块连线复用。
        list_box_positions.append(dict_box_position)

        # 直接把当前模块框 SVG 片段压入结果列表，避免额外临时变量只做一次转手。
        list_parts.append(
            render_svg_box(
                int_x,
                int_y,
                MODULE_BOX_WIDTH,
                MODULE_SVG_BOX_HEIGHT,
                # 最后两项传入已经换好的标题与说明文本，让 SVG 框体直接完成正文渲染。
                str_module_name,
                str_module_function,
            )
        )

    # 按模块顺序补充相邻模块之间的连接箭头。
    for int_index in range(len(list_box_positions) - 1):

        # 读取待发起连线的当前模块框边界，后续会据此决定水平还是竖向锚点。
        dict_current_box = list_box_positions[int_index]  # 当前模块框边界坐标

        # 读取即将接入的下一模块框边界，供边缘锚点连接做终点选择。
        dict_next_box = list_box_positions[int_index + 1]  # 下一模块框边界坐标

        # 按同行或跨行关系追加边缘锚点箭头。
        list_parts.append(render_module_svg_connector(dict_current_box, dict_next_box))

    # 补上模块图 SVG 结束标签，封口当前矢量图文档。
    list_parts.append("</svg>")

    # 返回完整模块图 SVG 文本，供后续写盘和 DOCX 嵌图流程复用。
    return "\n".join(list_parts)

# 运行时加载可选 matplotlib 后端，使轻量环境能安全进入 Pillow 回退路径。
def load_matplotlib_backend() -> tuple[Any, Any] | None:
    """加载 PNG 矢量绘图后端；轻量运行时缺失时返回空值。

    参数：
    - 无。

    返回：
    - `tuple[Any, Any] | None`：可用时返回 pyplot 与圆角框类型，否则返回 `None`。

    异常：
    - 无；缺失可选绘图库时由 Pillow 回退路径继续生成。
    """

    # 尝试导入绘图后端，避免在模块加载阶段强制依赖 matplotlib。
    try:

        # pyplot 负责画布，圆角框类型负责流程框和模块框。
        from matplotlib import pyplot as plt
        from matplotlib.patches import FancyBboxPatch as class_fancy_bbox_patch

    # 轻量运行时缺少 matplotlib 时由 Pillow 继续生成 PNG。
    except ModuleNotFoundError:

        # 空值明确表示调用方必须选择无 matplotlib 的回退实现。
        return None

    # 返回两个后端对象，保持流程图和模块图使用同一加载结果。
    return plt, class_fancy_bbox_patch

# 为 Pillow 回退图选择能够显示中文的字体。
def build_pillow_cjk_font(class_image_font: Any, int_font_size: int) -> Any:
    """构造 Pillow 回退路径使用的中文字体对象。

    参数：
    - `class_image_font`：Pillow 字体模块对象，不承载数组，shape、dtype 与 unit 均不适用。
    - `int_font_size`：目标字号，标量整数，shape=()，dtype=int，unit=像素。

    返回：
    - `Any`：Pillow 字体对象，不承载数值数组，shape、dtype 与 unit 均不适用。

    异常：
    - 无；字体文件不可用时保留可生成 PNG 的默认字体回退。

    数值风险：
    - 字号会取整数像素值，不执行插值或数值计算；不同字体度量可能改变换行位置，但不改变图示语义。
    """

    # 查询当前平台优先中文字体，避免图中文字变成空方框。
    path_font = find_preferred_cjk_font_path()  # Pillow 回退图使用的中文字体路径

    # 找到字体文件时优先按目标字号加载。
    if path_font is not None:

        # 字体文件可能存在但 Pillow 无法解析，因此保留安全回退。
        try:

            # 返回指定字号的中文字体对象。
            return class_image_font.truetype(str(path_font), int_font_size)

        # 字体解析失败不阻断整份交底书的附图生成。
        except OSError:

            # 交由下方默认字体路径继续处理。
            pass

    # 极端环境没有可用中文字体时仍生成结构完整的 PNG。
    return class_image_font.load_default()

# 使用 Pillow 生成纵向黑白框图，作为 matplotlib 缺失时的确定性回退。
def write_pillow_diagram(
    path_output_png: Path,
    str_title: str,
    list_text_blocks: list[str],
) -> None:
    """在缺少 matplotlib 时使用 Pillow 写出可交付的黑白结构图。

    参数：
    - `path_output_png`：PNG 输出路径。
    - `str_title`：图标题。
    - `list_text_blocks`：按阅读顺序排列的图框正文列表。

    返回：
    - `None`。

    异常：
    - Pillow 不可用或图片写入失败时由底层异常上抛。
    """

    # 延迟导入 Pillow，正常 matplotlib 环境不需要加载该依赖。
    from PIL import Image, ImageDraw, ImageFont

    # 回退画布保持足够宽度，使中文摘要无需缩小字号。
    int_canvas_width = PILLOW_CANVAS_WIDTH  # Pillow 回退图画布宽度（像素）

    # 左右留白避免圆角框贴近图片边缘。
    int_horizontal_margin = PILLOW_HORIZONTAL_MARGIN  # 回退图水平页边距（像素）

    # 读取图题区高度，后续所有框体都从该纵坐标以下开始排列。
    int_title_height = PILLOW_TITLE_HEIGHT  # 当前画布的图题占用高度

    # 读取统一框高，使方法步骤和系统模块拥有相同的垂直节奏。
    int_box_height = PILLOW_BOX_HEIGHT  # 当前回退图采用的内容框高度

    # 框间距容纳竖向连线和箭头尖端。
    int_box_gap = PILLOW_BOX_GAP  # 相邻内容框间距（像素）

    # 底部留白与框间距一致，避免末框压住画布边界。
    int_bottom_margin = PILLOW_BOTTOM_MARGIN  # 回退图底部留白（像素）

    # 按正文块数量计算画布高度，避免固定高度裁切后续步骤。
    int_canvas_height = (  # Pillow 回退图画布高度（像素）
        int_title_height  # 图题区域高度
        + len(list_text_blocks) * (int_box_height + int_box_gap)  # 全部框体及框间连接区域
        + int_bottom_margin  # 末框后的底部留白
    )

    # 创建白底 RGB 图像，确保 Word 和 PDF 渲染结果一致。
    obj_image = Image.new("RGB", (int_canvas_width, int_canvas_height), "white")  # 白底回退图对象

    # 为图像创建绘图上下文，后续文字、框线和箭头共享该对象。
    obj_draw = ImageDraw.Draw(obj_image)  # Pillow 绘图上下文

    # 图题使用较大中文字体，和正文框形成视觉层级。
    obj_title_font = build_pillow_cjk_font(ImageFont, PILLOW_TITLE_FONT_SIZE)  # 回退图标题字体

    # 正文使用稍小字号，兼顾多行内容与可读性。
    obj_body_font = build_pillow_cjk_font(ImageFont, PILLOW_BODY_FONT_SIZE)  # 回退图正文框字体

    # 内容框左边界由统一水平留白确定。
    int_box_left = int_horizontal_margin  # 内容框左边界（像素）

    # 内容框右边界与左边界保持对称。
    int_box_right = int_canvas_width - int_horizontal_margin  # 内容框右边界（像素）

    # 所有框体和箭头共用画布中心线。
    int_center_x = int_canvas_width // 2  # 内容框中心横坐标（像素）

    # 在首个框体上方写入图号和图名。
    obj_draw.text((int_center_x, PILLOW_TITLE_CENTER_Y), str_title, fill="black", font=obj_title_font, anchor="mm")

    # 按阅读顺序逐个绘制正文框及其下方连接箭头。
    for int_index, str_text_block in enumerate(list_text_blocks):

        # 根据序号计算当前框体顶部位置。
        int_box_top = int_title_height + int_index * (int_box_height + int_box_gap)  # 当前框体上边界（像素）

        # 框体底部由固定高度推导，保证所有步骤视觉一致。
        int_box_bottom = int_box_top + int_box_height  # 当前框体下边界（像素）

        # 正文锚点位于框体几何中心。
        int_center_y = (int_box_top + int_box_bottom) // 2  # 当前框体中心纵坐标（像素）

        # 绘制黑白圆角框，避免使用填充色影响专利附图打印。
        obj_draw.rounded_rectangle(
            (int_box_left, int_box_top, int_box_right, int_box_bottom),
            radius=PILLOW_BOX_RADIUS,
            outline="black",
            width=PILLOW_LINE_WIDTH,
        )

        # 把已经换行的技术摘要写入框体中心。
        obj_draw.multiline_text(
            (int_center_x, int_center_y),
            str_text_block,
            fill="black",
            font=obj_body_font,
            anchor="mm",
            align="center",
            spacing=PILLOW_TEXT_SPACING,
        )

        # 最后一个框体不需要向下连接箭头。
        if int_index < len(list_text_blocks) - 1:

            # 绘制当前框到下一框的纵向连接箭头。
            draw_pillow_vertical_arrow(obj_draw, int_center_x, int_box_bottom, int_box_gap)

    # 确保目标目录存在，允许独立调用该回退渲染函数。
    path_output_png.parent.mkdir(parents=True, exist_ok=True)

    # 以显式 PNG 格式写盘，供 DOCX 嵌图和独立附图包复用。
    obj_image.save(path_output_png, format="PNG")

# 构造 Pillow 流程图使用的多行步骤框正文。
def build_flow_pillow_text_blocks(list_steps: list[dict[str, str]]) -> list[str]:
    """按方法步骤顺序构造 Pillow 回退框正文。

    参数：
    - `list_steps`：结构化方法步骤列表。

    返回：
    - `list[str]`：已经受控换行的步骤框正文。
    """

    # 保持正式步骤顺序，并复用 SVG 相同的换行宽度与行数上限。
    return [
        "\n".join(
            wrap_figure_text(
                f"{dict_step['id']}：{dict_step['summary']}",  # 当前步骤编号和摘要
                FLOW_TEXT_WRAP_WIDTH,  # 步骤框换行宽度
                FLOW_TEXT_MAX_LINES,  # 步骤框最大文本行数
            )
        )
        for dict_step in list_steps  # 保持方法步骤原始顺序
    ]

# 把方法步骤写成 PNG 交付图，供 DOCX 导出阶段直接嵌入正文。
def write_flow_png(path_output_png: Path, list_steps: list[dict[str, str]]) -> None:
    """把方法流程图写成 PNG 文件。

    参数：
    - `path_output_png`：方法流程图 PNG 输出路径。
    - `list_steps`：结构化方法步骤列表。

    返回：
    - `None`。

    异常：
    - 图片写入失败时由底层异常上抛。
    """

    # 优先加载 matplotlib 绘图后端；缺失时使用既有 Pillow 能力生成可交付 PNG。
    tuple_matplotlib_backend = load_matplotlib_backend()  # matplotlib 后端或空值

    # 可选后端不可用时改用确定性的纵向 Pillow 框图。
    if tuple_matplotlib_backend is None:

        # 把每个方法步骤整理成已经换行的单框正文。
        list_text_blocks = build_flow_pillow_text_blocks(list_steps)  # Pillow 回退流程图框正文

        # 写出可供 Word 直接嵌入的流程图 PNG。
        write_pillow_diagram(path_output_png, "图 1 方法流程图", list_text_blocks)

        # Pillow 已完成当前输出，避免继续进入 matplotlib 分支。
        return

    # 解包可用后端，类型名称使用 snake_case 别名满足当前项目命名约束。
    obj_pyplot, class_fancy_bbox_patch = tuple_matplotlib_backend  # matplotlib 流程图绘图对象

    # 根据步骤数量确定画布高度，给三行中文摘要和箭头都留出更稳定的空间。
    float_height = FLOW_CANVAS_BASE_HEIGHT + len(list_steps) * 1.7  # 方法流程图画布高度（英寸）

    # 创建白底画布，供方法步骤框和箭头稳定排版。
    obj_figure, obj_axes = obj_pyplot.subplots(figsize=(FLOW_CANVAS_WIDTH, float_height), dpi=FIGURE_PLOT_DPI)  # 方法流程图画布和坐标轴

    # 解析当前 PNG 绘图要复用的中文字体属性，避免默认字体把步骤正文渲染成缺字方块。
    obj_font_properties = build_png_cjk_font_properties()  # 方法流程图文本字体属性

    # 固定流程图箭头样式参数，避免每次 annotate 都重复拼接同一套黑白样式。
    dict_arrowprops = build_arrowprops()  # 流程图箭头样式参数

    # 关闭坐标轴显示，避免 PNG 图内混入无关刻度和边框。
    obj_axes.axis("off")

    # 固定流程图的横向范围，供步骤框和箭头坐标稳定复用。
    obj_axes.set_xlim(0.0, FLOW_X_AXIS_LIMIT)

    # 固定纵向范围，保证步骤框按上到下顺序均匀排布。
    obj_axes.set_ylim(0.0, float_height * FLOW_Y_AXIS_SCALE)

    # 在画布顶部写入图题，保证导出 PNG 单独查看时也能识别图号与类型。
    obj_axes.text(
        FLOW_TITLE_CENTER_X,
        float_height * FLOW_Y_AXIS_SCALE - FIGURE_TITLE_TOP_MARGIN,
        "图 1 方法流程图",
        ha="center",
        va="center",
        fontsize=FIGURE_TITLE_FONT_SIZE,
        fontweight="bold",
        fontproperties=obj_font_properties,
    )

    # 记录上一节点的纵坐标，供后续步骤框之间追加箭头连接。
    float_previous_y = 0.0  # 上一节点纵坐标

    # 按步骤顺序从上到下绘制方法步骤框和连接箭头。
    for int_index, dict_step in enumerate(list_steps):

        # 为当前步骤计算纵坐标，使更高的多行步骤框仍按稳定节奏自上而下排布。
        float_center_y = float_height * FLOW_Y_AXIS_SCALE - FLOW_FIRST_STEP_OFFSET - int_index * 2.7  # 当前步骤框垂直中心

        # 先构造当前步骤框起点坐标，供统一样式的圆角框对象复用。
        tuple_box_origin = (FLOW_BOX_LEFT, float_center_y - FLOW_BOX_HALF_HEIGHT)  # 当前步骤框左下角坐标

        # 准备当前步骤框对象，沿用统一的圆角框样式保持专利附图风格一致。
        obj_box = build_rounded_box_patch(class_fancy_bbox_patch, tuple_box_origin, FLOW_BOX_WIDTH, FLOW_BOX_HEIGHT)  # 当前步骤框图形对象

        # 把当前步骤框追加到画布，形成正式 PNG 图形主体。
        obj_axes.add_patch(obj_box)

        # 在步骤框中央写入步骤编号和摘要，保持与 SVG 版本语义一致。
        obj_axes.text(
            FLOW_TITLE_CENTER_X,
            float_center_y,
            "\n".join(
                wrap_figure_text(
                    f"{dict_step['id']}：{dict_step['summary']}",
                    FLOW_TEXT_WRAP_WIDTH,
                    FLOW_TEXT_MAX_LINES,
                )
            ),
            ha="center",
            va="center",
            fontsize=FLOW_TEXT_FONT_SIZE,
            fontproperties=obj_font_properties,
            linespacing=FLOW_TEXT_LINE_SPACING,
        )

        # 从第二步开始为相邻步骤框补画箭头，形成完整流程链路。
        if int_index > 0:

            # 把上一节点和当前节点之间补上竖向箭头，强调步骤先后次序。
            obj_axes.annotate(
                "",
                xy=(FLOW_ARROW_CENTER_X, float_center_y + FLOW_ARROW_OFFSET_Y),
                xytext=(FLOW_ARROW_CENTER_X, float_previous_y - FLOW_ARROW_OFFSET_Y),
                arrowprops=dict_arrowprops,
            )

        # 把当前节点中心纵坐标登记为下一轮箭头的起点参考。
        float_previous_y = float_center_y  # 下一轮箭头使用的上一节点纵坐标

    # 先确保输出目录存在，再把当前流程图写成白底 PNG 文件。
    path_output_png.parent.mkdir(parents=True, exist_ok=True)

    # 把流程图主体保存成紧凑 PNG，供 DOCX 主稿直接嵌入正文。
    obj_figure.savefig(path_output_png, bbox_inches="tight", facecolor="white")

    # 释放流程图画布对象，避免批量案件连续生成时积累绘图库句柄。
    obj_pyplot.close(obj_figure)

# 把系统模块写成 PNG 交付图，供 DOCX 导出阶段直接嵌入正文。
def write_module_png(path_output_png: Path, list_modules: list[dict[str, str]]) -> None:
    """把系统模块图写成 PNG 文件。

    参数：
    - `path_output_png`：系统模块图 PNG 输出路径。
    - `list_modules`：结构化系统模块列表。

    返回：
    - `None`。

    异常：
    - 图片写入失败时由底层异常上抛。
    """

    # 为模块图探测可选绘图库，探测失败不会阻断 PNG 输出。
    tuple_matplotlib_backend = load_matplotlib_backend()  # 模块图可选绘图后端

    # 可选后端不可用时改用纵向 Pillow 框图表达模块关系。
    if tuple_matplotlib_backend is None:

        # 合并模块名称和功能说明，形成单个模块框的多行正文。
        list_text_blocks = [  # Pillow 回退模块图图框正文列表
            "\n".join(  # 当前模块框内的名称与功能摘要
                [
                    *wrap_figure_text(  # 模块名称换行结果
                        str(dict_module["name"]),  # 当前模块正式名称
                        MODULE_NAME_WRAP_WIDTH,  # 模块名称允许的换行宽度
                        MODULE_NAME_MAX_LINES,  # 模块名称允许的最大文本行数
                    ),
                    *wrap_figure_text(  # 模块功能换行结果
                        str(dict_module["function"]),  # 当前模块功能说明
                        MODULE_FUNCTION_WRAP_WIDTH,  # 模块功能说明允许的换行宽度
                        MODULE_FUNCTION_MAX_LINES,  # 模块功能说明允许的最大文本行数
                    ),
                ]
            )
            for dict_module in list_modules  # 保持正式模块清单顺序
        ]

        # 写出可供 Word 直接嵌入的系统模块图 PNG。
        write_pillow_diagram(path_output_png, "图 2 系统模块图", list_text_blocks)

        # 模块框图已经写盘，当前函数无需创建第二份 matplotlib 画布。
        return

    # 解包可用后端，显式区分 pyplot 对象与圆角框类型。
    obj_pyplot, class_fancy_bbox_patch = tuple_matplotlib_backend  # matplotlib 模块图绘图对象

    # 依据模块数量确定列数，少量模块单列，多于两个模块时使用双列布局。
    int_columns = MODULE_DOUBLE_COLUMN if len(list_modules) > MODULE_DOUBLE_COLUMN_THRESHOLD else MODULE_SINGLE_COLUMN  # 当前模块图列数

    # 按列数推算行数，保证所有模块都能落在画布内。
    int_rows = (len(list_modules) + int_columns - 1) // int_columns  # 当前模块图行数

    # 根据行数生成画布高度，给更高的多行模块框和边缘箭头留出稳定留白。
    float_height = MODULE_PLOT_BASE_HEIGHT + int_rows * MODULE_PLOT_ROW_HEIGHT  # 系统模块图画布高度（英寸）

    # 创建白底画布，供模块框和连接箭头排版。
    obj_figure, obj_axes = obj_pyplot.subplots(figsize=(MODULE_PLOT_CANVAS_WIDTH, float_height), dpi=FIGURE_PLOT_DPI)  # 系统模块图画布和坐标轴

    # 解析当前 PNG 绘图要复用的中文字体属性，避免模块名和功能摘要退化成缺字方块。
    obj_font = build_png_cjk_font_properties()  # 系统模块图文本字体属性

    # 固定模块图箭头样式参数，避免每次 annotate 都重复拼接同一套黑白样式。
    dict_arrowprops = build_arrowprops()  # 模块图箭头样式参数

    # 固定圆角框类对象引用，避免附图绘制 helper 调用行过长。
    class_box_patch = class_fancy_bbox_patch  # 模块图圆角框类对象

    # 关闭坐标轴显示，保证模块图只保留结构框、标题和箭头。
    obj_axes.axis("off")

    # 固定横向范围，供单列和双列布局共用一套坐标语义。
    obj_axes.set_xlim(0.0, MODULE_X_AXIS_LIMIT)

    # 固定纵向范围，让图题和模块框位置稳定。
    obj_axes.set_ylim(0.0, float_height * MODULE_Y_AXIS_SCALE)

    # 在画布顶部写入系统模块图图题，保证单独查看 PNG 时也能识别图号与类型。
    obj_axes.text(
        MODULE_TITLE_CENTER_X,
        float_height * MODULE_Y_AXIS_SCALE - FIGURE_TITLE_TOP_MARGIN,
        "图 2 系统模块图",
        ha="center",
        va="center",
        fontsize=FIGURE_TITLE_FONT_SIZE,
        fontweight="bold",
        fontproperties=obj_font,
    )

    # 先把当前模块图的版面坐标固化成几何记录，保证连线阶段只消费记录而不再重算。
    list_boxes = draw_module_png_boxes(obj_axes, list_modules, int_columns, float_height, obj_font, class_box_patch)  # 模块图几何记录列表

    # 再按相邻模块的边界和中心坐标补画贴边箭头，保持系统模块关系连贯可读。
    draw_module_png_connections(obj_axes, list_boxes, dict_arrowprops)

    # 先确保输出目录存在，再把当前模块图写成白底 PNG 文件。
    path_output_png.parent.mkdir(parents=True, exist_ok=True)

    # 把模块图主体保存成紧凑 PNG，供正式交底书主稿直接嵌图。
    obj_figure.savefig(path_output_png, bbox_inches="tight", facecolor="white")

    # 释放模块图画布对象，避免多案件连续生成时持续占用绘图库资源。
    obj_pyplot.close(obj_figure)
