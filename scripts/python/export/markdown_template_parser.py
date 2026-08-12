"""解析导出 Markdown 与模板章节。"""

# 延迟解析类型注解，避免解析模块在导入期要求类型对象齐备。
from __future__ import annotations

# 只导入 Markdown 解析实际使用的常量、正则模块和清洗辅助函数。
from export_runtime_support import (
    INTERNAL_SECTION_PREFIXES,
    RE_BULLET,
    RE_HEADING,
    RE_INLINE_FORMULA,
    RE_ORDERED,
    re,
)

# 模板常量与文本清洗函数共同限定章节和附件的解析语义。
from export_runtime_support import (
    TEMPLATE_HEADING_ALIASES,
    TEMPLATE_SECTION_ORDER,
    TEXT_ATTACHMENT_PLACEHOLDER,
    TEXT_ATTACHMENT_TITLE,
    WORD_HEADING_LEVEL_LIMIT,
    RE_TABLE_SEPARATOR,
)

# 非空行收集沿用运行时共享实现，确保表格与公式证据采用同一清洗边界。
from export_runtime_support import collect_nonempty_stripped_lines

# 清洗 Markdown 行内标记，避免导出到 Word 后残留源语法噪声。
def strip_markdown_inline_text(str_text: str, bool_preserve_inline_math: bool = False) -> str:
    """清洗 Markdown 行内标记并返回纯文本。

    参数：
    - `str_text`：待清洗的原始 Markdown 行文本。
    - `bool_preserve_inline_math`：是否保留 `$...$` 供模板渲染器生成可编辑公式。

    返回：
    - `str`：移除图片、链接和强调标记后的纯文本。

    异常：
    - 无。
    """

    # 先把 Markdown 图片标记替换成可读占位文本，避免图示信息完全丢失。
    str_clean_text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"[图片：\1]", str_text)  # 替换图片语法后的文本

    # 再把 Markdown 链接降级成文字标签，避免把链接语法原样带进 DOCX。
    str_clean_text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", str_clean_text)  # 替换链接语法后的文本

    # 随后去掉行内代码反引号，只保留其中的实际文本内容。
    str_clean_text = re.sub(r"`([^`]+)`", r"\1", str_clean_text)  # 去掉行内代码标记后的文本

    # 仅在纯文本回退路径去掉公式边界；模板路径必须把边界交给可编辑公式渲染器。
    if not bool_preserve_inline_math:

        # 回退导出不具备公式节点能力，去掉源标记但保留表达式文本。
        str_clean_text = RE_INLINE_FORMULA.sub(r"\1", str_clean_text)  # 去掉行内公式标记后的文本

    # 最后去掉常见强调标记，让导出正文保留可阅读文本而非 Markdown 语法。
    str_clean_text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", str_clean_text)  # 去掉强调语法后的文本

    # 返回去除首尾空白后的纯文本，供后续段落构造逻辑继续使用。
    return str_clean_text.strip()

# 把单条 Markdown 表格行转换成线性文本，供最小导出路径稳定保留表格信息。
def normalize_table_row(str_line: str) -> str:
    """把单条 Markdown 表格行转换成线性文本。

    参数：
    - `str_line`：当前 Markdown 表格行原文。

    返回：
    - `str`：当前表格行的线性化文本；分隔行会返回空字符串。

    异常：
    - 无。
    """

    # 先准备单元格纯文本列表，后续逐项记录当前表格行的可读内容。
    list_cells: list[str] = []  # 当前表格行的单元格纯文本列表

    # 顺序遍历当前表格行的原始单元格文本，逐项完成行内 Markdown 清洗。
    for str_cell in str_line.strip().strip("|").split("|"):

        # 把当前单元格清洗成纯文本后收进列表，供后续判断分隔行和拼接正文。
        list_cells.append(strip_markdown_inline_text(str_cell.strip()))

    # 先记录每个单元格是否命中分隔符规则，供整行判断是否为表头分隔线复用。
    list_separator_matches = [bool(RE_TABLE_SEPARATOR.fullmatch(str_cell or "")) for str_cell in list_cells]  # 各单元格的分隔符匹配结果

    # 判断当前行是否只是 `---` 分隔行，避免把分隔符误写入正文。
    bool_is_separator = bool(list_cells) and all(list_separator_matches)  # 当前表格行是否只是分隔符

    # 在当前行仅承担表头分隔职责时直接返回空串，交给上游跳过。
    if bool_is_separator:

        # 用空串通知上游忽略当前分隔行，避免导出无意义横线。
        return ""

    # 把当前表格行拼成 `|` 分隔的线性文本，保留最小可读结构。
    str_table_text = " | ".join(str_cell for str_cell in list_cells if str_cell)  # 当前表格行的线性化文本

    # 将线性化后的表格行文本交回正文解析逻辑继续登记。
    return str_table_text

