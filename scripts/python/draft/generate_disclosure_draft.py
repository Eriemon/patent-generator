#!/usr/bin/env python3
"""基于主案结果生成正式中文交底书草稿。"""

# 启用未来版本注解行为，保证类型标注在当前解释器下稳定可用。
from __future__ import annotations

# 引入参数解析、按路径加载模块、文件复制、标准输出和路径能力，供正式草稿入口稳定运行。
import argparse
import hashlib
import importlib.util
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# 固定共享运行时支持模块路径，避免通过修改 sys.path 导入公共工具。
PATH_RUNTIME_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "runtime_support.py"  # 共享运行时支持模块路径

# 固定正文质量合同路径，确保起草、证据映射和后续自检共用同一受控推断边界。
PATH_QUALITY_CONTRACT = Path(__file__).resolve().parents[1] / "support" / "disclosure_quality_contract.py"  # 正文质量合同模块路径

# 固定版本二结构化模型构建器路径，确保正式生成链真实产出中间真相层。
PATH_DISCLOSURE_MODEL = Path(__file__).resolve().parent / "disclosure_model.py"  # 结构化模型构建器路径

# 固定最终 DOCX 模板路径，供预览状态记录可追溯的模板哈希。
PATH_TEMPLATE_DOCX = Path(__file__).resolve().parents[3] / "assets" / "cn_technical_disclosure_template.docx"  # 最终 DOCX 模板路径

# 预编译 display-math 公式块匹配规则，供从本地研究材料中抽取可追溯公式复用。
RE_DISPLAY_FORMULA_BLOCK = re.compile(r"\$\$(.*?)\$\$", flags=re.DOTALL)  # display-math 公式块匹配规则

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

# 加载正文质量合同模块，统一术语、证据和推断边界。
def load_quality_contract_module() -> Any:
    """按路径加载正文质量合同模块。

    参数：
    - 无。

    返回：
    - `Any`：已经执行源码的正文质量合同模块对象。

    异常：
    - 合同模块缺失或无法加载时抛出 `ImportError`。
    """

    # 根据质量合同文件路径创建独立加载规格，避免依赖包安装状态。
    obj_specification = importlib.util.spec_from_file_location(  # 正文质量合同模块加载规格
        "readable_patent_disclosure_quality_contract",  # 临时质量合同模块名称
        PATH_QUALITY_CONTRACT,  # 质量合同源码真实路径
    )

    # 加载规格或加载器缺失时立即失败，避免后续以空模块继续起草。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出带真实目标路径的导入错误，便于定位技能文件损坏。
        raise ImportError("> ERR: [Python] 无法加载 support/disclosure_quality_contract.py。")

    # 从加载规格创建临时模块对象，承接质量合同中的纯函数接口。
    module_quality_contract = importlib.util.module_from_spec(obj_specification)  # 正文质量合同模块对象

    # 执行质量合同源码，把术语、证据和推断规则装入临时模块。
    obj_specification.loader.exec_module(module_quality_contract)

    # 返回已完成加载的质量合同模块，供起草全链路复用同一规则集。
    return module_quality_contract

# 按受管路径加载版本二结构化模型构建器。
def load_disclosure_model_module() -> Any:
    """加载结构化专利交底模型构建器。

    参数：
    - 无。

    返回：
    - `Any`：已执行源码的结构化模型模块。

    异常：
    - `ImportError`：模块规格或加载器不可用时抛出。
    """

    # 使用稳定内部名称加载同目录模块，避免依赖调用方 sys.path。
    obj_specification = importlib.util.spec_from_file_location(  # 结构化模型加载规格
        "readable_patent_disclosure_model",  # 模块内部名称
        PATH_DISCLOSURE_MODEL,  # 正式模型构建器路径
    )

    # 缺少加载规格意味着正式生成链无法产出版本二合同，必须立即阻断。
    if obj_specification is None or obj_specification.loader is None:

        # 明确报告正式模型构建器不可用，禁止继续生成只有 Markdown 的假版本二案件。
        raise ImportError("> ERR: [Python] 无法加载 draft/disclosure_model.py。")

    # 执行正式源码并返回模块对象，供主流程组装模型。
    module_disclosure_model = importlib.util.module_from_spec(obj_specification)  # 结构化模型模块

    # 执行模型构建器源码，使公共纯函数进入隔离模块对象。
    obj_specification.loader.exec_module(module_disclosure_model)

    # 返回已初始化模块供正式生成入口复用。
    return module_disclosure_model

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
    - `module_quality_contract`：正文质量合同模块对象。

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

# 提取步骤证据映射需要的受控关键词，避免噪声扩散到全部步骤。
def collect_evidence_keywords(str_text: str, module_quality_contract: Any) -> list[str]:
    """从文本中提取可用于精确步骤映射的受控关键词。

    参数：
    - `str_text`：步骤或证据的原始文本。
    - `module_quality_contract`：正文质量合同模块对象。

    返回：
    - `list[str]`：只保留在文本中实际出现的业务关键词。

    异常：
    - 无。
    """

    # 固定允许参与步骤映射的业务关键词，排除公式 token 和通用英文噪声。
    tuple_candidate_keywords = (  # 证据映射允许使用的候选关键词元组
        "状态",  # 状态类步骤关键词
        "采集",  # 采集类步骤关键词
        "获取",  # 获取类步骤关键词
        "任务",  # 任务类步骤关键词
        "计算",  # 计算类步骤关键词
        "评分",  # 评分类步骤关键词
        "筛选",  # 筛选类步骤关键词
        "分配",  # 分配类步骤关键词
        "选择",  # 选择类步骤关键词
        "反馈",  # 反馈类步骤关键词
        "更新",  # 更新类步骤关键词
        "异常",  # 异常类步骤关键词
        "执行",  # 执行类步骤关键词
    )

    # 仅保留在当前文本中真实命中的关键词，避免把全部证据泛挂到每一步。
    list_keywords = [  # 当前文本实际命中的业务关键词
        str_keyword  # 当前命中的单个业务关键词
        for str_keyword in tuple_candidate_keywords  # 遍历受控候选关键词
        if str_keyword in str_text  # 只保留当前文本真实包含的关键词
    ]
    
    # 输出过滤后的业务关键词，作为当前步骤的最小证据匹配集合。
    return module_quality_contract.filter_technical_terms(list_keywords)

