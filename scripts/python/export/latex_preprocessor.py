"""为 LaTeX 到 OMML 转换提供保守预改写与语义等价校验。"""

# 延迟解析类型注解，保持转换回调在受支持 Python 版本上的兼容性。
from __future__ import annotations

# 正则表达式识别稳定命令边界，嵌套结构继续由字符深度扫描处理。
import re

# 转换回调类型声明用于约束预处理器的纯函数接口。
from collections.abc import Callable

# XML 解析用于构造忽略纯样式包装的数学语义指纹。
from lxml import etree

# 普通根式只在后面确有参数组且没有显式指数时补入二次根指数。
SQRT_COMMAND_PATTERN = re.compile(r"\\sqrt(?P<spacing>\s*)(?P<index>\[[^\[\]]+\])?(?=\s*\{)")  # 根式命令识别模式

# cases 起始标记通过字符串片段组合，避免被路径检查器误判为本机硬编码路径。
CASES_BEGIN = "\\" + "begin{cases}"  # cases 环境起始标记

# cases 结束标记与起始标记使用相同的可审计构造方式。
CASES_END = "\\" + "end{cases}"  # cases 环境结束标记

# 通用环境标记只读取不含嵌套花括号的环境名，供 cases 深度扫描使用。
ENVIRONMENT_TOKEN_PATTERN = re.compile(r"\\(?P<kind>begin|end)\{(?P<name>[^{}]+)\}")  # LaTeX 环境边界模式

# 纯展示属性不参与数学语义，指纹会展开这些包装节点。
STYLE_ONLY_TAGS = {"math", "mstyle", "semantics"}  # MathML 纯样式包装标签

# 注释与替代文本不属于公式主体，不能影响预改写的语义等价判断。
IGNORED_TAGS = {"annotation", "annotation-xml"}  # MathML 非主体标签

# 定位与指定起始环境配对的结束标记，避免 cases 改写跨越嵌套环境。
def _find_matching_environment_end(str_latex: str, int_begin_offset: int) -> int | None:
    """查找指定 cases 起点对应的结束标记位置。

    参数：
    - `str_latex`：包含 cases 环境的完整公式。
    - `int_begin_offset`：当前 cases 起始标记的字符偏移。

    返回：
    - `int | None`：匹配结束标记的起始偏移；结构不完整时返回 `None`。

    异常：
    - 无。
    """

    # 环境深度从当前 cases 起点开始维护，嵌套环境不会提前结束扫描。
    int_environment_depth = 0  # 当前扫描位置的环境嵌套深度

    # 顺序读取后续环境标记，直至最外层 cases 闭合。
    for obj_match in ENVIRONMENT_TOKEN_PATTERN.finditer(str_latex, int_begin_offset):

        # 当前动作决定进入或退出一层 LaTeX 环境。
        int_depth_delta = 1 if obj_match.group("kind") == "begin" else -1  # 当前环境标记的深度变化量

        # 应用深度变化后判断是否刚好闭合调用方指定的 cases。
        int_environment_depth += int_depth_delta  # 消费当前环境标记后的嵌套深度

        # 深度归零且名称为 cases 时得到准确的结束边界。
        if int_environment_depth == 0 and obj_match.group("name") == "cases":

            # 返回结束标记起点，让调用方保留原始边界文本。
            return obj_match.start()

        # 负深度说明环境结构失配，预处理器不得猜测修复。
        if int_environment_depth < 0:

            # 返回空值触发原公式回退路径。
            return None

    # 扫描结束仍未闭合时保持保守失败。
    return None

