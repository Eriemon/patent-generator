"""为专利交底书生成提供可复用的证据、推断和质量合同。"""

# 引入路径加载、正则与动态数据类型，复用正式模型验证并输出合同对象。
import importlib.util
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# 过滤脱离上下文的代码 token，防止它们污染代理审阅用术语表。
NOISE_TERMS = {"cpu", "times", "weight_i", "weight", "max", "min"}  # 无业务语义的术语标记

# 识别效果结论所需的结果词，避免把纯方案说明错归类为技术效果。
EFFECT_WORDS = ("提高", "降低", "减少", "改善", "提升", "缩短", "增强", "抑制")  # 效果结果词集合

# 排除技术方案语言，防止包含方法或模块描述的句子充当效果依据。
SOLUTION_WORDS = ("提出", "方法", "步骤", "包括", "用于", "装置", "模块")  # 方案描述词集合

# 禁止在受控推断中补写参数、公式和实验事实，确保推断只承担结构连接作用。
FORBIDDEN_INFERENCE_MARKERS = ("=", "+", "-", "*", "/", "实验", "对比", "数据", "参数", "公式")  # 禁止推断标记集合

# 识别正文中可确定为参数更新规则的赋值表达式，避免把普通等号语句误判为数学公式。
RE_INLINE_PARAMETER_UPDATE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:max|min)\([^()\n]*\)")  # 参数更新式匹配规则

# 单独识别被 Markdown 代码样式误包裹的完整更新式，使正文数学语义能够脱离反引号。
RE_BACKTICK_PARAMETER_UPDATE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:max|min)\([^()\n]*\))`")  # 反引号更新式匹配规则

# 隔离已有公式和代码片段，保证标记与漏标检查都不会重复处理受保护内容。
RE_PROTECTED_MATH_OR_CODE = re.compile(r"(```.*?```|`[^`\n]*`|\$\$.*?\$\$|\$[^$\n]+\$)", flags=re.DOTALL)  # 受保护文本分段规则

# 评分卡与正式验证报告必须消费同一 Model 4.0 闭包。
PATH_STRUCTURED_CONTRACT_VALIDATOR = Path(__file__).resolve().parents[1] / "review" / "structured_contract_validator.py"  # 正式模型验证器

# 把正文参数更新式规整为 MathType 转换链可消费的 LaTeX 表达。
def normalize_inline_math_expression(str_expression: str) -> str:
    """规范正文参数更新式中的函数和乘法运算符。

    参数：
    - `str_expression`：从普通正文中识别出的参数更新式。

    返回：
    - `str`：可由现有 LaTeX 至 MathType 链处理的行内公式。

    异常：
    - 无。
    """

    # 将 Unicode 乘号转成标准 LaTeX 命令，避免转换库按普通字符处理。
    str_normalized = str_expression.replace("×", r"\times ")  # 运算符规范化后的表达式

    # 为数学函数补充 LaTeX 命令前缀，使 MathType 以函数样式显示 max 和 min。
    str_normalized = re.sub(r"\b(max|min)\s*\(", lambda obj_match: rf"\{obj_match.group(1)}(", str_normalized)  # 函数规范化后的表达式

    # 返回不改变变量名和数值的规范公式文本。
    return str_normalized

# 在正文普通文本片段中补充行内公式标记，已有公式和代码片段保持原样。
def mark_inline_math_expressions(str_markdown: str) -> str:
    """把明确的正文参数更新式转换为 Markdown 行内公式。

    参数：
    - `str_markdown`：可能包含普通文本数学表达式的交底书正文。

    返回：
    - `str`：已为确定性参数更新式补充 `$...$` 标记的正文。

    异常：
    - 无。
    """

    # 先把被代码样式误包裹的完整更新式改成公式，普通代码标识仍由后续保护规则保留。
    str_math_ready_markdown = RE_BACKTICK_PARAMETER_UPDATE.sub(  # 已释放反引号公式的正文
        lambda obj_match: f"${normalize_inline_math_expression(obj_match.group(1))}$",  # 完整更新式的公式包装动作
        str_markdown,  # 尚未处理反引号数学表达的原始正文
    )

    # 按已有公式与代码边界切分正文，偶数位置才允许执行自动标记。
    list_segments = RE_PROTECTED_MATH_OR_CODE.split(str_math_ready_markdown)  # 自动标记使用的正文区段

    # 只改写未受保护的普通正文片段，保持函数重复调用时结果幂等。
    for int_index in range(0, len(list_segments), 2):

        # 用规范 LaTeX 包裹当前片段内所有确定性参数更新式。
        str_marked_segment = RE_INLINE_PARAMETER_UPDATE.sub(  # 当前片段的公式标记结果
            lambda obj_match: f"${normalize_inline_math_expression(obj_match.group(0))}$",  # 单条更新式的 LaTeX 包装动作
            list_segments[int_index],  # 尚未进入公式语法的普通正文片段
        )

        # 将完成公式包装的片段放回原序列，后续拼接仍保持文档位置不变。
        list_segments[int_index] = str_marked_segment  # 当前位置的已标记正文片段

    # 拼回原有正文顺序，使标题、段落和受保护内容均保持原位置。
    return "".join(list_segments)

