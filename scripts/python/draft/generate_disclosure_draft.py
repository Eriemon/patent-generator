#!/usr/bin/env python3
"""基于主案结果生成正式中文交底书草稿。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、按路径加载模块、文件复制、标准输出和路径能力，供正式草稿入口稳定运行。
import argparse
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Any

# 固定共享运行时支持模块路径，避免通过修改 sys.path 导入公共工具。
PATH_RUNTIME_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "runtime_support.py"  # 共享运行时支持模块路径

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

    # 执行共享支持模块源码，把公共文本、路径和 JSON 工具装入模块对象。
    obj_spec.loader.exec_module(module_runtime_support)

    # 返回已完成加载的共享支持模块，供正式草稿入口复用。
    return module_runtime_support

# 构造命令行参数解析器，统一声明案件目录和内部预览放行开关。
def build_parser() -> argparse.ArgumentParser:
    """构造正式草稿入口的命令行解析器。

    参数：
    - 无。

    返回：
    - `argparse.ArgumentParser`：已注册参数的解析器对象。

    异常：
    - 无。
    """

    # 先准备解析器说明文本，避免初始化语句过长。
    str_description = "Generate a governed Chinese disclosure draft from selected invention outputs."  # 入口说明文本

    # 初始化当前正式草稿入口的命令行解析器。
    obj_parser = argparse.ArgumentParser(description=str_description)  # 正式草稿入口解析器

    # 注册案件目录参数，确保草稿始终围绕当前案件目录落盘。
    obj_parser.add_argument("--case-dir", required=True)

    # 注册内部预览放行开关，允许只在受控内部场景下绕过确认门生成中间草稿。
    obj_parser.add_argument(
        "--allow-unconfirmed-preview",
        action="store_true",
        help="Allow internal draft generation before preview confirmation.",
    )

    # 返回完成参数注册的解析器对象。
    return obj_parser

# 校验预览确认状态，默认阻止未确认预览的案件直接进入正式正文起草阶段。
def ensure_preview_confirmed(
    path_case_dir: Path,
    allow_unconfirmed_preview: bool,
    module_runtime_support: Any,
) -> None:
    """校验预览确认状态。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `allow_unconfirmed_preview`：是否允许在内部场景下绕过预览确认门。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `None`。

    异常：
    - 预览状态文件缺失时抛出 `FileNotFoundError`。
    - 预览尚未确认且当前未显式放行时抛出 `PermissionError`。
    """

    # 固定预览状态 JSON 路径，供正式草稿入口统一读取确认门状态。
    path_preview_status = path_case_dir / "03_drafts" / "preview_status.json"  # 预览状态 JSON 路径

    # 在预览状态文件缺失时立即报错，避免未走预览主链的案件直接进入正文阶段。
    if not path_preview_status.exists():

        # 抛出明确错误，提醒调用方先生成预览材料再进入正式正文起草。
        raise FileNotFoundError("> ERR: [Python] 缺少 preview_status.json，请先生成预览材料。")

    # 读取当前案件的预览状态字典，供确认门判断是否已经通过。
    dict_preview_status = module_runtime_support.read_json_file(path_preview_status)  # 当前案件预览状态字典

    # 在当前案件已经完成预览确认时直接结束检查。
    if dict_preview_status.get("confirmed"):

        # 预览已经确认的案件允许继续进入正式正文阶段。
        return

    # 在调用方显式要求内部放行时允许继续生成中间草稿。
    if allow_unconfirmed_preview:

        # 内部放行场景允许跳过正式确认门，但不改变 preview_status.json 本身状态。
        return

    # 在未确认且未显式放行时阻止正文继续生成。
    raise PermissionError("> ERR: [Python] 预览尚未确认，禁止进入正式正文起草。")

# 读取主案选择结果与 facts 结果，确保正式草稿阶段绑定完整的上游事实产物。
def load_selected_bundle(
    path_case_dir: Path,
    module_runtime_support: Any,
) -> dict[str, Any]:
    """读取主案选择结果与 facts 结果。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `dict[str, Any]`：包含 `selected_bundle` 与 `facts` 两个键的结构化字典。

    异常：
    - 主案选择结果缺失时抛出 `FileNotFoundError`。
    - facts 结果缺失时抛出 `FileNotFoundError`。
    """

    # 固定主案选择结果 JSON 路径，供正文生成阶段读取当前主案。
    path_selected_json = path_case_dir / "02_facts" / "selected_invention_point.json"  # 主案选择结果 JSON 路径

    # 固定 facts 结果 JSON 路径，供正文起草阶段补齐术语和候选证据。
    path_facts_json = path_case_dir / "02_facts" / "research_facts.json"  # facts 结果 JSON 路径

    # 在主案选择结果缺失时立即报错，避免正文围绕空主案生成空壳草稿。
    if not path_selected_json.exists():

        # 抛出明确错误，提醒调用方先完成主案选择阶段。
        raise FileNotFoundError("> ERR: [Python] 缺少 selected_invention_point.json，请先完成主案选择。")

    # 在 facts 结果缺失时立即报错，避免正文无法回溯上游事实。
    if not path_facts_json.exists():

        # 抛出明确错误，提醒调用方先完成研究事实抽取阶段。
        raise FileNotFoundError("> ERR: [Python] 缺少 research_facts.json，请先完成事实抽取。")

    # 先准备返回字典，后续逐项登记主案结果与 facts 结果。
    dict_loaded_bundle: dict[str, Any] = {}  # 主案选择结果与 facts 结果组合字典

    # 登记当前案件的主案选择结果，供正文起草围绕选中的问题和方案展开。
    dict_loaded_bundle["selected_bundle"] = module_runtime_support.read_json_file(path_selected_json)  # 主案选择结果字典

    # 登记当前案件的 facts 结果，供术语、候选证据和辅助信息补充复用。
    dict_loaded_bundle["facts"] = module_runtime_support.read_json_file(path_facts_json)  # facts 结果字典

    # 返回完整的上游产物组合字典，供正文起草阶段继续拆读。
    return dict_loaded_bundle

# 把研究根目录中的已核验查新记录同步到案件目录，避免正文阶段直接引用工作区外部文件。
def stage_verified_prior_art_records(
    path_case_dir: Path,
    module_runtime_support: Any,
) -> None:
    """同步已核验查新记录到案件目录。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `None`。

    异常：
    - 配置读取或文件复制失败时由底层异常上抛。
    """

    # 固定案件目录内的查新记录目标路径，供正文和自检入口后续统一读取。
    path_target_records = path_case_dir / "02_facts" / "prior_art_records.json"  # 案件目录内的查新记录目标路径

    # 在案件目录已经存在查新记录时直接结束，避免覆盖后续人工修订结果。
    if path_target_records.exists():

        # 当前案件已经具备本地查新记录，无需再从研究根目录重复同步。
        return

    # 读取案件配置字典，定位研究根目录中是否已有可复用的查新记录文件。
    dict_case_config = module_runtime_support.load_case_config(path_case_dir)  # 当前案件配置字典

    # 读取案件配置中的研究根目录字段，供外部查新记录定位复用。
    str_research_root = dict_case_config.get("research_root", "")  # 当前案件研究根目录文本

    # 在案件配置没有研究根目录时直接结束，让正文阶段按无查新记录安全降级。
    if not str_research_root:

        # 缺少研究根目录配置时不强造查新记录，保持行为真实可追溯。
        return

    # 定位研究根目录中的查新记录文件，供同步到案件目录前做存在性检查。
    path_source_records = Path(str_research_root).resolve() / "prior_art_records.json"  # 研究根目录中的查新记录源路径

    # 在研究根目录没有查新记录文件时直接结束，让正文阶段按最小样例安全降级。
    if not path_source_records.exists():

        # 不伪造外部查新记录，只在真实文件存在时才同步进入案件目录。
        return

    # 先确保案件目录下的 facts 目录存在，再把外部查新记录复制进当前案件空间。
    module_runtime_support.ensure_dir(path_target_records.parent)

    # 把研究根目录中的查新记录复制到当前案件目录，供正文和自检统一消费本地副本。
    shutil.copyfile(path_source_records, path_target_records)

# 把主案名称规整成正式交底书标题，补齐“一种”和技术客体后缀。
def normalize_title(str_name: str, module_runtime_support: Any) -> str:
    """规整正式交底书标题。

    参数：
    - `str_name`：原始主案名称或案件名文本。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `str`：符合中文专利标题习惯的正式标题文本。

    异常：
    - 无。
    """

    # 先清洗原始标题文本，避免空白与噪声标记直接进入正式标题。
    str_title = module_runtime_support.clean_text(str_name) or "一种待确认技术方案"  # 清洗后的标题文本

    # 在标题末尾尚未带有常见客体后缀时默认补上“方法”。
    if not any(str_suffix in str_title for str_suffix in ("方法", "系统", "装置", "设备", "介质")):

        # 把没有技术客体后缀的标题补成方法类标题，保持最小正式外观。
        str_title = f"{str_title}方法"  # 补齐后的方法类标题文本

    # 在标题尚未以“一种”开头时补上发明名称惯用前缀。
    if not str_title.startswith("一种"):

        # 为正式标题补上“一种”前缀，保持专利交底书名称习惯。
        str_title = "一种" + str_title  # 补齐前缀后的正式标题文本

    # 返回长度受控的正式标题文本，减少极长标题带来的版式风险。
    return str_title[:60]

# 把技术问题拆成正文 3.3 小节可直接使用的条目列表。
def build_problem_lines(str_problem: str, module_runtime_support: Any) -> list[str]:
    """构建现有技术缺点条目列表。

    参数：
    - `str_problem`：主案问题描述文本。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[str]`：适合直接写入 3.3 小节的条目文本列表。

    异常：
    - 无。
    """

    # 先准备问题条目列表，后续按句子拆分结果逐项收录可用文本。
    list_problem_lines: list[str] = []  # 现有技术缺点条目列表

    # 逐条清洗主案问题拆分得到的短句，只保留真正可写入正文的条目。
    for str_item in module_runtime_support.split_sentences(str_problem, limit=6):

        # 把当前问题短句清洗成单行文本，便于统一判断是否可写入正文。
        str_problem_line = module_runtime_support.clean_text(str_item)  # 当前问题条目文本

        # 在当前短句确实存在有效文本时再把它加入结果列表。
        if str_problem_line:

            # 把当前可用问题条目加入结果列表，供正文 3.3 小节直接复用。
            list_problem_lines.append(str_problem_line)

    # 在已经得到至少一条问题条目时直接返回当前结果列表。
    if list_problem_lines:

        # 返回清洗后的问题条目列表，保持与主案问题描述的一致性。
        return list_problem_lines

    # 在问题描述无法拆出有效短句时回退到受控默认条目。
    return ["现有技术仍存在需要结合真实研发材料进一步核对的处理缺口。"]

# 从主案技术方案证据里提取可直接复用的方法步骤短句。
def collect_solution_texts(
    dict_selected: dict[str, Any],
    module_runtime_support: Any,
) -> list[str]:
    """收集方法步骤短句候选列表。

    参数：
    - `dict_selected`：当前主案选择结果字典。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[str]`：优先来自技术方案证据的步骤短句列表。

    异常：
    - 无。
    """

    # 先准备正文证据里已经明确写出的技术方案短句列表。
    list_solution_texts: list[str] = []  # 技术方案短句候选列表

    # 逐项清洗技术方案证据文本，只保留真正可直接转成步骤摘要的条目。
    for dict_item in dict_selected.get("technical_solution_evidence", []):

        # 读取并清洗当前技术方案证据文本，便于统一判断可用性。
        str_solution_text = module_runtime_support.clean_text(dict_item.get("text", ""))  # 当前技术方案证据短句

        # 在当前技术方案证据确实存在有效文本时再收入候选列表。
        if str_solution_text:

            # 把当前短句纳入候选列表，供后续覆盖默认步骤摘要。
            list_solution_texts.append(str_solution_text)

    # 在正文证据已经给出可用短句时直接返回当前候选列表。
    if list_solution_texts:

        # 返回已收集的技术方案短句，避免继续回退到主案 solution 文本。
        return list_solution_texts

    # 在正文证据缺失时回退到主案 solution 字段自动拆句。
    return module_runtime_support.split_sentences(dict_selected.get("solution", ""), limit=6)

# 基于聚合术语生成稳定的默认方法步骤骨架。
def build_default_step_summaries(list_terms: list[str]) -> list[str]:
    """构建默认方法步骤摘要列表。

    参数：
    - `list_terms`：聚合后的技术术语列表。

    返回：
    - `list[str]`：四步法默认步骤摘要列表。

    异常：
    - 无。
    """

    # 汇总前几项术语生成状态相关表述，便于默认步骤摘要保持上下文一致。
    str_state_terms = "、".join(list_terms[:4]) or "候选对象状态"  # 状态相关术语串接文本

    # 汇总后几项术语生成评分相关表述，便于默认步骤摘要保持领域感。
    str_scoring_terms = "、".join(list_terms[4:8]) or "匹配评分参数"  # 评分相关术语串接文本

    # 返回正文证据不足时使用的最小默认步骤骨架。
    return [
        f"采集与当前任务相关的 {str_state_terms}。",
        f"根据 {str_scoring_terms} 计算匹配结果，并筛选满足阈值条件的候选对象。",
        "将当前任务分配给匹配结果最优的候选对象，并输出分配结果。",
        "当候选对象响应失败或状态异常时，记录反馈信息并更新下一轮选择依据。",
    ]

# 用正文证据短句覆盖默认步骤摘要，尽量让正文贴近真实主案材料。
def overlay_solution_summaries(
    list_step_summaries: list[str],
    list_solution_texts: list[str],
) -> None:
    """用技术方案证据覆盖默认步骤摘要。

    参数：
    - `list_step_summaries`：默认方法步骤摘要列表。
    - `list_solution_texts`：技术方案证据短句列表。

    返回：
    - 无。

    异常：
    - 无。
    """

    # 用正文证据里的前四条方案短句覆盖默认步骤摘要，尽量贴近真实主案描述。
    for int_index, str_text in enumerate(list_solution_texts[:4]):

        # 在当前证据短句存在时用它覆盖对应默认步骤摘要。
        if str_text:

            # 把当前证据短句规整为句号收尾的正文步骤摘要。
            list_step_summaries[int_index] = str_text.rstrip("。；;") + "。"  # 覆盖后的步骤摘要文本

# 根据步骤摘要判断当前步骤的输入输出说明。
def resolve_step_io_fields(str_summary: str) -> tuple[str, str]:
    """解析步骤摘要对应的输入输出说明。

    参数：
    - `str_summary`：当前步骤摘要文本。

    返回：
    - `tuple[str, str]`：依次为输入说明和输出说明。

    异常：
    - 无。
    """

    # 用数据驱动的规则映射步骤语义，减少入口函数里的分支噪声。
    list_io_rules = [
        (("采集", "获取"), ("任务请求或原始状态数据", "状态采集结果")),  # 状态采集阶段语义规则
        (("计算", "评分"), ("状态采集结果", "匹配评分结果")),  # 评分筛选阶段语义规则
        (("分配", "选择"), ("匹配评分结果", "任务分配结果")),  # 决策分配阶段语义规则
        (("反馈", "更新"), ("执行结果和异常状态", "更新后的选择依据")),  # 反馈修正阶段语义规则
    ]  # 步骤语义到输入输出说明的映射规则

    # 逐条命中语义规则，优先返回最贴近当前步骤摘要的输入输出说明。
    for tuple_keywords, tuple_io_fields in list_io_rules:

        # 在当前步骤摘要命中语义关键词时，先拆出对应输入输出说明。
        if any(str_keyword in str_summary for str_keyword in tuple_keywords):

            # 先把命中规则的第一个槽位映射成 input 字段。
            str_input = tuple_io_fields[0]  # 命中规则后的输入字段文本

            # 再把命中规则的第二个槽位映射成 output 字段。
            str_output = tuple_io_fields[1]  # 命中规则后的输出字段文本

            # 返回当前命中的输入输出说明，避免后续规则继续覆盖。
            return str_input, str_output

    # 在没有命中任何语义规则时回退到通用输入输出说明。
    return "待处理输入", "阶段结果"

# 把单个步骤摘要整理成正文、附图和权利要求共用的结构化步骤记录。
def build_step_record(
    int_index: int,
    str_summary: str,
    module_runtime_support: Any,
) -> dict[str, str]:
    """构建单个方法步骤结构化记录。

    参数：
    - `int_index`：当前步骤编号中的数值部分。
    - `str_summary`：当前步骤摘要文本。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `dict[str, str]`：单个方法步骤结构化记录。

    异常：
    - 无。
    """

    # 生成当前步骤的稳定编号，供正文、附图和权利要求复用同一骨架。
    str_step_id = f"S{int_index}"  # 当前步骤编号

    # 清洗步骤摘要文本，避免原始证据里的噪声字符直接进入正式正文。
    str_clean_summary = module_runtime_support.clean_text(str_summary)  # 当前步骤清洗后摘要文本

    # 先解析当前步骤的输入输出说明元组，避免后续重复判断语义规则。
    tuple_io_fields = resolve_step_io_fields(str_clean_summary)  # 当前步骤输入输出说明元组

    # 把元组首位值落成步骤记录的 input 字段。
    str_input = tuple_io_fields[0]  # 结构化记录里的 input 文本

    # 再补齐步骤末端产出字段，方便后链直接读取结果名称。
    str_output = tuple_io_fields[1]  # 最终输出字段文案

    # 返回当前步骤的结构化记录，供后续正文、附图与 claims 阶段共同复用。
    return {
        "id": str_step_id,
        "summary": str_clean_summary,
        "condition": "在当前案件已经完成前序步骤后执行。",
        "input": str_input,
        "action": str_clean_summary,
        "output": str_output,
    }

# 基于主案内容与术语列表整理出稳定的方法步骤骨架。
def build_method_steps(
    dict_selected: dict[str, Any],
    list_terms: list[str],
    module_runtime_support: Any,
) -> list[dict[str, str]]:
    """构建方法步骤列表。

    参数：
    - `dict_selected`：当前主案选择结果字典。
    - `list_terms`：聚合后的技术术语列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[dict[str, str]]`：方法步骤结构化记录列表。

    异常：
    - 无。
    """

    # 先把候选短句池拉出来，后面只负责覆盖默认骨架。
    list_solution_texts = collect_solution_texts(dict_selected, module_runtime_support)  # 后续覆盖默认骨架的短句池

    # 基于聚合术语生成默认步骤骨架，供正文证据不足时稳定回退。
    list_step_summaries = build_default_step_summaries(list_terms)  # 默认方法步骤摘要列表

    # 用正文证据里的可用短句覆盖默认骨架，尽量让步骤摘要贴近真实材料。
    overlay_solution_summaries(list_step_summaries, list_solution_texts)

    # 先准备结构化步骤结果列表，后续按顺序登记步骤编号与输入输出说明。
    list_steps: list[dict[str, str]] = []  # 结构化方法步骤结果列表

    # 逐条整理步骤摘要，补齐固定编号、输入、动作和输出字段。
    for int_index, str_summary in enumerate(list_step_summaries, start=101):

        # 把当前步骤摘要转换成结构化记录，并保持顺序写入结果列表。
        list_steps.append(build_step_record(int_index, str_summary, module_runtime_support))

    # 返回结构化方法步骤列表，供正文、附图和权利要求后链共同复用。
    return list_steps

# 根据步骤摘要语义归并系统模块名称。
def resolve_module_name(str_summary: str) -> str:
    """解析步骤摘要对应的系统模块名称。

    参数：
    - `str_summary`：当前步骤摘要文本。

    返回：
    - `str`：当前步骤应归并到的系统模块名称。

    异常：
    - 无。
    """

    # 用数据驱动的归并规则统一模块命名，避免正文与附图使用不同术语。
    list_module_rules = [
        (("采集", "获取"), "状态采集模块"),  # 采集类步骤归并规则
        (("计算", "评分"), "评分筛选模块"),  # 评分类步骤归并规则
        (("分配", "选择"), "任务分配模块"),  # 分配类步骤归并规则
        (("反馈", "更新"), "反馈更新模块"),  # 反馈类步骤归并规则
    ]  # 步骤语义到模块名称的归并规则

    # 逐条命中模块归并规则，优先返回最贴近当前步骤职责的模块名称。
    for tuple_keywords, str_module_name in list_module_rules:

        # 在当前步骤摘要命中关键词时，返回对应的模块职责名称。
        if any(str_keyword in str_summary for str_keyword in tuple_keywords):

            # 立即返回命中的模块名称，避免后续规则覆盖当前归并结果。
            return str_module_name

    # 在没有命中任何归并规则时回退到通用处理模块名称。
    return "处理模块"

# 把方法步骤收敛为系统模块骨架，避免系统方案与方法方案脱节。
def build_modules(list_steps: list[dict[str, str]]) -> list[dict[str, str]]:
    """构建系统模块列表。

    参数：
    - `list_steps`：结构化方法步骤列表。

    返回：
    - `list[dict[str, str]]`：系统模块结构化记录列表。

    异常：
    - 无。
    """

    # 先准备系统模块结果列表，后续按方法步骤语义逐项归并模块名称。
    list_modules: list[dict[str, str]] = []  # 系统模块结构化记录列表

    # 逐条读取方法步骤摘要，按语义归并成状态采集、评分筛选等模块名称。
    for dict_step in list_steps:

        # 读取当前步骤摘要文本，供模块名称归并规则判断复用。
        str_summary = dict_step["summary"]  # 当前步骤摘要文本

        # 按步骤摘要语义解析模块名称，保持系统方案与方法步骤的术语一致。
        str_module_name = resolve_module_name(str_summary)  # 当前步骤归并后的模块名称

        # 在当前模块名与上一条模块名相同时直接跳过，避免连续重复模块。
        if list_modules and list_modules[-1]["name"] == str_module_name:

            # 连续步骤归并到同一模块时跳过重复登记，保持模块清单精简。
            continue

        # 组装当前模块记录，保留模块名称与功能摘要的稳定映射关系。
        dict_module_record = {"name": str_module_name, "function": str_summary}  # 单个系统模块结构化记录

        # 把当前模块记录追加到结果列表，保持模块顺序与正文步骤顺序一致。
        list_modules.append(dict_module_record)

    # 返回系统模块结构化记录列表，供正文模块化方案和附图清单共同复用。
    return list_modules

# 整理 4.3 小节技术效果，优先使用主案效果或效果证据，缺失时回退到受控默认值。
def build_effect_lines(
    dict_selected: dict[str, Any],
    module_runtime_support: Any,
) -> list[str]:
    """构建技术效果条目列表。

    参数：
    - `dict_selected`：当前主案选择结果字典。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[str]`：适合直接写入 4.3 小节的技术效果条目列表。

    异常：
    - 无。
    """

    # 先准备直接效果条目列表，优先收录主案 effects 字段中的明确文本。
    list_effect_lines: list[str] = []  # 技术效果条目列表

    # 逐条清洗主案的直接效果描述，只保留真正可写入正文的条目。
    for str_item in dict_selected.get("effects", []):

        # 把当前技术效果文本清洗成单行文本，便于统一判断可用性。
        str_effect_line = module_runtime_support.clean_text(str_item)  # 当前技术效果条目文本

        # 在当前技术效果文本确实存在有效内容时再加入结果列表。
        if str_effect_line:

            # 把当前可用技术效果条目加入结果列表，优先作为 4.3 小节来源。
            list_effect_lines.append(str_effect_line)

    # 在已经得到至少一条效果条目时直接返回当前结果列表。
    if list_effect_lines:

        # 返回主案明确给出的技术效果条目列表。
        return list_effect_lines

    # 继续准备效果证据条目列表，在 effects 为空时从效果证据里补齐。
    list_effect_evidence_lines: list[str] = []  # 技术效果证据条目列表

    # 逐条清洗技术效果证据文本，只保留真正可写入正文的条目。
    for dict_item in dict_selected.get("technical_effect_evidence", []):

        # 读取并清洗当前效果证据文本，便于统一判断可用性。
        str_effect_evidence = module_runtime_support.clean_text(dict_item.get("text", ""))  # 当前效果证据条目文本

        # 在当前效果证据文本存在有效内容时再加入候选列表。
        if str_effect_evidence:

            # 把当前可用效果证据加入候选列表，作为 4.3 小节的次优来源。
            list_effect_evidence_lines.append(str_effect_evidence)

    # 在效果证据已经补出条目时直接返回当前证据条目列表。
    if list_effect_evidence_lines:

        # 返回效果证据条目列表，保持 4.3 小节尽量贴近真实主案材料。
        return list_effect_evidence_lines

    # 在主案和证据都没有给出明确效果时回退到最小正式表述。
    return ["当前材料说明该方案能够改善处理过程中的稳定性和资源利用效率。"]

# 生成 review 与 claims 可复用的轻量来源映射，避免正文关键特征脱离真实材料。
def build_evidence_map(
    path_case_dir: Path,
    list_steps: list[dict[str, str]],
    dict_selected: dict[str, Any],
    list_prior_summaries: list[str],
    module_runtime_support: Any,
) -> dict[str, Any]:
    """生成来源证据映射。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `list_steps`：结构化方法步骤列表。
    - `dict_selected`：当前主案选择结果字典。
    - `list_prior_summaries`：最接近现有技术摘要列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `dict[str, Any]`：已经写回 `latest_evidence_map.json` 的结构化映射字典。

    异常：
    - JSON 写入失败时由底层异常上抛。
    """

    # 先准备证据索引列表，后续逐批登记问题、方案、效果和现有技术来源。
    list_evidence_index: list[dict[str, str]] = []  # 证据索引列表

    # 逐项登记技术问题证据，供正文与自检回溯主问题来源。
    for int_index, dict_item in enumerate(dict_selected.get("technical_problem_evidence", []), start=1):

        # 读取并清洗当前问题证据文本，便于判断是否可登记到映射文件中。
        str_problem_text = module_runtime_support.clean_text(dict_item.get("text", ""))  # 当前问题证据文本

        # 在当前问题证据存在有效文本时再登记到证据索引列表。
        if str_problem_text:

            # 把当前问题证据写入来源索引，供正文与 review 阶段回溯。
            list_evidence_index.append({"id": f"E-PROB-{int_index}", "kind": "problem", "text": str_problem_text})

    # 逐项登记技术方案证据，供方法步骤和权利要求回溯主方案来源。
    for int_index, dict_item in enumerate(dict_selected.get("technical_solution_evidence", []), start=1):

        # 提取当前方案证据文本，供方法步骤与 claims 阶段共享来源编号。
        str_solution_text = module_runtime_support.clean_text(dict_item.get("text", ""))  # 当前方案证据文本

        # 在当前方案证据存在有效文本时再登记到证据索引列表。
        if str_solution_text:

            # 把当前方案证据写入来源索引，供方法步骤与权利要求回溯。
            list_evidence_index.append({"id": f"E-SOL-{int_index}", "kind": "solution", "text": str_solution_text})

    # 逐项登记技术效果证据，供正文技术效果和 review 回溯来源。
    for int_index, dict_item in enumerate(dict_selected.get("technical_effect_evidence", []), start=1):

        # 提取当前效果证据文本，供技术效果与自检阶段共享来源编号。
        str_effect_text = module_runtime_support.clean_text(dict_item.get("text", ""))  # 当前效果证据文本

        # 在当前效果证据存在有效文本时再登记到证据索引列表。
        if str_effect_text:

            # 把当前效果证据写入来源索引，供 review 与导出阶段回溯。
            list_evidence_index.append({"id": f"E-EFF-{int_index}", "kind": "effect", "text": str_effect_text})

    # 逐项登记最接近现有技术摘要，补齐背景技术对比来源索引。
    for int_index, str_summary in enumerate(list_prior_summaries, start=1):

        # 把当前现有技术摘要登记到证据索引列表，供 review 与导出回溯来源。
        list_evidence_index.append(
            {
                "id": f"E-PRIOR-{int_index}",
                "kind": "prior_art",
                "text": module_runtime_support.clean_text(str_summary),
            }
        )

    # 汇总技术方案证据编号，供后续方法步骤默认支撑集合复用。
    list_solution_ids = [dict_item["id"] for dict_item in list_evidence_index if dict_item["kind"] == "solution"]  # 技术方案证据编号列表

    # 汇总技术效果证据编号，供最后一步附带效果支撑时复用。
    list_effect_ids = [dict_item["id"] for dict_item in list_evidence_index if dict_item["kind"] == "effect"]  # 技术效果证据编号列表

    # 汇总技术问题证据编号，供第一步附带问题支撑时复用。
    list_problem_ids = [dict_item["id"] for dict_item in list_evidence_index if dict_item["kind"] == "problem"]  # 技术问题证据编号列表

    # 先准备特征映射列表，后续按步骤顺序登记步骤摘要与支持证据编号。
    list_features: list[dict[str, Any]] = []  # 正文特征映射列表

    # 逐项遍历方法步骤，补齐每一步的特征文本和支持证据编号列表。
    for int_index, dict_step in enumerate(list_steps):

        # 先复制一份方案证据编号列表，作为当前步骤的默认支撑集合。
        list_support_ids = list_solution_ids[:]  # 当前步骤默认支持证据编号列表

        # 在当前步骤是第一步且存在问题证据时，把问题证据并入支撑集合。
        if int_index == 0 and list_problem_ids:

            # 为第一步补入问题证据编号，说明方案起点针对的处理缺口。
            list_support_ids = list_problem_ids + list_support_ids  # 第一条步骤补入问题证据编号

        # 在当前步骤是最后一步且存在效果证据时，把效果证据并入支撑集合。
        if int_index == len(list_steps) - 1 and list_effect_ids:

            # 为最后一步补入效果证据编号，说明方案终点对应的技术收益。
            list_support_ids = list_support_ids + list_effect_ids  # 最后一条步骤补入效果证据编号

        # 组装当前步骤的特征映射记录，保持步骤摘要与支撑证据一一对应。
        dict_feature_record = {  # 单个步骤特征映射记录
            "type": "method_step",  # 特征类型
            "step": dict_step["id"],  # 步骤编号
            "feature": dict_step["summary"],  # 步骤特征文本
            "support_ids": list(dict.fromkeys(list_support_ids)),  # 去重后的支持证据编号列表
        }

        # 把当前步骤映射记录追加到特征列表，保持步骤顺序稳定。
        list_features.append(dict_feature_record)

    # 组装最终来源证据映射字典，供 review 和 claims 阶段共同复用。
    dict_evidence_map = {  # 最终来源证据映射字典
        "generated_at": module_runtime_support.iso_now(),  # 来源映射生成时间
        "case_dir": str(path_case_dir.resolve()),  # 当前案件目录绝对路径文本
        "evidence_index": list_evidence_index,  # 来源证据索引列表
        "features": list_features,  # 正文特征到来源编号的映射列表
    }

    # 把最新证据映射写回案件目录，供权利要求、自检和导出阶段统一读取。
    module_runtime_support.write_json_file(path_case_dir / "03_drafts" / "latest_evidence_map.json", dict_evidence_map)

    # 返回已经落盘的来源证据映射字典，便于当前正文阶段继续复用。
    return dict_evidence_map

# 把方法步骤整理成正文 4.2.1 小节可直接拼接的行列表。
def build_step_markdown_lines(list_steps: list[dict[str, str]]) -> list[str]:
    """构建方法步骤 Markdown 行列表。

    参数：
    - `list_steps`：结构化方法步骤列表。

    返回：
    - `list[str]`：正文 4.2.1 小节可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备步骤 Markdown 行列表，后续按方法步骤顺序依次追加说明块。
    list_step_lines: list[str] = []  # 方法步骤 Markdown 行列表

    # 逐项遍历方法步骤，按固定顺序输出摘要、条件、输入、动作和输出说明。
    for dict_step in list_steps:

        # 把当前步骤拆成固定说明块，保持 4.2.1 小节的阅读节奏稳定。
        list_step_lines.extend(
            [
                f"{dict_step['id']}：{dict_step['summary']}",
                "",
                f"本步骤的触发条件为：{dict_step['condition']}",
                f"输入为：{dict_step['input']}",
                f"技术动作为：{dict_step['action']}",
                f"输出为：{dict_step['output']}",
                "",
            ]
        )

    # 返回方法步骤 Markdown 行列表，供正文渲染阶段直接拼接。
    return list_step_lines