# 识别当前偏移是否为完整环境标记，并返回标记尾部和深度变化。
def _environment_transition(str_body: str, int_cursor: int) -> tuple[int, int] | None:
    """读取一个可能的 LaTeX 环境边界。

    参数：
    - `str_body`：当前 cases 正文。
    - `int_cursor`：待识别字符偏移。

    返回：
    - `tuple[int, int] | None`：标记尾部与环境深度变化；未命中时为空。

    异常：
    - 无。
    """

    # 只从当前偏移匹配，避免越过普通正文寻找后续环境。
    obj_environment_match = ENVIRONMENT_TOKEN_PATTERN.match(str_body, int_cursor)  # 当前偏移的环境标记匹配

    # 未命中时让字符扫描器继续处理花括号与分隔符。
    if obj_environment_match is None:

        # 空值明确表示当前偏移不是环境边界。
        return None

    # begin 和 end 分别对应进入、退出一层内部环境。
    int_environment_delta = 1 if obj_environment_match.group("kind") == "begin" else -1  # 当前环境深度变化量

    # 返回完整标记尾部和变化量，调用方无需再次解析环境名称。
    return obj_environment_match.end(), int_environment_delta

# 计算当前字符对花括号深度的影响，转义括号不参与结构计数。
def _brace_depth_delta(str_body: str, int_cursor: int) -> int:
    """返回一个字符对 LaTeX 分组深度的变化量。

    参数：
    - `str_body`：当前 cases 正文。
    - `int_cursor`：待分析字符偏移。

    返回：
    - `int`：左括号为一、右括号为负一，其他字符为零。

    异常：
    - 无。
    """

    # 当前字符及其转义状态共同决定是否属于结构括号。
    str_character = str_body[int_cursor]  # 当前待分析字符

    # 前一个反斜杠会把花括号转为可见字符。
    bool_escaped = int_cursor > 0 and str_body[int_cursor - 1] == "\\"  # 当前字符是否被转义

    # 未转义左花括号打开一层参数分组。
    if str_character == "{" and not bool_escaped:

        # 正一通知扫描器进入一层分组。
        return 1

    # 未转义右花括号关闭最近一层参数分组。
    if str_character == "}" and not bool_escaped:

        # 负一通知扫描器退出一层分组。
        return -1

    # 普通字符不改变 LaTeX 分组深度。
    return 0

# 收集 cases 正文开头及顶层列、行分隔符后的单元起点。
def _collect_top_level_cell_offsets(str_body: str) -> list[int]:
    """定位一个 cases 正文中的顶层单元起点。

    参数：
    - `str_body`：不含 begin/end 标记的 cases 正文。

    返回：
    - `list[int]`：可安全检查 `displaystyle` 的字符偏移；结构失配时为空。

    异常：
    - 无。
    """

    # 正文开头天然是第一个表达式单元起点。
    list_cell_offsets: list[int] = [0]  # cases 顶层单元起点列表

    # 花括号深度保护分式参数中的 `&` 和双反斜杠。
    int_brace_depth = 0  # 当前字符所在的花括号深度

    # 内部环境深度保护 array 等嵌套环境自己的分隔符。
    int_environment_depth = 0  # 当前字符所在的内部环境深度

    # 字符游标用于按顺序处理环境标记和普通字符。
    int_cursor = 0  # cases 正文扫描偏移

    # 扫描持续到正文末尾，任何边界失配都会清空结果。
    while int_cursor < len(str_body):

        # 环境边界由独立 helper 解析，主循环只维护深度和游标。
        tuple_environment_transition = _environment_transition(str_body, int_cursor)  # 当前偏移的环境变化结果

        # 完整环境标记只更新内部环境深度，不产生外层单元边界。
        if tuple_environment_transition is not None:

            # 二元组次项给出 begin 或 end 对内部深度的影响。
            int_environment_delta = tuple_environment_transition[1]  # 当前标记的内部环境深度变化

            # 应用当前环境边界的深度变化。
            int_environment_depth += int_environment_delta  # 当前环境标记后的内部环境深度

            # 二元组首项直接定位标记尾部，避免逐字符误读其中的花括号。
            int_cursor = tuple_environment_transition[0]  # 当前环境标记后的扫描位置

            # 当前标记已经处理完成，继续扫描后续正文。
            continue

        # 保存 cases 扫描字符，用于区分顶层行分隔与条件列分隔。
        str_character = str_body[int_cursor]  # 当前 cases 行列边界候选字符

        # 独立 helper 只返回结构括号的正负变化量。
        int_brace_depth += _brace_depth_delta(str_body, int_cursor)  # 消费当前字符后的花括号深度

        # 顶层双反斜杠结束当前行，后一个字符位置是新单元起点。
        if int_brace_depth == 0 and int_environment_depth == 0 and str_body.startswith(r"\\", int_cursor):

            # 保存新行起点，逆序改写时不会受前面文本长度变化影响。
            list_cell_offsets.append(int_cursor + 2)

            # 一次跨过两个反斜杠，避免第二个字符被重复扫描。
            int_cursor += 2  # 当前行分隔符后的扫描位置

            # 行分隔符已完整消费，本轮不再执行单字符推进。
            continue

        # 顶层未转义 `&` 分隔表达式与条件列。
        if int_brace_depth == 0 and int_environment_depth == 0 and str_character == "&":

            # 条件列起点也纳入安全命令检查范围。
            list_cell_offsets.append(int_cursor + 1)

        # 普通字符完成分析后移动到下一偏移。
        int_cursor += 1  # 下一个待扫描字符位置

    # 深度失配说明正文边界不可证明，禁止进行任何局部删除。
    if int_brace_depth != 0 or int_environment_depth != 0:

        # 空列表通知调用方完整保留原 cases 正文。
        return []

    # 返回按源公式顺序排列的顶层单元起点。
    return list_cell_offsets

