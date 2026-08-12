#!/usr/bin/env python3
"""根据正式交底书草稿生成本地附图草案与清单。"""

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

    异常：
    - 框对象构造失败时由底层异常上抛。
    """

    # 先读取圆角矩形框样式，避免构造调用里直接堆叠多个全局样式常量。
    str_boxstyle = FIGURE_BOX_STYLE  # 圆角矩形框样式字符串

    # 读取圆角矩形框线宽，供构造调用统一复用。
    float_linewidth = FIGURE_BOX_LINEWIDTH  # 圆角矩形框线宽

    # 读取圆角矩形框边框颜色，保持所有附图统一为黑白稿。
    str_edgecolor = FIGURE_BOX_EDGE_COLOR  # 圆角矩形框边框颜色

    # 读取圆角矩形框填充颜色，保证框体背景始终为白色。
    str_facecolor = FIGURE_BOX_FACE_COLOR  # 圆角矩形框填充颜色

    # 先组装圆角矩形框的基础位置与尺寸参数，避免构造调用块过密。
    tuple_patch_args = (tuple_origin, float_width, float_height)  # 圆角矩形框基础参数

    # 再用统一样式参数构造圆角矩形框对象，供流程图与模块图共用。
    return class_box_patch(
        *tuple_patch_args,
        boxstyle=str_boxstyle,
        linewidth=float_linewidth,
        edgecolor=str_edgecolor,
        facecolor=str_facecolor,
    )

# 构造附图箭头样式参数，供流程图与模块图复用同一套黑白箭头风格。
def build_arrowprops() -> dict[str, Any]:
    """构造附图箭头样式参数。

    参数：
    - 无。

    返回：
    - `dict[str, Any]`：供 matplotlib `annotate` 复用的箭头样式参数字典。

    异常：
    - 无。
    """

    # 返回统一箭头样式，保证流程图与模块图箭头视觉一致。
    return {
        "arrowstyle": FIGURE_ARROW_STYLE,
        "linewidth": FIGURE_ARROW_LINEWIDTH,
        "color": FIGURE_ARROW_COLOR,
    }

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
    int_width = 760  # 方法流程图画布宽度

    # 固定流程图矩形框横坐标，保证各步骤节点居中对齐。
    int_box_x = 120  # 方法步骤框横坐标

    # 固定流程图矩形框宽度，保证标题和摘要有稳定容纳空间。
    int_box_width = 520  # 方法步骤框宽度

    # 固定流程图矩形框高度，保证三行中文摘要也能真正进入框内。
    int_box_height = FLOW_SVG_BOX_HEIGHT  # 方法步骤框高度

    # 根据步骤数量计算画布高度，给更高的多行步骤框和箭头预留空间。
    int_height = 96 + len(list_steps) * (int_box_height + FLOW_SVG_BOX_GAP)  # 方法流程图画布高度

    # 先准备 SVG 文本片段列表，后续逐项追加标题、节点与箭头。
    list_parts = [  # 方法流程图 SVG 片段列表
        render_svg_header(int_width, int_height),  # 通用 SVG 头部
        (
            f'<text x="380" y="32" text-anchor="middle" font-size="18" '
            f'font-family="{SVG_FONT_FAMILY_STACK}">图 1 方法流程图</text>'
        ),  # 图题文本
    ]

    # 记录上一节点底部纵坐标，供后续箭头连接使用。
    int_previous_bottom = 0  # 上一节点底部纵坐标

    # 按方法步骤顺序逐项渲染节点和连接箭头。
    for int_index, dict_step in enumerate(list_steps):

        # 计算当前步骤框纵坐标，保持更高的多行步骤框之间仍有稳定留白。
        int_box_y = 60 + int_index * (int_box_height + FLOW_SVG_BOX_GAP)  # 当前步骤框纵坐标

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
                    380,
                    int_previous_bottom + FLOW_ARROW_EDGE_PADDING * 10,
                    380,
                    int_box_y - FLOW_ARROW_EDGE_PADDING * 10,
                )
            )

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

        # 在同一行时绘制水平箭头，更符合模块左右串联的阅读方向。
        if dict_current_box["top"] == dict_next_box["top"]:

            # 追加当前模块到下一模块的水平箭头。
            if dict_current_box["center_x"] < dict_next_box["center_x"]:

                # 在左到右场景下从右边缘连到下一模块左边缘，避免斜线穿过框体。
                list_parts.append(
                    render_svg_arrow(
                        dict_current_box["right"] + 2,
                        dict_current_box["center_y"],
                        dict_next_box["left"] - 2,
                        dict_next_box["center_y"],
                    )
                )

            # 在右到左场景下从左边缘连回前一列，保持蛇形阅读方向一致。
            else:

                # 从当前模块左边缘连到下一模块右边缘，避免跨框对角线。
                list_parts.append(
                    render_svg_arrow(
                        dict_current_box["left"] - 2,
                        dict_current_box["center_y"],
                        dict_next_box["right"] + 2,
                        dict_next_box["center_y"],
                    )
                )

        # 在跨行时绘制竖向箭头，保持模块迁移路径可读。
        else:

            # 追加当前模块到底下一行模块的竖向箭头。
            list_parts.append(
                render_svg_arrow(
                    dict_current_box["center_x"],
                    dict_current_box["bottom"] + 2,
                    dict_next_box["center_x"],
                    dict_next_box["top"] - 2,
                )
            )

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

            # 箭头从框体下方留白处开始，避免线段贴住边框。
            int_arrow_top = int_box_bottom + PILLOW_ARROW_MARGIN  # 当前箭头起点纵坐标（像素）

            # 箭头终点位于下一框体之前，给尖端保留空间。
            int_arrow_bottom = int_box_bottom + int_box_gap - PILLOW_ARROW_MARGIN  # 当前箭头终点纵坐标（像素）

            # 绘制箭头主干，沿框体中心线连接上下步骤。
            obj_draw.line(
                (int_center_x, int_arrow_top, int_center_x, int_arrow_bottom),
                fill="black",
                width=PILLOW_LINE_WIDTH,
            )

            # 使用实心三角形表示流程方向。
            obj_draw.polygon(
                [
                    (int_center_x, int_arrow_bottom + PILLOW_ARROW_TIP_LENGTH),
                    (int_center_x - PILLOW_ARROW_HALF_WIDTH, int_arrow_bottom - PILLOW_ARROW_BASE_OFFSET),
                    (int_center_x + PILLOW_ARROW_HALF_WIDTH, int_arrow_bottom - PILLOW_ARROW_BASE_OFFSET),
                ],
                fill="black",
            )

    # 确保目标目录存在，允许独立调用该回退渲染函数。
    path_output_png.parent.mkdir(parents=True, exist_ok=True)

    # 以显式 PNG 格式写盘，供 DOCX 嵌图和独立附图包复用。
    obj_image.save(path_output_png, format="PNG")

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
        list_text_blocks = [  # Pillow 回退流程图图框正文列表
            "\n".join(  # 当前步骤框内的多行中文摘要
                wrap_figure_text(  # 当前步骤编号和摘要的换行结果
                    f"{dict_step['id']}：{dict_step['summary']}",  # 当前方法步骤的编号和摘要
                    FLOW_TEXT_WRAP_WIDTH,  # 方法步骤框的换行宽度
                    FLOW_TEXT_MAX_LINES,  # 方法步骤框允许的最大文本行数
                )
            )
            for dict_step in list_steps  # 保持正式方法步骤的原始顺序
        ]

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

# 把附图资产路径收敛成轻量结构，避免 manifest 构造函数携带过多离散路径参数。
@dataclass(frozen=True)
class FigureArtifactPaths:
    """承载附图交付资产路径。"""

    # 记录正文草稿路径，供 manifest 溯源原始 disclosure draft。
    path_markdown: Path  # 正文草稿路径

    # 记录方法流程图 SVG 路径，供 review 阶段复用矢量稿。
    path_flow_svg: Path  # 方法流程图 SVG 路径

    # 记录方法流程图 PNG 路径，供正式 DOCX 主稿嵌图复用。
    path_flow_png: Path  # 交付主稿嵌图使用的流程图 PNG

    # 记录系统模块图 SVG 路径，供 review 阶段复用矢量稿。
    path_module_svg: Path  # 系统模块图 SVG 路径

    # 记录系统模块图 PNG 路径，供正式 DOCX 主稿嵌图复用。
    path_module_png: Path  # 交付主稿嵌图使用的系统图 PNG

# 以短函数名集中构造附图资产路径对象，避免主流程里出现超长 dataclass 初始化语句。
def make_artifact_paths(
    path_markdown: Path,
    path_flow_svg: Path,
    path_flow_png: Path,
    path_module_svg: Path,
    path_module_png: Path,
) -> FigureArtifactPaths:
    """构造附图资产路径对象。

    参数：
    - `path_markdown`：正文草稿路径。
    - `path_flow_svg`：方法流程图 SVG 路径。
    - `path_flow_png`：方法流程图 PNG 路径。
    - `path_module_svg`：系统模块图 SVG 路径。
    - `path_module_png`：系统模块图 PNG 路径。

    返回：
    - `FigureArtifactPaths`：统一封装后的附图资产路径对象。

    异常：
    - 无。
    """

    # 返回统一封装后的附图资产路径对象，供 manifest 构造逻辑直接消费。
    return FigureArtifactPaths(path_markdown, path_flow_svg, path_flow_png, path_module_svg, path_module_png)

# 组装 figures manifest 结构化数据，供 review 和 export 阶段复用。
def build_manifest(
    obj_artifact_paths: FigureArtifactPaths,
    list_steps: list[dict[str, str]],
    list_modules: list[dict[str, str]],
    module_runtime_support: Any,
) -> dict[str, Any]:
    """构造 figures manifest 结构化数据。

    参数：
    - `obj_artifact_paths`：附图交付资产路径集合。
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

    # 先组装附图元数据条目列表，保持图1 与图2 的交付语义集中管理。
    list_figures = [
        {
            "figure_no": "图1",  # 方法流程图图号
            "title": "方法流程图",  # 方法流程图标题
            "file": obj_artifact_paths.path_flow_svg.name,  # review 阶段复用的 SVG 文件名
            "delivery_file": obj_artifact_paths.path_flow_png.name,  # 正式交付 PNG 文件名
            "steps": list_step_ids,  # 方法流程图步骤索引列表
        },
        {
            "figure_no": "图2",  # 系统模块图图号
            "title": "系统模块图",  # 系统模块图标题
            "file": obj_artifact_paths.path_module_svg.name,  # review 阶段读取的系统图 SVG 文件名
            "delivery_file": obj_artifact_paths.path_module_png.name,  # 正式交付使用的系统图 PNG 文件名
            "modules": list_module_names,  # 系统模块图模块索引列表
        },
    ]  # figures manifest 附图条目列表

    # 再组装正式交付要暴露的附图文件清单，固定 PNG+SVG 双输出顺序。
    list_delivery_files = [
        obj_artifact_paths.path_flow_png.name,  # 方法流程图 PNG 文件名
        obj_artifact_paths.path_flow_svg.name,  # 正式交付中的流程图 SVG 文件名
        obj_artifact_paths.path_module_png.name,  # 系统模块图 PNG 文件名
        obj_artifact_paths.path_module_svg.name,  # 正式交付中的系统图 SVG 文件名
    ]  # 正式交付附图文件名列表

    # 返回完整 figures manifest 结构化数据，供 JSON 落盘与后链工具复用。
    return {
        "generated_at": module_runtime_support.iso_now(),
        "source_draft": str(obj_artifact_paths.path_markdown.resolve()),
        "figures": list_figures,
        "delivery_files": list_delivery_files,
    }