# 把系统模块整理成正文 4.2.2 小节可直接拼接的行列表。
def build_module_markdown_lines(list_modules: list[dict[str, str]]) -> list[str]:
    """构建系统模块 Markdown 行列表。

    参数：
    - `list_modules`：结构化系统模块列表。

    返回：
    - `list[str]`：正文 4.2.2 小节可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备系统模块 Markdown 行列表，后续按模块顺序依次追加条目。
    list_module_lines: list[str] = []  # 系统模块 Markdown 行列表

    # 逐条生成系统模块说明，保持模块名称和功能表述的稳定顺序。
    for int_index, dict_module in enumerate(list_modules, start=1):

        # 追加当前模块条目文本，供正文 4.2.2 小节直接写入模块清单。
        list_module_lines.append(f"{int_index}. {dict_module['name']}，用于 {dict_module['function']}")

    # 返回系统模块 Markdown 行列表，供正文渲染阶段直接拼接。
    return list_module_lines

# 把技术效果整理成正文 4.3 小节可直接拼接的行列表。
def build_effect_markdown_lines(list_effects: list[str]) -> list[str]:
    """构建技术效果 Markdown 行列表。

    参数：
    - `list_effects`：技术效果条目列表。

    返回：
    - `list[str]`：正文 4.3 小节可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备技术效果 Markdown 行列表，后续按条目顺序依次追加编号行。
    list_effect_lines: list[str] = []  # 技术效果 Markdown 行列表

    # 逐条生成技术效果编号行，保持效果条目在正文中的稳定顺序。
    for int_index, str_effect in enumerate(list_effects, start=1):

        # 追加当前技术效果编号行，供正文 4.3 小节直接复用。
        list_effect_lines.append(f"{int_index}. {str_effect.rstrip('。；;')}。")

    # 返回技术效果 Markdown 行列表，供正文渲染阶段直接拼接。
    return list_effect_lines

