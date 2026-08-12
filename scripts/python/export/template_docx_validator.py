"""独立验证最终模板 DOCX 的中文排版角色和槽位边界。"""

# 启用延迟类型注解，避免运行时解析 python-docx 私有类型。
from __future__ import annotations

# 标准库负责合同读取、路径约束、角色识别和宽松对象类型。
import json
from pathlib import Path
import re
from typing import Any

# 编号步骤合同覆盖普通序号和专利方法步骤编号。
PATTERN_NUMBERED_STEP = re.compile(r"^(?:\d+[.、]|S\d+[，,:：.、])")  # 编号步骤识别表达式

# 参考文献条目必须从方括号编号开始。
PATTERN_REFERENCE_ENTRY = re.compile(r"^\[\d+\]\s*")  # 参考文献条目识别表达式

# 点数比较允许 OOXML 序列化产生的轻微舍入差异。
FLOAT_TOLERANCE_PT = 0.2  # 排版点数比较容差

# 规整标题中的全部空白，兼容模板标题内部的软换行。
def normalize_slot_text(str_text: str) -> str:
    """返回用于槽位标题比较的无空白文本。

    参数：
    - `str_text`：最终 DOCX 中的原始段落文本。

    返回：
    - `str`：删除全部空白后的标题比较键。
    """

    # 只改变比较键，不改写最终文档中的可见标题。
    return "".join(str_text.split())

# 判断段落 XML 是否包含指定 OOXML 本地标签。
def paragraph_contains_tag(obj_paragraph: Any, str_local_name: str) -> bool:
    """判断段落是否包含指定 OOXML 节点。

    参数：
    - `obj_paragraph`：待扫描的 python-docx 段落对象。
    - `str_local_name`：目标 OOXML 节点本地名。

    返回：
    - `bool`：段落后代节点包含目标标签时为真。
    """

    # 遍历当前段落全部后代，兼容公式或图片位于嵌套 run 中。
    for obj_element in obj_paragraph._p.iter():

        # OOXML 标签以命名空间加本地名结尾。
        if obj_element.tag.endswith("}" + str_local_name):

            # 找到目标节点后无需继续扫描。
            return True

    # 全部节点均未命中目标标签。
    return False

# 根据最终 OOXML 和可见文本独立判定段落角色。
def classify_final_paragraph(obj_paragraph: Any) -> str:
    """返回最终 DOCX 段落对应的样式角色。

    参数：
    - `obj_paragraph`：从最终落盘 DOCX 读取的内容段落。

    返回：
    - `str`：样式合同中的唯一角色名称。
    """

    # 先提取普通可见文本，区分独立公式段落和含行内公式的正文。
    str_text = obj_paragraph.text.strip()  # 最终段落普通可见文本

    # 只有不含普通文本的纯 OMML 或 MathType OLE 段落才使用行间公式角色。
    if not str_text and (
        paragraph_contains_tag(obj_paragraph, "oMath")
        or paragraph_contains_tag(obj_paragraph, "object")
    ):

        # 原生 Office 数学节点使用行间公式角色。
        return "display_formula"

    # Drawing 节点表示正式附图段落。
    if paragraph_contains_tag(obj_paragraph, "drawing"):

        # 图片段落使用居中且无缩进角色。
        return "figure"

    # 参考文献标题使用独立强调样式。
    if str_text == "参考文献":

        # 标题不继承普通正文的首行缩进。
        return "reference_heading"

    # 著录项使用方括号编号和悬挂缩进。
    if PATTERN_REFERENCE_ENTRY.match(str_text):

        # 返回参考文献条目角色。
        return "reference_entry"

    # 序号或方法步骤号开头的正文使用悬挂缩进。
    if PATTERN_NUMBERED_STEP.match(str_text):

        # 返回编号步骤角色。
        return "numbered_step"

    # 其余非空槽位内容均为普通中文正文。
    return "body"

# 创建结构稳定的排版 finding，供导出门禁和测试共同消费。
def build_finding(str_code: str, str_role: str, int_paragraph: int, str_message: str) -> dict[str, Any]:
    """构造一个可机器读取的 DOCX 排版问题。

    参数：
    - `str_code`：稳定的问题代码。
    - `str_role`：发生偏差的段落或结构角色。
    - `int_paragraph`：最终正文中的段落序号。
    - `str_message`：供审阅者理解的中文偏差说明。

    返回：
    - `dict[str, Any]`：字段固定的排版 finding。
    """

    # 返回字段固定的一行字典，避免不同检查生成不兼容结构。
    return {"code": str_code, "role": str_role, "paragraph": int_paragraph, "message": str_message}

