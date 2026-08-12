#!/usr/bin/env python3
"""提取研究材料中的结构化证据与来源术语。"""
from __future__ import annotations

# 这里引入标准库参数、时间、序列化和路径工具，供 facts 入口完成本地事实汇总与落盘。
import argparse
import hashlib
import importlib.util
import json

# 正则、进程、时间和路径工具负责文本抽取及本地入口运行。
import re
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

# 这里引入拆分后的报告辅助函数，让主文件只保留事实抽取和聚合流程。
from facts_report_support import build_missing_information
from facts_report_support import render_markdown

# 固定事实完整性模块路径，使数值候选与最终数据门禁同源。
PATH_FACT_INTEGRITY_CONTRACT = Path(__file__).resolve().parents[1] / "support" / "fact_integrity_contract.py"  # 事实合同模块路径

# 这里集中列出术语统计阶段要主动忽略的泛化词，避免候选专利点被空泛词主导。
STOP_TERMS = frozenset(  # 高频术语统计停用词集合
    """
    一种
    方法
    系统
    模块
    数据
    技术
    方案
    处理
    进行
    当前
    以及
    the
    and
    for
    with
    from
    """.split()
)

# 问题类标题关键词集合。
PROBLEM_HEADING_KEYWORDS = frozenset(  # 技术问题标题关键词集合
    """
    背景问题
    技术问题
    不足
    缺陷
    挑战
    痛点
    problem
    limitation
    challenge
    """.split()
)

# 方案类标题关键词集合。
SOLUTION_HEADING_KEYWORDS = frozenset(  # 技术方案标题关键词集合
    """
    技术方案
    解决方案
    发明内容
    具体实施
    实施方式
    方法
    系统
    算法
    architecture
    method
    solution
    """.split()
)

# 效果类标题关键词集合。
EFFECT_HEADING_KEYWORDS = frozenset(  # 技术效果标题关键词集合
    """
    技术效果
    有益效果
    实验结果
    测试结果
    性能
    评估
    effect
    result
    experiment
    benchmark
    """.split()
)

# 现有技术类标题关键词集合。
PRIOR_ART_HEADING_KEYWORDS = frozenset(  # 现有技术标题关键词集合
    """
    现有技术
    背景技术
    相关技术
    基线
    对比
    prior
    related
    baseline
    """.split()
)

# 问题句匹配词组集合。
PROBLEM_PATTERNS = """
问题
缺陷
瓶颈
挑战
不足
痛点
导致
忽略
不能
难以
problem
challenge
limitation
""".split()  # 技术问题匹配模式列表

# 方案句匹配词组集合。
SOLUTION_PATTERNS = """
提出
方案
方法
系统
模块
算法
架构
流程
采集
计算
分配
反馈
method
system
algorithm
architecture
""".split()  # 技术方案匹配模式列表

# 效果句匹配词组集合。
EFFECT_PATTERNS = r"""
提升
降低
减少
提高
改善
优化
准确率
延迟
吞吐
效率
\d+\s*%
\d+\s*ms
\d+\s*次
improve
reduce
increase
""".split()  # 技术效果匹配模式列表

# 现有技术句匹配词组集合。
PRIOR_ART_PATTERNS = """
现有技术
背景技术
baseline
基线
固定轮询
prior art
related work
对比
论文
专利
""".split()  # 现有技术匹配模式列表

# 从基础模块复用规范化、分句与术语统计能力。
from readable_patent_facts_io import keyword_counter
from readable_patent_facts_io import normalize_text
from readable_patent_facts_io import split_sentences

