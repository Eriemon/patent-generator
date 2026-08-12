"""依据受管审查合同评估交底书、创造性和权利要求支撑质量。"""

# 延迟解析类型注解，避免运行时导入仅用于类型声明的对象。
from __future__ import annotations

# 标准库用于读取合同资产并处理受管路径。
import json
from pathlib import Path
from typing import Any

# 固定正式合同资产位置，确保生成链和验证链读取同一规则源。
PATH_EXAMINATION_CONTRACT = Path(__file__).resolve().parents[3] / "assets" / "examination_quality_contract.json"  # 统一审查合同路径

# 限定允许写入案件配置的技术profile，拒绝静默接受未知类型。
SET_TECHNICAL_PROFILES = {"general", "ai_algorithm"}  # 合法技术profile集合

# 限定AI专项规则的适用范围，分别覆盖训练和场景应用。
SET_AI_SCOPES = {"model_training", "model_application", "both"}  # 合法AI适用范围集合

# 汇总能够提示AI案件的高置信技术术语，提示结果仍需用户确认。
TUPLE_AI_INDICATORS = (  # 疑似AI案件术语集合
    "人工智能",  # 中文AI总称
    "机器学习",  # 机器学习方法
    "深度学习",  # 深度学习方法
    "神经网络",  # 神经网络模型
    "模型训练",  # 模型训练过程
    "训练参数",  # 训练参数配置
    "特征向量",  # 常见模型输入表示
    "machine learning",  # 英文机器学习术语
    "neural network",  # 英文神经网络术语
    "deep learning",  # 英文深度学习术语
)

# 读取机器可读审查合同并执行最小结构校验。
def load_examination_contract(path_contract: Path | None = None) -> dict[str, Any]:
    """读取统一审查合同资产。

    参数：
    - `path_contract`：可选合同路径；未提供时读取正式技能资产。

    返回：
    - `dict[str, Any]`：可供评估函数消费的合同内容。

    异常：
    - `FileNotFoundError`：合同资产不存在时抛出。
    - `ValueError`：合同缺少版本、来源或规则时抛出。
    """

    # 优先使用调用方显式路径，否则固定读取正式合同资产。
    path_selected_contract = path_contract or PATH_EXAMINATION_CONTRACT  # 本次读取的合同路径

    # 合同缺失会破坏审查可追溯性，必须立即停止。
    if not path_selected_contract.exists():

        # 抛出带真实目标的错误，便于定位安装包或源码缺件。
        raise FileNotFoundError(f"> ERR: [Python] 缺少统一审查合同：{path_selected_contract}")

    # 解析UTF-8 JSON，保留中文规则说明和来源标题。
    dict_contract = json.loads(path_selected_contract.read_text(encoding="utf-8"))  # 审查合同结构化内容

    # 核心字段缺失时拒绝使用不完整合同产生审查结论。
    if not dict_contract.get("contract_version") or not dict_contract.get("sources") or not dict_contract.get("rules"):

        # 使用稳定错误前缀报告合同结构损坏。
        raise ValueError("> ERR: [Python] 统一审查合同缺少版本、来源或规则。")

    # 返回已完成最小结构校验的合同内容。
    return dict_contract

# 把研究事实中的可读文本汇总为profile提示输入。
def collect_profile_text(dict_research_facts: dict[str, Any]) -> str:
    """汇总技术术语和候选发明点文本。

    参数：
    - `dict_research_facts`：事实抽取阶段输出的研究事实。

    返回：
    - `str`：用于AI术语提示的归一化小写文本。

    异常：
    - 无；缺失字段按空集合处理。
    """

    # 收集顶层技术术语，保留研发材料中的原始表达。
    list_text_parts = [str(str_term) for str_term in dict_research_facts.get("technical_terms", [])]  # profile提示文本片段

    # 候选名称和方案可补足顶层技术术语遗漏的AI信号。
    for dict_candidate in dict_research_facts.get("candidate_invention_points", []):

        # 候选名称和方案能够补足顶层术语遗漏的案件类型信号。
        list_candidate_parts = [  # 当前候选的可检索文本片段
            str(dict_candidate.get("name", "")),  # 候选发明点名称
            str(dict_candidate.get("solution", "")),  # 候选技术方案摘要
            " ".join(str(str_term) for str_term in dict_candidate.get("technical_terms", [])),  # 候选技术术语
        ]

        # 把当前候选文本并入统一提示语料。
        list_text_parts.extend(list_candidate_parts)

    # 合并并转为小写，支持中英文术语稳定匹配。
    return " ".join(list_text_parts).lower()