# 把可选 python-docx Length 转换为点数。
def optional_length_pt(obj_length: Any) -> float | None:
    """返回长度对象的点数；未设置时返回空值。

    参数：
    - `obj_length`：python-docx Length 对象或空值。

    返回：
    - `float | None`：显式点数，未设置时为空值。
    """

    # Word 默认值在本合同中不能替代显式缩进。
    if obj_length is None:

        # 使用空值区分显式零点和未设置。
        return None

    # python-docx Length 统一提供 pt 属性。
    return float(obj_length.pt)

# 比较一个实际点数与合同期望值。
def points_match(float_actual: float | None, float_expected: float) -> bool:
    """判断实际点数是否落在合同容差内。

    参数：
    - `float_actual`：从最终 OOXML 读取的可选实际点数。
    - `float_expected`：样式合同要求的点数。

    返回：
    - `bool`：实际点数存在且位于固定容差内时为真。
    """

    # 未显式写入的 Word 默认值不能通过排版合同。
    if float_actual is None:

        # 缺失值与任何显式合同值都不相等。
        return False

    # 使用固定绝对容差吸收 OOXML 半点等舍入差异。
    return abs(float_actual - float_expected) <= FLOAT_TOLERANCE_PT

# 验证一个内容段落的字体、行距、缩进、对齐和强调属性。
def collect_paragraph_role_findings(
    obj_paragraph: Any,
    str_role: str,
    dict_contract: dict[str, Any],
    int_paragraph: int,
) -> list[dict[str, Any]]:
    """返回一个最终段落相对样式角色的全部偏差。

    参数：
    - `obj_paragraph`：待验证的最终 DOCX 内容段落。
    - `str_role`：依据最终 OOXML 独立判定的角色。
    - `dict_contract`：正式中文 DOCX 样式合同。
    - `int_paragraph`：当前内容在最终正文中的段落序号。

    返回：
    - `list[dict[str, Any]]`：当前段落的结构化排版问题列表。
    """

    # 延迟导入东亚字体命名 helper，保持模块发现阶段不强制 python-docx。
    from docx.oxml.ns import qn

    # 读取当前角色合同并初始化问题列表。
    dict_role = dict_contract["roles"][str_role]  # 当前验证角色合同

    # 当前段落可能产生多个独立排版问题。
    list_findings: list[dict[str, Any]] = []  # 当前段落排版问题

    # 未声明字号的公式、附图和空段仍以小四字号换算零字符缩进。
    float_font_size = float(dict_role.get("font_size_pt", 14))  # 当前角色字号点数

    # 首行缩进由角色字符数与字号共同决定。
    float_expected_first = float(dict_role.get("first_line_indent_chars", 0)) * float_font_size  # 期望首行缩进点数

    # 左缩进用于普通正文归零或形成悬挂缩进边界。
    float_expected_left = float(dict_role.get("left_indent_chars", 0)) * float_font_size  # 期望左缩进点数

    # 读取最终段落的两个直接格式长度。
    float_actual_first = optional_length_pt(obj_paragraph.paragraph_format.first_line_indent)  # 实际首行缩进点数

    # 左缩进必须与首行缩进独立验证。
    float_actual_left = optional_length_pt(obj_paragraph.paragraph_format.left_indent)  # 实际左缩进点数

    # 首行缩进漂移会直接降低中文正文或悬挂条目的可读性。
    if not points_match(float_actual_first, float_expected_first):

        # 使用角色前缀生成可稳定定位的 finding 代码。
        list_findings.append(
            build_finding(
                f"{str_role}_first_line_indent",  # 首行缩进问题代码
                str_role,  # 当前段落角色
                int_paragraph,  # 最终文档段落序号
                f"期望首行缩进 {float_expected_first:.1f} pt，实际为 {float_actual_first}",  # 偏差说明
            )
        )

    # 左缩进必须显式归零或达到两字符悬挂边界。
    if not points_match(float_actual_left, float_expected_left):

        # 记录当前角色的左缩进偏差。
        list_findings.append(
            build_finding(
                f"{str_role}_left_indent",  # 左缩进问题代码
                str_role,  # 接受左缩进检查的角色
                int_paragraph,  # 问题所在段落序号
                f"期望左缩进 {float_expected_left:.1f} pt，实际为 {float_actual_left}",  # 左缩进偏差说明
            )
        )

    # 文字角色必须显式使用合同倍数行距。
    if "line_spacing" in dict_role:

        # 读取 python-docx 暴露的最终倍数行距。
        obj_line_spacing = obj_paragraph.paragraph_format.line_spacing  # 实际段落行距

        # 未设置或数值漂移均视为合同失败。
        if obj_line_spacing is None or abs(float(obj_line_spacing) - float(dict_role["line_spacing"])) > 0.01:

            # 记录倍数行距偏差。
            list_findings.append(
                build_finding(
                    f"{str_role}_line_spacing",  # 行距问题代码
                    str_role,  # 接受行距检查的角色
                    int_paragraph,  # 行距偏差段落序号
                    f"期望 {dict_role['line_spacing']} 倍行距，实际为 {obj_line_spacing}",  # 行距偏差说明
                )
            )

    # 合同对齐名称转为 python-docx 对应的稳定整数值。
    dict_alignment_values = {"left": 0, "center": 1}  # 验证端对齐名称映射

    # 读取当前角色的期望对齐值。
    int_expected_alignment = dict_alignment_values[str(dict_role.get("alignment", "left"))]  # 期望对齐枚举值

    # 对齐方式必须由生成端直接写入，不能依赖样式继承。
    if obj_paragraph.alignment != int_expected_alignment:

        # 记录公式、附图或文字段落的对齐偏差。
        list_findings.append(
            build_finding(
                f"{str_role}_alignment",  # 对齐问题代码
                str_role,  # 接受对齐检查的角色
                int_paragraph,  # 对齐偏差段落序号
                f"期望对齐值 {int_expected_alignment}，实际为 {obj_paragraph.alignment}",  # 对齐偏差说明
            )
        )

    # 没有字体合同的公式和附图到此已经完成验证。
    if "font_family" not in dict_role:

        # 返回段落级格式发现。
        return list_findings

    # 只验证承载可见文本的 run，忽略书签和数学结构 run。
    list_text_runs = [obj_run for obj_run in obj_paragraph.runs if obj_run.text]  # 当前段落可见文字片段

    # 每个可见文字片段都必须显式写入宋体、小四和角色粗体状态。
    for obj_run in list_text_runs:

        # 获取可能缺失的直接 run 属性节点。
        obj_run_properties = obj_run._element.rPr  # 当前文字片段属性节点

        # 读取 East Asia 字体，缺失时保留空值供合同阻断。
        str_east_asia_font = (
            obj_run_properties.rFonts.get(qn("w:eastAsia"))  # 当前文字片段东亚字体
            if obj_run_properties is not None and obj_run_properties.rFonts is not None  # 字体属性节点完整
            else None  # 未显式设置东亚字体
        )  # 最终东亚字体名称

        # 中文字体必须显式为宋体。
        if str_east_asia_font != str(dict_role["font_family"]):

            # 同一 run 的字体问题使用当前段落位置定位。
            list_findings.append(
                build_finding(
                    f"{str_role}_font_family",  # 字体问题代码
                    str_role,  # 接受字体检查的角色
                    int_paragraph,  # 字体偏差段落序号
                    f"期望字体 {dict_role['font_family']}，实际为 {str_east_asia_font}",  # 字体偏差说明
                )
            )

        # 读取直接字号点数，未设置时保留空值。
        float_run_size = float(obj_run.font.size.pt) if obj_run.font.size is not None else None  # 当前文字片段字号

        # 正文字号必须为合同小四点数。
        if not points_match(float_run_size, float(dict_role["font_size_pt"])):

            # 记录当前 run 的字号偏差。
            list_findings.append(
                build_finding(
                    f"{str_role}_font_size",  # 字号问题代码
                    str_role,  # 接受字号检查的角色
                    int_paragraph,  # 字号偏差段落序号
                    f"期望字号 {dict_role['font_size_pt']} pt，实际为 {float_run_size}",  # 字号偏差说明
                )
            )

        # 角色粗体状态必须显式一致。
        if bool(obj_run.bold) != bool(dict_role.get("bold", False)):

            # 记录参考文献标题或普通正文的粗体偏差。
            list_findings.append(
                build_finding(
                    f"{str_role}_bold",  # 粗体问题代码
                    str_role,  # 接受粗体检查的角色
                    int_paragraph,  # 粗体偏差段落序号
                    f"期望粗体 {bool(dict_role.get('bold', False))}，实际为 {obj_run.bold}",  # 粗体偏差说明
                )
            )

    # 返回当前内容段落的全部独立问题。
    return list_findings

