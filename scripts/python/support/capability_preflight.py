#!/usr/bin/env python3
"""按命名能力检查 Python 包与外部运行时是否共同就绪。

stdout_protocol: json
当调用方选择 JSON 输出时，stdout 只包含单个完整 JSON 对象。
"""

# 启用延迟注解，保持受支持 Python 版本间的类型行为一致。
from __future__ import annotations

# 引入参数解析、模块探测、平台识别、序列化和注册表检查能力。
import argparse
import importlib.util
import json
import platform
import sys

# 路径用于验证生产入口仍位于当前 source、dist 或 installed 技能根。
from pathlib import Path

# 类型合同覆盖配置载荷、可注入探针和 CLI 参数序列。
from typing import Any
from typing import Callable
from typing import Sequence

# 固定正式技能唯一依赖入口，所有能力安装提示都回到同一文件。
SINGLE_REQUIREMENTS_PATH = "requirements.txt"  # 正式技能唯一依赖入口

# 当前文件位于 scripts/python/support，向上三级得到可迁移技能根。
PATH_SKILL_ROOT = Path(__file__).resolve().parents[3]  # 当前能力声明所属技能根目录

# 能力名称是公开 CLI 合同，顺序同时决定无选择诊断报告的稳定顺序。
CAPABILITY_NAMES = (  # 受支持能力名称序列
    "core-model",  # Model 4 与 Claims 3 的 JSON Schema 验证
    "office-intake",  # DOCX、PPTX 等 Office 材料读取
    "pdf-intake",  # PDF 材料读取
    "figures",  # 技术附图生成
    "formula-omml",  # 原生可编辑 Office 公式
    "native-mathtype",  # Windows Word 中的 MathType OLE 公式
    "cnipa-search",  # CNIPA 浏览器检索
    "test",  # 开发测试
)  # 能力名称稳定序列

# 每项能力只声明真实必需模块，不把其他未使用能力混入阻断判断。
CAPABILITY_SPECS: dict[str, dict[str, Any]] = {  # 能力到依赖合同的映射
    "core-model": {  # 结构化模型验证能力
        "packages": ("jsonschema",),  # Draft 2020-12 Schema 执行依赖
        "runtime_probe": "",  # 纯 Python 能力不需要额外运行时
        "note": "Model 4.0 与 Claims Map 3.0 的正式 JSON Schema 验证。",  # 能力用途
    },
    "office-intake": {  # Office 材料读取能力
        "packages": ("docx", "pptx"),  # 当前 DOCX 和 PPTX 生产入口实际导入模块
        "runtime_probe": "",  # 解析 Office 文件不依赖桌面应用
        "required_files": (),  # 包探测已经覆盖当前生产实现
        "note": "DOCX、PPTX 等 Office 研究材料读取。",  # Office 输入边界说明
    },
    "pdf-intake": {  # 便携文档独立解析分组
        "packages": ("pypdf",),  # PDF 文本读取模块
        "runtime_probe": "",  # 本地 PDF 解析不依赖外部程序
        "note": "PDF 研究材料读取。",  # 不与 Office 解析合并的输入约束
    },
    "figures": {  # 技术附图能力
        "packages": ("matplotlib",),  # 位图附图渲染模块
        "runtime_probe": "",  # SVG 主链和 Matplotlib 包即可完成当前图件
        "note": "技术附图的 SVG 与位图输出。",  # 图件输出边界说明
    },
    "formula-omml": {  # Office 原生公式能力
        "packages": ("docx", "latex2mathml", "mathml2omml"),  # LaTeX 到 OMML 转换链
        "runtime_probe": "",  # OMML 不需要启动 Word
        "note": "可编辑 Office OMML 公式生成。",  # Office 公式边界说明
    },
    "native-mathtype": {  # MathType 原生对象能力
        "packages": ("docx", "latex2mathml", "pythoncom", "win32clipboard", "win32com"),  # MathType OLE 真实导入闭包
        "runtime_probe": "windows-word-mathtype",  # Windows 注册运行时探针
        "required_files": (),  # 桌面运行时由专用探针确认
        "note": "Windows Word 中的 Equation.DSMT4 原生 MathType OLE。",  # MathType 桌面边界说明
    },
    "cnipa-search": {  # CNIPA 在线检索能力
        "packages": (),  # 公共在线入口只使用标准库 urllib
        "runtime_probe": "",  # 当前实现不要求浏览器或第三方运行时
        "required_files": (  # 防止依赖声明存在但生产入口已经断链
            "scripts/python/search/cnipa_epub_search.py",  # 在线检索与结构化解析入口
            "scripts/python/search/cnipa_epub_crawler.py",  # urllib 远端抓取实现
        ),
        "note": "通过标准库 urllib 执行 CNIPA 在线检索与页面读取。",  # 在线检索边界说明
    },
    "test": {  # 项目测试能力
        "packages": ("pytest",),  # 完整测试入口
        "runtime_probe": "",  # 测试能力不需要额外桌面运行时
        "note": "技能开发与回归测试。",  # 开发验证边界说明
    },
}  # 能力依赖合同映射

