"""提供流水线能力选择和子进程协议的无状态运行工具。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数命名空间、JSON、子进程、解释器路径和文件系统路径能力。
import argparse
import json
import subprocess
import sys
from pathlib import Path

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
