#!/usr/bin/env python3
"""准备正文修订稿并登记本地迭代日志。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、模块加载、文件复制和路径能力。
import argparse
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Any

# 固定共享运行时支持模块路径，供当前迭代入口按文件路径惰性加载公共工具。
PATH_RUNTIME_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "runtime_support.py"  # 共享运行时支持模块路径

# 按文件路径加载共享运行时支持模块，避免导入时修改 sys.path。
def load_runtime_support_module() -> Any:
    """加载共享运行时支持模块。

    参数：
    - 无。

    返回：
    - `Any`：已经执行源码的共享运行时支持模块对象。

    异常：
    - 支持模块缺失或无法加载时抛出 `ImportError`。
    """

    # 先根据支持模块文件路径构造模块加载规格。
    obj_spec = importlib.util.spec_from_file_location("readable_patent_runtime_support", PATH_RUNTIME_SUPPORT)  # 共享支持模块加载规格

    # 在加载规格或 loader 缺失时立即报错，避免后续出现难以定位的空对象异常。
    if obj_spec is None or obj_spec.loader is None:

        # 抛出明确导入错误，提醒调用方检查 support/runtime_support.py 是否存在。
        raise ImportError("> ERR: [Python] 无法加载 support/runtime_support.py。")

    # 根据加载规格创建临时模块对象，供后续执行共享支持模块源码。
    module_runtime_support = importlib.util.module_from_spec(obj_spec)  # 临时共享支持模块对象

    # 执行共享支持模块源码，把公共路径和文件工具装入临时模块对象。
    obj_spec.loader.exec_module(module_runtime_support)  # 已执行源码的共享支持模块

    # 返回已加载的共享支持模块，供修订稿和日志流程复用。
    return module_runtime_support

# 构造命令行参数解析器，统一声明 prepare 和 log 两个子命令。
def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已注册子命令和参数的解析器对象。

    异常：
    - 无。
    """

    # 先准备解析器说明文本，避免初始化语句过长。
    str_description = "Prepare or log disclosure iterations under the governed draft directory."  # 迭代入口说明文本

    # 初始化当前迭代入口的命令行解析器。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 迭代入口命令行解析器

    # 创建子命令容器，要求调用方显式选择 prepare 或 log。
    obj_subparsers = obj_parser.add_subparsers(dest="command", required=True)  # 迭代入口子命令容器

    # 创建 prepare 子命令解析器，用于复制新的修订草稿工作副本。
    obj_prepare_parser = obj_subparsers.add_parser("prepare", help="Create a timestamped revision draft.")  # prepare 子命令解析器

    # prepare 子命令必须显式给出案件目录，确保修订稿仍然写回当前案件空间。
    obj_prepare_parser.add_argument("--case-dir", required=True)  # prepare 案件目录参数

    # prepare 子命令允许补传输入草稿路径，用来覆盖自动定位逻辑。
    obj_prepare_parser.add_argument("--input")  # prepare 输入草稿参数

    # prepare 子命令允许携带修订请求文本，便于同步生成请求说明单。
    obj_prepare_parser.add_argument("--request")  # prepare 修订请求参数

    # 单独创建日志解析器，用于向 revision_log.md 追加一条新记录。
    obj_log_parser = obj_subparsers.add_parser("log", help="Append a revision log entry.")  # 负责登记 revision_log.md 的子命令解析器

    # 日志写入仍需案件目录，避免把 revision_log.md 追加到错误案件。
    obj_log_parser.add_argument("--case-dir", required=True)  # 绑定日志归属案件目录的必填参数

    # 允许记录入口类型字段，后续可区分修订、评审或人工补录场景。
    obj_log_parser.add_argument("--kind", default="revision")  # 区分 revision 或 review 的日志类型参数

    # 允许补记最初的修改诉求，便于回看为什么会触发这次迭代。
    obj_log_parser.add_argument("--request")  # 记录原始修改诉求的可选文本参数

    # 允许登记处理摘要，帮助后续快速理解本次日志条目已完成什么。
    obj_log_parser.add_argument("--summary")  # log 修订摘要参数

    # 允许登记关联产物，便于回看这次迭代真正改动了哪些文件。
    obj_log_parser.add_argument("--artifacts")  # log 产物清单参数

    # 返回完成参数注册的解析器对象，供主流程统一解析命令行。
    return obj_parser