# 构造命令行解析器，提供可重复能力选择和稳定 JSON 输出。
def build_parser() -> argparse.ArgumentParser:
    """构造能力预检参数解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已经注册能力选择与输出开关的解析器。

    异常：
    - 无。
    """

    # 使用简短说明明确该入口检查的是能力而不是全量强制依赖。
    str_description = "Check named capability package and runtime readiness."  # CLI 用途说明

    # 创建能力预检参数解析器。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 能力预检解析器

    # 注册可重复能力选择；省略时只诊断全部能力而不强制可选项。
    obj_parser.add_argument(
        "--capability",
        action="append",
        choices=CAPABILITY_NAMES,
        default=[],
        help="Required capability; repeat to select multiple groups.",
    )

    # 注册机器协议开关，输出形态不得改变能力失败退出码。
    obj_parser.add_argument("--json", action="store_true", help="Output raw JSON only.")

    # 返回已经配置完成的解析器。
    return obj_parser

# 检查模块规格是否存在，避免为普通包探测执行导入副作用。
def has_module(str_module_name: str) -> bool:
    """检查 Python 模块是否可定位。

    参数：
    - `str_module_name`：需要探测的导入模块名。

    返回：
    - `bool`：模块规格存在时返回 `True`。

    异常：
    - 探测异常被转换为不可用状态。
    """

    # 捕获无效模块规格和父包导入失败，保证预检总能形成结构化结果。
    try:

        # 仅查询模块规格，不执行目标模块代码。
        return importlib.util.find_spec(str_module_name) is not None

    # 已知规格错误都表示当前解释器不能可靠使用该模块。
    except (AttributeError, ImportError, ValueError):

        # 返回不可用，由能力报告列出缺失模块。
        return False

