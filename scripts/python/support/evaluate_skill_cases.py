#!/usr/bin/env python3
"""执行技能内置的确定性文件与合同术语评测。"""

# 启用未来版本注解行为，保持类型标注在受支持解释器间一致。
from __future__ import annotations

# 引入参数解析、JSON 序列化、标准输出和路径处理能力。
import argparse
import base64
import json

# 引入进程、临时目录、路径和类型支持，限制运行时评测副作用。
import os
import subprocess
import sys
import tempfile
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

# 替换运行时参数中的受控根目录标记，使清单不保存本机绝对路径。
def replace_runtime_tokens(str_value: str, path_skill_root: Path, path_case_root: Path) -> str:
    """替换运行时清单中的路径标记。

    参数：
    - `str_value`：可能包含根目录标记的参数文本。
    - `path_skill_root`：当前被评测技能根目录。
    - `path_case_root`：当前临时案例根目录。

    返回：
    - `str`：完成受控路径替换的参数文本。

    异常：
    - 无。
    """

    # 先替换技能根标记，再替换临时案例根标记。
    str_replaced = str_value.replace("{skill_root}", str(path_skill_root))  # 已替换技能根的文本

    # 返回同时完成两类根目录替换的文本。
    return str_replaced.replace("{case_root}", str(path_case_root))

# 把清单声明的最小夹具写入临时案例根目录。
def prepare_runtime_files(path_case_root: Path, list_setup_files: list[dict[str, Any]]) -> None:
    """写入运行时评测夹具。

    参数：
    - `path_case_root`：本轮临时案例根目录。
    - `list_setup_files`：相对路径及文本或 JSON 内容声明。

    返回：
    - `None`：全部夹具写入临时目录。

    异常：
    - 路径越界或内容声明无效时抛出 `ValueError`。
    """

    # 逐项写入清单内声明的最小输入文件。
    for dict_file in list_setup_files:

        # 复用技能路径边界规则校验临时案例相对路径。
        path_target = resolve_skill_file(path_case_root, str(dict_file["path"]))  # 当前夹具目标路径

        # 创建当前夹具父目录，允许清单表达真实案件层级。
        path_target.parent.mkdir(parents=True, exist_ok=True)

        # 哈希绑定夹具按原始字节恢复，避免 Windows 换行转换破坏来源链。
        if "base64" in dict_file:

            # 解码清单中的原始字节并直接落盘，保持跨平台哈希一致。
            bytes_content = base64.b64decode(str(dict_file["base64"]), validate=True)  # 哈希绑定夹具字节

            # 二进制写入不执行文本换行转换。
            path_target.write_bytes(bytes_content)

            # 当前夹具已经落盘，无需进入文本写入分支。
            continue

        # JSON 内容使用稳定 UTF-8 和缩进写出。
        if "json" in dict_file:

            # 序列化结构化夹具，保证运行入口读取真实 JSON 文件。
            str_content = json.dumps(dict_file["json"], ensure_ascii=False, indent=2) + "\n"  # 当前 JSON 夹具文本

        # 普通文本内容按原值写出。
        else:

            # 将显式文本转换为字符串，避免隐式写入二进制对象。
            str_content = str(dict_file["text"])  # 当前文本夹具内容

        # 把夹具落到临时案例根，不修改技能源目录。
        path_target.write_text(str_content, encoding="utf-8")

