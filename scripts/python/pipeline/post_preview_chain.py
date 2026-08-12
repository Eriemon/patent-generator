#!/usr/bin/env python3
"""实现预览确认后的工件准备、自检和交付后链。"""

# 导入后链运行所需的标准库。
import importlib.util
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 复用模块入口阶段的流水线目录字段，保持数据边界。
PATH_PIPELINE_DIR = Path(__file__).resolve().parent  # 固定模块入口阶段的流水线目录字段。

# 追踪模块入口阶段的Python入口根字段，保持数据边界。
PATH_PYTHON_ROOT = PATH_PIPELINE_DIR.parent  # 组装模块入口阶段的Python入口根字段。

# 固定模块入口阶段的JSON支持模块字段，保持数据边界。
PATH_RUNTIME_SUPPORT = PATH_PYTHON_ROOT / "support" / "runtime_support.py"  # 汇总模块入口阶段的JSON支持模块字段。

# 保存模块入口阶段的Model4来源链模块字段，保持数据边界。
PATH_MODEL4_PROVENANCE = PATH_PYTHON_ROOT / "support" / "model_provenance.py"  # 回收模块入口阶段的Model4来源链模块字段。

# 拆分模块入口阶段的流水线运行模块字段，保持数据边界。
PATH_PIPELINE_RUNTIME = PATH_PIPELINE_DIR / "pipeline_runtime.py"  # 返回模块入口阶段的流水线运行模块字段。

# 返回模块入口阶段的正文生成入口字段，保持数据边界。
PATH_GENERATE_DRAFT_SCRIPT = PATH_PYTHON_ROOT / "draft" / "generate_disclosure_draft.py"  # 隔离模块入口阶段的正文生成入口字段。

# 绑定模块入口阶段的附图生成入口字段，保持数据边界。
PATH_GENERATE_FIGURES_SCRIPT = PATH_PYTHON_ROOT / "figures" / "generate_figures.py"  # 记录模块入口阶段的附图生成入口字段。

# 封存模块入口阶段的权利要求入口字段，保持数据边界。
PATH_GENERATE_CLAIMS_SCRIPT = PATH_PYTHON_ROOT / "claims" / "generate_claims.py"  # 筛选模块入口阶段的权利要求入口字段。

# 记录模块入口阶段的公共自检入口字段，保持数据边界。
PATH_VALIDATE_DISCLOSURE_SCRIPT = PATH_PYTHON_ROOT / "review" / "validate_disclosure.py"  # 追踪模块入口阶段的公共自检入口字段。

# 封存模块入口阶段的DOCX导出入口字段，保持数据边界。
PATH_EXPORT_DOCX_SCRIPT = PATH_PYTHON_ROOT / "export" / "export_docx.py"  # 筛选模块入口阶段的DOCX导出入口字段。

# 进入模块加载的功能边界。
def load_module(path_module: Path, name_module: str) -> Any:
    """按绝对路径加载自包含的运行时模块。

    参数：
    - path_module、name_module

    返回：
    - Any：已初始化模块对象。

    异常：
    - 模块规格缺失时抛出 ImportError。
    """

    # 封存模块加载阶段的对象字段，保持数据边界。
    obj_spec = importlib.util.spec_from_file_location(name_module, path_module)  # 筛选模块加载阶段的对象字段。

    # 先判断模块加载阶段门禁条件。
    if obj_spec is None or obj_spec.loader is None:

        # 阻断模块加载阶段不满足合同的路径。
        raise ImportError(f"> ERR: [Python] 无法加载 {path_module.name}。")

    # 导出模块加载阶段的模块字段，保持数据边界。
    module_loaded = importlib.util.module_from_spec(obj_spec)  # 读取模块加载阶段的模块字段。

    # 执行模块加载阶段的受管调用。
    obj_spec.loader.exec_module(module_loaded)

    # 返回模块加载阶段函数的稳定结果。
    return module_loaded

# 进入案件支持加载的功能边界。
def load_runtime_support_module() -> Any:
    """加载案件 JSON 和正文定位支持模块。

    参数：
    - 无。

    返回：
    - Any：共享运行时支持模块。

    异常：
    - 模块无法加载时抛出 ImportError。
    """

    # 返回案件支持加载阶段函数的稳定结果。
    return load_module(PATH_RUNTIME_SUPPORT, "readable_patent_post_preview_runtime")

