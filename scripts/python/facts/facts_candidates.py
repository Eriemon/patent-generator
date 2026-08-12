#!/usr/bin/env python3
"""构造事实来源、候选专利点与人工审核工件。"""
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

# 从基础模块复用目录、序列化与文本统计能力。
from readable_patent_facts_io import ensure_dir
from readable_patent_facts_io import keyword_counter
from readable_patent_facts_io import normalize_text
from readable_patent_facts_io import split_sentences
from readable_patent_facts_io import write_json_file

# 从证据模块复用来源解析与结构化证据抽取能力。
from readable_patent_facts_evidence import build_source_term_input
from readable_patent_facts_evidence import collect_source_evidence_by_kind
from readable_patent_facts_evidence import extract_structured_prior_art_evidence
from readable_patent_facts_evidence import infer_title_from_record
from readable_patent_facts_evidence import parse_markdown_sections
from readable_patent_facts_evidence import parse_prior_art_preview

# 这里根据盘点记录构造统一的 source 事实记录。
def build_source_record(dict_record: dict[str, Any]) -> dict[str, Any]:
    """
    根据单条盘点记录构造统一的事实源记录。

    参数：
    - `dict_record`：单条盘点记录字典。

    返回：
    - `dict[str, Any]`：包含事实摘要、证据项和术语结果的 source 记录。

    异常：
    - 无。
    """

    # 这里读取当前记录相对路径。
    str_path = str(dict_record.get("path", "unknown"))  # 当前记录相对路径

    # 这里读取正文预览文本。
    str_preview = str(dict_record.get("preview", ""))  # 当前记录正文预览文本

    # 这里读取标题列表。
    list_headings = [str(str_heading) for str_heading in dict_record.get("headings", [])]  # 当前记录标题列表

    # 这里读取文件后缀。
    str_suffix = str(dict_record.get("suffix", "")).lower()  # 当前记录文件后缀

    # 这里把正文预览拆成章节列表。
    list_sections = parse_markdown_sections(str_preview)  # 当前记录章节列表

    # 这里优先解析 JSON 风格的 prior-art 预览。
    dict_prior_art_preview = parse_prior_art_preview(str_preview) if str_suffix == ".json" else None  # prior-art 结构化预览结果

    # 这里为问题线索预留起始 evidence 列表。
    list_problem_evidence: list[dict[str, str]] = []  # 技术问题 evidence 列表

    # 这里为方案描述预留起始 evidence 列表。
    list_solution_evidence: list[dict[str, str]] = []  # 技术方案 evidence 列表

    # 这里为收益结论预留起始 evidence 列表。
    list_effect_evidence: list[dict[str, str]] = []  # 技术效果 evidence 列表

    # 这里为对比背景预留起始 evidence 列表。
    list_prior_art_evidence: list[dict[str, str]] = []  # 现有技术 evidence 列表

    # 这里在 JSON 风格预览可用时优先走结构化提取。
    if dict_prior_art_preview and isinstance(dict_prior_art_preview.get("records"), list):

        # 这里一次性收下四类结构化 evidence。
        tuple_structured_evidence = extract_structured_prior_art_evidence(dict_prior_art_preview, str_path)  # 结构化 evidence 元组

        # 这里取出问题 evidence 列表。
        list_problem_evidence = tuple_structured_evidence[0]  # 结构化问题证据集合

        # 这里取出方案 evidence 列表。
        list_solution_evidence = tuple_structured_evidence[1]  # 结构化方案证据集合

        # 这里取出效果 evidence 列表。
        list_effect_evidence = tuple_structured_evidence[2]  # 结构化效果证据集合

        # 这里取出现有技术 evidence 列表。
        list_prior_art_evidence = tuple_structured_evidence[3]  # 结构化 prior-art 线索集合

    # 这里只在问题 evidence 为空时回退章节抽取。
    if not list_problem_evidence:

        # 这里补抓问题 evidence。
        list_problem_evidence = collect_source_evidence_by_kind(list_sections, str_path, "technical_problem")  # 当前 source 的问题证据列表

    # 这里只在方案 evidence 为空时回退章节抽取。
    if not list_solution_evidence:

        # 这里补抓方案 evidence。
        list_solution_evidence = collect_source_evidence_by_kind(list_sections, str_path, "technical_solution")  # 当前 source 的方案证据列表

    # 这里只在效果 evidence 为空时回退章节抽取。
    if not list_effect_evidence:

        # 这里补抓效果 evidence。
        list_effect_evidence = collect_source_evidence_by_kind(list_sections, str_path, "technical_effect")  # 当前 source 的效果证据列表

    # 这里只在现有技术 evidence 为空时回退章节抽取。
    if not list_prior_art_evidence:

        # 这里补抓现有技术 evidence。
        list_prior_art_evidence = collect_source_evidence_by_kind(list_sections, str_path, "prior_art_or_baseline")  # 当前 source 的 prior-art 线索列表

    # 这里把预览切成句子。
    list_summary_sentences = split_sentences(str_preview, int_limit=6)  # source 摘要句列表

    # 这里优先用前两句拼接 source 摘要。
    str_summary = "；".join(list_summary_sentences[:2]) if list_summary_sentences else "[待确认：未提取到材料摘要]"  # source 摘要文本

    # 这里先把四类 evidence 装进统一列表。
    list_term_inputs = [list_problem_evidence, list_solution_evidence, list_effect_evidence, list_prior_art_evidence]  # 术语统计证据列表

    # 这里组合当前 source 的术语输入。
    str_terms_source = build_source_term_input(list_headings, *list_term_inputs)  # 当前 source 的术语输入文本

    # 这里统计当前 source 的高频技术词。
    list_terms = [str_term for str_term, _ in keyword_counter(str_terms_source, int_limit=20)]  # 当前 source 技术词列表

    # 这里返回统一 source 记录，供 candidate point 聚合和 Markdown 渲染复用。
    return {
        "path": str_path,
        "summary": str_summary,
        "title_candidates": [infer_title_from_record(dict_record)],
        "technical_terms": list_terms,
        "technical_problem_evidence": list_problem_evidence,
        "technical_solution_evidence": list_solution_evidence,
        "technical_effect_evidence": list_effect_evidence,
        "prior_art_evidence": list_prior_art_evidence,
    }

