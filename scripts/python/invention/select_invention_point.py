#!/usr/bin/env python3
"""从事实摘要中选出当前主专利点。"""
from __future__ import annotations

# 这里引入标准库参数、序列化和路径工具，供主案选择入口完成本地读写与规则整理。
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 这里收敛主案保护焦点常见特征词，供必要技术特征提炼阶段复用。
KEY_FEATURE_HINTS = tuple(  # 主案保护焦点提示词
    """
    负载状态
    网络延迟
    任务优先级
    匹配分数
    阈值条件
    反馈队列
    设备权重
    CPU 占用率
    队列长度
    响应延迟
    失败状态
    重试次数
    """.split()
)

# 这里定义可选特征兜底列表，避免主案保护焦点出现空壳结果。
DEFAULT_OPTIONAL_FEATURES = ["异常处理", "反馈优化", "阈值调整", "部署方式"]  # 主案可选特征兜底列表

# 这里解析命令行参数，锁定本次主案选择要处理的案件目录。
def parse_arguments() -> argparse.Namespace:
    """
    解析主案选择入口参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含案件目录的参数对象。

    异常：
    - 参数缺失时由 `argparse` 自动结束进程。
    """

    # 这里构造命令行解析器，说明本脚本负责从事实摘要中选择主案。
    obj_parser = argparse.ArgumentParser(description="Select a primary invention point from governed facts.")  # 主案选择命令行解析器

    # 这里要求调用方提供案件目录，保证输入输出都绑定到当前正式案件。
    obj_parser.add_argument("--case-dir", required=True, help="Case directory containing research facts.")  # 案件目录参数

    # 这里返回解析后的参数对象，供主流程继续读取 facts 输入。
    return obj_parser.parse_args()

# 这里确保结果目录存在，供 JSON 和 Markdown 报告稳定落盘。
def ensure_dir(path_dir: Path) -> Path:
    """
    创建目录并返回目录路径。

    参数：
    - `path_dir`：需要确保存在的目录路径。

    返回：
    - `Path`：已经确认存在的目录路径。

    异常：
    - 底层目录创建失败时由文件系统异常上抛。
    """

    # 这里递归创建目标目录，允许调用方直接传入多级路径。
    path_dir.mkdir(parents=True, exist_ok=True)  # 已确保存在的目录路径

    # 这里返回目录对象，方便主流程继续拼接结果文件路径。
    return path_dir

# 这里统一读取 UTF-8 JSON 文件，减少主案选择入口的重复文件处理逻辑。
def read_json_file(path_file: Path) -> Any:
    """
    读取 UTF-8 JSON 文件。

    参数：
    - `path_file`：待读取的 JSON 文件路径。

    返回：
    - `Any`：反序列化后的 Python 数据结构。

    异常：
    - 文件不存在、编码错误或 JSON 语法错误时由底层异常上抛。
    """

    # 这里读取原始 JSON 文本，供统一反序列化处理。
    str_json_text = path_file.read_text(encoding="utf-8")  # JSON 原始文本

    # 这里返回解析结果，供主流程继续读取候选点列表。
    return json.loads(str_json_text)

# 这里统一写入 UTF-8 文本文件，保证 Markdown 报告落盘前自动创建父目录。
def write_text_file(path_file: Path, str_text: str) -> None:
    """
    写入 UTF-8 文本文件。

    参数：
    - `path_file`：目标文本文件路径。
    - `str_text`：待写入的文本内容。

    返回：
    - `None`。

    异常：
    - 底层目录创建或文件写入失败时由文件系统异常上抛。
    """

    # 这里先确保父目录存在，避免调用方在写报告前手动建目录。
    path_parent_dir = ensure_dir(path_file.parent)  # 目标文件父目录

    # 这里把文本内容按 UTF-8 写入目标文件，保证中文审阅材料直接可读。
    (path_parent_dir / path_file.name).write_text(str_text, encoding="utf-8")  # 已写入的目标文本文件