# 进入来源链加载的功能边界。
def load_model4_provenance_module() -> Any:
    """加载 Model 4 来源链支持模块。

    参数：
    - 无。

    返回：
    - Any：来源链支持模块。

    异常：
    - 模块无法加载时抛出 ImportError。
    """

    # 返回来源链加载阶段函数的稳定结果。
    return load_module(PATH_MODEL4_PROVENANCE, "readable_patent_post_preview_provenance")

# 解析模块入口阶段的模块字段，保持数据边界。
module_pipeline_runtime = load_module(  # 定位模块入口阶段的模块字段。
    PATH_PIPELINE_RUNTIME,  # 执行模块入口阶段的模块字段。
    "readable_patent_post_preview_pipeline_runtime",  # 回收模块入口阶段的模块字段。
)

# 保存模块入口阶段的阶段变量字段，保持数据边界。
run_child_entrypoint = module_pipeline_runtime.run_child_entrypoint  # 回收模块入口阶段的阶段变量字段。

# 绑定模块入口阶段的子进程执行入口，保持阶段协议。
run_required_stage = module_pipeline_runtime.run_required_stage  # 子进程执行协议入口。

# 保存模块入口阶段的路径字段，保持数据边界。
read_output_path = module_pipeline_runtime.read_output_path  # 回收模块入口阶段的路径字段。

# 隔离模块入口阶段的阶段变量字段，保持数据边界。
collect_delivery_figure_files = module_pipeline_runtime.collect_delivery_figure_files  # 串联模块入口阶段的阶段变量字段。

@dataclass(frozen=True)

# 定义PostPreviewChainResult的数据契约。
class PostPreviewChainResult:
    """预览后链的退出码和机器可读载荷。"""

    # 返回模块入口阶段的阶段变量字段，保持数据边界。
    int_return_code: int  # 隔离模块入口阶段的阶段变量字段。

    # 回收模块入口阶段的字典字段，保持数据边界。
    dict_payload: dict[str, Any]  # 传播模块入口阶段的字典字段。

@dataclass(frozen=True)

# 描述后链工件集合的数据契约。
class PostPreviewArtifacts:
    """公共自检和导出共同消费的权威工件。"""

    # 绑定模块入口阶段的路径字段，保持数据边界。
    path_draft: Path  # 记录模块入口阶段的路径字段。

    # 复用模块入口阶段的路径字段，保持数据边界。
    path_figures_manifest: Path  # 固定模块入口阶段的路径字段。

    # 编排模块入口阶段的路径字段，保持数据边界。
    path_authoritative_model: Path | None  # 拆分模块入口阶段的路径字段。

@dataclass(frozen=True)

# 描述公共自检结果的数据契约。
class PostPreviewValidation:
    """公共自检入口的退出码和状态。"""

    # 归档模块入口阶段的阶段变量字段，保持数据边界。
    int_return_code: int  # 校验模块入口阶段的阶段变量字段。

    # 复用模块入口阶段的状态、文本字段，保持数据边界。
    str_status: str  # 固定模块入口阶段的状态、文本字段。

# 进入既有正文定位的功能边界。
def find_existing_draft(path_case_dir: Path) -> Path:
    """定位 reviewed 重入必须复用的既有正文。

    参数：
    - path_case_dir：当前案件根目录。

    返回：
    - Path：既有正文绝对路径。

    异常：
    - 正文缺失时抛出 FileNotFoundError。
    """

    # 转换既有正文定位阶段的模块字段，保持数据边界。
    module_runtime_support = load_runtime_support_module()  # 准备既有正文定位阶段的模块字段。

    # 执行既有正文定位阶段的路径字段，保持数据边界。
    path_draft = module_runtime_support.find_disclosure_draft(path_case_dir, None)  # 封存既有正文定位阶段的路径字段。

    # 提前判断既有正文定位阶段门禁条件。
    if path_draft is None or not path_draft.exists():

        # 阻断既有正文定位阶段不满足合同的路径。
        raise FileNotFoundError(
            "> ERR: [Python] reviewed-model 重入缺少既有 disclosure draft。"
        )

    # 返回既有正文定位阶段函数的稳定结果。
    return path_draft.resolve()

