#!/usr/bin/env python3
"""执行正式主链，并在预览确认后继续进入后链。"""
# 启用未来注解行为，保证模块加载时类型标注保持惰性解析。
from __future__ import annotations

# 导入命令行、动态加载、JSON、子进程、标准输出和路径能力。
import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 追踪模块入口阶段的流水线目录字段，保持数据边界。
PATH_PIPELINE_DIR = Path(__file__).resolve().parent  # 组装模块入口阶段的流水线目录字段。

# 追踪模块入口阶段的Python入口根字段，保持数据边界。
PATH_PYTHON_ROOT = PATH_PIPELINE_DIR.parent  # 组装模块入口阶段的Python入口根字段。

# 读取模块入口阶段的JSON支持模块字段，保持数据边界。
PATH_RUNTIME_SUPPORT = PATH_PYTHON_ROOT / "support" / "runtime_support.py"  # 传递模块入口阶段的JSON支持模块字段。

# 拆分模块入口阶段的能力预检入口字段，保持数据边界。
PATH_CAPABILITY_PREFLIGHT = PATH_PYTHON_ROOT / "support" / "check_dependencies.py"  # 返回模块入口阶段的能力预检入口字段。

# 校验模块入口阶段的Model4来源链模块字段，保持数据边界。
PATH_MODEL4_PROVENANCE = PATH_PYTHON_ROOT / "support" / "model_provenance.py"  # 执行模块入口阶段的Model4来源链模块字段。

# 校验模块入口阶段的流水线运行模块字段，保持数据边界。
PATH_PIPELINE_RUNTIME = PATH_PIPELINE_DIR / "pipeline_runtime.py"  # 执行模块入口阶段的流水线运行模块字段。

# 传递模块入口阶段的后链模块字段，保持数据边界。
PATH_POST_PREVIEW_CHAIN = PATH_PIPELINE_DIR / "post_preview_chain.py"  # 阻断模块入口阶段的后链模块字段。

# 汇总模块入口阶段的建案入口字段，保持数据边界。
PATH_CREATE_CASE_SCRIPT = PATH_PYTHON_ROOT / "case" / "create_case.py"  # 维护模块入口阶段的建案入口字段。

# 恢复模块入口阶段的材料盘点入口字段，保持数据边界。
PATH_RESEARCH_INVENTORY_SCRIPT = PATH_PYTHON_ROOT / "intake" / "research_inventory.py"  # 收敛模块入口阶段的材料盘点入口字段。

# 转换模块入口阶段的事实抽取入口字段，保持数据边界。
PATH_EXTRACT_RESEARCH_FACTS_SCRIPT = PATH_PYTHON_ROOT / "facts" / "extract_research_facts.py"  # 准备模块入口阶段的事实抽取入口字段。

# 确认模块入口阶段的主案选择入口字段，保持数据边界。
PATH_SELECT_INVENTION_POINT_SCRIPT = PATH_PYTHON_ROOT / "invention" / "select_invention_point.py"  # 导出模块入口阶段的主案选择入口字段。

# 维护模块入口阶段的查新规划入口字段，保持数据边界。
PATH_PLAN_PRIOR_ART_SCRIPT = PATH_PYTHON_ROOT / "prior_art" / "plan_prior_art_queries.py"  # 确认模块入口阶段的查新规划入口字段。

# 阻断模块入口阶段的CNIPA检索入口字段，保持数据边界。
PATH_CNIPA_SEARCH_SCRIPT = PATH_PYTHON_ROOT / "search" / "cnipa_epub_search.py"  # 转换模块入口阶段的CNIPA检索入口字段。

# 传播模块入口阶段的预览生成入口字段，保持数据边界。
PATH_GENERATE_PREVIEW_SCRIPT = PATH_PYTHON_ROOT / "preview" / "generate_preview.py"  # 约束模块入口阶段的预览生成入口字段。

# 保留正式正文入口路径，兼容仍引用旧常量的调用方。
PATH_GENERATE_DRAFT_SCRIPT = PATH_PYTHON_ROOT / "draft" / "generate_disclosure_draft.py"  # 正式正文生成入口路径。