# 把单行 Markdown 正文登记成线性 block，统一处理标题、列表和普通段落。
def append_text_block(
    list_blocks: list[dict[str, Any]],
    str_line: str,
    str_stripped_line: str,
) -> None:
    """把单行 Markdown 正文登记成线性 block。

    参数：
    - `list_blocks`：当前累计的线性 block 列表。
    - `str_line`：保留原始空白的 Markdown 原始文本行。
    - `str_stripped_line`：去掉首尾空白后的 Markdown 文本行。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 先尝试按 Markdown 标题规则识别当前文本行。
    obj_heading_match = RE_HEADING.match(str_stripped_line)  # 当前文本行的标题匹配结果

    # 在命中标题时直接登记受控层级的标题 block。
    if obj_heading_match:

        # 计算当前标题可映射到 Word 的实际层级，避免超过最小样式集上限。
        int_heading_level = min(len(obj_heading_match.group(1)), WORD_HEADING_LEVEL_LIMIT)  # 当前标题映射后的 Word 层级

        # 清洗标题正文文本，避免行内 Markdown 标记残留到导出结果中。
        str_heading_text = strip_markdown_inline_text(obj_heading_match.group(2))  # 当前标题的纯文本内容

        # 把当前标题加入线性输出序列，供两个导出后端复用同一结构。
        list_blocks.append({"kind": "heading", "text": str_heading_text, "level": int_heading_level})

        # 结束当前函数，避免后续列表和段落分支重复处理标题行。
        return

    # 再按项目符号规则识别当前文本行，覆盖 `-` 和 `*` 样式列表。
    obj_bullet_match = RE_BULLET.match(str_line)  # 当前文本行的无序列表匹配结果

    # 在命中无序列表时登记带项目符号前缀的普通段落 block。
    if obj_bullet_match:

        # 清洗无序列表正文，并补上统一项目符号前缀。
        str_bullet_text = "• " + strip_markdown_inline_text(obj_bullet_match.group(1))  # 当前无序列表的线性化正文

        # 把当前项目符号条目加入线性输出序列。
        list_blocks.append({"kind": "paragraph", "text": str_bullet_text})

        # 结束当前函数，避免后续分支重复处理同一条列表项。
        return

    # 若前面都未命中，这里再判断是否属于带编号的步骤条目。
    obj_ordered_match = RE_ORDERED.match(str_line)  # “1.” 样式步骤条目的匹配结果

    # 在命中有序列表时登记保留序号正文的普通段落 block。
    if obj_ordered_match:

        # 清洗编号列表正文，并保留 `1.` 风格前缀以维持阅读顺序。
        str_ordered_text = strip_markdown_inline_text(str_stripped_line)  # 当前编号列表的线性化正文

        # 把当前编号条目加入线性输出序列。
        list_blocks.append({"kind": "paragraph", "text": str_ordered_text})

        # 结束当前函数，避免后续普通段落逻辑再次写入同一行。
        return

    # 将剩余普通文本行清洗成纯文本段落，供导出正文直接写入。
    str_paragraph_text = strip_markdown_inline_text(str_stripped_line)  # 当前普通正文行的纯文本内容

    # 把当前普通段落加入线性输出序列，形成最终 DOCX 正文内容。
    list_blocks.append({"kind": "paragraph", "text": str_paragraph_text})

# 把已闭合的 fenced code block 转成正文占位和附件正文，避免正文直接嵌入大段源码。
def flush_code_block(
    list_blocks: list[dict[str, Any]],
    list_attachments: list[str],
    list_code_lines: list[str],
) -> None:
    """把已闭合的 fenced code block 转成正文占位和附件正文。

    参数：
    - `list_blocks`：当前累计的线性 block 列表。
    - `list_attachments`：当前累计的附件正文列表。
    - `list_code_lines`：当前代码块收集到的原始正文行列表。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 把代码块正文拼成单段附件文本，供文末附件章节集中收纳。
    str_attachment_text = "\n".join(list_code_lines).strip()  # 当前代码块的附件正文文本

    # 仅在代码块正文非空时才把它记入附件列表。
    if str_attachment_text:

        # 将当前代码块正文收进附件列表，保持与正文出现顺序一致。
        list_attachments.append(str_attachment_text)

    # 在正文当前位置写入附件占位提示，提醒评审人后续人工替换。
    list_blocks.append({"kind": "paragraph", "text": TEXT_ATTACHMENT_PLACEHOLDER})