# 识别疑似AI材料并返回可解释的提示原因。
def suggest_technical_profile(dict_research_facts: dict[str, Any]) -> dict[str, Any]:
    """根据研究事实给出非强制技术profile建议。

    参数：
    - `dict_research_facts`：事实抽取阶段输出的研究事实。

    返回：
    - `dict[str, Any]`：建议profile及命中的提示术语。

    异常：
    - 无；无法识别时建议保持通用profile。
    """

    # 汇总当前案件可用于类型提示的研究文本。
    str_profile_text = collect_profile_text(dict_research_facts)  # 归一化profile提示文本

    # 保留实际命中的术语，供预览阶段向用户解释建议依据。
    list_matched_indicators = [  # 命中的AI提示术语
        str_indicator  # 原始受管术语
        for str_indicator in TUPLE_AI_INDICATORS  # 遍历高置信AI术语集合
        if str_indicator in str_profile_text  # 只保留当前材料真实出现的术语
    ]

    # 任一高置信术语命中时仅建议AI专项，不直接改变案件配置。
    str_suggested_profile = "ai_algorithm" if list_matched_indicators else "general"  # 建议技术profile

    # 返回可供预览状态持久化的profile提示结果。
    return {
        "suggested_profile": str_suggested_profile,  # 系统建议的技术profile
        "reason_codes": list_matched_indicators,  # 触发建议的具体术语
    }