# 把附图 manifest 转换为模型中的来源与正文绑定登记表。
def build_figure_registry(dict_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """构造附图来源登记表。

    参数：
    - `dict_manifest`：已生成的 figures manifest。

    返回：
    - `list[dict[str, Any]]`：可写入结构化交底模型的附图登记表。

    异常：
    - manifest 中的 `figures` 不是列表时抛出 `ValueError`。
    """

    # 读取附图条目并验证容器类型，防止损坏 manifest 被写入正式模型。
    list_figures = dict_manifest.get("figures", [])  # manifest 附图条目

    # manifest 容器类型错误时立即阻断，避免继续解释不可信结构。
    if not isinstance(list_figures, list):

        # 抛出明确结构错误，要求调用方修复 manifest 后重新生成。
        raise ValueError("> ERR: [Python] figures manifest 的 figures 必须为列表。")

    # 保留正文草稿绝对路径，作为每张图的统一生成来源。
    str_provenance = str(dict_manifest.get("source_draft", "")).strip()  # 附图生成来源

    # 按 manifest 稳定顺序生成 FIG 标识，保持多次运行结果一致。
    list_registry: list[dict[str, Any]] = []  # 附图来源登记表

    # 逐条转换正式附图，保持 manifest 顺序与 FIG 标识一致。
    for int_index, dict_figure in enumerate(list_figures, start=1):

        # 非对象条目无法提供图号、文件和来源索引，必须立即阻断。
        if not isinstance(dict_figure, dict):

            # 抛出明确条目类型错误，避免生成部分有效的附图登记表。
            raise ValueError("> ERR: [Python] figures manifest 的附图条目必须为对象。")

        # 流程图使用步骤索引，模块图使用模块索引，二者统一映射为 source_items。
        list_source_items = dict_figure.get("steps", dict_figure.get("modules", []))  # 图内结构索引

        # 图内索引不是列表时无法建立稳定映射，必须停止回填。
        if not isinstance(list_source_items, list):

            # 抛出明确索引类型错误，要求修复附图生成输入。
            raise ValueError("> ERR: [Python] 附图 steps/modules 必须为列表。")

        # 记录来源、图号、文件及正文绑定，供审查与导出阶段交叉验证。
        list_registry.append(
            {
                "figure_id": f"FIG{int_index:03d}",
                "figure_no": str(dict_figure.get("figure_no", "")).strip(),
                "title": str(dict_figure.get("title", "")).strip(),
                "provenance": str_provenance,
                "section_ids": ["4.2", "5", "6"],
                "file": str(dict_figure.get("file", "")).strip(),
                "delivery_file": str(dict_figure.get("delivery_file", "")).strip(),
                "source_items": [str(obj_item).strip() for obj_item in list_source_items],
            }
        )

    # 返回与模型版本三合同兼容的附图登记表。
    return list_registry

# 在附图完成后回填结构化交底模型，避免模型与交付图件脱节。
def update_disclosure_model_figure_registry(
    path_case_dir: Path,
    dict_manifest: dict[str, Any],
    module_runtime_support: Any,
) -> Path:
    """回填结构化模型中的附图登记表。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `dict_manifest`：已生成的 figures manifest。
    - `module_runtime_support`：共享运行时支持模块。

    返回：
    - `Path`：完成回填的结构化模型路径。

    异常：
    - 模型文件不存在时抛出 `FileNotFoundError`。
    - 模型顶层不是对象时抛出 `ValueError`。
    """

    # 固定读取正式版本三模型，禁止在附图阶段另建旁路真相文件。
    path_model = path_case_dir / "03_drafts" / "latest_disclosure_model.json"  # 正式结构化模型路径

    # 模型不存在时禁止附图旁路落盘，以免交付图件脱离模型真相层。
    if not path_model.exists():

        # 抛出明确缺失错误，要求先完成正式交底模型生成阶段。
        raise FileNotFoundError("> ERR: [Python] 缺少 latest_disclosure_model.json，不能登记附图来源。")

    # 读取并验证模型顶层类型，避免覆盖损坏或非对象 JSON。
    dict_model = module_runtime_support.read_json_file(path_model)  # 当前结构化交底模型

    # 非对象模型无法安全更新登记表，必须保留原文件并停止处理。
    if not isinstance(dict_model, dict):

        # 抛出明确结构错误，避免覆盖损坏的模型文件。
        raise ValueError("> ERR: [Python] latest_disclosure_model.json 顶层必须为对象。")

    # 使用本次 manifest 重建附图登记表，使重复运行保持幂等。
    dict_model["figure_registry"] = build_figure_registry(dict_manifest)  # 本次附图来源登记表

    # 原位写回正式模型，让后续验证和 DOCX 导出读取同一事实源。
    module_runtime_support.write_json_file(path_model, dict_model)

    # 返回模型路径，便于调用方测试或记录本次回填目标。
    return path_model

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

    # 固定方法流程图 PNG 输出路径，作为正式主稿嵌图交付资产。
    path_flow_png = path_output_dir / "图1_方法流程图.png"  # 方法流程图 PNG 交付路径

    # 固定系统模块图 SVG 输出路径，保持附图目录命名稳定。
    path_module_svg = path_output_dir / "图2_系统模块图.svg"  # 系统模块图 SVG 输出路径

    # 固定系统模块图 PNG 输出路径，作为正式主稿嵌图交付资产。
    path_module_png = path_output_dir / "图2_系统模块图.png"  # 系统模块图 PNG 交付路径

    # 渲染并写出方法流程图 SVG 文本。
    module_runtime_support.write_text_file(path_flow_svg, render_flow_svg(list_steps))

    # 渲染并写出方法流程图 PNG 文件，作为正文嵌图交付资产。
    write_flow_png(path_flow_png, list_steps)

    # 渲染并写出系统模块图 SVG 文本。
    module_runtime_support.write_text_file(path_module_svg, render_module_svg(list_modules))

    # 渲染并写出系统模块图 PNG 文件，作为正文嵌图交付资产。
    write_module_png(path_module_png, list_modules)

    # 写出两份 Mermaid 源文件，便于后续增强渲染。
    write_mermaid_files(path_output_dir, list_steps, list_modules, module_runtime_support)

    # 先收拢附图资产路径参数序列，避免命名合规修复引入新的超长单行。
    list_artifact_path_args = [path_markdown, path_flow_svg, path_flow_png, path_module_svg, path_module_png]  # 附图资产路径参数序列

    # 先组装附图资产路径对象，供 manifest 构造逻辑统一消费。
    figure_artifact_paths_artifact_paths = make_artifact_paths(*list_artifact_path_args)  # 附图路径集

    # 为 manifest 构造调用准备共享支持别名，避免调用行超过当前项目长度阈值。
    module_support = module_runtime_support  # manifest 构造使用的共享支持模块

    # 再生成 figures manifest 结构化数据，供 JSON 落盘与后链工具复用。
    dict_manifest = build_manifest(figure_artifact_paths_artifact_paths, list_steps, list_modules, module_support)  # 待落盘的 figures manifest 结果

    # 固定 figures manifest JSON 输出路径，保持后链读取约定稳定。
    path_manifest_json = path_output_dir / "figures_manifest.json"  # figures manifest JSON 输出路径

    # 把 figures manifest JSON 写入案件目录。
    module_runtime_support.write_json_file(path_manifest_json, dict_manifest)

    # 回填正式结构化模型中的附图来源与正文绑定，禁止交付图件脱离模型真相层。
    update_disclosure_model_figure_registry(path_case_dir, dict_manifest, module_runtime_support)

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