# 把附件正文统一展开成文末章节，确保两个导出后端看到相同的附件结构。
def append_attachment_blocks(
    list_blocks: list[dict[str, Any]],
    list_attachments: list[str],
) -> None:
    """把附件正文统一展开成文末章节。

    参数：
    - `list_blocks`：当前累计的线性 block 列表。
    - `list_attachments`：正文中摘出的附件正文列表。

    返回：
    - `None`。

    异常：
    - 无。
    """

    # 只有在存在附件正文时才需要追加分页和附件章节。
    if not list_attachments:

        # 在没有附件内容时提前返回，避免正文尾部平白新增附件标题。
        return

    # 先加入分页 block，把附件章节与正文主体视觉分隔开。
    list_blocks.append({"kind": "page_break"})

    # 再写入附件章节标题，帮助评审人快速定位需要人工处理的内容。
    list_blocks.append({"kind": "heading", "text": TEXT_ATTACHMENT_TITLE, "level": 1})

    # 按原正文出现顺序逐项展开附件正文，保持回看路径稳定。
    for int_attachment_index, str_attachment_text in enumerate(list_attachments, start=1):

        # 先登记当前附件的小标题，便于文末逐条核对代码块来源。
        list_blocks.append({"kind": "paragraph", "text": f"附件 {int_attachment_index}"})

        # 再按行展开当前附件正文，避免超长整段影响 Word 可读性。
        for str_attachment_line in str_attachment_text.splitlines():

            # 只在当前附件行有实际内容时才把它写入文末章节。
            if str_attachment_line.strip():

                # 截断过长附件行，避免单行源码把页面版式横向撑开。
                str_trimmed_attachment_line = str_attachment_line[:600]  # 当前附件行的受控文本

                # 把当前附件行作为普通段落加入附件章节。
                list_blocks.append({"kind": "paragraph", "text": str_trimmed_attachment_line})

# 收集并线性化一个连续 Markdown 表格段。
def append_markdown_table_blocks(
    list_lines: list[str],
    int_start_index: int,
    list_blocks: list[dict[str, Any]],
) -> int:
    """把连续表格行追加为普通段落并返回下一行游标。

    参数：
    - `list_lines`：Markdown 原始行列表。
    - `int_start_index`：当前表格段首行索引。
    - `list_blocks`：待追加的线性 block 列表。

    返回：
    - `int`：表格段结束后的下一行索引。
    """

    # 从表格首行开始持续消费连续的竖线表格行。
    int_index = int_start_index  # 当前表格行游标

    # 每次只处理当前连续表格段，遇到普通正文即停止。
    while int_index < len(list_lines) and list_lines[int_index].strip().startswith("|"):

        # 将当前表格行转换成线性文本，纯分隔行会得到空文本。
        str_table_text = normalize_table_row(list_lines[int_index])  # 当前表格行的线性正文

        # 有效表格正文作为普通段落登记，保证回退导出仍可阅读。
        if str_table_text:

            # 保存当前线性化表格行，不改变原表格行顺序。
            list_blocks.append({"kind": "paragraph", "text": str_table_text})

        # 推进到下一原始行，继续确认它是否属于当前表格段。
        int_index += 1  # 当前表格段的下一待检查行

    # 返回首个非表格行位置，供主扫描器继续处理。
    return int_index

