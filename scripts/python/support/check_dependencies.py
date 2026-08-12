#!/usr/bin/env python3
"""报告单一 requirements 安装入口下的依赖就绪状态。

stdout_protocol: json
当使用 `--json` 时，本模块的 CLI stdout 是 machine-readable stdout protocol；调用方依赖完整 JSON 对象读取依赖检查结果。
"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、模块探测、序列化和本地命令探测能力。
import argparse
import importlib.util
import json
import shutil
import sys
from typing import Any

# 固定正式 skill 唯一允许的依赖入口路径，所有安装说明都应回到这里。
SINGLE_REQUIREMENTS_PATH = "requirements.txt"  # 正式 skill 唯一依赖入口

# 固定各能力域对应的依赖探测清单，便于统一输出 readiness 报告。
PYTHON_GROUPS: dict[str, dict[str, Any]] = {  # Python 依赖分组说明字典
    "core": {  # 正式主链标准库分组
        "packages": [],  # 主链标准库场景不需要额外第三方包
        "note": "正式主链只依赖 Python 3.10+ 标准库。",  # 主链依赖说明
    },
    "office_pdf": {  # Office 与 PDF 能力分组
        "packages": ["docx", "mammoth", "pptx", "pypdf"],  # Office/PDF 相关可选包
        "note": "Office/PDF 转换和 Word 导出增强能力。",  # Office/PDF 依赖说明
    },
    "render": {  # 渲染增强分组
        "packages": ["matplotlib"],  # 技术附图渲染相关可选包
        "note": "技术附图的位图渲染增强能力，不用于公式。",  # 附图渲染依赖说明
    },
    "equations": {  # Office 原生公式强制依赖分组
        "packages": ["latex2mathml", "mathml2omml"],  # LaTeX 到 OMML 的纯 Python 转换链
        "note": "Office 原生可编辑公式转换；缺失时必须阻断 DOCX 导出。",  # 公式转换依赖说明
    },
    "mathtype": {  # Windows 原生 MathType OLE 可选能力分组
        "packages": ["pythoncom", "win32clipboard", "win32com"],  # pywin32 暴露的 COM 模块
        "note": "MathType 模式还要求 Windows、Word 和 Equation.DSMT4 OLE 注册。",  # MathType 环境说明
    },
    "search": {  # CNIPA 检索增强分组
        "packages": ["playwright"],  # 检索增强相关可选包
        "note": "CNIPA 浏览器检索增强能力；安装后仍需 playwright 浏览器运行时。",  # 检索依赖说明
    },
    "test": {  # Python 测试增强分组
        "packages": ["pytest"],  # 测试增强相关可选包
        "note": "更完整的 Python 测试增强能力。",  # 测试依赖说明
    },
}  # Python 依赖分组说明

# 构造命令行参数解析器，统一声明 JSON 协议输出开关。
def parse_arguments() -> argparse.Namespace:
    """解析命令行参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含 JSON 输出开关的参数对象。

    异常：
    - 参数非法时由 `argparse` 自动结束进程。
    """

    # 先准备命令行说明文本，避免解析器定义行过长。
    str_description = "Check dependency readiness under the single governed requirements entry."  # 依赖检查入口说明文本

    # 初始化当前依赖检查入口的命令行解析器。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 依赖检查命令行解析器

    # 注册 JSON 输出开关，供上游程序直接消费结构化检查结果。
    obj_parser.add_argument("--json", action="store_true", help="Output raw JSON only.")  # JSON 输出开关

    # 返回解析后的参数对象，供主流程决定输出格式。
    return obj_parser.parse_args()

# 检查模块是否可以导入，供依赖组状态汇总逻辑复用。
def has_module(str_name: str) -> bool:
    """检查模块是否可导入。

    参数：
    - `str_name`：待检查的模块名。

    返回：
    - `bool`：模块可导入时返回 `True`，否则返回 `False`。

    异常：
    - 模块探测过程中的导入异常被吞掉并转换为 `False`。
    """

    # 尝试读取模块规格，避免真正执行模块导入副作用。
    try:

        # 根据模块规格是否存在判断模块是否可导入。
        return importlib.util.find_spec(str_name) is not None

    # 把模块探测异常转成不可用结果，保证依赖检查入口稳定返回报告。
    except (ImportError, ValueError, AttributeError):

        # 在模块规格探测失败时返回 False，由上游报告缺失模块。
        return False

# 构造单个依赖组的就绪状态，统一给出安装入口和缺失包列表。
def build_group_status(dict_group_spec: dict[str, Any]) -> dict[str, Any]:
    """构造单个依赖组的就绪状态。

    参数：
    - `dict_group_spec`：单个依赖组的配置字典。

    返回：
    - `dict[str, Any]`：包含可用性、缺失包、安装入口和说明的状态字典。

    异常：
    - 无。
    """

    # 读取当前依赖组声明的模块列表，供后续逐个探测。
    list_packages = list(dict_group_spec["packages"])  # 当前依赖组模块列表

    # 准备逐模块探测结果字典，后续按顺序记录每个模块是否可导入。
    dict_package_status: dict[str, bool] = {}  # 当前依赖组的逐模块探测结果字典

    # 逐个探测当前依赖组模块，形成稳定的可导入状态明细。
    for str_package in list_packages:

        # 记录当前模块是否可导入，供最终报告按包名回传结果。
        dict_package_status[str_package] = has_module(str_package)  # 当前模块可导入状态

    # 准备缺失模块列表，后续只收集探测失败的模块名。
    list_missing_packages: list[str] = []  # 当前依赖组缺失模块列表

    # 逐个检查探测结果，把不可导入的模块加入缺失列表。
    for str_package, bool_available in dict_package_status.items():

        # 在当前模块不可导入时登记其模块名，供安装提示直接复用。
        if not bool_available:

            # 把当前缺失模块名加入列表，便于最终报告输出安装建议。
            list_missing_packages.append(str_package)  # 已登记的缺失模块名

    # 组装依赖组状态字典，统一回填唯一 requirements 安装入口。
    dict_group_status = {  # 当前依赖组状态字典
        "requirements": SINGLE_REQUIREMENTS_PATH,  # 唯一依赖入口路径
        "available": not list_missing_packages,  # 当前依赖组是否全部就绪
        "packages": dict_package_status,  # 交给上游展示的逐模块探测明细
        "missing": list_missing_packages,  # 直接用于安装提示的缺失模块名
        "install": "" if not list_missing_packages else f"pip install -r {SINGLE_REQUIREMENTS_PATH}",  # 当前依赖组统一安装命令
        "note": dict_group_spec["note"],  # 当前依赖组说明文本
    }

    # 在当前依赖组包含 playwright 时补充浏览器运行时安装提示。
    if "playwright" in list_packages:

        # 记录 playwright 浏览器运行时后置安装步骤，避免只装 Python 包还不能运行。
        dict_group_status["post_install_steps"] = [  # playwright 浏览器运行时安装步骤
            "python -m playwright install chromium",  # playwright 浏览器运行时安装命令
        ]

    # 返回当前依赖组状态字典，供汇总报告统一收集。
    return dict_group_status

# 汇总所有 Python 依赖组和本地增强工具状态，形成最终检查报告。
def build_report() -> dict[str, Any]:
    """构造依赖检查报告。

    参数：
    - 无。

    返回：
    - `dict[str, Any]`：完整依赖检查报告字典。

    异常：
    - 无。
    """

    # 准备各依赖组状态字典，后续逐组写入统一报告对象。
    dict_python_groups: dict[str, dict[str, Any]] = {}  # 各 Python 依赖组状态字典

    # 逐组生成依赖状态，保持报告里每个分组都有显式状态块。
    for str_group_name, dict_group_spec in PYTHON_GROUPS.items():

        # 把当前依赖组状态写入报告字典，供 JSON 输出模式直接复用。
        dict_python_groups[str_group_name] = build_group_status(dict_group_spec)  # 当前依赖组状态

    # 探测 Node 运行时是否可用，供浏览器增强说明使用。
    bool_node_ready = shutil.which("node") is not None  # Node 运行时是否可用

    # 探测 npx 是否可用，供 Mermaid 等本地增强命令说明使用。
    bool_npx_ready = shutil.which("npx") is not None  # npx 命令执行器是否可用

    # 探测 Mermaid CLI 是否可用，供附图增强渲染说明使用。
    bool_mermaid_cli_ready = shutil.which("mmdc") is not None  # Mermaid CLI 渲染器是否可用

    # 组装可选增强状态字典，统一记录非 Python 运行时工具可用性。
    dict_optional_enhancements = {  # 非 Python 本地增强状态字典
        "node": bool_node_ready,  # 浏览器增强是否具备 Node 运行时
        "npx": bool_npx_ready,  # 本地包命令执行是否具备 npx
        "mermaid_cli": bool_mermaid_cli_ready,  # 附图增强是否具备 Mermaid CLI
        "note": "Node/Mermaid 仅作为本地增强说明，不再使用独立 requirements 或 tools 目录。",  # 本地增强说明文本
    }

    # 把依赖入口、分组状态和本地增强状态封装成统一报告对象。
    dict_report = {
        "requirements_entry": SINGLE_REQUIREMENTS_PATH,  # 唯一 requirements 安装入口路径
        "python_groups": dict_python_groups,  # 分组级依赖状态映射
        "optional_enhancements": dict_optional_enhancements,  # 本地增强工具状态字典
    }  # 供 JSON 协议和摘要模式复用的完整依赖检查报告

    # 返回完整依赖检查报告，供 JSON 协议和摘要输出模式共同复用。
    return dict_report

# 执行依赖检查入口，按需要输出 JSON 协议或简短状态摘要。
def main() -> int:
    """执行依赖检查入口。

    参数：
    - 无。

    返回：
    - `int`：成功完成依赖检查时返回 `0`。

    异常：
    - 标准输出写入失败时由底层异常上抛。
    """

    # 解析命令行参数，确定当前调用方需要 JSON 还是人类可读摘要。
    namespace_arguments = parse_arguments()  # 依赖检查入口参数

    # 生成依赖检查报告对象，供 JSON 协议分支和摘要分支共同复用。
    dict_report = build_report()  # 当前环境的依赖检查报告对象

    # 在调用方要求 JSON 协议时直接输出完整报告对象。
    if namespace_arguments.json:

        # 以单次 JSON dump 输出完整检查报告，供上游程序直接解析。
        json.dump(dict_report, sys.stdout, ensure_ascii=False, indent=2)

        # 返回成功状态码，表示 JSON 协议输出已经完成。
        return 0

    # 统计依赖分组总数，供终端输出简短进度摘要。
    int_group_count = len(dict_report["python_groups"])  # 依赖分组总数

    # 先把缺失分组计数清零，后续逐组累计尚未就绪的依赖分组数量。
    int_missing_group_count = 0  # 尚未就绪的依赖分组数量

    # 逐组检查依赖状态，只对未就绪分组累加计数。
    for dict_group in dict_report["python_groups"].values():

        # 在当前分组尚未就绪时递增计数，供统一安装提醒使用。
        if not dict_group["available"]:

            # 把未就绪分组计数加一，统计还需要安装的依赖分组数量。
            int_missing_group_count += 1  # 已累计的未就绪分组数量

    # 先汇报唯一依赖入口与总分组数，明确本脚本只认一个 requirements 文件。
    print(
        "> INFO: [Python] "
        f"依赖检查完成，唯一入口为 {SINGLE_REQUIREMENTS_PATH}，共检查 {int_group_count} 个分组。"
    )

    # 在仍有缺失分组时给出统一安装提醒，避免终端直接输出结构化明细。
    if int_missing_group_count:

        # 汇报缺失分组数量和统一安装入口，详细明细交给 JSON 模式输出。
        print(
            "> INFO: [Python] "
            f"当前仍有 {int_missing_group_count} 个分组未就绪；请执行 pip install -r {SINGLE_REQUIREMENTS_PATH}，详细明细请改用 --json。"
        )

    # 在所有分组均已就绪时给出简短通过提示。
    else:

        # 汇报所有依赖分组都已就绪，表示单一依赖入口已满足当前环境。
        print("> INFO: [Python] 所有依赖分组均已就绪。")

    # 取出本地增强状态字典，供后续统计当前可用的增强工具数量。
    dict_optional = dict_report["optional_enhancements"]  # 当前环境的本地增强状态字典

    # 先把可用增强工具计数清零，后续逐项累加当前环境可用的增强工具数量。
    int_optional_ready_count = 0  # 当前可用的本地增强工具数量

    # 逐项检查本地增强状态，只对可用工具递增统计计数。
    for str_key in ("node", "npx", "mermaid_cli"):

        # 在当前增强工具可用时递增计数，供最后的摘要提示使用。
        if dict_optional[str_key]:

            # 把可用增强工具计数加一，统计当前环境的可用增强数量。
            int_optional_ready_count += 1  # 已累计的可用增强工具数量

    # 汇报本地增强工具检查结果，只输出摘要数量而不输出结构化明细。
    print(
        "> INFO: [Python] "
        f"本地增强检查完成，当前共有 {int_optional_ready_count} 项增强工具可用。"
    )

    # 返回成功状态码，表示依赖检查入口已经完成。
    return 0

# 保留标准命令行入口，方便直接执行依赖检查脚本。
if __name__ == "__main__":

    # 使用 main 的返回值作为进程退出码，保持 CLI 行为一致。
    raise SystemExit(main())
