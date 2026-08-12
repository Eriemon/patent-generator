#!/usr/bin/env python3
"""研究材料文本整理与术语抽取支持。"""
from __future__ import annotations
import re
from collections import Counter

# 这里集中列出高频泛化词，避免它们在盘点和事实抽取里虚高。
STOP_TERMS = frozenset(  # 需要在术语统计里主动降噪的停用词集合
    """
    一种
    方法
    系统
    模块
    数据
    技术
    方案
    处理
    the
    and
    for
    with
    from
    """.split()
)

# 这里判断文本是否像章节标题，避免在标题提取函数里嵌套过深。
def is_section_heading(str_line: str) -> bool:
    """判断文本是否命中常见章节标题模式。

    参数：
    - `str_line`：待判断文本行。

    返回：
    - `bool`：命中常见章节标题模式时返回 `True`。

    异常：
    - 无。
    """

    # 这里统一复用章节标题正则，减少标题提取主流程中的条件复杂度。
    return re.match(
        r"^(第[一二三四五六七八九十]+[章节]|[一二三四五六七八九十]+、|[0-9]+(?:\.[0-9]+)*[、.\s])",
        str_line,
    ) is not None

# 这里提取 Markdown 和结构化文本中的标题，供盘点与事实抽取复用。
def extract_headings(text: str, int_limit: int = 40) -> list[str]:
    """从文本中提取标题列表。

    参数：
    - `text`：待分析文本。
    - `int_limit`：最多保留的标题数量。

    返回：
    - `list[str]`：识别出的标题列表。

    异常：
    - 无。
    """

    # 这里初始化标题结果列表，按出现顺序保存命中的标题。
    list_headings: list[str] = []  # 按出现顺序保留的标题结果

    # 这里逐行扫描文本，优先识别 Markdown 标题和常见中文章节标题。
    for raw_line in text.splitlines():

        # 这里统一去掉首尾空白，便于后续按模式识别标题。
        str_line = raw_line.strip()  # 去掉首尾空白后的文本行

        # 这里跳过空行，避免写入无意义标题。
        if not str_line:

            # 这里对空行直接略过，让标题列表只保留有效内容。
            continue

        # 这里优先识别 Markdown 标题格式。
        if str_line.startswith("#"):

            # 这里写入清洗后的 Markdown 标题文本。
            list_headings.append(str_line.lstrip("#").strip())

        # 这里保留长度合理的章节标题，避免把整段正文误判成标题。
        if is_section_heading(str_line) and len(str_line) <= 120:

            # 这里保留通过长度校验的章节标题文本。
            list_headings.append(str_line)

        # 这里补充识别常见专利写作标题，兼容无序号的简短栏目名。
        elif str_line in {"背景问题", "技术方案", "技术效果", "现有技术", "实验结果", "实施方式"}:

            # 这里保留短标题，方便人工快速浏览材料结构。
            list_headings.append(str_line)

        # 这里在达到数量上限时立即结束，保持输出规模稳定。
        if len(list_headings) >= int_limit:

            # 这里停止继续扫描，避免极长材料把标题列表拉得过长。
            break

    # 这里返回识别出的标题结果。
    return list_headings

# 这里按中英文句末标点和换行切分句子，供事实抽取和摘要生成复用。
def split_sentences(text: str, int_limit: int = 200) -> list[str]:
    """把文本切分为句子列表。

    参数：
    - `text`：待切分文本。
    - `int_limit`：最多保留的句子数量。

    返回：
    - `list[str]`：清洗后的句子列表。

    异常：
    - 无。
    """

    # 这里在空文本场景下直接返回空列表，避免后续无意义处理。
    if not text:

        # 这里对空输入安全降级，保持调用方逻辑简单。
        return []

    # 这里按中英文句末标点和换行切分句子。
    list_raw_sentences = re.split(r"(?<=[。！？；!?;])\s*|\n+", text)  # 初始句子切片

    # 这里初始化清洗后的句子列表。
    list_sentences: list[str] = []  # 过滤后的句子结果

    # 这里逐句清洗空白并过滤明显噪声句。
    for raw_sentence in list_raw_sentences:

        # 这里归一化句子内部空白，便于后续写入 Markdown 和 JSON。
        str_sentence = re.sub(r"\s+", " ", raw_sentence.strip())  # 归一化后的句子文本

        # 这里只保留长度合理的句子，减少碎片和超长段落噪声。
        if 8 <= len(str_sentence) <= 500:

            # 这里保留可用于后续事实抽取的句子内容。
            list_sentences.append(str_sentence)

    # 这里返回限定数量的句子结果。
    return list_sentences[:int_limit]

# 这里抽取高频技术词，供盘点、事实抽取和查新计划共用。
def keyword_counter(text: str, int_limit: int = 30) -> list[tuple[str, int]]:
    """抽取文本中的高频术语。

    参数：
    - `text`：待分析文本。
    - `int_limit`：最多保留的术语数量。

    返回：
    - `list[tuple[str, int]]`：`(术语, 频次)` 形式的结果列表。

    异常：
    - 无。
    """

    # 这里统一归一化空白，减少换行和多空格对术语切分的影响。
    str_normalized_text = re.sub(r"\s+", " ", text or "")  # 归一化后的全文文本

    # 这里初始化候选术语列表，后续再做频次统计。
    list_candidates: list[str] = []  # 候选术语列表

    # 这里按中英文数字混合片段提取候选词，优先覆盖技术短语。
    for obj_match in re.finditer(r"[\u4e00-\u9fffA-Za-z0-9_+\-/.]{2,24}", str_normalized_text):

        # 这里裁掉片段首尾的标点和括号，得到规整候选词。
        str_candidate = obj_match.group(0).strip(" ，,。；;：:（）()[]【】")  # 当前候选术语

        # 这里只保留非停用的候选词，减少泛化项干扰。
        if str_candidate and str_candidate not in STOP_TERMS:

            # 这里保存候选术语，供后续统一做频次统计。
            list_candidates.append(str_candidate)

    # 这里统计候选词频次，供后续排序使用。
    counter_term_hits: Counter[str] = Counter(list_candidates)  # 候选术语频次统计

    # 这里初始化最终结果列表。
    list_terms: list[tuple[str, int]] = []  # 最终术语结果

    # 这里逐个过滤纯数字和过短片段，保留更稳定的技术项。
    for str_term, int_hit_count in counter_term_hits.most_common(int_limit * 5):

        # 这里再次过滤停用词，防止特殊切分路径把它们重新带回来。
        if str_term in STOP_TERMS:

            # 这里直接跳过停用词，避免其占据结果名额。
            continue

        # 这里过滤纯数字片段，避免编号和版本号主导术语统计。
        if re.fullmatch(r"\d+(?:\.\d+)?", str_term):

            # 这里跳过纯数字项，只保留更像技术词的片段。
            continue

        # 这里过滤单字符片段，减少噪声术语。
        if len(str_term) <= 1:

            # 这里跳过过短片段，保持术语结果可读。
            continue

        # 这里保存通过筛选的术语及其命中次数。
        list_terms.append((str_term, int_hit_count))

        # 这里在达到术语上限时停止，保持输出规模稳定。
        if len(list_terms) >= int_limit:

            # 这里结束术语收集，避免返回过长结果。
            break

    # 这里返回高频术语结果。
    return list_terms