# 进入reviewed 模型校验的功能边界。
def validate_reviewed_model_artifact(
    path_case_dir: Path,
    path_reviewed_model: Path,
) -> tuple[Path, Path]:
    """校验 reviewed Model 4，并返回绑定的正文路径。

    参数：
    - path_case_dir、path_reviewed_model：案件根目录和 reviewed 模型路径。

    返回：
    - tuple[Path, Path]：权威模型和绑定正文。

    异常：
    - 模型不合法或配套正文缺失时抛出 FileNotFoundError 或 ValueError。
    """

    # 维护reviewed 模型校验阶段的路径字段，保持数据边界。
    path_authoritative_model = path_reviewed_model.resolve()  # 确认reviewed 模型校验阶段的路径字段。

    # 逐项判断reviewed 模型校验阶段门禁条件。
    if not path_authoritative_model.exists():

        # 以 Model 4.0 版本约束阻断 reviewed 输入。
        raise FileNotFoundError(
            f"> ERR: [Python] reviewed model 不存在:{path_authoritative_model}"
        )

    # 恢复reviewed 模型校验阶段的模块字段，保持数据边界。
    module_provenance = load_model4_provenance_module()  # 收敛reviewed 模型校验阶段的模块字段。

    # 定位reviewed 模型校验阶段的对象字段，保持数据边界。
    obj_model = module_provenance.validate_reviewed_model_for_case(  # 绑定reviewed 模型校验阶段的对象字段。
        path_case_dir,  # 封存reviewed 模型校验阶段的对象字段。
        path_authoritative_model,  # 传播reviewed 模型校验阶段的对象字段。
    )

    # 最终判断reviewed 模型校验阶段门禁条件。
    if not isinstance(obj_model, dict) or obj_model.get("contract_version") != "4.0":

        # 阻断reviewed 模型校验阶段不满足合同的路径。
        raise ValueError("> ERR: [Python] --reviewed-model 必须是 Model 4.0 JSON 对象。")

    # 返回reviewed 模型校验阶段函数的稳定结果。
    return path_authoritative_model, find_existing_draft(path_case_dir)

# 进入配套工件定位的功能边界。
def locate_reviewed_companion_artifacts(path_case_dir: Path) -> tuple[Path, Path]:
    """定位 reviewed 重入复用的附图清单和 Claims Map。

    参数：
    - path_case_dir：当前案件根目录。

    返回：
    - tuple[Path, Path]：附图清单和 Claims Map 路径。

    异常：
    - 配套工件缺失时抛出 FileNotFoundError。
    """

    # 定位配套工件定位阶段的路径字段，保持数据边界。
    path_figures_manifest = path_case_dir / "05_figures" / "figures_manifest.json"  # 绑定配套工件定位阶段的路径字段。

    # 拆分配套工件定位阶段的路径字段，保持数据边界。
    path_claims_map = path_case_dir / "03_drafts" / "claims_map.json"  # 返回配套工件定位阶段的路径字段。

    # 遍历配套工件定位阶段集合并保持顺序。
    for path_required_artifact in (path_figures_manifest, path_claims_map):

        # 明确判断配套工件定位阶段门禁条件。
        if not path_required_artifact.exists():

            # 阻断配套工件定位阶段不满足合同的路径。
            raise FileNotFoundError(
                "> ERR: [Python] reviewed-model 重入缺少既有配套工件:"
                f"{path_required_artifact}"
            )

    # 返回配套工件定位阶段函数的稳定结果。
    return path_figures_manifest, path_claims_map