# 这里把 Markdown 风格预览拆成按标题组织的章节片段，便于按章节抓取问题、方案和效果句子。
def parse_markdown_sections(str_preview: str) -> list[dict[str, str]]:
    """
    把 Markdown 风格预览拆成章节列表。

    参数：
    - `str_preview`：材料盘点阶段生成的正文预览文本。

    返回：
    - `list[dict[str, str]]`：每项包含标题和正文内容的章节列表。

    异常：
    - 无。
    """

    # 这里初始化章节结果列表，按预览中出现顺序保存章节片段。
    list_sections: list[dict[str, str]] = []  # 章节片段结果列表

    # 这里初始化当前章节标题，未命中标题时默认归入全文章节。
    str_current_title = "全文"  # 当前章节标题

    # 这里初始化当前章节正文缓冲区，逐行收集当前标题下的文本。
    list_buffer: list[str] = []  # 当前章节正文缓冲列表

    # 这里定义内部刷新函数，把当前缓冲区写入章节结果列表。
    def flush_section() -> None:
        """
        把当前标题和正文缓冲区写入章节结果列表。

        参数：
        - 无外部业务参数。

        返回：
        - 无业务返回值；结果直接写入外层章节列表。

        异常：
        - 无。
        """

        # 这里声明要回写的外层状态，确保内部刷新逻辑直接更新当前章节上下文。
        nonlocal str_current_title, list_buffer

        # 这里把当前缓冲区拼接成章节正文文本，供空章节过滤和结果写入使用。
        str_content = "\n".join(list_buffer).strip()  # 当前章节正文文本

        # 这里在存在正文或标题已不再是默认值时登记当前章节结果。
        if str_content or str_current_title != "全文":

            # 这里把当前标题与正文写入章节列表，供后续按章节类型抽取证据句。
            list_sections.append({"title": str_current_title, "content": str_content})

        # 这里清空正文缓冲区，为下一个章节重新开始收集文本。
        list_buffer = []  # 已清空的章节正文缓冲列表

    # 这里逐行扫描预览文本，按 Markdown 标题切出新的章节片段。
    for str_raw_line in str_preview.splitlines():

        # 这里去掉首尾空白，便于统一判断当前行是否为章节标题。
        str_line = str_raw_line.strip()  # 去空白后的当前行文本

        # 这里在命中 Markdown 标题行时先落当前章节，再切换到新标题。
        if str_line.startswith("#"):

            # 这里先把当前章节写入结果，避免标题切换时丢掉上一段正文。
            flush_section()

            # 这里把当前标题更新为清洗后的 Markdown 标题文本。
            str_current_title = str_line.lstrip("#").strip() or "全文"  # 新的当前章节标题

            # 这里继续处理下一行，避免标题文本进入正文缓冲区。
            continue

        # 这里把非标题行加入当前章节正文缓冲区，等待后续统一写入。
        list_buffer.append(str_raw_line)

    # 这里把最后一个章节缓冲区写入结果，确保末尾正文不会丢失。
    flush_section()

    # 这里在完全没切出章节时补一个全文章节，保证调用方总能拿到正文片段。
    if not list_sections:

        # 这里把整段预览视作全文章节，维持下游逻辑的统一输入形态。
        list_sections.append({"title": "全文", "content": str_preview})

    # 这里返回章节结果列表，供问题、方案和效果句抽取逻辑继续使用。
    return list_sections

# 这里判断标题是否命中某组关键词，供章节选择逻辑复用。
def heading_matches(str_title: str, set_keywords: frozenset[str]) -> bool:
    """
    判断章节标题是否命中指定关键词集合。

    参数：
    - `str_title`：待判断的章节标题文本。
    - `set_keywords`：用于匹配的标题关键词集合。

    返回：
    - `bool`：命中任一关键词时返回 `True`。

    异常：
    - 无。
    """

    # 这里统一把标题转成小写，便于兼容中英文关键词的宽松匹配。
    str_title_lower = str_title.lower()  # 小写化后的标题文本

    # 这里判断标题是否包含任一目标关键词，供章节过滤使用。
    return any(str_keyword.lower() in str_title_lower for str_keyword in set_keywords)

# 这里把文本和来源信息组织成证据项，便于 JSON 和 Markdown 同步使用统一结构。
def evidence_item(
    str_text: str,
    str_path: str,
    str_section: str,
    str_kind: str,
    str_confidence: str,
) -> dict[str, str]:
    """
    构造单条事实证据项。

    参数：
    - `str_text`：证据文本。
    - `str_path`：证据来源路径。
    - `str_section`：证据来源章节名。
    - `str_kind`：证据种类标识。
    - `str_confidence`：证据置信度文本。

    返回：
    - `dict[str, str]`：包含证据文本、路径、章节、类型和置信度的字典。

    异常：
    - 无。
    """

    # 这里返回统一证据结构，供 source 记录和 candidate point 共同复用。
    return {
        "text": normalize_text(str_text),
        "path": str_path,
        "section": str_section,
        "kind": str_kind,
        "confidence": str_confidence,
    }