# 保留附图入口路径，兼容后链阶段的路径审计。
PATH_GENERATE_FIGURES_SCRIPT = PATH_PYTHON_ROOT / "figures" / "generate_figures.py"  # 附图生成入口路径。

# 保留权利要求入口路径，兼容后链阶段的路径审计。
PATH_GENERATE_CLAIMS_SCRIPT = PATH_PYTHON_ROOT / "claims" / "generate_claims.py"  # 权利要求生成入口路径。

# 保留自检入口路径，兼容交付前检查的路径审计。
PATH_VALIDATE_DISCLOSURE_SCRIPT = PATH_PYTHON_ROOT / "review" / "validate_disclosure.py"  # 正文自检入口路径。

# 保留 DOCX 导出入口路径，兼容交付导出的路径审计。
PATH_EXPORT_DOCX_SCRIPT = PATH_PYTHON_ROOT / "export" / "export_docx.py"  # DOCX 导出入口路径。

# 进入模块加载的功能边界。
def load_module(path_module: Path, name_module: str) -> Any:
    """执行 load_module 的受管流水线职责。

    参数：
    - path_module、name_module：当前入口上下文。

    返回：
    - Any：当前阶段的稳定结果。

    异常：
    - 参数、模块或子入口不满足合同时抛出对应异常。
    """

    # 维护模块加载阶段的对象字段，保持数据边界。
    obj_spec = importlib.util.spec_from_file_location(name_module, path_module)  # 确认模块加载阶段的对象字段。

    # 分别判断模块加载阶段门禁条件。
    if obj_spec is None or obj_spec.loader is None:

        # 阻断模块加载阶段不满足合同的路径。
        raise ImportError(f"> ERR: [Python] 无法加载 {path_module.name}。")

    # 收敛模块加载阶段的模块字段，保持数据边界。
    module_loaded = importlib.util.module_from_spec(obj_spec)  # 复用模块加载阶段的模块字段。

    # 先登记动态模块，使 dataclass 前向注解能够解析所属模块。
    sys.modules[name_module] = module_loaded  # 动态模块注册表项。

    # 执行模块加载阶段的受管调用。
    obj_spec.loader.exec_module(module_loaded)

    # 返回模块加载阶段函数的稳定结果。
    return module_loaded

# 进入运行模块加载的功能边界。
def load_pipeline_runtime_module() -> Any:
    """执行 load_pipeline_runtime_module 的受管流水线职责。

    参数：
    - 无。

    返回：
    - Any：当前阶段的稳定结果。

    异常：
    - 参数、模块或子入口不满足合同时抛出对应异常。
    """

    # 返回运行模块加载阶段函数的稳定结果。
    return load_module(PATH_PIPELINE_RUNTIME, "readable_patent_pipeline_runtime")

# 封存模块入口阶段的模块字段，保持数据边界。
module_pipeline_runtime = load_pipeline_runtime_module()  # 筛选模块入口阶段的模块字段。

# 转换模块入口阶段的阶段变量字段，保持数据边界。
collect_research_suffixes = module_pipeline_runtime.collect_research_suffixes  # 准备模块入口阶段的阶段变量字段。

# 封存模块入口阶段的阶段变量字段，保持数据边界。
will_run_post_preview = module_pipeline_runtime.will_run_post_preview  # 筛选模块入口阶段的阶段变量字段。

# 导出模块入口阶段的阶段变量字段，保持数据边界。
determine_required_capabilities = module_pipeline_runtime.determine_required_capabilities  # 读取模块入口阶段的阶段变量字段。

# 传播模块入口阶段的阶段变量字段，保持数据边界。
run_child_entrypoint = module_pipeline_runtime.run_child_entrypoint  # 约束模块入口阶段的阶段变量字段。

# 维护模块入口阶段的阶段变量字段，保持数据边界。
require_success = module_pipeline_runtime.require_success  # 确认模块入口阶段的阶段变量字段。

# 确认模块入口阶段的阶段变量字段，保持数据边界。
read_last_stdout_line = module_pipeline_runtime.read_last_stdout_line  # 导出模块入口阶段的阶段变量字段。

# 隔离模块入口阶段的阶段变量字段，保持数据边界。
run_required_stage = module_pipeline_runtime.run_required_stage  # 串联模块入口阶段的阶段变量字段。