# 统一把 Markdown 解析成线性 block 列表，供两个导出后端共用同一份正文结构。
def collect_markdown_blocks(str_markdown: str) -> list[dict[str, Any]]:
    """把 Markdown 解析成线性 block 列表。

    参数：
    - `str_markdown`：待导出的 Markdown 全文。

    返回：
    - `list[MarkdownBlock]`：按正文顺序整理好的线性 block 列表。

    异常：
    - 无。
    """

    # 先准备线性 block 列表，后续会按正文顺序逐项登记内容。
    list_blocks: list[dict[str, Any]] = []  # Markdown 线性 block 列表

    # 把 Markdown 全文按行拆开，便于顺序扫描标题、表格和代码块。
    list_lines = str_markdown.splitlines()  # Markdown 原始行列表

    # 用行游标控制顺序扫描位置，避免复杂递归解析。
    int_index = 0  # 当前顺序扫描到的 Markdown 行号

    # 用状态位记录当前是否位于 fenced code block 内部。
    bool_in_code_block = False  # 当前是否位于代码块内部

    # 用列表暂存当前代码块正文行，待闭合后统一转入附件章节。
    list_code_lines: list[str] = []  # 当前代码块正文暂存列表

    # 用列表暂存所有附件正文，供扫描结束后集中追加到文末。
    list_attachments: list[str] = []  # 正文中摘出的附件正文列表

    # 顺序扫描 Markdown 各行，持续构造受控的线性正文结构。
    while int_index < len(list_lines):

        # 读取当前原始文本行，供后续判断标题、表格和代码块边界。
        str_line = list_lines[int_index]  # 当前原始 Markdown 行

        # 读取当前去首尾空白后的文本行，便于统一判断空行和 fenced code 标记。
        str_stripped_line = str_line.strip()  # 当前去首尾空白后的 Markdown 行

        # 在命中 fenced code block 边界时切换代码块状态。
        if str_stripped_line.startswith("```"):

            # 在代码块闭合点把已收集正文转入附件并写入正文占位。
            if bool_in_code_block:

                # 把当前已闭合代码块刷新成正文占位和附件正文。
                flush_code_block(list_blocks, list_attachments, list_code_lines)

            # 在遇到新的代码块起始边界时清空代码块正文暂存列表。
            else:

                # 为新的代码块正文重新准备暂存列表，避免污染上一段附件内容。
                list_code_lines = []  # 新代码块的正文暂存列表

            # 翻转代码块状态，让下一轮扫描按新状态继续解析正文。
            bool_in_code_block = not bool_in_code_block  # 切换后的代码块状态

            # 跳过当前 fenced code 边界行，继续扫描下一行正文。
            int_index += 1  # 跳过代码块边界后的下一行游标位置

            # 直接进入下一轮扫描，避免边界行继续落入普通正文分支。
            continue

        # 在代码块内部时仅累计原始文本行，不做标题和列表识别。
        if bool_in_code_block:

            # 把当前代码行加入暂存列表，等待代码块闭合后统一写入附件。
            list_code_lines.append(str_line)

            # 推进行游标到下一行，继续读取代码块正文。
            int_index += 1  # 代码块正文继续扫描后的下一行游标位置

            # 直接进入下一轮扫描，避免代码行被误判为普通正文。
            continue

        # 在普通空白行场景下仅跳过当前行，不生成额外段落。
        if not str_stripped_line:

            # 推进行游标到下一行，保持原始空白只承担段落分隔职责。
            int_index += 1  # 空白行跳过后的下一行游标位置

            # 直接进入下一轮扫描，避免空白行进入正文列表。
            continue

        # 在命中 Markdown 表格时收集连续表格行，并按最小线性格式写入正文。
        if str_stripped_line.startswith("|"):

            # 消费当前连续表格段并把游标移动到首个普通正文行。
            int_index = append_markdown_table_blocks(list_lines, int_index, list_blocks)  # 表格段后游标

            # 直接进入下一轮扫描，避免表格段首行再次落入普通正文分支。
            continue

        # 把当前普通文本行登记成标题、列表或普通段落 block。
        append_text_block(list_blocks, str_line, str_stripped_line)

        # 推进行游标到下一行，继续扫描后续 Markdown 内容。
        int_index += 1  # 普通正文处理后的下一行游标位置

    # 在扫描结束时兜底处理未闭合代码块，避免最后一段源码完全丢失。
    if bool_in_code_block:

        # 把末尾未闭合代码块也转入正文占位和附件章节。
        flush_code_block(list_blocks, list_attachments, list_code_lines)

    # 把附件正文统一展开到文末，保持附件结构和顺序稳定。
    append_attachment_blocks(list_blocks, list_attachments)

    # 将完整线性 block 列表交给导出后端继续写入 DOCX。
    return list_blocks