# 从问题证据选择候选点问题正文。
def select_candidate_problem(list_problem_evidence: list[dict[str, Any]]) -> str:
    """返回首条问题证据或明确的待确认占位。

    参数：
    - `list_problem_evidence`：当前来源的问题证据列表。

    返回：
    - `str`：候选点问题正文。
    """

    # 有问题证据时优先采用首条受控原文。
    if list_problem_evidence:

        # 返回首条证据文本，保持原有候选生成顺序。
        return str(list_problem_evidence[0]["text"])

    # 缺少问题证据时保留显式待确认边界。
    return "[待确认：核心技术问题]"

# 根据问题、方案和效果证据完整度确定候选置信度。
def classify_candidate_confidence(
    list_problem_evidence: list[dict[str, Any]],
    list_solution_evidence: list[dict[str, Any]],
    list_effect_evidence: list[dict[str, Any]],
) -> str:
    """按三类证据完整度返回候选置信度。

    参数：
    - `list_problem_evidence`：问题证据列表。
    - `list_solution_evidence`：方案证据列表。
    - `list_effect_evidence`：效果证据列表。

    返回：
    - `str`：`high`、`medium` 或 `low`。
    """

    # 问题、方案和效果三项齐备时判定为高置信度。
    if list_problem_evidence and list_solution_evidence and list_effect_evidence:

        # 完整证据链允许候选进入高置信度层级。
        return "high"

    # 方案存在且问题或效果至少命中一项时判定为中置信度。
    if list_solution_evidence and (list_problem_evidence or list_effect_evidence):

        # 部分证据链保留进入后续筛选的资格。
        return "medium"

    # 其余情况统一标记为低置信度，提醒后续补料。
    return "low"

