#!/usr/bin/env python3
"""提供安装包内稳定的命名能力预检入口。

stdout_protocol: json
当调用方使用 `--json` 时，stdout 只包含单个完整 JSON 对象。
"""

# 启用延迟注解，保持包装入口的类型行为稳定。
from __future__ import annotations

# 引入动态加载、路径与参数序列类型，使文件路径加载和 CLI 执行保持一致。
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence

# 固定同目录能力实现路径，安装副本不依赖仓库包结构。
PATH_CAPABILITY_PREFLIGHT = Path(__file__).resolve().with_name("capability_preflight.py")  # 命名能力实现路径

# 从相邻文件加载正式能力实现，兼容 CLI 和 importlib 文件加载。
def load_capability_module() -> ModuleType:
    """加载命名能力实现模块。

    参数：
    - 无。

    返回：
    - `ModuleType`：已经初始化的能力实现模块。

    异常：
    - `ImportError`：无法构造模块规格时抛出。
    """

    # 根据安装副本内真实路径构造模块规格。
    obj_spec = importlib.util.spec_from_file_location(  # 能力实现加载规格
        "readable_patent_capability_preflight",  # 隔离能力模块名
        PATH_CAPABILITY_PREFLIGHT,  # 安装副本内能力文件
    )

    # 缺少规格或加载器时拒绝继续，避免形成半初始化预检。
    if obj_spec is None or obj_spec.loader is None:

        # 抛出统一前缀错误，指向能力实现边界。
        raise ImportError("> ERR: [Python] 无法加载 capability_preflight.py。")

    # 根据有效规格创建能力实现模块。
    module_type_capability = importlib.util.module_from_spec(obj_spec)  # 能力实现模块对象

    # 执行能力实现代码，暴露正式探测合同。
    obj_spec.loader.exec_module(module_type_capability)

    # 返回已经初始化的能力模块。
    return module_type_capability

# 只加载一次能力实现，供公开兼容名称与 main 共用。
MODULE_CAPABILITY = load_capability_module()  # 当前安装副本能力实现模块

# 继续导出既有依赖入口常量，避免调用方迁移期间丢失单入口合同。
SINGLE_REQUIREMENTS_PATH = MODULE_CAPABILITY.SINGLE_REQUIREMENTS_PATH  # 唯一 requirements 入口

# 导出新版公开能力名称，供 pipeline 和测试读取。
CAPABILITY_NAMES = MODULE_CAPABILITY.CAPABILITY_NAMES  # 受支持能力名称

# 导出能力配置，便于只读诊断当前包与运行时边界。
CAPABILITY_SPECS = MODULE_CAPABILITY.CAPABILITY_SPECS  # 能力依赖合同

# 默认模块探测函数保持可替换，支持确定性测试缺失场景。
has_module = MODULE_CAPABILITY.has_module  # Python 模块规格探测函数

# 导出单项能力构造函数，保留直接调用兼容性。
build_capability_status = MODULE_CAPABILITY.build_capability_status  # 单项能力状态构造函数

# 导出完整报告函数，供 pipeline 在同进程内复用。
build_report = MODULE_CAPABILITY.build_report  # 完整能力报告构造函数

# 保留既有公开 main 名称，把全部行为交给命名能力实现。
def main(argv: Sequence[str] | None = None) -> int:
    """执行命名能力预检。

    参数：
    - `argv`：可选命令行参数；为 `None` 时读取进程参数。

    返回：
    - `int`：选中能力就绪或仅诊断时为 0，缺少选中能力时为 1。

    异常：
    - 参数和能力配置错误由正式能力实现处理。
    """

    # 调用同目录能力实现，确保 source、dist 与 installed 行为一致。
    return MODULE_CAPABILITY.main(argv, has_module)

# 直接执行包装脚本时把正式入口返回值交给解释器。
if __name__ == "__main__":

    # 保持命令行退出语义与 main 一致。
    raise SystemExit(main())
