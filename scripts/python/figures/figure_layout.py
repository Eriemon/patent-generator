#!/usr/bin/env python3
"""承载附图生成流程的既有实现，供协调器兼容加载。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入 dataclass，供附图资产路径以轻量结构统一传递。
from dataclasses import dataclass

# 引入参数解析、环境变量、按路径加载模块、标准输出和路径能力，供附图入口稳定运行。
import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

# 引入 HTML 转义和正则能力，供 SVG 文本安全输出与正文结构提取逻辑复用。
from html import escape
import re
import textwrap

# 使用 Pillow 绘制相邻纵向框体之间的连接箭头。
def draw_pillow_vertical_arrow(
    obj_draw: Any,
    int_center_x: int,
    int_box_bottom: int,
    int_box_gap: int,
) -> None:
    """绘制纵向箭头主干和实心三角尖端。

    参数：
    - `obj_draw`：Pillow 绘图上下文。
    - `int_center_x`：框体中心横坐标。
    - `int_box_bottom`：当前框体底部纵坐标。
    - `int_box_gap`：当前框体到下一框体的间距。

    返回：
    - `None`。
    """

    # 箭头起点保留边缘间距，避免线段贴住当前框体。
    int_arrow_top = int_box_bottom + PILLOW_ARROW_MARGIN  # 箭头起点纵坐标

    # 箭头终点位于下一框体上方，为三角尖端保留空间。
    int_arrow_bottom = int_box_bottom + int_box_gap - PILLOW_ARROW_MARGIN  # 箭头终点纵坐标

    # 沿框体中心线绘制箭头主干。
    obj_draw.line(
        (int_center_x, int_arrow_top, int_center_x, int_arrow_bottom),
        fill="black",
        width=PILLOW_LINE_WIDTH,
    )

    # 使用实心三角形表达自上而下的阅读方向。
    obj_draw.polygon(
        [
            (int_center_x, int_arrow_bottom + PILLOW_ARROW_TIP_LENGTH),
            (int_center_x - PILLOW_ARROW_HALF_WIDTH, int_arrow_bottom - PILLOW_ARROW_BASE_OFFSET),
            (int_center_x + PILLOW_ARROW_HALF_WIDTH, int_arrow_bottom - PILLOW_ARROW_BASE_OFFSET),
        ],
        fill="black",
    )

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

# 固定流程图画布基础高度，供标题、步骤框和箭头共用纵向空间。
FLOW_CANVAS_BASE_HEIGHT = 1.6  # 方法流程图基础高度（英寸）

# 固定流程图每个步骤增加的纵向高度，保证步骤框与箭头留白稳定。
FLOW_CANVAS_STEP_HEIGHT = 1.35  # 每个步骤贡献的画布高度（英寸）

# 固定流程图画布宽度，兼顾图题与步骤摘要换行可读性。
FLOW_CANVAS_WIDTH = 8.0  # 方法流程图画布宽度（英寸）

# 固定 PNG 绘图 DPI，保证 DOCX 嵌图时文字仍可阅读。
FIGURE_PLOT_DPI = 180  # 绘图输出 DPI

# 固定 Pillow 回退画布宽度，保证中文摘要拥有足够横向空间。
PILLOW_CANVAS_WIDTH = 1400  # Pillow 回退画布宽度（像素）

# 固定 Pillow 回退图的左右留白，避免框线贴边。
PILLOW_HORIZONTAL_MARGIN = 90  # Pillow 回退图水平留白（像素）

# 固定图题区域和首框之间的垂直空间。
PILLOW_TITLE_HEIGHT = 110  # Pillow 图题区域高度（像素）

# 固定回退图内容框高度，容纳多行中文摘要。
PILLOW_BOX_HEIGHT = 150  # Pillow 内容框高度（像素）

# 固定相邻内容框之间的连接区域高度。
PILLOW_BOX_GAP = 70  # Pillow 内容框间距（像素）

# 固定回退图底部留白，防止末框贴边。
PILLOW_BOTTOM_MARGIN = 70  # Pillow 底部留白（像素）

# 固定 Pillow 图题和正文的字体层级。
PILLOW_TITLE_FONT_SIZE = 34  # Pillow 图题字号

# 固定 Pillow 正文框字体大小。
PILLOW_BODY_FONT_SIZE = 28  # Pillow 正文字号

# 固定图题中心的纵坐标。
PILLOW_TITLE_CENTER_Y = 45  # Pillow 图题中心纵坐标（像素）

# 固定圆角框半径和黑白线条宽度。
PILLOW_BOX_RADIUS = 18  # Pillow 圆角框半径（像素）

# 固定回退图框线和箭头的笔画宽度。
PILLOW_LINE_WIDTH = 3  # Pillow 线条宽度（像素）

# 固定多行正文的行间距。
PILLOW_TEXT_SPACING = 6  # Pillow 多行正文间距（像素）

# 固定箭头主干与上下框体之间的安全留白。
PILLOW_ARROW_MARGIN = 12  # Pillow 箭头端点留白（像素）

# 固定箭头尖端伸出主干的长度。
PILLOW_ARROW_TIP_LENGTH = 10  # Pillow 箭头尖端长度（像素）

# 固定箭头三角形的半宽。
PILLOW_ARROW_HALF_WIDTH = 8  # Pillow 箭头尖端半宽（像素）

# 固定箭头三角形底边相对主干终点的偏移。
PILLOW_ARROW_BASE_OFFSET = 4  # Pillow 箭头底边偏移（像素）

# 固定方法流程图横向坐标范围，供步骤框和箭头共享一套坐标语义。
FLOW_X_AXIS_LIMIT = 10.0  # 方法流程图横向坐标上限

# 固定流程图纵向缩放倍率，让顶部标题和步骤框落在同一坐标体系下。
FLOW_Y_AXIS_SCALE = 2.0  # 方法流程图纵向缩放倍率

# 固定方法流程图图题横向中心点，保证标题位于画布正中。
FLOW_TITLE_CENTER_X = 5.0  # 方法流程图图题横向中心点

# 固定图题距离画布顶端的纵向留白，避免标题贴边。
FIGURE_TITLE_TOP_MARGIN = 0.6  # 图题顶部留白

# 固定附图图题字号，保证单独查看 PNG 时仍能识别图号。
FIGURE_TITLE_FONT_SIZE = 14  # 附图图题字号

# 固定流程图首个步骤框中心纵坐标偏移，保证标题与正文留白稳定。
FLOW_FIRST_STEP_OFFSET = 1.8  # 流程图首个步骤框纵向偏移

# 固定流程图相邻步骤框中心纵向间距，保证箭头和文字不拥挤。
FLOW_STEP_VERTICAL_GAP = 2.2  # 流程图步骤框纵向间距

# 固定流程图步骤框左边距，保证框体整体位于画布中部。
FLOW_BOX_LEFT = 1.4  # 流程图步骤框左边距

# 固定流程图步骤框宽度，兼顾步骤编号和摘要的横向排版。
FLOW_BOX_WIDTH = 7.2  # 流程图步骤框宽度

# 固定流程图步骤框高度，保证三行摘要场景下框体仍有上下留白。
FLOW_BOX_HEIGHT = 1.6  # 流程图步骤框高度

# 固定流程图步骤框半高，便于从中心坐标稳定反推出框体起点。
FLOW_BOX_HALF_HEIGHT = 0.8  # 流程图步骤框半高

# 固定流程图步骤文字字号，兼顾 DOCX 嵌图后的可读性与三行排版密度。
FLOW_TEXT_FONT_SIZE = 9.3  # 流程图步骤文字字号

# 固定流程图箭头所在横坐标，使连接线始终穿过步骤框中心。
FLOW_ARROW_CENTER_X = 5.0  # 流程图箭头横向中心点

# 固定流程图箭头与步骤框边缘的纵向留白，避免箭头压到更高的框体边界。
FLOW_ARROW_OFFSET_Y = 0.92  # 流程图箭头纵向偏移

# 固定模块图画布宽度，兼顾双列布局与图题排版空间。
MODULE_PLOT_CANVAS_WIDTH = 8.8  # 系统模块图画布宽度（英寸）

# 固定模块图基础高度，容纳图题和首行模块框。
MODULE_PLOT_BASE_HEIGHT = 2.0  # 系统模块图基础高度（英寸）

# 固定模块图每行增加的高度，保证更高模块框与跨行箭头仍有可读留白。
MODULE_PLOT_ROW_HEIGHT = 2.8  # 系统模块图每行贡献高度（英寸）

# 固定模块图横向坐标范围，供单双列布局共用同一套坐标语义。
MODULE_X_AXIS_LIMIT = 10.0  # 系统模块图横向坐标上限

# 固定模块图纵向缩放倍率，让图题和模块框位置稳定。
MODULE_Y_AXIS_SCALE = 2.0  # 系统模块图纵向缩放倍率

# 固定模块图图题横向中心点，确保标题在双列布局下仍位于视觉中心。
MODULE_TITLE_CENTER_X = 5.0  # 模块图标题中心点坐标

# 固定模块图首列左边距，供按列排版计算模块框位置。
MODULE_BOX_LEFT = 0.9  # 系统模块图模块框左边距

# 固定模块图列间距，保证双列场景下左右模块不会挤压。
MODULE_BOX_COLUMN_GAP = 4.5  # 系统模块图列间距

# 固定模块图首行纵向偏移，保证图题下方留白稳定。
MODULE_FIRST_ROW_OFFSET = 2.2  # 系统模块图首行纵向偏移

# 固定模块图行间距，给相邻模块和箭头留出足够空间。
MODULE_ROW_GAP = 2.3  # 系统模块图行间距

# 固定模块图模块框宽度，兼顾模块名和功能摘要换行。
MODULE_BOX_WIDTH_PLOT = 3.6  # 系统模块图模块框宽度

# 固定模块图模块框高度，保证标题加两行说明仍可读。
MODULE_BOX_HEIGHT_PLOT = 1.95  # 系统模块图模块框高度

# 固定模块图模块框中心相对左边距的横向偏移，便于统一写入文字。
MODULE_BOX_CENTER_OFFSET_X = 1.8  # 系统模块图模块框中心横向偏移

# 固定模块图模块框中心相对顶部的纵向偏移，保证高框体里的标题与说明仍居中。
MODULE_BOX_CENTER_OFFSET_Y = 0.62  # 系统模块图模块框中心纵向偏移

# 固定模块图文字字号，兼顾单列和双列场景下的换行可读性。
MODULE_TEXT_FONT_SIZE = 8.3  # 系统模块图文字字号

# 固定模块图箭头与模块框边缘的纵向留白，避免箭头压线。
MODULE_ARROW_OFFSET_Y = 0.72  # 系统模块图箭头纵向偏移

# 固定圆角矩形框的样式参数，保持流程图与模块图风格一致。
FIGURE_BOX_STYLE = "round,pad=0.08"  # 圆角矩形框样式

# 固定附图框线宽，保证 PNG 嵌入 DOCX 后边界仍清晰。
FIGURE_BOX_LINEWIDTH = 1.4  # 附图框线宽

# 固定附图边框颜色，保持所有导出图统一为黑白稿。
FIGURE_BOX_EDGE_COLOR = "black"  # 附图边框颜色

# 固定附图填充颜色，保证导出图适配专利常见黑白交底风格。
FIGURE_BOX_FACE_COLOR = "white"  # 附图填充颜色

# 固定附图箭头样式，保持流程图与模块图的一致视觉语义。
FIGURE_ARROW_STYLE = "->"  # 附图箭头样式

# 固定附图箭头线宽，保证导出 PNG 在缩放后仍可辨识。
FIGURE_ARROW_LINEWIDTH = 1.2  # 附图箭头线宽

# 固定附图箭头颜色，保持导出图整体为黑白稿。
FIGURE_ARROW_COLOR = "black"  # 附图箭头颜色

# 基于系统环境变量和当前用户主目录盘符推导 Windows 字体目录，避免在源码里写死本机盘符。
def build_windows_fonts_dir() -> Path:
    """推导当前环境下的 Windows 字体目录。

    参数：
    - 无。

    返回：
    - `Path`：Windows 字体目录路径。

    异常：
    - 无。
    """

    # 先按环境变量与当前用户盘符顺序推导系统根目录，兼容本机与受限运行环境。
    str_windows_root = os.environ.get("WINDIR")  # 优先尝试当前进程显式暴露的 Windows 根目录

    # WINDIR 缺失时，继续尝试兼容旧式环境变量名。
    if not str_windows_root:

        # 再读取 SystemRoot，兼容只暴露旧式系统根目录变量的运行环境。
        str_windows_root = os.environ.get("SystemRoot")  # 兼容只提供旧式变量名的 Windows 根目录

    # 系统环境变量仍缺失时，再回退到当前用户主目录盘符。
    if not str_windows_root:

        # 主目录盘符通常仍能反映当前 Windows 安装所在盘符。
        str_windows_root = Path.home().anchor  # 从当前用户主目录反推出本机系统盘符

    # 如果以上候选都为空，再用平台根路径保底，避免得到空路径。
    if not str_windows_root:

        # 平台根路径是最后的兜底值，保证后续字体目录拼装总有基准。
        str_windows_root = os.sep  # 在非 Windows 受限环境下保留根路径兜底

    # 再在系统根目录下拼出 Fonts 子目录，供字体探测逻辑稳定复用。
    path_windows_fonts_dir = Path(str_windows_root) / "Fonts"  # Windows 字体目录路径

    # 返回推导出的 Windows 字体目录。
    return path_windows_fonts_dir

# 固定 Windows 字体目录路径，供 PNG 绘图优先解析可用中文字体。
WINDOWS_FONTS_DIR = build_windows_fonts_dir()  # PNG 绘图使用的字体目录

# 固定 PNG 绘图优先尝试的中文字体文件名序列，优先选择常见无衬线中文字体。
PREFERRED_CJK_FONT_FILENAMES = (  # PNG 绘图优先尝试的中文字体文件名
    "NotoSansSC-VF.ttf",  # 跨平台开源思源黑体可变字体
    "msyh.ttc",  # 微软雅黑常规字体
    "msyhl.ttc",  # 微软雅黑 Light 字体
    "simhei.ttf",  # 黑体字体
    "simsun.ttc",  # 宋体字体
    "simsunb.ttf",  # 宋体粗体字体
)  # PNG 绘图优先中文字体文件名序列

# 允许隔离服务器显式提供字体目录，避免代码依赖某个操作系统的全局安装位置。
PATENT_FONT_DIR_ENV = "PATENT_GENERATOR_FONT_DIR"  # 可选字体目录环境变量

# 固定 SVG 文本要声明的字体族栈，保证独立附图源文件也优先命中中文字体。
SVG_FONT_FAMILY_STACK = "Microsoft YaHei, SimHei, SimSun, Arial, sans-serif"  # SVG 文本字体族栈

# 固定附图源文本可保留的最大字符数，避免提取阶段就把句子截成生硬半句。
METHOD_STEP_SUMMARY_MAX_CHARS = 56  # 方法步骤摘要的最大字符数

# 固定模块名称可保留的最大字符数，避免模块标题过长挤压功能说明空间。
MODULE_NAME_MAX_CHARS = 20  # 模块名称的最大字符数

# 固定模块功能说明可保留的最大字符数，兼顾信息量和图框可读性。
MODULE_FUNCTION_MAX_CHARS = 32  # 模块功能说明的最大字符数

# 固定附图文本溢出时使用的省略号字符，避免截断后看起来像误生成。
FIGURE_TEXT_ELLIPSIS = "…"  # 附图文本截断省略号

# 预编译附图文本多空白压缩规则，保证换行前的字数估算稳定。
RE_FIGURE_TEXT_MULTISPACE = re.compile(r"\s+")  # 附图文本多空白压缩规则

# 固定流程图文本换行宽度，保证中文摘要能够真正进入框内。
FLOW_TEXT_WRAP_WIDTH = 24  # 流程图文本每行最大字符数

# 固定流程图文本最大行数，避免单步说明把整张图拉得过长。
FLOW_TEXT_MAX_LINES = 3  # 流程图文本最大行数

# 固定流程图文本行距，保证多行摘要在 DOCX 嵌图后仍可分辨。
FLOW_TEXT_LINE_SPACING = 1.28  # 流程图文本行距

# 固定流程图箭头与步骤框边缘的额外留白，避免箭头压住边框。
FLOW_ARROW_EDGE_PADDING = 0.12  # 流程图箭头与边框之间的额外留白

# 固定流程图 SVG 节点高度，让三行步骤摘要在矢量图里仍保有上下留白。
FLOW_SVG_BOX_HEIGHT = 88  # 三行流程摘要对应的 SVG 框高

# 固定流程图 SVG 节点间距，给竖向箭头留出稳定连接空间。
FLOW_SVG_BOX_GAP = 30  # 流程图 SVG 步骤框间距

# 固定模块标题文本换行宽度，保证名称和功能说明分层清晰。
MODULE_NAME_WRAP_WIDTH = 10  # 模块标题每行最大字符数

# 固定模块标题最大行数，避免模块名挤占功能说明的主要空间。
MODULE_NAME_MAX_LINES = 2  # 模块标题最大行数

# 固定模块功能说明换行宽度，保证双列模块图也能完整放入框内。
MODULE_FUNCTION_WRAP_WIDTH = 16  # 模块功能说明每行最大字符数

# 固定模块功能说明最大行数，避免图框被少量长句拖垮。
MODULE_FUNCTION_MAX_LINES = 2  # 模块功能说明最大行数

# 固定模块图文本行距，保证标题和功能说明在同框内分层可读。
MODULE_TEXT_LINE_SPACING = 1.2  # 模块图文本行距

# 固定模块图箭头与边框之间的额外留白，避免连线压到矩形边缘。
MODULE_ARROW_EDGE_PADDING = 0.1  # 模块图箭头与边框之间的额外留白

# 固定模块图 SVG 节点高度，保证标题加两行说明时仍可读。
MODULE_SVG_BOX_HEIGHT = 108  # 模块图 SVG 模块框高度

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

# 解析当前环境下可直接用于 PNG 绘图的中文字体路径。
def find_preferred_cjk_font_path() -> Path | None:
    """解析首个可用中文字体路径。

    参数：
    - 无。

    返回：
    - `Path | None`：命中时返回首个可用中文字体路径，否则返回 `None`。

    异常：
    - 无。
    """

    # 显式字体目录优先于系统目录，便于远端隔离验证和无管理员权限部署。
    list_font_dirs = [Path(os.environ[PATENT_FONT_DIR_ENV])] if os.environ.get(PATENT_FONT_DIR_ENV) else []  # 候选字体目录

    # Windows 字体目录始终作为本地兼容回退候选。
    list_font_dirs.append(WINDOWS_FONTS_DIR)

    # 按目录和文件优先级逐项检查，保证 PNG 绘图稳定命中可用中文字体。
    for path_font_dir in list_font_dirs:

        # 当前目录按既定字体优先级逐项检查。
        for str_filename in PREFERRED_CJK_FONT_FILENAMES:

            # 拼出当前候选中文字体路径，供存在性检查复用。
            path_candidate_font = path_font_dir / str_filename  # 当前候选中文字体路径

            # 找到首个真实存在的中文字体后立即返回，减少后续重复扫描。
            if path_candidate_font.is_file():

                # 返回首个命中的中文字体路径，供 matplotlib FontProperties 构造复用。
                return path_candidate_font

    # 在当前环境没有命中任何预设中文字体时返回空值，让上层继续走默认字体回退。
    return None

# 构造 PNG 绘图要使用的中文字体属性对象，避免默认字体缺少中文字形。
def build_png_cjk_font_properties() -> Any | None:
    """构造 PNG 绘图中文字体属性。

    参数：
    - 无。

    返回：
    - `Any | None`：命中字体时返回 matplotlib 字体属性对象，否则返回 `None`。

    异常：
    - 无；字体属性构造失败时直接回退为 `None`。
    """

    # 先解析当前环境可用的中文字体路径，供后续字体属性构造复用。
    path_font = find_preferred_cjk_font_path()  # 当前环境可用中文字体路径

    # 在当前环境没有可用中文字体路径时直接回退空值，让上层保留默认字体行为。
    if path_font is None:

        # 返回空字体属性，表示当前绘图路径只能继续使用 matplotlib 默认字体。
        return None

    # 尝试按路径导入 matplotlib 字体属性对象，避免模块导入期强依赖字体子模块。
    try:

        # 只在函数内部导入 FontProperties，减少非 PNG 路径的额外依赖耦合。
        from matplotlib.font_manager import FontProperties

    # 字体属性子模块异常时直接回退空值，保持附图流程不会因为字体辅助失败而中断。
    except Exception:

        # 返回空字体属性，交由上层走默认字体回退路径。
        return None

    # 返回绑定真实中文字体文件的属性对象，供流程图和模块图文本统一复用。
    return FontProperties(fname=str(path_font))

# 在附图换行与截断之前先规整轻量 Markdown 装饰，避免图框里残留反引号。
def normalize_figure_source_text(str_text: str) -> str:
    """规整附图源文本里的轻量 Markdown 装饰。

    参数：
    - `str_text`：待规整的原始文本。

    返回：
    - `str`：去掉轻量 Markdown 装饰并压缩空白后的单行文本。

    异常：
    - 无。
    """

    # 先去掉行内代码反引号，避免附图正文直接泄露 Markdown 装饰符。
    str_plain_text = str_text.replace("`", "")  # 去掉行内代码标记后的文本

    # 再压缩连续空白并去掉首尾空白，保证后续截断和换行使用同一份文本。
    return RE_FIGURE_TEXT_MULTISPACE.sub(" ", str_plain_text).strip()

# 在附图抽取阶段对原始文本做受控截断，避免句子半截停在连词或标点后面。
def clip_figure_source_text(str_text: str, int_max_chars: int) -> str:
    """对附图源文本做带省略号的受控截断。

    参数：
    - `str_text`：待截断的原始文本。
    - `int_max_chars`：允许保留的最大字符数。

    返回：
    - `str`：长度受控且必要时附带省略号的文本。

    异常：
    - 无。
    """

    # 先规整源文本里的 Markdown 装饰与空白，保证截断计数和最终输出一致。
    str_single_line_text = normalize_figure_source_text(str_text)  # 适合参与字符截断的单行文本

    # 在文本本身已经足够短时直接返回，避免平白引入省略号。
    if len(str_single_line_text) <= int_max_chars:

        # 返回原始长度已合规的文本，供后续换行逻辑继续处理。
        return str_single_line_text

    # 为省略号预留一个字符位，并去掉尾部可能影响观感的悬挂标点。
    str_clipped_text = str_single_line_text[: max(int_max_chars - 1, 1)].rstrip("，,；;、：: ")  # 已裁切但尚未补省略号的文本

    # 返回带省略号的受控截断结果，提醒读者该框内文本已经做过压缩。
    return f"{str_clipped_text}{FIGURE_TEXT_ELLIPSIS}"

# 按固定字符宽度为附图文本插入人工换行，避免中文在 matplotlib 中完全不换行。
def wrap_figure_text(
    str_text: str,
    int_wrap_width: int,
    int_max_lines: int,
) -> list[str]:
    """按附图约束把文本包装成有限行数。

    参数：
    - `str_text`：待换行的原始文本。
    - `int_wrap_width`：每行最大字符数。
    - `int_max_lines`：允许输出的最大行数。

    返回：
    - `list[str]`：已经插入人工换行的文本行列表。

    异常：
    - 无。
    """

    # 先规整 Markdown 装饰与多空白，保证字符宽度估算稳定。
    str_single_line_text = normalize_figure_source_text(str_text)  # 待换行的单行文本

    # 在当前文本为空时返回单个空行，避免调用方额外处理空列表。
    if not str_single_line_text:

        # 返回单个空行，保持上层拼接逻辑结构稳定。
        return [""]

    # 先收拢 textwrap 的关键参数，避免后续调用在视觉修复阶段再次拉成长块代码。
    dict_wrap_options = {"width": int_wrap_width, "break_long_words": True, "break_on_hyphens": False}  # textwrap 包装参数字典

    # 按固定字符宽度拆成多行，显式允许中文长串在没有空格时也能断行。
    list_wrapped_lines = textwrap.wrap(str_single_line_text, **dict_wrap_options)  # 初步换行后的文本行列表

    # 在初步换行结果为空时回退到原文本单行，避免边界输入导致空输出。
    if not list_wrapped_lines:

        # 返回未换行的原文本，保证至少保留可见内容。
        return [str_single_line_text]

    # 在当前行数已经满足上限时直接返回，避免无意义的再次裁剪。
    if len(list_wrapped_lines) <= int_max_lines:

        # 返回已经满足约束的换行结果，供流程图和模块图直接复用。
        return list_wrapped_lines

    # 先保留最大行数之前的所有完整行，最后一行再做受控合并裁剪。
    list_preserved_lines = list_wrapped_lines[: int_max_lines - 1]  # 可以原样保留的前置文本行

    # 把剩余文本重新拼成一个尾行候选，保证省略号总是落在最后一行。
    str_tail_text = "".join(list_wrapped_lines[int_max_lines - 1 :])  # 等待压缩进最后一行的尾部文本

    # 依据末行宽度约束对尾行做受控截断，避免超过框体宽度。
    str_last_line = clip_figure_source_text(str_tail_text, int_wrap_width)  # 最大行数约束下的最终尾行文本

    # 返回行数受控的换行结果，确保最后一行必要时带省略号。
    return [*list_preserved_lines, str_last_line]

# 解析模块图的蛇形列位置，保证相邻模块跨行时仍能走边缘竖线而不是对角穿框。
def resolve_module_grid_position(int_index: int, int_columns: int) -> tuple[int, int]:
    """解析模块图中单个模块的蛇形行列位置。

    参数：
    - `int_index`：当前模块在原始顺序中的索引。
    - `int_columns`：当前模块图的总列数。

    返回：
    - `tuple[int, int]`：模块所在的行号与列号。

    异常：
    - 无。
    """

    # 先按普通行优先顺序推导当前模块所在的基础行号。
    int_row = int_index // int_columns  # 当前模块所在的基础行号

    # 再按当前列数推导基础列号，供蛇形布局修正前复用。
    int_column = int_index % int_columns  # 当前模块所在的基础列号

    # 在双列模块图的奇数行启用反向列号，让跨行连接保持竖向边缘对齐。
    if int_columns > MODULE_SINGLE_COLUMN and int_row % 2 == 1:

        # 把奇数行列号反向，形成更适合顺序箭头的蛇形排布。
        int_column = int_columns - MODULE_SINGLE_COLUMN - int_column  # 蛇形布局下修正后的列号

    # 返回最终的蛇形布局行列位置，供 SVG 和 PNG 共用。
    return int_row, int_column

# 构造 SVG 模块框的边界记录，供后续边缘箭头连接复用。
def build_svg_box_position_record(
    int_left: int,
    int_top: int,
    int_width: int,
    int_height: int,
) -> dict[str, int]:
    """构造 SVG 模块框的边界记录。

    参数：
    - `int_left`：模块框左边缘横坐标。
    - `int_top`：模块框上边缘纵坐标。
    - `int_width`：模块框宽度。
    - `int_height`：模块框高度。

    返回：
    - `dict[str, int]`：包含边界和中心坐标的 SVG 模块框记录。

    异常：
    - 无。
    """

    # 直接返回 SVG 模块框的边界与中心坐标，避免主流程重复手写同构字典。
    return {
        "left": int_left,
        "right": int_left + int_width,
        "top": int_top,
        "bottom": int_top + int_height,
        "center_x": int_left + int_width // 2,
        "center_y": int_top + int_height // 2,
    }

# 把 PNG 布局坐标封装成浮点边界记录，避免 annotate 阶段重复推导边缘位置。
def build_png_box_geometry_record(
    float_left: float,
    float_bottom: float,
    float_width: float,
    float_height: float,
    float_center_x: float,
    float_center_y: float,
) -> dict[str, float]:
    """构造 PNG 模块框的边界记录。

    参数：
    - `float_left`：模块框左边缘横坐标。
    - `float_bottom`：模块框下边缘纵坐标。
    - `float_width`：模块框宽度。
    - `float_height`：模块框高度。
    - `float_center_x`：模块框中心横坐标。
    - `float_center_y`：模块框中心纵坐标。

    返回：
    - `dict[str, float]`：包含边界和中心坐标的 PNG 模块框记录。

    异常：
    - 无。
    """

    # 直接返回 PNG 模块框的边界与中心坐标，避免主流程重复手写浮点字典。
    return {
        "left": float_left,
        "right": float_left + float_width,
        "top": float_bottom + float_height,
        "bottom": float_bottom,
        "center_x": float_center_x,
        "center_y": float_center_y,
    }

# 先把模块标题和功能说明整理成统一多行文本，避免 PNG 绘制循环里重复拼接包装逻辑。
def build_module_png_box_text(dict_module: dict[str, str]) -> str:
    """构造 PNG 模块框的多行正文文本。

    参数：
    - `dict_module`：当前模块的名称和功能说明记录。

    返回：
    - `str`：适合直接写入 matplotlib 文本节点的多行正文。

    异常：
    - 无。
    """

    # 先包装模块标题，保证名称不会沿水平方向撑破单列或双列框体。
    list_module_name_lines = wrap_figure_text(dict_module["name"], MODULE_NAME_WRAP_WIDTH, MODULE_NAME_MAX_LINES)  # 当前模块标题文本行列表

    # 先固定模块功能说明的单行宽度上限，避免长行调用再次触发风格门禁。
    int_wrap_width = MODULE_FUNCTION_WRAP_WIDTH  # 当前模块功能说明单行宽度上限

    # 再固定模块功能说明的最大行数，保证说明区不会继续向下拉长框体。
    int_line_limit = MODULE_FUNCTION_MAX_LINES  # 当前模块功能说明最大保留行数

    # 为了缩短 PNG 包装调用行，这里先缓存当前模块的功能说明原文。
    str_module_function_source = dict_module["function"]  # PNG 模块功能说明原文

    # 最后按宽度和行数约束包装功能说明，保证说明段落稳定落在边界内。
    list_module_function_lines = wrap_figure_text(str_module_function_source, int_wrap_width, int_line_limit)  # 当前模块功能说明文本行列表

    # 返回标题和说明拼接后的多行文本，供 PNG 框体正文直接复用。
    return "\n".join([*list_module_name_lines, *list_module_function_lines])

# 根据模块框左上角坐标推导 PNG 边界记录，避免绘制循环里重复展开中心点和边长常量。
def build_module_png_box_geometry(float_box_x: float, float_box_y: float) -> dict[str, float]:
    """构造单个 PNG 模块框的边界与中心坐标记录。

    参数：
    - `float_box_x`：模块框左上角横坐标。
    - `float_box_y`：模块框左上角纵坐标。

    返回：
    - `dict[str, float]`：当前模块框的边界与中心坐标记录。

    异常：
    - 无。
    """

    # 先推导当前模块框底边纵坐标，供贴边箭头上下锚点复用。
    float_box_bottom = float_box_y - MODULE_BOX_HEIGHT_PLOT + 0.72  # 当前模块框底边纵坐标

    # 再推导当前模块框中心横坐标，供左右箭头沿中心线贴边连接。
    float_box_center_x = float_box_x + MODULE_BOX_CENTER_OFFSET_X  # 当前模块框中心横坐标

    # 最后推导当前模块框中心纵坐标，供上下箭头和文本中心线共用。
    float_box_center_y = float_box_y - 0.255  # 当前模块框中心纵坐标

    # 返回当前模块框的完整几何记录，供后续箭头连接阶段直接消费。
    return build_png_box_geometry_record(
        float_box_x,
        float_box_bottom,
        MODULE_BOX_WIDTH_PLOT,
        MODULE_BOX_HEIGHT_PLOT,
        float_box_center_x,
        float_box_center_y,
    )

# 把模块框绘制和几何记录集中到 helper，避免主入口函数同时承担排版、落笔和收集三种职责。
def draw_module_png_boxes(
    obj_axes: Any,
    list_modules: list[dict[str, str]],
    int_columns: int,
    float_height: float,
    obj_font_properties: Any,
    class_box_patch: Any,
) -> list[dict[str, float]]:
    """绘制系统模块图的所有模块框，并返回箭头连接所需的边界记录。

    参数：
    - `obj_axes`：当前模块图的 matplotlib 坐标轴对象。
    - `list_modules`：结构化系统模块列表。
    - `int_columns`：当前模块图列数。
    - `float_height`：当前模块图画布高度。
    - `obj_font_properties`：模块图正文使用的中文字体属性。
    - `class_box_patch`：matplotlib 圆角矩形框类对象。

    返回：
    - `list[dict[str, float]]`：供后续箭头连接复用的模块框边界记录列表。

    异常：
    - 模块框绘制失败时由底层异常上抛。
    """

    # 收集每个模块框的边界和中心坐标，供相邻模块箭头沿边缘稳定连接。
    list_boxes: list[dict[str, float]] = []  # 模块框边界与中心坐标列表

    # 逐个模块绘制框体和正文，并同步登记后续箭头需要的几何信息。
    for int_index, dict_module in enumerate(list_modules):

        # 先读取当前模块在蛇形布局里的完整行列位置，后续再分别取出行号和列号。
        tuple_grid_position = resolve_module_grid_position(int_index, int_columns)  # 当前模块在蛇形布局下的行列位置二元组

        # 再单独读取当前模块所在行号，避免后续纵向坐标推导混入列方向语义。
        int_row = tuple_grid_position[0]  # 当前模块框目标行号

        # 继续读取当前模块所在列号，供横向排版和蛇形回折复用。
        int_column = tuple_grid_position[1]  # 当前模块框目标列号

        # 根据当前列号推导模块框左上角横坐标。
        float_box_x = MODULE_BOX_LEFT + int_column * MODULE_BOX_COLUMN_GAP  # 当前模块框左上角横坐标

        # 根据当前行号推导模块框左上角纵坐标。
        float_box_y = float_height * MODULE_Y_AXIS_SCALE - MODULE_FIRST_ROW_OFFSET - int_row * MODULE_ROW_GAP  # 当前模块框左上角纵坐标

        # 先把左上角坐标转换成圆角框构造器要求的左下角起点。
        tuple_box_origin = (float_box_x, float_box_y - MODULE_BOX_HEIGHT_PLOT + 0.72)  # 当前模块框左下角坐标

        # 先把当前模块框挂到画布，再把多行正文落在框体中央，保持 PNG 与 SVG 语义一致。
        obj_axes.add_patch(
            build_rounded_box_patch(
                class_box_patch,
                tuple_box_origin,
                MODULE_BOX_WIDTH_PLOT,
                MODULE_BOX_HEIGHT_PLOT,
            )
        )

        # 再把当前模块标题和功能说明写到框体中央，保证模块框正文与 SVG 版本保持同义。
        obj_axes.text(
            float_box_x + MODULE_BOX_CENTER_OFFSET_X,
            float_box_y - MODULE_BOX_CENTER_OFFSET_Y,
            build_module_png_box_text(dict_module),
            ha="center",
            va="center",
            fontsize=MODULE_TEXT_FONT_SIZE,
            fontproperties=obj_font_properties,
            linespacing=MODULE_TEXT_LINE_SPACING,
        )

        # 先固化当前模块框的边界和中心坐标，避免压入列表时再把几何推导混在一起。
        dict_box_geometry = build_module_png_box_geometry(float_box_x, float_box_y)  # 当前模块框几何记录

        # 再把当前模块框几何记录压入列表，供后续相邻模块贴边箭头直接复用。
        list_boxes.append(dict_box_geometry)

    # 返回完整的模块框几何记录，供箭头绘制阶段直接复用。
    return list_boxes

# 把相邻模块的箭头连接集中处理，避免主入口函数同时包含布局循环和连线分支。
def draw_module_png_connections(
    obj_axes: Any,
    list_boxes: list[dict[str, float]],
    dict_arrowprops: dict[str, Any],
) -> None:
    """给相邻模块框补画贴边箭头。

    参数：
    - `obj_axes`：当前模块图的 matplotlib 坐标轴对象。
    - `list_boxes`：模块框边界与中心坐标列表。
    - `dict_arrowprops`：统一箭头样式参数。

    返回：
    - `None`。

    异常：
    - 箭头绘制失败时由底层异常上抛。
    """

    # 按模块顺序连接相邻框体，保持方法描述里的数据流和控制流可视化。
    for int_index in range(1, len(list_boxes)):

        # 先读取箭头起点对应的上一模块框边界与中心坐标。
        dict_previous_box = list_boxes[int_index - 1]  # 上一模块框边界与中心坐标

        # 再读取箭头终点对应的当前模块框边界与中心坐标。
        dict_current_box = list_boxes[int_index]  # 当前模块框边界与中心坐标

        # 同行模块使用水平箭头，避免对角线穿过正文；跨行模块沿上下边缘竖连。
        if dict_previous_box["top"] == dict_current_box["top"]:

            # 在上一模块位于左侧时，沿左右边缘追加水平向右箭头。
            if dict_previous_box["center_x"] < dict_current_box["center_x"]:

                # 把上一框右边缘连到下一框左边缘，保持同行顺序关系清晰。
                obj_axes.annotate(
                    "",
                    xy=(dict_current_box["left"] - MODULE_ARROW_EDGE_PADDING, dict_current_box["center_y"]),
                    xytext=(dict_previous_box["right"] + MODULE_ARROW_EDGE_PADDING, dict_previous_box["center_y"]),
                    arrowprops=dict_arrowprops,
                )

            # 在上一模块位于右侧时，沿回折方向补画水平向左箭头。
            else:

                # 把上一框左边缘连回当前框右边缘，适配蛇形布局的回折阅读方向。
                obj_axes.annotate(
                    "",
                    xy=(dict_current_box["right"] + MODULE_ARROW_EDGE_PADDING, dict_current_box["center_y"]),
                    xytext=(dict_previous_box["left"] - MODULE_ARROW_EDGE_PADDING, dict_previous_box["center_y"]),
                    arrowprops=dict_arrowprops,
                )

            # 同行连接已经完成，本轮无需再走跨行竖向箭头分支。
            continue

        # 跨行场景保持竖向贴边连接，保证蛇形布局换行后仍然清晰可读。
        obj_axes.annotate(
            "",
            xy=(dict_current_box["center_x"], dict_current_box["top"] + MODULE_ARROW_EDGE_PADDING),
            xytext=(dict_previous_box["center_x"], dict_previous_box["bottom"] - MODULE_ARROW_EDGE_PADDING),
            arrowprops=dict_arrowprops,
        )

# 构造命令行参数解析器，统一声明案件目录和可选输入草稿参数。