# 检查 Windows 注册表中的 Word 与 MathType ProgID 是否同时存在。
def probe_windows_word_mathtype() -> dict[str, Any]:
    """检查原生 MathType 所需 Windows 桌面运行时。

    参数：
    - 无。

    返回：
    - `dict[str, Any]`：包含平台、Word 和 MathType 注册状态。

    异常：
    - 注册表读取异常被转换为未就绪状态。
    """

    # 先判断平台，非 Windows 环境不尝试导入注册表模块。
    bool_windows = platform.system() == "Windows"  # 当前解释器是否运行在 Windows

    # 非 Windows 无法提供 Word COM 和 MathType OLE。
    if not bool_windows:

        # 返回完整运行时明细，避免把平台缺口误报成 Python 包缺失。
        return {
            "ready": False,  # 原生 MathType 运行时不可用
            "platform": platform.system(),  # 当前操作系统名称
            "word_registered": False,  # 当前平台无法提供 Word COM
            "mathtype_registered": False,  # MathType OLE 类无法在本平台注册
            "missing": ["windows", "Word.Application", "Equation.DSMT4"],  # 运行时缺口
        }

    # Windows 注册表模块仅在平台确认后导入。
    import winreg

    # ProgID 通过 CLSID 映射存在即可证明对应 COM 类已注册。
    dict_registration = {  # 两个桌面运行时的注册状态
        "Word.Application": False,  # Word 自动化类尚未确认
        "Equation.DSMT4": False,  # MathType 公式类尚未确认
    }

    # 逐项读取 ProgID 的 CLSID，任何访问失败都保留为未注册。
    for str_program_id in dict_registration:

        # 注册表访问失败不抛出堆栈，而是进入结构化缺口列表。
        try:

            # 查询 ProgID 默认 CLSID 值，存在即视为已注册。
            winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, f"{str_program_id}\\CLSID")

            # 记录当前桌面程序已经注册。
            dict_registration[str_program_id] = True  # 当前 ProgID 注册状态

        # 缺少注册键或访问失败都表示当前运行时未就绪。
        except OSError:

            # 保持初始 False，继续检查另一项以形成完整诊断。
            continue

    # 收集未注册程序，供阻断报告精确说明缺口。
    list_missing = [  # 当前 Windows 运行时缺失项
        str_program_id  # 未注册的桌面程序标识
        for str_program_id, bool_registered in dict_registration.items()  # 遍历全部必需 ProgID
        if not bool_registered  # 只保留未注册项
    ]

    # 返回平台和两项注册状态，包就绪与运行时就绪保持分离。
    return {
        "ready": not list_missing,  # 两项 ProgID 均注册时运行时就绪
        "platform": platform.system(),  # 桌面运行时所在平台
        "word_registered": dict_registration["Word.Application"],  # Word 自动化类最终状态
        "mathtype_registered": dict_registration["Equation.DSMT4"],  # MathType 公式类最终状态
        "missing": list_missing,  # 未注册桌面运行时
    }

# 按能力声明选择对应外部运行时探针。
def probe_runtime(str_probe_name: str) -> dict[str, Any]:
    """执行能力声明的外部运行时探针。

    参数：
    - `str_probe_name`：能力配置中的探针名称。

    返回：
    - `dict[str, Any]`：统一含有 `ready` 和 `missing` 的运行时状态。

    异常：
    - 未知探针名称抛出 `ValueError`，阻止配置漂移。
    """

    # 空探针表示该能力没有包以外的运行时前置条件。
    if not str_probe_name:

        # 返回显式就绪状态，避免调用方猜测空字段语义。
        return {"ready": True, "missing": []}

    # Windows Word 与 MathType 使用注册表探针。
    if str_probe_name == "windows-word-mathtype":

        # 返回桌面程序注册状态。
        return probe_windows_word_mathtype()

    # 未知探针代表能力配置与实现脱节，必须立即阻断。
    raise ValueError(f"> ERR: [Python] 未知能力运行时探针：{str_probe_name}")