# 递归检查实际 JSON 是否包含清单要求的结构和值。
def json_contains(obj_actual: Any, obj_expected: Any) -> bool:
    """检查 JSON 子集合同。

    参数：
    - `obj_actual`：运行入口产生的实际 JSON 值。
    - `obj_expected`：清单声明的必要 JSON 子集。

    返回：
    - `bool`：实际值包含全部预期结构和值时返回 `True`。

    异常：
    - 无。
    """

    # 字典预期要求实际对象包含相同键及递归匹配值。
    if isinstance(obj_expected, dict):

        # 实际对象必须也是字典。
        if not isinstance(obj_actual, dict):

            # 字典预期不接受标量或列表实际值。
            return False

        # 所有预期键都必须存在并满足递归子集。
        return all(
            str_key in obj_actual and json_contains(obj_actual[str_key], obj_value)
            for str_key, obj_value in obj_expected.items()
        )

    # 列表预期采用逐项子集匹配，允许实际报告保留额外诊断。
    if isinstance(obj_expected, list):

        # 实际对象必须也是列表。
        if not isinstance(obj_actual, list):

            # 类型不一致时立即返回不匹配。
            return False

        # 每个预期项都必须能在实际列表中找到递归匹配项。
        return all(
            any(json_contains(obj_item, obj_required) for obj_item in obj_actual)
            for obj_required in obj_expected
        )

    # 标量预期使用普通值相等。
    return obj_actual == obj_expected