# 合并案件配置、自动建议和用户决定，形成可审计profile状态。
def build_profile_check(
    dict_case_config: dict[str, Any],
    dict_research_facts: dict[str, Any],
    str_confirmed_profile: str = "",
) -> dict[str, Any]:
    """构造技术profile确认状态。

    参数：
    - `dict_case_config`：案件配置，包含已保存的技术profile和AI范围。
    - `dict_research_facts`：用于生成非强制profile建议的研究事实。
    - `str_confirmed_profile`：本轮用户明确确认的profile；空值表示尚未确认。

    返回：
    - `dict[str, Any]`：配置值、建议值、决定和确认门状态。

    异常：
    - `ValueError`：配置或确认profile不是受支持值时抛出。
    """

    # 读取案件显式配置，旧案件缺失时保持通用profile兼容行为。
    str_configured_profile = str(dict_case_config.get("technical_profile", "general"))  # 已保存技术profile

    # 未知profile会导致规则错误适用，必须在评估前阻断。
    if str_configured_profile not in SET_TECHNICAL_PROFILES:

        # 报告非法配置值并要求调用方修复案件配置。
        raise ValueError(f"> ERR: [Python] 不支持的technical_profile：{str_configured_profile}")

    # 用户确认值存在时也必须经过同一受管枚举校验。
    if str_confirmed_profile and str_confirmed_profile not in SET_TECHNICAL_PROFILES:

        # 防止命令行确认把未知profile写入预览状态。
        raise ValueError(f"> ERR: [Python] 不支持的确认profile：{str_confirmed_profile}")

    # 计算研究材料建议，建议本身不具有修改配置的权限。
    dict_suggestion = suggest_technical_profile(dict_research_facts)  # 非强制profile建议

    # 读取建议profile，供后续判断是否需要询问用户。
    str_suggested_profile = str(dict_suggestion["suggested_profile"])  # 系统建议技术profile

    # 用户在本轮给出确认时，以确认值作为有效profile并记录决定类型。
    if str_confirmed_profile:

        # 区分保持通用与切换AI，便于预览状态清楚展示用户决定。
        str_decision = "keep_general" if str_confirmed_profile == "general" else "switch_to_ai_algorithm"  # 用户profile决定

        # 返回已解除确认门的profile状态。
        return {
            "configured_profile": str_configured_profile,  # 确认前保存的案件类型
            "suggested_profile": str_suggested_profile,  # 与用户决定并列展示的系统建议
            "effective_profile": str_confirmed_profile,  # 本轮用户选择
            "confirmation_required": False,  # 表示无需再次询问
            "decision": str_decision,  # 本轮选择的审计标签
            "reason_codes": dict_suggestion["reason_codes"],  # 触发建议的材料术语
        }

    # 已显式配置AI的案件视为建案时完成确认，无需重复询问。
    if str_configured_profile == "ai_algorithm":

        # 返回配置直接生效的AI profile状态。
        return {
            "configured_profile": str_configured_profile,  # 建案时明确选择的AI类型
            "suggested_profile": str_suggested_profile,  # 材料识别给出的辅助建议
            "effective_profile": str_configured_profile,  # 建案选择直接生效
            "confirmation_required": False,  # 显式AI配置已经完成确认
            "decision": "configured",  # 标记配置直接生效
            "reason_codes": dict_suggestion["reason_codes"],  # 支撑提示的术语证据
        }

    # 通用配置与AI建议冲突时必须等待用户确认，不能静默切换。
    bool_confirmation_required = str_suggested_profile == "ai_algorithm"  # 是否需要用户确认AI建议

    # 返回预览阶段需要持久化的待确认或普通状态。
    return {
        "configured_profile": str_configured_profile,  # 当前仍保存的通用类型
        "suggested_profile": str_suggested_profile,  # 材料识别出的候选类型
        "effective_profile": str_configured_profile,  # 未确认前不得自动切换
        "confirmation_required": bool_confirmation_required,  # 是否暂停等待询问
        "decision": "pending" if bool_confirmation_required else "not_required",  # 预览阶段的确认状态
        "reason_codes": dict_suggestion["reason_codes"],  # 展示给用户的触发词
    }

# 向统一finding列表追加一条稳定、可操作的审查问题。
def add_finding(
    list_findings: list[dict[str, str]],
    str_level: str,
    str_code: str,
    str_message: str,
    str_action: str,
) -> None:
    """追加统一审查finding。

    参数：
    - `list_findings`：待扩展的审查问题列表。
    - `str_level`：`blocker`、`major`或`minor`。
    - `str_code`：供测试和状态机消费的稳定错误码。
    - `str_message`：面向审阅者的问题说明。
    - `str_action`：研发人员或代理人的补正动作。

    返回：
    - `None`：函数原地扩展问题列表。

    异常：
    - 无；级别和错误码由受管调用方提供。
    """

    # 以现有验证报告兼容的字段结构登记审查问题。
    list_findings.append(
        {
            "level": str_level,  # 问题严重级别
            "code": str_code,  # 稳定问题编号
            "message": str_message,  # 可读问题说明
            "action": str_action,  # 建议补正动作
        }
    )

