#!/usr/bin/env python3
"""执行正式主链，并在预览确认后继续进入后链。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入命令行、按路径加载模块、结构化数据、子进程、标准输出和路径能力，供正式流水线稳定运行。
import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 固定共享运行时支持模块路径，避免通过修改 sys.path 导入公共工具。
PATH_RUNTIME_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "runtime_support.py"  # 共享运行时支持模块路径

# 固定正式 skill 的 Python 入口根目录，供各主链与后链脚本路径拼接复用。
PATH_PYTHON_ROOT = Path(__file__).resolve().parents[1]  # 正式 skill 的 Python 入口根目录

# 固定建案入口脚本路径，供新案件初始化阶段复用。
PATH_CREATE_CASE_SCRIPT = PATH_PYTHON_ROOT / "case" / "create_case.py"  # 建案入口脚本路径

# 固定材料盘点入口脚本路径，供研究材料扫描阶段复用。
PATH_RESEARCH_INVENTORY_SCRIPT = PATH_PYTHON_ROOT / "intake" / "research_inventory.py"  # 材料盘点入口脚本路径

# 固定事实抽取入口脚本路径，供候选专利点提炼阶段复用。
PATH_EXTRACT_RESEARCH_FACTS_SCRIPT = PATH_PYTHON_ROOT / "facts" / "extract_research_facts.py"  # 事实抽取入口脚本路径

# 固定主案选择入口脚本路径，供主方案锁定阶段复用。
PATH_SELECT_INVENTION_POINT_SCRIPT = PATH_PYTHON_ROOT / "invention" / "select_invention_point.py"  # 主案选择入口脚本路径

# 固定查新规划入口脚本路径，供预览前查新准备阶段复用。
PATH_PLAN_PRIOR_ART_SCRIPT = PATH_PYTHON_ROOT / "prior_art" / "plan_prior_art_queries.py"  # 查新规划入口脚本路径

# 固定预览生成入口脚本路径，供预览确认门生成阶段复用。
PATH_GENERATE_PREVIEW_SCRIPT = PATH_PYTHON_ROOT / "preview" / "generate_preview.py"  # 预览生成入口脚本路径

# 固定正式正文生成入口脚本路径，供预览确认后的正文阶段复用。
PATH_GENERATE_DRAFT_SCRIPT = PATH_PYTHON_ROOT / "draft" / "generate_disclosure_draft.py"  # 正文生成入口脚本路径

# 固定附图生成入口脚本路径，供正式后链附图阶段复用。
PATH_GENERATE_FIGURES_SCRIPT = PATH_PYTHON_ROOT / "figures" / "generate_figures.py"  # 附图生成入口脚本路径

# 固定权利要求生成入口脚本路径，供正式后链权利要求阶段复用。
PATH_GENERATE_CLAIMS_SCRIPT = PATH_PYTHON_ROOT / "claims" / "generate_claims.py"  # 权利要求生成入口脚本路径

# 固定自检入口脚本路径，供正式后链自检阶段复用。
PATH_VALIDATE_DISCLOSURE_SCRIPT = PATH_PYTHON_ROOT / "review" / "validate_disclosure.py"  # 自检入口脚本路径

# 固定 DOCX 导出入口脚本路径，供可选导出阶段复用。
PATH_EXPORT_DOCX_SCRIPT = PATH_PYTHON_ROOT / "export" / "export_docx.py"  # DOCX 导出入口脚本路径

# 描述推进到预览阶段后需要交给主流程继续处理的案件上下文。
@dataclass(frozen=True)
class PreviewCheckpoint:
    """预览阶段准备结果。"""

    # 固定当前案件根目录，供预览门和后链路径组装共同复用。
    path_case_dir: Path  # 当前案件根目录路径

    # 固定当前案件预览材料路径，供确认门和最终返回载荷共同复用。
    path_preview_markdown: Path  # 当前案件预览 Markdown 路径

# 描述预览确认后的后链执行结果，统一封装退出码和 JSON 载荷。
@dataclass(frozen=True)
class PostPreviewChainResult:
    """预览后链执行结果。"""

    # 固定正式后链返回的退出码，供主流程保持既有协议复用。
    int_return_code: int  # 正式后链返回的退出码

    # 固定正式后链返回的机器可读载荷，供主流程补齐预览路径后写回标准输出。
    dict_payload: dict[str, Any]  # 正式后链返回的机器可读载荷

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

    # 执行共享支持模块源码，把公共文件、时间和路径工具装入模块对象。
    obj_spec.loader.exec_module(module_runtime_support)

    # 返回已完成加载的共享支持模块，供正式流水线复用。
    return module_runtime_support

# 构造命令行参数解析器，统一声明新建案件、续跑案件和可选导出参数。
def build_parser() -> argparse.ArgumentParser:
    """构造正式流水线入口的命令行解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已注册参数的解析器对象。

    异常：
    - 无。
    """

    # 先准备解析器说明文本，避免初始化语句过长。
    str_description = "Run the governed patent pipeline with a hard preview confirmation gate."  # 入口说明文本

    # 初始化当前正式流水线入口的命令行解析器。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 正式流水线入口解析器

    # 注册续跑案件目录参数，允许调用方从既有案件目录继续执行。
    obj_parser.add_argument("--case-dir", help="Existing case directory to resume.")

    # 注册新建案件研究材料根目录参数，供新案件主链初始化复用。
    obj_parser.add_argument("--research-root", help="Research folder or file path for a new case.")

    # 注册新建案件名称参数，供建案入口生成稳定案件目录名。
    obj_parser.add_argument("--case-name", help="Short case or invention name for a new case.")

    # 注册新建案件输出根目录参数，供本地 runs 目录定向落盘复用。
    obj_parser.add_argument("--output-root", default="runs/patent_cases")

    # 注册预览确认标记参数，允许调用方在本轮执行前显式确认当前预览。
    obj_parser.add_argument(
        "--confirmed-preview",
        action="store_true",
        help="Mark the current preview as confirmed before entering the post-preview chain.",
    )

    # 注册兼容旧调用的 DOCX 导出开关参数；当前后链默认始终生成 DOCX。
    obj_parser.add_argument(
        "--export-docx",
        action="store_true",
        help="Retained for compatibility; the pipeline now exports DOCX by default.",
    )

    # 返回完成参数注册的解析器对象。
    return obj_parser

# 解析命令行参数，并强制校验新建案件路径必须同时提供研究材料和案件名称。
def parse_arguments() -> argparse.Namespace:
    """解析并校验命令行参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：通过参数完整性校验后的命令行参数对象。

    异常：
    - 参数不完整时由 `argparse` 输出错误并终止当前进程。
    """

    # 创建一份专供参数完整性校验使用的解析器对象，缺参错误也通过它统一回写。
    argument_parser_for_validation = build_parser()  # 参数校验阶段使用的解析器对象

    # 解析命令行参数，得到当前执行上下文配置。
    namespace_arguments = argument_parser_for_validation.parse_args()  # 当前执行使用的命令行参数对象

    # 在调用方显式给出案件目录时，视为续跑场景并直接返回参数对象。
    if namespace_arguments.case_dir:

        # 直接返回续跑案件参数，后续由主流程接管预览和后链判断。
        return namespace_arguments

    # 在新建案件场景缺少研究材料根目录或案件名称时立即报错。
    if not namespace_arguments.research_root or not namespace_arguments.case_name:

        # 通过 argparse 统一输出参数缺失错误并终止当前执行。
        argument_parser_for_validation.error("--research-root 和 --case-name 在新建案件时必填。")

    # 返回完成新建案件参数完整性校验后的参数对象。
    return namespace_arguments

# 执行指定子入口脚本，并保留完整标准输出与标准错误供上层判断。
def run_child_entrypoint(
    path_script: Path,
    list_args: list[str],
) -> subprocess.CompletedProcess[str]:
    """执行指定子入口脚本。

    参数：
    - `path_script`：待执行的子入口脚本路径。
    - `list_args`：需要透传给子入口的命令行参数列表。

    返回：
    - `subprocess.CompletedProcess[str]`：完整子进程执行结果对象。

    异常：
    - 子进程启动失败时由底层异常上抛。
    """

    # 执行子入口脚本，并捕获标准输出与标准错误供上层统一判断。
    return subprocess.run(
        [sys.executable, str(path_script), *list_args],
        cwd=path_script.parent,
        text=True,
        capture_output=True,
        check=False,
    )

# 断言子入口执行成功，失败时把脚本名与标准输出内容一并转成明确错误。
def require_success(
    path_script: Path,
    completed_process_stage: subprocess.CompletedProcess[str],
) -> None:
    """断言子入口执行成功。

    参数：
    - `path_script`：已执行的子入口脚本路径。
    - `completed_process_stage`：对应的子进程执行结果对象。

    返回：
    - `None`。

    异常：
    - 子入口返回非零退出码时抛出 `RuntimeError`。
    """

    # 在子入口返回成功状态码时直接结束当前检查。
    if completed_process_stage.returncode == 0:

        # 成功场景无需进一步处理，直接返回给上层继续串联流程。
        return

    # 把失败脚本名与完整标准输出内容转成显式运行时错误。
    raise RuntimeError(
        f"> ERR: [Python] 子入口执行失败：{path_script.name}\n"
        f"stdout:\n{completed_process_stage.stdout}\n"
        f"stderr:\n{completed_process_stage.stderr}"
    )

# 从子入口标准输出中读取最后一条非空行，供路径型结果回传逻辑复用。
def read_last_stdout_line(completed_process_stage: subprocess.CompletedProcess[str]) -> str:
    """读取子入口标准输出中的最后一条非空行。

    参数：
    - `completed_process_stage`：对应的子进程执行结果对象。

    返回：
    - `str`：标准输出中的最后一条非空文本行。

    异常：
    - 标准输出为空或不存在可解析非空行时抛出 `ValueError`。
    """

    # 逐行清洗标准输出文本，只保留真正可解析的非空文本行。
    list_output_lines = [  # 当前子入口标准输出中的非空文本行列表
        str_line.strip()  # 去掉首尾空白后的单行输出文本
        for str_line in completed_process_stage.stdout.splitlines()  # 当前子入口原始输出行
        if str_line.strip()  # 仅保留非空白输出行
    ]

    # 在标准输出中没有任何可解析结果时立即报错。
    if not list_output_lines:

        # 抛出明确错误，提醒调用方检查目标入口是否写回了预期路径。
        raise ValueError("> ERR: [Python] 子入口未返回任何可解析输出。")

    # 返回最后一条非空输出行，保持与现有入口协议一致。
    return list_output_lines[-1]

# 执行必须成功的子入口，并把完整子进程结果返回给上层继续解析。
def run_required_stage(
    path_script: Path,
    list_args: list[str],
) -> subprocess.CompletedProcess[str]:
    """执行必须成功的子入口。

    参数：
    - `path_script`：待执行的子入口脚本路径。
    - `list_args`：需要透传给子入口的命令行参数列表。

    返回：
    - `subprocess.CompletedProcess[str]`：已经通过成功校验的子进程执行结果对象。

    异常：
    - 子入口启动失败时由底层异常上抛。
    - 子入口返回非零退出码时抛出 `RuntimeError`。
    """

    # 先执行当前子入口脚本，捕获完整标准输出和标准错误。
    completed_process_stage = run_child_entrypoint(path_script, list_args)  # 当前子入口执行结果对象

    # 强制校验当前子入口执行成功，失败时立即终止主流程。
    require_success(path_script, completed_process_stage)

    # 返回已经通过成功校验的子进程结果，供上层继续解析输出。
    return completed_process_stage

# 把子入口最后输出的一条路径文本解析成绝对路径对象，统一处理路径型结果。
def read_output_path(completed_process_stage: subprocess.CompletedProcess[str]) -> Path:
    """把路径型标准输出解析成绝对路径对象。

    参数：
    - `completed_process_stage`：对应的子进程执行结果对象。

    返回：
    - `Path`：由最后一条非空输出行解析得到的绝对路径对象。

    异常：
    - 子入口未返回可解析路径文本时抛出 `ValueError`。
    """

    # 读取子入口返回的最后一条非空输出文本，作为路径型结果源。
    str_output_path = read_last_stdout_line(completed_process_stage)  # 子入口返回的路径文本

    # 把路径文本解析成绝对路径对象，供后续主流程直接复用。
    return Path(str_output_path).resolve()

# 从新建案件开始推进到预览阶段，确保预览确认门前的所有主链步骤都已完成。
def create_case_until_preview(namespace_arguments: argparse.Namespace) -> PreviewCheckpoint:
    """从新建案件推进到预览阶段。

    参数：
    - `namespace_arguments`：已经通过完整性校验的命令行参数对象。

    返回：
    - `PreviewCheckpoint`：包含案件目录与预览 Markdown 路径的阶段结果。

    异常：
    - 任一主链子入口失败时抛出 `RuntimeError`。
    """

    # 解析研究材料根目录绝对路径，确保建案和材料盘点看到的是同一位置。
    path_research_root = Path(namespace_arguments.research_root).resolve()  # 研究材料根目录绝对路径

    # 解析新建案件输出根目录绝对路径，确保 runs 落盘位置稳定。
    path_output_root = Path(namespace_arguments.output_root).resolve()  # 新建案件输出根目录绝对路径

    # 先准备建案入口参数列表，确保案件名称、研究根目录和输出根目录以稳定顺序透传。
    list_create_case_args = [  # 建案入口参数列表
        "--case-name",  # 案件名称参数名
        namespace_arguments.case_name,  # 当前新建案件名称
        "--research-root",  # 研究材料根目录参数名
        str(path_research_root),  # 研究材料根目录文本
        "--output-root",  # 输出根目录参数名
        str(path_output_root),  # 输出根目录文本
    ]

    # 执行建案入口，先创建当前案件目录与基础配置文件。
    completed_process_create_case = run_required_stage(PATH_CREATE_CASE_SCRIPT, list_create_case_args)  # 建案入口执行结果对象

    # 解析建案入口返回的案件目录路径，后续所有主链阶段都要围绕这个案件空间继续落盘。
    path_case_dir = read_output_path(completed_process_create_case)  # 新建案件根目录路径

    # 执行材料盘点入口，把研究目录中的本地材料整理进案件空间。
    list_inventory_args = ["--case-dir", str(path_case_dir), "--research-root", str(path_research_root)]  # 材料盘点入口参数列表

    # 把研究目录中的本地材料整理进案件空间，供后续 facts 阶段读取。
    run_required_stage(PATH_RESEARCH_INVENTORY_SCRIPT, list_inventory_args)

    # 执行事实抽取入口，生成候选专利点与结构化研究事实。
    list_facts_args = ["--case-dir", str(path_case_dir)]  # facts 入口参数列表

    # 生成候选专利点与结构化研究事实，供主案选择阶段继续收敛。
    run_required_stage(PATH_EXTRACT_RESEARCH_FACTS_SCRIPT, list_facts_args)

    # 执行主案选择入口，锁定当前案件的主问题、主方案与保护重点。
    list_selection_args = ["--case-dir", str(path_case_dir)]  # 主案选择入口参数列表

    # 锁定当前案件的主问题、主方案与保护重点，避免后链消费未定稿主案。
    run_required_stage(PATH_SELECT_INVENTION_POINT_SCRIPT, list_selection_args)

    # 执行查新规划入口，生成最接近现有技术的本地检索计划。
    list_prior_art_args = ["--case-dir", str(path_case_dir)]  # 查新规划入口参数列表

    # 生成最接近现有技术的本地检索计划，补齐预览前的查新准备材料。
    run_required_stage(PATH_PLAN_PRIOR_ART_SCRIPT, list_prior_art_args)

    # 先准备预览生成入口参数，确保预览固定围绕当前案件目录输出。
    list_preview_args = ["--case-dir", str(path_case_dir)]  # 预览生成入口参数列表

    # 写出预览确认材料并建立确认门状态文件。
    completed_process_preview = run_required_stage(PATH_GENERATE_PREVIEW_SCRIPT, list_preview_args)  # 预览生成入口执行结果对象

    # 解析预览入口返回的 Markdown 路径，供预览门返回载荷复用。
    path_preview_markdown = read_output_path(completed_process_preview)  # 预览 Markdown 路径

    # 返回推进到预览阶段后的案件上下文，供主流程继续判断确认门。
    return PreviewCheckpoint(
        path_case_dir=path_case_dir.resolve(),  # 已建案件目录绝对路径
        path_preview_markdown=path_preview_markdown.resolve(),  # 新生成预览 Markdown 绝对路径
    )

# 确保既有案件目录中已经存在预览材料；缺失时自动补生成当前预览。
def ensure_existing_preview(path_case_dir: Path) -> Path:
    """确保既有案件目录下存在预览材料。

    参数：
    - `path_case_dir`：当前案件根目录路径。

    返回：
    - `Path`：当前案件可用的预览 Markdown 路径。

    异常：
    - 预览补生成失败时抛出 `RuntimeError`。
    """

    # 固定正式案件下的预览 Markdown 路径，优先命中稳定文件而不是重复补跑预览入口。
    path_preview_markdown = path_case_dir / "03_drafts" / "pre_draft_preview.md"  # 稳定预览 Markdown 路径

    # 在预览 Markdown 已经存在时直接返回其绝对路径。
    if path_preview_markdown.exists():

        # 返回既有预览材料路径，避免重复执行预览入口。
        return path_preview_markdown.resolve()

    # 先准备预览补生成入口参数，确保补出的材料仍然落回当前案件目录。
    list_preview_args = ["--case-dir", str(path_case_dir)]  # 预览补生成入口参数列表

    # 在预览材料缺失时补执行一次预览入口，恢复正式确认门文件。
    completed_process_preview = run_required_stage(PATH_GENERATE_PREVIEW_SCRIPT, list_preview_args)  # 预览补生成入口执行结果对象

    # 返回补生成后的预览 Markdown 路径，供后续确认门判断复用。
    return read_output_path(completed_process_preview)

# 在需要时把预览状态切换为已确认，并返回当前案件最新的预览状态字典。
def apply_preview_confirmation(
    path_case_dir: Path,
    confirmed_preview: bool,
    module_runtime_support: Any,
) -> dict[str, Any]:
    """按需要更新预览确认状态。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `confirmed_preview`：是否在本轮执行前强制把预览标记为已确认。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `dict[str, Any]`：当前案件最新的预览状态字典。

    异常：
    - 预览状态文件缺失时抛出 `FileNotFoundError`。
    - 预览状态 JSON 非法时由底层异常上抛。
    """

    # 固定预览状态 JSON 路径，供正式主链的确认门判断复用。
    path_preview_status = path_case_dir / "03_drafts" / "preview_status.json"  # 预览状态 JSON 路径

    # 在预览状态文件缺失时立即报错，避免当前案件跳过正式确认门。
    if not path_preview_status.exists():

        # 抛出明确错误，提醒调用方先生成预览材料再进入正式主链。
        raise FileNotFoundError("> ERR: [Python] 缺少 preview_status.json。")

    # 读取当前案件的预览状态字典，供确认门判断和可选确认更新复用。
    dict_preview_status = module_runtime_support.read_json_file(path_preview_status)  # 当前案件预览状态字典

    # 在调用方显式要求确认预览时，把当前状态切换为已确认。
    if confirmed_preview:

        # 把预览确认标记切换为真值，允许当前案件继续进入正式后链。
        dict_preview_status["confirmed"] = True  # 预览确认布尔值

        # 把预览状态切换为 confirmed，保持 JSON 状态文本与布尔值一致。
        dict_preview_status["status"] = "confirmed"  # 预览状态文本

        # 把更新后的预览状态写回案件目录，供后链与测试共同读取。
        module_runtime_support.write_json_file(path_preview_status, dict_preview_status)

    # 返回当前案件最新的预览状态字典，供主流程继续判断是否停在确认门。
    return dict_preview_status

# 组装预览待确认阶段的 JSON 载荷，保持既有测试依赖的键名与空值契约不变。
def build_pending_payload(preview_checkpoint: PreviewCheckpoint) -> dict[str, str]:
    """组装预览待确认载荷。

    参数：
    - `preview_checkpoint`：包含案件目录与预览 Markdown 路径的阶段结果。

    返回：
    - `dict[str, str]`：预览待确认阶段的机器可读 JSON 载荷。

    异常：
    - 无。
    """

    # 返回正式预览门待确认载荷，默认只暴露案件目录和预览源稿路径。
    return {
        "delivery_status": "preview_pending",
        "case_dir": str(preview_checkpoint.path_case_dir.resolve()),
        "preview_markdown": str(preview_checkpoint.path_preview_markdown.resolve()),
    }

# 收集正式交付包中的附图文件路径列表，默认优先返回 PNG+SVG 双输出资产。
def collect_delivery_figure_files(path_case_dir: Path) -> list[str]:
    """收集正式交付包中的附图文件路径列表。

    参数：
    - `path_case_dir`：当前案件根目录路径。

    返回：
    - `list[str]`：按稳定顺序排列的正式附图文件绝对路径列表。

    异常：
    - 无。
    """

    # 固定正式附图目录路径，供交付包文件收集逻辑统一复用。
    path_figures_dir = path_case_dir / "05_figures"  # 正式附图目录路径

    # 先固定默认正式交付承诺中的附图文件名顺序，保证返回列表稳定可预测。
    list_default_names = ["图1_方法流程图.png", "图1_方法流程图.svg", "图2_系统模块图.png", "图2_系统模块图.svg"]  # 默认正式附图文件名列表

    # 再把默认附图文件名映射成正式附图路径列表，供存在性检查和结果返回复用。
    list_default_paths = [path_figures_dir / str_name for str_name in list_default_names]  # 默认正式附图路径列表

    # 仅保留已经真实落盘的默认附图文件，避免把不存在的路径写进机器可读结果。
    list_existing_paths = [path_item.resolve() for path_item in list_default_paths if path_item.exists()]  # 已存在的默认正式附图路径列表

    # 在默认交付附图已经存在时直接按受控顺序返回。
    if list_existing_paths:

        # 返回默认正式附图路径列表，保证输出契约顺序稳定。
        return [str(path_item) for path_item in list_existing_paths]

    # 回退扫描图号文件，兼容后续扩展附图数量时的最小交付列表生成。
    return [
        str(path_item.resolve())
        for path_item in sorted(path_figures_dir.glob("图*.*"))
        if path_item.suffix.lower() in {".png", ".svg"}
    ]

# 在预览已确认后执行正文、附图、权利要求、自检与可选导出阶段。
def run_post_preview_chain(
    path_case_dir: Path,
) -> PostPreviewChainResult:
    """执行预览确认后的正式后链。

    参数：
    - `path_case_dir`：当前案件根目录路径。

    返回：
    - `PostPreviewChainResult`：包含退出码与机器可读 JSON 载荷的后链结果。

    异常：
    - 任一强制成功子入口失败时抛出 `RuntimeError`。
    - 自检入口返回异常退出码时抛出 `RuntimeError`。
    """

    # 先准备正式正文入口参数，确保正文固定围绕当前案件目录落盘。
    list_draft_args = ["--case-dir", str(path_case_dir)]  # 正文生成入口参数列表

    # 执行正式正文入口，生成交底书主草稿与来源证据映射。
    completed_process_draft = run_required_stage(PATH_GENERATE_DRAFT_SCRIPT, list_draft_args)  # 正文生成入口执行结果对象

    # 解析正文入口返回的主草稿路径，供后续附图、权利要求和自检复用。
    path_draft = read_output_path(completed_process_draft)  # 正文主草稿路径

    # 先准备附图入口参数，确保附图阶段读取当前正文并把产物写回当前案件。
    list_figures_args = ["--case-dir", str(path_case_dir), "--input", str(path_draft)]  # 附图入口参数列表

    # 执行附图入口，生成与当前正文对应的附图清单与占位图示文件。
    completed_process_figures = run_required_stage(PATH_GENERATE_FIGURES_SCRIPT, list_figures_args)  # 附图入口执行结果对象

    # 解析附图入口返回的附图清单路径，供内部 review 和交付包路径收集复用。
    path_figures_manifest = read_output_path(completed_process_figures)  # 附图清单路径

    # 先准备权利要求入口参数，确保权利要求阶段消费的是当前正文主稿。
    list_claims_args = ["--case-dir", str(path_case_dir), "--input", str(path_draft)]  # 权利要求入口参数列表

    # 执行权利要求入口，生成与当前正文对应的权利要求草案与映射文件。
    completed_process_claims = run_required_stage(PATH_GENERATE_CLAIMS_SCRIPT, list_claims_args)  # 权利要求入口执行结果对象

    # 读取权利要求入口返回路径，只把它当作内部落盘校验信号而不进入公开交付结果。
    _ = read_output_path(completed_process_claims)  # 权利要求内部工件落盘校验路径

    # 先准备自检入口参数，确保自检阶段针对当前正文主稿输出对应报告。
    list_review_args = ["--case-dir", str(path_case_dir), "--input", str(path_draft)]  # 自检入口参数列表

    # 执行自检入口，允许其通过退出码区分 blocked、needs_revision 与通过状态。
    completed_process_review = run_child_entrypoint(PATH_VALIDATE_DISCLOSURE_SCRIPT, list_review_args)  # 自检入口执行结果对象

    # 在自检入口返回了协议外退出码时立即报错，避免主流程误判状态。
    if completed_process_review.returncode not in (0, 1, 2):

        # 抛出明确错误，提示当前自检入口没有遵守既定退出码协议。
        raise RuntimeError(
            "> ERR: [Python] 自检入口执行异常。\n"
            f"stdout:\n{completed_process_review.stdout}\n"
            f"stderr:\n{completed_process_review.stderr}"
        )

    # 读取自检报告路径并解析统一状态，供 DOCX 导出后保留视觉验收门而不误标 completed。
    path_validation_report = read_output_path(completed_process_review)  # 自检报告内部落盘校验路径

    # 解析自检报告正文，后续状态传播只读取结构化字段。
    dict_validation_report = json.loads(path_validation_report.read_text(encoding="utf-8"))  # 自检报告结构化数据

    # 缺少状态字段时采用需修订状态，禁止宽松推断为完成。
    str_validation_status = str(dict_validation_report.get("status", "needs_revision"))  # 自检报告统一状态

    # 先准备后链返回载荷字典，默认仅围绕正式交付包暴露机器可读字段。
    dict_payload: dict[str, Any] = {"case_dir": str(path_case_dir.resolve())}  # 正式后链返回载荷字典

    # 在自检报告状态为 blocked 时写回阻断状态并返回退出码 1。
    if completed_process_review.returncode == 1:

        # 把当前交付状态标记为 blocked，提醒调用方当前案件仍不能进入正式交付态。
        dict_payload["delivery_status"] = "blocked"  # 阻断状态文本

        # 返回 blocker 对应的退出码与当前机器可读载荷。
        return PostPreviewChainResult(int_return_code=1, dict_payload=dict_payload)

    # 在自检报告状态为 needs_revision 时写回待修订状态并返回退出码 2。
    if completed_process_review.returncode == 2:

        # 把当前交付状态标记为 needs_revision，提醒先修正文稿再生成正式交付包。
        dict_payload["delivery_status"] = "needs_revision"  # 待修订状态文本

        # 返回待修订对应的退出码与当前机器可读载荷。
        return PostPreviewChainResult(int_return_code=2, dict_payload=dict_payload)

    # 先准备 DOCX 导出入口参数，确保导出件与当前正式 Markdown 主稿一一对应。
    list_export_args = ["--case-dir", str(path_case_dir), "--input", str(path_draft)]  # DOCX 导出入口参数列表

    # 把当前正文转成正式导出件，导出器内部会执行严格模板与媒体嵌入校验。
    completed_process_export = run_required_stage(PATH_EXPORT_DOCX_SCRIPT, list_export_args)  # DOCX 导出入口执行结果对象

    # 解析导出入口返回的 DOCX 路径，供正式交付包结果复用。
    path_delivery_docx = read_output_path(completed_process_export).resolve()  # 正式 DOCX 交付件路径

    # 直接从附图清单定位附图目录根，避免再次扫描案件树猜测正式交付目录。
    path_delivery_figures_dir = path_figures_manifest.parent.resolve()  # 交付包附图目录根路径

    # 生成返回给调用方的附图文件序列，优先固定默认双格式资产。
    list_delivery_figure_files = collect_delivery_figure_files(path_case_dir)  # 正式附图文件绝对路径列表

    # 在语义自检通过且正式交付件落盘后写回完整交付包字段；视觉验收状态不得提前完成。
    dict_payload.update(
        {
            "delivery_docx": str(path_delivery_docx),  # 主交付 DOCX 路径
            "delivery_markdown": str(path_draft.resolve()),  # 正式源稿 Markdown 路径
            "delivery_figures_dir": str(path_delivery_figures_dir),  # 返回给调用方的附图目录根路径
            "delivery_figure_files": list_delivery_figure_files,  # 返回给调用方的附图文件序列
            "delivery_status": str_validation_status,  # 已导出但仍可能待视觉审阅的交付包状态文本
        }
    )

    # 返回正式完成状态和当前机器可读载荷。
    return PostPreviewChainResult(int_return_code=0, dict_payload=dict_payload)

# 把机器可读 JSON 载荷写到标准输出，供测试与自动化调用方稳定解析。
def write_json_stdout(dict_payload: dict[str, Any]) -> None:
    """把机器可读 JSON 载荷写到标准输出。

    参数：
    - `dict_payload`：需要写到标准输出的机器可读 JSON 载荷。

    返回：
    - `None`。

    异常：
    - JSON 序列化失败时由底层异常上抛。
    """

    # 先把当前载荷序列化为单行 JSON 文本，保持上游测试解析逻辑稳定。
    str_json_payload = json.dumps(dict_payload, ensure_ascii=False)  # 单行 JSON 载荷文本

    # 再把 JSON 文本编码成 UTF-8 字节，保证 Windows 重定向场景也能稳定保留中文路径。
    bytes_json_payload = (str_json_payload + "\n").encode("utf-8")  # UTF-8 编码后的 JSON 载荷字节串

    # 优先直接写入底层缓冲区，避免标准输出文本编码把中文附图路径退回本地代码页。
    stream_stdout_buffer = getattr(sys.stdout, "buffer", None)  # 标准输出底层二进制缓冲区对象

    # 在当前标准输出暴露了底层缓冲区时，直接按 UTF-8 字节写回机器可读结果。
    if stream_stdout_buffer is not None:

        # 把 UTF-8 编码后的 JSON 载荷写入底层缓冲区，确保重定向文件可按 UTF-8 解码。
        stream_stdout_buffer.write(bytes_json_payload)

        # 立即刷新底层缓冲区，避免调用方在短进程场景读到不完整结果。
        stream_stdout_buffer.flush()

        # 当前机器可读载荷已经完成写回，无需再走文本 stdout 回退分支。
        return

    # 在极少数没有 buffer 的标准输出替身场景下，退回文本写法以保持测试替身兼容。
    sys.stdout.write(bytes_json_payload.decode("utf-8"))

    # 刷新文本标准输出，避免替身流在短进程场景丢失最后一行 JSON。
    sys.stdout.flush()

# 执行正式流水线主入口，并严格遵守预览确认门与后链退出码协议。
def main() -> int:
    """执行正式流水线主入口。

    参数：
    - 无。

    返回：
    - `int`：预览待确认返回 `2`，自检阻断返回 `1`，待修订返回 `2`，通过返回 `0`。

    异常：
    - 参数无效、共享支持加载失败或任一关键子入口失败时由底层异常上抛。
    """

    # 加载共享运行时支持模块，复用正式主链对 JSON 读写的一致约定。
    module_runtime_support = load_runtime_support_module()  # 共享运行时支持模块

    # 解析并校验命令行参数，确定当前属于新建案件还是续跑案件。
    namespace_arguments = parse_arguments()  # 正式流水线入口参数对象

    # 在调用方显式给出案件目录时先补齐或定位既有预览材料。
    if namespace_arguments.case_dir:

        # 解析续跑案件目录绝对路径，确保后续所有子入口都定位到同一案件空间。
        path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 续跑案件根目录路径

        # 确保当前案件已经存在可用预览材料，缺失时自动补生成后再继续后链判断。
        path_preview_markdown = ensure_existing_preview(path_case_dir)  # 补生成或复用后的预览 Markdown 路径

        # 组装续跑案件的预览检查点，供确认门和最终返回载荷共同复用。
        preview_checkpoint_state = PreviewCheckpoint(path_case_dir, path_preview_markdown)  # 续跑案件的预览检查点

    # 在未给出案件目录时按新建案件主链推进到预览阶段。
    else:

        # 从研究材料新建案件并推进到预览阶段，建立正式确认门上下文。
        preview_checkpoint_state = create_case_until_preview(namespace_arguments)  # 新建案件推进到预览阶段后的检查点

    # 在需要时更新预览确认状态，并读取当前案件最新的确认门结果。
    # 先把调用方是否显式确认预览整理成布尔值，供确认门逻辑直接复用。
    bool_confirmed_preview = bool(namespace_arguments.confirmed_preview)  # 调用方是否显式确认预览

    # 根据调用方确认动作刷新 preview_status.json，并读取这次执行应遵循的确认门状态。
    dict_preview_status = apply_preview_confirmation(  # 当前案件最新的预览状态字典
        preview_checkpoint_state.path_case_dir,  # 需要刷新 preview_status.json 的案件目录
        bool_confirmed_preview,  # 调用方是否要求在本轮执行前确认预览
        module_runtime_support,  # 共享 JSON 读写支持模块对象
    )

    # 在预览尚未确认时把当前案件停在 preview_pending，并返回受控退出码。
    if not dict_preview_status.get("confirmed"):

        # 组装预览待确认载荷，保持现有测试依赖的键名和空草稿约束。
        dict_pending_payload = build_pending_payload(preview_checkpoint_state)  # 预览待确认阶段 JSON 载荷

        # 把预览待确认载荷写回标准输出，供上游测试与自动化工具解析。
        write_json_stdout(dict_pending_payload)

        # 用退出码 2 表示当前案件仍停在预览确认门。
        return 2

    # 把已经通过确认门的案件目录交给正式后链执行器继续推进。
    post_preview_chain_result_state = run_post_preview_chain(  # 预览确认后的正式后链结果
        preview_checkpoint_state.path_case_dir  # 已通过确认门的案件目录
    )

    # 复制一份后链结果载荷，保持正式交付包结果与内部执行态隔离。
    dict_result_payload = dict(post_preview_chain_result_state.dict_payload)  # 后链结果载荷副本

    # 把完整结果载荷写回标准输出，供测试和自动化工具继续解析。
    write_json_stdout(dict_result_payload)

    # 返回正式后链结果中的既定退出码，保持 blocked/needs_revision/completed 协议不变。
    return post_preview_chain_result_state.int_return_code

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())