# 去掉 Markdown 标题标记并返回清洗后的标题正文。
def normalize_markdown_heading(str_line: str) -> str:
    """归一化 Markdown 标题文本。

    参数：
    - `str_line`：原始 Markdown 行文本。

    返回：
    - `str`：去掉标题井号和行内标记后的标题正文。

    异常：
    - 无。
    """

    # 先尝试按 Markdown 标题规则识别当前行。
    obj_heading_match = RE_HEADING.match(str_line.strip())  # 当前行的 Markdown 标题匹配结果

    # 不是标题时返回空字符串，供调用方继续按普通正文处理。
    if obj_heading_match is None:

        # 空字符串表示当前行不参与章节切换。
        return ""

    # 清洗标题正文，避免行内 Markdown 标记影响模板章节匹配。
    str_heading_text = strip_markdown_inline_text(obj_heading_match.group(2))  # 当前标题正文文本

    # 返回清洗后的标题正文，供章节归一化逻辑继续判断。
    return str_heading_text

# 把 Markdown 标题映射到正式模板章节名。
def resolve_template_heading(str_heading_text: str) -> str:
    """把 Markdown 标题映射到模板章节名。

    参数：
    - `str_heading_text`：已经清洗过的 Markdown 标题正文。

    返回：
    - `str`：匹配到的模板章节名；无法匹配时返回空字符串。

    异常：
    - 无。
    """

    # 标题完全命中映射时直接返回模板章节名。
    if str_heading_text in TEMPLATE_HEADING_ALIASES:

        # 返回完全匹配得到的模板章节名。
        return TEMPLATE_HEADING_ALIASES[str_heading_text]

    # 处理旧草稿中带空格或半角冒号差异的标题文本。
    str_compact_heading = str_heading_text.replace(" ", "").replace(":", "：")  # 去空格后的标题文本

    # 逐项比较归一化后的标题，兼容旧标题里的轻微格式差异。
    for str_source_heading, str_target_heading in TEMPLATE_HEADING_ALIASES.items():

        # 准备映射源标题的紧凑形式，便于和当前标题比较。
        str_compact_source = str_source_heading.replace(" ", "").replace(":", "：")  # 映射源标题紧凑文本

        # 当前标题和映射源标题紧凑形式相同时返回模板标题。
        if str_compact_heading == str_compact_source:

            # 返回归一化后的模板章节名。
            return str_target_heading

    # 无法匹配模板章节时返回空字符串，让调用方决定是否进入 sidecar。
    return ""

# 判断当前标题是否属于内部审查章节。
def is_internal_heading(str_heading_text: str) -> bool:
    """判断当前标题是否属于内部审查章节。

    参数：
    - `str_heading_text`：已经清洗过的 Markdown 标题正文。

    返回：
    - `bool`：标题属于内部章节时返回 `True`。

    异常：
    - 无。
    """

    # 返回标题是否以受控内部章节前缀开头。
    return str_heading_text.startswith(INTERNAL_SECTION_PREFIXES)