# 在临时案例根执行真实公开入口并核对结构化结果。
def evaluate_runtime_case(
    path_skill_root: Path,
    dict_runtime: dict[str, Any],
) -> dict[str, Any]:
    """执行单个运行时评测合同。

    参数：
    - `path_skill_root`：当前被评测技能根目录。
    - `dict_runtime`：入口、参数、夹具和预期结果声明。

    返回：
    - `dict[str, Any]`：运行命令状态与失败断言列表。

    异常：
    - 路径越界、进程启动或 JSON 解析异常由上层统一处理。
    """

    # 每个用例使用独立临时目录，避免 source、dist 与 installed 之间共享状态。
    with tempfile.TemporaryDirectory() as str_temp_dir:

        # 解析本轮临时案例根。
        path_case_root = Path(str_temp_dir).resolve()  # 当前运行时案例根目录

        # 写入清单声明的最小夹具。
        prepare_runtime_files(path_case_root, list(dict_runtime.get("setup_files", [])))

        # 解析并限制公开入口路径，禁止评测器执行技能根以外脚本。
        path_entrypoint = resolve_skill_file(path_skill_root, str(dict_runtime["entrypoint"]))  # 当前公开入口路径

        # 准备 Python 子进程命令，默认关闭字节码回写。
        list_command = [sys.executable, "-B"]  # 当前运行时评测命令

        # 缺包能力场景用 -S 隔离 site-packages，稳定验证缺失退出语义。
        if bool(dict_runtime.get("no_site_packages", False)):

            # 禁用 site 模块后执行同一正式依赖入口。
            list_command.append("-S")

        # 把真实公开入口加入命令。
        list_command.append(str(path_entrypoint))

        # 替换受控路径标记后追加场景参数。
        list_arguments = [  # 当前入口参数序列
            replace_runtime_tokens(str(obj_argument), path_skill_root, path_case_root)  # 当前参数的受控根替换结果
            for obj_argument in dict_runtime.get("arguments", [])  # 遍历清单声明的公开入口参数
        ]

        # 追加全部入口参数。
        list_command.extend(list_arguments)

        # 默认继承环境并关闭字节码写入，避免评测污染安装副本。
        dict_environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}  # 当前子进程环境

        # 执行真实公开入口，始终捕获输出供结构化断言。
        obj_completed = subprocess.run(  # 证明清单场景已接入生产 CLI 而非静态文本
            list_command,  # 当前用例实际执行的解释器参数序列
            cwd=path_case_root,  # 将入口副作用限制在一次性案件空间
            check=False,  # 保留非零状态供清单核对预期阻断语义
            capture_output=True,  # 保留协议输出与错误诊断供后续断言
            text=True,  # 将子进程输出交给 JSON 文本解析路径
            encoding="utf-8",  # 按技能公开协议解码中文结构化输出
            errors="replace",  # 非协议诊断字节只替换显示，不影响结构化文件断言
            env=dict_environment,  # 继承工具环境但禁止污染技能目录字节码
        )

        # 准备运行时失败断言列表，收集全部不一致。
        list_failures: list[str] = []  # 当前运行时断言失败列表

        # 校验退出码属于清单允许集合。
        list_expected_codes = list(dict_runtime.get("expected_exit_codes", [0]))  # 允许退出码列表

        # 非预期退出码表明入口行为与合同断开。
        if obj_completed.returncode not in list_expected_codes:

            # 记录稳定失败类型，不把临时绝对路径写入报告。
            list_failures.append("unexpected_exit_code")

        # stdout_json 存在时解析并检查必要子集。
        if "stdout_json" in dict_runtime:

            # JSON 解析失败也作为结构化结果失败而不是评测器崩溃。
            try:

                # 解析公开入口 stdout 的单个 JSON 对象。
                obj_stdout_json = json.loads(obj_completed.stdout)  # 当前入口 stdout JSON

                # 实际 JSON 未包含预期子集时登记断链。
                if not json_contains(obj_stdout_json, dict_runtime["stdout_json"]):

                    # 记录稳定子集不匹配类型。
                    list_failures.append("stdout_json_mismatch")

            # 非 JSON stdout 不能满足结构化结果合同。
            except json.JSONDecodeError:

                # 记录解析失败，不把完整输出复制到发布报告。
                list_failures.append("stdout_not_json")

        # 逐项检查入口写入的 JSON 文件。
        for dict_assertion in dict_runtime.get("output_json", []):

            # 输出文件只能位于当前临时案例根。
            path_output = resolve_skill_file(path_case_root, str(dict_assertion["path"]))  # 当前预期 JSON 输出

            # 缺失输出文件时登记失败并继续检查其他断言。
            if not path_output.is_file():

                # 保存稳定缺失标记。
                list_failures.append(f"missing_output:{dict_assertion['path']}")

                # 当前文件不存在，不能继续解析。
                continue

            # 读取真实输出 JSON。
            obj_output_json = json.loads(path_output.read_text(encoding="utf-8"))  # 当前运行时输出 JSON

            # 输出结构未包含预期子集时登记失败。
            if not json_contains(obj_output_json, dict_assertion["contains"]):

                # 保存相对路径，避免报告泄露临时根。
                list_failures.append(f"output_json_mismatch:{dict_assertion['path']}")

        # 返回稳定运行时报告，不保存临时路径和完整敏感载荷。
        return {
            "status": "passed" if not list_failures else "failed",  # 当前运行时评测状态
            "returncode": obj_completed.returncode,  # 真实公开入口退出码
            "failures": list_failures,  # 所有运行时断言失败
        }

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
    bool_static_passed = not list_missing_files and not list_missing_terms  # 当前用例静态检查状态

    # 默认静态 lint 用例没有运行时结果。
    dict_runtime_report: dict[str, Any] | None = None  # 当前用例可选运行时报告

    # runtime 模式必须执行真实公开入口，静态术语不能代替行为证据。
    if dict_case.get("mode", "lint") == "runtime" and bool_static_passed:

        # 执行当前用例声明的真实入口与结构化断言。
        dict_runtime_report = evaluate_runtime_case(path_skill_root, dict_case["runtime"])  # 当前运行时结果

    # 静态检查和适用的运行时检查都通过时才允许用例通过。
    bool_runtime_passed = dict_runtime_report is None or dict_runtime_report["status"] == "passed"  # 运行时检查状态

    # 组合静态和运行时两部分结论。
    bool_passed = bool_static_passed and bool_runtime_passed  # 当前用例最终通过状态

    # 返回当前用例的稳定结果结构，供汇总逻辑计数与写出报告。
    return {
        "id": str(dict_case["id"]),
        "status": "passed" if bool_passed else "failed",
        "missing_files": list_missing_files,
        "missing_terms": list_missing_terms,
        "mode": str(dict_case.get("mode", "lint")),
        "runtime": dict_runtime_report,
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

    # 评测清单必须属于 supplied skill root，禁止 source/dist/installed 越界读取仓库测试。
    path_evals = resolve_skill_file(path_skill_root, namespace_arguments.evals)  # 技能根内评测清单路径

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
