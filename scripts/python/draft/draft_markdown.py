"""渲染交底书 Markdown 正文与内部审查文本。"""

# 延迟解析渲染函数类型注解，保持拆分模块兼容。
from __future__ import annotations

# 标准库提供公式匹配、路径与动态载荷类型。
import re
from pathlib import Path
from typing import Any

# 文档写入边界复用证据模块的合同工件生成函数。
from readable_patent_draft_evidence import write_draft_contract_artifacts

# 预编译行间公式匹配规则，供本地研究材料抽取复用。
RE_DISPLAY_FORMULA_BLOCK = re.compile(r"\$\$(.*?)\$\$", flags=re.DOTALL)  # 行间公式块匹配规则

# 把方法步骤整理成正文 4.2.2 小节可直接拼接的行列表。
def build_step_markdown_lines(list_steps: list[dict[str, str]]) -> list[str]:
    """构建方法步骤 Markdown 行列表。

    参数：
    - `list_steps`：结构化方法步骤列表。

    返回：
    - `list[str]`：正文 4.2.2 小节可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备步骤 Markdown 行列表，后续按方法步骤顺序依次追加说明块。
    list_step_lines: list[str] = []  # 方法步骤 Markdown 行列表

    # 逐项遍历方法步骤，按固定顺序输出摘要、条件、输入、动作和输出说明。
    for dict_step in list_steps:

        # 把当前步骤拆成固定说明块，保持 4.2.2 小节的阅读节奏稳定。
        list_step_lines.extend(
            [
                f"{dict_step['id']}：{dict_step['summary']}",
                "",
                f"本步骤的触发条件为：{dict_step['condition']}",
                f"输入为：{dict_step['input']}",
                f"技术动作为：{dict_step['action']}",
                f"输出为：{dict_step['output']}",
                "",
            ]
        )

    # 返回方法步骤 Markdown 行列表，供正文渲染阶段直接拼接。
    return list_step_lines

# 把系统模块整理成正文 4.2.1 小节可直接拼接的行列表。
def build_module_markdown_lines(list_modules: list[dict[str, str]]) -> list[str]:
    """构建系统模块 Markdown 行列表。

    参数：
    - `list_modules`：结构化系统模块列表。

    返回：
    - `list[str]`：正文 4.2.1 小节可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备系统模块 Markdown 行列表，后续按模块顺序依次追加条目。
    list_module_lines: list[str] = []  # 系统模块 Markdown 行列表

    # 逐条生成系统模块说明，保持模块名称和功能表述的稳定顺序。
    for int_index, dict_module in enumerate(list_modules, start=1):

        # 追加当前模块条目文本，供正文 4.2.1 小节直接写入模块清单。
        list_module_lines.append(f"{int_index}. {dict_module['name']}，用于 {dict_module['function']}")

    # 返回系统模块 Markdown 行列表，供正文渲染阶段直接拼接。
    return list_module_lines