# 验证最终文档全部正式槽位和内容角色。
def collect_docx_style_findings(path_docx: Path, path_contract: Path) -> list[dict[str, Any]]:
    """返回最终 DOCX 相对中文样式合同的全部问题。

    参数：
    - `path_docx`：已经保存到磁盘的最终 DOCX 路径。
    - `path_contract`：正式 JSON 样式合同路径。

    返回：
    - `list[dict[str, Any]]`：槽位结构和段落角色的全部 finding。

    异常：
    - DOCX 或合同无法读取时继续抛出底层异常，禁止静默放行。
    """

    # 延迟导入 Document，使缺少文档依赖时错误发生在真实验证入口。
    from docx import Document

    # 读取正式合同和最终落盘 DOCX。
    dict_contract = json.loads(Path(path_contract).read_text(encoding="utf-8"))  # 最终验证样式合同

    # 从磁盘重新打开文档，禁止验证未序列化的内存对象。
    obj_document = Document(str(path_docx))  # 最终交付文档对象

    # 固化正文段落序列，槽位索引和 finding 使用同一顺序。
    list_paragraphs = list(obj_document.paragraphs)  # 最终文档正文段落序列

    # 建立规整标题到正式标题的唯一映射。
    dict_normalized_headings = {
        normalize_slot_text(str_heading): str_heading  # 规整键对应的正式槽位标题
        for str_heading in dict_contract["slot_headings"]  # 合同声明的槽位标题来源
    }  # 规整槽位标题映射

    # 保存每个正式标题在最终正文中的段落位置。
    dict_heading_indexes: dict[str, int] = {}  # 最终槽位标题索引

    # 扫描最终正文，忽略信息表和说明页中的非正式文字。
    for int_index, obj_paragraph in enumerate(list_paragraphs):

        # 规整当前可见文本供标题映射查询。
        str_normalized_text = normalize_slot_text(obj_paragraph.text)  # 标题扫描使用的无空白文本

        # 仅登记与合同标题完全相等的正式节点。
        if str_normalized_text in dict_normalized_headings:

            # 保存标准标题对应的最终段落位置。
            dict_heading_indexes[dict_normalized_headings[str_normalized_text]] = int_index  # 正式标题最终位置

    # 缺少任一标题时，无法可靠判断其槽位内容边界。
    list_missing_headings = [
        str_heading  # 当前缺失的正式槽位标题
        for str_heading in dict_contract["slot_headings"]  # 全部强制标题来源
        if str_heading not in dict_heading_indexes  # 最终正文未登记该标题
    ]  # 最终文档缺失标题

    # 初始化最终文档全部样式 finding。
    list_findings: list[dict[str, Any]] = []  # 最终 DOCX 排版问题

    # 每个缺失标题都生成独立 finding，随后停止不可靠的边界扫描。
    for str_missing_heading in list_missing_headings:

        # 缺失标题没有可用段落序号，使用负一表示结构级问题。
        list_findings.append(
            build_finding(
                "slot_heading_missing",  # 槽位标题缺失代码
                "slot_heading",  # 结构级标题角色
                -1,  # 未定位到最终段落
                f"最终 DOCX 缺少槽位标题：{str_missing_heading}",  # 缺失标题说明
            )
        )

    # 标题不完整时直接返回，避免错误归属相邻章节正文。
    if list_missing_headings:

        # 返回结构级问题供导出协调器阻断。
        return list_findings

    # 按合同顺序逐槽位验证正文角色和尾空段数量。
    for int_slot_index, str_heading in enumerate(dict_contract["slot_headings"]):

        # 当前槽位内容从标题后一个段落开始。
        int_content_start = dict_heading_indexes[str_heading] + 1  # 当前槽位正文起点

        # 下一标题或文档尾部构成当前槽位的排他结束位置。
        int_content_end = (
            dict_heading_indexes[dict_contract["slot_headings"][int_slot_index + 1]]  # 下一槽位标题位置
            if int_slot_index + 1 < len(dict_contract["slot_headings"])  # 当前槽位不是最后一项
            else len(list_paragraphs)  # 最后槽位延伸到正文末尾
        )  # 当前槽位正文结束位置

        # 提取当前标题与下一标题之间的最终段落。
        list_slot_paragraphs = list_paragraphs[int_content_start:int_content_end]  # 当前槽位最终内容段落

        # 从槽位末端统计连续空段，公式和附图不会被误当作空段。
        int_trailing_blank_count = 0  # 当前槽位尾空段数量

        # 逆序扫描直到遇到首个可见正文、公式或图片。
        for obj_candidate in reversed(list_slot_paragraphs):

            # 纯空段既没有可见文本，也没有 OMML、MathType OLE 或图片节点。
            bool_candidate_blank = (
                not obj_candidate.text.strip()  # 当前候选没有可见文本
                and not paragraph_contains_tag(obj_candidate, "oMath")  # 当前候选没有数学节点
                and not paragraph_contains_tag(obj_candidate, "object")  # 当前候选没有 MathType OLE 对象
                and not paragraph_contains_tag(obj_candidate, "drawing")  # 当前候选没有图片节点
            )  # 当前候选是否为纯空段

            # 遇到内容后终止尾空段统计。
            if not bool_candidate_blank:

                # 当前槽位尾部空段序列已经结束。
                break

            # 累加一个连续尾空段。
            int_trailing_blank_count += 1  # 当前槽位累计尾空段数

        # 去掉尾空段后剩余内容决定槽位是否已填充。
        list_content_paragraphs = (
            list_slot_paragraphs[:-int_trailing_blank_count]  # 排除已统计的尾空段
            if int_trailing_blank_count  # 当前槽位存在连续尾空段
            else list_slot_paragraphs  # 当前槽位没有尾空段
        )  # 当前槽位实际内容段落

        # 至少一个正文、公式或图片段落即视为有内容槽位。
        bool_slot_populated = bool(list_content_paragraphs)  # 当前槽位填充状态

        # 依据填充状态选择合同规定的精确尾空段数量。
        int_expected_blank_count = (
            int(dict_contract["slot_spacing"]["populated_trailing_blank_paragraphs"])  # 有内容槽位期望值
            if bool_slot_populated  # 当前槽位已经写入正式内容
            else int(dict_contract["slot_spacing"]["empty_trailing_blank_paragraphs"])  # 空槽位期望值
        )  # 当前槽位期望尾空段数

        # 尾空段数量必须精确相等，禁止靠累积空行制造松散版面。
        if int_trailing_blank_count != int_expected_blank_count:

            # 记录当前槽位边界偏差。
            list_findings.append(
                build_finding(
                    "slot_trailing_blank_count",  # 槽位尾空段数量代码
                    "slot_spacing",  # 槽位边界角色
                    dict_heading_indexes[str_heading],  # 当前槽位标题段落序号
                    f"{str_heading} 期望 {int_expected_blank_count} 个尾空段，实际为 {int_trailing_blank_count}",  # 边界偏差说明
                )
            )

        # 对当前槽位每个真实内容段落执行独立角色验证。
        for int_offset, obj_content in enumerate(list_content_paragraphs):

            # 最终段落角色仅依据 OOXML 和可见文本重新判定。
            str_role = classify_final_paragraph(obj_content)  # 当前最终段落角色

            # 计算当前内容在整个正文中的稳定段落序号。
            int_document_paragraph = int_content_start + int_offset  # 当前内容全局段落序号

            # 汇总当前段落相对角色合同的全部偏差。
            list_findings.extend(
                collect_paragraph_role_findings(
                    obj_content,  # 当前最终内容段落
                    str_role,  # 独立判定的段落角色
                    dict_contract,  # 正式样式合同
                    int_document_paragraph,  # 当前内容在验证报告中的位置
                )
            )

    # 返回全部结构化 finding；空列表表示当前样式合同通过。
    return list_findings