# 这里从句子列表中挑出命中模式的证据句，并按需要优先保留含指标的效果句。
def pick_matching_sentences(
    list_sentences: list[str],
    list_patterns: list[str],
    int_limit: int,
    bool_prefer_metrics: bool = False,
) -> list[str]:
    """
    从句子列表里挑选命中模式的候选证据句。

    参数：
    - `list_sentences`：候选句子列表。
    - `list_patterns`：需要匹配的正则模式列表。
    - `int_limit`：最多保留的候选句子数量。
    - `bool_prefer_metrics`：是否优先保留包含数值指标的句子。

    返回：
    - `list[str]`：去重后的候选证据句列表。

    异常：
    - 无。
    """

    # 这里把模式列表编译成联合正则，便于一次判断句子是否命中目标类型。
    pattern_sentence_matcher: re.Pattern[str] = re.compile("|".join(list_patterns), re.I)  # 候选句匹配正则

    # 这里收集命中模式的句子，作为后续排序和去重的原始候选集合。
    list_matches = [str_sentence for str_sentence in list_sentences if pattern_sentence_matcher.search(str_sentence)]  # 原始命中句子列表

    # 这里在效果句抽取场景下优先保留带数值指标的句子，增强技术效果的可审阅性。
    if bool_prefer_metrics:

        # 这里准备指标句正则，后续只保留量化句。
        str_metric_pattern = r"\d+(?:\.\d+)?\s*(?:%|ms|秒|次|台|条|倍)"  # 指标句判定正则

        # 这里准备指标句列表，只收带量化信息的候选句。
        list_metric_matches = []  # 指标句列表

        # 这里遍历候选句，优先收下带量化信息的句子。
        for str_sentence in list_matches:

            # 这里跳过非指标句，把优先名额留给量化表达。
            if not re.search(str_metric_pattern, str_sentence):

                # 这里继续检查下一句，避免把普通句误收进指标集合。
                continue

            # 这里登记当前指标句，供后续优先排序。
            list_metric_matches.append(str_sentence)

        # 这里把定量效果句放在前面，再补上其他命中句子。
        set_metric_matches = set(list_metric_matches)  # 指标句集合

        # 这里准备普通句列表，补收未被指标优先的候选句。
        list_remaining_matches = []  # 普通候选句列表

        # 这里补收未被指标优先命中的句子，避免普通有效句被直接丢掉。
        for str_sentence in list_matches:

            # 这里跳过已归入指标集合的句子，避免后面合并时重复保留。
            if str_sentence in set_metric_matches:

                # 这里继续检查下一句，只把普通候选句补进剩余列表。
                continue

            # 这里登记当前普通句，保证指标优先后仍保留其他候选。
            list_remaining_matches.append(str_sentence)

        # 这里合并指标句和普通句，形成最终的优先排序结果。
        list_matches = list_metric_matches + list_remaining_matches  # 指标优先后的命中句子列表

    # 这里初始化去重后的候选句列表，供后续按顺序保留首个有效句子。
    list_unique_matches: list[str] = []  # 去重后的候选句列表

    # 这里初始化已见集合，按规整文本去重，避免同一句在不同空白形态下重复出现。
    set_seen_sentences: set[str] = set()  # 已见候选句键集合

    # 这里逐句保留首个有效命中句，保证候选证据句不重复。
    for str_sentence in list_matches:

        # 这里把当前句子规整成去重键，减少空白和标点差异对去重的影响。
        str_sentence_key = normalize_text(str_sentence).lower()  # 当前句子的去重键

        # 这里跳过空句或已见句，保证输出句子列表尽量紧凑。
        if not str_sentence_key or str_sentence_key in set_seen_sentences:

            # 这里忽略重复或空白句子，让证据列表只保留有效新句子。
            continue

        # 这里登记当前句子键，标记它已进入最终候选集合。
        set_seen_sentences.add(str_sentence_key)

        # 这里保留当前命中句，供后续构造 evidence 项和候选专利点描述。
        list_unique_matches.append(normalize_text(str_sentence))

        # 这里在达到数量上限时及时停止，控制单类证据的体量。
        if len(list_unique_matches) >= int_limit:

            # 这里结束候选句收集，避免单类证据句数量过多。
            break

    # 这里返回去重后的候选句列表，供 evidence 组装逻辑继续使用。
    return list_unique_matches