# 把导出 Markdown 拆成模板正文分节和内部 sidecar 文本。
def collect_template_sections(str_markdown: str) -> dict[str, Any]:
    """收集模板正文分节和内部说明。

    参数：
    - `str_markdown`：待导出的 Markdown 全文。

    返回：
    - `dict[str, Any]`：包含模板分节和内部说明行的结构化结果。

    异常：
    - 无。
    """

    # 为每个模板章节准备正文列表，保持最终 DOCX 章节顺序稳定。
    dict_sections: dict[str, list[str]] = {str_heading: [] for str_heading in TEMPLATE_SECTION_ORDER}  # 模板章节正文映射

    # 准备用于 sidecar 的内部说明行列表，承接七至九节等内部内容。
    list_internal_lines: list[str] = []  # sidecar 暂存的内部正文行

    # 当前模板章节名为空时，普通正文会被忽略或转入 sidecar。
    str_current_section = ""  # 当前正在收集的模板章节名

    # 当前是否处于内部审查章节，用来决定后续正文是否进入 sidecar。
    bool_collecting_internal = False  # 是否正在收集内部审查章节

    # 顺序扫描 Markdown 行，按标题边界收集正文。
    for str_line in str_markdown.splitlines():

        # 提取当前行的 Markdown 标题正文；非标题时为空字符串。
        str_heading_text = normalize_markdown_heading(str_line)  # 当前行标题正文

        # 标题行会切换当前正文收集目标。
        if str_heading_text:

            # 内部标题会改写后续正文路由，确保其不进入主 DOCX。
            bool_collecting_internal = is_internal_heading(str_heading_text)  # 当前标题的 sidecar 路由标记

            # 在内部章节命中时记录标题并停止写入主 DOCX。
            if bool_collecting_internal:

                # 将内部章节标题写入 sidecar，便于人工回看被移出的内容。
                list_internal_lines.append(f"## {str_heading_text}")

                # 清空主 DOCX 章节目标，避免内部正文继续进入主交付件。
                str_current_section = ""  # 主 DOCX 章节目标清空

                # 当前标题已经处理完毕，继续扫描下一行。
                continue

            # 尝试把当前标题映射到模板章节名。
            str_mapped_heading = resolve_template_heading(str_heading_text)  # 当前标题对应的模板章节名

            # 在命中模板章节时切换主 DOCX 收集目标。
            if str_mapped_heading:

                # 记录当前主 DOCX 章节目标，后续正文写入该章节。
                str_current_section = str_mapped_heading  # 当前模板章节名

                # 当前标题只承担分节边界职责，不作为正文重复写入。
                continue

            # 未命中模板且非内部章节时清空当前章节，避免误写未知标题正文。
            str_current_section = ""  # 未识别标题后的主 DOCX 章节目标

            # 未识别标题不进入主文档，继续扫描后续行。
            continue

        # 清洗当前普通行，供正文和 sidecar 统一使用。
        str_clean_line = strip_markdown_inline_text(str_line.strip())  # 当前普通行清洗文本

        # 空行只承担段落分隔职责，不进入 DOCX 或 sidecar。
        if not str_clean_line:

            # 跳过空行，保持最终文档内容紧凑。
            continue

        # 内部章节正文进入提交说明 sidecar。
        if bool_collecting_internal:

            # 追加内部说明正文，避免其进入最终 DOCX 主体。
            list_internal_lines.append(str_clean_line)

            # 当前行已进入 sidecar，继续扫描下一行。
            continue

        # 已定位模板章节时，把当前正文写入对应章节。
        if str_current_section:

            # 把正文追加到当前模板章节，供后续按模板顺序输出。
            dict_sections[str_current_section].append(str_clean_line)

    # 返回模板分节和内部说明，供 DOCX 渲染与 sidecar 渲染共同使用。
    return {"sections": dict_sections, "internal_lines": list_internal_lines}

# 把已闭合公式正文追加到当前正式模板章节。
def append_template_formula_block(
    dict_sections: dict[str, list[dict[str, str]]],
    str_current_section: str,
    list_formula_lines: list[str],
    bool_collecting_internal: bool,
) -> None:
    """清洗公式正文并在满足正式章节边界时追加公式块。

    参数：
    - `dict_sections`：模板章节结构化块映射。
    - `str_current_section`：当前正式模板章节名。
    - `list_formula_lines`：当前已闭合公式的原始正文行。
    - `bool_collecting_internal`：当前是否位于内部说明区域。

    返回：
    - `None`。
    """

    # 清理空白公式行并合并为稳定的多行公式文本。
    list_clean_formula_lines = collect_nonempty_stripped_lines(list_formula_lines)  # 规整公式正文行

    # 用换行保持多行公式结构，供公式渲染器继续解析。
    str_formula_text = "\n".join(list_clean_formula_lines)  # 当前公式块正文文本

    # 只有正式章节中的非空公式才能进入交付主稿。
    if str_current_section and str_formula_text and not bool_collecting_internal:

        # 保存公式块，供 DOCX 导出阶段渲染为嵌入式图片。
        dict_sections[str_current_section].append({"kind": "formula", "text": str_formula_text})

