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

# 固定命名能力预检入口，流水线必须在本轮首次输出前完成所需能力检查。
PATH_CAPABILITY_PREFLIGHT = Path(__file__).resolve().parents[1] / "support" / "check_dependencies.py"  # 能力预检入口路径

# Model 4 来源链集中在支持模块，pipeline 不复制哈希和路径边界。
PATH_MODEL4_PROVENANCE = Path(__file__).resolve().parents[1] / "support" / "model_provenance.py"  # Model 4 来源链模块

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

# 固定 CNIPA 在线检索入口，显式查询不得只选择能力而不执行生产实现。
PATH_CNIPA_SEARCH_SCRIPT = PATH_PYTHON_ROOT / "search" / "cnipa_epub_search.py"  # CNIPA 在线检索公共入口

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

# 固定后链准备阶段产生的权威工件，避免后续阶段重新猜测路径。
@dataclass(frozen=True)
class PostPreviewArtifacts:
    """后链准备阶段的工件集合。"""

    # 保存公共自检和导出共同消费的正式正文。
    path_draft: Path  # 正式正文路径

    # 保存交付阶段定位附图目录所需的正式清单。
    path_figures_manifest: Path  # 正式附图清单路径

    # 保存 reviewed 重入时必须显式传递的唯一模型。
    path_authoritative_model: Path | None  # reviewed 重入的权威模型路径

# 固定公共自检入口的协议结果，供状态分流与交付阶段共同消费。
@dataclass(frozen=True)
class PostPreviewValidation:
    """后链公共自检结果。"""

    # 保存公共入口用于业务状态分流的退出码。
    int_return_code: int  # 公共自检入口退出码

    # 保存验证报告中用于交付状态传播的统一结论。
    str_status: str  # 自检报告中的统一状态

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

# 加载命名能力预检模块，保持安装副本内自包含。
def load_capability_module() -> Any:
    """加载流水线使用的能力预检模块。

    参数：
    - 无。

    返回：
    - `Any`：已经执行的能力预检模块。

    异常：
    - `ImportError`：无法定位或加载能力模块时抛出。
    """

    # 根据安装副本内真实路径构造能力模块规格。
    obj_spec = importlib.util.spec_from_file_location(  # 流水线能力模块规格
        "readable_patent_pipeline_capabilities",  # 隔离能力模块名
        PATH_CAPABILITY_PREFLIGHT,  # 安装副本内预检入口
    )

    # 缺少规格或加载器时禁止绕过预检。
    if obj_spec is None or obj_spec.loader is None:

        # 抛出明确能力边界错误。
        raise ImportError("> ERR: [Python] 无法加载 support/check_dependencies.py。")

    # 根据有效规格创建本轮能力模块。
    module_capability = importlib.util.module_from_spec(obj_spec)  # 当前流水线能力模块

    # 执行能力预检源码，使报告构造入口可用。
    obj_spec.loader.exec_module(module_capability)

    # 返回已经初始化的能力模块。
    return module_capability

# 收集研究材料中的文件扩展名，用于只选择真实输入需要的读取能力。
def collect_research_suffixes(path_research_root: Path) -> set[str]:
    """收集研究输入文件扩展名。

    参数：
    - `path_research_root`：本轮研究材料文件或目录。

    返回：
    - `set[str]`：小写文件扩展名集合。

    异常：
    - 无；路径不存在时返回空集合，后续正式入口负责路径错误。
    """

    # 单文件输入直接返回其扩展名。
    if path_research_root.is_file():

        # 空扩展名不会触发 Office 或 PDF 能力。
        return {path_research_root.suffix.lower()} if path_research_root.suffix else set()

    # 不存在或不是目录的输入暂不推断可选读取能力。
    if not path_research_root.is_dir():

        # 保持只要求 core-model，由正式建案入口报告路径问题。
        return set()

    # 递归扫描真实材料文件，目录名不参与能力推导。
    set_suffixes = {  # 本轮研究材料扩展名集合
        path_item.suffix.lower()  # 统一小写扩展名
        for path_item in path_research_root.rglob("*")  # 遍历研究目录下全部条目
        if path_item.is_file() and path_item.suffix  # 只保留带扩展名的文件
    }

    # 返回实际出现的输入格式集合。
    return set_suffixes

# 判断本轮调用是否会进入生成附图和最终公式的确认后链。
def will_run_post_preview(namespace_arguments: argparse.Namespace) -> bool:
    """判断本轮是否需要确认后链能力。

    参数：
    - `namespace_arguments`：已经解析的流水线参数。

    返回：
    - `bool`：本轮会进入确认后链时返回 `True`。

    异常：
    - 状态文件读取失败时返回保守的参数推断结果。
    """

    # 显式确认或 reviewed model 重入一定会请求确认后链。
    if namespace_arguments.confirmed_preview or namespace_arguments.reviewed_model:

        # 本轮需要附图和公式导出能力。
        return True

    # 新建案件且未显式确认时只推进到预览，不需要后链能力。
    if not namespace_arguments.case_dir:

        # 预览阶段不应被未使用的图件或桌面公式能力阻断。
        return False

    # 既有案件可能已在前次调用中确认预览。
    path_preview_status = Path(namespace_arguments.case_dir).resolve() / "03_drafts" / "preview_status.json"  # 既有预览状态路径

    # 缺少状态文件时后续会刷新预览，本轮先按未确认处理。
    if not path_preview_status.is_file():

        # 不提前强制后链可选能力。
        return False

    # 尝试读取已确认状态，损坏文件交给正式预览流程报告。
    try:

        # 解析预览状态 JSON。
        dict_preview_status = json.loads(path_preview_status.read_text(encoding="utf-8"))  # 既有预览状态

    # 文件或 JSON 异常时不在能力推导阶段掩盖正式诊断。
    except (OSError, TypeError, ValueError, json.JSONDecodeError):

        # 保守保持预览阶段能力集合。
        return False

    # 只有明确 confirmed=true 才视为本轮会进入后链。
    return bool(dict_preview_status.get("confirmed", False))