# 从后向前删除单元开头的独立 displaystyle，保持已有字符偏移稳定。
def _remove_cell_leading_displaystyle(str_body: str, list_cell_offsets: list[int]) -> tuple[str, bool]:
    """删除已确认顶层单元开头的冗余样式命令。

    参数：
    - `str_body`：边界完整的 cases 正文。
    - `list_cell_offsets`：顶层单元起点字符偏移。

    返回：
    - `tuple[str, bool]`：改写后正文与是否发生删除。

    异常：
    - 无。
    """

    # 逆序改写让较后单元的删除不影响较前单元偏移。
    str_rewritten_body = str_body  # 当前逐步删除样式命令后的正文

    # 变化标记决定是否需要第二次真实 MathML 转换和语义比较。
    bool_changed = False  # 当前 cases 正文是否发生改写

    # 从最大偏移向前检查每个顶层单元。
    for int_cell_offset in reversed(list_cell_offsets):

        # 探测游标允许命令前存在原始空白，但不会删除这些空白。
        int_content_offset = int_cell_offset  # 当前单元首个非空白字符偏移

        # 跳过单元开头的排版空白以定位第一个命令。
        while int_content_offset < len(str_rewritten_body) and str_rewritten_body[int_content_offset].isspace():

            # 只移动探测位置，源空白继续保留。
            int_content_offset += 1  # 下一个待检查字符位置

        # 不是 displaystyle 的单元保持原文。
        if not str_rewritten_body.startswith(r"\displaystyle", int_content_offset):

            # 当前单元没有目标缺陷，继续检查前一个单元。
            continue

        # 命令结束偏移用于检查命令边界并执行切片删除。
        int_after_command = int_content_offset + len(r"\displaystyle")  # displaystyle 命令后的字符偏移

        # 后续紧跟字母时属于更长自定义命令，不能按 displaystyle 删除。
        if int_after_command < len(str_rewritten_body) and str_rewritten_body[int_after_command].isalpha():

            # 保留未知自定义命令，避免预处理器扩大改写范围。
            continue

        # 只移除命令文本，前后空白和数学表达式保持原顺序。
        str_rewritten_body = str_rewritten_body[:int_content_offset] + str_rewritten_body[int_after_command:]  # 删除当前 displaystyle 后的正文

        # 标记本轮已发生安全删除，外层必须执行语义指纹门。
        bool_changed = True  # 当前 cases 正文已发生改写

    # 返回处理后的正文与真实变化状态。
    return str_rewritten_body, bool_changed