# 把 Markdown 拆成可提交模板章节的段落块和公式块，供代理交付版 DOCX 真正嵌入公式。
def collect_template_section_blocks(str_markdown: str) -> dict[str, Any]:
    """收集模板章节的结构化段落块和公式块。

    参数：
    - `str_markdown`：待导出的 Markdown 全文。

    返回：
    - `dict[str, Any]`：包含模板章节块列表和内部说明行的结构化结果。

    异常：
    - 无。
    """

    # 为每个模板章节准备结构化块列表，后续按顺序登记段落或公式块。
    dict_sections: dict[str, list[dict[str, str]]] = {str_heading: [] for str_heading in TEMPLATE_SECTION_ORDER}  # 模板章节块映射

    # 为内部审查 sidecar 暂存正文行，避免这些内容误入正式交付主稿。
    list_internal_lines: list[str] = []  # 内部审查说明行列表

    # 用空字符串表示扫描器尚未命中正式模板章节标题。
    str_current_section = ""  # 当前命中的正式模板章节标题

    # 单独跟踪是否进入内部审查段，供普通正文决定写入主稿还是 sidecar。
    bool_collecting_internal = False  # 内部审查区域状态位

    # 当前是否位于 display-math 公式块内部。
    bool_in_formula_block = False  # 是否正在收集公式块

    # 暂存当前公式块的原始正文行，待闭合后统一写入结构化结果。
    list_formula_lines: list[str] = []  # 当前公式块正文行列表

    # 顺序扫描 Markdown 各行，按章节边界和公式块边界收集结构化内容。
    for str_line in str_markdown.splitlines():

        # 读取当前去首尾空白后的文本，供标题、空行和公式块边界判断复用。
        str_stripped_line = str_line.strip()  # 当前去首尾空白后的文本行

        # 在 display-math 边界行上切换公式块状态。
        if str_stripped_line == "$$":

            # 命中公式块闭合边界时，把已收集公式正文写回当前模板章节。
            if bool_in_formula_block:

                # 清洗并提交当前公式块，内部说明区或无章节公式会被忽略。
                append_template_formula_block(
                    dict_sections,  # 模板章节结构化块映射
                    str_current_section,  # 当前正式模板章节
                    list_formula_lines,  # 当前公式原始正文行
                    bool_collecting_internal,  # 当前内部说明区域状态
                )

                # 公式块正文已消费后清空暂存列表，避免污染后续公式块。
                list_formula_lines = []  # 已清空的公式块正文行列表

            # 切换公式块状态，让扫描器继续处理后续内容。
            bool_in_formula_block = not bool_in_formula_block  # 切换后的公式块状态

            # display-math 边界行本身不进入主稿正文，直接处理下一行。
            continue

        # 在公式块内部时只累计公式正文，不再执行标题或普通段落识别。
        if bool_in_formula_block:

            # 把当前公式正文行加入暂存列表，等待闭合边界统一提交。
            list_formula_lines.append(str_line)

            # 当前行已经作为公式正文处理，继续扫描下一行。
            continue

        # 先归一化当前行标题文本，后续再决定它指向主稿章节还是内部说明。
        str_heading_text = normalize_markdown_heading(str_line)  # 归一化后的标题候选文本

        # 在命中标题时重新决定后续普通行的路由目标。
        if str_heading_text:

            # 先判断当前标题是否属于内部章节。
            bool_collecting_internal = is_internal_heading(str_heading_text)  # 当前标题的内部章节标记

            # 内部标题只进入内部说明，不作为主稿章节继续扩展。
            if bool_collecting_internal:

                # 把内部标题写入内部说明，保留人工回看路径。
                list_internal_lines.append(f"## {str_heading_text}")

                # 清空当前模板章节，避免内部正文误写回主稿。
                str_current_section = ""  # 已清空的当前模板章节名

                # 当前标题已处理完成，继续扫描下一行。
                continue

            # 把当前标题映射到模板章节锚点，无法识别时保持后续普通行不进入主稿。
            str_current_section = resolve_template_heading(str_heading_text)  # 标题命中的模板章节锚点

            # 当前标题只承担章节切换职责，不作为正文再次写入。
            continue

        # 把当前普通行先清成纯文本，再决定它是否进入正式交底书主稿。
        str_clean_line = strip_markdown_inline_text(str_stripped_line, bool_preserve_inline_math=True)  # 保留行内公式边界的正文文本

        # 空行只承担段落分隔职责，不进入主稿或内部说明。
        if not str_clean_line:

            # 跳过空行，保持主稿段落列表紧凑。
            continue

        # 内部章节正文统一进入内部说明，不进入正式交付主稿。
        if bool_collecting_internal:

            # 把当前内部说明行追加到内部说明列表。
            list_internal_lines.append(str_clean_line)

            # 当前行已经写入内部说明，继续扫描下一行。
            continue

        # 只有在已经定位到模板章节时才把当前普通行写入主稿章节。
        if str_current_section:

            # 把当前普通段落写入主稿章节，供 DOCX 导出逐段写入。
            dict_sections[str_current_section].append({"kind": "paragraph", "text": str_clean_line})

    # 返回模板章节结构化块和内部说明，供严格模板导出复用。
    return {"sections": dict_sections, "internal_lines": list_internal_lines}