# 根据真实输入格式和本轮输出请求推导最小能力集合。
def determine_required_capabilities(namespace_arguments: argparse.Namespace) -> list[str]:
    """推导流水线本轮必需能力。

    参数：
    - `namespace_arguments`：已经解析的流水线参数。

    返回：
    - `list[str]`：按执行依赖顺序排列的能力名称。

    异常：
    - 无。
    """

    # Model 4 与 Claims 3 验证贯穿全部流水线阶段。
    list_capabilities = ["core-model"]  # 本轮最小能力集合

    # 新建案件根据真实研究材料扩展名选择读取能力。
    if namespace_arguments.research_root:

        # 扫描本轮输入格式。
        set_suffixes = collect_research_suffixes(Path(namespace_arguments.research_root).resolve())  # 研究材料扩展名

        # DOCX 和 PPTX 输入需要 Office 读取能力。
        if set_suffixes.intersection({".docx", ".pptx"}):

            # 追加 Office 材料读取能力。
            list_capabilities.append("office-intake")

        # PDF 输入独立选择 PDF 读取能力。
        if ".pdf" in set_suffixes:

            # 将独立 PDF 解析能力加入本轮阻断集合。
            list_capabilities.append("pdf-intake")

    # 显式在线检索请求必须选择与 urllib 生产入口对应的 CNIPA 能力。
    if str(getattr(namespace_arguments, "cnipa_query", "")).strip():

        # 把在线检索能力加入输出前阻断集合。
        list_capabilities.append("cnipa-search")

    # 只有本轮会进入确认后链时才要求附图和公式能力。
    if will_run_post_preview(namespace_arguments):

        # 正式后链固定生成技术附图。
        list_capabilities.append("figures")

        # Office 模式只需要纯 OMML 转换链。
        if namespace_arguments.equation_mode == "office":

            # 追加 Office 原生公式能力。
            list_capabilities.append("formula-omml")

        # MathType 模式需要 Windows Word 与 Equation.DSMT4。
        else:

            # 追加原生 MathType 桌面运行时能力。
            list_capabilities.append("native-mathtype")

    # 返回不含未使用可选项的能力序列。
    return list_capabilities

# 在流水线首次写出案件产物前阻断缺失的必需能力。
def require_pipeline_capabilities(namespace_arguments: argparse.Namespace) -> dict[str, Any]:
    """执行本轮流水线能力预检。

    参数：
    - `namespace_arguments`：已经解析的流水线参数。

    返回：
    - `dict[str, Any]`：全部能力诊断与本轮选择结果。

    异常：
    - `RuntimeError`：任一本轮必需能力未就绪时抛出。
    """

    # 加载安装副本内能力实现。
    module_capability = load_capability_module()  # 流水线能力预检模块

    # 依据真实输入和本轮阶段推导最小能力集合。
    list_capabilities = determine_required_capabilities(namespace_arguments)  # 本轮必需能力

    # 构造完整诊断，但只让本轮能力参与阻断。
    dict_report = module_capability.build_report(list_capabilities)  # 本轮能力预检报告

    # 任一选中能力缺失时禁止创建或更新案件输出。
    if not dict_report["ready"]:

        # 汇总能力名称，保持错误文本简短且可操作。
        str_missing = ", ".join(dict_report["missing_selected"])  # 本轮缺失能力摘要

        # 抛出统一前缀错误，调用方可先独立运行 check_dependencies --json。
        raise RuntimeError(f"> ERR: [Python] 流水线必需能力未就绪：{str_missing}")

    # 返回报告供测试和未来调用方审计本轮选择。
    return dict_report

