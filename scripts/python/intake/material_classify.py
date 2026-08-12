#!/usr/bin/env python3
"""研究材料模板识别与文本清洗支持。"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

# 这里收录行政字段关键词，帮助区分模板表头与真实技术内容。
ADMIN_PLACEHOLDER_KEYWORDS = frozenset(  # 模板行政字段关键词集合
    """
    申请人
    发明人
    联系人
    手机
    电话
    邮箱
    E-mail
    地址
    身份证
    撰写人
    所属项目
    """.split()
)

# 这里识别明显属于模板或示例的文件名模式。
TEMPLATE_FILE_RE = re.compile(r"(模板|模版|示例|样例|example|template)", re.I)  # 模板文件名识别规则

# 这里识别模板正文中常见的提示语。
TEMPLATE_MARKER_RE = re.compile(  # 模板提示语识别规则
    r"技术交底书模板|发明/实用新型专利申请技术资料交底模板|烦请填写下表|"
    r"为了方便与您的沟通|简单而明了地反映|最接近本申请|根据发明类型选择|"
    r"对于方法类的技术方案|对于结构类的技术方案|例如[:：]|【[^】]{6,220}】"
)

# 这里识别可直接删除的模板指令行。
TEMPLATE_INSTRUCTION_LINE_RE = re.compile(  # 模板指令整行识别规则
    r"^\s*(?:【[^】]{0,260}】|例如[:：].*|注[:：].*|附[:：].*|"
    r"为了方便与您的沟通|烦请填写下表|技术交底书模板|"
    r"发明/实用新型专利申请技术资料交底模板|"
    r"发明名称|发明创造类型|申请人名称|申请人地址|发明人排名|"
    r"第一发明人身份证号码|交底书撰写人|交底书撰写人手机号码|"
    r"交底书撰写人办公电话|交底书撰写人\s*E-mail|所属项目)\s*$",
    re.I,  # 忽略大小写匹配
)

# 这里识别解析失败提示，避免把失败消息当成真实发明内容。
UNREADABLE_HINT_RE = re.compile(r"\[(?:docx|pptx|pdf|text) (?:unreadable|parse error)|requirements.txt", re.I)  # 忽略大小写匹配的失败提示规则

# 这里识别需要剔除的长方括号模板提示。
TEMPLATE_BRACKET_RE = re.compile(r"【[^】]{6,}】")  # 模板长方括号提示识别规则

# 这里识别示例前缀，避免把模板举例语句带入事实抽取。
EXAMPLE_PREFIX_RE = re.compile(r"^例如[:：]")  # 示例前缀识别规则

# 这里提取模板提示命中原因，供盘点结果向人工解释降权依据。
def collect_template_reasons(list_marker_hits: list[str], bool_file_name_says_template: bool) -> list[str]:
    """生成模板识别原因列表。

    参数：
    - `list_marker_hits`：模板提示命中列表。
    - `bool_file_name_says_template`：文件名是否命中模板规则。

    返回：
    - `list[str]`：排序后的原因列表。

    异常：
    - 无。
    """

    # 这里先截断模板提示原因，避免单个文件把原因列表撑得过长。
    list_reasons = [str(str_marker) for str_marker in list_marker_hits[:8]]  # 模板提示原因列表

    # 这里补充文件名层面的模板信号，方便人工理解为什么被降权。
    if bool_file_name_says_template:

        # 这里显式记录文件名命中模板规则这一事实。
        list_reasons.append("filename_template_or_example")

    # 这里去重并排序，保证不同运行得到稳定输出顺序。
    return sorted(set(list_reasons))

# 这里计算行政字段命中数，辅助区分表单模板和真实研发材料。
def count_admin_placeholders(str_text_head: str) -> int:
    """统计行政字段关键词命中数。

    参数：
    - `str_text_head`：材料头部文本。

    返回：
    - `int`：行政字段命中数量。

    异常：
    - 无。
    """

    # 这里仅统计头部片段，足以识别大多数表单模板。
    str_head_for_admin = str_text_head[:4000]  # 行政字段判断文本样本

    # 这里累计行政字段命中数量，供后续模板判定使用。
    return sum(1 for str_keyword in ADMIN_PLACEHOLDER_KEYWORDS if str_keyword in str_head_for_admin)

# 这里汇总模板信号，减少分类主流程里的展开复杂度。
def collect_template_signals(str_text_head: str) -> dict[str, Any]:
    """汇总材料的模板信号。

    参数：
    - `str_text_head`：材料头部文本。

    返回：
    - `dict[str, Any]`：包含模板判断和相关统计的结果字典。

    异常：
    - 无。
    """

    # 这里提取模板提示命中列表，供角色判定和原因输出使用。
    list_marker_hits = TEMPLATE_MARKER_RE.findall(str_text_head)  # 模板提示命中列表

    # 这里统计长方括号提示数量，过多时通常说明正文仍是模板。
    int_bracket_count = len(TEMPLATE_BRACKET_RE.findall(str_text_head))  # 方括号提示数量

    # 这里统计行政字段命中数，模板表单会集中出现此类词。
    int_admin_hits = count_admin_placeholders(str_text_head)  # 行政字段命中数

    # 这里综合正文信号判断文本是否明显带模板提示。
    bool_looks_like_template = bool(list_marker_hits) or int_bracket_count >= 3 or int_admin_hits >= 5  # 是否带模板提示

    # 这里返回模板判断结果和中间统计，供上层复用。
    return {
        "bool_looks_like_template": bool_looks_like_template,
        "list_marker_hits": list_marker_hits,
        "int_bracket_count": int_bracket_count,
        "int_admin_hits": int_admin_hits,
    }

# 这里判断材料是研究内容、带提示的交底书，还是纯模板/示例。
def classify_input_document(path: Path, text: str) -> dict[str, Any]:
    """识别材料角色与模板风险。

    参数：
    - `path`：材料文件路径。
    - `text`：已抽取的材料文本。

    返回：
    - `dict[str, Any]`：包含角色、跳过标志和原因的分类结果。

    异常：
    - 无。
    """

    # 这里提取文件名，供文件名级别的模板判断使用。
    str_file_name = path.name if path else ""  # 当前文件名

    # 这里只分析头部文本，足以识别绝大多数模板提示。
    str_text_head = (text or "")[:30_000]  # 材料头部文本样本

    # 这里计算正文层面的模板信号和统计结果。
    dict_template_signals = collect_template_signals(str_text_head)  # 模板信号汇总结果

    # 角色判定只看这一条综合结论，因此先把它提取出来。
    bool_looks_like_template = bool(dict_template_signals["bool_looks_like_template"])  # 分类阶段使用的综合模板判断值

    # 审阅报告需要展示原始命中短语，所以这里保留提示词列表。
    list_marker_hits = list(dict_template_signals["list_marker_hits"])  # 供报告解释降权原因的提示短语列表

    # 这里根据文件名判断是否明显属于模板或示例材料。
    bool_file_name_says_template = bool(TEMPLATE_FILE_RE.search(str_file_name))  # 文件名模板信号

    # 这里识别抽取失败提示，避免把错误信息当成真实技术材料。
    bool_unreadable_hint = bool(UNREADABLE_HINT_RE.search(str_text_head))  # 解析失败提示信号

    # 这里只在文件名和正文都明显指向模板时把材料降级为仅参考。
    bool_sample_only = bool_file_name_says_template and (bool_looks_like_template or bool_unreadable_hint)  # 是否只应作为模板或示例参考

    # 这里生成材料角色，供盘点排序和事实抽取决定是否跳过。
    if bool_sample_only:

        # 这里把明显模板或示例材料标记为只读参考。
        str_role = "template_or_example"  # 仅模板或示例材料角色

    # 这里把带提示但包含真实内容的交底书单独标出来，方便后续清洗。
    elif bool_looks_like_template:

        # 这里保留带模板提示但可能有真实技术内容的材料角色。
        str_role = "filled_disclosure_with_prompts"  # 带模板提示的已填写交底书角色

    # 这里把普通研发材料标记为研究材料。
    else:

        # 这里把未命中模板特征的材料视为研究输入。
        str_role = "research_material"  # 普通研发材料角色

    # 这里生成可审阅的分类原因列表。
    list_reasons = collect_template_reasons(list_marker_hits, bool_file_name_says_template)  # 模板原因列表

    # 这里返回分类结果，供上游决定是否跳过或降权。
    return {
        "role": str_role,
        "skip_as_invention": bool_sample_only,
        "contains_template_prompts": bool_looks_like_template,
        "reasons": list_reasons,
        "bracket_instruction_count": int(dict_template_signals["int_bracket_count"]),
        "admin_field_hits": int(dict_template_signals["int_admin_hits"]),
    }

# 这里删除模板提示行和空表头，尽量保留真实技术段落。
def strip_template_instructions(text: str) -> str:
    """删除模板提示行。

    参数：
    - `text`：待清洗文本。

    返回：
    - `str`：删除模板提示后的文本。

    异常：
    - 无。
    """

    # 这里在空文本场景下直接返回空字符串。
    if not text:

        # 这里对空输入安全降级，避免上层还要额外判断。
        return ""

    # 这里初始化输出行列表，按原始顺序保留有效文本。
    list_output_lines: list[str] = []  # 清洗后的文本行

    # 这里逐行清洗模板说明和表单字段。
    for raw_line in text.splitlines():

        # 这里统一去掉首尾空白，便于模板规则判断。
        str_line = raw_line.strip()  # 去空白后的行文本

        # 这里保留空行，避免过度压缩破坏段落结构。
        if not str_line:

            # 这里保留空行占位，让有效段落边界尽量不丢失。
            list_output_lines.append("")

            # 这里跳到下一行处理，避免空行再参与其他模板规则判断。
            continue

        # 这里移除长方括号模板提示，但尽量保留同行真实说明文字。
        if "【" in str_line and "】" in str_line:

            # 这里删除行内长方括号提示，只保留可能存在的真实内容。
            str_line = TEMPLATE_BRACKET_RE.sub("", str_line).strip()  # 去除长方括号提示后的文本行

            # 这里在整行只剩模板提示时直接跳过。
            if not str_line:

                # 这里略过已经被完全清空的模板提示行。
                continue

        # 这里删除纯模板指令行和表单字段行。
        if TEMPLATE_INSTRUCTION_LINE_RE.match(str_line):

            # 这里直接跳过模板说明行，不让它进入事实抽取。
            continue

        # 这里删除模板复选框前缀行，避免无意义表单项污染正文。
        if str_line.startswith(("□发明", "□ 发明")):

            # 这里跳过模板复选框行。
            continue

        # 这里删除示例前缀行，避免举例说明误进入技术事实。
        if EXAMPLE_PREFIX_RE.match(str_line):

            # 这里跳过纯示例提示行。
            continue

        # 这里保留有效文本行，供后续事实抽取使用。
        list_output_lines.append(str_line)

    # 这里先按原始顺序重新拼接文本行。
    str_output_text = "\n".join(list_output_lines)  # 初步拼接后的文本

    # 这里循环压缩多余空行，避免输出里出现过长空白段。
    while "\n\n\n" in str_output_text:

        # 这里每轮把连续三行以上空白压缩成双空行。
        str_output_text = str_output_text.replace("\n\n\n", "\n\n")  # 压缩多余空行后的文本

    # 这里返回清洗后的文本结果。
    return str_output_text.strip()

# 这里统一收敛证据文本长度和空白，便于写入结构化证据字段。
def normalize_evidence_text(text: str, max_len: int = 280) -> str:
    """清洗证据文本。

    参数：
    - `text`：原始证据文本。
    - `max_len`：允许保留的最大长度。

    返回：
    - `str`：清洗后的证据文本。

    异常：
    - 无。
    """

    # 这里先复用模板清洗逻辑，避免把表单提示带入证据摘要。
    str_cleaned_text = strip_template_instructions(str(text or ""))  # 模板清洗后的证据文本

    # 这里归一化空白并去掉句首句尾杂质符号。
    str_cleaned_text = re.sub(r"\s+", " ", str_cleaned_text).strip(" ，,。；;：:")  # 规整后的证据文本

    # 这里在文本过长时截断，避免单条证据把 JSON 体积拉得过大。
    if len(str_cleaned_text) > max_len:

        # 这里只保留前部可读片段，并加省略号提醒已截断。
        str_cleaned_text = str_cleaned_text[:max_len].rstrip(" ，,。；;：:") + "…"  # 截断后的证据文本

    # 这里返回规整后的证据文本。
    return str_cleaned_text