# 传播模块入口阶段的路径字段，保持数据边界。
read_output_path = module_pipeline_runtime.read_output_path  # 约束模块入口阶段的路径字段。

# 归档模块入口阶段的阶段变量字段，保持数据边界。
collect_delivery_figure_files = module_pipeline_runtime.collect_delivery_figure_files  # 校验模块入口阶段的阶段变量字段。

# 进入后链模块加载的功能边界。
def load_post_preview_chain_module() -> Any:
    """执行 load_post_preview_chain_module 的受管流水线职责。

    参数：
    - 无。

    返回：
    - Any：当前阶段的稳定结果。

    异常：
    - 参数、模块或子入口不满足合同时抛出对应异常。
    """

    # 返回后链模块加载阶段函数的稳定结果。
    return load_module(PATH_POST_PREVIEW_CHAIN, "readable_patent_post_preview_chain")

# 回收模块入口阶段的模块字段，保持数据边界。
module_post_preview_chain = load_post_preview_chain_module()  # 传播模块入口阶段的模块字段。

# 定位模块入口阶段的阶段变量字段，保持数据边界。
PostPreviewChainResult = module_post_preview_chain.PostPreviewChainResult  # 绑定模块入口阶段的阶段变量字段。

# 生成模块入口阶段的阶段变量字段，保持数据边界。
PostPreviewArtifacts = module_post_preview_chain.PostPreviewArtifacts  # 恢复模块入口阶段的阶段变量字段。

# 执行模块入口阶段的阶段变量字段，保持数据边界。
PostPreviewValidation = module_post_preview_chain.PostPreviewValidation  # 封存模块入口阶段的阶段变量字段。

# 暴露草稿查找入口，供主链准备阶段复用。
find_existing_draft = module_post_preview_chain.find_existing_draft  # 后链草稿查找公共入口。

# 记录模块入口阶段的阶段变量字段，保持数据边界。
validate_reviewed_model_artifact = module_post_preview_chain.validate_reviewed_model_artifact  # 追踪模块入口阶段的阶段变量字段。

# 准备模块入口阶段的阶段变量字段，保持数据边界。
locate_reviewed_companion_artifacts = module_post_preview_chain.locate_reviewed_companion_artifacts  # 编排模块入口阶段的阶段变量字段。

# 暴露首轮后预览工件生成入口，保持协调器只负责委托。
generate_initial_post_preview_artifacts = (  # 首轮后预览工件委托字段。
    module_post_preview_chain.generate_initial_post_preview_artifacts  # 首轮后预览工件生成公共入口。
)

# 暴露后预览模型封印入口，沿用稳定公共名称。
seal_initial_post_preview_model = module_post_preview_chain.seal_initial_post_preview_model  # 后预览模型封印公共入口。

# 暴露后预览准备入口，保留既有调用协议。
prepare_post_preview_artifacts = module_post_preview_chain.prepare_post_preview_artifacts  # 后预览准备公共入口。

# 复用模块入口阶段的阶段变量字段，保持数据边界。
validate_post_preview_artifacts = module_post_preview_chain.validate_post_preview_artifacts  # 固定模块入口阶段的阶段变量字段。

# 暴露交付导出入口，继续由后链模块实现。
export_post_preview_delivery = module_post_preview_chain.export_post_preview_delivery  # 后预览交付导出公共入口。

# 收敛模块入口阶段的阶段变量字段，保持数据边界。
run_post_preview_chain = module_post_preview_chain.run_post_preview_chain  # 复用模块入口阶段的阶段变量字段。

@dataclass(frozen=True)

# 定义PreviewCheckpoint的数据契约。
class PreviewCheckpoint:
    """推进到预览阶段后交给确认门的案件上下文。"""

    # 转换模块入口阶段的路径字段，保持数据边界。
    path_case_dir: Path  # 准备模块入口阶段的路径字段。

    # 复用模块入口阶段的路径字段，保持数据边界。
    path_preview_markdown: Path  # 固定模块入口阶段的路径字段。

# 进入案件支持加载的功能边界。
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

# 定位重入案件的既有正文，禁止为取得路径而重新生成并覆盖 Model 4.0。
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