# 按文件路径加载 Model 4 来源链支持模块。
def load_model4_provenance_module() -> Any:
    """加载 Model 4 来源链模块。

    参数：
    - 无。

    返回：
    - `Any`：已经执行源码的来源链模块。

    异常：
    - `ImportError`：模块规格或加载器缺失时抛出。
    """

    # 根据正式支持模块路径创建隔离加载规格。
    obj_spec = importlib.util.spec_from_file_location(  # Model 4 来源链加载规格
        "readable_patent_model4_provenance",  # 与其他动态模块隔离的名称
        PATH_MODEL4_PROVENANCE,  # 正式来源链模块路径
    )  # 来源链模块加载规格

    # 规格或加载器缺失时禁止跳过案件绑定验证。
    if obj_spec is None or obj_spec.loader is None:

        # 抛出指向正式模块的明确导入错误。
        raise ImportError("> ERR: [Python] 无法加载 support/model_provenance.py。")

    # 根据已验证规格创建本轮独享的来源链模块。
    module_provenance = importlib.util.module_from_spec(obj_spec)  # 待执行来源链模块实例

    # 执行正式模块源码，使封印和验证入口可用。
    obj_spec.loader.exec_module(module_provenance)

    # 返回已经初始化的唯一来源链规则实现。
    return module_provenance

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

    # 注册显式 CNIPA 在线检索词，空值保持可选能力不参与阻断。
    obj_parser.add_argument(
        "--cnipa-query",  # 在线检索词参数名
        default="",  # 空值表示本轮不使用 CNIPA 能力
        help="Optional keyword query executed by the CNIPA public entrypoint.",  # CLI 帮助文本
    )

    # 注册新建案件输出根目录参数，供本地 runs 目录定向落盘复用。
    obj_parser.add_argument("--output-root", default="runs/patent_cases")

    # 注册建案技术类型，默认保持通用规则以兼容既有流水线调用。
    obj_parser.add_argument(  # 新案件技术类型参数
        "--technical-profile",
        choices=("general", "ai_algorithm"),
        default="general",
        help="Examination profile explicitly selected for a new case.",
    )

    # 注册AI专项适用范围，仅在显式选择AI类型时生效。
    obj_parser.add_argument(  # AI专项规则范围参数
        "--ai-scope",
        choices=("model_training", "model_application", "both"),
        default="",
        help="Required for a new ai_algorithm case.",
    )

    # 注册疑似AI案件的用户确认决定，续跑时可明确保持通用或切换AI。
    obj_parser.add_argument(  # 技术类型确认参数
        "--confirm-technical-profile",
        choices=("general", "ai_algorithm"),
        default="",
        help="Explicit decision for a profile suggestion shown in preview_status.json.",
    )

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

    # 注册已嵌入审查的权威模型，用于正式后链重入时跳过正文和模型再生成。
    obj_parser.add_argument(
        "--reviewed-model",
        help="Authoritative reviewed Model 4.0 used for post-preview reentry.",
    )

    # 注册公式兼容模式并透传给正式 DOCX 导出入口。
    obj_parser.add_argument(  # 公式兼容模式参数
        "--equation-mode",  # 流水线参数名称
        choices=("office", "mathtype"),  # Office OMML 或原生 MathType OLE
        default="mathtype",  # 默认生成原生 MathType OLE 公式对象
        help="Editable equation mode for the final DOCX.",  # 参数说明
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

    # 新建AI案件必须明确专项规则适用范围。
    if namespace_arguments.technical_profile == "ai_algorithm" and not namespace_arguments.ai_scope:

        # 通过同一解析器报告条件必填错误。
        argument_parser_for_validation.error("--ai-scope 在 --technical-profile=ai_algorithm 时必填。")

    # 通用案件不接受AI范围，避免建案配置内部矛盾。
    if namespace_arguments.technical_profile == "general" and namespace_arguments.ai_scope:

        # 要求调用方删除scope或显式选择AI类型。
        argument_parser_for_validation.error("--ai-scope 仅适用于 --technical-profile=ai_algorithm。")

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

# 通过正式 CNIPA 公共入口执行显式在线检索。
def run_cnipa_online_search(str_query: str) -> list[dict[str, Any]]:
    """执行 CNIPA 在线检索并解析结构化命中。

    参数：
    - `str_query`：调用方显式提供的在线检索词。

    返回：
    - `list[dict[str, Any]]`：公共入口返回的结构化专利命中。

    异常：
    - 公共入口失败、输出不是 JSON 数组或数组元素损坏时抛出。
    """

    # 使用生产检索入口而不是在 pipeline 内复制 urllib 和解析规则。
    completed_process_search = run_required_stage(  # CNIPA 在线检索子进程结果
        PATH_CNIPA_SEARCH_SCRIPT,  # 标准库 urllib 在线检索入口
        ["--query", str_query],  # 调用方明确要求的检索词
    )

    # 公共入口声明 JSON stdout 协议，pipeline 直接解析完整数组。
    obj_hits = json.loads(completed_process_search.stdout)  # CNIPA 在线命中原始对象

    # 非数组输出表示生产入口协议已经断链，不能写出伪造结果文件。
    if not isinstance(obj_hits, list) or not all(isinstance(obj_item, dict) for obj_item in obj_hits):

        # 抛出稳定错误，阻止后续案件输出掩盖在线检索协议错误。
        raise ValueError("> ERR: [Python] CNIPA 在线检索入口必须返回 JSON 对象数组。")

    # 返回逐项类型已核验的命中集合。
    return obj_hits

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
        "--technical-profile",  # 技术类型参数名
        namespace_arguments.technical_profile,  # 用户显式选择的技术类型
    ]

    # AI案件需要把专项适用范围继续透传给建案入口。
    if namespace_arguments.ai_scope:

        # 追加scope参数，通用案件保持空配置且不传无效值。
        list_create_case_args.extend(["--ai-scope", namespace_arguments.ai_scope])

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
    """刷新既有案件目录下的预览材料。

    参数：
    - `path_case_dir`：当前案件根目录路径。

    返回：
    - `Path`：当前案件可用的预览 Markdown 路径。

    异常：
    - 预览刷新失败时抛出 `RuntimeError`。
    """

    # 准备预览刷新参数，使事实审核决定变化后能够重新计算 review_closed。
    list_preview_args = ["--case-dir", str(path_case_dir)]  # 预览刷新入口参数列表

    # 每次续跑都刷新预览状态，禁止以已存在的 Markdown 代替当前审核闭包检查。
    completed_process_preview = run_required_stage(PATH_GENERATE_PREVIEW_SCRIPT, list_preview_args)  # 预览刷新入口执行结果对象

    # 返回刷新后的预览 Markdown 路径，供后续确认门判断复用。
    return read_output_path(completed_process_preview)