# 复制一份新的修订草稿，并同步写出修订请求说明单。
def prepare_revision(namespace_arguments: argparse.Namespace) -> int:
    """准备新的修订草稿。

    参数：
    - `namespace_arguments`：包含案件目录、输入草稿和修订请求的参数对象。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 找不到可修订草稿时抛出 `FileNotFoundError`。
    - 文件复制或说明单写入失败时由底层异常上抛。
    """

    # 取回共享运行时支持模块，供修订稿准备流程复用受管文件工具。
    module_runtime_support = load_runtime_support_module()  # 供日志登记流程复用的公共工具模块

    # 解析案件目录绝对路径，确保修订稿仍然落在当前案件空间内。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 这次日志追加对应的案件根目录

    # 在调用方显式给定输入草稿时解析其绝对路径，否则保留空值供自动查找逻辑处理。
    path_input = Path(namespace_arguments.input).resolve() if namespace_arguments.input else None  # 调用方显式指定的输入草稿路径

    # 定位本次修订要基于哪一份正文草稿，优先使用调用方显式指定路径。
    path_base_draft = module_runtime_support.find_disclosure_draft(path_case_dir, path_input)  # 本次修订的基线正文草稿

    # 在找不到修订基线草稿时立即报错，避免生成空壳修订文件。
    if path_base_draft is None or not path_base_draft.exists():

        # 抛出明确错误，提醒调用方先准备 disclosure draft markdown。
        raise FileNotFoundError("> ERR: [Python] 缺少可用于修订的 disclosure draft markdown。")

    # 确保 drafts 目录存在，后续新的修订稿和请求说明单都会落在这里。
    path_output_dir = module_runtime_support.ensure_dir(path_case_dir / "03_drafts")  # 修订草稿输出目录

    # 清洗基线草稿文件名主体，供新修订稿稳定命名。
    str_clean_stem = module_runtime_support.sanitize_name(path_base_draft.stem, fallback="revised_disclosure")  # 修订草稿文件名前缀

    # 基于清洗后的前缀和当前时间戳拼出新的修订草稿文件名。
    str_revision_name = f"{str_clean_stem}_{module_runtime_support.now_timestamp()}_revision.md"  # 新修订草稿文件名

    # 拼接新的修订草稿输出路径，避免覆盖已有历史修订版本。
    path_revision_draft = path_output_dir / str_revision_name  # 新修订草稿路径

    # 复制基线草稿内容到新的修订稿路径，形成独立的本次修订工作副本。
    shutil.copyfile(path_base_draft, path_revision_draft)

    # 为当前修订稿同步生成修订请求说明单，便于保留本轮修订上下文。
    path_request_note = path_revision_draft.with_name(f"{path_revision_draft.stem}_revision_request.md")  # 修订请求说明单路径

    # 组装修订请求说明单各行文本，记录时间、基线草稿和用户诉求。
    list_request_lines = [  # 修订请求说明单文本行列表
        "# Revision Request",  # 说明单标题
        "",  # 标题后的空行
        f"- Time: {module_runtime_support.iso_now()}",  # 修订时间
        f"- Base: `{path_base_draft.name}`",  # 基线草稿文件名
        f"- New draft: `{path_revision_draft.name}`",  # 新修订稿文件名
        f"- User request: {namespace_arguments.request or '[not provided]'}",  # 用户修订请求文本
        "",  # 说明单结尾空行
    ]

    # 把修订请求说明单行列表拼成 Markdown 文本，供案件目录落盘使用。
    str_request_note = "\n".join(list_request_lines)  # 修订请求说明单 Markdown 文本

    # 把修订请求说明单写入案件目录，方便后续人工或脚本继续迭代。
    module_runtime_support.write_text_file(path_request_note, str_request_note)

    # 把新修订稿绝对路径作为机器可读输出写回上游流程。
    sys.stdout.write(str(path_revision_draft.resolve()) + "\n")

    # 返回成功状态码，表示修订草稿和请求说明单都已准备完成。
    return 0