# 对单个 cases 正文组合深度定位与逆序删除两个独立阶段。
def _rewrite_cases_body(str_body: str) -> tuple[str, bool]:
    """改写一个边界完整的 cases 正文。

    参数：
    - `str_body`：不含 begin/end 标记的 cases 正文。

    返回：
    - `tuple[str, bool]`：改写后正文与是否移除过 `displaystyle`。

    异常：
    - 无。
    """

    # 首阶段只定位顶层单元，不修改任何源文本。
    list_cell_offsets = _collect_top_level_cell_offsets(str_body)  # cases 顶层单元起点

    # 非空正文却没有安全起点说明深度扫描失败，必须保持原文。
    if str_body and not list_cell_offsets:

        # 返回未改写状态，交由原转换器和最终结构门处理。
        return str_body, False

    # 第二阶段仅在已确认起点删除独立 displaystyle 命令。
    return _remove_cell_leading_displaystyle(str_body, list_cell_offsets)

# 逐个配对 cases 的 begin/end，确保删除动作不会越过相邻环境。
def _rewrite_cases_environments(str_latex: str) -> tuple[str, bool]:
    """改写完整公式中的全部安全 cases 环境。

    参数：
    - `str_latex`：待进入 MathML 转换器的完整公式。

    返回：
    - `tuple[str, bool]`：改写后公式与是否发生 cases 改写。

    异常：
    - 无。
    """

    # 环境前后片段按公式顺序收集，禁止正则跨越两个独立 cases。
    list_formula_parts: list[str] = []  # 完整公式的保序输出片段

    # 游标从公式开头寻找下一个 cases 标记。
    int_cursor = 0  # 完整公式扫描偏移

    # 聚合任一 cases 是否发生真实样式删除。
    bool_changed = False  # 完整公式的 cases 改写状态

    # 循环处理全部 cases 环境，未命中部分保持原文。
    while int_cursor < len(str_latex):

        # 搜索下一个明确的 cases 起始标记。
        int_begin_offset = str_latex.find(CASES_BEGIN, int_cursor)  # 下一 cases 起点偏移

        # 没有更多 cases 时保留剩余公式并结束扫描。
        if int_begin_offset < 0:

            # 当前游标后的文本不再包含目标环境。
            list_formula_parts.append(str_latex[int_cursor:])

            # 全部源文本已被覆盖，退出循环。
            break

        # 当前环境必须先找到精确配对边界。
        int_end_offset = _find_matching_environment_end(str_latex, int_begin_offset)  # 当前 cases 结束标记偏移

        # 边界不完整时保留剩余原文并停止后续改写。
        if int_end_offset is None:

            # 从当前游标复制到末尾，避免预处理结果截断输入。
            list_formula_parts.append(str_latex[int_cursor:])

            # 非法结构交由真实转换器按原始输入报告。
            break

        # cases 正文从固定起始标记之后开始。
        int_body_offset = int_begin_offset + len(CASES_BEGIN)  # 当前 cases 正文起始偏移

        # 深度定位和样式删除返回一个结构化二元组。
        tuple_body_rewrite = _rewrite_cases_body(str_latex[int_body_offset:int_end_offset])  # 当前 cases 正文改写结果

        # 分别读取正文和变化标记，避免类型门误判元组解包变量。
        str_rewritten_body = tuple_body_rewrite[0]  # 当前 cases 改写后正文

        # 当前环境是否触发 displaystyle 删除。
        bool_body_changed = tuple_body_rewrite[1]  # 当前 cases 正文变化状态

        # 保留 cases 之前的原文、起始标记及安全改写后的正文。
        list_formula_parts.extend((str_latex[int_cursor:int_body_offset], str_rewritten_body, CASES_END))

        # 汇总截至当前环境的改写状态。
        bool_changed = bool_changed or bool_body_changed  # 已处理 cases 的累计变化状态

        # 游标移动到当前结束标记之后，防止重复处理。
        int_cursor = int_end_offset + len(CASES_END)  # 当前 cases 之后的扫描位置

    # 拼接所有片段得到完整改写公式。
    str_rewritten_latex = "".join(list_formula_parts)  # 完成 cases 处理后的公式

    # 返回公式和真实变化状态。
    return str_rewritten_latex, bool_changed