# 把技术效果整理成正文 4.3 小节可直接拼接的行列表。
def build_effect_markdown_lines(list_effects: list[str]) -> list[str]:
    """构建技术效果 Markdown 行列表。

    参数：
    - `list_effects`：技术效果条目列表。

    返回：
    - `list[str]`：正文 4.3 小节可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备技术效果 Markdown 行列表，后续按条目顺序依次追加编号行。
    list_effect_lines: list[str] = []  # 技术效果 Markdown 行列表

    # 逐条生成技术效果编号行，保持效果条目在正文中的稳定顺序。
    for int_index, str_effect in enumerate(list_effects, start=1):

        # 追加当前技术效果编号行，供正文 4.3 小节直接复用。
        list_effect_lines.append(f"{int_index}. {str_effect.rstrip('。；;')}。")

    # 返回技术效果 Markdown 行列表，供正文渲染阶段直接拼接。
    return list_effect_lines

# 从研究根目录的本地材料中提取 display-math 公式块，保证正式交付源稿可追溯公式来源。
def collect_formula_blocks_from_research_root(
    path_case_dir: Path,
    module_runtime_support: Any,
) -> list[str]:
    """从研究根目录提取 display-math 公式块。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[str]`：按材料扫描顺序去重后的公式块正文列表。

    异常：
    - 文件读取失败时由底层异常上抛。
    """

    # 载入当前案件配置，后续只从中读取研究材料根目录用于本地公式追溯。
    dict_case_config = module_runtime_support.load_case_config(path_case_dir)  # research_root 来源的案件配置映射

    # 读取研究根目录文本；缺失时直接返回空列表。
    str_research_root = dict_case_config.get("research_root", "")  # 研究材料根目录文本

    # 在案件配置未登记研究根目录时直接返回空列表。
    if not str_research_root:

        # 空列表表示当前案件暂无可追溯的本地公式块材料。
        return []

    # 解析研究根目录绝对路径，后续据此扫描 Markdown 和文本材料。
    path_research_root = Path(str_research_root).resolve()  # 研究材料根目录路径

    # 在研究根目录不存在时直接返回空列表，避免引用无效外部路径。
    if not path_research_root.exists():

        # 空列表表示当前案件的研究材料目录不可用。
        return []

    # 先准备去重后的公式块正文列表，保持多材料扫描结果稳定。
    list_formula_blocks: list[str] = []  # 去重后的公式块正文列表

    # 记录已见公式键，避免同一公式因多份同步材料重复进入正文。
    set_seen_formulas: set[str] = set()  # 已见公式去重键集合

    # 逐个扫描常见文本材料后缀，只从本地文本源抽取 display-math 公式块。
    for path_source in sorted(path_research_root.rglob("*")):

        # 只处理常见文本材料，避免对二进制文件盲读造成噪声。
        if path_source.suffix.lower() not in {".md", ".txt"} or not path_source.is_file():

            # 当前文件不是受支持的本地文本材料，继续检查下一项。
            continue

        # 读取当前文本材料全文，供 display-math 匹配规则复用。
        str_source_text = path_source.read_text(encoding="utf-8")  # 当前材料全文

        # 顺序提取当前材料中的所有 display-math 公式块。
        for str_formula in RE_DISPLAY_FORMULA_BLOCK.findall(str_source_text):

            # 先读取当前公式块的原始行序列，供后续统一规整空白和保留原始换行顺序。
            list_raw_formula_lines = str_formula.splitlines()  # 当前公式块原始正文行列表

            # 先把每一行做去首尾空白处理，供后续统一过滤空行。
            list_stripped_formula_lines = [str_formula_line.strip() for str_formula_line in list_raw_formula_lines]  # 当前公式块去空白后的正文行

            # 再过滤掉空行，避免空白内容干扰去重与主稿保留。
            list_formula_text_lines = [str_line for str_line in list_stripped_formula_lines if str_line]  # 当前公式块有效正文行

            # 再按保留换行的形式拼回公式正文，供 Markdown 主稿直接复用。
            str_formula_text = "\n".join(list_formula_text_lines)  # 当前公式块保留换行的正文文本

            # 把当前公式块压缩成单行键，用于跨文件去重。
            str_formula_key = re.sub(r"\s+", "", str_formula_text)  # 当前公式块去重键

            # 空公式或重复公式都不再进入结果列表。
            if not str_formula_key or str_formula_key in set_seen_formulas:

                # 当前公式块无效或已收录，继续检查下一条公式。
                continue

            # 登记当前公式块去重键，避免后续重复追加。
            set_seen_formulas.add(str_formula_key)

            # 把当前本地公式块追加到结果列表，供正式交付源稿复用。
            list_formula_blocks.append(str_formula_text)

    # 返回已去重的公式块正文列表，供 Markdown 正文插入受控公式段。
    return list_formula_blocks

# 把公式块整理成正文 4.2.2 小节可直接拼接的 Markdown 行列表。
def build_formula_markdown_lines(list_formula_blocks: list[str]) -> list[str]:
    """构建公式块 Markdown 行列表。

    参数：
    - `list_formula_blocks`：从本地研究材料抽取的公式块正文列表。

    返回：
    - `list[str]`：正文 4.2.2 小节可直接拼接的公式说明与公式块行列表。

    异常：
    - 无。
    """

    # 没有公式块时返回空列表，让正文安全降级为纯文字方案描述。
    if not list_formula_blocks:

        # 空列表表示当前正文无需额外插入公式块段落。
        return []

    # 先准备公式说明首句，作为后续所有 display-math 公式块的统一导语。
    str_formula_intro = "在一个实施例中，所述评分、筛选或参数更新逻辑可结合本地研发材料中的公式表达进一步限定如下："  # 正文公式说明首句

    # 再初始化公式说明与公式块行列表，后续按顺序继续追加每个公式块。
    list_formula_lines = [str_formula_intro, ""]  # 公式块 Markdown 行列表

    # 按公式顺序逐个写出 display-math 公式块，保持与本地材料语义一致。
    for str_formula_block in list_formula_blocks:

        # 先写入公式块起始标记，保持 Markdown 源稿可直接追溯和继续编辑。
        list_formula_lines.append("$$")

        # 再写入当前公式块正文，保持数学表达与本地材料一致。
        list_formula_lines.extend(str_formula_block.splitlines())

        # 最后闭合当前公式块，并补空行分隔后续内容。
        list_formula_lines.extend(["$$", ""])

    # 返回整理后的公式块 Markdown 行列表，供正文 4.2.2 小节直接拼接。
    return list_formula_lines

# 把待确认事项整理成内部审查 sidecar 可直接拼接的行列表；为空时补一条受控默认提醒。
def build_missing_information_lines(
    list_missing_information: list[str],
    module_runtime_support: Any,
) -> list[str]:
    """构建待确认事项 Markdown 行列表。

    参数：
    - `list_missing_information`：上游主案结果中的待确认事项列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `list[str]`：内部审查待确认事项可直接拼接的行列表。

    异常：
    - 无。
    """

    # 先准备待确认事项 Markdown 行列表，后续按上游条目依次追加。
    list_missing_lines: list[str] = []  # 待确认事项 Markdown 行列表

    # 逐条清洗待确认事项文本，只保留真正可写入 sidecar 的条目。
    for str_item in list_missing_information:

        # 把当前待确认事项清洗成单行文本，便于统一判断可用性。
        str_missing_item = module_runtime_support.clean_text(str_item)  # 当前待确认事项文本

        # 在当前待确认事项存在有效文本时再生成 Markdown 条目。
        if str_missing_item:

            # 把当前待确认事项追加为 Markdown 列表项，供内部审查 sidecar 写入。
            list_missing_lines.append(f"- {str_missing_item}")

    # 在上游已经给出待确认事项时直接返回当前条目列表。
    if list_missing_lines:

        # 返回上游待确认事项列表，保持内部审查工作项真实可追溯。
        return list_missing_lines

    # 在上游没有给出待确认事项时补一条最小正式提醒。
    return ["- 正式提交前仍需由发明人和代理人复核具体实施例参数与行政信息。"]

# 构建正文封面与发明名称章节。
def build_cover_section(
    str_case_name: str,
    str_title: str,
) -> list[str]:
    """构建封面与发明名称章节。

    参数：
    - `str_case_name`：当前案件名称文本。
    - `str_title`：正式交底书标题文本。

    返回：
    - `list[str]`：封面与发明名称章节的 Markdown 行列表。

    异常：
    - 无。
    """

    # 返回封面与发明名称章节的固定骨架。
    return [
        "# 发明/实用新型专利申请技术交底书",
        "",
        f"案件：{str_case_name}",
        "",
        "## 一、发明名称",
        "",
        str_title,
        "",
        "## 二、所属技术领域",
        "",
        f"本发明属于计算机数据处理与工程系统优化技术领域，具体涉及 {str_title}。",
        "",
    ]

# 构建现有技术章节，包括背景、最接近现有技术和缺点条目。
def build_prior_art_section(
    list_background_lines: list[str],
    list_prior_summaries: list[str],
    list_problem_lines: list[str],
    list_reference_entries: list[str],
) -> list[str]:
    """构建现有技术章节。

    参数：
    - `list_background_lines`：带来源编号的技术机制与应用约束段落。
    - `list_prior_summaries`：最接近现有技术摘要列表。
    - `list_problem_lines`：现有技术缺点条目列表。
    - `list_reference_entries`：与正文编号对应的参考文献条目列表。

    返回：
    - `list[str]`：现有技术章节的 Markdown 行列表。

    异常：
    - 无。
    """

    # 先准备现有技术章节 Markdown 行列表，后续按章节顺序补齐问题条目。
    list_section_lines: list[str] = []  # 现有技术章节 Markdown 行列表

    # 先写入现有技术章节的固定骨架，建立背景与最接近现有技术描述。
    list_section_lines.extend(
        [
            "## 三、现有技术（背景技术）",
            "",
            "### 3.1相关技术背景以及最接近的现有技术",
            "",
        ]
    )

    # 逐条写入来源支持的技术机制和应用约束，避免用术语串替代技术背景。
    for str_background_line in list_background_lines:

        # 当前段落后保留一个 Markdown 空行，使不同来源的背景陈述边界清晰。
        list_section_lines.extend([str_background_line, ""])

    # 缺少核验来源时保留明确待补状态，正式交付仍由 blocker 门禁阻止。
    if not list_background_lines:

        # 写入不含推测事实的缺源说明，避免生成器伪造技术背景。
        list_section_lines.extend(["尚未提供可核验来源，无法形成正式技术背景说明。", ""])

    # 进入最接近现有技术小节，后续按同一来源顺序写入摘要。
    list_section_lines.extend(["### 3.2与本发明最相似的现有技术实现方案", ""])

    # 逐条写入带稳定引用编号的最接近现有技术摘要。
    for str_prior_summary in list_prior_summaries:

        # 每条现有技术摘要独立成段，便于读者按编号回查来源。
        list_section_lines.extend([str_prior_summary, ""])

    # 缺少现有技术摘要时不生成通用方案句，只标明待核验状态。
    if not list_prior_summaries:

        # 受控缺源文本与正式 blocker 保持一致，不冒充可提交的现有技术分析。
        list_section_lines.extend(["正式提交前需补齐已核验的最接近现有技术。", ""])

    # 写入现有技术缺点标题，继续组织由案件事实提供的因果问题条目。
    list_section_lines.extend(["### 3.3现有技术的缺点", ""])

    # 逐条写入现有技术缺点条目，保持 3.3 小节的编号结构稳定。
    for int_index, str_problem_line in enumerate(list_problem_lines, start=1):

        # 追加当前缺点编号行，保持问题条目与人工审阅顺序一致。
        list_section_lines.append(f"{int_index}. {str_problem_line.rstrip('。；;')}。")

    # 在问题条目后建立参考文献标题，使正文引用形成可回查闭环。
    list_section_lines.extend(["", "参考文献", ""])

    # 逐条写入与 3.1、3.2 共用编号顺序的参考文献条目。
    for str_reference_entry in list_reference_entries:

        # 每条著录项单独成段，便于 DOCX 导出器应用悬挂缩进。
        list_section_lines.extend([str_reference_entry, ""])

    # 返回现有技术章节行列表，供正文渲染阶段统一拼接。
    return list_section_lines

# 构建发明内容章节，包括发明目的、方法流程、系统方案和技术效果。
def build_invention_section(
    str_problem: str,
    list_step_lines: list[str],
    list_formula_lines: list[str],
    list_module_lines: list[str],
    list_effect_lines: list[str],
) -> list[str]:
    """构建发明内容章节。

    参数：
    - `str_problem`：主案问题文本。
    - `list_step_lines`：方法步骤 Markdown 行列表。
    - `list_formula_lines`：公式块 Markdown 行列表。
    - `list_module_lines`：系统模块 Markdown 行列表。
    - `list_effect_lines`：技术效果 Markdown 行列表。

    返回：
    - `list[str]`：发明内容章节的 Markdown 行列表。

    异常：
    - 无。
    """

    # 先准备发明内容章节 Markdown 行列表，后续顺序拼接步骤、模块与效果条目。
    list_section_lines: list[str] = []  # 发明内容章节 Markdown 行列表

    # 先写入发明目的与方法流程小节标题，建立正文主体章节骨架。
    list_section_lines.extend(
        [
            "## 四、发明内容：",
            "",
            "### 4.1 发明目的",
            "",
            f"本发明旨在针对“{str_problem}”所对应的处理缺口，形成可执行、可复核、可迭代的技术方案。",
            "",
            "### 4.2 技术解决方案",
            "",
            "#### 4.2.1 装置、结构类",
            "",
        ]
    )

    # 拼接系统/装置方案模块条目，对齐模板中 4.2.1 装置结构小节。
    list_section_lines.extend(list_module_lines)

    # 拼接方法方案小节标题与步骤条目。
    list_section_lines.extend(
        [
            "#### 4.2.2 方法类",
            "",
        ]
    )

    # 追加方法步骤说明块，保持每一步都带条件、输入、动作和输出。
    list_section_lines.extend(list_step_lines)

    # 在存在本地可追溯公式块时，把它们追加到方法小节尾部供正式源稿保留公式表达。
    if list_formula_lines:

        # 先补一个空行，再把公式说明与公式块写入当前技术方案小节。
        list_section_lines.extend(["", *list_formula_lines])

    # 在系统方案小节与技术效果小节之间补一个空行。
    list_section_lines.append("")

    # 拼接技术效果小节标题与编号条目。
    list_section_lines.extend(
        [
            "### 4.3、技术效果",
            "",
        ]
    )

    # 追加技术效果编号条目，供正文渲染阶段直接拼接。
    list_section_lines.extend(list_effect_lines)

    # 返回发明内容章节行列表，供正文渲染阶段统一拼接。
    return list_section_lines

# 构建附图说明与具体实施方式章节，内部审查材料另写 sidecar。
def build_tail_section() -> list[str]:
    """构建正文尾部章节。

    参数：
    - 无。

    返回：
    - `list[str]`：正文尾部章节的 Markdown 行列表。

    异常：
    - 无。
    """

    # 先准备正文尾部章节 Markdown 行列表，只保留可提交代理的主交底书章节。
    list_section_lines: list[str] = []  # 正文尾部章节 Markdown 行列表

    # 写入附图说明与具体实施方式章节骨架。
    list_section_lines.extend(
        [
            "",
            "## 五、附图及附图的简单说明",
            "",
            "图 1 为方法流程图，用于示出 S101 起至末步骤的处理流程。",
            "图 2 为系统模块图，用于示出状态采集、评分筛选、任务分配和反馈更新之间的数据关系。",
            "",
            "## 六、具体实施方式",
            "",
            "在一个基本实施例中，系统先接收待处理输入，再依次执行 4.2.1 所述步骤，并把每一步输出作为下一步骤输入。",
            "在异常实施例中，当候选对象响应失败、状态不满足阈值或反馈记录出现异常时，系统触发回退与更新逻辑，避免持续选择不可用对象。",
            "在效果验证实施例中，应至少记录输入规模、运行环境、评价指标和对比对象，以支撑 4.3 小节技术效果。",
            "",
        ]
    )

    # 在正文尾部补一个空行，保持导出器读取结尾时的版式稳定。
    list_section_lines.append("")

    # 返回正文尾部章节行列表，供正文渲染阶段统一拼接。
    return list_section_lines

# 渲染内部审查 sidecar，承接术语、证据和待确认事项。
def render_internal_review_markdown(
    str_case_name: str,
    list_terms: list[str],
    list_missing_lines: list[str],
) -> str:
    """渲染内部审查 Markdown 文本。

    参数：
    - `str_case_name`：当前案件名称文本。
    - `list_terms`：聚合后的技术术语列表。
    - `list_missing_lines`：待确认事项 Markdown 行列表。

    返回：
    - `str`：内部审查 sidecar Markdown 文本。

    异常：
    - 无。
    """

    # 先准备内部审查 sidecar 标题和来源说明。
    list_lines = [  # 内部审查 Markdown 行列表
        "# 内部审查材料",  # 固定 sidecar 标题
        "",  # 标题后的 Markdown 空行
        f"- case: {str_case_name}",  # 记录案件名而非本地路径
        "- note: 本文件不属于提交给代理的主交底书正文。",  # 明确提交边界
        "",  # 来源说明和术语小节分隔
        "## 术语说明",  # 内部术语审查入口
        "",  # 术语小节标题后的空行
    ]

    # 逐条写入术语说明列表，保持术语说明与上游术语聚合结果同步。
    for str_term in list_terms[:12]:

        # 追加当前术语条目，便于审阅人快速对齐正文里的关键名词。
        list_lines.append(f"- {str_term}")

    # 追加来源证据摘要说明，提示审阅人回看结构化证据映射。
    list_lines.extend(
        [
            "",
            "## 来源证据摘要",
            "",
            "正式技术特征应回溯到 `latest_evidence_map.json` 中的来源编号；缺少来源支撑的内容不得作为定稿必要技术特征。",
            "",
            "## 待确认事项",
            "",
        ]
    )

    # 追加待确认事项列表，提醒正式提交前仍需人工补齐的内容。
    list_lines.extend(list_missing_lines)

    # 在文件尾部补空行，保持 Markdown 结尾稳定。
    list_lines.append("")

    # 返回完整内部审查文本，供草稿阶段落盘。
    return "\n".join(list_lines)

# 渲染正式中文交底书草稿，统一拼接标题、背景、方案和效果。
def render_markdown(
    dict_render_payload: dict[str, Any],
    module_runtime_support: Any,
) -> str:
    """渲染正式中文交底书草稿。

    参数：
    - `dict_render_payload`：包含正文渲染所需全部字段的结构化字典。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `str`：完整的正式中文交底书 Markdown 文本。

    异常：
    - 无。
    """

    # 读取最接近现有技术摘要列表，供背景技术与现有技术小节复用。
    list_prior_summaries = dict_render_payload["list_prior_summaries"]  # 最接近现有技术摘要列表

    # 读取来源支持的背景说明段落，供 3.1 小节直接复用。
    list_background_lines = dict_render_payload["list_background_lines"]  # 技术机制与应用约束段落

    # 读取参考文献列表，使正文引用与文末著录项共享同一编号顺序。
    list_reference_entries = dict_render_payload["list_reference_entries"]  # 参考文献条目列表

    # 从渲染载荷读取步骤主链，供 4.2.2 小节展开输入处理输出关系。
    list_steps = dict_render_payload["list_steps"]  # 方法章节步骤主链

    # 读取系统模块列表，供 4.2.1 小节生成模块化方案说明。
    list_modules = dict_render_payload["list_modules"]  # 结构化系统模块列表

    # 提取技术效果条目列表，供技术效果小节生成编号说明。
    list_effects = dict_render_payload["list_effects"]  # 4.3 小节的效果原始条目列表

    # 生成 4.2.2 小节的步骤说明行列表，供正文渲染阶段直接插入。
    list_step_lines = build_step_markdown_lines(list_steps)  # 4.2.2 小节步骤说明行列表

    # 生成 4.2.2 小节末尾的公式说明与公式块，保留本地材料中的原始数学表达。
    list_formula_lines = dict_render_payload["list_formula_lines"]  # 4.2.2 小节公式块行列表

    # 生成 4.2.1 小节的系统模块行列表，供正文渲染阶段直接插入。
    list_module_lines = build_module_markdown_lines(list_modules)  # 4.2.1 小节系统模块行列表

    # 生成 4.3 小节的技术效果行列表，供正文渲染阶段直接插入。
    list_effect_lines = build_effect_markdown_lines(list_effects)  # 4.3 小节技术效果行列表

    # 先准备正文 Markdown 行列表，后续按章节顺序逐段追加正式内容。
    list_markdown_lines: list[str] = []  # 正文 Markdown 文本行列表

    # 按章节顺序拼接封面、现有技术、发明内容与正文尾部章节。
    list_markdown_lines.extend(
        build_cover_section(
            dict_render_payload["str_case_name"],
            dict_render_payload["str_title"],
        )
    )

    # 再拼接现有技术章节，建立背景、最接近现有技术与问题条目。
    list_markdown_lines.extend(
        build_prior_art_section(
            list_background_lines,
            list_prior_summaries,
            dict_render_payload["list_problem_lines"],
            list_reference_entries,
        )
    )

    # 然后拼接发明内容章节，写入方法流程、系统方案和技术效果。
    list_markdown_lines.extend(
        build_invention_section(
            dict_render_payload["str_problem"],
            list_step_lines,
            list_formula_lines,
            list_module_lines,
            list_effect_lines,
        )
    )

    # 最后拼接正文尾部章节，只保留附图说明和具体实施方式。
    list_markdown_lines.extend(build_tail_section())

    # 返回完整 Markdown 文本，供案件目录落盘与后链工具继续复用。
    return "\n".join(list_markdown_lines)

# 统一写入正文、内部审查和合同工件，缩小命令行入口职责。
def write_generated_documents(
    path_case_dir: Path,
    dict_document_context: dict[str, Any],
    module_runtime_support: Any,
    module_quality_contract: Any,
) -> Path:
    """写入正式草稿、内部审查、快照和起草合同工件。

    参数：
    - `path_case_dir`：当前案件根目录路径。
    - `dict_document_context`：正文、标题、步骤和审查内容组成的写入上下文。
    - `module_runtime_support`：共享运行时支持模块对象。
    - `module_quality_contract`：正文质量合同模块对象。

    返回：
    - `Path`：稳定主草稿路径。

    异常：
    - 目录创建或文件写入失败时由底层异常上抛。
    """

    # 确保草稿输出目录存在，供稳定草稿、审查 sidecar 和快照共同落盘。
    path_output_dir = module_runtime_support.ensure_dir(path_case_dir / "03_drafts")  # 草稿输出目录路径

    # 固定稳定主草稿与内部审查路径，供后续链路按约定名称读取。
    path_stable_draft = path_output_dir / "disclosure_draft.md"  # 稳定主草稿路径

    # 内部审查材料采用独立 sidecar，避免进入代理人提交正文。
    path_internal_review = path_output_dir / "disclosure_internal_review.md"  # 内部审查 sidecar 路径

    # 由案件名和当前时间生成安全快照路径，保留本轮生成历史。
    str_snapshot_name = module_runtime_support.sanitize_name(dict_document_context["case_name"])  # 快照文件名前缀

    # 生成不含路径非法字符的紧凑时间片段。
    str_snapshot_timestamp = module_runtime_support.iso_now().replace(":", "").replace("-", "")  # 快照时间片段

    # 使用案件名前缀和时间片段生成唯一正文快照路径。
    path_snapshot_draft = path_output_dir / f"{str_snapshot_name}_{str_snapshot_timestamp}.md"  # 正文快照路径

    # 在正式落盘前为确定性参数更新式补充行内公式标记，确保 DOCX 导出时进入可编辑公式链。
    str_marked_markdown = module_quality_contract.mark_inline_math_expressions(dict_document_context["markdown"])  # 已结构化标记的正文

    # 写入代理人正文、内部审查 sidecar 和时间快照，保持内部材料不进入主文档。
    module_runtime_support.write_text_file(path_stable_draft, str_marked_markdown)

    # 单独写入内部审查材料，供人工复核证据和待确认项。
    module_runtime_support.write_text_file(path_internal_review, dict_document_context["internal_review"])

    # 保存本轮正文快照，便于后续核对确认前后的内容哈希。
    module_runtime_support.write_text_file(path_snapshot_draft, str_marked_markdown)

    # 将正文相关字段收敛为起草合同上下文，避免写入函数暴露过多独立参数。
    dict_artifact_context = {  # 起草合同写入上下文
        "title": dict_document_context["title"],  # 合同中的发明名称
        "steps": dict_document_context["steps"],  # 合同中的方法步骤
        "modules": dict_document_context["modules"],  # 合同中的装置模块
        "effects": dict_document_context["effects"],  # 合同中的技术效果
    }

    # 写入起草计划、模板槽位正文和预览哈希，锁定确认后的生成边界。
    write_draft_contract_artifacts(
        path_output_dir,
        str_marked_markdown,
        dict_artifact_context,
        module_runtime_support,
        module_quality_contract,
    )

    # 返回稳定主草稿路径，供命令行入口输出给上游流水线。
    return path_stable_draft

# 执行正式草稿生成入口，读取主案结果并输出交底书草稿与证据映射。