# 判断最接近现有技术记录是否形成完整创造性推理链。
def has_complete_inventiveness_chain(dict_record: dict[str, Any]) -> bool:
    """检查单条先前技术记录的创造性推理字段。

    参数：
    - `dict_record`：已核验的最接近现有技术记录。

    返回：
    - `bool`：区别特征、效果、实际问题和技术启示均存在时为真。

    异常：
    - 无；缺失字段按不完整处理。
    """

    # 规范化区别特征文本，空白条目不能计入完整推理链。
    list_different_features = [  # 有效区别特征列表
        str(obj_feature).strip()  # 统一转成可用于效果映射的文本键
        for obj_feature in dict_record.get("different_features", [])  # 原始区别特征条目
        if str(obj_feature).strip()  # 过滤空白区别特征
    ]

    # 区别特征必须存在，才能继续评价其技术效果和技术启示。
    bool_has_differences = bool(list_different_features)  # 是否存在有效区别特征

    # 逐特征效果必须使用对象映射，禁止旧版单一效果文本掩盖局部缺口。
    obj_difference_effects = dict_record.get("difference_effects")  # 原始区别效果映射

    # 每项区别特征都要有非空效果说明，才算完成效果链。
    bool_has_difference_effects = isinstance(obj_difference_effects, dict) and all(  # 是否逐项解释区别效果
        bool(str(obj_difference_effects.get(str_feature, "")).strip())  # 当前区别特征的效果说明是否有效
        for str_feature in list_different_features  # 遍历全部有效区别特征
    )

    # 实际技术问题必须由区别特征产生的效果重新确定，空白文本不接受。
    bool_has_actual_problem = bool(str(dict_record.get("actual_technical_problem", "")).strip())  # 是否给出实际技术问题

    # 技术启示必须结构化记录结论和依据，避免只有空泛判断。
    obj_technical_motivation = dict_record.get("technical_motivation")  # 原始技术启示对象

    # 非对象载荷降级为空映射，使结论和证据检查共同失败。
    dict_technical_motivation = (  # 规范化技术启示对象
        obj_technical_motivation  # 保留结构化技术启示字段
        if isinstance(obj_technical_motivation, dict)  # 只接受对象合同
        else {}  # 字符串或其他旧载荷按不完整处理
    )

    # 读取技术启示结论，空映射会自然得到空文本。
    str_motivation_conclusion = str(dict_technical_motivation.get("conclusion", "")).strip()  # 技术启示结论

    # 读取证据载荷，后续兼容单条文本和证据列表。
    obj_motivation_evidence = dict_technical_motivation.get("evidence")  # 技术启示证据

    # 证据列表至少包含一条非空说明，单条文本则必须去空白后非空。
    bool_has_motivation_evidence = (  # 技术启示是否包含可回查证据
        any(bool(str(obj_item).strip()) for obj_item in obj_motivation_evidence)  # 证据列表中存在有效条目
        if isinstance(obj_motivation_evidence, list)  # 列表证据分支
        else bool(str(obj_motivation_evidence or "").strip())  # 单条证据文本分支
    )

    # 结论和证据同时存在时才认为技术启示判断完整。
    bool_has_motivation = bool(str_motivation_conclusion) and bool_has_motivation_evidence  # 是否记录技术启示及依据

    # 四段推理链全部存在时才视为创造性评估就绪。
    return bool_has_differences and bool_has_difference_effects and bool_has_actual_problem and bool_has_motivation

# 检查查新记录是否足以支持创造性审阅。
def append_inventiveness_findings(
    list_prior_art_records: list[dict[str, Any]],
    list_findings: list[dict[str, str]],
) -> None:
    """把创造性推理缺项追加到统一finding列表。

    参数：
    - `list_prior_art_records`：已核验的先前技术记录。
    - `list_findings`：待扩展的统一审查问题列表。

    返回：
    - `None`：函数原地扩展问题列表。

    异常：
    - 无；空记录由既有先前技术硬门处理。
    """

    # 没有记录时交由既有missing_verified_prior_art规则处理，避免重复finding。
    if not list_prior_art_records:

        # 空记录不在本函数重复报告。
        return

    # 至少一条记录形成完整链即可进入人工创造性审阅。
    bool_has_complete_record = any(  # 是否存在完整创造性链
        has_complete_inventiveness_chain(dict_record)  # 当前记录是否具备完整推理字段
        for dict_record in list_prior_art_records  # 遍历已核验的现有技术记录
    )

    # 所有记录都缺少推理字段时要求补充，而不是把浅层查新当作创造性结论。
    if not bool_has_complete_record:

        # 以major进入needs_revision，阻止不完整创造性分析进入正式交付。
        add_finding(
            list_findings,
            "major",
            "inventiveness_chain_incomplete",
            "现有技术记录尚未形成区别特征、技术效果、实际技术问题和技术启示的完整推理链。",
            "补齐区别特征对应效果、重新确定的实际技术问题，以及技术启示及其证据。",
        )