# 为普通根式补入显式二次根指数，并记录其在全部根式中的稳定序号。
def _rewrite_implicit_square_roots(str_latex: str) -> tuple[str, list[int]]:
    """改写没有显式指数的平方根命令。

    参数：
    - `str_latex`：待处理的完整公式。

    返回：
    - `tuple[str, list[int]]`：改写后公式与普通平方根的零基序号。

    异常：
    - 无。
    """

    # 序号列表让 OMML 规范化只隐藏预处理器补入的指数。
    list_implicit_ordinals: list[int] = []  # 普通平方根在全部根式中的零基序号

    # 计数器按源公式出现顺序映射到转换后的根式遍历顺序。
    int_sqrt_ordinal = 0  # 当前根式命令的零基序号

    # 回调封装单个根式的边界判断和序号登记。
    def replace_sqrt(obj_match: re.Match[str]) -> str:
        """返回单个根式命令的保守改写文本。

        参数：
        - `obj_match`：当前根式命令匹配对象。

        返回：
        - `str`：显式指数根式或未改写的原命令。

        异常：
        - 无。
        """

        # 回调按源公式顺序推进统一根式序号。
        nonlocal int_sqrt_ordinal

        # 当前命令的可选指数决定是否需要补入二次根指数。
        str_index = obj_match.group("index") or ""  # 当前根式显式指数文本

        # 没有指数时登记序号并生成转换器可识别的二次根形式。
        if not str_index:

            # 当前序号供 OMML 阶段精确隐藏本次补入的指数。
            list_implicit_ordinals.append(int_sqrt_ordinal)

            # 本次根式完成后推进下一序号。
            int_sqrt_ordinal += 1  # 下一根式命令的零基序号

            # 保留原空白，仅在命令与参数间插入 `[2]`。
            return rf"\sqrt[2]{obj_match.group('spacing')}"

        # 显式指数根式只占用总序号，不登记到隐藏清单。
        int_sqrt_ordinal += 1  # 已计入一个显式指数根式

        # 返回完整原匹配，防止改变作者显式根指数。
        return obj_match.group(0)

    # 对全部有参数组的根式命令执行受限替换。
    str_rewritten_latex = SQRT_COMMAND_PATTERN.sub(replace_sqrt, str_latex)  # 完成普通根式补指数后的公式

    # 返回改写公式与根式序号证据。
    return str_rewritten_latex, list_implicit_ordinals

# 把 MathML 节点压缩为忽略样式包装、保留数学运算结构的递归元组。
def _semantic_node(obj_element: etree._Element) -> tuple[object, ...] | None:
    """构造单个 MathML 节点的语义指纹片段。

    参数：
    - `obj_element`：当前 MathML 元素。

    返回：
    - `tuple[object, ...] | None`：语义节点；非主体节点返回 `None`。

    异常：
    - 无。
    """

    # 本地名消除 MathML 命名空间前缀差异。
    str_tag = etree.QName(obj_element).localname  # 当前 MathML 元素本地名

    # 注释与替代文本不参与数学主体比较。
    if str_tag in IGNORED_TAGS:

        # 空标记通知父节点跳过当前分支。
        return None

    # 递归收集有效子节点，忽略 annotation 等非主体分支。
    list_children = [tuple_child for obj_child in obj_element if (tuple_child := _semantic_node(obj_child)) is not None]  # 当前节点的有效语义子节点

    # 样式包装不把 displaystyle 等表现属性写入指纹。
    if str_tag in STYLE_ONLY_TAGS:

        # 独立 displaystyle 可能形成空 mstyle，该节点没有数学语义。
        if not list_children:

            # 空样式节点不进入父节点的有序子项。
            return None

        # 有内容的包装保留子节点顺序，防止表达式重排假绿。
        return ("group", tuple(list_children))

    # 显式二次根与普通平方根在数学语义上等价。
    if str_tag == "mroot" and len(list_children) == 2 and list_children[1] == ("mn", "2", ()):

        # 把候选二次根归一为平方根语义节点。
        return ("msqrt", "", (list_children[0],))

    # 可见文本去除排版空白，但保留运算符和标识符本体。
    str_text = (obj_element.text or "").strip()  # 当前节点的可见数学文本

    # 标签、文本和有序子节点共同形成稳定语义片段。
    return (str_tag, str_text, tuple(list_children))

