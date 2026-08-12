"""为专利交底书生成提供可复用的证据、推断和质量合同。"""

# 引入正则与动态数据类型，用于清洗本地证据并输出可序列化的合同对象。
import re
from typing import Any

# 过滤脱离上下文的代码 token，防止它们污染代理审阅用术语表。
NOISE_TERMS = {"cpu", "times", "weight_i", "weight", "max", "min"}  # 无业务语义的术语标记

# 识别效果结论所需的结果词，避免把纯方案说明错归类为技术效果。
EFFECT_WORDS = ("提高", "降低", "减少", "改善", "提升", "缩短", "增强", "抑制")  # 效果结果词集合

# 排除技术方案语言，防止包含方法或模块描述的句子充当效果依据。
SOLUTION_WORDS = ("提出", "方法", "步骤", "包括", "用于", "装置", "模块")  # 方案描述词集合

# 禁止在受控推断中补写参数、公式和实验事实，确保推断只承担结构连接作用。
FORBIDDEN_INFERENCE_MARKERS = ("=", "+", "-", "*", "/", "实验", "对比", "数据", "参数", "公式")  # 禁止推断标记集合

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

# 对正文的背景、方案、效果和实施方式覆盖度打分，输出不会提前 completed 的统一状态。
def build_quality_scorecard(str_markdown: str, bool_visual_review_complete: bool = False) -> dict[str, Any]:
    """以确定性规则评估交底书草稿的章节覆盖和可审阅程度。

    参数：
    - `str_markdown`：待审阅的正式交底书 Markdown。
    - `bool_visual_review_complete`：是否已经完成外部视觉验收。

    返回：
    - `dict[str, Any]`：评分、问题和统一状态组成的质量报告。

    异常：
    - 无。
    """

    # 记录四项正文质量条件，覆盖背景诊断、步骤链、因果效果和实施充分性。
    dict_checks = {
        "background": "三、现有技术" in str_markdown and "3.3现有技术的缺点" in str_markdown,  # 背景诊断条件
        "solution": len(re.findall(r"S\d{3}", str_markdown)) >= 2,  # 方案步骤条件
        "effect": "4.3、技术效果" in str_markdown and "通过" in str_markdown,  # 效果因果条件
        "embodiment": (  # 实施充分条件
            "六、具体实施方式" in str_markdown  # 实施章节存在性
            and len(str_markdown.split("六、具体实施方式", 1)[-1]) >= 120  # 实施段落最小长度
        ),
    }

    # 生成每项未满足条件的可追踪修订建议，供代理人与发明人定位补证缺口。
    list_findings = [
        {
            "level": "major",  # 语义缺陷严重级别
            "code": f"quality_{str_name}_missing",  # 稳定缺陷编号
            "message": f"{str_name} 章节缺少可审阅的完整内容。",  # 缺陷说明文本
            "suggestion": "补充与现有证据直接对应的技术描述。",  # 定向修订建议
        }
        for str_name, bool_passed in dict_checks.items()  # 当前质量条件名称和判定结果
        if not bool_passed  # 仅收录未通过的质量条件
    ]

    # 计算四项质量条件的累计得分，避免只检查文件存在或章节非空。
    int_score = sum(25 for bool_passed in dict_checks.values() if bool_passed)  # 正文质量总分

    # 依据语义缺陷和视觉审阅完成情况收敛唯一流程状态。
    str_status = (  # 统一流程状态
        "needs_revision"  # 存在语义缺陷时优先回到修订态
        if list_findings  # 缺陷列表非空时不得进入视觉验收或完成态
        else ("completed" if bool_visual_review_complete else "visual_review_required")  # 语义通过后的视觉状态
    )

    # 返回评分卡全文，供 JSON 报告、流水线状态和人工审阅共用同一事实来源。
    return {
        "status": str_status,  # 评分卡流程状态
        "score": int_score,  # 正文质量分值
        "checks": dict_checks,  # 各质量条件结果
        "findings": list_findings,  # 可追踪语义缺陷列表
    }