# 扫描仍以普通文本存在的参数更新式，供交付校验阻止公式退化。
def find_unmarked_inline_math_expressions(str_markdown: str) -> list[str]:
    """查找未使用 Markdown 行内公式标记的参数更新式。

    参数：
    - `str_markdown`：待执行公式完整性检查的交底书正文。

    返回：
    - `list[str]`：按正文顺序去重后的未标记表达式。

    异常：
    - 无。
    """

    # 先移除完整更新式外层的反引号，使误用代码样式的数学内容仍会被审计发现。
    str_auditable_markdown = RE_BACKTICK_PARAMETER_UPDATE.sub(lambda obj_match: obj_match.group(1), str_markdown)  # 释放反引号公式后的审计正文

    # 代码示例与合法公式均不属于审计对象，此处仅留下可见正文供裸表达式扫描。
    list_segments = RE_PROTECTED_MATH_OR_CODE.split(str_auditable_markdown)  # 漏标审计使用的裸文本区段

    # 收集普通正文片段中的参数更新式，避免已有公式触发误报。
    list_expressions = [  # 未标记参数更新式候选列表
        obj_match.group(0)  # 保留材料中的原始表达形式
        for int_index in range(0, len(list_segments), 2)  # 只读取普通正文位置
        for obj_match in RE_INLINE_PARAMETER_UPDATE.finditer(list_segments[int_index])  # 当前片段命中的赋值更新式
    ]

    # 按首次出现顺序去重，避免同一漏标表达产生重复 blocker。
    return list(dict.fromkeys(list_expressions))

# 规整空白，以便多个证据来源进入同一比较规则前具有稳定文本形态。
def clean_text(str_text: str) -> str:
    """压缩空白并返回可用于质量判断的正文文本。

    参数：
    - `str_text`：待规整文本。

    返回：
    - `str`：规整后的单行文本。

    异常：
    - 无。
    """

    # 返回压缩后的单行证据文本，避免空白差异影响术语或效果判断。
    return " ".join(str_text.split())

# 判断候选术语能否代表可审阅的技术概念，而非符号或脱离语境的 token。
def is_noise_term(str_term: str) -> bool:
    """判断术语是否应从正式术语表排除。

    参数：
    - `str_term`：待判断术语。

    返回：
    - `bool`：应排除时为 `True`。

    异常：
    - 无。
    """

    # 取得用于长度、符号和词表比较的规范术语文本。
    str_normalized = clean_text(str_term)  # 术语规范文本

    # 取得不区分大小写的候选键，兼容上游材料中的英文技术 token。
    str_lowered = str_normalized.lower()  # 术语小写比较键

    # 返回所有噪声条件的并集，避免正常自然语言术语被过度过滤。
    return (
        not str_normalized
        or str_lowered in NOISE_TERMS
        or len(str_normalized) > 36
        or any(str_marker in str_normalized for str_marker in ("=", "+", "*", "/"))
        or bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str_normalized))
    )

# 按输入顺序筛掉噪声和重复项，保留审阅者可理解的业务术语。
def filter_technical_terms(list_terms: list[str]) -> list[str]:
    """过滤噪声术语并保持可用技术术语的原始顺序。

    参数：
    - `list_terms`：上游候选术语列表。

    返回：
    - `list[str]`：去噪且去重后的技术术语列表。

    异常：
    - 无。
    """

    # 返回有序去重后的可用术语，避免同一概念在背景与实施方式中反复出现。
    return list(
        dict.fromkeys(
            clean_text(str_term)
            for str_term in list_terms
            if not is_noise_term(clean_text(str_term))
        )
    )