# 统计模板章节块中的公式数量，供最终 DOCX 媒体数量校验复用。
def count_formula_blocks(dict_sections: dict[str, list[dict[str, str]]]) -> int:
    """统计模板章节块中的公式数量。

    参数：
    - `dict_sections`：模板章节到结构化块列表的映射。

    返回：
    - `int`：所有章节中公式块的总数。

    异常：
    - 无。
    """

    # 逐章节汇总 `formula` 类型块数量，供 DOCX 媒体校验复用。
    return sum(
        1
        for list_blocks in dict_sections.values()
        for dict_block in list_blocks
        if dict_block.get("kind") == "formula"
    )

# 收集当前案件可用于 DOCX 正文嵌图的 PNG 附图路径。
def collect_delivery_figure_image_paths(path_case_dir: Path | None) -> list[Path]:
    """收集可用于 DOCX 嵌图的 PNG 附图路径。

    参数：
    - `path_case_dir`：当前案件目录路径；为空时返回空列表。

    返回：
    - `list[Path]`：按稳定顺序排列的 PNG 附图路径列表。

    异常：
    - 无。
    """

    # 缺少案件目录时无法定位正式附图目录，直接返回空列表。
    if path_case_dir is None:

        # 空列表表示当前导出不具备可用附图资产。
        return []

    # 固定正式附图目录路径，保持与案件目录合同一致。
    path_figures_dir = path_case_dir / "05_figures"  # 正式附图目录路径

    # 在附图目录缺失时直接返回空列表，让导出器只输出正文与公式。
    if not path_figures_dir.exists():

        # 空列表表示当前案件尚未生成可嵌入 DOCX 的附图资产。
        return []

    # 先按默认产品承诺的两张正式附图顺序收集 PNG 资产。
    list_default_paths = [  # 默认正式附图 PNG 路径列表
        path_figures_dir / "图1_方法流程图.png",  # 方法流程图的 PNG 交付路径
        path_figures_dir / "图2_系统模块图.png",  # 系统模块图的 PNG 交付路径
    ]

    # 仅保留已经真实落盘的默认 PNG 附图，避免把不存在的文件写进返回结果。
    list_existing_default_paths = [path_item for path_item in list_default_paths if path_item.exists()]  # 已存在的默认 PNG 附图路径列表

    # 在默认两张附图已经存在时直接按固定顺序返回。
    if list_existing_default_paths:

        # 返回默认附图路径列表，保证 DOCX 正文中的嵌图顺序稳定。
        return list_existing_default_paths

    # 默认文件名缺失时回退到扫描全部 `图*.png` 文件，兼容后续扩展附图场景。
    return sorted(path_figures_dir.glob("图*.png"))