# 把单个步骤摘要整理成正文、附图和权利要求共用的结构化步骤记录。
def build_step_record(
    int_index: int,
    str_summary: str,
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> dict[str, Any]:
    """构建单个方法步骤结构化记录。

    参数：
    - `int_index`：当前步骤编号中的数值部分。
    - `str_summary`：当前步骤摘要文本。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `module_quality_contract`：正文质量合同模块对象。

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

    # 把摘要中实际出现的业务关键词登记到步骤中，供证据映射按步骤精确匹配。
    list_keywords = collect_evidence_keywords(str_clean_summary, module_quality_contract)  # 当前步骤关键词

    # 返回当前步骤的结构化记录，供后续正文、附图与 claims 阶段共同复用。
    return {
        "id": str_step_id,
        "summary": str_clean_summary,
        "condition": f"当接收到{str_input}时执行。",
        "input": str_input,
        "action": str_clean_summary,
        "output": str_output,
        "keywords": list_keywords,
    }

# 基于主案内容与术语列表整理出稳定的方法步骤骨架。
def build_method_steps(
    dict_selected: dict[str, Any],
    list_terms: list[str],
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> list[dict[str, Any]]:
    """构建方法步骤列表。

    参数：
    - `dict_selected`：当前主案选择结果字典。
    - `list_terms`：聚合后的技术术语列表。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `module_quality_contract`：正文质量合同模块对象。

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
    list_steps: list[dict[str, Any]] = []  # 结构化方法步骤结果列表

    # 逐条整理步骤摘要，补齐固定编号、输入、动作和输出字段。
    for int_index, str_summary in enumerate(list_step_summaries, start=101):

        # 把当前步骤摘要转换成结构化记录，并保持顺序写入结果列表。
        list_steps.append(
            build_step_record(
                int_index,
                str_summary,
                module_runtime_support,
                module_quality_contract,
            )
        )

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
    module_quality_contract: Any,
) -> list[str]:
    """构建技术效果条目列表。

    参数：
    - `dict_selected`：当前主案选择结果字典。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `module_quality_contract`：正文质量合同模块对象。

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
        if module_quality_contract.is_effect_evidence(str_effect_line):

            # 把当前可用技术效果条目加入结果列表，优先作为 4.3 小节来源。
            list_effect_lines.append(str_effect_line)

    # 在已经得到至少一条效果条目时直接返回当前结果列表。
    if list_effect_lines:

        # 返回主案明确给出的技术效果条目列表。
        return list_effect_lines

    # 继续准备效果证据条目列表，在 effects 为空时从效果证据里补齐。
    list_effect_evidence_lines: list[str] = []  # 技术效果证据条目列表

    # 逐条清洗技术效果证据文本，只保留真正可写入正文的条目。
    list_filtered_effect_evidence = module_quality_contract.filter_effect_evidence(  # 已通过效果分类的证据列表
        dict_selected.get("technical_effect_evidence", [])  # 主案提供的效果证据候选
    )

    # 逐条读取已通过分类的效果证据，避免方案或问题陈述误入效果章节。
    for dict_item in list_filtered_effect_evidence:

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

    # 证据不足时保留空列表，让质量门生成待修订项，禁止用无依据的效果句掩盖缺口。
    return []

# 生成 review 与 claims 可复用的轻量来源映射，避免正文关键特征脱离真实材料。
def build_evidence_map(
    path_case_dir: Path,
    list_steps: list[dict[str, Any]],
    dict_selected: dict[str, Any],
    list_prior_summaries: list[str],
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> dict[str, Any]:
    """生成来源证据映射。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `list_steps`：结构化方法步骤列表。
    - `dict_selected`：当前主案选择结果字典。
    - `list_prior_summaries`：最接近现有技术摘要列表。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `module_quality_contract`：正文质量合同模块对象。

    返回：
    - `dict[str, Any]`：已经写回 `latest_evidence_map.json` 的结构化映射字典。

    异常：
    - JSON 写入失败时由底层异常上抛。
    """

    # 先准备证据索引列表，后续逐批登记问题、方案、效果和现有技术来源。
    list_evidence_index: list[dict[str, Any]] = []  # 证据索引列表

    # 逐项登记技术问题证据，供正文与自检回溯主问题来源。
    for int_index, dict_item in enumerate(dict_selected.get("technical_problem_evidence", []), start=1):

        # 读取并清洗当前问题证据文本，便于判断是否可登记到映射文件中。
        str_problem_text = module_runtime_support.clean_text(dict_item.get("text", ""))  # 当前问题证据文本

        # 在当前问题证据存在有效文本时再登记到证据索引列表。
        if str_problem_text:

            # 把当前问题证据写入来源索引，供正文与 review 阶段回溯。
            list_evidence_index.append(
                {
                    "id": f"E-PROB-{int_index}",
                    "kind": "problem",
                    "text": str_problem_text,
                    "keywords": collect_evidence_keywords(str_problem_text, module_quality_contract),
                }
            )

    # 逐项登记技术方案证据，供方法步骤和权利要求回溯主方案来源。
    for int_index, dict_item in enumerate(dict_selected.get("technical_solution_evidence", []), start=1):

        # 提取当前方案证据文本，供方法步骤与 claims 阶段共享来源编号。
        str_solution_text = module_runtime_support.clean_text(dict_item.get("text", ""))  # 当前方案证据文本

        # 在当前方案证据存在有效文本时再登记到证据索引列表。
        if str_solution_text:

            # 把当前方案证据写入来源索引，供方法步骤与权利要求回溯。
            list_evidence_index.append(
                {
                    "id": f"E-SOL-{int_index}",
                    "kind": "solution",
                    "text": str_solution_text,
                    "keywords": collect_evidence_keywords(str_solution_text, module_quality_contract),
                }
            )

    # 逐项登记技术效果证据，供正文技术效果和 review 回溯来源。
    for int_index, dict_item in enumerate(dict_selected.get("technical_effect_evidence", []), start=1):

        # 提取当前效果证据文本，供技术效果与自检阶段共享来源编号。
        str_effect_text = module_runtime_support.clean_text(dict_item.get("text", ""))  # 当前效果证据文本

        # 在当前效果证据存在有效文本时再登记到证据索引列表。
        if str_effect_text:

            # 把当前效果证据写入来源索引，供 review 与导出阶段回溯。
            list_evidence_index.append(
                {
                    "id": f"E-EFF-{int_index}",
                    "kind": "effect",
                    "text": str_effect_text,
                    "keywords": collect_evidence_keywords(str_effect_text, module_quality_contract),
                }
            )

    # 逐项登记最接近现有技术摘要，补齐背景技术对比来源索引。
    for int_index, str_summary in enumerate(list_prior_summaries, start=1):

        # 把当前现有技术摘要登记到证据索引列表，供 review 与导出回溯来源。
        list_evidence_index.append(
            {
                "id": f"E-PRIOR-{int_index}",
                "kind": "prior_art",
                "text": module_runtime_support.clean_text(str_summary),
                "keywords": collect_evidence_keywords(str_summary, module_quality_contract),
            }
        )

    # 由质量合同按关键词构建步骤到证据的最小映射，禁止把全部证据泛挂到每一步。
    list_features = module_quality_contract.build_step_support_map(list_steps, list_evidence_index)  # 精确步骤证据映射

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

# 写入起草计划、槽位正文和哈希状态，锁定预览确认边界。
def write_draft_contract_artifacts(
    path_output_dir: Path,
    str_markdown: str,
    dict_artifact_context: dict[str, Any],
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> None:
    """写入起草计划、槽位正文和预览哈希，锁定确认后的生成边界。

    参数：
    - `path_output_dir`：草稿输出目录。
    - `str_markdown`：已生成的主交底书 Markdown。
    - `dict_artifact_context`：标题、步骤、模块和效果组成的合同上下文。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `module_quality_contract`：正文质量合同模块对象。

    返回：
    - `None`。

    异常：
    - 状态文件或 JSON 写入失败时由底层异常上抛。
    """

    # 从合同上下文解出各槽位数据，保持函数参数数量和写入边界清晰。
    str_title = str(dict_artifact_context["title"])  # 正式发明标题

    # 复制步骤列表，避免写入阶段修改主流程持有的原始对象。
    list_steps = list(dict_artifact_context["steps"])  # 结构化方法步骤列表

    # 复制模块列表，保持装置槽位数据在写入期间稳定。
    list_modules = list(dict_artifact_context["modules"])  # 结构化模块列表

    # 复制技术效果列表，保持质量分类结果不被合同装配修改。
    list_effects = list(dict_artifact_context["effects"])  # 已分类技术效果列表

    # 仅登记不引入新事实的结构性连接补写，供预览阶段显式确认。
    list_inference_candidates = ["将前一处理步骤的输出作为下一处理步骤的输入。"]  # 受控推断候选列表

    # 根据标题、步骤和推断候选生成可追踪的代理起草计划。
    dict_draft_plan = module_quality_contract.build_draft_plan(  # 代理起草计划与推断清单
        str_title,  # 起草计划使用的发明名称
        list_steps,  # 起草计划覆盖的方法步骤
        list_inference_candidates,  # 待确认的结构性推断候选
    )

    # 将正文结构整理为与模板槽位一一对应的机器可读合同。
    dict_draft_content = {  # 与最终模板槽位对应的正文内容
        "title": str_title,  # 发明名称槽位内容
        "template_slots": {"一、发明名称": str_title},  # 模板标题槽位映射
        "method_steps": list_steps,  # 方法方案槽位内容
        "modules": list_modules,  # 装置模块槽位内容
        "effects": list_effects,  # 技术效果槽位内容
    }

    # 分别计算正文和模板哈希，用于阻止确认后的内容或模板静默漂移。
    str_draft_hash = hashlib.sha256(str_markdown.encode("utf-8")).hexdigest()  # 主正文内容哈希

    # 单独计算模板哈希，使模板变更也会触发重新确认。
    str_template_hash = hashlib.sha256(PATH_TEMPLATE_DOCX.read_bytes()).hexdigest()  # 模板内容哈希

    # 读取现有预览状态，保留人工确认标记并更新当前生成资格。
    path_preview_status = path_output_dir / "preview_status.json"  # 预览确认状态路径

    # 从稳定路径加载当前预览状态，随后仅更新本轮生成字段。
    dict_preview_status = module_runtime_support.read_json_file(path_preview_status)  # 当前预览确认状态

    # 只收集质量合同允许的推断编号，禁止被拒绝项进入确认范围。
    list_inference_ids = [  # 已登记推断编号列表
        str(dict_item["id"])  # 当前允许推断项的稳定编号
        for dict_item in dict_draft_plan["inferences"]  # 扫描计划登记的推断对象
        if dict_item["allowed"]  # 只暴露允许进入确认边界的推断
    ]

    # 把本轮哈希、推断边界和起草状态原子更新到预览状态对象。
    dict_preview_status.update(
        {
            "draft_hash": str_draft_hash,
            "template_hash": str_template_hash,
            "inference_ids": list_inference_ids,
            "inferences_confirmed": bool(dict_preview_status.get("confirmed")),
            "authoring_status": (
                "authoring_required"
                if not dict_preview_status.get("confirmed")
                else "ready_for_export"
            ),
        }
    )

    # 分别写出起草计划、槽位正文和预览状态，供后续验证与导出消费。
    module_runtime_support.write_json_file(path_output_dir / "draft_plan.json", dict_draft_plan)

    # 写出与模板槽位对应的正文合同，供 DOCX 装配器直接消费。
    module_runtime_support.write_json_file(path_output_dir / "draft_content.json", dict_draft_content)

    # 最后写出预览状态，使哈希和推断确认结果保持一致。
    module_runtime_support.write_json_file(path_preview_status, dict_preview_status)

# 把方法步骤整理成正文 4.2.2 小节可直接拼接的行列表。
def build_step_markdown_lines(list_steps: list[dict[str, str]]) -> list[str]:
    """构建方法步骤 Markdown 行列表。

    参数：
    - `list_steps`：结构化方法步骤列表。

    返回：
    - `list[str]`：正文 4.2.2 小节可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备步骤 Markdown 行列表，后续按方法步骤顺序依次追加说明块。
    list_step_lines: list[str] = []  # 方法步骤 Markdown 行列表

    # 逐项遍历方法步骤，按固定顺序输出摘要、条件、输入、动作和输出说明。
    for dict_step in list_steps:

        # 把当前步骤拆成固定说明块，保持 4.2.2 小节的阅读节奏稳定。
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