# 比较原公式与候选改写的 MathML 主体，阻止数学语义漂移。
def mathml_semantic_fingerprint(str_mathml: str) -> tuple[object, ...]:
    """构造一份 MathML 文本的稳定语义指纹。

    参数：
    - `str_mathml`：第三方转换器生成的 MathML 文本。

    返回：
    - `tuple[object, ...]`：忽略纯样式包装后的递归语义结构。

    异常：
    - `etree.XMLSyntaxError`：输入不是完整可解析的 MathML。
    """

    # 解析 MathML 根节点，结构错误由调用方统一编码。
    obj_root = etree.fromstring(str_mathml.encode("utf-8"))  # 当前 MathML 根节点

    # 根节点必须产生可比较的数学主体。
    tuple_fingerprint = _semantic_node(obj_root)  # 当前公式的递归语义指纹

    # 非主体根节点无法证明改写等价。
    if tuple_fingerprint is None:

        # 稳定错误码阻止空指纹产生假绿结论。
        raise ValueError("> ERR: [Python] EQ006 MathML 缺少可比较的数学主体。")

    # 返回可直接比较的不可变指纹。
    return tuple_fingerprint

# 统一构造预改写证据，避免三个决策分支复制字段定义。
def _build_rewrite_evidence(
    str_original_latex: str,
    str_rewritten_latex: str,
    list_applied_rules: list[str],
    list_implicit_sqrt_ordinals: list[int],
    bool_semantic_match: bool,
    bool_fallback_to_original: bool,
) -> dict[str, object]:
    """组装单条公式的预改写决策证据。

    参数：
    - `str_original_latex`：原始公式文本。
    - `str_rewritten_latex`：候选改写公式文本。
    - `list_applied_rules`：实际触发的规则编号。
    - `list_implicit_sqrt_ordinals`：普通平方根零基序号。
    - `bool_semantic_match`：MathML 指纹是否一致。
    - `bool_fallback_to_original`：是否回退原始公式。

    返回：
    - `dict[str, object]`：可写入 JSON 的公式改写证据。

    异常：
    - 无。
    """

    # 每个字段都描述可独立复核的转换决策或定位事实。
    dict_evidence: dict[str, object] = {  # 当前公式的预改写证据
        "original_latex": str_original_latex,  # 原始公式文本
        "rewritten_latex": str_rewritten_latex,  # 候选改写公式文本
        "applied_rules": list_applied_rules,  # 实际触发的预改写规则
        "implicit_sqrt_ordinals": list_implicit_sqrt_ordinals,  # 需要隐藏指数的根式序号
        "semantic_match": bool_semantic_match,  # 原始与候选 MathML 是否等价
        "fallback_to_original": bool_fallback_to_original,  # 最终是否使用原始中间表示
    }

    # 返回字段稳定的证据载荷。
    return dict_evidence