# 判断一条材料能否作为技术效果的直接证据，而不是问题或方案本身。
def is_effect_evidence(str_text: str) -> bool:
    """判断证据文本是否可直接作为技术效果。

    参数：
    - `str_text`：待分类证据文本。

    返回：
    - `bool`：属于可用技术效果时为 `True`。

    异常：
    - 无。
    """

    # 取得用于结果词和方案词判断的规范证据文本。
    str_clean_text = clean_text(str_text)  # 效果证据规范文本

    # 返回结果词存在且方案词不存在的判定，防止误把方案陈述写入效果章节。
    return any(str_word in str_clean_text for str_word in EFFECT_WORDS) and not any(
        str_word in str_clean_text for str_word in SOLUTION_WORDS
    )

# 保留文本分类为真实效果的证据记录，让正文效果段具有来源边界。
def filter_effect_evidence(list_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """只保留可证明结果的技术效果证据记录。

    参数：
    - `list_evidence`：上游效果证据记录列表。

    返回：
    - `list[dict[str, Any]]`：过滤后的效果证据记录列表。

    异常：
    - 无。
    """

    # 返回通过效果分类的原始记录副本，保证来源编号和定位信息不会丢失。
    return [
        dict_item
        for dict_item in list_evidence
        if is_effect_evidence(str(dict_item.get("text", "")))
    ]

# 判断补写是否仅表达结构关系，而没有虚构可量化或可验证的技术事实。
def is_allowed_controlled_inference(str_text: str) -> bool:
    """判断补写文本是否满足受控推断边界。

    参数：
    - `str_text`：待作为推断写入的文本。

    返回：
    - `bool`：仅包含安全结构连接时为 `True`。

    异常：
    - 无。
    """

    # 取得用于数字与禁止事实标记判断的规范推断文本。
    str_clean_text = clean_text(str_text)  # 推断规范文本

    # 返回严格边界判定，禁止把参数、公式、数据或实验结果作为合理推断写入正文。
    return bool(str_clean_text) and not re.search(r"\d", str_clean_text) and not any(
        str_marker in str_clean_text for str_marker in FORBIDDEN_INFERENCE_MARKERS
    )

# 通过关键词交集为一个步骤筛选最小支撑证据集合，禁止全量证据泛挂。
def build_step_support_map(
    list_steps: list[dict[str, Any]],
    list_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """按步骤关键词建立精确证据映射。

    参数：
    - `list_steps`：包含步骤标识、摘要和关键词的步骤记录。
    - `list_evidence`：包含证据标识、文本和关键词的证据记录。

    返回：
    - `list[dict[str, Any]]`：每一步对应的最小支撑证据编号列表。

    异常：
    - 无。
    """

    # 返回按步骤顺序组织的映射记录，让后续校验能明确指出无证据的具体步骤。
    return [
        {
            "type": "method_step",  # 方法步骤特征类型
            "step": str(dict_step.get("id", "")),  # 当前步骤标识
            "feature": str(dict_step.get("summary", "")),  # 当前步骤技术特征
            "support_ids": list(  # 与当前关键词真实相交的最小来源集合
                dict.fromkeys(
                    str(dict_evidence["id"])
                    for dict_evidence in list_evidence
                    if set(dict_step.get("keywords", [])).intersection(dict_evidence.get("keywords", []))
                )
            ),
        }
        for dict_step in list_steps
    ]

# 构造先计划后起草的 sidecar，登记章节目标、步骤链和每条受控推断。
def build_draft_plan(
    str_title: str,
    list_steps: list[dict[str, Any]],
    list_inference_candidates: list[str],
) -> dict[str, Any]:
    """构造代理起草前的可确认计划与受控推断清单。

    参数：
    - `str_title`：当前发明标题。
    - `list_steps`：主方案方法步骤列表。
    - `list_inference_candidates`：待评估的结构性补写候选文本。

    返回：
    - `dict[str, Any]`：包含章节目标、步骤链和推断边界的计划字典。

    异常：
    - 无。
    """

    # 返回可序列化起草计划，使预览确认能绑定到具体的推断编号和正文骨架。
    return {
        "title": clean_text(str_title),  # 计划对应的发明标题
        "section_objectives": {
            "background": "说明可核验现状、缺陷及其形成原因。",  # 背景章节论证目标
            "solution": "按输入、处理、输出、触发条件和上下游关系展开。",  # 方案章节论证目标
            "effect": "以技术特征、作用机制和效果构成因果链。",  # 效果章节论证目标
            "embodiment": "完整覆盖主方案及反馈、更新、异常或边界流程。",  # 实施方式论证目标
        },
        "step_chain": [str(dict_step.get("id", "")) for dict_step in list_steps],  # 主方案步骤链
        "inferences": [
            {
                "id": f"INF-{int_index:03d}",  # 稳定推断编号
                "text": clean_text(str_candidate),  # 待确认推断文本
                "allowed": is_allowed_controlled_inference(str_candidate),  # 推断边界判断结果
            }
            for int_index, str_candidate in enumerate(list_inference_candidates, start=1)
        ],
    }

# 按受管路径加载正式模型验证器，评分卡不得复制弱化规则。
def load_structured_contract_validator() -> Any:
    """加载 Model 4.0 正式结构和语义闭包验证器。

    参数：
    - 无。

    返回：
    - `Any`：已经执行的正式模型验证模块。

    异常：
    - `ImportError`：模块规格或加载器缺失时抛出。
    """

    # 固定内部名称不会改写调用方模块搜索路径。
    str_module_name = "readable_patent_scorecard_structured_validator"  # 正式验证器内部模块名

    # 根据正式源码路径创建隔离加载规格。
    obj_specification = importlib.util.spec_from_file_location(  # Model4 验证器加载规格
        str_module_name,  # 正式验证器隔离模块名
        PATH_STRUCTURED_CONTRACT_VALIDATOR,  # Model 4.0 验证器源码路径
    )

    # 正式验证器缺失时不能回退 pass/confirm 字段检查。
    if obj_specification is None or obj_specification.loader is None:

        # 报告评分卡单一事实来源缺失。
        raise ImportError("> ERR: [Python] 无法加载 structured_contract_validator.py。")

    # 创建隔离模块并执行正式验证源码。
    module_validator = importlib.util.module_from_spec(obj_specification)  # 正式模型验证模块

    # 执行源码后才能取得统一 findings 和活动确认判定。
    obj_specification.loader.exec_module(module_validator)

    # 返回当前评分卡使用的正式验证器。
    return module_validator

# 复用正式验证器取得模型缺口和活动人工目标。
def inspect_delivery_closure(
    dict_delivery_model: Mapping[str, Any] | None,
    dict_claims_map: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, str]], set[tuple[str, str]], set[tuple[str, str]]]:
    """检查 Model 4.0 正式闭包。

    参数：
    - `dict_delivery_model`：当前权威 Model 4.0。
    - `dict_claims_map`：与当前模型共同交付的实时权利要求映射。

    返回：
    - `tuple`：正式 findings、有效人工目标和必需技术效果目标。

    异常：
    - 无；缺失模型返回空目标，交由评分卡 fail closed。
    """

    # 非对象模型无法进入正式验证器。
    if not isinstance(dict_delivery_model, Mapping):

        # 空结果不会被误判为模型通过，因为调用方同时检查对象类型。
        return [], set(), set()

    # 正式验证器同时负责 Schema、代理目标和当前哈希。
    module_validator = load_structured_contract_validator()  # Model 4.0 正式验证实现

    # 评分卡直接消费正式报告使用的同一 findings。
    list_formal_findings = module_validator.validate_structured_model(  # 正式模型缺口
        dict_delivery_model,  # 当前权威 Model 4.0
        dict_claims_map,  # 当前实时 Claims Map 3
    )

    # 损坏语义容器不提供活动确认数组。
    obj_semantic_review = dict_delivery_model.get("semantic_review")  # 当前语义审查容器

    # Task1 验证器会选择同目标最后一条记录并复算摘要。
    obj_human_confirmations = (
        obj_semantic_review.get("human_confirmations", [])  # 当前活动确认数组
        if isinstance(obj_semantic_review, Mapping)  # 仅对象容器可读取记录
        else []  # 损坏容器按无确认处理
    )  # 可交给正式验证器的确认数组

    # 公共闭包返回当前有效目标集合。
    tuple_human_validation = module_validator.validate_human_confirmation_records(  # 正式人工确认验证结果
        dict_delivery_model,  # 当前完整 Model 4.0
        obj_human_confirmations,  # 当前活动人工确认数组
        dict_claims_map,  # 独立项必须从实时映射解析
    )

    # 只保留目标解析、confirm 决定和当前哈希均有效的坐标。
    set_valid_confirmation_targets = set(tuple_human_validation[1])  # 有效人工确认目标

    # 每项稳定特征的技术效果都需要逐项人工确认。
    set_required_effect_targets = {
        ("feature_technical_effect", str(dict_feature.get("feature_id")))  # 技术效果确认坐标
        for dict_feature in dict_delivery_model.get("feature_registry", [])  # 遍历稳定技术特征
        if isinstance(dict_feature, Mapping) and dict_feature.get("feature_id")  # 排除损坏身份
    }  # 当前全部技术效果必需目标

    # 三组结果供评分卡组合，不在辅助层创造放行状态。
    return list_formal_findings, set_valid_confirmation_targets, set_required_effect_targets

