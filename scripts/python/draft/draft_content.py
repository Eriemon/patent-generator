"""构建交底书正文内容与结构化起草上下文。"""

# 延迟解析拆分后的类型注解，保持公共 helper 合同稳定。
from __future__ import annotations

# 标准库提供文件同步、路径与动态载荷类型。
import shutil
from pathlib import Path
from typing import Any

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

# 把已核验查新记录规整成正文可直接使用的现有技术摘要句列表。
def build_background_lines(
    list_prior_records: list[dict[str, Any]],
    module_runtime_support: Any,
) -> list[str]:
    """构建来源支持的技术背景段落。

    参数：
    - `list_prior_records`：已核验查新记录列表。
    - `module_runtime_support`：共享文本清洗与引用支持模块对象。

    返回：
    - `list[str]`：说明技术对象、机制和应用约束的背景段落列表。

    异常：
    - 无。
    """

    # 准备背景段落结果，按查新记录顺序保持引用编号稳定。
    list_background_lines: list[str] = []  # 3.1 小节背景技术段落

    # 逐条提取已公开技术机制和应用限制，禁止从术语列表推测背景事实。
    for int_citation_index, dict_record in enumerate(list_prior_records, start=1):

        # 准备当前来源的机制文本列表，只收录清洗后的非空特征。
        list_mechanism_parts: list[str] = []  # 当前来源公开的技术机制片段

        # 逐项清洗相同特征，防止空白值进入背景段落。
        for obj_feature in dict_record.get("same_features", []):

            # 将当前相同特征规整为可直接写入正文的单行文本。
            str_same_feature = module_runtime_support.clean_text(obj_feature)  # 当前机制特征文本

            # 只有可读的机制特征才进入最终串接结果。
            if str_same_feature:

                # 收录当前机制片段，保持原始查新记录中的排列顺序。
                list_mechanism_parts.append(str_same_feature)

        # 串接当前来源公开的相同特征，作为技术运行机制描述。
        str_mechanism = "、".join(list_mechanism_parts)  # 当前来源支持的技术机制

        # 准备当前来源的约束文本列表，只收录清洗后的非空差异。
        list_constraint_parts: list[str] = []  # 当前来源揭示的应用限制片段

        # 逐项清洗区别特征，保留其与原始记录一致的排列顺序。
        for obj_feature in dict_record.get("different_features", []):

            # 将当前区别特征规整为可直接写入背景段落的单行文本。
            str_different_feature = module_runtime_support.clean_text(obj_feature)  # 当前约束特征文本

            # 只有可读的约束特征才参与现有方案边界说明。
            if str_different_feature:

                # 收录当前约束片段，避免空内容破坏中文标点结构。
                list_constraint_parts.append(str_different_feature)

        # 串接当前来源的区别特征，作为现有方案的应用约束说明。
        str_constraint = "、".join(list_constraint_parts)  # 当前来源揭示的应用限制

        # 读取来源标识，帮助读者理解当前背景事实对应的技术对象。
        str_title = module_runtime_support.clean_text(dict_record.get("publication_no_or_title"))  # 当前来源标识

        # 形成包含技术对象、运行机制、约束和引用编号的完整背景段落。
        list_background_lines.append(
            f"{str_title} 所代表的现有方案以 {str_mechanism} 为主要技术机制；"
            f"其应用约束在于 {str_constraint}。[{int_citation_index}]"
        )

    # 返回按来源顺序组织的背景段落，供 3.1 小节直接渲染。
    return list_background_lines

# 生成最接近现有技术摘要，维持其与背景段落相同的来源编号。
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
    for int_citation_index, dict_record in enumerate(list_prior_records, start=1):

        # 把当前查新记录压缩成单句摘要，便于 3.2 小节直接复用。
        list_prior_summaries.append(
            module_runtime_support.summarize_prior_art(dict_record, int_citation_index)
        )

    # 返回现有技术摘要列表，供正文与证据映射阶段共同复用。
    return list_prior_summaries

# 根据已核验查新记录生成与正文引用顺序一致的参考文献列表。
def build_prior_references(
    list_prior_records: list[dict[str, Any]],
    module_runtime_support: Any,
) -> list[str]:
    """构建先技术参考文献列表。

    参数：
    - `list_prior_records`：已核验查新记录列表。
    - `module_runtime_support`：共享引用格式支持模块对象。

    返回：
    - `list[str]`：带稳定方括号序号的参考文献条目列表。

    异常：
    - 非专利记录绕过筛选且缺少著录文本时由支持模块抛出异常。
    """

    # 按正文使用顺序格式化参考文献，确保每个序号只对应一个来源。
    return [
        module_runtime_support.format_prior_art_reference(dict_record, int_citation_index)
        for int_citation_index, dict_record in enumerate(list_prior_records, start=1)
    ]

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
            "prior_records": dict_render_payload["list_prior_records"],  # 保留公开时序和用途的查新记录
        },
    }