# 构造单项能力状态，分别保留包和外部运行时证据。
def build_capability_status(
    str_capability: str,
    func_module_probe: Callable[[str], bool] = has_module,
) -> dict[str, Any]:
    """构造单项能力就绪状态。

    参数：
    - `str_capability`：公开能力名称。
    - `func_module_probe`：可替换的模块规格探测函数。

    返回：
    - `dict[str, Any]`：包含包、运行时、缺口和安装入口的能力状态。

    异常：
    - 能力名称未知时抛出 `KeyError`。
    """

    # 读取当前能力声明，未知名称由映射访问直接阻断。
    dict_spec = CAPABILITY_SPECS[str_capability]  # 当前能力依赖声明

    # 按声明顺序探测全部 Python 模块。
    dict_packages = {  # 当前能力逐模块状态
        str_package: func_module_probe(str_package)  # 当前模块是否可定位
        for str_package in dict_spec["packages"]  # 遍历当前能力必需模块
    }

    # 收集当前能力缺失模块，供退出报告和安装提示使用。
    list_missing_packages = [  # 当前能力缺失模块
        str_package  # 未通过探测的模块名
        for str_package, bool_available in dict_packages.items()  # 遍历逐模块状态
        if not bool_available  # 只保留不可定位模块
    ]

    # 生产入口路径属于能力闭包，文件断链不能被标准库或已安装包掩盖。
    dict_files = {  # 当前能力所需生产入口存在性
        str_relative_path: (PATH_SKILL_ROOT / str_relative_path).is_file()  # 安装副本内入口是否存在
        for str_relative_path in dict_spec.get("required_files", ())  # 遍历显式生产入口
    }

    # 收集断开的生产入口，供 source、dist 和 installed copy 同构诊断。
    list_missing_files = [  # 当前能力缺失生产入口
        str_relative_path  # 技能根相对入口路径
        for str_relative_path, bool_exists in dict_files.items()  # 遍历生产入口状态
        if not bool_exists  # 只保留已经断链的入口
    ]

    # 包未就绪时不执行可能依赖这些包的外部运行时探针。
    if list_missing_packages or list_missing_files:

        # 明确标记运行时因闭包不完整未执行，避免报告把它误称为成功。
        dict_runtime = {
            "ready": False,  # 包或生产入口缺失时能力整体不可用
            "checked": False,  # 外部探针尚未执行
            "missing": [],  # 运行时缺口未知而不是空缺口
            "skip_reason": "incomplete_production_closure",  # 探针跳过原因
        }

    # 包齐全时执行能力声明的运行时探针。
    else:

        # 获取外部运行时状态。
        dict_runtime = probe_runtime(str(dict_spec["runtime_probe"]))  # 当前能力运行时状态

        # 标记外部探针已经实际执行，区别于包缺失跳过。
        dict_runtime["checked"] = True  # 包齐全后已实际执行运行时检查

    # 包和运行时必须同时就绪，单独安装包不能形成假绿。
    bool_available = (  # 当前能力最终状态
        not list_missing_packages  # 所需 Python 模块全部可定位
        and not list_missing_files  # 声明的生产入口全部存在
        and bool(dict_runtime["ready"])  # 外部运行时探针已经就绪
    )

    # 返回对 source、dist 和 installed copy 稳定的能力状态结构。
    return {
        "capability": str_capability,  # 公开能力名称
        "available": bool_available,  # 包与运行时共同就绪状态
        "requirements": SINGLE_REQUIREMENTS_PATH,  # 唯一依赖安装入口
        "packages": dict_packages,  # Python 包探测证据
        "files": dict_files,  # 生产入口存在性证据
        "runtime": dict_runtime,  # 外部运行时探测证据
        "missing_packages": list_missing_packages,  # 缺失 Python 模块
        "missing_files": list_missing_files,  # 缺失生产入口
        "note": str(dict_spec["note"]),  # 当前能力用途
    }

# 汇总全部能力，同时只把调用方显式选择项纳入阻断结果。
def build_report(
    list_selected_capabilities: Sequence[str],
    func_module_probe: Callable[[str], bool] = has_module,
) -> dict[str, Any]:
    """构造完整能力预检报告。

    参数：
    - `list_selected_capabilities`：调用方本轮真正需要的能力名称。
    - `func_module_probe`：可替换的模块规格探测函数。

    返回：
    - `dict[str, Any]`：包含全部诊断和选中项阻断结论的报告。

    异常：
    - 能力配置错误时由下层函数上抛。
    """

    # 去重但保留调用顺序，重复 --capability 不产生重复阻断。
    list_selected = list(dict.fromkeys(list_selected_capabilities))  # 本轮选中能力稳定序列

    # 无论是否选择能力都诊断全部分组，帮助人工查看可选能力状态。
    dict_capabilities = {  # 全部能力状态映射
        str_capability: build_capability_status(str_capability, func_module_probe)  # 当前能力状态
        for str_capability in CAPABILITY_NAMES  # 按公开稳定顺序诊断
    }

    # 只收集显式选中且未就绪的能力，未使用可选项不得阻断。
    list_missing_selected = [  # 本轮真正阻断的能力名称
        str_capability  # 当前选中但未就绪的能力
        for str_capability in list_selected  # 遍历调用方显式选择
        if not dict_capabilities[str_capability]["available"]  # 只保留未就绪项
    ]

    # 返回能力级报告，同时保留 python_groups 兼容别名供既有调用方迁移。
    return {
        "requirements_entry": SINGLE_REQUIREMENTS_PATH,  # 唯一 requirements 入口
        "selected_capabilities": list_selected,  # 本轮强制能力
        "missing_selected": list_missing_selected,  # 本轮阻断能力
        "ready": not list_missing_selected,  # 选中能力是否全部就绪
        "capabilities": dict_capabilities,  # 新版能力状态映射
        "python_groups": dict_capabilities,  # 既有单入口测试的兼容映射
    }