# 把正式闭包结果转换为可追踪评分卡 findings。
def build_scorecard_findings(
    bool_markdown_present: bool,
    list_formal_findings: list[dict[str, str]],
    bool_semantic_review_passed: bool,
    bool_human_confirmation_passed: bool,
) -> list[dict[str, str]]:
    """构造正文质量缺口。

    参数：
    - `bool_markdown_present`：正文是否具有可见内容。
    - `list_formal_findings`：正式 Model 4.0 findings。
    - `bool_semantic_review_passed`：正式模型总门结果。
    - `bool_human_confirmation_passed`：必需人工类别闭包结果。

    返回：
    - `list[dict[str, str]]`：无数值分数的质量缺口。

    异常：
    - 无。
    """

    # 缺口数组只记录失败事实，表面关键词不会贡献通过项。
    list_findings: list[dict[str, str]] = []  # 当前评分卡 findings

    # 空正文不能形成正式交付物。
    if not bool_markdown_present:

        # 正文缺失独立于模型闭包报告。
        list_findings.append(
            {
                "level": "blocker",
                "code": "quality_markdown_missing",
                "message": "正式交底书Markdown为空。",
                "suggestion": "从已审查Model 4.0生成正式正文。",
            }
        )

    # Schema、引用、目标或哈希缺口统一引用正式验证报告。
    if list_formal_findings:

        # 评分卡摘要底层数量，不复制弱化底层规则。
        list_findings.append(
            {
                "level": "blocker",
                "code": "quality_formal_model_invalid",
                "message": f"当前Model 4.0正式验证存在{len(list_formal_findings)}项问题。",
                "suggestion": "先修复正式验证报告中的schema、目标覆盖和当前哈希问题。",
            }
        )

    # 正式模型未通过时不能依赖标题或关键词放行。
    if not bool_semantic_review_passed:

        # 单独暴露代理审查总门，便于交付流程定位。
        list_findings.append(
            {
                "level": "blocker",
                "code": "quality_semantic_review_required",
                "message": "当前Model 4.0尚未完成活动代理语义审查。",
                "suggestion": "完成全部章节和特征的当前内容审查。",
            }
        )

    # 缺少任一必需人工类别都不能形成最终合规结论。
    if not bool_human_confirmation_passed:

        # AI、技术效果和独立项范围共享同一人工总门。
        list_findings.append(
            {
                "level": "blocker",
                "code": "quality_human_confirmation_required",
                "message": "当前Model 4.0尚未完成必要人工确认。",
                "suggestion": "逐项确认AI适用性、技术效果和独立项范围。",
            }
        )

    # 调用方按真实 findings 计数和选择状态。
    return list_findings