# 进入首次工件生成的功能边界。
def generate_initial_post_preview_artifacts(
    path_case_dir: Path,
) -> tuple[Path, Path, Path]:
    """按正文、附图、权利要求顺序生成首次后链工件。

    参数：
    - path_case_dir：当前案件根目录。

    返回：
    - tuple[Path, Path, Path]：正文、附图清单和 Claims Map 路径。

    异常：
    - 任一子入口失败时抛出 RuntimeError。
    """

    # 拆分首次工件生成阶段的子进程字段，保持数据边界。
    completed_process_draft = run_required_stage(  # 返回首次工件生成阶段的子进程字段。
        PATH_GENERATE_DRAFT_SCRIPT,  # 阻断首次工件生成阶段的子进程字段。
        ["--case-dir", str(path_case_dir)],  # 维护首次工件生成阶段的子进程字段。
    )

    # 检查首次工件生成阶段的路径字段，保持数据边界。
    path_draft = read_output_path(completed_process_draft)  # 保存首次工件生成阶段的路径字段。

    # 维护首次工件生成阶段的子进程字段，保持数据边界。
    completed_process_figures = run_required_stage(  # 确认首次工件生成阶段的子进程字段。
        PATH_GENERATE_FIGURES_SCRIPT,  # 收敛首次工件生成阶段的子进程字段。
        ["--case-dir", str(path_case_dir), "--input", str(path_draft)],  # 记录首次工件生成阶段的子进程字段。
    )

    # 恢复首次工件生成阶段的路径字段，保持数据边界。
    path_figures_manifest = read_output_path(completed_process_figures)  # 收敛首次工件生成阶段的路径字段。

    # 转换首次工件生成阶段的子进程字段，保持数据边界。
    completed_process_claims = run_required_stage(  # 准备首次工件生成阶段的子进程字段。
        PATH_GENERATE_CLAIMS_SCRIPT,  # 导出首次工件生成阶段的子进程字段。
        ["--case-dir", str(path_case_dir), "--input", str(path_draft)],  # 复用首次工件生成阶段的子进程字段。
    )

    # 执行首次工件生成阶段的受管调用。
    read_output_path(completed_process_claims)

    # 返回首次工件生成阶段函数的稳定结果。
    return path_draft, path_figures_manifest, path_case_dir / "03_drafts" / "claims_map.json"

# 进入初始模型封印的功能边界。
def seal_initial_post_preview_model(
    path_case_dir: Path,
    path_draft: Path,
    path_claims_map: Path,
) -> None:
    """把首次后链生成的工件摘要封印到初始 Model 4。

    参数：
    - path_case_dir、path_draft、path_claims_map：案件根、正文和 Claims Map 路径。

    返回：
    - None：工件摘要完成封印。

    异常：
    - 来源链模块无法加载或封印失败时抛出异常。
    """

    # 校验初始模型封印阶段的模块字段，保持数据边界。
    module_provenance = load_model4_provenance_module()  # 执行初始模型封印阶段的模块字段。

    # 执行初始模型封印阶段的受管调用。
    module_provenance.seal_initial_model_artifact(
        path_case_dir,
        path_case_dir / "03_drafts" / "latest_disclosure_model.json",
        path_draft,
        path_case_dir / "03_drafts" / "pre_draft_preview.md",
        path_claims_map,
    )

# 进入后链工件准备的功能边界。
def prepare_post_preview_artifacts(
    path_case_dir: Path,
    path_reviewed_model: Path | None,
) -> PostPreviewArtifacts:
    """准备公共自检和交付阶段需要的唯一工件集合。

    参数：
    - path_case_dir、path_reviewed_model：案件根目录和可选 reviewed 模型。

    返回：
    - PostPreviewArtifacts：后链权威工件。

    异常：
    - 工件缺失或生成入口失败时抛出对应异常。
    """

    # 再判断后链工件准备阶段门禁条件。
    if path_reviewed_model is not None:

        # 导出后链工件准备阶段的路径、元组字段，保持数据边界。
        tuple_path_authoritative_model, tuple_path_draft = validate_reviewed_model_artifact(  # 读取后链工件准备阶段的路径、元组字段。
            path_case_dir,  # 固定后链工件准备阶段的路径、元组字段。
            path_reviewed_model,  # 组装后链工件准备阶段的路径、元组字段。
        )

        # 将 reviewed 模型路径绑定到统一的后链工件字段。
        path_authoritative_model = tuple_path_authoritative_model  # reviewed 模型权威路径。

        # 确认后链工件准备阶段的路径、元组字段，保持数据边界。
        tuple_path_figures_manifest, _ = locate_reviewed_companion_artifacts(path_case_dir)  # reviewed 附图清单路径。

    # 收束后链工件准备阶段的当前分支。
    else:

        # 回收后链工件准备阶段的路径字段，保持数据边界。
        path_authoritative_model = None  # 传播后链工件准备阶段的路径字段。

        # 记录后链工件准备阶段的路径、元组字段，保持数据边界。
        tuple_path_draft, tuple_path_figures_manifest, tuple_path_claims_map = (  # 追踪后链工件准备阶段的路径、元组字段。
            generate_initial_post_preview_artifacts(path_case_dir)  # 整理后链工件准备阶段的路径、元组字段。
        )

        # 执行后链工件准备阶段的受管调用。
        seal_initial_post_preview_model(path_case_dir, tuple_path_draft, tuple_path_claims_map)

    # 返回后链工件准备阶段函数的稳定结果。
    return PostPreviewArtifacts(
        path_draft=tuple_path_draft.resolve(),
        path_figures_manifest=tuple_path_figures_manifest.resolve(),
        path_authoritative_model=path_authoritative_model,
    )