# 在需要时把预览状态切换为已确认，并返回当前案件最新的预览状态字典。
def apply_preview_confirmation(
    path_case_dir: Path,
    confirmed_preview: bool,
    module_runtime_support: Any,
    confirmed_profile: str = "",
    ai_scope: str = "",
) -> dict[str, Any]:
    """按需要更新预览确认状态。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `confirmed_preview`：是否在本轮执行前强制把预览标记为已确认。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `confirmed_profile`：用户对技术类型建议作出的明确决定。
    - `ai_scope`：用户切换AI类型时明确选择的专项适用范围。

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

    # 用户提供类型决定时同步更新案件配置和预览确认状态。
    if confirmed_profile:

        # 固定案件配置路径，保证用户决定可跨会话追溯。
        path_case_config = path_case_dir / "case_config.json"  # 当前案件配置路径

        # 读取建案配置并保留其他入口字段不变。
        dict_case_config = module_runtime_support.read_json_file(path_case_config)  # 当前案件配置内容

        # 切换到AI类型时必须同时提供或沿用合法scope。
        str_effective_ai_scope = ai_scope or str(dict_case_config.get("ai_scope", ""))  # 本轮有效AI适用范围

        # 缺少AI范围会导致专项规则无法确定，确认动作必须失败。
        if confirmed_profile == "ai_algorithm" and not str_effective_ai_scope:

            # 要求用户在确认切换AI时同步选择适用范围。
            raise ValueError("> ERR: [Python] 确认 ai_algorithm 时必须提供 --ai-scope。")

        # 保存用户最终选择，后续预览不得重新覆盖该决定。
        dict_case_config["technical_profile"] = confirmed_profile  # 用户确认后的技术类型

        # 单独记录确认值，区分建案默认值与用户后续明确决定。
        dict_case_config["profile_confirmation"] = confirmed_profile  # 持久化的类型确认决定

        # AI案件保存有效scope，保持通用时清空不适用字段。
        dict_case_config["ai_scope"] = str_effective_ai_scope if confirmed_profile == "ai_algorithm" else ""  # 确认后的AI范围

        # 把更新后的案件配置写回统一入口文件。
        module_runtime_support.write_json_file(path_case_config, dict_case_config)

        # 读取预览中的建议信息，保留系统提示与用户决定的审计关系。
        dict_profile_check = dict(dict_preview_status.get("profile_check", {}))  # 预览技术类型检查结果

        # 先保存用户决定后的有效类型，不删除系统原始建议。
        dict_profile_check["effective_profile"] = confirmed_profile  # 用户决定后的有效类型

        # 再解除独立类型确认门，允许后续确认整份预览。
        dict_profile_check["confirmation_required"] = False  # 类型确认门已解除

        # 记录保持通用或切换AI的稳定审计标签。
        dict_profile_check["decision"] = "keep_general" if confirmed_profile == "general" else "switch_to_ai_algorithm"  # 用户决定标签

        # 将更新后的检查对象放回预览状态根结构。
        dict_preview_status["profile_check"] = dict_profile_check  # 更新后的技术类型检查结果

        # 即使本轮尚未确认整份预览，也必须持久化独立的类型决定。
        module_runtime_support.write_json_file(path_preview_status, dict_preview_status)

    # 预览确认不能绕过尚未完成的技术类型确认门。
    if confirmed_preview and dict_preview_status.get("profile_check", {}).get("confirmation_required"):

        # 要求调用方先对疑似AI建议给出明确决定。
        raise ValueError("> ERR: [Python] 请先使用 --confirm-technical-profile 明确案件技术类型。")

    # 命令行确认不能绕过逐项事实复核门，且要纠正外部直接写入的非法确认状态。
    if confirmed_preview and not dict_preview_status.get("review_closed", False):

        # 恢复未确认状态，阻止主流程在事实复核仍有待决项时进入正式后链。
        dict_preview_status["confirmed"] = False  # 事实复核未闭环时的预览确认标记

        # 同步恢复状态文本，避免布尔值与文本状态表达相互矛盾。
        dict_preview_status["status"] = "pending_confirmation"  # 事实复核未闭环时的预览状态

        # 持久化纠正后的状态，使后续重试和审计读取同一事实。
        module_runtime_support.write_json_file(path_preview_status, dict_preview_status)

        # 立即返回纠正后的状态，统一复用主流程已有的 preview_pending 返回路径。
        return dict_preview_status

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

# 定位重入案件的既有正文，禁止为取得路径而重新生成并覆盖 Model 4.0。
def find_existing_draft(path_case_dir: Path) -> Path:
    """定位案件中已经存在的正式正文草稿。

    参数：
    - `path_case_dir`：当前重入案件根目录。

    返回：
    - `Path`：已经存在的正式正文草稿绝对路径。

    异常：
    - `FileNotFoundError`：案件中不存在正式正文草稿时抛出。
    """

    # 加载共享运行时支持模块，复用正式正文定位规则。
    module_runtime_support: Any = load_runtime_support_module()  # 确认状态读写支持对象

    # 只查找已有正文，不调用任何生成入口。
    path_draft = module_runtime_support.find_disclosure_draft(path_case_dir, None)  # 既有正文草稿路径

    # 正文缺失时拒绝 reviewed-model 重入，避免模型与空白正文脱节。
    if path_draft is None or not path_draft.exists():

        # 抛出明确文件缺失错误，提示调用方先完成首次正文生成。
        raise FileNotFoundError("> ERR: [Python] reviewed-model 重入缺少既有 disclosure draft。")

    # 返回规范化绝对路径，确保后续子入口消费同一正文。
    return path_draft.resolve()

# 校验 reviewed Model 4 并定位与其绑定的既有正文。
def validate_reviewed_model_artifact(
    path_case_dir: Path,
    path_reviewed_model: Path,
) -> tuple[Path, Path]:
    """校验 reviewed Model 4 与当前案件的来源链。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `path_reviewed_model`：调用方显式提交的 reviewed Model 4。

    返回：
    - `tuple[Path, Path]`：权威模型和既有正文的绝对路径。

    异常：
    - 模型缺失、版本错误或来源链不匹配时抛出对应异常。
    """

    # 规范化权威模型路径，避免后续阶段回退读取 latest 模型。
    path_authoritative_model: Path = path_reviewed_model.resolve()  # 权威模型绝对路径

    # 权威模型必须已经真实落盘。
    if not path_authoritative_model.exists():

        # 缺失时报告实际路径，便于调用方修复重入参数。
        raise FileNotFoundError(
            f"> ERR: [Python] reviewed model 不存在:{path_authoritative_model}"
        )

    # 加载正式来源链模块，复用案件身份和父工件摘要校验。
    module_provenance: Any = load_model4_provenance_module()  # 来源链验证模块

    # 对当前案件执行正式 reviewed 模型验证。
    obj_model: Any = module_provenance.validate_reviewed_model_for_case(  # 已验证模型对象
        path_case_dir,  # 当前模型所属案件
        path_authoritative_model,  # 调用方提交的唯一模型文件
    )

    # 只允许结构化 Model 4 进入正式后链。
    if not isinstance(obj_model, dict) or obj_model.get("contract_version") != "4.0":

        # 旧版本或非对象输入必须显式失败。
        raise ValueError("> ERR: [Python] --reviewed-model 必须是 Model 4.0 JSON 对象。")

    # 定位与权威模型配套的既有正文，禁止重新生成覆盖。
    path_draft: Path = find_existing_draft(path_case_dir)  # reviewed 配套正文路径

    # 返回已经完成案件绑定的两项权威路径。
    return path_authoritative_model, path_draft

# 定位 reviewed 重入必须复用的附图清单与 Claims Map 3。
def locate_reviewed_companion_artifacts(
    path_case_dir: Path,
) -> tuple[Path, Path]:
    """定位 reviewed 模型的配套工件。

    参数：
    - `path_case_dir`：当前案件根目录。

    返回：
    - `tuple[Path, Path]`：附图清单和 Claims Map 3 路径。

    异常：
    - 任一配套工件缺失时抛出 `FileNotFoundError`。
    """

    # 定位首次后链已经生成的正式附图清单。
    path_figures_manifest: Path = path_case_dir / "05_figures" / "figures_manifest.json"  # 附图清单路径

    # 定位来源链摘要已经绑定的 Claims Map 3。
    path_claims_map: Path = path_case_dir / "03_drafts" / "claims_map.json"  # reviewed 配套 claims 路径

    # 两项配套工件都必须存在，禁止重生成改变权威边界。
    for path_required_artifact in (path_figures_manifest, path_claims_map):

        # 缺少任一配套工件时拒绝 reviewed 重入。
        if not path_required_artifact.exists():

            # 报告实际缺失路径，便于恢复同一案件。
            raise FileNotFoundError(
                f"> ERR: [Python] reviewed-model 重入缺少既有配套工件:"
                f"{path_required_artifact}"
            )

    # 返回后续自检与交付阶段共用的配套路径。
    return path_figures_manifest, path_claims_map

# 首次后链按固定顺序生成正文、附图和权利要求工件。
def generate_initial_post_preview_artifacts(
    path_case_dir: Path,
) -> tuple[Path, Path, Path]:
    """生成首次后链的三类正式工件。

    参数：
    - `path_case_dir`：当前案件根目录。

    返回：
    - `tuple[Path, Path, Path]`：正文、附图清单和 Claims Map 3 路径。

    异常：
    - 任一生产入口失败或机器输出无效时抛出 `RuntimeError`。
    """

    # 执行正文生成入口并保留其机器输出。
    completed_process_draft: subprocess.CompletedProcess[str] = run_required_stage(  # 正文生成结果
        PATH_GENERATE_DRAFT_SCRIPT,  # 正文生产入口路径
        ["--case-dir", str(path_case_dir)],  # 当前案件生成参数
    )

    # 解析正式正文路径，供后续阶段共同消费。
    path_draft: Path = read_output_path(completed_process_draft)  # 后续附图与 claims 的正文输入

    # 执行附图生成入口并保留正式清单。
    completed_process_figures: subprocess.CompletedProcess[str] = run_required_stage(  # 附图生成结果
        PATH_GENERATE_FIGURES_SCRIPT,  # 附图生产入口路径
        ["--case-dir", str(path_case_dir), "--input", str(path_draft)],  # 正文绑定参数
    )

    # 解析附图入口唯一机器输出路径。
    path_figures_manifest: Path = read_output_path(completed_process_figures)  # 交付阶段附图根依据

    # 执行权利要求生成入口，形成 Claims Map 3。
    completed_process_claims: subprocess.CompletedProcess[str] = run_required_stage(  # 权利要求生成结果
        PATH_GENERATE_CLAIMS_SCRIPT,  # 权利要求生产入口路径
        ["--case-dir", str(path_case_dir), "--input", str(path_draft)],  # claims 所属案件与主稿
    )

    # 读取机器输出，确认权利要求阶段真实完成落盘。
    path_claims_output: Path = read_output_path(completed_process_claims)  # 权利要求输出校验路径

    # 固定正式 Claims Map 3 路径，供来源链封印复用。
    path_claims_map: Path = path_case_dir / "03_drafts" / "claims_map.json"  # 初始模型封印的 claims 依据

    # 保留显式校验变量，避免机器输出只被解析却未消费。
    _ = path_claims_output  # 权利要求阶段落盘证据

    # 返回首次后链产生的三类正式工件。
    return path_draft, path_figures_manifest, path_claims_map

# 在首次 claims 生成后一次性封印初始 Model 4 的案件内容摘要。
def seal_initial_post_preview_model(
    path_case_dir: Path,
    path_draft: Path,
    path_claims_map: Path,
) -> None:
    """封印首次后链的初始 Model 4。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `path_draft`：正式正文路径。
    - `path_claims_map`：Claims Map 3 路径。

    返回：
    - `None`：初始模型完成案件与内容绑定。

    异常：
    - 来源链模块加载或封印失败时由底层异常上抛。
    """

    # 加载正式来源链模块，执行唯一初始封印。
    module_provenance: Any = load_model4_provenance_module()  # 初始模型封印模块

    # 写入案件身份、正文、预览和 Claims Map 3 摘要。
    module_provenance.seal_initial_model_artifact(
        path_case_dir,
        path_case_dir / "03_drafts" / "latest_disclosure_model.json",
        path_draft,
        path_case_dir / "03_drafts" / "pre_draft_preview.md",
        path_claims_map,
    )

# 准备后链权威工件；首次运行负责生成并封印，reviewed 重入只复用既有工件。
def prepare_post_preview_artifacts(
    path_case_dir: Path,
    path_reviewed_model: Path | None,
) -> PostPreviewArtifacts:
    """准备公共自检和交付阶段需要的权威工件。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `path_reviewed_model`：可选 reviewed Model 4 路径。

    返回：
    - `PostPreviewArtifacts`：正文、附图清单与可选权威模型路径。

    异常：
    - 生成入口失败、工件缺失或来源链不匹配时抛出对应异常。
    """

    # reviewed 重入只验证并复用既有权威工件。
    if path_reviewed_model is not None:

        # 校验 reviewed 模型并定位其绑定正文。
        tuple_reviewed_paths: tuple[Path, Path] = validate_reviewed_model_artifact(  # reviewed 路径集合
            path_case_dir,  # 当前重入案件根
            path_reviewed_model,  # 显式 reviewed 模型
        )

        # 分离权威模型路径，供公共自检显式传参。
        path_authoritative_model: Path = tuple_reviewed_paths[0]  # reviewed 权威模型路径

        # 分离既有正文路径，禁止生成器覆盖 reviewed 内容。
        path_draft: Path = tuple_reviewed_paths[1]  # 公共自检使用的 reviewed 正文

        # 定位 reviewed 模型绑定的配套附图与 claims 工件。
        tuple_companion_paths: tuple[Path, Path] = locate_reviewed_companion_artifacts(  # 配套路径集合
            path_case_dir  # 配套工件所属案件根
        )

        # 分离附图清单路径，供交付阶段定位附图根。
        path_figures_manifest: Path = tuple_companion_paths[0]  # reviewed 交付附图索引

        # 分离 Claims Map 3 路径，确认配套 claims 已落盘。
        path_claims_map: Path = tuple_companion_paths[1]  # reviewed 权利要求映射依据

    # 首次后链生成正式工件并封印初始模型。
    else:

        # 首次后链没有调用方外部权威模型。
        path_authoritative_model = None  # 首次后链权威模型标记

        # 按固定顺序生成正文、附图和 Claims Map 3。
        tuple_initial_paths: tuple[Path, Path, Path] = generate_initial_post_preview_artifacts(  # 首次工件路径集合
            path_case_dir  # 当前首次后链案件根
        )

        # 分离正文路径，供来源链封印和公共自检复用。
        path_draft = tuple_initial_paths[0]  # 首次生成正文路径

        # 提取首次附图清单，供正式交付定位已生成的图件。
        path_figures_manifest = tuple_initial_paths[1]  # 首次生成附图清单路径

        # 分离 Claims Map 3 路径，供初始 Model 4 封印。
        path_claims_map = tuple_initial_paths[2]  # 首次生成 claims 路径

        # 将首次生成内容一次性绑定到初始 Model 4。
        seal_initial_post_preview_model(
            path_case_dir,
            path_draft,
            path_claims_map,
        )

    # 返回后续公共自检和导出阶段唯一消费的工件集合。
    return PostPreviewArtifacts(
        path_draft=path_draft.resolve(),
        path_figures_manifest=path_figures_manifest.resolve(),
        path_authoritative_model=path_authoritative_model,
    )

# 始终调用公共 validate_disclosure 入口，不在 pipeline 内复制或放宽审查规则。
def validate_post_preview_artifacts(
    path_case_dir: Path,
    post_preview_artifacts_obj_artifacts: PostPreviewArtifacts,
) -> PostPreviewValidation:
    """执行公共自检入口并解析稳定状态协议。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `post_preview_artifacts_obj_artifacts`：准备阶段权威工件。

    返回：
    - `PostPreviewValidation`：公共入口退出码和报告状态。

    异常：
    - 公共入口返回协议外退出码或报告无效时抛出 `RuntimeError`。
    """

    # 准备公共自检入口的案件与正文参数。
    list_review_args: list[str] = [  # 公共自检参数列表
        "--case-dir",  # 案件根参数名
        str(path_case_dir),  # 当前案件根路径
        "--input",  # 正式正文参数名
        str(post_preview_artifacts_obj_artifacts.path_draft),  # 权威正文路径
    ]

    # reviewed 重入必须把唯一权威模型显式传给公共入口。
    if post_preview_artifacts_obj_artifacts.path_authoritative_model is not None:

        # 追加权威模型参数，禁止公共入口回退 latest 模型。
        list_review_args.extend(
            [
                "--model",
                str(post_preview_artifacts_obj_artifacts.path_authoritative_model),
            ]
        )

    # 执行真实公共自检入口并保留全部协议输出。
    completed_process_review: subprocess.CompletedProcess[str] = run_child_entrypoint(  # 公共自检结果
        PATH_VALIDATE_DISCLOSURE_SCRIPT,  # 公共验证入口路径
        list_review_args,  # 当前案件验证参数
    )

    # 只接受公共入口声明的三类业务退出码。
    if completed_process_review.returncode not in (0, 1, 2):

        # 协议外退出码必须携带标准输出与错误摘要。
        raise RuntimeError(
            "> ERR: [Python] 自检入口执行异常。\n"
            f"stdout:\n{completed_process_review.stdout}\n"
            f"stderr:\n{completed_process_review.stderr}"
        )

    # 解析公共入口输出的唯一验证报告路径。
    path_validation_report: Path = read_output_path(completed_process_review)  # 验证报告路径

    # 读取结构化状态，禁止从诊断文本推断交付结论。
    dict_validation_report: dict[str, Any] = json.loads(  # 验证报告对象
        path_validation_report.read_text(encoding="utf-8")  # 公共报告 UTF-8 文本
    )

    # 返回供状态分流和交付阶段共同消费的公共验证结果。
    return PostPreviewValidation(
        int_return_code=completed_process_review.returncode,
        str_status=str(dict_validation_report.get("status", "needs_revision")),
    )

# 只在公共自检允许交付后执行 DOCX 导出，并组装稳定交付载荷。
def export_post_preview_delivery(
    path_case_dir: Path,
    str_equation_mode: str,
    post_preview_artifacts_obj_artifacts: PostPreviewArtifacts,
    post_preview_validation_obj_validation: PostPreviewValidation,
) -> dict[str, Any]:
    """导出正式交付件并返回机器可读载荷。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `str_equation_mode`：Office 或原生 MathType 公式模式。
    - `post_preview_artifacts_obj_artifacts`：准备阶段权威工件。
    - `post_preview_validation_obj_validation`：公共自检结果。

    返回：
    - `dict[str, Any]`：完整正式交付载荷。

    异常：
    - DOCX 导出失败或机器输出无效时抛出 `RuntimeError`。
    """

    # 执行正式 DOCX 导出入口，消费已通过公共自检的正文。
    completed_process_export: subprocess.CompletedProcess[str] = run_required_stage(  # DOCX 导出结果
        PATH_EXPORT_DOCX_SCRIPT,  # 正式 DOCX 导出入口路径
        [
            "--case-dir",  # 导出案件根参数名
            str(path_case_dir),  # 当前导出案件根
            "--input",  # 导出正文参数名
            str(post_preview_artifacts_obj_artifacts.path_draft),  # 已审正式正文
            "--equation-mode",  # 公式对象模式参数名
            str_equation_mode,  # 调用方确认的公式模式
        ],
    )

    # 解析正式 DOCX 路径，供交付载荷稳定引用。
    path_delivery_docx: Path = read_output_path(completed_process_export).resolve()  # DOCX 交付路径

    # 返回正式主稿、附图和状态组成的机器可读交付载荷。
    return {
        "case_dir": str(path_case_dir.resolve()),
        "delivery_docx": str(path_delivery_docx),
        "delivery_markdown": str(post_preview_artifacts_obj_artifacts.path_draft),
        "delivery_figures_dir": str(
            post_preview_artifacts_obj_artifacts.path_figures_manifest.parent.resolve()
        ),
        "delivery_figure_files": collect_delivery_figure_files(path_case_dir),
        "delivery_status": post_preview_validation_obj_validation.str_status,
    }

# 在预览已确认后按准备、自检、交付三段职责编排正式后链。
def run_post_preview_chain(
    path_case_dir: Path,
    str_equation_mode: str,
    path_reviewed_model: Path | None = None,
) -> PostPreviewChainResult:
    """执行预览确认后的正式后链。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `str_equation_mode`：Office 或原生 MathType 公式模式。
    - `path_reviewed_model`：可选 reviewed Model 4 路径。

    返回：
    - `PostPreviewChainResult`：稳定退出码与机器可读载荷。

    异常：
    - 准备、自检或导出阶段异常时由对应入口上抛。
    """

    # 准备后链唯一消费的权威工件集合。
    post_preview_artifacts_obj_artifacts: PostPreviewArtifacts = prepare_post_preview_artifacts(  # 权威工件集合
        path_case_dir,  # 工件准备所属案件
        path_reviewed_model,  # 工件准备的可选权威模型
    )

    # 通过公共 validate_disclosure 入口取得唯一审查结论。
    post_preview_validation_obj_validation: PostPreviewValidation = validate_post_preview_artifacts(  # 公共审查结论
        path_case_dir,  # 公共自检所属案件
        post_preview_artifacts_obj_artifacts,  # 准备阶段权威工件
    )

    # 初始化阻断或待修订分支使用的最小载荷。
    dict_payload: dict[str, Any] = {  # 后链机器载荷
        "case_dir": str(path_case_dir.resolve())  # 当前案件绝对路径
    }

    # 退出码一仅在非视觉待验状态下表示真实 blocker。
    if (
        post_preview_validation_obj_validation.int_return_code == 1
        and post_preview_validation_obj_validation.str_status
        != "visual_review_required"
    ):

        # 明确记录当前案件被公共自检阻断。
        dict_payload["delivery_status"] = "blocked"  # 公共自检阻断状态

        # 返回 blocker 对应退出码，不执行正式导出。
        return PostPreviewChainResult(
            int_return_code=1,
            dict_payload=dict_payload,
        )

    # 退出码二表示正文或模型需要修订。
    if post_preview_validation_obj_validation.int_return_code == 2:

        # 明确记录当前案件仍需修订。
        dict_payload["delivery_status"] = "needs_revision"  # 公共自检待修订状态

        # 返回待修订退出码，不执行正式导出。
        return PostPreviewChainResult(
            int_return_code=2,
            dict_payload=dict_payload,
        )

    # 公共自检允许交付后执行唯一正式导出入口。
    dict_payload = export_post_preview_delivery(  # 完整正式交付载荷
        path_case_dir,  # 正式导出所属案件
        str_equation_mode,  # 正式导出公式模式
        post_preview_artifacts_obj_artifacts,  # 已通过准备门的工件
        post_preview_validation_obj_validation,  # 公共自检允许交付的结论
    )

    # 返回成功退出码和完整正式交付载荷。
    return PostPreviewChainResult(
        int_return_code=0,
        dict_payload=dict_payload,
    )

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

# 统一诊断文本流编码，避免 Windows 本地代码页破坏中文协议。
def configure_utf8_text_streams() -> None:
    """固定流水线诊断流编码。

    参数：
    - 无。

    返回：
    - `None`：可重配置的标准流已切换为 UTF-8。

    异常：
    - 无。
    """

    # 逐一处理标准输出和标准错误，兼容测试替身流。
    for stream_text in (sys.stdout, sys.stderr):

        # 获取可选运行时重配置接口。
        func_reconfigure = getattr(stream_text, "reconfigure", None)  # 当前文本流编码配置函数

        # 只对真实可重配置文本流执行编码切换。
        if callable(func_reconfigure):

            # 固定 UTF-8，保证中文诊断可被跨平台调用方读取。
            func_reconfigure(encoding="utf-8")

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

    # 解析并校验命令行参数，确定当前属于新建案件还是续跑案件。
    namespace_arguments = parse_arguments()  # 正式流水线入口参数对象

    # 在任何案件输出前校验本轮真实需要的包与外部运行时。
    require_pipeline_capabilities(namespace_arguments)

    # 在线检索同样发生在案件输出前，网络或公共入口失败时不留下半成品结果。
    list_cnipa_hits = (  # 本轮显式 CNIPA 在线检索命中
        run_cnipa_online_search(namespace_arguments.cnipa_query.strip())  # 真实公共入口命中
        if namespace_arguments.cnipa_query.strip()  # 只执行调用方明确请求的在线检索
        else []  # 未使用可选检索能力时保持空集合
    )

    # 能力就绪后加载案件读写支持，供本轮确认状态更新使用。
    module_runtime_support = load_runtime_support_module()  # 共享运行时支持模块

    # 在调用方显式给出案件目录时先补齐或定位既有预览材料。
    if namespace_arguments.case_dir:

        # 解析续跑案件目录绝对路径，确保后续所有子入口都定位到同一案件空间。
        path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 续跑案件根目录路径

        # reviewed-model 重入必须保留正文阶段写入的哈希，不得刷新预览状态覆盖它们。
        if namespace_arguments.reviewed_model:

            # 直接定位既有预览，避免预览生成器覆盖正文和模板哈希。
            path_preview_markdown = path_case_dir / "03_drafts" / "pre_draft_preview.md"  # 既有预览 Markdown 路径

            # 重入缺少预览时拒绝继续，禁止重新生成改变确认边界。
            if not path_preview_markdown.exists():

                # 抛出明确缺失错误，提示先完成首次预览阶段。
                raise FileNotFoundError("> ERR: [Python] reviewed-model 重入缺少既有预览 Markdown。")

        # 普通续跑仍按既有规则刷新预览和候选审核闭包。
        else:

            # 生成或刷新普通续跑案件的预览材料。
            path_preview_markdown = ensure_existing_preview(path_case_dir)  # 补生成或复用后的预览 Markdown 路径

        # 组装续跑案件的预览检查点，供确认门和最终返回载荷共同复用。
        preview_checkpoint_state = PreviewCheckpoint(path_case_dir, path_preview_markdown)  # 续跑案件的预览检查点

    # 在未给出案件目录时按新建案件主链推进到预览阶段。
    else:

        # 从研究材料新建案件并推进到预览阶段，建立正式确认门上下文。
        preview_checkpoint_state = create_case_until_preview(namespace_arguments)  # 新建案件推进到预览阶段后的检查点

    # 显式在线结果只在检索成功且案件根确定后进入受管 facts 目录。
    if namespace_arguments.cnipa_query.strip():

        # 固定在线命中落盘位置，使后续人工核验和恢复流程可以追踪本轮结果。
        path_cnipa_results = preview_checkpoint_state.path_case_dir / "02_facts" / "cnipa_search_results.json"  # CNIPA 命中工件

        # 使用共享原子 JSON 写入约定保存结构化命中。
        module_runtime_support.write_json_file(path_cnipa_results, list_cnipa_hits)

    # 在需要时更新预览确认状态，并读取当前案件最新的确认门结果。
    # 先把调用方是否显式确认预览整理成布尔值，供确认门逻辑直接复用。
    bool_confirmed_preview = bool(namespace_arguments.confirmed_preview)  # 调用方是否显式确认预览

    # 根据调用方确认动作刷新 preview_status.json，并读取这次执行应遵循的确认门状态。
    dict_preview_status = apply_preview_confirmation(  # 当前案件最新的预览状态字典
        preview_checkpoint_state.path_case_dir,  # 需要刷新 preview_status.json 的案件目录
        bool_confirmed_preview,  # 调用方是否要求在本轮执行前确认预览
        module_runtime_support,  # 共享 JSON 读写支持模块对象
        namespace_arguments.confirm_technical_profile,  # 用户对疑似AI建议的明确决定
        namespace_arguments.ai_scope,  # 切换AI时提供的专项适用范围
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
    # 将可选模型参数先规范化，避免在函数调用中嵌套条件表达式。
    path_reviewed_model = (  # 当前执行使用的可选权威模型路径
        Path(namespace_arguments.reviewed_model).resolve()  # 显式模型规范路径
        if namespace_arguments.reviewed_model  # 仅处理显式重入模型
        else None  # 普通后链保持空模型参数
    )

    # 进入正式后链，并把可选权威模型作为显式重入输入。
    post_preview_chain_result_state = run_post_preview_chain(  # 预览确认后的正式后链结果
        preview_checkpoint_state.path_case_dir,  # 已通过确认门的案件目录
        namespace_arguments.equation_mode,  # 透传到最终 DOCX 的公式兼容模式
        path_reviewed_model,  # 可选权威审查模型
    )

    # 复制一份后链结果载荷，保持正式交付包结果与内部执行态隔离。
    dict_result_payload = dict(post_preview_chain_result_state.dict_payload)  # 后链结果载荷副本

    # 把完整结果载荷写回标准输出，供测试和自动化工具继续解析。
    write_json_stdout(dict_result_payload)

    # 返回正式后链结果中的既定退出码，保持 blocked/needs_revision/completed 协议不变。
    return post_preview_chain_result_state.int_return_code

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 在任何诊断输出前固定标准文本流编码。
    configure_utf8_text_streams()

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())