# 这里统一写入可读 JSON 文件，保证主案结果具备稳定缩进和中文直出格式。
def write_json_file(path_file: Path, data: Any) -> None:
    """
    写入 UTF-8 JSON 文件。

    参数：
    - `path_file`：目标 JSON 文件路径。
    - `data`：可被 `json.dumps` 序列化的数据。

    返回：
    - `None`。

    异常：
    - 底层序列化或文件写入失败时由相关异常上抛。
    """

    # 这里先把结构化结果序列化成带缩进的可读 JSON 文本。
    str_json_text = json.dumps(data, ensure_ascii=False, indent=2)  # 可读 JSON 文本

    # 这里复用统一文本写入入口，把 JSON 文本写到目标文件。
    write_text_file(path_file, str_json_text)

# 这里从 evidence 列表里取出首条可用文本，供问题、方案和效果做稳定补缺。
def first_evidence_text(list_evidence: list[dict[str, Any]], str_fallback: str) -> str:
    """
    返回 evidence 列表中的首条可用文本。

    参数：
    - `list_evidence`：evidence 字典列表。
    - `str_fallback`：没有可用文本时返回的兜底值。

    返回：
    - `str`：首条可用 evidence 文本或兜底文本。

    异常：
    - 无。
    """

    # 这里逐条扫描 evidence 文本，优先返回第一条真正有内容的句子。
    for dict_item in list_evidence:

        # 这里读取当前 evidence 文本，供是否可作为补缺内容判断。
        str_text_value = str(dict_item.get("text", "")).strip()  # 当前 evidence 文本

        # 这里在命中可用文本时立即返回，保持问题和方案补缺稳定可解释。
        if str_text_value:

            # 这里直接返回当前可用句子，避免继续扫描后面的低优先级证据。
            return str_text_value

    # 这里在 evidence 中没有可用文本时返回兜底值，保持输出协议稳定。
    return str_fallback

# 这里按当前候选点文本提炼保护焦点，避免后续预览阶段只拿到空壳主案。
def choose_focus_features(str_solution_text: str, list_terms: list[str]) -> tuple[list[str], list[str]]:
    """
    提炼必要技术特征和可选技术特征。

    参数：
    - `str_solution_text`：候选点技术方案文本。
    - `list_terms`：候选点技术术语列表。

    返回：
    - `tuple[list[str], list[str]]`：必要技术特征列表和可选技术特征列表。

    异常：
    - 无。
    """

    # 这里初始化必要技术特征列表，优先放入更适合独立权利要求的特征。
    list_focus_features: list[str] = []  # 必要技术特征列表

    # 这里初始化可选技术特征列表，供后续从属方向和预览材料使用。
    list_optional_features: list[str] = []  # 可选技术特征列表

    # 这里逐个检查必要特征提示词，命中时把它们加入保护焦点。
    for str_keyword in KEY_FEATURE_HINTS:

        # 这里在方案正文或术语表命中特征时收下该必要技术特征。
        if str_keyword in str_solution_text or str_keyword in list_terms:

            # 这里把当前命中的必要特征加入保护焦点列表。
            list_focus_features.append(str_keyword)

    # 这里在必要特征仍为空时回退到术语列表，保证保护焦点不会完全缺失。
    if not list_focus_features:

        # 这里用术语表或占位项兜底，避免保护焦点结果完全缺失。
        list_focus_features = list_terms[:6] or ["[待确认：必要技术特征]"]  # 兜底必要技术特征列表

    # 这里在术语较多时把剩余术语视作可选特征，便于后续从属方向继续展开。
    if len(list_terms) > len(list_focus_features):

        # 这里把必要特征之后的术语切片用作可选技术特征。
        list_optional_features = list_terms[len(list_focus_features) : len(list_focus_features) + 4]  # 基于术语切片的可选技术特征列表

    # 这里在可选特征仍为空时补一组稳定兜底项，方便后续预览继续展开。
    if not list_optional_features:

        # 这里补入常见展开方向，保证预览材料里总有可继续细化的附加特征。
        list_optional_features = list(DEFAULT_OPTIONAL_FEATURES)  # 兜底可选技术特征列表

    # 这里返回两组保护焦点结果，供主案 JSON 和 Markdown 同步使用。
    return list_focus_features[:10], list_optional_features[:10]