# 这里从章节和全文预览中提取指定类型的证据句，优先使用标题语义更明确的章节。
def collect_evidence_from_sections(
    list_sections: list[dict[str, str]],
    set_heading_keywords: frozenset[str],
    list_patterns: list[str],
    str_path: str, str_kind: str, int_limit: int,
    bool_prefer_metrics: bool = False,
) -> list[dict[str, str]]:
    """
    从章节列表中收集指定类型的证据项。

    参数：
    - `list_sections`：章节列表。
    - `set_heading_keywords`：目标章节标题关键词集合。
    - `list_patterns`：句子匹配模式列表。
    - `str_path`：来源材料相对路径。
    - `str_kind`：证据种类标识。
    - `int_limit`：最多保留的证据项数量。
    - `bool_prefer_metrics`：是否优先保留含数值指标的句子。

    返回：
    - `list[dict[str, str]]`：去重后的证据项列表。

    异常：
    - 无。
    """

    # 这里初始化证据项结果列表，后续按章节顺序保留命中的事实句。
    list_evidence: list[dict[str, str]] = []  # 证据项结果列表

    # 这里初始化已见集合，避免同一条事实句在多章节或回退抽取中重复出现。
    set_seen_texts: set[str] = set()  # 已见事实句键集合

    # 这里优先遍历命中目标标题关键词的章节，从语义更明确的位置抓取证据句。
    for dict_section in list_sections:

        # 这里读取当前章节标题，供标题语义筛选使用。
        str_section_title = str(dict_section.get("title", "全文"))  # 当前章节标题文本

        # 这里跳过不匹配目标标题关键词的章节，把重点放在更相关的段落上。
        if not heading_matches(str_section_title, set_heading_keywords):

            # 这里继续检查下一个章节，避免把无关段落过早纳入证据集合。
            continue

        # 这里把当前章节正文切成句子，供模式匹配和证据项构造复用。
        list_sentences = split_sentences(str(dict_section.get("content", "")))  # 当前章节句子列表

        # 这里按当前标题语义抽取候选句，优先保留和目标章节直接相关的事实表达。
        list_matches = pick_matching_sentences(list_sentences, list_patterns, int_limit, bool_prefer_metrics)  # 当前标题命中的证据句列表

        # 这里逐句写入 evidence 项，并按规整文本去重。
        for str_match in list_matches:

            # 这里把当前候选句规整成去重键，避免同一句跨章节重复入选。
            str_match_key = normalize_text(str_match).lower()  # 当前候选句去重键

            # 这里跳过已见句子，保持证据项列表尽量聚焦。
            if str_match_key in set_seen_texts:

                # 这里忽略重复句子，让证据项只保留第一次命中的上下文。
                continue

            # 这里登记当前句子键，标记它已进入最终证据集合。
            set_seen_texts.add(str_match_key)

            # 这里把当前句子连同路径和章节名写成统一 evidence 项。
            list_evidence.append(evidence_item(str_match, str_path, str_section_title, str_kind, "high"))

            # 这里在达到数量上限时及时停止，避免单类证据过多。
            if len(list_evidence) >= int_limit:

                # 这里直接返回当前证据结果，保持单类证据规模稳定。
                return list_evidence

    # 这里在分节抽取不足时回退到全文句子匹配，保证最小样例也能产出候选事实。
    if len(list_evidence) < int_limit:

        # 这里把全部章节正文拼回全文，供缺失类型做保守回退抽取。
        str_full_text = "\n".join(str(dict_section.get("content", "")) for dict_section in list_sections)  # 全文回退文本

        # 这里把全文切成句子，供回退匹配复用。
        list_full_sentences = split_sentences(str_full_text)  # 全文句子列表

        # 这里从全文补抓候选句，弥补标题筛选的遗漏。
        list_full_matches = pick_matching_sentences(list_full_sentences, list_patterns, int_limit, bool_prefer_metrics)  # 全文回退候选句

        # 这里逐个补充回退句，直到证据数量到上限。
        for str_match in list_full_matches:

            # 这里规整当前全文回退句，作为统一去重键。
            str_match_key = normalize_text(str_match).lower()  # 全文回退句去重键

            # 这里跳过已见句子，避免回退抽取和章节抽取重复。
            if str_match_key in set_seen_texts:

                # 这里忽略已见回退句，把名额留给新增事实句。
                continue

            # 这里登记当前回退句键，表明它已经进入 evidence 结果。
            set_seen_texts.add(str_match_key)

            # 这里把回退句写成低置信度 evidence，提示调用方这是全文保守抽取。
            list_evidence.append(evidence_item(str_match, str_path, "全文", str_kind, "medium"))

            # 这里在达到数量上限时及时停止，保持单类 evidence 规模可控。
            if len(list_evidence) >= int_limit:

                # 这里结束回退抽取，返回当前证据结果列表。
                break

    # 这里返回最终 evidence 列表，供 source 记录和 candidate point 汇总复用。
    return list_evidence

