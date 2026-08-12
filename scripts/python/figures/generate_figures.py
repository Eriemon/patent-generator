#!/usr/bin/env python3
"""协调正式交底书附图草案与清单生成。"""

# 延迟解析协调器类型注解，保持文件规格加载兼容。
from __future__ import annotations

# 标准库负责按真实路径加载拆分后的附图职责模块。
import importlib.util
import sys
from pathlib import Path
from typing import Any

# 固定当前附图职责模块目录，避免依赖调用方搜索路径。
PATH_FIGURE_MODULE_DIR = Path(__file__).resolve().parent  # 附图职责模块目录

# 声明职责模块加载顺序，使跨模块依赖先于使用方完成登记。
TUPLE_FIGURE_MODULE_NAMES = (  # 固定布局、正文、渲染、登记和编排模块的依赖加载顺序，避免后序导入缺件
    "readable_patent_figure_layout",  # 中文字体、文本换行和框体坐标计算职责
    "readable_patent_figure_content",  # 交底正文方法步骤与系统模块提取职责
    "readable_patent_figure_assets",  # 共享绘图样式与 Mermaid 源文件写入职责
    "readable_patent_figure_renderers",  # 矢量图、位图和可编辑图源渲染职责
    "readable_patent_figure_registry",  # 附图清单、来源登记与模型回填职责
    "readable_patent_figure_workflow",  # 附图资产生成顺序和落盘路径编排职责
)

# 按同目录真实路径加载职责模块，避免调用方搜索路径影响入口兼容性。
def load_figure_internal_module(str_module_name: str) -> Any:
    """按文件路径加载附图内部模块。

    参数：
    - `str_module_name`：内部模块的稳定注册名称。

    返回：
    - `Any`：已经执行并登记的模块对象。

    异常：
    - `ImportError`：模块文件无法建立加载规格时抛出。
    """

    # 从稳定注册名称还原同目录文件名。
    str_file_stem = str_module_name.removeprefix("readable_patent_")  # 职责模块文件 stem

    # 拼出职责模块真实路径，避免修改 sys.path。
    path_module = PATH_FIGURE_MODULE_DIR / f"{str_file_stem}.py"  # 职责模块源码路径

    # 读取稳定名称下已登记的模块，判断它是否属于当前技能 root。
    obj_registered_module = sys.modules.get(str_module_name)  # 已登记的同名职责模块

    # 只有真实文件路径一致时才复用模块对象，保持同 root 对象身份。
    if obj_registered_module is not None:

        # 读取已登记模块文件路径；无文件来源的对象不能证明属于当前 root。
        str_registered_file = getattr(obj_registered_module, "__file__", "")  # 已登记模块来源路径

        # 当前路径一致时返回原对象，避免重复初始化模块级常量。
        if str_registered_file and Path(str_registered_file).resolve() == path_module.resolve():

            # 返回当前技能 root 已完成加载的职责模块。
            return obj_registered_module

    # 为当前职责模块创建独立加载规格。
    obj_specification = importlib.util.spec_from_file_location(str_module_name, path_module)  # 职责模块加载规格

    # 加载规格不完整时阻断协调器启动。
    if obj_specification is None or obj_specification.loader is None:

        # 报告真实缺件路径，便于定位不完整技能包。
        raise ImportError(f"> ERR: [Python] 无法加载附图内部模块：{path_module}")

    # 创建模块对象并提前登记，供后续职责模块解析前序依赖。
    obj_module = importlib.util.module_from_spec(obj_specification)  # 待执行职责模块

    # 登记稳定模块名，保持跨模块 import 指向同一对象。
    sys.modules[str_module_name] = obj_module  # 职责模块注册项

    # 执行当前职责模块源码；组事务统一负责所有稳定键的失败回滚。
    obj_specification.loader.exec_module(obj_module)

    # 返回已加载模块供兼容导出收集名称。
    return obj_module

# 以完整稳定键组为事务边界加载全部附图职责模块。
def load_figure_module_group() -> list[Any]:
    """原子加载当前 root 的全部附图职责模块。

    参数：
    - 无。

    返回：
    - `list[Any]`：按依赖顺序完成加载的附图职责模块。

    异常：
    - 任一 helper 加载失败时恢复整组稳定键后原样上抛。
    """

    # 只记录事务开始时真实存在的稳定键及其对象身份。
    dict_original_modules = {  # 附图模块组事务快照
        str_module_name: sys.modules[str_module_name]  # 事务开始前的原模块对象
        for str_module_name in TUPLE_FIGURE_MODULE_NAMES  # 覆盖完整附图稳定键组
        if str_module_name in sys.modules  # 原先不存在的键不写入快照
    }

    # 顺序加载整组 helper，成功时保留当前 root 的完整模块组。
    try:

        # 返回完整模块列表，供兼容名称收集保持旧覆盖顺序。
        return [
            load_figure_internal_module(str_module_name)  # 当前附图职责模块
            for str_module_name in TUPLE_FIGURE_MODULE_NAMES  # 固定依赖加载顺序
        ]

    # 任一 helper 失败时必须撤销本轮所有前序稳定键替换。
    except Exception:

        # 按完整稳定键组恢复原对象或删除本轮新增键。
        for str_module_name in TUPLE_FIGURE_MODULE_NAMES:

            # 原先存在的键恢复为事务开始前的同一对象。
            if str_module_name in dict_original_modules:

                # 恢复附图 helper 的原始注册身份。
                sys.modules[str_module_name] = dict_original_modules[str_module_name]  # 原附图模块对象

            # 原先不存在的键必须删除，避免留下当前 root 的部分模块组。
            else:

                # 清除本轮事务新登记的附图 helper。
                sys.modules.pop(str_module_name, None)

        # 保留真实加载异常和 traceback，供调用方定位具体缺件。
        raise