# 向案件日志追加一条迭代记录，沉淀修订请求、摘要和关联产物清单。
def append_revision_log(namespace_arguments: argparse.Namespace) -> int:
    """追加迭代日志记录。

    参数：
    - `namespace_arguments`：包含案件目录、记录类型、摘要和产物信息的参数对象。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 日志目录创建或文件写入失败时由底层异常上抛。
    """

    # 为日志登记流程加载共享支持模块，复用时间戳和受管目录工具。
    module_runtime_support = load_runtime_support_module()  # 共享运行时支持模块

    # 解析日志归属案件目录的绝对路径，确保条目追加到正确案件下。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 当前案件根目录

    # 确保日志目录存在，并固定 revision_log.md 作为本案的迭代日志入口。
    path_log_file = module_runtime_support.ensure_dir(path_case_dir / "99_logs") / "revision_log.md"  # 迭代日志文件路径

    # 组装本次日志条目的各行文本，保留时间、请求、摘要和关联产物信息。
    list_entry_lines = [  # 本次迭代日志条目文本行列表
        f"## {module_runtime_support.iso_now()}",  # 日志条目时间标题
        "",  # 时间标题后的空行
        f"- kind: {namespace_arguments.kind or 'revision'}",  # 日志记录类型
        f"- request: {namespace_arguments.request or '[not provided]'}",  # 原始修订请求文本
        f"- summary: {namespace_arguments.summary or '[not provided]'}",  # 本次处理摘要
        f"- artifacts: {namespace_arguments.artifacts or '[not provided]'}",  # 关联产物清单
        "",  # 日志条目结尾空行
    ]

    # 把日志条目行列表拼成 Markdown 文本，供追加写入日志文件。
    str_entry = "\n".join(list_entry_lines)  # 本次迭代日志条目 Markdown 文本

    # 以追加模式打开日志文件，保留既有历史记录不被覆盖。
    with path_log_file.open("a", encoding="utf-8") as obj_log_file:

        # 把本次日志条目追加到文件尾部，形成完整的本地迭代轨迹。
        obj_log_file.write(str_entry)

    # 把日志文件绝对路径作为机器可读输出写回上游流程。
    sys.stdout.write(str(path_log_file.resolve()) + "\n")

    # 返回成功状态码，表示日志条目已经成功落盘。
    return 0

# 组织迭代入口主流程，按子命令分派修订稿准备或日志追加逻辑。
def main() -> int:
    """执行迭代入口主流程。

    参数：
    - 无。

    返回：
    - `int`：子命令成功完成时返回 `0`。

    异常：
    - 未识别子命令时抛出 `ValueError`。
    - prepare 或 log 过程中的底层异常继续上抛。
    """

    # 解析命令行参数，读取当前调用方请求的迭代子命令和参数。
    namespace_arguments = build_parser().parse_args()  # 迭代入口参数对象

    # 在命中 prepare 子命令时进入修订草稿准备流程。
    if namespace_arguments.command == "prepare":

        # 把 prepare 分支状态码交还给当前命令行调用方。
        return prepare_revision(namespace_arguments)

    # 在命中 log 子命令时进入迭代日志追加流程。
    if namespace_arguments.command == "log":

        # 让 log 分支的退出码沿原样返回给当前 shell 调用方。
        return append_revision_log(namespace_arguments)

    # 对未知子命令抛出明确错误，避免静默吞掉错误调用。
    raise ValueError("> ERR: [Python] 未识别的 iteration 子命令。")

# 保留标准命令行入口，方便直接执行迭代脚本。
if __name__ == "__main__":

    # 使用 main 的返回值作为进程退出码，保持 CLI 行为一致。
    raise SystemExit(main())