# 这里优先从标题列表中推断候选技术名称，便于生成更可读的候选专利点标题。
def infer_title_from_record(dict_record: dict[str, Any]) -> str:
    """
    从盘点记录中推断候选技术名称。

    参数：
    - `dict_record`：单条盘点记录字典。

    返回：
    - `str`：用于候选专利点的技术名称文本。

    异常：
    - 无。
    """

    # 这里先尝试使用首个标题，通常它最接近研究主题或发明名称。
    for str_heading in dict_record.get("headings", []):

        # 这里清洗示例前缀，只保留更接近正式发明名称的主体文本。
        str_cleaned_heading = normalize_text(re.sub(r"^(示例研究|研究|项目)\s*[：:]", "", str(str_heading)))  # 清洗后的标题文本

        # 这里在标题非空时直接返回，让候选专利点名称更贴近原材料表达。
        if str_cleaned_heading:

            # 这里返回首个有效标题，作为候选专利点名称优先值。
            return str_cleaned_heading

    # 这里在标题缺失时退回相对路径主文件名，至少保留一个稳定标识。
    str_path_text = str(dict_record.get("path", "source"))  # 当前记录的相对路径文本

    # 这里返回去后缀的文件名，作为标题缺失场景下的保底候选名。
    return Path(str_path_text).stem

# 这里解析 prior-art JSON 预览，供结构化对比线索抽取复用。
def parse_prior_art_preview(str_preview: str) -> dict[str, Any] | None:
    """
    解析 prior-art JSON 预览文本。

    参数：
    - `str_preview`：正文预览文本。

    返回：
    - `dict[str, Any] | None`：解析成功返回 JSON 对象，否则返回 `None`。

    异常：
    - 无。
    """

    # 这里仅对 JSON 风格预览执行解析。
    if not str_preview.strip().startswith("{"):

        # 这里对非 JSON 预览直接降级。
        return None

    # 这里尝试解析 JSON 对象。
    try:

        # 这里返回解析成功的结构化对象。
        return json.loads(str_preview)

    # 这里在 JSON 解析失败时退回空值。
    except json.JSONDecodeError:

        # 这里对截断预览安全降级。
        return None