# 把系统模块整理成正文 4.2.1 小节可直接拼接的行列表。
def build_module_markdown_lines(list_modules: list[dict[str, str]]) -> list[str]:
    """构建系统模块 Markdown 行列表。

    参数：
    - `list_modules`：结构化系统模块列表。

    返回：
    - `list[str]`：正文 4.2.1 小节可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备系统模块 Markdown 行列表，后续按模块顺序依次追加条目。
    list_module_lines: list[str] = []  # 系统模块 Markdown 行列表

    # 逐条生成系统模块说明，保持模块名称和功能表述的稳定顺序。
    for int_index, dict_module in enumerate(list_modules, start=1):

        # 追加当前模块条目文本，供正文 4.2.1 小节直接写入模块清单。
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

# 从研究根目录的本地材料中提取 display-math 公式块，保证正式交付源稿可追溯公式来源。
def collect_formula_blocks_from_research_root(
    path_case_dir: Path,
    module_runtime_support: Any,
) -> list[str]:
    """从研究根目录提取 display-math 公式块。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[str]`：按材料扫描顺序去重后的公式块正文列表。

    异常：
    - 文件读取失败时由底层异常上抛。
    """

    # 载入当前案件配置，后续只从中读取研究材料根目录用于本地公式追溯。
    dict_case_config = module_runtime_support.load_case_config(path_case_dir)  # research_root 来源的案件配置映射

    # 读取研究根目录文本；缺失时直接返回空列表。
    str_research_root = dict_case_config.get("research_root", "")  # 研究材料根目录文本

    # 在案件配置未登记研究根目录时直接返回空列表。
    if not str_research_root:

        # 空列表表示当前案件暂无可追溯的本地公式块材料。
        return []

    # 解析研究根目录绝对路径，后续据此扫描 Markdown 和文本材料。
    path_research_root = Path(str_research_root).resolve()  # 研究材料根目录路径

    # 在研究根目录不存在时直接返回空列表，避免引用无效外部路径。
    if not path_research_root.exists():

        # 空列表表示当前案件的研究材料目录不可用。
        return []

    # 先准备去重后的公式块正文列表，保持多材料扫描结果稳定。
    list_formula_blocks: list[str] = []  # 去重后的公式块正文列表

    # 记录已见公式键，避免同一公式因多份同步材料重复进入正文。
    set_seen_formulas: set[str] = set()  # 已见公式去重键集合

    # 逐个扫描常见文本材料后缀，只从本地文本源抽取 display-math 公式块。
    for path_source in sorted(path_research_root.rglob("*")):

        # 只处理常见文本材料，避免对二进制文件盲读造成噪声。
        if path_source.suffix.lower() not in {".md", ".txt"} or not path_source.is_file():

            # 当前文件不是受支持的本地文本材料，继续检查下一项。
            continue

        # 读取当前文本材料全文，供 display-math 匹配规则复用。
        str_source_text = path_source.read_text(encoding="utf-8")  # 当前材料全文

        # 顺序提取当前材料中的所有 display-math 公式块。
        for str_formula in RE_DISPLAY_FORMULA_BLOCK.findall(str_source_text):

            # 先读取当前公式块的原始行序列，供后续统一规整空白和保留原始换行顺序。
            list_raw_formula_lines = str_formula.splitlines()  # 当前公式块原始正文行列表

            # 先把每一行做去首尾空白处理，供后续统一过滤空行。
            list_stripped_formula_lines = [str_formula_line.strip() for str_formula_line in list_raw_formula_lines]  # 当前公式块去空白后的正文行

            # 再过滤掉空行，避免空白内容干扰去重与主稿保留。
            list_formula_text_lines = [str_line for str_line in list_stripped_formula_lines if str_line]  # 当前公式块有效正文行

            # 再按保留换行的形式拼回公式正文，供 Markdown 主稿直接复用。
            str_formula_text = "\n".join(list_formula_text_lines)  # 当前公式块保留换行的正文文本

            # 把当前公式块压缩成单行键，用于跨文件去重。
            str_formula_key = re.sub(r"\s+", "", str_formula_text)  # 当前公式块去重键

            # 空公式或重复公式都不再进入结果列表。
            if not str_formula_key or str_formula_key in set_seen_formulas:

                # 当前公式块无效或已收录，继续检查下一条公式。
                continue

            # 登记当前公式块去重键，避免后续重复追加。
            set_seen_formulas.add(str_formula_key)

            # 把当前本地公式块追加到结果列表，供正式交付源稿复用。
            list_formula_blocks.append(str_formula_text)

    # 返回已去重的公式块正文列表，供 Markdown 正文插入受控公式段。
    return list_formula_blocks

# 把公式块整理成正文 4.2.2 小节可直接拼接的 Markdown 行列表。
def build_formula_markdown_lines(list_formula_blocks: list[str]) -> list[str]:
    """构建公式块 Markdown 行列表。

    参数：
    - `list_formula_blocks`：从本地研究材料抽取的公式块正文列表。

    返回：
    - `list[str]`：正文 4.2.2 小节可直接拼接的公式说明与公式块行列表。

    异常：
    - 无。
    """

    # 没有公式块时返回空列表，让正文安全降级为纯文字方案描述。
    if not list_formula_blocks:

        # 空列表表示当前正文无需额外插入公式块段落。
        return []

    # 先准备公式说明首句，作为后续所有 display-math 公式块的统一导语。
    str_formula_intro = "在一个实施例中，所述评分、筛选或参数更新逻辑可结合本地研发材料中的公式表达进一步限定如下："  # 正文公式说明首句

    # 再初始化公式说明与公式块行列表，后续按顺序继续追加每个公式块。
    list_formula_lines = [str_formula_intro, ""]  # 公式块 Markdown 行列表

    # 按公式顺序逐个写出 display-math 公式块，保持与本地材料语义一致。
    for str_formula_block in list_formula_blocks:

        # 先写入公式块起始标记，保持 Markdown 源稿可直接追溯和继续编辑。
        list_formula_lines.append("$$")

        # 再写入当前公式块正文，保持数学表达与本地材料一致。
        list_formula_lines.extend(str_formula_block.splitlines())

        # 最后闭合当前公式块，并补空行分隔后续内容。
        list_formula_lines.extend(["$$", ""])

    # 返回整理后的公式块 Markdown 行列表，供正文 4.2.2 小节直接拼接。
    return list_formula_lines

# 把待确认事项整理成内部审查 sidecar 可直接拼接的行列表；为空时补一条受控默认提醒。
def build_missing_information_lines(
    list_missing_information: list[str],
    module_runtime_support: Any,
) -> list[str]:
    """构建待确认事项 Markdown 行列表。

    参数：
    - `list_missing_information`：上游主案结果中的待确认事项列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[str]`：内部审查待确认事项可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备待确认事项 Markdown 行列表，后续按上游条目依次追加。
    list_missing_lines: list[str] = []  # 待确认事项 Markdown 行列表

    # 逐条清洗待确认事项文本，只保留真正可写入 sidecar 的条目。
    for str_item in list_missing_information:

        # 把当前待确认事项清洗成单行文本，便于统一判断可用性。
        str_missing_item = module_runtime_support.clean_text(str_item)  # 当前待确认事项文本

        # 在当前待确认事项存在有效文本时再生成 Markdown 条目。
        if str_missing_item:

            # 把当前待确认事项追加为 Markdown 列表项，供内部审查 sidecar 写入。
            list_missing_lines.append(f"- {str_missing_item}")

    # 在上游已经给出待确认事项时直接返回当前条目列表。
    if list_missing_lines:

        # 返回上游待确认事项列表，保持内部审查工作项真实可追溯。
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
            "## 三、现有技术（背景技术）",
            "",
            "### 3.1相关技术背景以及最接近的现有技术",
            "",
            f"围绕 {str_terms} 的工程场景，现有方案往往依赖固定规则或单指标决策，难以同时兼顾状态变化、异常反馈和处理效率。",
            "",
            "### 3.2与本发明最相似的现有技术实现方案",
            "",
            str_prior_summary,
            "",
            "### 3.3现有技术的缺点",
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
    list_formula_lines: list[str],
    list_module_lines: list[str],
    list_effect_lines: list[str],
) -> list[str]:
    """构建发明内容章节。

    参数：
    - `str_problem`：主案问题文本。
    - `list_step_lines`：方法步骤 Markdown 行列表。
    - `list_formula_lines`：公式块 Markdown 行列表。
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
            "## 四、发明内容：",
            "",
            "### 4.1 发明目的",
            "",
            f"本发明旨在针对“{str_problem}”所对应的处理缺口，形成可执行、可复核、可迭代的技术方案。",
            "",
            "### 4.2 技术解决方案",
            "",
            "#### 4.2.1 装置、结构类",
            "",
        ]
    )

    # 拼接系统/装置方案模块条目，对齐模板中 4.2.1 装置结构小节。
    list_section_lines.extend(list_module_lines)

    # 拼接方法方案小节标题与步骤条目。
    list_section_lines.extend(
        [
            "#### 4.2.2 方法类",
            "",
        ]
    )

    # 追加方法步骤说明块，保持每一步都带条件、输入、动作和输出。
    list_section_lines.extend(list_step_lines)

    # 在存在本地可追溯公式块时，把它们追加到方法小节尾部供正式源稿保留公式表达。
    if list_formula_lines:

        # 先补一个空行，再把公式说明与公式块写入当前技术方案小节。
        list_section_lines.extend(["", *list_formula_lines])

    # 在系统方案小节与技术效果小节之间补一个空行。
    list_section_lines.append("")

    # 拼接技术效果小节标题与编号条目。
    list_section_lines.extend(
        [
            "### 4.3、技术效果",
            "",
        ]
    )

    # 追加技术效果编号条目，供正文渲染阶段直接拼接。
    list_section_lines.extend(list_effect_lines)

    # 返回发明内容章节行列表，供正文渲染阶段统一拼接。
    return list_section_lines

# 构建附图说明与具体实施方式章节，内部审查材料另写 sidecar。
def build_tail_section() -> list[str]:
    """构建正文尾部章节。

    参数：
    - 无。

    返回：
    - `list[str]`：正文尾部章节的 Markdown 行列表。

    异常：
    - 无。
    """

    # 先准备正文尾部章节 Markdown 行列表，只保留可提交代理的主交底书章节。
    list_section_lines: list[str] = []  # 正文尾部章节 Markdown 行列表

    # 写入附图说明与具体实施方式章节骨架。
    list_section_lines.extend(
        [
            "",
            "## 五、附图及附图的简单说明",
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
        ]
    )

    # 在正文尾部补一个空行，保持导出器读取结尾时的版式稳定。
    list_section_lines.append("")

    # 返回正文尾部章节行列表，供正文渲染阶段统一拼接。
    return list_section_lines

# 渲染内部审查 sidecar，承接术语、证据和待确认事项。
def render_internal_review_markdown(
    str_case_name: str,
    list_terms: list[str],
    list_missing_lines: list[str],
) -> str:
    """渲染内部审查 Markdown 文本。

    参数：
    - `str_case_name`：当前案件名称文本。
    - `list_terms`：聚合后的技术术语列表。
    - `list_missing_lines`：待确认事项 Markdown 行列表。

    返回：
    - `str`：内部审查 sidecar Markdown 文本。

    异常：
    - 无。
    """

    # 先准备内部审查 sidecar 标题和来源说明。
    list_lines = [  # 内部审查 Markdown 行列表
        "# 内部审查材料",  # 固定 sidecar 标题
        "",  # 标题后的 Markdown 空行
        f"- case: {str_case_name}",  # 记录案件名而非本地路径
        "- note: 本文件不属于提交给代理的主交底书正文。",  # 明确提交边界
        "",  # 来源说明和术语小节分隔
        "## 术语说明",  # 内部术语审查入口
        "",  # 术语小节标题后的空行
    ]

    # 逐条写入术语说明列表，保持术语说明与上游术语聚合结果同步。
    for str_term in list_terms[:12]:

        # 追加当前术语条目，便于审阅人快速对齐正文里的关键名词。
        list_lines.append(f"- {str_term}")

    # 追加来源证据摘要说明，提示审阅人回看结构化证据映射。
    list_lines.extend(
        [
            "",
            "## 来源证据摘要",
            "",
            "正式技术特征应回溯到 `latest_evidence_map.json` 中的来源编号；缺少来源支撑的内容不得作为定稿必要技术特征。",
            "",
            "## 待确认事项",
            "",
        ]
    )

    # 追加待确认事项列表，提醒正式提交前仍需人工补齐的内容。
    list_lines.extend(list_missing_lines)

    # 在文件尾部补空行，保持 Markdown 结尾稳定。
    list_lines.append("")

    # 返回完整内部审查文本，供草稿阶段落盘。
    return "\n".join(list_lines)

# 渲染正式中文交底书草稿，统一拼接标题、背景、方案和效果。
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

    # 读取技术术语列表，供背景技术小节复用。
    list_terms = dict_render_payload["list_terms"]  # 聚合后的技术术语列表

    # 从渲染载荷读取步骤主链，供 4.2.2 小节展开输入处理输出关系。
    list_steps = dict_render_payload["list_steps"]  # 方法章节步骤主链

    # 读取系统模块列表，供 4.2.1 小节生成模块化方案说明。
    list_modules = dict_render_payload["list_modules"]  # 结构化系统模块列表

    # 提取技术效果条目列表，供技术效果小节生成编号说明。
    list_effects = dict_render_payload["list_effects"]  # 4.3 小节的效果原始条目列表

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

    # 生成 4.2.2 小节的步骤说明行列表，供正文渲染阶段直接插入。
    list_step_lines = build_step_markdown_lines(list_steps)  # 4.2.2 小节步骤说明行列表

    # 生成 4.2.2 小节末尾的公式说明与公式块，保留本地材料中的原始数学表达。
    list_formula_lines = dict_render_payload["list_formula_lines"]  # 4.2.2 小节公式块行列表

    # 生成 4.2.1 小节的系统模块行列表，供正文渲染阶段直接插入。
    list_module_lines = build_module_markdown_lines(list_modules)  # 4.2.1 小节系统模块行列表

    # 生成 4.3 小节的技术效果行列表，供正文渲染阶段直接插入。
    list_effect_lines = build_effect_markdown_lines(list_effects)  # 4.3 小节技术效果行列表

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
            list_formula_lines,
            list_module_lines,
            list_effect_lines,
        )
    )

    # 最后拼接正文尾部章节，只保留附图说明和具体实施方式。
    list_markdown_lines.extend(build_tail_section())

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

# 统一写入正文、内部审查和合同工件，缩小命令行入口职责。
def write_generated_documents(
    path_case_dir: Path,
    dict_document_context: dict[str, Any],
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> Path:
    """写入正式草稿、内部审查、快照和起草合同工件。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `dict_document_context`：正文、标题、步骤和审查内容组成的写入上下文。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `module_quality_contract`：正文质量合同模块对象。

    返回：
    - `Path`：稳定主草稿路径。

    异常：
    - 目录创建或文件写入失败时由底层异常上抛。
    """

    # 确保草稿输出目录存在，供稳定草稿、审查 sidecar 和快照共同落盘。
    path_output_dir = module_runtime_support.ensure_dir(path_case_dir / "03_drafts")  # 草稿输出目录路径

    # 固定稳定主草稿与内部审查路径，供后续链路按约定名称读取。
    path_stable_draft = path_output_dir / "disclosure_draft.md"  # 稳定主草稿路径

    # 内部审查材料采用独立 sidecar，避免进入代理人提交正文。
    path_internal_review = path_output_dir / "disclosure_internal_review.md"  # 内部审查 sidecar 路径

    # 由案件名和当前时间生成安全快照路径，保留本轮生成历史。
    str_snapshot_name = module_runtime_support.sanitize_name(dict_document_context["case_name"])  # 快照文件名前缀

    # 生成不含路径非法字符的紧凑时间片段。
    str_snapshot_timestamp = module_runtime_support.iso_now().replace(":", "").replace("-", "")  # 快照时间片段

    # 使用案件名前缀和时间片段生成唯一正文快照路径。
    path_snapshot_draft = path_output_dir / f"{str_snapshot_name}_{str_snapshot_timestamp}.md"  # 正文快照路径

    # 在正式落盘前为确定性参数更新式补充行内公式标记，确保 DOCX 导出时进入可编辑公式链。
    str_marked_markdown = module_quality_contract.mark_inline_math_expressions(dict_document_context["markdown"])  # 已结构化标记的正文

    # 写入代理人正文、内部审查 sidecar 和时间快照，保持内部材料不进入主文档。
    module_runtime_support.write_text_file(path_stable_draft, str_marked_markdown)

    # 单独写入内部审查材料，供人工复核证据和待确认项。
    module_runtime_support.write_text_file(path_internal_review, dict_document_context["internal_review"])

    # 保存本轮正文快照，便于后续核对确认前后的内容哈希。
    module_runtime_support.write_text_file(path_snapshot_draft, str_marked_markdown)

    # 将正文相关字段收敛为起草合同上下文，避免写入函数暴露过多独立参数。
    dict_artifact_context = {  # 起草合同写入上下文
        "title": dict_document_context["title"],  # 合同中的发明名称
        "steps": dict_document_context["steps"],  # 合同中的方法步骤
        "modules": dict_document_context["modules"],  # 合同中的装置模块
        "effects": dict_document_context["effects"],  # 合同中的技术效果
    }

    # 写入起草计划、模板槽位正文和预览哈希，锁定确认后的生成边界。
    write_draft_contract_artifacts(
        path_output_dir,
        str_marked_markdown,
        dict_artifact_context,
        module_runtime_support,
        module_quality_contract,
    )

    # 返回稳定主草稿路径，供命令行入口输出给上游流水线。
    return path_stable_draft

# 执行正式草稿生成入口，读取主案结果并输出交底书草稿与证据映射。
# 汇总版本二模型所需的既有正文事实。
def build_structured_model_payload(
    dict_render_payload: dict[str, Any],
    dict_selected: dict[str, Any],
    list_formula_blocks: list[str],
) -> dict[str, Any]:
    """从正文渲染上下文构建结构化模型输入。

    参数：
    - `dict_render_payload`：当前正文渲染上下文。
    - `dict_selected`：当前主案事实。
    - `list_formula_blocks`：正文实际展示公式。

    返回：
    - `dict[str, Any]`：公式、主案和章节事实组成的模型输入。

    异常：
    - 无。
    """

    # 只重组已经进入正文生成链的事实，不在此边界新增技术内容。
    return {
        "formula_blocks": list_formula_blocks,  # 正文展示公式
        "selected": dict_selected,  # 证据映射使用的主案事实
        "context": {  # 章节与证据映射共享的起草事实
            "title": dict_render_payload["str_title"],  # 已规范化发明名称
            "problem": dict_render_payload["str_problem"],  # 已确认主技术问题
            "steps": dict_render_payload["list_steps"],  # 结构化方法步骤
            "modules": dict_render_payload["list_modules"],  # 结构化装置模块
            "effects": dict_render_payload["list_effects"],  # 已分类技术效果
            "prior_summaries": dict_render_payload["list_prior_summaries"],  # 已核验现有技术摘要
        },
    }

# 构建并写出版本二结构化交底模型。
def write_structured_disclosure_model(
    path_case_dir: Path,
    dict_model_payload: dict[str, Any],
    module_runtime_support: Any,
    module_disclosure_model: Any,
    module_quality_contract: Any,
) -> None:
    """把正文上下文、公式事实和证据映射写成版本二模型。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `dict_model_payload`：公式块、证据映射和章节上下文。
    - `module_runtime_support`：共享 JSON 写入模块。
    - `module_disclosure_model`：版本二模型构建模块。
    - `module_quality_contract`：证据映射使用的正文质量合同模块。

    返回：
    - `None`。

    异常：
    - 公式事实或章节合同损坏时由模型模块异常上抛。
    """

    # 先写出最新证据映射，使旧版消费者和版本二模型共享同一来源编号。
    dict_evidence_map = build_evidence_map(  # 正文与结构化模型共享的来源映射
        path_case_dir,  # 当前案件根目录
        dict_model_payload["context"]["steps"],  # 已生成的方法步骤
        dict_model_payload["selected"],  # 当前主案事实
        dict_model_payload["context"]["prior_summaries"],  # 背景章节使用的查新摘要
        module_runtime_support,  # JSON 与文本支持模块
        module_quality_contract,  # 精确步骤证据映射规则
    )

    # 从研究根目录读取人工确认公式事实；缺失语义不会在生成阶段被猜测。
    list_confirmed_formula_facts = module_disclosure_model.load_confirmed_formula_facts(path_case_dir)  # 人工确认公式事实

    # 逐条匹配正文展示公式，未匹配记录将在后续语义验证中形成 blocker。
    list_formula_records = module_disclosure_model.match_formula_records(  # 与正文公式一一对应的登记表
        dict_model_payload["formula_blocks"],  # 正文实际使用的展示公式
        list_confirmed_formula_facts,  # 本地材料提供的确认语义
    )

    # 按正式章节合同生成十一项叶子章节。
    list_section_records = module_disclosure_model.build_section_records(  # 十一项章节记录
        dict_model_payload["context"],  # 标题、问题、步骤、模块和效果
        dict_evidence_map,  # 当前案件真实来源映射
    )

    # 将旧版 evidence_index 映射为验证器消费的 records，同时保留兼容字段。
    dict_normalized_evidence_map = module_disclosure_model.normalize_evidence_map(  # 版本二证据映射
        dict_evidence_map  # 旧版 evidence_index 来源对象
    )

    # 组合章节、公式与证据三个事实域，并为公式添加稳定内容哈希。
    dict_disclosure_model = module_disclosure_model.build_disclosure_model(  # 完整结构化交底模型
        list_section_records,  # 十一项章节事实
        list_formula_records,  # 与正文展示公式一致的语义登记
        dict_normalized_evidence_map,  # 含版本二 records 的来源映射
    )

    # 固定写入验证器约定路径，使当前案件无法绕过版本二跨对象门禁。
    module_runtime_support.write_json_file(
        path_case_dir / "03_drafts" / "disclosure_model.json",
        dict_disclosure_model,
    )

# 执行正式正文生成入口。
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

    # 加载正文质量合同，统一约束术语、效果、证据映射与受控推断边界。
    module_quality_contract = load_quality_contract_module()  # 正文质量合同模块

    # 加载版本二模型构建器，使正式生成链同步产出章节、公式和证据真相层。
    module_disclosure_model = load_disclosure_model_module()  # 结构化交底模型模块

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
    list_raw_terms = module_runtime_support.collect_terms(dict_selected, dict_facts)  # 背景与术语说明候选结果

    # 过滤公式 token、通用英文标记和完整句子，避免它们误作为正式技术术语。
    list_terms = module_quality_contract.filter_technical_terms(list_raw_terms)  # 去噪后的技术术语列表

    # 基于主案方案和术语列表生成方法步骤骨架，作为正文主链的核心结构。
    list_steps = build_method_steps(  # 4.2.2 方法流程结构化步骤
        dict_selected,  # 当前主案选择结果
        list_terms,  # 步骤构造使用的去噪术语
        module_runtime_support,  # 步骤文本清洗与默认值工具
        module_quality_contract,  # 步骤证据与术语约束规则
    )

    # 把方法步骤归并成系统模块骨架，供装置方案与附图说明复用同一术语。
    list_modules = build_modules(list_steps)  # 4.2.1 装置方案模块清单

    # 生成 4.3 小节的技术效果条目列表，保持效果表述与真实材料一致。
    list_effects = build_effect_lines(  # 4.3 小节效果编号条目
        dict_selected,  # 效果分类所依据的主案数据
        module_runtime_support,  # 共享文本清洗工具
        module_quality_contract,  # 技术效果证据分类规则
    )

    # 从本地研究材料中提取可追溯公式块，供正式交付源稿保留公式表达。
    list_formula_blocks = collect_formula_blocks_from_research_root(path_case_dir, module_runtime_support)  # 本地研究材料公式块列表

    # 把去重公式块展开成正文插入片段，供 4.2.2 方法小节直接拼接。
    list_formula_lines = build_formula_markdown_lines(list_formula_blocks)  # 正文方法小节公式片段

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

    # 再登记正文主体章节依赖列表，确保方法、模块、公式与效果能按章节直接渲染。
    dict_render_payload.update(
        {
            "list_problem_lines": list_problem_lines,  # 3.3 小节问题条目列表
            "list_steps": list_steps,  # 4.2.2 方法步骤列表
            "list_formula_lines": list_formula_lines,  # 4.2.2 方法小节公式片段
            "list_modules": list_modules,  # 4.2.1 模块条目列表
            "list_effects": list_effects,  # 4.3 小节效果条目列表
        }
    )

    # 最后登记辅助渲染字段，供背景、导出和内部审查 sidecar 统一读取。
    dict_render_payload.update(
        {
            "list_terms": list_terms,  # 背景与术语说明词表
            "list_prior_summaries": list_prior_summaries,  # 3.2 小节现有技术摘要
            "list_missing_information": list_missing_information,  # 内部审查待确认事项列表
        }
    )

    # 先把正文渲染字段转换为结构化模型写入上下文。
    dict_model_payload = build_structured_model_payload(dict_render_payload, dict_selected, list_formula_blocks)  # 结构化模型输入

    # 将已确认正文事实落为版本二模型，供当前验证链执行跨对象闭包。
    write_structured_disclosure_model(
        path_case_dir,  # 结构化模型所属案件根目录
        dict_model_payload,  # 已汇总的正文、主案和公式事实
        module_runtime_support,
        module_disclosure_model,
        module_quality_contract,
    )

    # 渲染完整正式中文交底书 Markdown 文本。
    str_markdown = render_markdown(dict_render_payload, module_runtime_support)  # 完整正式中文交底书 Markdown 文本

    # 把待确认事项预格式化成内部审查条目，避免其进入主交底书正文。
    list_missing_lines = build_missing_information_lines(list_missing_information, module_runtime_support)  # 内部审查待确认事项条目

    # 渲染内部审查 sidecar，承接术语、证据摘要和待确认事项。
    str_internal_review_markdown = render_internal_review_markdown(  # 内部审查 Markdown 文本
        str_case_name,  # 当前案件展示名称
        list_terms,  # 从材料和主案聚合的术语列表
        list_missing_lines,  # 已整理成 Markdown 条目的待确认事项
    )

    # 汇总文件写入所需字段，避免主入口继续承担路径与快照装配细节。
    dict_document_context = {  # 正式草稿文件写入上下文
        "case_name": str_case_name,  # 当前案件名称
        "title": str_title,  # 合同工件使用的正式标题
        "markdown": str_markdown,  # 代理人审阅正文 Markdown
        "internal_review": str_internal_review_markdown,  # 内部审查 sidecar 内容
        "steps": list_steps,  # 方法步骤合同内容
        "modules": list_modules,  # 装置模块合同内容
        "effects": list_effects,  # 技术效果合同内容
    }

    # 将 Markdown、内部审查文本与合同数据交给统一文件写入边界。
    path_stable_draft = write_generated_documents(  # 上游流水线读取的 Markdown 入口
        path_case_dir,  # 最终草稿所属案件目录
        dict_document_context,  # 正文与合同文件写入上下文
        module_runtime_support,  # 文件系统与 JSON 写入工具
        module_quality_contract,  # 起草合同与推断边界规则
    )

    # 把稳定主草稿绝对路径写回标准输出，供上游流水线与测试稳定解析。
    sys.stdout.write(str(path_stable_draft.resolve()) + "\n")

    # 返回成功退出码，表示当前正式正文与证据映射都已落盘。
    return 0

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())
