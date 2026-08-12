#!/usr/bin/env python3
"""提供附图共享样式对象与 Mermaid 源文件写入职责。"""

# 延迟解析类型注解，保持独立文件规格加载兼容。
from __future__ import annotations

# 标准库提供路径与运行时模块类型。
from pathlib import Path
from typing import Any

# 复用布局模块中登记的黑白附图样式常量。
from readable_patent_figure_layout import (
    FIGURE_ARROW_COLOR,
    FIGURE_ARROW_LINEWIDTH,
    FIGURE_ARROW_STYLE,

    # 框体边框、填充与线宽常量共同固定专利附图的黑白视觉规格。
    FIGURE_BOX_EDGE_COLOR,
    FIGURE_BOX_FACE_COLOR,
    FIGURE_BOX_LINEWIDTH,
    FIGURE_BOX_STYLE,
)

# 构造 Matplotlib 圆角框，统一流程图与模块图线条风格。
def build_rounded_box_patch(
    class_box_patch: Any,
    tuple_origin: tuple[float, float],
    float_width: float,
    float_height: float,
) -> Any:
    """构造统一样式的圆角矩形框对象。

    参数：
    - `class_box_patch`：圆角矩形框类对象。
    - `tuple_origin`：矩形框左下角起点坐标。
    - `float_width`：矩形框宽度。
    - `float_height`：矩形框高度。

    返回：
    - `Any`：已填充统一样式参数的圆角矩形框对象。
    """

    # 先读取圆角矩形框样式，避免构造调用里直接堆叠多个全局常量。
    str_boxstyle = FIGURE_BOX_STYLE  # 圆角矩形框样式字符串

    # 读取圆角矩形框线宽，供构造调用统一复用。
    float_linewidth = FIGURE_BOX_LINEWIDTH  # 圆角矩形框线宽

    # 读取边框颜色，保持所有附图统一为黑白稿。
    str_edgecolor = FIGURE_BOX_EDGE_COLOR  # 圆角矩形框边框颜色

    # 读取填充颜色，保证框体背景始终为白色。
    str_facecolor = FIGURE_BOX_FACE_COLOR  # 圆角矩形框填充颜色

    # 收拢框体基础位置与尺寸参数，保持构造调用清晰。
    tuple_patch_args = (tuple_origin, float_width, float_height)  # 圆角矩形框基础参数

    # 返回使用统一样式构造的圆角矩形框对象。
    return class_box_patch(
        *tuple_patch_args,
        boxstyle=str_boxstyle,
        linewidth=float_linewidth,
        edgecolor=str_edgecolor,
        facecolor=str_facecolor,
    )

# 构造箭头样式参数，供流程图与模块图复用同一套黑白箭头风格。
def build_arrowprops() -> dict[str, Any]:
    """构造 matplotlib 附图共用的黑白箭头样式参数。

    返回：
    - `dict[str, Any]`：供绘图调用复用的箭头样式参数。
    """

    # 返回统一箭头样式，保证流程图与模块图视觉一致。
    return {
        "arrowstyle": FIGURE_ARROW_STYLE,
        "linewidth": FIGURE_ARROW_LINEWIDTH,
        "color": FIGURE_ARROW_COLOR,
    }

# 生成 Mermaid 源文件，便于后续外部渲染或人工细化。
def write_mermaid_files(
    path_output_dir: Path,
    list_steps: list[dict[str, str]],
    list_modules: list[dict[str, str]],
    module_runtime_support: Any,
) -> None:
    """把方法步骤与系统模块写为可编辑 Mermaid 源文件。

    参数：
    - `path_output_dir`：附图输出目录路径。
    - `list_steps`：结构化方法步骤列表。
    - `list_modules`：结构化系统模块列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `None`：文件写入完成后返回。
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

    # 准备系统模块图 Mermaid 行列表，固定使用自左向右方向。
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