# 按依赖顺序原子加载全部附图职责模块。
LIST_FIGURE_MODULES = load_figure_module_group()  # 已加载附图职责模块

# 收集拆分模块的全部非私有名称，完整恢复原入口公共 helper 面。
def collect_figure_compatibility() -> dict[str, Any]:
    """收集附图职责模块的公共兼容名称。

    参数：
    - 无。

    返回：
    - `dict[str, Any]`：原入口继续暴露的名称与对象。

    异常：
    - 无。
    """

    # 初始化兼容名称表，后加载模块沿用旧单文件覆盖顺序。
    dict_compatibility: dict[str, Any] = {}  # 附图入口兼容名称表

    # 按依赖顺序扫描已经加载的职责模块。
    for obj_figure_module in LIST_FIGURE_MODULES:

        # 逐项恢复非私有名称，兼容既有 helper import。
        for str_export_name in dir(obj_figure_module):

            # 私有实现细节不属于原入口公共面。
            if str_export_name.startswith("_"):

                # 跳过内部名称并检查下一个候选。
                continue

            # 读取当前公共名称对应的真实对象。
            obj_export_value = getattr(obj_figure_module, str_export_name)  # 当前兼容导出对象

            # 写入兼容表，保留后加载模块覆盖同名绑定的顺序。
            dict_compatibility[str_export_name] = obj_export_value  # 当前公共名称绑定

    # 返回完整兼容表供协调器一次性恢复。
    return dict_compatibility

# 生成旧入口公共 helper 的兼容绑定表。
DICT_FIGURE_COMPATIBILITY = collect_figure_compatibility()  # 旧入口公共绑定

# 把受控兼容表合入当前入口模块。
globals().update(DICT_FIGURE_COMPATIBILITY)

# 保留渲染模块对象，供兼容 wrapper 同步测试注入点。
MODULE_FIGURE_RENDERERS = sys.modules["readable_patent_figure_renderers"]  # PNG 渲染职责模块

# 保留布局模块对象，为绘制模块框 helper 注入圆角框构造职责。
MODULE_FIGURE_LAYOUT = sys.modules["readable_patent_figure_layout"]  # 字体与布局职责模块

# 恢复原单文件中布局 helper 对圆角框构造函数的直接调用关系。
MODULE_FIGURE_LAYOUT.build_rounded_box_patch = MODULE_FIGURE_RENDERERS.build_rounded_box_patch  # 布局层圆角框构造函数

# 保留工作流模块对象，供入口 wrapper 同步渲染兼容面。
MODULE_FIGURE_WORKFLOW = sys.modules["readable_patent_figure_workflow"]  # 附图编排职责模块

# 包装流程图 PNG 写入，保留旧入口上的 matplotlib backend monkeypatch 行为。
def write_flow_png(path_output_png: Path, list_steps: list[dict[str, str]]) -> None:
    """写出方法流程图 PNG。

    参数：
    - `path_output_png`：目标 PNG 路径。
    - `list_steps`：结构化方法步骤列表。

    返回：
    - `None`：文件写入完成后返回。

    异常：
    - 渲染失败时由职责模块继续上抛。
    """

    # 流程图调用前同步入口 backend 注入点，使 mock 仍作用于旧命名空间。
    MODULE_FIGURE_RENDERERS.load_matplotlib_backend = globals()["load_matplotlib_backend"]  # 流程图 backend 解析函数

    # 调用真实渲染实现并保持原返回语义。
    return MODULE_FIGURE_RENDERERS.write_flow_png(path_output_png, list_steps)

# 包装模块图 PNG 写入，保留旧入口上的 matplotlib backend monkeypatch 行为。
def write_module_png(path_output_png: Path, list_modules: list[dict[str, str]]) -> None:
    """写出系统模块图 PNG。

    参数：
    - `path_output_png`：目标 PNG 路径。
    - `list_modules`：结构化系统模块列表。

    返回：
    - `None`：文件写入完成后返回。

    异常：
    - 渲染失败时由职责模块继续上抛。
    """

    # 模块图调用前同步入口 backend 注入点，使 Pillow 回退测试仍可控。
    MODULE_FIGURE_RENDERERS.load_matplotlib_backend = globals()["load_matplotlib_backend"]  # 模块图 backend 解析函数

    # 交给模块图渲染器完成文件写入并透传其异常语义。
    return MODULE_FIGURE_RENDERERS.write_module_png(path_output_png, list_modules)

# 执行附图入口，并把兼容 wrapper 注入实际编排模块。
def main() -> int:
    """执行附图生成入口。

    参数：
    - 无。

    返回：
    - `int`：成功时返回零。

    异常：
    - 输入或写入失败时由职责模块继续上抛。
    """

    # 让工作流经由流程图 wrapper 调用 PNG 渲染，保留入口注入边界。
    MODULE_FIGURE_WORKFLOW.write_flow_png = write_flow_png  # 编排层流程图 PNG 写入函数

    # 把模块图 wrapper 写入编排层，确保两类 PNG 都接受入口 mock。
    MODULE_FIGURE_WORKFLOW.write_module_png = write_module_png  # 编排层模块图 PNG 写入函数

    # 调用拆分后的真实工作流并返回状态码。
    return MODULE_FIGURE_WORKFLOW.main()

# 直接执行入口时进入命令行主流程，导入场景不产生文件副作用。
if __name__ == "__main__":

    # 把主流程状态码交还操作系统。
    raise SystemExit(main())
