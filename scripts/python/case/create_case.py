#!/usr/bin/env python3
"""创建专利生成案件目录并写入基础配置。"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# 这里引入同目录下的建案支持函数，避免主脚本塞入过多通用细节。
from case_support import CASE_STAGE_DIRECTORIES
from case_support import ensure_dir
from case_support import iso_now
from case_support import sanitize_name
from case_support import write_json_file
from case_support import write_text_file

# 这里解析命令行参数，明确建案的名称、研究根目录和输出根目录。
def parse_arguments() -> argparse.Namespace:
    """解析建案命令行参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含建案所需的命令行参数。

    异常：
    - 参数缺失时由 `argparse` 自动结束进程。
    """

    # 这里构造命令行解析器，向调用方说明本脚本的用途。
    parser = argparse.ArgumentParser(description="Create a governed readable patent case directory.")  # 建案命令行解析器

    # 这里要求调用方提供案件名，确保目录和配置具备稳定标识。
    parser.add_argument(  # 案件名参数
        "--case-name",
        required=True,
        help="Short case or invention name.",
    )

    # 这里要求调用方提供研究材料根目录，供后续全链路继续使用。
    parser.add_argument(  # 研究根目录参数
        "--research-root",
        required=True,
        help="Research folder or file path to analyze.",
    )

    # 这里把默认输出根固定到 runs/patent_cases，符合当前正式目录合同。
    parser.add_argument(  # 案件输出根目录参数
        "--output-root",
        default="runs/patent_cases",
        help="Root directory for generated patent cases.",
    )

    # 要求调用方显式选择技术类型，默认保持通用规则以兼容既有命令。
    parser.add_argument(  # 案件技术类型参数
        "--technical-profile",
        choices=("general", "ai_algorithm"),
        default="general",
        help="Examination profile selected by the user.",
    )

    # AI案件需要进一步选择模型训练、场景应用或两者兼有。
    parser.add_argument(  # AI规则适用范围参数
        "--ai-scope",
        choices=("model_training", "model_application", "both"),
        default="",
        help="Required scope when --technical-profile is ai_algorithm.",
    )

    # 先解析参数，后续联合校验profile与scope的条件关系。
    namespace_arguments = parser.parse_args()  # 初步解析的建案参数

    # AI案件缺少适用范围时无法确定专项审查规则。
    if namespace_arguments.technical_profile == "ai_algorithm" and not namespace_arguments.ai_scope:

        # 通过argparse统一报告条件必填错误。
        parser.error("--ai-scope 在 --technical-profile=ai_algorithm 时必填。")

    # 通用案件不接受AI范围，避免保存互相矛盾的配置。
    if namespace_arguments.technical_profile == "general" and namespace_arguments.ai_scope:

        # 要求调用方删除无效scope或明确切换到AI profile。
        parser.error("--ai-scope 仅适用于 --technical-profile=ai_algorithm。")

    # 这里返回解析结果，供建案逻辑继续使用。
    return namespace_arguments

# 这里根据案件目录标准结构创建所有阶段子目录。
def create_stage_directories(case_dir: Path) -> None:
    """创建案件阶段目录。

    参数：
    - `case_dir`：案件根目录。

    返回：
    - `None`。

    异常：
    - 目录创建失败时由底层异常上抛。
    """

    # 这里逐个创建标准阶段目录，保证后续脚本不需要再猜路径。
    for stage_name in CASE_STAGE_DIRECTORIES:

        # 这里拼接阶段目录路径，统一落到当前案件根目录下。
        path_stage_dir = case_dir / stage_name  # 当前阶段目录路径

        # 这里确保阶段目录存在，允许重复运行而不报错。
        ensure_dir(path_stage_dir)

# 这里写入案件配置和简要说明，作为后续主链脚本的稳定输入。
def write_case_bootstrap_files(
    case_dir: Path,
    case_name: str,
    case_slug: str,
    research_root: Path,
    technical_profile: str,
    ai_scope: str,
) -> None:
    """写入案件配置和说明文件。

    参数：
    - `case_dir`：案件根目录。
    - `case_name`：用户提供的案件名称。
    - `case_slug`：经过清洗后的案件目录名。
    - `research_root`：研究材料根目录。
    - `technical_profile`：用户在建案阶段明确选择的审查类型。
    - `ai_scope`：AI案件适用范围；通用案件为空字符串。

    返回：
    - `None`。

    异常：
    - 文件写入失败时由底层异常上抛。
    """

    # 这里生成案件配置字典，供后续每个脚本读取统一入口信息。
    dict_case_config = {  # 案件基础配置
        "case_name": case_name,  # 原始案件名称
        "case_slug": case_slug,  # 清洗后的目录标识
        "research_root": str(research_root.resolve()),  # 研究材料绝对路径
        "created_at": iso_now(),  # 建案时间
        "case_dir": str(case_dir.resolve()),  # 案件绝对路径
        "technical_profile": technical_profile,  # 用户明确选择的审查类型
        "ai_scope": ai_scope,  # AI专项规则适用范围
    }

    # 这里把案件配置写入根目录，作为全链路的统一配置入口。
    write_json_file(case_dir / "case_config.json", dict_case_config)

    # 这里生成简短说明文件，方便人工快速确认案件入口信息。
    readme_text = (
        f"# {case_name}\n\n"
        "## Case Overview\n\n"
        f"- Research root: `{dict_case_config['research_root']}`\n"
        f"- Created at: {dict_case_config['created_at']}\n"
        f"- Case slug: `{case_slug}`\n"
    )  # 案件说明文本

    # 这里写入案件说明文件，供人工审阅和后续追踪使用。
    write_text_file(case_dir / "README.md", readme_text)

# 这里执行建案主流程，并把案件目录路径打印到标准输出末尾。
def main() -> int:
    """执行建案主流程。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 参数、目录创建或文件写入错误时由底层异常上抛。
    """

    # 这里先解析参数，确保建案信息完整可用。
    namespace_arguments = parse_arguments()  # 命令行参数

    # 这里清洗案件名，得到稳定可用的目录标识。
    case_slug = sanitize_name(namespace_arguments.case_name)  # 案件目录标识

    # 这里解析输出根目录，后续会在该目录下创建具体案件目录。
    path_output_root = Path(namespace_arguments.output_root).resolve()  # 案件输出根目录

    # 这里解析研究材料根目录，写入配置时保留稳定绝对路径。
    path_research_root = Path(namespace_arguments.research_root).resolve()  # 研究材料根目录

    # 这里拼接案件根目录，保证每个案件拥有独立落盘空间。
    path_case_dir = ensure_dir(path_output_root / case_slug)  # 当前案件目录

    # 这里创建案件标准阶段目录，保证后续主链路径一致。
    create_stage_directories(path_case_dir)

    # 这里写入案件基础配置和说明文件，供后续脚本统一读取。
    write_case_bootstrap_files(
        path_case_dir,
        namespace_arguments.case_name,
        case_slug,
        path_research_root,
        namespace_arguments.technical_profile,
        namespace_arguments.ai_scope,
    )

    # 这里输出最终案件目录，供上游自动流程直接捕获使用。
    sys.stdout.write(str(path_case_dir.resolve()) + "\n")

    # 这里返回成功状态码，表示建案已完成。
    return 0

# 这里保留标准脚本入口，方便命令行和子进程统一调用。
if __name__ == "__main__":

    # 这里通过标准退出路径返回状态码，保持命令行调用行为一致。
    raise SystemExit(main())