# 根据新版claims_map执行分级权利要求支撑检查。
def append_claim_support_findings(
    dict_claims_map: dict[str, Any],
    list_findings: list[dict[str, str]],
) -> None:
    """把权利要求支撑问题追加到统一finding列表。

    参数：
    - `dict_claims_map`：权利要求生成阶段输出的新版映射。
    - `list_findings`：待扩展的统一审查问题列表。

    返回：
    - `None`：函数原地扩展问题列表。

    异常：
    - 无；旧版或空映射由现有兼容路径继续处理。
    """

    # 遍历实际生成的权利要求，主权项缺失支撑时进入硬门。
    for dict_claim in dict_claims_map.get("claims", []):

        # 只对方法或其他客体的独立权利要求执行阻断级支撑检查。
        str_claim_type = str(dict_claim.get("claim_type", ""))  # 当前权利要求类型

        # 从属项由生成阶段过滤，本函数只处理独立项必要特征。
        if not str_claim_type.startswith("independent_"):

            # 跳过非独立项，避免把次级候选错误升级为blocker。
            continue

        # 显式unsupported或缺少全部证据都说明主权项没有说明书支撑。
        bool_is_unsupported = dict_claim.get("support_status") == "unsupported" or not dict_claim.get("support_ids")  # 主权项是否无支撑

        # 无支撑主权项会直接影响保护范围合法基础，必须阻断。
        if bool_is_unsupported:

            # 登记一次稳定blocker，具体缺失特征保留在claims_map中供补料。
            add_finding(
                list_findings,
                "blocker",
                "unsupported_independent_claim",
                f"独立权利要求{dict_claim.get('claim_no', '')}存在未被说明书或研发材料支撑的必要特征。",
                "补齐必要特征的说明书展开和来源证据，或从主权项删除无支撑特征。",
            )

    # 汇总被安全省略的次级候选，保持提示可见但不阻断交底书主交付。
    list_omitted_candidates = list(dict_claims_map.get("omitted_candidates", []))  # 被省略的次级候选

    # 存在省略候选时只追加一条minor摘要，避免重复finding淹没主问题。
    if list_omitted_candidates:

        # 提示审阅者补料后可重新生成，但当前交底书仍可继续审阅。
        add_finding(
            list_findings,
            "minor",
            "unsupported_secondary_claim_omitted",
            f"已省略{len(list_omitted_candidates)}个缺少材料支撑的从属或其他客体权利要求候选。",
            "如需恢复候选保护方向，请先在研发材料和说明书中补齐相应技术特征。",
        )

# 判断结构化AI披露对象是否包含指定非空字段。
def has_required_fields(dict_section: dict[str, Any], tuple_fields: tuple[str, ...]) -> bool:
    """检查AI专项披露对象的必要字段。

    参数：
    - `dict_section`：模型结构、训练过程或场景结合对象。
    - `tuple_fields`：当前规则要求的字段名集合。

    返回：
    - `bool`：全部字段均为非空值时为真。

    异常：
    - 无；缺失或空值按不完整处理。
    """

    # 先收集必要字段值，避免空白文本绕过可实施细节检查。
    list_field_values = [dict_section.get(str_field) for str_field in tuple_fields]  # 必要字段原始值

    # 字符串必须包含可见内容，列表和对象等其他类型沿用非空语义。
    return all(
        bool(obj_value.strip()) if isinstance(obj_value, str) else bool(obj_value)
        for obj_value in list_field_values
    )