# 进入公共自检的功能边界。
def validate_post_preview_artifacts(
    path_case_dir: Path,
    post_preview_artifacts_obj_artifacts: PostPreviewArtifacts,
) -> PostPreviewValidation:
    """调用唯一公共自检入口并解析其状态协议。

    参数：
    - path_case_dir、post_preview_artifacts_obj_artifacts：案件根目录和准备阶段工件。

    返回：
    - PostPreviewValidation：自检退出码和状态。

    异常：
    - 公共入口协议异常时抛出 RuntimeError。
    """

    # 检查公共自检阶段的参数、列表字段，保持数据边界。
    list_review_args = [  # 保存公共自检阶段的参数、列表字段。
        "--case-dir",  # 拆分公共自检阶段的参数、列表字段。
        str(path_case_dir),  # 传递公共自检阶段的参数、列表字段。
        "--input",  # 汇总公共自检阶段的参数、列表字段。
        str(post_preview_artifacts_obj_artifacts.path_draft),  # 生成公共自检阶段的参数、列表字段。
    ]

    # 再判断公共自检阶段门禁条件。
    if post_preview_artifacts_obj_artifacts.path_authoritative_model is not None:

        # 执行公共自检阶段的受管调用。
        list_review_args.extend(
            ["--model", str(post_preview_artifacts_obj_artifacts.path_authoritative_model)]
        )

    # 传播公共自检阶段的子进程字段，保持数据边界。
    completed_process_review = run_child_entrypoint(  # 约束公共自检阶段的子进程字段。
        PATH_VALIDATE_DISCLOSURE_SCRIPT,  # 串联公共自检阶段的子进程字段。
        list_review_args,  # 准备公共自检阶段的子进程字段。
    )

    # 拒绝公共自检返回协议之外的业务退出码。
    if completed_process_review.returncode not in (0, 1, 2):

        # 阻断公共自检阶段不满足合同的路径。
        raise RuntimeError(
            "> ERR: [Python] 自检入口执行异常。\n"
            f"stdout:\n{completed_process_review.stdout}\n"
            f"stderr:\n{completed_process_review.stderr}"
        )

    # 复用公共自检阶段的路径、报告字段，保持数据边界。
    path_validation_report = read_output_path(completed_process_review)  # 固定公共自检阶段的路径、报告字段。

    # 整理公共自检阶段的报告、字典字段，保持数据边界。
    dict_validation_report = json.loads(  # 解析公共自检阶段的报告、字典字段。
        path_validation_report.read_text(encoding="utf-8")  # 校验公共自检阶段的报告、字典字段。
    )

    # 返回公共自检阶段函数的稳定结果。
    return PostPreviewValidation(
        int_return_code=completed_process_review.returncode,
        str_status=str(dict_validation_report.get("status", "needs_revision")),
    )