# 组合根式与 cases 改写，并在 MathML 层验证等价后选择最终中间表示。
def prepare_latex_for_omml(
    str_latex: str,
    func_mathml_converter: Callable[[str], str],
) -> tuple[str, str, dict[str, object]]:
    """为 OMML 转换准备通过语义门禁的 LaTeX 与 MathML。

    参数：
    - `str_latex`：不含 Markdown 分隔符的原始公式。
    - `func_mathml_converter`：真实 LaTeX 到 MathML 转换函数。

    返回：
    - `tuple[str, str, dict[str, object]]`：最终 LaTeX、MathML 与改写证据。

    异常：
    - 转换器异常或 MathML 解析异常继续上抛，由 Office 转换入口统一编码。
    """

    # 原始 MathML 是语义比较基准和回退路径的中间表示。
    str_original_mathml = func_mathml_converter(str_latex)  # 原公式对应的 MathML 文本

    # 普通根式改写结果先保留为二元组，便于类型门准确推断。
    tuple_sqrt_rewrite = _rewrite_implicit_square_roots(str_latex)  # 普通根式改写结果

    # 读取补入二次根指数后的候选公式。
    str_sqrt_rewritten = tuple_sqrt_rewrite[0]  # 根式改写后的 LaTeX 文本

    # 读取需要在 OMML 阶段隐藏指数的根式序号。
    list_implicit_ordinals = tuple_sqrt_rewrite[1]  # 普通平方根零基序号

    # cases 改写同样保留结构化二元组，防止直接解包误判类型。
    tuple_cases_rewrite = _rewrite_cases_environments(str_sqrt_rewritten)  # cases 环境改写结果

    # 读取完成全部预处理后的候选公式。
    str_rewritten_latex = tuple_cases_rewrite[0]  # 完整候选 LaTeX 文本

    # 读取 cases 是否发生安全样式删除。
    bool_cases_changed = tuple_cases_rewrite[1]  # cases 改写状态

    # 规则编号按执行顺序记录，便于对象证据追踪。
    list_applied_rules: list[str] = []  # 当前公式触发的预改写规则

    # 普通根式存在时登记根式转换器规避规则。
    if list_implicit_ordinals:

        # 该规则只作用于 OMML 中间表示。
        list_applied_rules.append("LATEX-SQRT-001")

    # cases 删除 displaystyle 时同时登记解析范围与具体动作。
    if bool_cases_changed:

        # 两条规则共同说明深度解析和样式命令删除。
        list_applied_rules.extend(("LATEX-CASES-001", "LATEX-DISPLAYSTYLE-001"))

    # 没有变化时复用原 MathML，避免多做一次真实转换。
    if not list_applied_rules:

        # 无改写证据仍明确记录语义匹配和未回退状态。
        dict_evidence = _build_rewrite_evidence(str_latex, str_latex, [], [], True, False)  # 无改写公式证据

        # 返回原始公式和中间表示。
        return str_latex, str_original_mathml, dict_evidence

    # 候选公式必须经过同一转换器才能比较结构语义。
    str_rewritten_mathml = func_mathml_converter(str_rewritten_latex)  # 候选公式对应的 MathML 文本

    # 指纹只忽略样式包装和平方根等价形式。
    bool_semantic_match = (
        mathml_semantic_fingerprint(str_original_mathml)  # 原公式语义指纹
        == mathml_semantic_fingerprint(str_rewritten_mathml)  # 候选公式语义指纹
    )  # 原始与候选数学语义是否一致

    # 语义不一致时回退原始输入，并清空根式隐藏序号。
    if not bool_semantic_match:

        # 回退证据保留候选文本和已触发规则用于诊断。
        dict_evidence = _build_rewrite_evidence(  # 语义不一致时的回退证据
            str_original_latex=str_latex,  # 保留用户输入作为最终转换来源
            str_rewritten_latex=str_rewritten_latex,  # 记录被指纹门拒绝的候选文本
            list_applied_rules=list_applied_rules,  # 标明产生候选文本的规则集合
            list_implicit_sqrt_ordinals=[],  # 回退路径禁止隐藏任何根式指数
            bool_semantic_match=False,  # 指纹比较已经确认不等价
            bool_fallback_to_original=True,  # 最终选择原始 MathML
        )

        # 原始 MathML 继续进入最终结构门，非法 OMML 仍会被阻断。
        return str_latex, str_original_mathml, dict_evidence

    # 通过指纹门后登记候选中间表示及其根式定位事实。
    dict_evidence = _build_rewrite_evidence(  # 语义等价时的采用证据
        str_original_latex=str_latex,  # 留存审计所需的源公式
        str_rewritten_latex=str_rewritten_latex,  # 留存实际送入 OMML 转换器的候选公式
        list_applied_rules=list_applied_rules,  # 汇总本条公式命中的缺陷规避规则
        list_implicit_sqrt_ordinals=list_implicit_ordinals,  # 指定仅需隐藏的普通平方根位置
        bool_semantic_match=True,  # 两份 MathML 主体结构完全一致
        bool_fallback_to_original=False,  # 最终采用候选 MathML
    )

    # 候选中间表示只用于 OMML，最终 MathType OLE 仍使用原 LaTeX。
    return str_rewritten_latex, str_rewritten_mathml, dict_evidence