# 按案件AI范围追加模型、训练、场景和伦理finding。
def append_ai_findings(
    dict_case_config: dict[str, Any],
    dict_research_facts: dict[str, Any],
    list_findings: list[dict[str, str]],
) -> None:
    """把AI专项披露缺项追加到统一finding列表。

    参数：
    - `dict_case_config`：包含technical_profile和ai_scope的案件配置。
    - `dict_research_facts`：包含ai_disclosure的研究事实。
    - `list_findings`：待扩展的统一审查问题列表。

    返回：
    - `None`：函数原地扩展问题列表。

    异常：
    - 无；非法scope转换为稳定blocker。
    """

    # 普通案件不适用AI专项规则，避免产生无关缺项。
    if dict_case_config.get("technical_profile", "general") != "ai_algorithm":

        # 通用profile直接结束AI专项检查。
        return

    # 读取AI适用范围，决定训练和应用规则的条件组合。
    str_ai_scope = str(dict_case_config.get("ai_scope", ""))  # 当前AI专项适用范围

    # 缺失或非法scope会导致规则无法正确适用，必须阻断并停止专项细分。
    if str_ai_scope not in SET_AI_SCOPES:

        # 要求建案或确认阶段明确选择训练、应用或两者。
        add_finding(
            list_findings,
            "blocker",
            "ai_scope_missing",
            "AI案件尚未明确属于模型训练、场景应用或两者兼有。",
            "在case_config.json中补充ai_scope后重新执行审查。",
        )

        # scope不确定时无法安全决定后续字段要求。
        return

    # 读取AI专项事实对象，缺失时按空对象执行条件门。
    dict_ai_disclosure = dict(dict_research_facts.get("ai_disclosure", {}))  # AI专项披露事实

    # 模型训练或both案件必须说明必要模块、层级和连接关系。
    if str_ai_scope in {"model_training", "both"}:

        # 提取模型结构对象，供三个必要字段联合判断。
        dict_model_structure = dict(dict_ai_disclosure.get("model_structure", {}))  # 模型结构披露

        # 模型结构不完整时报告独立blocker，便于精确补充。
        if not has_required_fields(dict_model_structure, ("modules_or_layers", "connections", "purpose")):

            # 阻止只有模型名称、没有结构关系的描述进入正式交底书。
            add_finding(
                list_findings,
                "blocker",
                "ai_model_structure_missing",
                "AI训练方案缺少必要模块或层级、连接关系及其用途说明。",
                "补充模型必要组成、层级或模块连接关系以及各部分承担的处理作用。",
            )

        # 提取训练过程对象，检查数据、步骤和关键参数是否足以复现。
        dict_training_process = dict(dict_ai_disclosure.get("training_process", {}))  # 模型训练过程披露

        # 训练过程字段缺失会导致所属技术领域人员无法实施。
        if not has_required_fields(dict_training_process, ("data_source", "steps", "key_parameters")):

            # 以充分公开相关blocker要求研发人员补充训练细节。
            add_finding(
                list_findings,
                "blocker",
                "ai_training_process_missing",
                "AI训练方案缺少训练数据来源、训练步骤或关键参数说明。",
                "补充数据来源和处理方式、训练步骤，以及影响模型行为的关键参数或参数来源。",
            )

    # 场景应用或both案件必须解释模型与具体技术场景的内在结合。
    if str_ai_scope in {"model_application", "both"}:

        # 提取场景结合对象，检查场景、输入、输出和关联机制。
        dict_scenario_integration = dict(dict_ai_disclosure.get("scenario_integration", {}))  # AI场景结合披露

        # 场景关系不完整时阻止仅罗列算法名称的方案进入正式交付。
        bool_has_scenario_details = has_required_fields(  # 场景结合字段是否齐全
            dict_scenario_integration,  # 当前案件的场景结合事实
            ("scenario", "input_semantics", "output_semantics", "relationship"),  # 必要披露字段
        )

        # 根据联合检查结果决定是否登记应用场景缺项。
        if not bool_has_scenario_details:

            # 要求写清输入输出如何服务具体技术问题和技术效果。
            add_finding(
                list_findings,
                "blocker",
                "ai_scenario_integration_missing",
                "AI应用方案缺少具体场景、输入输出语义或二者内在关联。",
                "补充模型如何嵌入具体技术场景，以及输入、输出与技术问题之间的关系。",
            )

    # 所有AI案件都需要人工复核伦理、法律和公共利益风险。
    dict_ethics_review = dict(dict_ai_disclosure.get("ethics_review", {}))  # AI伦理与公共利益复核记录

    # 固化人工复核状态，区分未复核与已识别风险两类处置路径。
    str_ethics_status = str(dict_ethics_review.get("status", ""))  # AI伦理人工复核状态

    # 缺失或非法状态表示尚未完成可核验的人工复核。
    if str_ethics_status not in {"reviewed_no_issue", "reviewed_issue_identified"}:

        # 伦理结论不能由文本规则自动代替，保持major并要求人工复核。
        add_finding(
            list_findings,
            "major",
            "ai_ethics_review_pending",
            "AI案件尚未记录伦理、法律和公共利益人工复核状态。",
            "由专利代理人或合规人员完成复核并记录结论；本工具不自动作出法律判断。",
        )

    # 已识别风险不能因完成复核而静默通过，必须保留人工处置项。
    elif str_ethics_status == "reviewed_issue_identified":

        # 工具仅暴露风险，不替代代理人或合规人员作出法律结论。
        add_finding(
            list_findings,
            "major",
            "ai_ethics_issue_identified",
            "AI案件的人工复核已识别伦理、法律或公共利益风险。",
            "由专利代理人或合规人员审查风险摘要和证据，并记录处置结论；本工具不自动作出法律判断。",
        )