# 根据报告输出简短人工摘要，不把完整结构化载荷混入终端。
def write_human_summary(dict_report: dict[str, Any]) -> None:
    """输出能力预检人工摘要。

    参数：
    - `dict_report`：已经完成探测的能力报告。

    返回：
    - `None`：摘要写入 stdout。

    异常：
    - 标准输出异常由底层接口上抛。
    """

    # 统计当前环境全部就绪能力，便于无选择诊断快速浏览。
    int_ready_count = sum(  # 当前环境就绪能力数量
        1  # 每个就绪能力计为一项
        for dict_status in dict_report["capabilities"].values()  # 遍历全部能力状态
        if dict_status["available"]  # 只统计完全就绪能力
    )

    # 输出能力总数与就绪数，完整细节留给 JSON 模式。
    print(
        "> INFO: [Python] "
        f"能力预检完成：{int_ready_count}/{len(CAPABILITY_NAMES)} 项就绪，"
        f"唯一依赖入口为 {SINGLE_REQUIREMENTS_PATH}。"
    )

    # 只有显式选择能力时才输出强制检查结论。
    if dict_report["selected_capabilities"]:

        # 选中能力存在缺口时输出警告摘要。
        if dict_report["missing_selected"]:

            # 只列能力名称，不向终端倾倒完整包与运行时报告。
            str_missing = ", ".join(dict_report["missing_selected"])  # 选中但未就绪的能力摘要

            # 告知调用方本轮会被阻断。
            print(f"> WARNING: [Python] 选中能力未就绪：{str_missing}。")

        # 所有选中能力就绪时输出通过摘要。
        else:

            # 明确本轮要求已经满足。
            print("> INFO: [Python] 本轮选中能力全部就绪。")

# 执行能力预检公开入口，保持 JSON 与人工输出相同的退出语义。
def main(
    argv: Sequence[str] | None = None,
    func_module_probe: Callable[[str], bool] = has_module,
) -> int:
    """执行能力预检 CLI。

    参数：
    - `argv`：可选参数序列；为 `None` 时读取进程参数。
    - `func_module_probe`：模块规格探测函数，测试可注入确定性替身。

    返回：
    - `int`：选中能力全部就绪或未选择时返回 0，否则返回 1。

    异常：
    - 参数错误由 `argparse` 处理，配置错误由下层上抛。
    """

    # 解析可重复能力选择与输出模式。
    namespace_arguments = build_parser().parse_args(argv)  # 当前预检参数

    # 对全部能力形成诊断，但只让显式选中项参与最终退出状态。
    dict_report = build_report(namespace_arguments.capability, func_module_probe)  # 当前能力预检报告

    # JSON 模式只改变输出形态，不改变缺能力退出码。
    if namespace_arguments.json:

        # 单次写出完整 JSON 对象，供 pipeline 和自动化门禁消费。
        json.dump(dict_report, sys.stdout, ensure_ascii=False, indent=2)

        # 补写换行，保持命令行协议完整。
        sys.stdout.write("\n")

    # 普通模式只输出简短人类可读摘要。
    else:

        # 汇报本轮能力数量与阻断状态。
        write_human_summary(dict_report)

    # 选中能力有缺口时返回一，否则无选择诊断和全就绪均返回零。
    return 0 if dict_report["ready"] else 1

# 直接执行时把公开入口返回值交给解释器。
if __name__ == "__main__":

    # 保持命令行退出语义与 main 一致。
    raise SystemExit(main())
