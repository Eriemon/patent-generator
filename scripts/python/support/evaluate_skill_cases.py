#!/usr/bin/env python3
"""执行技能内置的确定性文件与合同术语评测。"""

# 启用未来版本注解行为，保持类型标注在受支持解释器间一致。
from __future__ import annotations

# 引入参数解析、JSON 序列化、标准输出和路径处理能力。
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 构造命令行参数解析器，统一声明评测输入与报告输出路径。
def parse_arguments() -> argparse.Namespace:
    """解析技能评测命令行参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含技能根目录、评测清单、报告路径和静默开关。

    异常：
    - 参数非法时由 `argparse` 自动结束进程。
    """

    # 固定当前 CLI 的用途说明，供命令行帮助文本直接复用。
    str_description = "Evaluate install-local readable patent generator contracts."  # 评测入口说明文本

    # 初始化当前评测入口的参数解析器。
    argument_parser_obj_parser: argparse.ArgumentParser = argparse.ArgumentParser(description=str_description)  # 评测入口参数解析器

    # 注册技能根目录参数，确保评测路径边界有唯一锚点。
    argument_parser_obj_parser.add_argument("--skill-root", required=True, help="Installed skill root.")

    # 注册评测清单参数，允许源目录和安装目录复用同一入口。
    argument_parser_obj_parser.add_argument("--evals", required=True, help="Evaluation corpus JSON path.")

    # 注册机器可读报告路径，避免 stdout 文本与报告协议混合。
    argument_parser_obj_parser.add_argument("--output", required=True, help="Machine-readable report path.")

    # 注册静默开关，供自动化门禁关闭过程性 INFO。
    argument_parser_obj_parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")

    # 返回解析后的参数对象，供主流程定位本轮评测输入与输出。
    return argument_parser_obj_parser.parse_args()

# 把评测相对路径限制在技能根目录内，阻止安装后越界读取仓库文件。
def resolve_skill_file(path_skill_root: Path, str_relative_path: str) -> Path:
    """解析技能根目录内的评测目标文件。

    参数：
    - `path_skill_root`：已经解析的技能根目录。
    - `str_relative_path`：评测清单声明的相对文件路径。

    返回：
    - `Path`：技能根目录内的绝对目标路径。

    异常：
    - 路径越过技能根目录时抛出 `ValueError`。
    """

    # 组合技能根目录与清单相对路径，形成待校验的绝对路径。
    path_candidate = (path_skill_root / str_relative_path).resolve()  # 待校验的评测目标路径

    # 尝试把目标路径表示为技能根目录的后代，验证边界未被突破。
    try:

        # 只使用相对路径计算完成边界检查，不依赖目标文件是否已经存在。
        path_candidate.relative_to(path_skill_root)

    # 捕获无法相对到技能根目录的情况，并转成稳定评测错误。
    except ValueError as obj_error:

        # 抛出带稳定编号的越界错误，供 CLI 统一形成配置失败退出码。
        raise ValueError(
            f"> ERR: [Python] EVAL001 评测路径越过技能根目录：{str_relative_path}"
        ) from obj_error

    # 返回已经通过边界检查的绝对路径，供文件和术语检查复用。
    return path_candidate

# 检查单个用例声明的全部文件和合同术语，形成稳定的逐例结果。
def evaluate_case(path_skill_root: Path, dict_case: dict[str, Any]) -> dict[str, Any]:
    """执行一个技能评测用例。

    参数：
    - `path_skill_root`：已经解析的技能根目录。
    - `dict_case`：当前用例的文件与术语要求字典。

    返回：
    - `dict[str, Any]`：包含状态、缺失文件和缺失术语的逐例报告。

    异常：
    - 清单字段缺失、文件读取或路径越界异常由调用方统一处理。
    """

    # 准备缺失文件列表，按清单顺序记录安装后不可用的目标。
    list_missing_files: list[str] = []  # 当前用例缺失文件列表

    # 准备缺失术语列表，记录具体文件与未命中的合同文本。
    list_missing_terms: list[dict[str, str]] = []  # 当前用例缺失术语明细

    # 逐个检查当前用例声明的必需文件，先建立结构完整性证据。
    for str_relative_path in dict_case["required_files"]:

        # 解析并限制当前文件路径，确保评测始终保持安装目录内自包含。
        path_required_file = resolve_skill_file(path_skill_root, str(str_relative_path))  # 当前必需文件绝对路径

        # 在目标不是普通文件时登记缺失项，供最终报告明确定位。
        if not path_required_file.is_file():

            # 保存当前相对路径，保持报告不泄露调用机器绝对目录。
            list_missing_files.append(str(str_relative_path))

    # 逐组检查指定文件中的合同术语，验证关键行为没有从实现中漂移。
    for dict_requirement in dict_case["required_terms"]:

        # 读取当前术语组对应的技能内相对路径。
        str_relative_path = str(dict_requirement["file"])  # 当前术语组目标文件相对路径

        # 解析并限制当前术语目标，阻止清单借助父目录读取仓库测试。
        path_required_file = resolve_skill_file(path_skill_root, str_relative_path)  # 当前术语目标绝对路径

        # 在术语目标文件缺失时只登记结构问题，不继续尝试读取内容。
        if not path_required_file.is_file():

            # 避免同一缺失文件在结构检查和术语检查中重复出现。
            if str_relative_path not in list_missing_files:

                # 补登记只在术语清单中出现的缺失文件。
                list_missing_files.append(str_relative_path)

            # 跳过当前缺失文件的术语遍历，继续检查后续要求。
            continue

        # 读取当前技能文件的 UTF-8 文本，供全部合同术语共享。
        str_source_text = path_required_file.read_text(encoding="utf-8")  # 当前术语目标源码文本

        # 逐个核对当前文件要求的合同术语，收集所有缺口而非首错即停。
        for str_required_term in dict_requirement["terms"]:

            # 在合同术语不存在时记录文件与术语，便于修复精确定位。
            if str(str_required_term) not in str_source_text:

                # 追加当前缺失术语明细，保持机器报告字段固定。
                list_missing_terms.append(
                    {"file": str_relative_path, "term": str(str_required_term)}
                )

    # 只有文件和术语两个维度均无缺口时，当前用例才算通过。
    bool_passed = not list_missing_files and not list_missing_terms  # 当前用例最终通过状态

    # 返回当前用例的稳定结果结构，供汇总逻辑计数与写出报告。
    return {
        "id": str(dict_case["id"]),
        "status": "passed" if bool_passed else "failed",
        "missing_files": list_missing_files,
        "missing_terms": list_missing_terms,
    }