# 统一执行创造性、权利要求支撑和AI专项评估。
def assess_examination_quality(
    dict_case_config: dict[str, Any],
    dict_research_facts: dict[str, Any],
    list_prior_art_records: list[dict[str, Any]],
    dict_claims_map: dict[str, Any],
) -> dict[str, Any]:
    """评估当前案件的审查准备度。

    参数：
    - `dict_case_config`：案件技术profile和AI适用范围。
    - `dict_research_facts`：研发事实及可选AI专项披露。
    - `list_prior_art_records`：已核验的最接近现有技术记录。
    - `dict_claims_map`：实际生成权利要求及被省略候选的支撑映射。

    返回：
    - `dict[str, Any]`：合同版本、适用profile、状态和统一findings。

    异常：
    - 合同资产损坏或profile非法时由底层校验异常上抛。
    """

    # 读取合同版本和来源，保证每份评估结果可以回溯到受管规则。
    dict_contract = load_examination_contract()  # 当前生效审查合同

    # 初始化统一finding列表，后续各规则族只追加标准结构。
    list_findings: list[dict[str, str]] = []  # 统一审查问题列表

    # 先评估现有技术记录能否支撑创造性判断。
    append_inventiveness_findings(list_prior_art_records, list_findings)

    # 再核对实际生成主权项与省略候选的材料支撑。
    append_claim_support_findings(dict_claims_map, list_findings)

    # 最后按案件profile执行条件化AI专项规则。
    append_ai_findings(dict_case_config, dict_research_facts, list_findings)

    # 收集问题级别，供统一状态机按blocker优先级决策。
    set_finding_levels = {str(dict_item["level"]) for dict_item in list_findings}  # 本次finding级别集合

    # blocker存在时案件不能进入正式交付。
    if "blocker" in set_finding_levels:

        # 记录最高风险状态供验证入口直接消费。
        str_status = "blocked"  # 审查评估阻断状态

    # major存在时要求修订，minor本身不阻断主交付。
    elif "major" in set_finding_levels:

        # 记录需要修订状态，等待补齐审查链。
        str_status = "needs_revision"  # 审查评估修订状态

    # 没有blocker或major时视为通过自动辅助检查。
    else:

        # minor提示仍保留在findings中供人工审阅。
        str_status = "pass"  # 审查评估通过状态

    # 返回带合同来源和适用profile的可审计评估结果。
    return {
        "contract_version": str(dict_contract["contract_version"]),  # 审查合同版本
        "effective_from": str(dict_contract["effective_from"]),  # 合同生效日期
        "technical_profile": str(dict_case_config.get("technical_profile", "general")),  # 实际适用profile
        "status": str_status,  # 统一审查状态
        "findings": list_findings,  # 结构化审查问题
    }