# 组合单条 prior-art 记录的共同特征和区别特征摘要。
def build_prior_art_solution_summary(dict_item: dict[str, Any]) -> str:
    """从单条 prior-art 记录生成方案对比摘要。

    参数：
    - `dict_item`：单条结构化 prior-art 记录。

    返回：
    - `str`：共同特征与区别特征组成的方案摘要。
    """

    # 分别规整共同特征和区别特征，保持记录内原始顺序。
    list_same_features = [normalize_text(str(str_value)) for str_value in dict_item.get("same_features", [])]  # 共同特征列表

    # 区别特征单独规整，供摘要保持共同特征在前的稳定顺序。
    list_different_features = [normalize_text(str(str_value)) for str_value in dict_item.get("different_features", [])]  # 区别特征列表

    # 准备摘要片段，最多保留每类前三项特征。
    list_solution_fragments: list[str] = []  # 方案对比摘要片段

    # 存在共同特征时登记已公开部分。
    if list_same_features:

        # 保留前三项共同特征，避免单条 evidence 过长。
        list_solution_fragments.append(f"共同特征：{'、'.join(list_same_features[:3])}")

    # 存在区别特征时登记本案新增部分。
    if list_different_features:

        # 保留前三项区别特征，与共同特征使用相同数量边界。
        list_solution_fragments.append(f"区别特征：{'、'.join(list_different_features[:3])}")

    # 返回按共同、区别顺序拼接的稳定摘要。
    return "；".join(list_solution_fragments)

# 从单条结构化 prior-art 记录生成四类 evidence。
def extract_prior_art_record_evidence(
    dict_item: dict[str, Any],
    str_path: str,
) -> dict[str, list[dict[str, str]]]:
    """把一条 prior-art 记录转换为分类 evidence 映射。

    参数：
    - `dict_item`：单条结构化 prior-art 记录。
    - `str_path`：当前 source 的相对路径。

    返回：
    - `dict[str, list[dict[str, str]]]`：问题、方案、效果和现有技术 evidence 映射。
    """

    # 读取并规整当前记录的公开标识、问题、效果和方案摘要。
    str_publication = normalize_text(str(dict_item.get("publication_no_or_title", "")))  # 公开编号或标题

    # 实际技术问题用于构造问题类 evidence。
    str_problem = normalize_text(str(dict_item.get("actual_technical_problem", "")))  # 实际技术问题

    # 技术效果保持原记录语义，不从方案字段推断。
    str_effect = normalize_text(str(dict_item.get("technical_effect", "")))  # 技术效果

    # 方案摘要仅由共同特征和区别特征组成。
    str_solution = normalize_text(build_prior_art_solution_summary(dict_item))  # 特征对比方案摘要

    # 按字段是否存在构造至多一条的分类列表，保持旧版输出结构。
    return {
        "problem": (
            [evidence_item(str_problem, str_path, str_publication or "prior_art_record", "technical_problem", "medium")]
            if str_problem
            else []
        ),
        "solution": (
            [
                evidence_item(
                    str_solution,
                    str_path,
                    str_publication or "prior_art_record",
                    "technical_solution",
                    "medium",
                )
            ]
            if str_solution
            else []
        ),
        "effect": (
            [evidence_item(str_effect, str_path, str_publication or "prior_art_record", "technical_effect", "medium")]
            if str_effect
            else []
        ),
        "prior_art": (
            [evidence_item(str_publication, str_path, "prior_art_record", "prior_art_or_baseline", "high")]
            if str_publication
            else []
        ),
    }