# 把每个用例的结构与术语结果汇入同一份发布门禁报告。
def build_evaluation_report(path_skill_root: Path, path_evals: Path) -> dict[str, Any]:
    """构造完整技能评测报告。

    参数：
    - `path_skill_root`：已经解析的技能根目录。
    - `path_evals`：当前评测清单 JSON 路径。

    返回：
    - `dict[str, Any]`：包含总状态、计数和逐例结果的机器报告。

    异常：
    - JSON、字段、路径或文件异常由调用方统一转换为配置失败。
    """

    # 读取并解析评测清单，保留 JSON 原始用例顺序。
    dict_evals: dict[str, Any] = json.loads(path_evals.read_text(encoding="utf-8"))  # 当前评测清单字典

    # 准备逐例报告列表，后续按清单顺序追加每个结果。
    list_case_reports: list[dict[str, Any]] = []  # 全部用例评测结果列表

    # 逐个执行评测用例，确保任何失败都进入同一份汇总报告。
    for dict_case in dict_evals["cases"]:

        # 执行当前用例并保存其结构与术语检查结果。
        dict_case_report = evaluate_case(path_skill_root, dict_case)  # 当前用例评测结果

        # 把当前结果加入汇总列表，保持与输入清单一致的可追踪顺序。
        list_case_reports.append(dict_case_report)

    # 统计状态为 passed 的用例数量，供最终退出码与摘要共同使用。
    int_passed_count = sum(1 for dict_report in list_case_reports if dict_report["status"] == "passed")  # 通过用例数量

    # 由总数减去通过数得到失败数，避免重复遍历产生不一致计数。
    int_failed_count = len(list_case_reports) - int_passed_count  # 失败用例数量

    # 返回稳定机器报告结构，便于源目录、发布目录和安装目录做同构验证。
    return {
        "status": "passed" if int_failed_count == 0 else "failed",
        "passed": int_passed_count,
        "failed": int_failed_count,
        "cases": list_case_reports,
    }

# 执行 CLI 主流程，统一处理输入错误、报告写出与退出码协议。
def main() -> int:
    """执行技能评测命令行入口。

    参数：
    - 无。

    返回：
    - `int`：全通过返回 0，用例失败返回 1，配置或读取失败返回 2。

    异常：
    - 已知输入异常会转换为稳定错误文本和退出码 2。
    """

    # 解析命令行参数，定位本轮技能根目录、清单和报告文件。
    namespace_arguments = parse_arguments()  # 当前命令行参数对象

    # 解析技能根目录为绝对路径，供所有清单目标执行边界检查。
    path_skill_root = Path(namespace_arguments.skill_root).resolve()  # 当前技能根目录

    # 解析评测清单为绝对路径，避免调用目录改变输入语义。
    path_evals = Path(namespace_arguments.evals).resolve()  # 当前评测清单路径

    # 解析报告输出为绝对路径，确保父目录创建位置明确。
    path_output = Path(namespace_arguments.output).resolve()  # 当前评测报告输出路径

    # 执行全部评测并把已知输入异常转换为稳定 CLI 失败协议。
    try:

        # 构造完整评测报告，供后续写盘和退出码判断复用。
        dict_report = build_evaluation_report(path_skill_root, path_evals)  # 当前完整评测报告

    # 捕获清单、路径和读取异常，避免向自动化调用方泄露不稳定堆栈。
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as obj_error:

        # 向错误流写出稳定编号与根因摘要，保持机器报告 stdout 不受污染。
        sys.stderr.write(f"> ERR: [Python] EVAL002 无法执行技能评测：{obj_error}\n")

        # 返回配置失败退出码，区别于合法执行后存在未通过用例。
        return 2

    # 创建报告父目录，允许调用方把结果写入新的临时验证目录。
    path_output.parent.mkdir(parents=True, exist_ok=True)

    # 按 UTF-8 和稳定缩进写出机器可读报告，方便发布与安装证据比对。
    path_output.write_text(
        json.dumps(dict_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 非静默模式下输出过程性摘要，便于人工运行时快速查看结果。
    if not namespace_arguments.quiet:

        # 使用项目统一 INFO 前缀输出通过与失败数量，不混入报告文件。
        sys.stdout.write(
            f"> INFO: [Python] 技能评测完成：{dict_report['passed']} 通过，"
            f"{dict_report['failed']} 失败。\n"
        )

    # 根据总状态返回稳定退出码，使自动化门禁可以直接判断结果。
    return 0 if dict_report["status"] == "passed" else 1

# 保留标准命令行入口，支持源目录、发布目录和安装目录直接运行评测。
if __name__ == "__main__":

    # 把主流程退出码交给解释器，供外层门禁准确识别成功或失败。
    raise SystemExit(main())
