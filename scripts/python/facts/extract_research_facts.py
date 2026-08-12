#!/usr/bin/env python3
"""基于材料盘点结果提炼专利事实摘要。"""
from __future__ import annotations

# 这里引入标准库参数、时间、序列化和路径工具，供 facts 入口完成本地事实汇总与落盘。
import argparse
import json
import re
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

# 这里引入拆分后的报告辅助函数，让主文件只保留事实抽取和聚合流程。
from facts_report_support import build_missing_information
from facts_report_support import render_markdown

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
EFFECT_PATTERNS = """
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

# 这里解析 facts 入口参数，锁定案件目录和可选的研究根目录覆盖值。
def parse_arguments() -> argparse.Namespace:
    """
    解析 facts 入口命令行参数。

    参数：
    - 无。

    返回：
    - `argparse.Namespace`：包含案件目录和提取上限的参数对象。

    异常：
    - 参数缺失时由 `argparse` 自动结束进程。
    """

    # 这里先准备命令描述文本，避免解析器初始化行过长影响 current-project 可读性。
    str_parser_description = "Extract governed patent facts from research inventory."  # facts 命令说明文本

    # 这里构造命令行解析器，说明本脚本负责从盘点结果生成事实摘要。
    argument_parser_facts_cli = argparse.ArgumentParser(description=str_parser_description)  # facts 命令行解析器

    # 这里要求调用方提供案件目录，确保 facts 输出稳定写入当前案件目录。
    argument_parser_facts_cli.add_argument(  # 案件目录参数
        "--case-dir",
        required=True,
        help="Case directory containing inventory outputs.",
    )

    # 这里允许显式覆盖研究根目录，兼容盘点前后路径调整的场景。
    argument_parser_facts_cli.add_argument(  # 研究根目录覆盖参数
        "--research-root",
        required=False,
        help="Optional research root override.",
    )

    # 这里限制最多处理的源材料数量，避免单次 facts 汇总拉入过多低价值材料。
    argument_parser_facts_cli.add_argument(  # 最多处理源材料数量参数
        "--max-sources",
        type=int,
        default=12,
        help="Maximum readable source records to summarize.",
    )

    # 这里返回解析后的参数对象，供主流程继续读取案件目录和盘点结果。
    return argument_parser_facts_cli.parse_args()

# 这里生成 UTC 时间戳，供 facts JSON 明确记录本次汇总的生成时刻。
def iso_now() -> str:
    """
    生成当前 UTC 时间戳文本。

    参数：
    - 无。

    返回：
    - `str`：ISO 8601 格式的 UTC 时间戳文本。

    异常：
    - 无。
    """

    # 这里返回带时区信息的 UTC 时间文本，便于后续事实结果追踪生成时刻。
    return datetime.now(timezone.utc).isoformat()

# 这里确保目标目录存在，供 facts 入口统一写入 JSON 和 Markdown 结果。
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

    # 这里递归创建目录，允许调用方直接传入多级目标路径。
    path_dir.mkdir(parents=True, exist_ok=True)  # 已确保存在的目录路径

    # 这里返回目录对象，方便主流程继续拼接输出文件路径。
    return path_dir

# 这里统一读取 UTF-8 JSON 文件，减少 facts 入口对盘点和案件配置的重复读取逻辑。
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

    # 这里返回解析结果，供 facts 主流程继续访问结构化字段。
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

    # 这里把文本内容按 UTF-8 写入目标文件，保证中文事实摘要可直接审阅。
    (path_parent_dir / path_file.name).write_text(str_text, encoding="utf-8")  # 已写入的目标文本文件

# 这里统一写入可读 JSON 文件，保证 facts 结果具备稳定缩进和中文直出格式。
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

    # 这里复用统一文本写入入口，把 JSON 文本落到目标文件。
    write_text_file(path_file, str_json_text)

# 这里统一规整句子和证据文本中的空白与句边符号，减少重复句子难以去重的问题。
def normalize_text(str_text: str) -> str:
    """
    规整文本中的空白和句边杂质符号。

    参数：
    - `str_text`：待规整的原始文本。

    返回：
    - `str`：规整后的文本。

    异常：
    - 无。
    """

    # 这里先压缩连续空白，避免换行和多空格干扰句子与术语统计。
    str_normalized = re.sub(r"\s+", " ", str_text or "")  # 压缩空白后的文本

    # 这里去掉句首句尾的常见标点和空格，减少重复文本的表面差异。
    return str_normalized.strip(" ，,。；;：:[]【】()（）")

# 这里按中英文句末标点和换行切分句子，供技术问题、方案和效果的句子抽取复用。
def split_sentences(str_text: str, int_limit: int = 120) -> list[str]:
    """
    把文本切分为句子列表。

    参数：
    - `str_text`：待切分文本。
    - `int_limit`：最多保留的句子数量。

    返回：
    - `list[str]`：规整后的句子列表。

    异常：
    - 无。
    """

    # 这里在空文本场景下直接返回空列表，避免后续句子选择逻辑白跑一遍。
    if not str_text:

        # 这里对空输入安全降级，让调用方只处理真实句子内容。
        return []

    # 这里按中文句号、问号、叹号、分号和换行切开原始文本。
    list_raw_sentences = re.split(r"(?<=[。！？；!?;])\s*|\n+", str_text)  # 初始句子切片列表

    # 这里初始化规整后的句子结果列表。
    list_sentences: list[str] = []  # 规整后的句子结果列表

    # 这里逐句规整空白并过滤过短或过长的句子片段。
    for str_raw_sentence in list_raw_sentences:

        # 这里规整当前句子的空白和句边符号，得到更稳定的比较文本。
        str_sentence = normalize_text(str_raw_sentence)  # 规整后的单句文本

        # 这里只保留长度合适的句子，减少标题噪声和超长段落对抽取质量的干扰。
        if 8 <= len(str_sentence) <= 500:

            # 这里把通过长度筛选的句子加入结果列表。
            list_sentences.append(str_sentence)

        # 这里在达到数量上限时提前停止，保证 facts 汇总规模稳定。
        if len(list_sentences) >= int_limit:

            # 这里结束句子收集，避免长预览文本拉高处理开销。
            break

    # 这里返回最终句子列表，供证据句和摘要句抽取复用。
    return list_sentences

# 这里抽取高频技术词，供候选专利点命名和术语摘要复用。
def keyword_counter(str_text: str, int_limit: int = 30) -> list[tuple[str, int]]:
    """
    统计文本中的高频技术词。

    参数：
    - `str_text`：待统计文本。
    - `int_limit`：最多保留的术语数量。

    返回：
    - `list[tuple[str, int]]`：`(术语, 频次)` 形式的结果列表。

    异常：
    - 无。
    """

    # 这里规整全文空白，避免换行和多空格影响候选词切分。
    str_normalized_text = re.sub(r"\s+", " ", str_text or "")  # 规整空白后的全文文本

    # 这里初始化候选词频次字典，后续逐个累加技术词出现次数。
    dict_counts: dict[str, int] = {}  # 候选技术词频次字典

    # 这里逐个提取中英文数字混合片段，优先覆盖技术短语和符号名。
    for obj_match in re.finditer(r"[\u4e00-\u9fffA-Za-z0-9_+\-/.]{2,32}", str_normalized_text):

        # 这里规整当前候选词文本，去掉句边符号和无意义包裹字符。
        str_candidate = normalize_text(obj_match.group(0))  # 当前候选技术词

        # 这里跳过停用词和过短片段，避免泛化词主导技术术语结果。
        if not str_candidate or str_candidate in STOP_TERMS or len(str_candidate) <= 1:

            # 这里直接忽略噪声词，让词频统计聚焦技术名词和关键短语。
            continue

        # 这里跳过纯数字片段，避免编号和年份被误当成核心技术词。
        if re.fullmatch(r"\d+(?:\.\d+)?", str_candidate):

            # 这里过滤纯数字项，保留更像技术术语的候选词。
            continue

        # 这里累计候选词命中次数，供后续按频次排序。
        dict_counts[str_candidate] = dict_counts.get(str_candidate, 0) + 1  # 当前候选词累计命中次数

    # 这里按频次和术语文本排序，得到稳定可复现的术语结果顺序。
    list_sorted_terms = sorted(dict_counts.items(), key=lambda tuple_item: (-tuple_item[1], tuple_item[0]))  # 排序后的术语频次列表

    # 这里返回前若干术语结果，供候选点命名和 Markdown 摘要展示使用。
    return list_sorted_terms[:int_limit]

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

        # 这里读取 publication 字段。
        str_publication = normalize_text(str(dict_item.get("publication_no_or_title", "")))  # prior-art 记录标题

        # 这里读取实际技术问题字段。
        str_problem = normalize_text(str(dict_item.get("actual_technical_problem", "")))  # prior-art 中的实际技术问题

        # 这里读取技术效果字段。
        str_effect = normalize_text(str(dict_item.get("technical_effect", "")))  # prior-art 中的技术效果

        # 这里规整相同特征列表。
        list_same_features = [normalize_text(str(str_value)) for str_value in dict_item.get("same_features", [])]  # same_features 规整列表

        # 这里先读取原始区别特征列表。
        list_raw_different_features = list(dict_item.get("different_features", []))  # 原始区别特征列表

        # 这里规整区别特征短句。
        list_different_features = [normalize_text(str(str_value)) for str_value in list_raw_different_features]  # 规整后的区别特征短句列表

        # 这里在存在问题字段时补充问题 evidence。
        if str_problem:

            # 这里写入问题 evidence。
            list_problem_evidence.append(
                evidence_item(
                    str_problem,
                    str_path,
                    str_publication or "prior_art_record",
                    "technical_problem",
                    "medium",
                )
            )

        # 这里在存在特征时拼接方案摘要。
        if list_same_features or list_different_features:

            # 这里准备方案摘要片段列表。
            list_solution_fragments: list[str] = []  # 结构化方案摘要片段列表

            # 这里追加共同特征摘要。
            if list_same_features:

                # 这里登记已公开的共同特征摘要。
                list_solution_fragments.append(f"共同特征：{'、'.join(list_same_features[:3])}")

            # 这里追加区别特征摘要。
            if list_different_features:

                # 这里登记本案新增的区别特征摘要。
                list_solution_fragments.append(f"区别特征：{'、'.join(list_different_features[:3])}")

            # 这里组合方案摘要文本。
            str_solution = "；".join(list_solution_fragments)  # 结构化方案摘要文本

            # 这里仅在摘要非空时写入方案 evidence。
            if normalize_text(str_solution):

                # 这里写入方案 evidence。
                list_solution_evidence.append(
                    evidence_item(
                        str_solution,
                        str_path,
                        str_publication or "prior_art_record",
                        "technical_solution",
                        "medium",
                    )
                )

        # 这里在存在效果字段时写入效果 evidence。
        if str_effect:

            # 这里写入效果 evidence。
            list_effect_evidence.append(
                evidence_item(
                    str_effect,
                    str_path,
                    str_publication or "prior_art_record",
                    "technical_effect",
                    "medium",
                )
            )

        # 这里在存在 publication 标识时写入现有技术 evidence。
        if str_publication:

            # 这里写入现有技术 evidence。
            list_prior_art_evidence.append(
                evidence_item(
                    str_publication,
                    str_path,
                    "prior_art_record",
                    "prior_art_or_baseline",
                    "high",
                )
            )

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

        # 这里在存在问题 evidence 时优先使用首条问题句，没有时回退到待确认占位。
        if list_problem_evidence:

            # 这里取首条问题证据作为候选点问题文本，保持问题描述尽量具体。
            str_problem = list_problem_evidence[0]["text"]  # 候选点技术问题文本

        # 这里在问题 evidence 缺失时显式保留待确认占位，提醒后续人工补料。
        else:

            # 这里给缺少问题证据的候选点填入标准占位文本。
            str_problem = "[待确认：核心技术问题]"  # 候选点技术问题占位文本

        # 这里优先拼接前两条方案 evidence，没有时回退到 source 摘要文本。
        str_solution_text = "；".join(obj_item["text"] for obj_item in list_solution_evidence[:2])  # 前两条方案证据拼接文本

        # 这里在方案 evidence 拼接结果为空时回退到 source 摘要，避免候选点丢失最小方案描述。
        str_solution = str_solution_text or str(dict_source.get("summary", "[待确认：核心技术方案]"))  # 候选点技术方案文本

        # 这里用前三条效果 evidence 组装效果列表，没有时退回待确认占位。
        list_effects = [obj_item["text"] for obj_item in list_effect_evidence[:3]] or ["[待确认：技术效果]"]  # 候选点技术效果列表

        # 这里在问题、方案和效果三项齐备时把候选点标成高置信度。
        if list_problem_evidence and list_solution_evidence and list_effect_evidence:

            # 这里记录三项证据齐全的高置信度结果。
            str_confidence = "high"  # 候选点高置信度标签

        # 这里在方案齐备且问题或效果至少命中其一时保留中置信度。
        elif list_solution_evidence and (list_problem_evidence or list_effect_evidence):

            # 这里记录信息仍有缺口但已足够进入后续筛选的中置信度结果。
            str_confidence = "medium"  # 候选点中置信度标签

        # 这里把剩余证据不足的候选点标成低置信度，提醒后续慎用。
        else:

            # 这里记录当前候选点仍缺核心支撑证据的低置信度结果。
            str_confidence = "low"  # 候选点低置信度标签

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

# 这里执行 facts 主流程，并把 Markdown 报告路径写到标准输出末尾。
def main() -> int:
    """
    执行 facts 摘要主流程。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 缺少案件配置、盘点结果或 facts 输出目录写入失败时由底层异常上抛。
    """

    # 这里解析命令行参数，锁定案件目录和本次 facts 汇总的处理上限。
    namespace_arguments = parse_arguments()  # facts 入口参数

    # 这里解析案件目录绝对路径，保证后续读取配置和写结果都指向同一案件目录。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 案件根目录

    # 这里固定案件配置路径，供 facts 入口读取案件名称和默认研究根目录。
    path_case_config = path_case_dir / "case_config.json"  # 案件配置文件路径

    # 这里在缺少案件配置时立即报错，避免 facts 结果失去案件上下文。
    if not path_case_config.exists():

        # 这里抛出明确错误，提醒调用方先完成建案或补齐案件配置。
        raise FileNotFoundError("> ERR: [Python] 缺少 case_config.json，无法生成事实摘要")

    # 这里读取案件配置，供 facts 结果补齐案件名称和研究根目录字段。
    dict_case_config = read_json_file(path_case_config)  # 案件配置字典

    # 这里解析本次 research_root 文本，允许命令行覆盖案件配置里的默认值。
    str_research_root = namespace_arguments.research_root or dict_case_config.get("research_root", ".")  # 研究根目录文本

    # 这里固定盘点 JSON 路径，facts 入口默认直接消费受管盘点结果。
    path_inventory_json = path_case_dir / "01_inventory" / "research_inventory.json"  # 盘点 JSON 路径

    # 这里在缺少盘点结果时立即报错，避免 facts 入口在无输入场景下伪造成功。
    if not path_inventory_json.exists():

        # 这里抛出明确错误，提醒调用方先完成材料盘点步骤。
        raise FileNotFoundError("> ERR: [Python] 缺少 research_inventory.json，请先完成材料盘点")

    # 这里读取盘点结果，作为 facts 入口构造 source 记录和候选专利点的主输入。
    dict_inventory = read_json_file(path_inventory_json)  # 盘点结果字典

    # 这里创建 facts 输出目录，保证 JSON 和 Markdown 都有稳定落点。
    path_output_dir = ensure_dir(path_case_dir / "02_facts")  # facts 输出目录

    # 这里初始化原始 source 记录输入列表，后续只保留可读且非模板的材料记录。
    list_inventory_records = list(dict_inventory.get("files", []))  # 原始盘点记录列表

    # 这里初始化经过筛选的 source 输入记录列表，后续只纳入高价值可读材料。
    list_selected_records: list[dict[str, Any]] = []  # 已筛选的 source 输入记录列表

    # 这里逐个筛选盘点记录，只保留可读且不应跳过的材料进入 facts 汇总。
    for dict_record in list_inventory_records:

        # 这里在材料不可读或明确应跳过时直接略过，避免候选专利点被模板或空壳记录污染。
        if not dict_record.get("readable") or dict_record.get("skip_as_invention"):

            # 这里继续检查下一条盘点记录，把名额留给真实研发材料。
            continue

        # 这里把通过筛选的盘点记录加入 source 输入列表，供后续事实抽取使用。
        list_selected_records.append(dict_record)

        # 这里在达到 source 数量上限时及时停止，避免拉入过多低价值材料。
        if len(list_selected_records) >= namespace_arguments.max_sources:

            # 这里结束 source 记录筛选，保持 facts 结果规模稳定。
            break

    # 这里在筛选后仍无可读材料时立即报错，避免生成没有来源支撑的 facts 结果。
    if not list_selected_records:

        # 这里抛出明确错误，提示调用方补充可读材料或检查盘点结果。
        raise ValueError("> ERR: [Python] 盘点结果中没有可用于事实抽取的材料")

    # 这里逐个构造 source 事实记录，供 candidate point 聚合和 Markdown 渲染复用。
    list_sources = [build_source_record(dict_record) for dict_record in list_selected_records]  # source 事实记录列表

    # 这里根据 source 记录聚合候选专利点，形成事实摘要的核心结果。
    list_candidate_points = build_candidate_points(list_sources)  # 聚合后的候选专利点主视图

    # 这里初始化 prior-art 说明列表，后续按 source 展开对比线索。
    list_prior_art_notes = []  # prior-art 摘要列表

    # 这里逐个 source 展开 prior-art 线索，方便报告回看对比依据。
    for dict_source in list_sources:

        # 这里逐条写入当前 source 的 prior-art 摘要，保留来源语义。
        for dict_evidence in dict_source.get("prior_art_evidence", [])[:4]:

            # 这里把当前线索压成单行摘要，直接显示来源与结论。
            list_prior_art_notes.append(f"{dict_source['path']}: {dict_evidence['text']}")

    # 这里初始化全局术语片段列表，后续把候选点和 source 术语统一压平。
    list_terms_fragments = []  # 全局术语片段列表

    # 这里先追加候选点名称，保留主案命名和创新点标签。
    list_terms_fragments.extend(dict_point["name"] for dict_point in list_candidate_points)

    # 这里继续追加问题描述，避免问题导向术语被漏掉。
    list_terms_fragments.extend(dict_point["problem"] for dict_point in list_candidate_points)

    # 这里继续追加方案描述，让词频更贴近真实方案表达。
    list_terms_fragments.extend(dict_point["solution"] for dict_point in list_candidate_points)

    # 这里继续追加效果描述，让收益和性能类术语进入全局词频。
    for dict_point in list_candidate_points:

        # 这里逐条追加当前候选点的效果描述，保留收益类术语。
        for str_effect in dict_point["effects"]:

            # 这里写入当前效果片段，让收益术语进入统计输入。
            list_terms_fragments.append(str_effect)

    # 这里最后追加各个 source 的技术术语，补足候选点之外的领域词。
    for dict_source in list_sources:

        # 这里逐条追加当前 source 的技术术语，补齐领域词汇。
        for str_term in dict_source.get("technical_terms", []):

            # 这里写入当前 source 的术语片段，补足聚合摘要之外的词汇。
            list_terms_fragments.append(str_term)

    # 这里把全局术语片段压成统一词频输入，供项目级主题词统计继续复用。
    str_terms_source = "\n".join(list_terms_fragments)  # 全局技术术语统计输入文本

    # 这里统计全局技术术语，供 facts JSON 和 Markdown 报告展示项目级技术主题。
    list_global_terms = [str_term for str_term, _ in keyword_counter(str_terms_source, int_limit=80)]  # 全局技术术语列表

    # 这里把候选点缺口和 prior-art 线索残缺度转成待补料清单，供后续人工补齐。
    list_missing_information = build_missing_information(list_candidate_points, list_prior_art_notes)  # 缺失信息提示列表

    # 这里组装最终 facts 数据字典，供 JSON 落盘和 Markdown 渲染共同复用。
    dict_facts = {  # 最终 facts 数据字典
        "case_name": str(dict_case_config.get("case_name", path_case_dir.name)),  # 案件名称文本
        "research_root": str(Path(str_research_root).resolve()),  # 研究根目录绝对路径文本
        "generated_at": iso_now(),  # facts 生成时间戳
        "sources": list_sources,  # 当前案件的 source 事实记录列表
        "candidate_invention_points": list_candidate_points,  # 供后续主案选择使用的候选专利点列表
        "prior_art_notes": list_prior_art_notes[:40],  # 供人工审阅的 prior-art 摘要线索列表
        "technical_terms": list_global_terms,  # 汇总后的全局技术术语列表
        "missing_information": list_missing_information,  # 后续仍需补料的缺失信息提示列表
    }

    # 这里固定 facts JSON 输出路径，供后续候选点选择和正文起草步骤继续读取。
    path_facts_json = path_output_dir / "research_facts.json"  # facts JSON 输出路径

    # 这里固定人工审阅版 Markdown 路径，方便与 JSON 机器结果形成一对输出件。
    path_facts_markdown = path_output_dir / "research_facts.md"  # 人工审阅版 facts Markdown 路径

    # 这里把结构化 facts 数据写成 JSON 文件，作为后续步骤的稳定机器输入。
    write_json_file(path_facts_json, dict_facts)

    # 这里渲染 facts Markdown 文本，供人工快速审阅候选专利点和待补信息。
    str_facts_markdown = render_markdown(dict_facts)  # 待写入案件目录的 facts Markdown 报告文本

    # 这里把 facts Markdown 报告写入案件目录，方便人工继续阅读和确认。
    write_text_file(path_facts_markdown, str_facts_markdown)

    # 这里把 Markdown 报告路径作为机器可读输出写给上游流程。
    sys.stdout.write(str(path_facts_markdown.resolve()) + "\n")

    # 这里返回成功状态码，表示 facts 摘要已经完成并写入案件目录。
    return 0

# 这里保留标准脚本入口，方便命令行和流水线子进程统一调用 facts 入口。
if __name__ == "__main__":

    # 这里通过标准退出路径返回状态码，保持命令行调用行为一致。
    raise SystemExit(main())