# 这里把结构化 prior-art 预览抽成四类 evidence。
def extract_structured_prior_art_evidence(
    dict_prior_art_preview: dict[str, Any],
    str_path: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """
    从结构化 prior-art 预览中提取四类 evidence 列表。

    参数：
    - `dict_prior_art_preview`：已解析的 prior-art 预览对象。
    - `str_path`：当前 source 的相对路径。

    返回：
    - `tuple[...]`：按问题、方案、效果、现有技术顺序返回 evidence 列表。

    异常：
    - 无。
    """

    # 这里初始化问题 evidence 列表。
    list_problem_evidence: list[dict[str, str]] = []  # 结构化问题 evidence 列表

    # 这里初始化方案 evidence 列表。
    list_solution_evidence: list[dict[str, str]] = []  # 结构化方案 evidence 列表

    # 这里初始化效果 evidence 列表。
    list_effect_evidence: list[dict[str, str]] = []  # 结构化效果 evidence 列表

    # 这里初始化现有技术 evidence 列表。
    list_prior_art_evidence: list[dict[str, str]] = []  # 结构化现有技术 evidence 列表

    # 这里逐条遍历结构化 prior-art 记录。
    for dict_item in dict_prior_art_preview.get("records", []):

        # 把当前记录转换为四类列表，再按原记录顺序追加到总结果。
        dict_record_evidence = extract_prior_art_record_evidence(dict_item, str_path)  # 当前记录分类 evidence

        # 追加当前记录的问题证据，保持记录输入顺序。
        list_problem_evidence.extend(dict_record_evidence["problem"])

        # 追加当前记录的方案特征摘要。
        list_solution_evidence.extend(dict_record_evidence["solution"])

        # 追加当前记录明确声明的技术效果。
        list_effect_evidence.extend(dict_record_evidence["effect"])

        # 追加当前记录的公开编号或标题。
        list_prior_art_evidence.extend(dict_record_evidence["prior_art"])

    # 这里返回四类结构化 evidence。
    return (
        list_problem_evidence,
        list_solution_evidence,
        list_effect_evidence,
        list_prior_art_evidence,
    )

# 这里按 evidence 种类统一执行章节回退抽取。
def collect_source_evidence_by_kind(
    list_sections: list[dict[str, str]],
    str_path: str,
    str_kind: str,
) -> list[dict[str, str]]:
    """
    按 evidence 种类执行章节与全文回退抽取。

    参数：
    - `list_sections`：已解析的 Markdown 章节列表。
    - `str_path`：当前 source 的相对路径。
    - `str_kind`：evidence 种类标识。

    返回：
    - `list[dict[str, str]]`：按指定种类抽到的 evidence 列表。

    异常：
    - 无。
    """

    # 这里处理技术问题 evidence 回退。
    if str_kind == "technical_problem":

        # 这里返回问题类标题和句式命中的证据列表。
        return collect_evidence_from_sections(
            list_sections,
            PROBLEM_HEADING_KEYWORDS,
            PROBLEM_PATTERNS,
            str_path,
            str_kind,
            6,
        )

    # 这里处理技术方案 evidence 回退。
    if str_kind == "technical_solution":

        # 这里返回方案类标题和动作句式命中的证据列表。
        return collect_evidence_from_sections(
            list_sections,
            SOLUTION_HEADING_KEYWORDS,
            SOLUTION_PATTERNS,
            str_path,
            str_kind,
            8,
        )

    # 这里处理技术效果 evidence 回退。
    if str_kind == "technical_effect":

        # 这里返回效果类标题与量化收益命中的证据列表。
        return collect_evidence_from_sections(
            list_sections,
            EFFECT_HEADING_KEYWORDS,
            EFFECT_PATTERNS,
            str_path,
            str_kind, 5, bool_prefer_metrics=True,
        )

    # 这里把剩余种类都按 prior-art 线索回退。
    # 这里返回现有技术或基线线索命中的证据列表。
    return collect_evidence_from_sections(
        list_sections,
        PRIOR_ART_HEADING_KEYWORDS,
        PRIOR_ART_PATTERNS,
        str_path,
        str_kind,
        6,
    )

# 这里统一拼接术语统计输入。
def build_source_term_input(
    list_headings: list[str],
    list_problem_evidence: list[dict[str, str]],
    list_solution_evidence: list[dict[str, str]],
    list_effect_evidence: list[dict[str, str]],
    list_prior_art_evidence: list[dict[str, str]],
) -> str:
    """
    组装当前 source 的术语统计输入文本。

    参数：
    - `list_headings`：当前 source 的标题列表。
    - `list_problem_evidence`：问题 evidence 列表。
    - `list_solution_evidence`：方案 evidence 列表。
    - `list_effect_evidence`：效果 evidence 列表。
    - `list_prior_art_evidence`：现有技术 evidence 列表。

    返回：
    - `str`：供术语统计复用的文本。

    异常：
    - 无。
    """

    # 这里合并标题与四类 evidence 文本。
    return "\n".join(  # 术语统计输入文本
        list_headings
        + [obj_item["text"] for obj_item in list_problem_evidence]
        + [obj_item["text"] for obj_item in list_solution_evidence]
        + [obj_item["text"] for obj_item in list_effect_evidence]
        + [obj_item["text"] for obj_item in list_prior_art_evidence]
    )