# 这里从 source 记录里组装候选专利点，保留问题、方案、效果和来源路径的统一视图。
def build_candidate_points(list_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    根据 source 记录列表构造候选专利点列表。

    参数：
    - `list_sources`：已经抽取完成的 source 记录列表。

    返回：
    - `list[dict[str, Any]]`：候选专利点结果列表。

    异常：
    - 无。
    """

    # 这里初始化候选专利点列表，后续逐个吸收具备方案证据的 source 记录。
    list_candidate_points: list[dict[str, Any]] = []  # 候选专利点列表

    # 这里初始化已见名称集合，避免多个 source 生成近乎同名的重复候选点。
    set_seen_names: set[str] = set()  # 已见候选点名称键集合

    # 这里逐个处理 source 记录，只为具备方案线索的记录生成候选专利点。
    for dict_source in list_sources:

        # 这里读取方案 evidence 列表，没有方案线索的 source 不进入候选点集合。
        list_solution_evidence = list(dict_source.get("technical_solution_evidence", []))  # 方案 evidence 列表

        # 这里跳过缺少方案线索的 source，避免产出只有背景或 prior-art 的空壳候选点。
        if not list_solution_evidence:

            # 这里直接处理下一个 source，把候选点名额留给更完整的材料。
            continue

        # 这里读取候选名称优先值，没有时退回来源路径主文件名。
        str_name = normalize_text(  # 候选专利点名称
            str(dict_source.get("title_candidates", [""])[0] or dict_source.get("path", "source"))  # 原始候选名称文本
        )

        # 这里把候选名称规整成去重键，避免多个 source 因大小写或空白差异重复入选。
        str_name_key = re.sub(r"\s+", "", str_name.lower())  # 候选点名称去重键

        # 这里跳过名称为空或已见候选，保持候选点列表聚焦且不重复。
        if not str_name_key or str_name_key in set_seen_names:

            # 这里忽略重复候选名称，避免 Markdown 报告重复展示相同概念。
            continue

        # 这里登记候选名称键，标记当前名称已经进入最终结果列表。
        set_seen_names.add(str_name_key)

        # 这里读取问题 evidence 列表，供候选点问题描述和置信度判断复用。
        list_problem_evidence = list(dict_source.get("technical_problem_evidence", []))  # 问题 evidence 列表

        # 这里读取效果 evidence 列表，供候选点效果描述和置信度判断复用。
        list_effect_evidence = list(dict_source.get("technical_effect_evidence", []))  # 效果 evidence 列表

        # 这里读取现有技术 evidence 列表，用来给当前候选点补上查新背景和对比来源。
        list_prior_art_evidence = list(dict_source.get("prior_art_evidence", []))  # 当前候选点的对比线索列表

        # 这里优先使用首条问题证据，缺失时保留待确认占位。
        str_problem = select_candidate_problem(list_problem_evidence)  # 候选点技术问题文本

        # 这里优先拼接前两条方案 evidence，没有时回退到 source 摘要文本。
        str_solution_text = "；".join(obj_item["text"] for obj_item in list_solution_evidence[:2])  # 前两条方案证据拼接文本

        # 这里在方案 evidence 拼接结果为空时回退到 source 摘要，避免候选点丢失最小方案描述。
        str_solution = str_solution_text or str(dict_source.get("summary", "[待确认：核心技术方案]"))  # 候选点技术方案文本

        # 这里用前三条效果 evidence 组装效果列表，没有时退回待确认占位。
        list_effects = [obj_item["text"] for obj_item in list_effect_evidence[:3]] or ["[待确认：技术效果]"]  # 候选点技术效果列表

        # 这里按问题、方案和效果证据完整度计算候选置信度。
        str_confidence = classify_candidate_confidence(  # 候选点置信度标签
            list_problem_evidence,  # 当前问题证据列表
            list_solution_evidence,  # 当前方案证据列表
            list_effect_evidence,  # 当前效果证据列表
        )

        # 这里读取当前 source 的技术术语列表，供候选点摘要和 Markdown 展示复用。
        list_terms = list(dict_source.get("technical_terms", []))[:12]  # 候选点技术术语列表

        # 这里把当前 source 组织成统一候选专利点记录，供 JSON 和 Markdown 同步使用。
        list_candidate_points.append(
            {
                "name": str_name,
                "problem": str_problem,
                "solution": str_solution,
                "effects": list_effects,
                "source_paths": [str(dict_source.get("path", "unknown"))],
                "confidence": str_confidence,
                "technical_terms": list_terms,
                "technical_problem_evidence": list_problem_evidence,
                "technical_solution_evidence": list_solution_evidence,
                "technical_effect_evidence": list_effect_evidence,
                "prior_art_evidence": list_prior_art_evidence,
            }
        )

    # 这里返回最终候选专利点列表，供 facts JSON 和 Markdown 渲染复用。
    return list_candidate_points[:12]

# 组合主案与数据两类候选，形成不得直接进入正文的审核队列。
def load_fact_integrity_contract_module() -> Any:
    """加载数值候选使用的事实完整性合同。

    参数：
    - 无。

    返回：
    - `Any`：已经执行源码的事实合同模块。

    异常：
    - 模块规格或加载器缺失时抛出 `ImportError`。
    """

    # 使用 facts 专用模块名绑定正式事实合同源码。
    obj_specification = importlib.util.spec_from_file_location(  # 事实合同加载规格
        "patent_facts_integrity_contract",  # facts 隔离模块名称
        PATH_FACT_INTEGRITY_CONTRACT,  # 正式事实合同源码路径
    )

    # 无法加载规则时必须阻断候选生成，禁止回退到第二套数值正则。
    if obj_specification is None or obj_specification.loader is None:

        # 抛出稳定错误，明确事实候选门禁缺失。
        raise ImportError("> ERR: [Python] 无法加载事实完整性合同模块。")

    # 创建隔离模块对象供本次 facts 运行使用。
    module_contract = importlib.util.module_from_spec(obj_specification)  # 事实合同模块对象

    # 执行正式源码，使候选抽取与验证共享相同豁免规则。
    obj_specification.loader.exec_module(module_contract)

    # 返回已经初始化的事实合同模块。
    return module_contract

# 把事实抽取结果转换为必须逐项审核且内容绑定的候选工件。
def build_review_candidates(list_candidate_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """构建带稳定指纹的人工审核候选数组。

    参数：
    - `list_candidate_points`：事实抽取阶段生成的候选专利点。

    返回：
    - `list[dict[str, Any]]`：不得直接进入正文的审核候选数组。

    异常：
    - 候选包含非 JSON 值时由序列化逻辑上抛。
    """

    # 保存与候选点顺序一致的审核记录。
    list_review_candidates: list[dict[str, Any]] = []  # 人工审核候选数组

    # 加载同源数值识别规则，避免 facts 与最终验证发生漂移。
    module_fact_contract = load_fact_integrity_contract_module()  # 事实完整性合同模块

    # 逐项绑定身份和规范化内容摘要，避免材料变化后沿用旧决定。
    for int_index, dict_candidate in enumerate(list_candidate_points, start=1):

        # 使用稳定 JSON 编码计算当前候选的内容指纹。
        str_payload_json = json.dumps(  # 候选点规范化 JSON
            dict_candidate,  # 当前候选完整事实载荷
            ensure_ascii=False,  # 保持中文语义参与摘要
            sort_keys=True,  # 固定对象字段顺序
            separators=(",", ":"),  # 排除无意义空白差异
        )

        # SHA-256 指纹同时绑定人工决定和后续失效判断。
        str_fingerprint = hashlib.sha256(str_payload_json.encode("utf-8")).hexdigest()  # 当前候选内容摘要

        # 追加只读载荷及来源身份，不把候选文本自动升级为确认事实。
        list_review_candidates.append(
            {
                "candidate_id": f"C{int_index:03d}",  # 当前候选稳定编号
                "candidate_type": "invention_point",  # 当前候选业务类型
                "fingerprint": str_fingerprint,  # 当前候选内容绑定摘要
                "source_paths": list(dict_candidate.get("source_paths", [])),  # 候选对应本地材料
                "payload": dict_candidate,  # 等待人工审核的原始事实载荷
            }
        )

    # 从候选事实载荷中收集需要独立批准的量化文本。
    list_numeric_texts = module_fact_contract.collect_governed_numeric_texts(list_candidate_points)  # 量化事实候选文本

    # 数据候选编号接续主案候选，保证全部决定身份唯一。
    int_start_index = len(list_review_candidates) + 1  # 首条数据候选顺序编号

    # 每条量化文本单独绑定指纹，不允许随主案整体接受。
    for int_offset, str_numeric_text in enumerate(list_numeric_texts):

        # 对原始量化句计算稳定摘要，供人工决定失效检查。
        str_fingerprint = hashlib.sha256(str_numeric_text.encode("utf-8")).hexdigest()  # 数据候选内容摘要

        # 追加独立 data_claim 候选，后续获批后才可形成 data_registry。
        list_review_candidates.append(
            {
                "candidate_id": f"C{int_start_index + int_offset:03d}",  # 数据候选稳定编号
                "candidate_type": "data_claim",  # 需要独立批准的数值事实类型
                "fingerprint": str_fingerprint,  # 当前量化文本内容摘要
                "source_paths": [],  # 来源路径由人工审核时补齐或确认
                "payload": {"text": str_numeric_text},  # 保留完整量化原句供审核
            }
        )

    # 返回完整候选数组供决定工件和预览门禁共同消费。
    return list_review_candidates

# 为首次出现的候选创建显式 pending 决定，不默认接受提取结果。
def build_initial_review_decisions(list_review_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """创建与当前候选一一对应的待审核决定。

    参数：
    - `list_review_candidates`：已经绑定内容摘要的候选数组。

    返回：
    - `list[dict[str, Any]]`：初始 pending 决定数组。

    异常：
    - 无。
    """

    # 每条决定复制候选身份和指纹，但不预填接受结论。
    list_decisions = [  # 首次人工审核决定数组
        {
            "candidate_id": str(dict_candidate["candidate_id"]),  # 当前审核候选编号
            "fingerprint": str(dict_candidate["fingerprint"]),  # 决定绑定的候选版本摘要
            "decision": "pending",  # 等待人工选择的初始状态
            "source_roles": {  # 每份来源路径的人工用途决定
                str(obj_path): "unknown"  # 每份材料初始保持未确认用途
                for obj_path in dict_candidate.get("source_paths", [])  # 遍历当前候选涉及的来源路径
            },  # 人工必须逐份改为 invention_evidence 或 prior_art
        }
        for dict_candidate in list_review_candidates  # 为每条审核候选建立初始决定
    ]  # 完成所有候选的未决审核状态初始化

    # 返回初始决定，后续只允许人工改为 accept、modify 或 reject。
    return list_decisions

# 在不覆盖人工结论的前提下创建首次审核决定工件。
def ensure_initial_review_decisions(
    path_review_decisions: Path,
    list_review_candidates: list[dict[str, Any]],
) -> None:
    """确保首次人工审核决定工件存在。

    参数：
    - `path_review_decisions`：人工决定 JSON 路径。
    - `list_review_candidates`：当前内容绑定候选数组。

    返回：
    - `None`。

    异常：
    - 目录创建或 JSON 写入失败时由底层异常上抛。
    """

    # 已有人工决定属于用户工件，事实重算不得自动覆盖。
    if path_review_decisions.exists():

        # 直接返回并保留现有逐项审核结果。
        return

    # 首次生成先确保草稿目录存在。
    ensure_dir(path_review_decisions.parent)

    # 生成与候选一一对应且默认未接受、来源角色未知的决定数组。
    list_review_decisions = build_initial_review_decisions(list_review_candidates)  # 初始人工决定数组

    # 写入决定工件供 confirmed preview 门禁消费。
    write_json_file(path_review_decisions, list_review_decisions)