# 把待确认事项整理成正文末尾可直接拼接的行列表；为空时补一条受控默认提醒。
def build_missing_information_lines(
    list_missing_information: list[str],
    module_runtime_support: Any,
) -> list[str]:
    """构建待确认事项 Markdown 行列表。

    参数：
    - `list_missing_information`：上游主案结果中的待确认事项列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[str]`：正文末尾待确认事项可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备待确认事项 Markdown 行列表，后续按上游条目依次追加。
    list_missing_lines: list[str] = []  # 待确认事项 Markdown 行列表

    # 逐条清洗待确认事项文本，只保留真正可写入正文的条目。
    for str_item in list_missing_information:

        # 把当前待确认事项清洗成单行文本，便于统一判断可用性。
        str_missing_item = module_runtime_support.clean_text(str_item)  # 当前待确认事项文本

        # 在当前待确认事项存在有效文本时再生成 Markdown 条目。
        if str_missing_item:

            # 把当前待确认事项追加为 Markdown 列表项，供正文末尾直接写入。
            list_missing_lines.append(f"- {str_missing_item}")

    # 在上游已经给出待确认事项时直接返回当前条目列表。
    if list_missing_lines:

        # 返回上游待确认事项列表，保持正文末尾的工作项真实可追溯。
        return list_missing_lines

    # 在上游没有给出待确认事项时补一条最小正式提醒。
    return ["- 正式提交前仍需由发明人和代理人复核具体实施例参数与行政信息。"]

# 构建正文封面与发明名称章节。
def build_cover_section(
    str_case_name: str,
    str_title: str,
) -> list[str]:
    """构建封面与发明名称章节。

    参数：
    - `str_case_name`：当前案件名称文本。
    - `str_title`：正式交底书标题文本。

    返回：
    - `list[str]`：封面与发明名称章节的 Markdown 行列表。

    异常：
    - 无。
    """

    # 返回封面与发明名称章节的固定骨架。
    return [
        "# 发明/实用新型专利申请技术交底书",
        "",
        f"案件：{str_case_name}",
        "",
        "## 一、发明名称",
        "",
        str_title,
        "",
        "## 二、所属技术领域",
        "",
        f"本发明属于计算机数据处理与工程系统优化技术领域，具体涉及 {str_title}。",
        "",
    ]

# 构建现有技术章节，包括背景、最接近现有技术和缺点条目。
def build_prior_art_section(
    str_terms: str,
    str_prior_summary: str,
    list_problem_lines: list[str],
) -> list[str]:
    """构建现有技术章节。

    参数：
    - `str_terms`：背景技术小节使用的术语串接文本。
    - `str_prior_summary`：最接近现有技术主摘要文本。
    - `list_problem_lines`：现有技术缺点条目列表。

    返回：
    - `list[str]`：现有技术章节的 Markdown 行列表。

    异常：
    - 无。
    """

    # 先准备现有技术章节 Markdown 行列表，后续按章节顺序补齐问题条目。
    list_section_lines: list[str] = []  # 现有技术章节 Markdown 行列表

    # 先写入现有技术章节的固定骨架，建立背景与最接近现有技术描述。
    list_section_lines.extend(
        [
            "## 三、现有技术",
            "",
            "### 3.1 相关技术背景",
            "",
            f"围绕 {str_terms} 的工程场景，现有方案往往依赖固定规则或单指标决策，难以同时兼顾状态变化、异常反馈和处理效率。",
            "",
            "### 3.2 最接近现有技术",
            "",
            str_prior_summary,
            "",
            "### 3.3 现有技术缺点",
            "",
        ]
    )

    # 逐条写入现有技术缺点条目，保持 3.3 小节的编号结构稳定。
    for int_index, str_problem_line in enumerate(list_problem_lines, start=1):

        # 追加当前缺点编号行，保持问题条目与人工审阅顺序一致。
        list_section_lines.append(f"{int_index}. {str_problem_line.rstrip('。；;')}。")

    # 在现有技术缺点小节结束后补一个空行，便于进入发明内容总章。
    list_section_lines.append("")

    # 返回现有技术章节行列表，供正文渲染阶段统一拼接。
    return list_section_lines

# 构建发明内容章节，包括发明目的、方法流程、系统方案和技术效果。
def build_invention_section(
    str_problem: str,
    list_step_lines: list[str],
    list_module_lines: list[str],
    list_effect_lines: list[str],
) -> list[str]:
    """构建发明内容章节。

    参数：
    - `str_problem`：主案问题文本。
    - `list_step_lines`：方法步骤 Markdown 行列表。
    - `list_module_lines`：系统模块 Markdown 行列表。
    - `list_effect_lines`：技术效果 Markdown 行列表。

    返回：
    - `list[str]`：发明内容章节的 Markdown 行列表。

    异常：
    - 无。
    """

    # 先准备发明内容章节 Markdown 行列表，后续顺序拼接步骤、模块与效果条目。
    list_section_lines: list[str] = []  # 发明内容章节 Markdown 行列表

    # 先写入发明目的与方法流程小节标题，建立正文主体章节骨架。
    list_section_lines.extend(
        [
            "## 四、发明内容",
            "",
            "### 4.1 发明目的",
            "",
            f"本发明旨在针对“{str_problem}”所对应的处理缺口，形成可执行、可复核、可迭代的技术方案。",
            "",
            "### 4.2 技术解决方案",
            "",
            "#### 4.2.1 方法流程",
            "",
        ]
    )

    # 拼接方法步骤说明块，保持每一步都带条件、输入、动作和输出。
    list_section_lines.extend(list_step_lines)

    # 拼接系统/装置方案小节标题与模块条目。
    list_section_lines.extend(
        [
            "#### 4.2.2 系统/装置方案",
            "",
        ]
    )

    # 追加系统模块条目列表，保持模块职责与方法步骤顺序一致。
    list_section_lines.extend(list_module_lines)

    # 在系统方案小节与技术效果小节之间补一个空行。
    list_section_lines.append("")

    # 拼接技术效果小节标题与编号条目。
    list_section_lines.extend(
        [
            "### 4.3 技术效果",
            "",
        ]
    )

    # 追加技术效果编号条目，供正文渲染阶段直接拼接。
    list_section_lines.extend(list_effect_lines)

    # 返回发明内容章节行列表，供正文渲染阶段统一拼接。
    return list_section_lines

# 构建附图说明、实施方式、术语说明与待确认事项章节。
def build_tail_section(
    list_terms: list[str],
    list_missing_lines: list[str],
) -> list[str]:
    """构建正文尾部章节。

    参数：
    - `list_terms`：聚合后的技术术语列表。
    - `list_missing_lines`：待确认事项 Markdown 行列表。

    返回：
    - `list[str]`：正文尾部章节的 Markdown 行列表。

    异常：
    - 无。
    """

    # 先准备正文尾部章节 Markdown 行列表，后续顺序补齐术语与待确认事项。
    list_section_lines: list[str] = []  # 正文尾部章节 Markdown 行列表

    # 先写入附图说明、具体实施方式和术语说明章节骨架。
    list_section_lines.extend(
        [
            "",
            "## 五、附图及附图说明",
            "",
            "图 1 为方法流程图，用于示出 S101 起至末步骤的处理流程。",
            "图 2 为系统模块图，用于示出状态采集、评分筛选、任务分配和反馈更新之间的数据关系。",
            "",
            "## 六、具体实施方式",
            "",
            "在一个基本实施例中，系统先接收待处理输入，再依次执行 4.2.1 所述步骤，并把每一步输出作为下一步骤输入。",
            "在异常实施例中，当候选对象响应失败、状态不满足阈值或反馈记录出现异常时，系统触发回退与更新逻辑，避免持续选择不可用对象。",
            "在效果验证实施例中，应至少记录输入规模、运行环境、评价指标和对比对象，以支撑 4.3 小节技术效果。",
            "",
            "## 七、术语说明",
            "",
        ]
    )

    # 逐条写入术语说明列表，保持术语说明与上游术语聚合结果同步。
    for str_term in list_terms[:12]:

        # 追加当前术语条目，便于审阅人快速对齐正文里的关键名词。
        list_section_lines.append(f"- {str_term}")

    # 拼接来源证据摘要与待确认事项章节。
    list_section_lines.extend(
        [
            "",
            "## 八、来源证据摘要",
            "",
            "正式技术特征应回溯到 `latest_evidence_map.json` 中的来源编号；缺少来源支撑的内容不得作为定稿必要技术特征。",
            "",
            "## 九、待确认事项",
            "",
        ]
    )

    # 追加待确认事项列表，提醒正式提交前仍需人工补齐的内容。
    list_section_lines.extend(list_missing_lines)

    # 在正文尾部补一个空行，保持导出器读取结尾时的版式稳定。
    list_section_lines.append("")

    # 返回正文尾部章节行列表，供正文渲染阶段统一拼接。
    return list_section_lines

# 渲染正式中文交底书草稿，统一拼接标题、背景、方案、效果和待确认事项。
def render_markdown(
    dict_render_payload: dict[str, Any],
    module_runtime_support: Any,
) -> str:
    """渲染正式中文交底书草稿。

    参数：
    - `dict_render_payload`：包含正文渲染所需全部字段的结构化字典。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `str`：完整的正式中文交底书 Markdown 文本。

    异常：
    - 无。
    """

    # 读取最接近现有技术摘要列表，供背景技术与现有技术小节复用。
    list_prior_summaries = dict_render_payload["list_prior_summaries"]  # 最接近现有技术摘要列表

    # 读取技术术语列表，供背景技术与术语说明小节复用。
    list_terms = dict_render_payload["list_terms"]  # 聚合后的技术术语列表

    # 读取方法步骤列表，供 4.2.1 小节生成结构化流程说明。
    list_steps = dict_render_payload["list_steps"]  # 结构化方法步骤列表

    # 读取系统模块列表，供 4.2.2 小节生成模块化方案说明。
    list_modules = dict_render_payload["list_modules"]  # 结构化系统模块列表

    # 提取技术效果条目列表，供技术效果小节生成编号说明。
    list_effects = dict_render_payload["list_effects"]  # 4.3 小节的效果原始条目列表

    # 提取待确认事项列表，供正文末尾列出仍需人工补齐的内容。
    list_missing_information = dict_render_payload["list_missing_information"]  # 正文末尾待确认事项条目列表

    # 在存在最接近现有技术摘要时优先使用首条摘要，否则回退到受控默认说明。
    if list_prior_summaries:

        # 取首条已核验摘要作为 3.2 小节的主描述文本。
        str_prior_summary = list_prior_summaries[0]  # 最接近现有技术主摘要文本

    # 在缺少现有技术摘要时切换到受控兜底说明。
    else:

        # 在缺少已核验摘要时回退到受控说明，避免 3.2 小节完全空白。
        str_prior_summary = "当前工作区仅形成查新规划，正式提交前仍需补齐已核验的最接近现有技术。"  # 缺少现有技术时的兜底说明

    # 串接前几项技术术语，供背景技术小节形成更贴近主案的领域描述。
    str_terms = "、".join(list_terms[:8]) or "状态参数、处理规则和输出结果"  # 背景技术小节使用的术语串接文本

    # 生成 4.2.1 小节的步骤说明行列表，供正文渲染阶段直接插入。
    list_step_lines = build_step_markdown_lines(list_steps)  # 4.2.1 小节步骤说明行列表

    # 生成 4.2.2 小节的系统模块行列表，供正文渲染阶段直接插入。
    list_module_lines = build_module_markdown_lines(list_modules)  # 4.2.2 小节系统模块行列表

    # 生成 4.3 小节的技术效果行列表，供正文渲染阶段直接插入。
    list_effect_lines = build_effect_markdown_lines(list_effects)  # 4.3 小节技术效果行列表

    # 先把待确认事项预格式化成列表项，避免正文拼接时再做清洗。
    list_missing_lines = build_missing_information_lines(list_missing_information, module_runtime_support)  # 第九节待确认事项 Markdown 条目

    # 先准备正文 Markdown 行列表，后续按章节顺序逐段追加正式内容。
    list_markdown_lines: list[str] = []  # 正文 Markdown 文本行列表

    # 按章节顺序拼接封面、现有技术、发明内容与正文尾部章节。
    list_markdown_lines.extend(
        build_cover_section(
            dict_render_payload["str_case_name"],
            dict_render_payload["str_title"],
        )
    )

    # 再拼接现有技术章节，建立背景、最接近现有技术与问题条目。
    list_markdown_lines.extend(
        build_prior_art_section(
            str_terms,
            str_prior_summary,
            dict_render_payload["list_problem_lines"],
        )
    )

    # 然后拼接发明内容章节，写入方法流程、系统方案和技术效果。
    list_markdown_lines.extend(
        build_invention_section(
            dict_render_payload["str_problem"],
            list_step_lines,
            list_module_lines,
            list_effect_lines,
        )
    )

    # 最后拼接正文尾部章节，补齐附图说明、术语和待确认事项。
    list_markdown_lines.extend(build_tail_section(list_terms, list_missing_lines))

    # 返回完整 Markdown 文本，供案件目录落盘与后链工具继续复用。
    return "\n".join(list_markdown_lines)

# 把已核验查新记录规整成正文可直接使用的现有技术摘要句列表。
def build_prior_summaries(
    list_prior_records: list[dict[str, Any]],
    module_runtime_support: Any,
) -> list[str]:
    """构建最接近现有技术摘要列表。

    参数：
    - `list_prior_records`：已核验查新记录列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[str]`：最接近现有技术摘要列表。

    异常：
    - 无。
    """

    # 准备 3.2 小节可直接消费的摘要列表，后续按查新记录顺序逐条补入。
    list_prior_summaries: list[str] = []  # 最接近现有技术摘要结果列表

    # 逐项把查新记录规整成正文可直接使用的背景技术摘要句。
    for dict_record in list_prior_records:

        # 把当前查新记录压缩成单句摘要，便于 3.2 小节直接复用。
        list_prior_summaries.append(module_runtime_support.summarize_prior_art(dict_record))

    # 返回现有技术摘要列表，供正文与证据映射阶段共同复用。
    return list_prior_summaries

# 执行正式草稿生成入口，读取主案结果并输出交底书草稿与证据映射。
def main() -> int:
    """执行正式草稿生成入口。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 预览未确认、主案结果缺失或文件写入失败时由底层异常上抛。
    """

    # 加载共享运行时支持模块，复用文本清洗、时间戳和 JSON 读写工具。
    module_runtime_support = load_runtime_support_module()  # 共享运行时支持模块

    # 解析命令行参数，读取案件目录和内部预览放行开关。
    namespace_arguments = build_parser().parse_args()  # 正式草稿入口参数对象

    # 解析案件目录绝对路径，确保所有正文产物都固定落回当前案件空间。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 当前案件根目录路径

    # 先把内部预览放行开关整理成布尔值，供确认门逻辑直接复用。
    bool_allow_unconfirmed_preview = bool(namespace_arguments.allow_unconfirmed_preview)  # 是否允许内部绕过预览确认门

    # 校验当前案件是否已经通过预览确认门，未通过时默认阻止正式正文继续生成。
    ensure_preview_confirmed(path_case_dir, bool_allow_unconfirmed_preview, module_runtime_support)

    # 把研究根目录中的已核验查新记录同步到案件目录，避免正文直接依赖工作区外部文件。
    stage_verified_prior_art_records(path_case_dir, module_runtime_support)

    # 读取主案选择结果与 facts 结果，作为正文起草阶段的上游结构化输入。
    dict_loaded_bundle = load_selected_bundle(path_case_dir, module_runtime_support)  # 主案与 facts 结果组合字典

    # 从加载结果中解出主案选择包，作为标题和正文骨架的直接来源。
    dict_selected_bundle = dict_loaded_bundle["selected_bundle"]  # 主案选择包原始载荷

    # 同步取出 facts 结果，供术语聚合与补充材料提炼时复用。
    dict_facts = dict_loaded_bundle["facts"]  # facts 阶段结构化材料

    # 读取当前真正被选中的主案字典，供正文围绕主问题与主方案展开。
    dict_selected = dict_selected_bundle["selected"]  # 当前主案字典

    # 清洗案件名文本，供正文页眉和快照命名共同复用。
    str_case_name = module_runtime_support.clean_text(dict_selected_bundle.get("case_name", path_case_dir.name))  # 当前案件名称文本

    # 规整正式交底书标题，补齐“一种”和技术客体后缀。
    str_title = normalize_title(dict_selected.get("name", str_case_name), module_runtime_support)  # 正式交底书标题文本

    # 清洗主案问题文本，作为现有技术缺点与发明目的小节的核心输入。
    str_problem = module_runtime_support.clean_text(dict_selected.get("problem", "当前技术问题仍需结合研发材料核对。"))  # 主案问题文本

    # 生成 3.3 小节的问题条目列表，保持现有技术缺点可直接写入正文。
    list_problem_lines = build_problem_lines(str_problem, module_runtime_support)  # 3.3 小节问题编号条目

    # 聚合主案与 facts 中的关键术语，供背景、术语说明和步骤骨架复用。
    list_terms = module_runtime_support.collect_terms(dict_selected, dict_facts)  # 背景与术语说明聚合结果

    # 基于主案方案和术语列表生成方法步骤骨架，作为正文主链的核心结构。
    list_steps = build_method_steps(dict_selected, list_terms, module_runtime_support)  # 4.2.1 方法流程结构化步骤

    # 把方法步骤归并成系统模块骨架，供装置方案与附图说明复用同一术语。
    list_modules = build_modules(list_steps)  # 4.2.2 装置方案模块清单

    # 生成 4.3 小节的技术效果条目列表，保持效果表述与真实材料一致。
    list_effects = build_effect_lines(dict_selected, module_runtime_support)  # 4.3 小节效果编号条目

    # 读取并筛选已核验查新记录，供背景技术与证据映射阶段复用。
    list_prior_records = module_runtime_support.read_verified_prior_art_records(path_case_dir)  # 已核验查新记录列表

    # 把查新记录规整成正文可直接使用的最接近现有技术摘要列表。
    list_prior_summaries = build_prior_summaries(list_prior_records, module_runtime_support)  # 3.2 小节现有技术摘要列表

    # 复制待确认事项列表，避免正文渲染阶段直接共享上游可变对象。
    list_missing_information = list(dict_selected_bundle.get("missing_information", []))  # 待人工补齐的事项列表

    # 先登记封面与发明内容摘要字段，供封面、技术领域和发明目的章节直接复用。
    dict_render_payload: dict[str, Any] = {
        "str_case_name": str_case_name,  # 封面案件名称文本
        "str_title": str_title,  # 发明名称标题文本
        "str_problem": str_problem,  # 发明目的核心问题文本
    }

    # 再登记正文主体章节依赖的条目列表，保持问题、步骤、模块与效果同源。
    dict_render_payload.update(
        {
            "list_problem_lines": list_problem_lines,  # 3.3 小节问题条目列表
            "list_steps": list_steps,  # 4.2.1 方法步骤列表
            "list_modules": list_modules,  # 4.2.2 模块条目列表
            "list_effects": list_effects,  # 4.3 小节效果条目列表
        }
    )

    # 最后登记辅助渲染字段，供背景、术语说明和待确认事项章节统一读取。
    dict_render_payload.update(
        {
            "list_terms": list_terms,  # 背景与术语说明词表
            "list_prior_summaries": list_prior_summaries,  # 3.2 小节现有技术摘要
            "list_missing_information": list_missing_information,  # 末尾待确认事项列表
        }
    )

    # 先写出最新证据映射文件，供权利要求、自检和导出阶段统一回溯来源。
    build_evidence_map(
        path_case_dir,
        list_steps,
        dict_selected,
        list_prior_summaries,
        module_runtime_support,
    )

    # 渲染完整正式中文交底书 Markdown 文本。
    str_markdown = render_markdown(dict_render_payload, module_runtime_support)  # 完整正式中文交底书 Markdown 文本

    # 确保草稿输出目录存在，供稳定草稿和快照草稿共同落盘。
    path_output_dir = module_runtime_support.ensure_dir(path_case_dir / "03_drafts")  # 草稿输出目录路径

    # 固定稳定主草稿路径，供后链默认读取当前最新正文。
    path_stable_draft = path_output_dir / "disclosure_draft.md"  # 稳定主草稿路径

    # 先把案件名规整成安全快照前缀，避免快照文件名包含非法字符。
    str_snapshot_name = module_runtime_support.sanitize_name(str_case_name)  # 草稿快照安全文件名前缀

    # 把当前时间规整成紧凑时间片段，供快照文件名保持时间顺序。
    str_snapshot_timestamp = module_runtime_support.iso_now().replace(":", "").replace("-", "")  # 草稿快照时间片段

    # 拼出本轮正文快照路径，便于后续人工回看生成历史。
    path_snapshot_draft = path_output_dir / f"{str_snapshot_name}_{str_snapshot_timestamp}.md"  # 正文快照路径

    # 把稳定主草稿写入案件目录，供后链默认按约定路径读取。
    module_runtime_support.write_text_file(path_stable_draft, str_markdown)

    # 把时间快照草稿也写入案件目录，保留本轮生成历史供人工回看。
    module_runtime_support.write_text_file(path_snapshot_draft, str_markdown)

    # 把稳定主草稿绝对路径写回标准输出，供上游流水线与测试稳定解析。
    sys.stdout.write(str(path_stable_draft.resolve()) + "\n")

    # 返回成功退出码，表示当前正式正文与证据映射都已落盘。
    return 0

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())
