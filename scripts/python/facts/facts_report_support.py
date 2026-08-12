#!/usr/bin/env python3
"""facts 报告渲染辅助逻辑。"""
from __future__ import annotations

# 这里保留通用类型提示，方便辅助模块复用 facts 数据字典结构。
from typing import Any

# 这里根据当前 facts 结果补齐缺失信息提示，提醒后续人工确认关键专利信息。
def build_missing_information(
    list_candidate_points: list[dict[str, Any]],
    list_prior_art_notes: list[str],
) -> list[str]:
    """
    生成当前 facts 结果缺失信息提示列表。

    参数：
    - `list_candidate_points`：候选专利点列表。
    - `list_prior_art_notes`：prior-art 摘要说明列表。

    返回：
    - `list[str]`：仍需用户或后续步骤补充的信息提示列表。

    异常：
    - 无。
    """

    # 这里初始化缺失信息提示列表，后续按 facts 完整度逐项补充说明。
    list_missing_information: list[str] = []  # 缺失信息提示列表

    # 这里在没有任何候选专利点时提示先补充能表达方案的研究材料。
    if not list_candidate_points:

        # 这里记录候选点为空的核心原因，提醒后续优先补充可读技术材料。
        list_missing_information.append("尚未形成候选专利点，请补充能明确表达技术方案的研究材料。")

    # 这里在没有明确技术问题时提醒人工确认背景问题和现有技术缺口。
    if not any("待确认" not in dict_point.get("problem", "") for dict_point in list_candidate_points):

        # 这里提示技术问题仍需人工确认，避免后续权利要求缺少问题导向。
        list_missing_information.append("核心技术问题仍需人工确认。")

    # 这里在没有明确技术效果时提醒人工补充实验数据或定量改进结论。
    if not any(
        any("待确认" not in str_effect for str_effect in dict_point.get("effects", []))
        for dict_point in list_candidate_points
    ):

        # 这里提示技术效果证据不足，后续最好补充实验数据或性能对比。
        list_missing_information.append("技术效果或实验数据仍需补充。")

    # 这里在 prior-art 线索缺失时提醒后续补充查新或对比记录。
    if not list_prior_art_notes:

        # 这里提示还缺少已核验的现有技术线索，避免后续定稿时缺少对比依据。
        list_missing_information.append("尚未提炼出现有技术或查新对比线索。")

    # 这里总是提醒人工补全申请人和发明人等表单信息，保持事实摘要边界明确。
    list_missing_information.append("申请人、发明人和联系人等表单信息通常需要人工补充。")

    # 这里返回缺失信息提示列表，供 JSON 和 Markdown 同步展示后续待补事项。
    return list_missing_information

# 这里把 facts 数据渲染成 Markdown 报告，方便人工快速审阅候选专利点和来源摘要。
def render_markdown(dict_facts: dict[str, Any]) -> str:
    """
    生成 facts Markdown 报告文本。

    参数：
    - `dict_facts`：最终 facts 数据字典。

    返回：
    - `str`：最终写入文件的 Markdown 报告文本。

    异常：
    - 无。
    """

    # 这里初始化 Markdown 行列表，先写案件摘要和候选专利点主标题。
    list_lines = [  # facts Markdown 行列表
        "# Research Facts",  # 报告主标题
        "",  # 主标题后的空行
        f"Case: {dict_facts['case_name']}",  # 案件名称摘要
        "Research root: `[internal path redacted]`",  # 研究根目录红线摘要
        "",  # 摘要段后的空行
        "## Candidate invention points",  # 候选专利点小节标题
        "",  # 候选点标题后的空行
    ]

    # 这里逐个展开候选专利点，供人工快速审阅问题、方案、效果和来源路径。
    for int_index, dict_point in enumerate(dict_facts["candidate_invention_points"], start=1):

        # 这里写入当前候选点标题，把序号和名称一起展示到报告中。
        list_lines.append(f"### {int_index}. {dict_point['name']}")

        # 这里把当前候选点的关键摘要条目一次性写入报告。
        list_lines.extend(
            [
                f"- confidence: {dict_point['confidence']}",  # 当前候选点置信度
                f"- problem: {dict_point['problem']}",  # 当前候选点技术问题
                f"- solution: {dict_point['solution']}",  # 当前候选点技术方案
                f"- terms: {'、'.join(dict_point.get('technical_terms', [])[:12])}",  # 当前候选点技术术语摘要
                "- effects:",  # 技术效果条目标题
            ]
        )

        # 这里逐条写入技术效果，保留多条效果描述的可读展开形式。
        list_lines.extend([f"  - {str_effect}" for str_effect in dict_point["effects"]])

        # 这里继续写入来源路径小节标题，便于人工回看原始材料位置。
        list_lines.append("- sources:")

        # 这里逐条写入来源路径，保留候选点与材料来源之间的对应关系。
        list_lines.extend([f"  - `{str_path}`" for str_path in dict_point["source_paths"]])

        # 这里在当前候选点小节末尾补空行，保证 Markdown 阅读体验稳定。
        list_lines.append("")

    # 这里写入 prior-art 小节标题，集中展示查新和对比线索摘要。
    list_lines.append("## Prior-art / baseline hints")

    # 这里写入 prior-art 线索列表，没有时补一个待确认占位提示。
    list_lines.extend([f"- {str_note}" for str_note in dict_facts["prior_art_notes"]] or ["- [待确认] 尚未提炼 prior-art 线索"])

    # 这里补一个空行，分隔 prior-art 小节和技术术语小节。
    list_lines.append("")

    # 这里写入技术术语小节标题，方便人工快速浏览候选点中出现的高频技术词。
    list_lines.append("## Technical terms")

    # 这里逐条写入全局技术术语列表，保留前若干高价值术语用于审阅。
    list_lines.extend([f"- {str_term}" for str_term in dict_facts["technical_terms"][:30]])

    # 这里补一个空行，分隔技术术语小节和缺失信息小节。
    list_lines.append("")

    # 这里写入缺失信息小节标题，提示后续人工还需要补充的关键内容。
    list_lines.append("## Missing information")

    # 这里逐条写入缺失信息提示，明确 facts 摘要尚未覆盖的内容边界。
    list_lines.extend([f"- {str_item}" for str_item in dict_facts["missing_information"]])

    # 这里补一个空行，分隔缺失信息小节和 source 摘要小节。
    list_lines.append("")

    # 这里写入 source 摘要小节标题，供人工快速回看每份材料的事实提炼结果。
    list_lines.append("## Source summaries")

    # 这里逐个展开 source 摘要，帮助人工核对候选点和原材料之间的对应关系。
    for dict_source in dict_facts["sources"][:20]:

        # 这里写入当前 source 的小节标题，直接展示相对路径便于审阅定位。
        list_lines.append(f"### {dict_source['path']}")

        # 这里写入当前 source 摘要正文，保留对材料核心内容的压缩描述。
        list_lines.append(str(dict_source.get("summary", "")))

        # 这里在存在术语列表时写入术语摘要，便于人工快速感知材料技术主题。
        if dict_source.get("technical_terms"):

            # 这里写入当前 source 的技术术语摘要行。
            list_lines.append("- terms: " + "、".join(dict_source["technical_terms"][:10]))

        # 这里在每个 source 小节末尾补空行，保持 Markdown 布局整洁。
        list_lines.append("")

    # 这里返回最终 Markdown 文本，供主流程统一写入案件目录。
    return "\n".join(list_lines)