# 这里读取候选点中的各类 evidence 列表，供文本补缺与评分逻辑统一复用。
def read_candidate_evidence(dict_candidate: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """
    提取候选点中的 evidence 列表。

    参数：
    - `dict_candidate`：原始候选专利点字典。

    返回：
    - `dict[str, list[dict[str, Any]]]`：按 evidence 类型整理后的字典。

    异常：
    - 无。
    """

    # 这里组装各类 evidence 列表，避免后续函数重复读取同一批键名。
    dict_evidence = {
        "problem": list(dict_candidate.get("technical_problem_evidence", [])),  # 问题 evidence 列表
        "solution": list(dict_candidate.get("technical_solution_evidence", [])),  # 方案 evidence 列表
        "effect": list(dict_candidate.get("technical_effect_evidence", [])),  # 效果 evidence 列表
        "prior_art": list(dict_candidate.get("prior_art_evidence", [])),  # 现有技术 evidence 列表
    }  # 候选点 evidence 汇总字典

    # 这里返回 evidence 汇总结果，供文本补缺和评分逻辑共享使用。
    return dict_evidence

# 这里补齐候选点的标题、问题、方案、效果与术语，保证后续评分逻辑只面对稳定字段。
def normalize_candidate_fields(
    dict_candidate: dict[str, Any],
    dict_evidence: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """
    补齐候选点中的核心文本字段。

    参数：
    - `dict_candidate`：原始候选专利点字典。
    - `dict_evidence`：按 evidence 类型整理后的字典。

    返回：
    - `dict[str, Any]`：补齐后的标题、问题、方案、效果与术语。

    异常：
    - 无。
    """

    # 这里读取候选点名称，缺失时退化为待确认占位标题。
    str_name = str(dict_candidate.get("name") or "[待确认：主专利点]")  # 候选点名称

    # 这里优先保留已有问题字段，没有时再回退到问题 evidence。
    str_problem = str(dict_candidate.get("problem") or "")  # 原始技术问题文本

    # 这里在问题字段为空时补入首条问题 evidence，保证输出始终可读。
    if not str_problem:

        # 这里把问题 evidence 转成问题摘要，避免主案只剩占位标题。
        str_problem = first_evidence_text(dict_evidence["problem"], "[待确认：技术问题]")  # 补齐后的技术问题文本

    # 这里优先保留已有方案字段，没有时再回退到方案 evidence。
    str_solution = str(dict_candidate.get("solution") or "")  # 原始技术方案文本

    # 这里在方案字段为空时补入首条方案 evidence，保证方案摘要不缺位。
    if not str_solution:

        # 这里把方案 evidence 转成方案摘要，维持后续保护焦点提炼输入。
        str_solution = first_evidence_text(dict_evidence["solution"], "[待确认：技术方案]")  # 补齐后的技术方案文本

    # 这里读取效果列表，让已有结构化效果优先覆盖 evidence 补缺逻辑。
    list_effects = list(dict_candidate.get("effects") or [])  # 原始技术效果列表

    # 这里在效果列表为空时回退到效果 evidence，保证效果段仍有可审阅内容。
    if not list_effects:

        # 这里把效果 evidence 压成单条效果句，避免输出缺少效果信息。
        list_effects = [first_evidence_text(dict_evidence["effect"], "[待确认：技术效果]")]  # 补齐后的技术效果列表

    # 这里读取技术术语列表，供保护焦点与后续从属方向提炼使用。
    list_terms = list(dict_candidate.get("technical_terms") or [])  # 技术术语列表

    # 这里返回补齐后的核心字段，供评分和结果组装共享使用。
    return {
        "name": str_name,  # 主案候选标题
        "problem": str_problem,  # 稳定可读的问题摘要
        "solution": str_solution,  # 稳定可读的方案摘要
        "effects": list_effects,  # 稳定可读的效果列表
        "technical_terms": list_terms,  # 用于保护焦点提炼的术语列表
    }

# 这里按主案选择标准计算分数、加分理由与风险提示，避免主函数堆叠判断分支。
def score_candidate_fields(
    dict_fields: dict[str, Any],
    dict_evidence: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """
    计算候选点的分数、理由与风险。

    参数：
    - `dict_fields`：补齐后的候选点核心字段。
    - `dict_evidence`：按 evidence 类型整理后的字典。

    返回：
    - `dict[str, Any]`：包含分数、加分理由与风险提示的结果字典。

    异常：
    - 无。
    """

    # 这里初始化主案基础分数，后续按内容完整度逐层累加。
    int_score = 1  # 当前候选点基础分数

    # 这里初始化加分理由列表，供人工理解主案为何被选中。
    list_reasons: list[str] = []  # 主案加分理由列表

    # 这里初始化风险列表，供预览确认阶段集中提示人工关注点。
    list_risks: list[str] = []  # 主案风险提示列表

    # 这里读取补齐后的问题摘要，准备判断问题信息是否已经明确。
    str_problem = str(dict_fields["problem"])  # 用于评分的问题摘要

    # 这里在问题不是占位文本时增加问题侧分数，否则登记待确认风险。
    if "待确认" not in str_problem:

        # 这里给问题表达明确的候选点增加问题侧分数。
        int_score += 2  # 技术问题明确时的加分值

        # 这里记录问题侧加分原因，方便人工理解得分来源。
        list_reasons.append("技术问题已有明确表达。")

    # 这里在问题仍待确认时登记风险，提醒预览阶段优先补足问题定义。
    else:

        # 这里记录问题侧缺口，提醒后续预览优先补问题定义。
        list_risks.append("技术问题仍需人工确认。")

    # 这里读取补齐后的方案摘要，准备判断方案信息是否已经明确。
    str_solution = str(dict_fields["solution"])  # 用于评分的方案摘要

    # 这里在方案不是占位文本时增加方案侧分数，否则登记待确认风险。
    if "待确认" not in str_solution:

        # 这里给方案表达明确的候选点增加方案侧分数。
        int_score += 3  # 技术方案明确时的加分值

        # 这里记录方案侧加分原因，表示该主案可继续展开成稿。
        list_reasons.append("技术方案可继续展开成稿。")

    # 这里在方案仍待补充时登记风险，提醒后续预览继续补关键步骤。
    else:

        # 这里记录方案侧缺口，提醒后续预览继续补关键步骤。
        list_risks.append("技术方案仍需进一步补充。")

    # 这里读取补齐后的效果列表，准备判断效果信息是否已经明确。
    list_effects = list(dict_fields["effects"])  # 用于评分的效果列表

    # 这里在效果不是占位文本时增加效果侧分数，否则登记待确认风险。
    if all("待确认" not in str_effect for str_effect in list_effects):

        # 这里给效果表达明确的候选点增加效果侧分数。
        int_score += 2  # 技术效果明确时的加分值

        # 这里记录效果侧加分原因，说明效果已经具备可复述材料。
        list_reasons.append("技术效果已有可复述表达。")

    # 这里在效果仍待确认时登记风险，提醒后续补实验数据或效果描述。
    else:

        # 这里记录效果侧缺口，提醒后续补实验数据或效果描述。
        list_risks.append("技术效果仍需进一步补充。")

    # 这里在问题、方案、效果 evidence 同时存在时增加一层完整度加分。
    if dict_evidence["problem"] and dict_evidence["solution"] and dict_evidence["effect"]:

        # 这里给 evidence 基本闭合的候选点增加稳定性分数。
        int_score += 2  # evidence 三段闭合时的加分值

        # 这里记录完整度理由，说明该主案具备更稳的事实支撑。
        list_reasons.append("问题、方案、效果 evidence 基本闭合。")

    # 这里在存在现有技术线索时增加查新准备度分数，否则登记补充风险。
    if dict_evidence["prior_art"]:

        # 这里给带现有技术线索的候选点增加查新准备度分数。
        int_score += 1  # 现有技术线索存在时的加分值

        # 这里记录查新准备度理由，说明后续检索起点更明确。
        list_reasons.append("已有现有技术或 baseline 线索。")

    # 这里在缺少 baseline 线索时登记风险，提醒后续补现有技术或对比材料。
    else:

        # 这里记录 baseline 缺口，提醒后续补现有技术或对比材料。
        list_risks.append("现有技术或 baseline 线索仍需补充。")

    # 这里返回评分结果包，供主案结果组装直接复用。
    return {
        "score": int_score,  # 排序使用的最终分数
        "score_reasons": list_reasons,  # 展示给人工的加分理由
        "risks": list_risks,  # 预览阶段需要关注的风险
    }

# 这里把必要技术特征扩展成保护焦点摘要，供预览与成稿入口继续复用。
def build_protection_strategy(
    list_focus_features: list[str],
    list_optional_features: list[str],
) -> dict[str, Any]:
    """
    生成主案的保护焦点摘要。

    参数：
    - `list_focus_features`：必要技术特征列表。
    - `list_optional_features`：可选技术特征列表。

    返回：
    - `dict[str, Any]`：包含独立权利要求焦点、从属方向与保护类型的字典。

    异常：
    - 无。
    """

    # 这里初始化从属保护方向列表，后续按必要特征逐个扩展。
    list_dependent_directions: list[str] = []  # 从属保护方向列表

    # 这里逐个遍历必要技术特征，为它们生成可继续细化的从属方向。
    for str_feature in list_focus_features[:6]:

        # 这里把必要特征扩展成一个可继续写从属项的方向句。
        list_dependent_directions.append(f"限定 {str_feature} 的采集、计算或更新方式。")

    # 这里组装保护焦点摘要，供主案 JSON 与 Markdown 同步引用。
    return {
        "independent_claim_focus": list_focus_features,  # 独立权利要求的必要特征
        "optional_features": list_optional_features,  # 适合从属项展开的附加特征
        "dependent_claim_directions": list_dependent_directions,  # 从属保护延展方向
        "protection_types": ["方法", "系统", "电子设备", "计算机可读存储介质"],  # 推荐保护类型
    }

# 这里生成一个稳定的占位候选点，保证 facts 阶段没有候选时输出协议仍然完整。
def build_placeholder_candidate() -> dict[str, Any]:
    """
    构造待确认占位主案。

    参数：
    - 无。

    返回：
    - `dict[str, Any]`：经过统一整理后的占位主案结果。

    异常：
    - 无。
    """

    # 这里组装最小占位候选点，确保后续统一复用主案整理逻辑。
    dict_placeholder = {
        "name": "[待确认：主专利点]",  # 占位主案标题
        "problem": "[待确认：技术问题]",  # 占位技术问题
        "solution": "[待确认：技术方案]",  # 占位技术方案
        "effects": ["[待确认：技术效果]"],  # 占位技术效果列表
        "source_paths": [],  # 暂无来源材料路径
        "technical_terms": [],  # 暂无可复用术语
    }  # 占位候选点原始字典

    # 这里复用统一候选点整理逻辑，保证占位结果与正常输出结构一致。
    return build_selected_candidate(dict_placeholder)

# 这里把单个候选点整理成可排序的主案记录，避免后续主流程堆积分支逻辑。
def build_selected_candidate(dict_candidate: dict[str, Any]) -> dict[str, Any]:
    """
    整理单个候选点的主案摘要、评分和保护焦点。

    参数：
    - `dict_candidate`：原始候选专利点字典。

    返回：
    - `dict[str, Any]`：补齐评分、保护焦点和风险后的候选点字典。

    异常：
    - 无。
    """

    # 这里先读取候选点中的 evidence 列表，供文本补缺与评分逻辑共享使用。
    dict_evidence = read_candidate_evidence(dict_candidate)  # 候选点 evidence 汇总

    # 这里补齐候选点核心字段，确保后续评分与渲染只处理稳定结构。
    dict_fields = normalize_candidate_fields(dict_candidate, dict_evidence)  # 补齐后的候选点核心字段

    # 这里按方案摘要和术语提炼保护焦点，避免主案只停留在标题层。
    tuple_focus_result = choose_focus_features(dict_fields["solution"], dict_fields["technical_terms"])  # 主案保护焦点结果

    # 这里取出独立项应当优先保护的特征集合，供后续保护焦点摘要直接复用。
    list_focus_features = tuple_focus_result[0]  # 独立项优先保护的特征集合

    # 这里取出更适合从属项扩展的附加特征，供预览阶段继续展开。
    list_optional_features = tuple_focus_result[1]  # 从属项可延展的附加特征

    # 这里计算分数、理由和风险，保持主函数只负责结果编排。
    dict_scoring = score_candidate_fields(dict_fields, dict_evidence)  # 候选点评分结果

    # 这里构造保护焦点摘要，供 JSON 输出和 Markdown 报告共享引用。
    dict_protection_strategy = build_protection_strategy(list_focus_features, list_optional_features)  # 保护焦点摘要

    # 这里读取来源材料路径，供后续人工回看事实来源时定位原始文档。
    list_source_paths = list(dict_candidate.get("source_paths") or [])  # 来源材料路径列表

    # 这里读取原始置信度标签，供后续预览或排序解释时补充上下文。
    str_confidence = str(dict_candidate.get("confidence", "medium"))  # 原始置信度标签

    # 这里返回可直接排序和落盘的候选点结果，供主流程统一选择主案。
    return {
        "name": dict_fields["name"],  # 供人工识别的候选标题
        "problem": dict_fields["problem"],  # 预览中直接展示的问题摘要
        "solution": dict_fields["solution"],  # 后续正文继续展开的方案主干
        "effects": dict_fields["effects"],  # 可写入说明书效果段的效果列表
        "source_paths": list_source_paths,  # 回溯原始材料时使用的路径
        "confidence": str_confidence,  # 候选点沿用的置信度标签
        "technical_terms": dict_fields["technical_terms"][:12],  # 保留给审阅的核心术语
        "technical_problem_evidence": dict_evidence["problem"],  # 问题事实对应的 evidence
        "technical_solution_evidence": dict_evidence["solution"],  # 方案事实对应的 evidence
        "technical_effect_evidence": dict_evidence["effect"],  # 效果事实对应的 evidence
        "prior_art_evidence": dict_evidence["prior_art"],  # 查新准备阶段可复用的线索
        "protection_strategy": dict_protection_strategy,  # 独立项与从属项的保护焦点摘要
        "recommended_protection_types": dict_protection_strategy["protection_types"],  # 建议保护客体类型
        "score": dict_scoring["score"],  # 候选点最终排序分数
        "score_reasons": dict_scoring["score_reasons"],  # 主案得分的文字解释
        "risks": dict_scoring["risks"],  # 预览确认前需要关注的缺口
    }

# 这里把主案选择结果渲染成 Markdown 报告，方便人工快速审阅主案与备选案。
def render_markdown(dict_output: dict[str, Any]) -> str:
    """
    生成主案选择 Markdown 报告文本。

    参数：
    - `dict_output`：最终主案选择结果包。

    返回：
    - `str`：最终写入文件的 Markdown 报告文本。

    异常：
    - 无。
    """

    # 这里读取当前主案记录，供报告各小节统一引用主案内容。
    dict_selected = dict_output["selected"]  # 当前主案记录

    # 这里读取主案保护焦点摘要，供报告中的保护特征小节使用。
    dict_strategy = dict_selected["protection_strategy"]  # 当前主案保护焦点摘要

    # 这里初始化 Markdown 行列表，先写案件摘要和主案核心结论。
    list_lines = [
        "# Selected Invention Point",  # 报告标题
        "",  # 标题与案件信息之间留空
        f"Case: {dict_output['case_name']}",  # 案件名称行
        "",  # 案件信息与主案章节之间留空
        "## 主案",  # 主案章节标题
        "",  # 章节标题后留空
        f"- 名称：{dict_selected['name']}",  # 主案名称
        f"- 分数：{dict_selected['score']}",  # 主案分数
        f"- 技术问题：{dict_selected['problem']}",  # 主案问题摘要
        f"- 核心方案：{dict_selected['solution']}",  # 主案方案摘要
        "- 技术效果：",  # 技术效果列表标题
    ]  # Markdown 开场内容

    # 这里逐条写入技术效果，保留主案的多条效果描述。
    list_lines.extend([f"  - {str_effect}" for str_effect in dict_selected["effects"]])

    # 这里继续写入保护焦点、保护类型和风险摘要，方便人工做预览确认。
    list_lines.extend(
        [
            "- 必要技术特征：" + "、".join(dict_strategy["independent_claim_focus"]),
            "- 可选/从属特征：" + "、".join(dict_strategy["optional_features"]),
            "- 推荐保护类型：" + "、".join(dict_selected["recommended_protection_types"]),
            "- 风险：",
        ]
    )

    # 这里逐条写入风险项，没有风险时给出一个稳定兜底项。
    list_lines.extend([f"  - {str_risk}" for str_risk in dict_selected["risks"]] or ["  - 暂无"])

    # 这里进入备选案小节，保留少量备选候选点供人工比较。
    list_lines.extend(["", "## 备选案"])

    # 这里逐个展开备选案摘要，帮助人工在需要时快速切换主案。
    for int_index, dict_candidate in enumerate(dict_output.get("alternatives", []), start=1):

        # 这里把当前备选案摘要加入 Markdown，保留名称、分数和方案主干。
        list_lines.extend(
            [
                "",  # 与上一备选案之间留空
                f"### {int_index}. {dict_candidate['name']}",  # 备选案小标题
                f"- 分数：{dict_candidate['score']}",  # 备选案分数
                f"- 问题：{dict_candidate['problem']}",  # 备选案问题摘要
                f"- 方案：{dict_candidate['solution']}",  # 备选案方案摘要
            ]
        )

    # 这里进入待确认小节，保留 facts 阶段尚未补齐的信息提示。
    list_lines.extend(["", "## 待确认"])

    # 这里逐条写入待补信息，方便人工在预览前集中补足缺口。
    list_lines.extend([f"- {str_item}" for str_item in dict_output["missing_information"]])

    # 这里返回最终 Markdown 文本，供主流程统一写入案件目录。
    return "\n".join(list_lines)

# 这里执行主案选择主流程，并把 Markdown 报告路径写到标准输出末尾。
def main() -> int:
    """
    执行主案选择主流程。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 缺少 facts 输入文件或结果写入失败时由底层异常上抛。
    """

    # 这里解析命令行参数，锁定当前主案选择要处理的案件目录。
    namespace_arguments = parse_arguments()  # 主案选择入口参数

    # 这里解析案件目录绝对路径，保证输入读取和结果落盘都指向同一案件空间。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 案件根目录

    # 这里固定 facts JSON 路径，指向主案选择唯一接受的事实摘要输入文件。
    path_facts_json = path_case_dir / "02_facts" / "research_facts.json"  # 主案选择读取的 facts JSON 文件

    # 这里在缺少 facts 输入时立即报错，避免主案选择在无输入场景下伪造成功。
    if not path_facts_json.exists():

        # 这里抛出明确错误，提醒调用方先完成事实抽取步骤。
        raise FileNotFoundError("> ERR: [Python] 缺少 research_facts.json，请先完成事实抽取")

    # 这里读取 facts 数据字典，作为当前主案排序和渲染的唯一输入。
    dict_facts = read_json_file(path_facts_json)  # facts 数据字典

    # 这里读取原始候选点列表，供后续逐个整理并计算主案得分。
    list_candidates_raw = list(dict_facts.get("candidate_invention_points", []))  # 原始候选点列表

    # 这里初始化已评分候选点列表，后续只保留适合排序和落盘的结构。
    list_scored_candidates: list[dict[str, Any]] = []  # 已评分候选点列表

    # 这里逐个整理候选点，并把评分后的结果加入排序列表。
    for dict_candidate in list_candidates_raw:

        # 这里把当前候选点整理成可排序的主案记录。
        dict_scored_candidate = build_selected_candidate(dict_candidate)  # 当前已评分候选点

        # 这里把当前已评分候选点加入排序列表，供后续选出主案。
        list_scored_candidates.append(dict_scored_candidate)

    # 这里在没有候选点时主动补一个待确认主案，保证输出协议保持稳定。
    if not list_scored_candidates:

        # 这里补入占位主案，让后续预览阶段仍有可审阅的结构。
        dict_placeholder_candidate = build_placeholder_candidate()  # 待确认占位主案

        # 这里把占位主案加入排序列表，保证输出结构完整。
        list_scored_candidates.append(dict_placeholder_candidate)

    # 这里按分数倒序排序，让得分最高的候选点稳定成为当前主案。
    list_scored_candidates.sort(key=lambda dict_item: dict_item["score"], reverse=True)

    # 这里选出当前分数最高的主案，供后续 JSON 和 Markdown 同步引用。
    dict_selected = list_scored_candidates[0]  # 当前选中的主案

    # 这里切出保留给人工比较的备选案列表，避免报告中塞入全部候选点。
    list_alternatives = list_scored_candidates[1:8]  # 备选候选点列表

    # 这里读取仍待补齐的信息列表，供主案报告末尾集中提示。
    list_missing_information = list(dict_facts.get("missing_information", []))  # 待补信息列表

    # 这里准备案件名称，优先沿用 facts 中已有名称，没有时回退到目录名。
    str_case_name = str(dict_facts.get("case_name", path_case_dir.name))  # 案件名称文本

    # 这里组装最终输出结果包，供 JSON 落盘和 Markdown 渲染共同复用。
    dict_output = {
        "case_name": str_case_name,  # 报告首页展示的案件名称
        "selected": dict_selected,  # 已选主案记录
        "alternatives": list_alternatives,  # 保留给人工比较的备选案
        "all_candidates": list_scored_candidates,  # 完整评分后的候选点列表
        "missing_information": list_missing_information,  # 预览前仍需补齐的信息
    }  # 主案选择结果包

    # 这里固定输出目录和结果文件路径，保持主案选择结果落在 facts 阶段目录中。
    path_output_dir = ensure_dir(path_case_dir / "02_facts")  # 主案选择输出目录

    # 这里固定结构化结果文件位置，供后续预览和流水线入口继续读取。
    path_output_json = path_output_dir / "selected_invention_point.json"  # 结构化主案结果文件

    # 这里固定人工审阅报告位置，供预览确认前快速查看主案与备选案。
    path_output_markdown = path_output_dir / "selected_invention_point.md"  # 人工审阅用 Markdown 报告

    # 这里把主案选择结果写成 JSON 文件，作为后续步骤的稳定机器输入。
    write_json_file(path_output_json, dict_output)

    # 这里渲染主案选择 Markdown 文本，供人工快速确认主案与备选案。
    str_markdown = render_markdown(dict_output)  # 主案选择 Markdown 文本

    # 这里把主案选择 Markdown 报告写入案件目录，方便人工继续确认。
    write_text_file(path_output_markdown, str_markdown)

    # 这里把 Markdown 报告路径作为机器可读输出写给上游流程。
    sys.stdout.write(str(path_output_markdown.resolve()) + "\n")

    # 这里返回成功状态码，表示主案选择已经完成并写入案件目录。
    return 0

# 这里保留标准脚本入口，方便命令行和流水线子进程统一调用主案选择入口。
if __name__ == "__main__":

    # 这里通过标准退出路径返回状态码，保持命令行调用行为一致。
    raise SystemExit(main())