# 视觉状态只能在语义与人工门通过后推进。
def select_scorecard_status(
    dict_gate_counts: Mapping[str, int],
    bool_visual_review_complete: bool,
) -> str:
    """选择正文质量流程状态。

    参数：
    - `dict_gate_counts`：真实问题级别计数。
    - `bool_visual_review_complete`：当前版本视觉验收结果。

    返回：
    - `str`：needs_revision、visual_review_required 或 completed。

    异常：
    - 无。
    """

    # blocker 或 major 存在时视觉标记不能推进状态。
    if dict_gate_counts["blocker"] or dict_gate_counts["major"]:

        # 当前版本必须修订后重跑正式门。
        return "needs_revision"

    # 合规门通过后才允许进入独立视觉验收态。
    if not bool_visual_review_complete:

        # 视觉回执尚未绑定当前版本。
        return "visual_review_required"

    # 三类门均通过时才允许完成。
    return "completed"

# 根据Model 4.0语义审查和人工确认计算正文合规状态。
def build_quality_scorecard(
    str_markdown: str,
    bool_visual_review_complete: bool = False,
    dict_delivery_model: Mapping[str, Any] | None = None,
    dict_claims_map: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """评估交底书是否具备语义、人工和视觉放行条件。

    参数：
    - `str_markdown`：待审阅的正式交底书 Markdown。
    - `bool_visual_review_complete`：是否已经完成外部视觉验收。
    - `dict_delivery_model`：当前权威Model 4.0。
    - `dict_claims_map`：与当前模型共同交付的实时权利要求映射。

    返回：
    - `dict[str, Any]`：合规状态、gate计数和问题组成的质量报告。

    异常：
    - 无；缺失或损坏模型按未通过处理。
    """

    # Markdown 和视觉状态只是观察项，不能独立形成 pass。
    dict_checks = {
        "markdown_present": bool(str_markdown.strip()),  # 正文是否具有可见内容
        "visual_review": bool_visual_review_complete,  # 当前版本视觉验收结果
    }  # 非评分型辅助观察项

    # 统一闭包同时返回底层问题、有效确认和技术效果必需目标。
    tuple_closure = inspect_delivery_closure(  # 评分卡三组权威输入
        dict_delivery_model,  # 待检查的交付模型
        dict_claims_map,  # 独立项摘要权威来源
    )

    # 底层 findings 保留给正式计数和摘要。
    list_formal_findings = tuple_closure[0]  # Schema 与语义闭包底层缺口

    # 有效目标只包含当前摘要匹配的活动 confirm 记录。
    set_valid_confirmation_targets = tuple_closure[1]  # 当前有效人工目标

    # 技术效果必需目标按稳定 feature_id 构造。
    set_required_effect_targets = tuple_closure[2]  # 当前必需技术效果目标

    # 任一正式 finding 都表示 schema、引用、审查或人工闭包尚未完成。
    bool_semantic_review_passed = bool(  # 正式模型总门结果
        isinstance(dict_delivery_model, Mapping)  # 当前存在对象模型
        and not list_formal_findings  # 正式验证无缺口
    )  # 当前模型是否通过正式总门

    # AI、全部技术效果和至少一个独立项范围共同组成必需确认类别。
    bool_required_confirmations_present = bool(  # 三类必需人工确认结果
        ("ai_applicability", "model") in set_valid_confirmation_targets  # AI 目标当前有效
        and set_required_effect_targets <= set_valid_confirmation_targets  # 全部技术效果当前有效
        and any(  # 独立项范围确认存在性
            str_target_type == "independent_claim"  # 至少一个独立项范围当前有效
            for str_target_type, _ in set_valid_confirmation_targets  # 遍历全部有效目标
        )
    )  # 当前人工确认类别是否完整

    # 人工门同时要求正式模型通过和三类活动确认齐全。
    bool_human_confirmation_passed = bool(  # 正式人工总门结果
        bool_semantic_review_passed  # 底层模型已通过
        and bool_required_confirmations_present  # 三类确认均齐全
    )  # 当前人工确认是否完成正式闭包

    # 失败事实由独立构造器转成稳定评分卡 finding。
    list_findings = build_scorecard_findings(  # Model 4.0 合规缺口
        dict_checks["markdown_present"],  # 正文存在性观察项
        list_formal_findings,  # 正式底层 findings
        bool_semantic_review_passed,  # 正式模型总门
        bool_human_confirmation_passed,  # 人工类别总门
    )

    # 按严重级别统计真实gate数量，不再生成可伪造数值分数。
    dict_gate_counts = {  # 合规gate计数
        "blocker": sum(dict_item["level"] == "blocker" for dict_item in list_findings),  # 阻断项数量
        "major": sum(dict_item["level"] == "major" for dict_item in list_findings),  # 修订项数量
        "minor": sum(dict_item["level"] == "minor" for dict_item in list_findings),  # 提示项数量
    }

    # 状态选择与 finding 构造分离，视觉标记不能覆盖语义缺口。
    str_status = select_scorecard_status(dict_gate_counts, bool_visual_review_complete)  # 正式流程状态

    # 返回无数值分数的合规报告。
    return {
        "status": str_status,  # 合规流程状态
        "compliance_status": "compliant" if not list_findings else "blocked",  # 语义和人工合规结论
        "gate_counts": dict_gate_counts,  # 各严重级别真实问题数量
        "checks": {
            **dict_checks,  # Markdown和视觉观察项
            "semantic_review": bool_semantic_review_passed,  # Model4代理语义门
            "human_confirmation": bool_human_confirmation_passed,  # Model4人工确认门
            "formal_model": bool_semantic_review_passed,  # Model4正式总门
        },
        "findings": list_findings,  # 可追踪合规缺陷
        "formal_finding_count": len(list_formal_findings),  # 正式模型底层问题数量
    }