# 进入正式交付的功能边界。
def export_post_preview_delivery(
    path_case_dir: Path,
    str_equation_mode: str,
    post_preview_artifacts_obj_artifacts: PostPreviewArtifacts,
    post_preview_validation_obj_validation: PostPreviewValidation,
) -> dict[str, Any]:
    """执行正式 DOCX 导出并组装交付载荷。

    参数：
    - path_case_dir、str_equation_mode：案件根目录和公式模式。
    - post_preview_artifacts_obj_artifacts、post_preview_validation_obj_validation：后链工件和自检结果。

    返回：
    - dict[str, Any]：机器可读交付载荷。

    异常：
    - DOCX 子入口失败时抛出 RuntimeError。
    """

    # 筛选正式交付阶段的子进程字段，保持数据边界。
    completed_process_export = run_required_stage(  # 整理正式交付阶段的子进程字段。
        PATH_EXPORT_DOCX_SCRIPT,  # 归档正式交付阶段的子进程字段。
        [
            "--case-dir",  # 编排正式交付阶段的子进程字段。
            str(path_case_dir),  # 读取正式交付阶段的子进程字段。
            "--input",  # 固定正式交付阶段的子进程字段。
            str(post_preview_artifacts_obj_artifacts.path_draft),  # 组装正式交付阶段的子进程字段。
            "--equation-mode",  # 解析正式交付阶段的子进程字段。
            str_equation_mode,  # 校验正式交付阶段的子进程字段。
        ],
    )

    # 追踪正式交付阶段的路径字段，保持数据边界。
    path_delivery_docx = read_output_path(completed_process_export).resolve()  # 组装正式交付阶段的路径字段。

    # 返回正式交付阶段函数的稳定结果。
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

# 进入后链编排的功能边界。
def run_post_preview_chain(
    path_case_dir: Path,
    str_equation_mode: str,
    path_reviewed_model: Path | None = None,
) -> PostPreviewChainResult:
    """按准备、自检、交付三段职责执行预览后链。

    参数：
    - path_case_dir、str_equation_mode、path_reviewed_model：案件、公式模式和可选 reviewed 模型。

    返回：
    - PostPreviewChainResult：退出码与交付载荷。

    异常：
    - 后链阶段失败时抛出对应异常。
    """

    # 固定后链编排阶段的权威工件对象，保持数据边界。
    post_preview_artifacts_obj_artifacts = prepare_post_preview_artifacts(  # 后链权威工件对象。
        path_case_dir,  # 准备后链编排阶段的对象字段。
        path_reviewed_model,  # 导出后链编排阶段的对象字段。
    )

    # 固定后链编排阶段的公共自检对象，保持状态边界。
    post_preview_validation_obj_validation = validate_post_preview_artifacts(  # 后链公共自检对象。
        path_case_dir,  # 检查后链编排阶段的对象字段。
        post_preview_artifacts_obj_artifacts,  # 传递后链权威工件对象。
    )

    # 导出后链编排阶段的字典字段，保持数据边界。
    dict_payload: dict[str, Any] = {"case_dir": str(path_case_dir.resolve())}  # 读取后链编排阶段的字典字段。

    # 明确判断后链编排阶段门禁条件。
    if (
        post_preview_validation_obj_validation.int_return_code == 1
        and post_preview_validation_obj_validation.str_status != "visual_review_required"
    ):

        # 传播后链编排阶段的状态、字典字段，保持数据边界。
        dict_payload["delivery_status"] = "blocked"  # 约束后链编排阶段的状态、字典字段。

        # 以 needs_revision 退出码结束后链编排。
        return PostPreviewChainResult(1, dict_payload)

    # 严格判断后链编排阶段门禁条件。
    if post_preview_validation_obj_validation.int_return_code == 2:

        # 筛选后链编排阶段的状态、字典字段，保持数据边界。
        dict_payload["delivery_status"] = "needs_revision"  # 整理后链编排阶段的状态、字典字段。

        # 返回后链编排阶段函数的稳定结果。
        return PostPreviewChainResult(2, dict_payload)

    # 定位后链编排阶段的字典字段，保持数据边界。
    dict_payload = export_post_preview_delivery(  # 绑定后链编排阶段的字典字段。
        path_case_dir,  # 封存后链编排阶段的字典字段。
        str_equation_mode,  # 传播后链编排阶段的字典字段。
        post_preview_artifacts_obj_artifacts,  # 交给导出阶段的权威工件对象。
        post_preview_validation_obj_validation,  # 交给导出阶段的公共自检对象。
    )

    # 以 completed 退出码返回正式交付载荷。
    return PostPreviewChainResult(0, dict_payload)
