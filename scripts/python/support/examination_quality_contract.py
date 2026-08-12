"""依据受管审查合同评估交底书、创造性和权利要求支撑质量。"""

# 延迟解析类型注解，避免运行时导入仅用于类型声明的对象。
from __future__ import annotations

# 标准库处理加载路径。
import importlib.util
import json
from pathlib import Path
from collections.abc import Callable, Mapping
from typing import Any

# 固定正式合同资产位置，确保生成链和验证链读取同一规则源。
PATH_EXAMINATION_CONTRACT = Path(__file__).resolve().parents[3] / "assets" / "examination_quality_contract.json"  # 统一审查合同路径

# 固定拆分后的领域规则支持路径。
PATH_RULE_SUPPORT = Path(__file__).resolve().parent / "examination_rule_support.py"  # 创造性与字段闭包支持模块路径

# 固定合同引擎职责模块，主入口不再自行拥有 schema 和 registry 规则。
PATH_RULE_ENGINE = Path(__file__).resolve().parent / "examination_rule_engine.py"  # 合同验证与执行引擎路径

# 固定 AI 状态职责模块，活动确认只能复用 Task1 哈希验证。
PATH_AI_APPLICABILITY = Path(__file__).resolve().parent / "ai_applicability.py"  # AI 适用性状态模块路径

# 限定允许写入案件配置的技术profile，拒绝静默接受未知类型。
SET_TECHNICAL_PROFILES = {"general", "ai_algorithm"}  # 合法技术profile集合

# 限定AI专项规则的适用范围，分别覆盖训练和场景应用。
SET_AI_SCOPES = {"model_training", "model_application", "both"}  # 合法AI适用范围集合

# 固定规则严重级别，合同和运行时都不得接受自造等级。
SET_RULE_LEVELS = {"blocker", "major", "minor"}  # 合法审查finding级别

# 固定系统可观察的AI信号强度，避免把关键词提示伪装成确定事实。
SET_AI_SIGNAL_LEVELS = {"hard", "soft", "none"}  # 合法AI信号级别

# AI提示术语只形成材料信号。
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

# 按路径加载领域规则支持。
def load_rule_support_module() -> Any:
    """加载领域规则支持模块。

    参数：
    - 无。

    返回：
    - `Any`：支持模块。

    异常：
    - `ImportError`：加载失败时抛出。
    """

    # 稳定内部名称不污染模块搜索路径。
    str_module_name = "readable_patent_examination_rule_support"  # 规则支持模块内部名称

    # 从受管文件构造加载规格。
    obj_specification = importlib.util.spec_from_file_location(str_module_name, PATH_RULE_SUPPORT)  # 规则支持加载规格

    # 规格损坏时禁止跳过领域检查。
    if obj_specification is None or obj_specification.loader is None:

        # 报告支持模块缺件。
        raise ImportError("> ERR: [Python] 无法加载 examination_rule_support.py。")

    # 创建隔离模块实例。
    module_support = importlib.util.module_from_spec(obj_specification)  # 规则支持模块实例

    # 执行受管支持源码。
    obj_specification.loader.exec_module(module_support)

    # 返回已初始化模块。
    return module_support

# 加载一次支持模块，保持同一评估中的函数身份稳定。
MODULE_RULE_SUPPORT = load_rule_support_module()  # 已初始化规则支持模块

# 保留既有公共接口名称，调用方无需感知内部拆分。
has_complete_inventiveness_chain = MODULE_RULE_SUPPORT.has_complete_inventiveness_chain  # 创造性链完整性检查

# 规则handler继续复用相同的创造性finding语义。
append_inventiveness_findings = MODULE_RULE_SUPPORT.append_inventiveness_findings  # 创造性缺口追加入口

# AI和技术贡献handler复用统一非空字段语义。
has_required_fields = MODULE_RULE_SUPPORT.has_required_fields  # 结构化必要字段检查

# 按职责模块路径加载实现，避免兼容入口依赖 sys.path。
def load_responsibility_module(str_module_name: str, path_module: Path) -> Any:
    """加载审查合同的独立职责模块。

    参数：
    - `str_module_name`：当前进程中的隔离模块名。
    - `path_module`：待执行的正式职责模块路径。

    返回：
    - `Any`：已经执行源码的模块对象。

    异常：
    - `ImportError`：路径规格或加载器缺失时抛出。
    """

    # 从明确路径构造加载规格，禁止模糊模块搜索。
    obj_specification = importlib.util.spec_from_file_location(str_module_name, path_module)  # 当前职责模块加载规格

    # 职责模块缺失时不得回退主文件内的旧实现。
    if obj_specification is None or obj_specification.loader is None:

        # 错误保留真实路径，便于定位安装或源码缺件。
        raise ImportError(f"> ERR: [Python] 无法加载审查职责模块：{path_module}")

    # 创建隔离模块对象并执行受管源码。
    module_loaded = importlib.util.module_from_spec(obj_specification)  # 当前职责模块对象

    # 执行正式实现后再返回给兼容层。
    obj_specification.loader.exec_module(module_loaded)

    # 返回已经初始化的职责模块。
    return module_loaded

# 合同引擎在模块初始化时固定，全部调用共享相同字段闭包。
MODULE_RULE_ENGINE = load_responsibility_module(  # Contract 2.0 规则引擎
    "readable_patent_examination_rule_engine",  # 规则引擎隔离模块名
    PATH_RULE_ENGINE,  # 独立规则引擎源码路径
)

# AI 状态模块共享 Task1 活动确认验证器。
MODULE_AI_APPLICABILITY = load_responsibility_module(  # AI 适用性状态实现
    "readable_patent_ai_applicability",  # AI 状态隔离模块名
    PATH_AI_APPLICABILITY,  # 独立 AI 状态源码路径
)

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

    # 先区分结构化硬事实与关键词软提示。
    # 材料信号用于决定AI规则强制级别，与profile配置和人工决定相互独立。
    dict_signal = classify_ai_signals(dict_research_facts)  # AI适用状态的材料侧输入

    # hard或soft都提示审阅者注意AI写作profile，但不自动修改配置。
    str_suggested_profile = (  # 建议技术profile
        "ai_algorithm"  # AI信号存在时给出专项写作建议
        if dict_signal["signal_level"] in {"hard", "soft"}  # hard和soft都需要解释
        else "general"  # 无信号时保持通用写作建议
    )

    # 返回可供预览状态持久化的profile提示结果。
    return {
        "suggested_profile": str_suggested_profile,  # 系统建议的技术profile
        "signal_level": dict_signal["signal_level"],  # hard、soft或none信号分级
        "reason_codes": dict_signal["reason_codes"],  # 触发建议的结构化字段或术语
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

    # 信号分级独立于写作profile，hard会强制AI规则而soft等待人工理由。
    str_signal_level = str(dict_suggestion["signal_level"])  # 当前AI信号级别

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
            "ai_signal_level": str_signal_level,  # 系统检测到的AI事实强度
            "ai_rules_mandatory": str_signal_level == "hard",  # hard事实不能被profile关闭
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
            "ai_signal_level": str_signal_level,  # AI规则适用性信号说明
            "ai_rules_mandatory": str_signal_level == "hard",  # hard事实始终强制规则
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
        "ai_signal_level": str_signal_level,  # 系统信号分级不修改写作profile
        "ai_rules_mandatory": str_signal_level == "hard",  # hard事实独立启用AI审查规则
        "reason_codes": dict_suggestion["reason_codes"],  # 展示给用户的触发词
    }

# 每类领域 finding 绑定可由审阅者回查的案件事实坐标。
DICT_EVIDENCE_BINDING_BY_CODE = {
    "delivery_model_missing": "context:delivery_model",  # 权威模型输入
    "sufficient_disclosure_missing": "delivery_model:sections",  # 章节容器
    "sufficient_disclosure_incomplete": "delivery_model:sections",  # 章节正文
    "feature_mechanism_effect_missing": "delivery_model:feature_registry",  # 稳定技术特征
    "feature_mechanism_effect_incomplete": "delivery_model:feature_registry",  # 特征机制与效果
    "inventiveness_chain_incomplete": "context:prior_art_records",  # 创造性对比链
    "technical_contribution_incomplete": "research_facts:technical_contribution",  # 技术贡献对象
    "unsupported_independent_claim": "claims_map:claims",  # 独立权利要求支撑
    "unsupported_secondary_claim_omitted": "claims_map:omitted_candidates",  # 次级候选支撑
    "ai_hard_override_forbidden": "delivery_model:rule_applicability",  # hard 越权决定
    "ai_soft_decision_required": "delivery_model:rule_applicability",  # soft 决定与理由
    "ai_confirmation_required": "delivery_model:semantic_review.human_confirmations",  # AI 活动确认
    "ai_scope_missing": "case_config:ai_scope",  # AI 适用范围
    "ai_model_structure_missing": "research_facts:ai_disclosure.model_structure",  # 模型结构披露
    "ai_training_process_missing": "research_facts:ai_disclosure.training_process",  # 训练过程披露
    "ai_scenario_integration_missing": "research_facts:ai_disclosure",  # 场景输入输出披露
    "ai_ethics_review_pending": "research_facts:ai_disclosure.ethics_review",  # 公共利益审查状态
    "ai_ethics_issue_identified": "research_facts:ai_disclosure.ethics_review",  # 已识别公共利益问题
}  # 领域错误码到案件事实坐标

# 构造不含严重级别的域检查结果，级别由规则引擎从JSON补齐。
def build_handler_finding(str_code: str, str_message: str, str_action: str) -> dict[str, Any]:
    """构造handler返回的领域finding。

    参数：
    - `str_code`：稳定行为错误码。
    - `str_message`：面向审阅者的问题说明。
    - `str_action`：补正动作。

    返回：
    - `dict[str, Any]`：不含 level、带事实坐标的 handler 结果。

    异常：
    - 无；调用方负责提供受管文本。
    """

    # 绑定位置由领域错误码决定，未知代码保持空集合并由 required 规则阻断。
    str_evidence_binding = DICT_EVIDENCE_BINDING_BY_CODE.get(str_code, "")  # 当前 finding 事实坐标

    # handler 拥有领域事实及其可回查坐标，不拥有严重级别。
    return {
        "code": str_code,  # 领域稳定错误码
        "message": str_message,  # 领域问题说明
        "action": str_action,  # 领域补正动作
        "evidence_bindings": [str_evidence_binding] if str_evidence_binding else [],  # 可核验案件事实坐标
    }

# 检查核心充分公开所需的正式模型和非空章节。
def handle_sufficient_disclosure(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查正式模型是否提供可审查章节。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：充分公开缺口。

    异常：
    - 无；缺失模型形成显式finding。
    """

    # 读取权威交付模型，直接评估调用不能以Markdown替代它。
    obj_delivery_model = dict_context.get("delivery_model")  # 当前权威模型对象

    # 正式模型缺失时无法确认章节语义和证据闭包。
    if not isinstance(obj_delivery_model, Mapping):

        # 要求正式入口提供当前Model4而不是猜测正文状态。
        return [
            build_handler_finding(
                "delivery_model_missing",
                "统一审查缺少当前权威Model 4.0。",
                "提供正式Model 4.0并完成语义审查后重新验证。",
            )
        ]

    # 读取章节数组，后续检查可见内容是否齐全。
    obj_sections = obj_delivery_model.get("sections")  # 正式章节原始容器

    # 非空章节数组是充分公开语义审查的最低输入边界。
    if not isinstance(obj_sections, list) or not obj_sections:

        # 阻止空模型获得充分公开通过状态。
        return [
            build_handler_finding(
                "sufficient_disclosure_missing",
                "Model 4.0缺少可审查的正式章节。",
                "从真实研发证据补齐章节后重新执行语义审查。",
            )
        ]

    # 任一章节缺少可见正文都说明充分公开尚未闭合。
    bool_has_empty_section = any(  # 是否存在空白或损坏章节
        not isinstance(dict_section, Mapping)  # 损坏章节记录
        or not str(dict_section.get("content", "")).strip()  # 缺少可见章节正文
        for dict_section in obj_sections  # 逐项检查正式章节
    )

    # 空章节不能由标题或章节数量掩盖。
    if bool_has_empty_section:

        # 返回可由JSON级别标注的领域finding。
        return [
            build_handler_finding(
                "sufficient_disclosure_incomplete",
                "Model 4.0仍含空白或损坏章节。",
                "逐章补齐可实施技术内容并绑定真实证据。",
            )
        ]

    # 章节均有可见正文时本handler不产生问题。
    return []

# 检查稳定技术特征是否解释作用机制和技术效果。
def handle_feature_mechanism(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查特征、机制和效果的因果闭包。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：机制或效果缺口。

    异常：
    - 无；缺失模型由充分公开handler报告。
    """

    # 读取权威模型中的稳定特征登记表。
    obj_delivery_model = dict_context.get("delivery_model")  # 当前权威模型

    # 模型缺失时避免和充分公开规则重复报告。
    if not isinstance(obj_delivery_model, Mapping):

        # 当前handler没有可检查特征。
        return []

    # 特征登记表负责承载方案到效果的正式闭包。
    obj_features = obj_delivery_model.get("feature_registry")  # 稳定技术特征原始值

    # 非空数组是机制效果检查的最低输入。
    if not isinstance(obj_features, list) or not obj_features:

        # 报告无法形成技术贡献的空登记表。
        return [
            build_handler_finding(
                "feature_mechanism_effect_missing",
                "Model 4.0缺少稳定技术特征及其效果闭包。",
                "逐项登记特征、作用机制、章节、证据和技术效果。",
            )
        ]

    # 收集缺少正文或技术效果的具体特征编号。
    list_incomplete_ids = [  # 机制效果闭包不完整的特征编号
        str(dict_feature.get("feature_id", ""))  # 当前问题特征稳定身份
        for dict_feature in obj_features  # 遍历正式特征登记表
        if not isinstance(dict_feature, Mapping)  # 损坏记录不能形成因果闭包
        or not str(dict_feature.get("text", "")).strip()  # 特征内容必须可见
        or not dict_feature.get("technical_effects")  # 技术效果必须非空
    ]

    # 存在任一缺口时形成一条可定位finding。
    if list_incomplete_ids:

        # 聚合编号避免同一根因淹没报告。
        return [
            build_handler_finding(
                "feature_mechanism_effect_incomplete",
                f"技术特征缺少机制或效果闭包：{list_incomplete_ids}",
                "依据研发证据补齐特征作用机制和可验证技术效果。",
            )
        ]

    # 全部稳定特征具备正文和效果时本handler通过。
    return []

# 将既有创造性链检查封装为无级别handler。
def handle_inventiveness_chain(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查区别特征到技术启示的完整推理链。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：创造性链缺口。

    异常：
    - 无。
    """

    # 调用既有领域检查，随后移除Python硬编码级别。
    list_legacy_findings: list[dict[str, str]] = []  # 既有创造性检查结果

    # 复用已经验证的区别效果和技术启示判断。
    append_inventiveness_findings(dict_context["prior_art_records"], list_legacy_findings)

    # 只保留领域代码、消息和动作，级别由JSON规则补齐。
    return [
        build_handler_finding(
            str(dict_item["code"]),
            str(dict_item["message"]),
            str(dict_item["action"]),
        )
        for dict_item in list_legacy_findings
    ]

# 检查材料显式提供的技术贡献对象是否形成特征、机制、效果链。
def handle_technical_contribution(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查显式技术贡献事实的三段闭包。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：技术贡献缺口。

    异常：
    - 无；未提供独立贡献对象时由特征handler覆盖。
    """

    # 读取可选技术贡献对象，避免对旧材料重复制造同义finding。
    obj_contribution = dict_context["research_facts"].get("technical_contribution")  # 技术贡献原始对象

    # 未声明独立对象时依赖Model4稳定特征闭包，不重复报告。
    if obj_contribution is None:

        # 当前材料没有额外贡献对象需要检查。
        return []

    # 非对象或三段字段不齐全时无法支撑创造性贡献结论。
    if not isinstance(obj_contribution, Mapping) or not has_required_fields(
        dict(obj_contribution),
        ("feature", "mechanism", "effect"),
    ):

        # 要求回到研发证据补齐因果链。
        return [
            build_handler_finding(
                "technical_contribution_incomplete",
                "技术贡献缺少区别特征、作用机制或技术效果。",
                "依据证据补齐三段因果链，不得仅写结论。",
            )
        ]

    # 显式技术贡献三段事实齐全时本handler通过。
    return []

# 检查独立权利要求是否缺少说明书或研发证据支撑。
def handle_independent_claims(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查独立权利要求支撑状态。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：无支撑独立项问题。

    异常：
    - 无；损坏claims容器按空集合处理。
    """

    # 读取实际生成的权利要求集合。
    obj_claims = dict_context["claims_map"].get("claims")  # 权利要求原始数组

    # 非数组值不在此层迭代，由claims schema负责结构错误。
    if not isinstance(obj_claims, list):

        # 返回空列表避免handler因坏类型中断总报告。
        return []

    # 收集无证据或显式unsupported的独立项。
    list_unsupported_claims = [  # 无材料支撑的独立项编号
        str(dict_claim.get("claim_no", ""))  # 当前独立权利要求编号
        for dict_claim in obj_claims  # 遍历实际生成的权利要求
        if isinstance(dict_claim, Mapping)  # 只读取结构化权利要求
        and str(dict_claim.get("claim_type", "")).startswith("independent_")  # 仅检查独立项
        and (  # 无支撑状态或空证据集合任一命中即纳入
            dict_claim.get("support_status") == "unsupported"  # 上游明确标记无支撑
            or not dict_claim.get("support_ids")  # 旧映射缺少任何证据编号
        )
    ]

    # 无支撑独立项直接影响保护范围基础。
    if list_unsupported_claims:

        # 聚合问题编号便于一次补齐全部支撑。
        return [
            build_handler_finding(
                "unsupported_independent_claim",
                f"独立权利要求缺少说明书或研发证据支撑：{list_unsupported_claims}",
                "补齐稳定特征、章节和证据闭包，或删除无支撑特征。",
            )
        ]

    # 所有独立项均有显式支撑时本handler通过。
    return []

# 汇总被安全省略的次级权利要求候选。
def handle_secondary_claims(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查因缺少证据而省略的次级保护方向。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：次级候选提示。

    异常：
    - 无。
    """

    # 读取生成器明确省略的候选集合。
    obj_omitted_candidates = dict_context["claims_map"].get("omitted_candidates")  # 被省略候选原始值

    # 只有非空数组需要形成可见提示。
    if isinstance(obj_omitted_candidates, list) and obj_omitted_candidates:

        # 保持次级保护方向可追溯但不提升为独立项阻断。
        return [
            build_handler_finding(
                "unsupported_secondary_claim_omitted",
                f"已省略{len(obj_omitted_candidates)}个缺少支撑的次级权利要求候选。",
                "如需恢复保护方向，先补齐研发材料和说明书支撑。",
            )
        ]

    # 没有省略候选时本handler通过。
    return []

# 阻止hard信号被人工not_applicable决定关闭。
def handle_hard_ai_applicability(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查hard AI事实的不可关闭边界。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：非法不适用覆盖问题。

    异常：
    - 无。
    """

    # hard事实上的not_applicable决定与可观察材料冲突。
    if dict_context["ai_applicability"]["decision"] == "not_applicable":

        # 明确告知人工决定不能覆盖hard信号。
        return [
            build_handler_finding(
                "ai_hard_override_forbidden",
                "明确AI模型、训练、推理或算法步骤事实不得标记为不适用。",
                "保持AI规则适用并完成相应披露和人工确认。",
            )
        ]

    # 其他决定不关闭hard规则，由确认handler继续检查记录闭包。
    return []

# 要求soft信号使用理由和正式确认收敛争议。
def handle_soft_ai_applicability(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查soft AI信号的人工理由与确认。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：soft争议未闭合问题。

    异常：
    - 无。
    """

    # disputed表示二值决定、具体理由或正式确认至少缺一项。
    if dict_context["ai_applicability"]["state"] == "disputed":

        # 系统不得根据关键词替代人工适用性判断。
        return [
            build_handler_finding(
                "ai_soft_decision_required",
                "AI关键词或含混上下文仍处于disputed状态。",
                "由人工记录applicable或not_applicable、具体理由和Model 4.0确认。",
            )
        ]

    # 有理由且已确认的soft决定完成本handler。
    return []

# 保持任何AI信号级别都需要正式人工适用性确认。
def handle_ai_confirmation(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查Model 4.0人工AI适用性确认。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：缺失人工确认问题。

    异常：
    - 无。
    """

    # 系统检测结果不能代替Model4活动人工确认记录。
    if not dict_context["ai_applicability"]["human_confirmed"]:

        # 无论hard、soft或none都保持同一人工确认边界。
        return [
            build_handler_finding(
                "ai_confirmation_required",
                "当前模型缺少AI规则适用性的正式人工确认。",
                "通过Model 4.0审查入口记录当前适用性对象的确认。",
            )
        ]

    # 当前AI适用性已经形成正式人工确认。
    return []

# 检查AI实体规则生效时是否声明训练或应用范围。
def handle_ai_scope(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查AI规则适用范围。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：缺失或非法范围问题。

    异常：
    - 无。
    """

    # ai_scope从案件配置读取，写作profile不参与该判断。
    str_ai_scope = str(dict_context["case_config"].get("ai_scope", ""))  # 当前AI规则范围

    # 缺失或非法范围无法选择训练和场景规则。
    if str_ai_scope not in SET_AI_SCOPES:

        # 要求调用方明确训练、应用或两者兼有。
        return [
            build_handler_finding(
                "ai_scope_missing",
                "AI规则适用时尚未明确训练、场景应用或两者兼有。",
                "在case_config.json中补充合法ai_scope。",
            )
        ]

    # 合法范围可供规则引擎继续选择AI实体规则。
    return []

# 检查训练类AI案件的模型结构披露。
def handle_ai_model_structure(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查AI模型组成、连接关系和用途。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：模型结构缺口。

    异常：
    - 无。
    """

    # 读取AI专项事实对象，损坏值按空对象处理。
    obj_ai_disclosure = dict_context["research_facts"].get("ai_disclosure")  # AI披露原始对象

    # 安全提取模型结构对象。
    dict_ai_disclosure = obj_ai_disclosure if isinstance(obj_ai_disclosure, Mapping) else {}  # 可读取AI披露

    # 非对象结构按缺失处理。
    obj_model_structure = dict_ai_disclosure.get("model_structure")  # 模型结构原始值

    # 规范为普通字典供必要字段检查使用。
    dict_model_structure = dict(obj_model_structure) if isinstance(obj_model_structure, Mapping) else {}  # 可检查模型结构

    # 必要模块、连接关系和用途必须同时存在。
    if not has_required_fields(dict_model_structure, ("modules_or_layers", "connections", "purpose")):

        # 阻止只有模型名称的方案进入正式交付。
        return [
            build_handler_finding(
                "ai_model_structure_missing",
                "AI方案缺少必要模块或层级、连接关系及其用途。",
                "补充模型组成、连接关系和各部分处理作用。",
            )
        ]

    # 模型结构披露完整时本handler通过。
    return []

# 检查训练数据来源、步骤和关键参数。
def handle_ai_training_process(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查AI训练过程可实施细节。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：训练过程缺口。

    异常：
    - 无。
    """

    # 从研究事实读取训练披露，避免其他AI事实影响字段闭包。
    obj_ai_disclosure = dict_context["research_facts"].get("ai_disclosure")  # 训练披露所属AI事实对象

    # 损坏对象不能提供训练事实。
    dict_ai_disclosure = obj_ai_disclosure if isinstance(obj_ai_disclosure, Mapping) else {}  # 可读取训练事实容器

    # 提取训练过程映射，其他类型按空对象处理。
    obj_training_process = dict_ai_disclosure.get("training_process")  # 训练过程原始值

    # 规范训练对象供字段闭包检查使用。
    dict_training_process = dict(obj_training_process) if isinstance(obj_training_process, Mapping) else {}  # 可检查训练过程

    # 数据来源、步骤和关键参数共同决定训练方案是否可实施。
    if not has_required_fields(dict_training_process, ("data_source", "steps", "key_parameters")):

        # 返回训练公开缺口供JSON级别标注。
        return [
            build_handler_finding(
                "ai_training_process_missing",
                "AI训练方案缺少数据来源、训练步骤或关键参数。",
                "补充数据处理、训练流程和影响模型行为的参数依据。",
            )
        ]

    # 训练过程三项事实齐全时本handler通过。
    return []

# 检查AI模型与具体技术场景的输入输出关系。
def handle_ai_scenario(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查AI场景结合和输入输出语义。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：场景结合缺口。

    异常：
    - 无。
    """

    # 从研究事实读取场景披露，专项检查只消费输入输出关系。
    obj_ai_disclosure = dict_context["research_facts"].get("ai_disclosure")  # 场景披露所属AI事实对象

    # 损坏AI对象不能提供场景事实。
    dict_ai_disclosure = obj_ai_disclosure if isinstance(obj_ai_disclosure, Mapping) else {}  # 可读取场景事实容器

    # 提取场景结合对象供四项语义检查。
    obj_scenario = dict_ai_disclosure.get("scenario_integration")  # 场景结合原始值

    # 规范场景映射，字符串描述不能替代结构化关系。
    dict_scenario = dict(obj_scenario) if isinstance(obj_scenario, Mapping) else {}  # 可检查场景关系

    # 场景、输入、输出和关联机制必须共同存在。
    if not has_required_fields(
        dict_scenario,
        ("scenario", "input_semantics", "output_semantics", "relationship"),
    ):

        # 阻止只罗列算法名称的应用方案进入正式交付。
        return [
            build_handler_finding(
                "ai_scenario_integration_missing",
                "AI应用方案缺少具体场景、输入输出语义或内在关联。",
                "补充模型如何服务具体技术问题及其输入输出关系。",
            )
        ]

    # 场景结合四项事实齐全时本handler通过。
    return []

# 保持AI伦理、法律和公共利益问题由人工复核。
def handle_ai_public_interest(dict_context: dict[str, Any]) -> list[dict[str, str]]:
    """检查AI公共利益人工复核状态。

    参数：
    - `dict_context`：规则引擎统一输入上下文。

    返回：
    - `list[dict[str, str]]`：待复核或已识别风险问题。

    异常：
    - 无。
    """

    # 从研究事实读取公共利益复核记录所在的AI披露对象。
    obj_ai_disclosure = dict_context["research_facts"].get("ai_disclosure")  # 公共利益复核所属AI事实对象

    # 损坏AI对象不能提供伦理复核记录。
    dict_ai_disclosure = obj_ai_disclosure if isinstance(obj_ai_disclosure, Mapping) else {}  # 可读取公共利益复核容器

    # 伦理复核必须使用结构化人工记录。
    obj_ethics_review = dict_ai_disclosure.get("ethics_review")  # 伦理复核原始值

    # 非对象记录按尚未复核处理。
    dict_ethics_review = obj_ethics_review if isinstance(obj_ethics_review, Mapping) else {}  # 可读取复核记录

    # 读取人工复核状态，工具不自行给出法律结论。
    str_ethics_status = str(dict_ethics_review.get("status", ""))  # 公共利益人工复核状态

    # 缺少正式状态表示人工复核尚未完成。
    if str_ethics_status not in {"reviewed_no_issue", "reviewed_issue_identified"}:

        # 要求代理人或合规人员记录可核验结论。
        return [
            build_handler_finding(
                "ai_ethics_review_pending",
                "AI案件尚未记录伦理、法律和公共利益人工复核状态。",
                "由专利代理人或合规人员完成复核并记录结论。",
            )
        ]

    # 已识别风险必须保持可见，不能因reviewed状态静默通过。
    if str_ethics_status == "reviewed_issue_identified":

        # 暴露人工处置项但不替代法律判断。
        return [
            build_handler_finding(
                "ai_ethics_issue_identified",
                "AI人工复核已识别伦理、法律或公共利益风险。",
                "审查风险摘要和证据并记录人工处置结论。",
            )
        ]

    # 人工复核明确无问题时本handler通过。
    return []

# 注册每条JSON规则唯一对应的Python领域检查。
RULE_HANDLERS: dict[str, Callable[[dict[str, Any]], list[dict[str, str]]]] = {  # Contract2领域检查注册表
    "sufficient_disclosure": handle_sufficient_disclosure,  # 充分公开领域检查
    "feature_mechanism_effect": handle_feature_mechanism,  # 特征机制效果领域检查
    "inventiveness_chain": handle_inventiveness_chain,  # 创造性推理链领域检查
    "technical_contribution": handle_technical_contribution,  # 技术贡献领域检查
    "independent_claim_support": handle_independent_claims,  # 独立项支撑领域检查
    "secondary_claim_support": handle_secondary_claims,  # 次级候选支撑领域检查
    "ai_hard_applicability": handle_hard_ai_applicability,  # AI硬信号越权检查
    "ai_soft_applicability": handle_soft_ai_applicability,  # AI软信号决定检查
    "ai_human_confirmation": handle_ai_confirmation,  # AI人工确认检查
    "ai_scope": handle_ai_scope,  # AI技术范围检查
    "ai_model_structure": handle_ai_model_structure,  # AI模型结构检查
    "ai_training_process": handle_ai_training_process,  # AI训练过程检查
    "ai_scenario_integration": handle_ai_scenario,  # AI场景结合检查
    "ai_public_interest": handle_ai_public_interest,  # AI公共利益复核检查
}

# 兼容入口把合同结构和 registry 校验委托给独立引擎。
validate_rule_applicability = MODULE_RULE_ENGINE.validate_rule_applicability  # applicability 精确字段闭包

# 兼容入口保留既有注册校验函数名。
validate_rule_registry = MODULE_RULE_ENGINE.validate_rule_registry  # Contract 2.0 双向注册闭包

# 兼容入口保留 finding 元数据构造函数名。
build_engine_finding = MODULE_RULE_ENGINE.build_engine_finding  # JSON 元数据合并入口

# 兼容入口保留规则适用性选择函数名。
is_rule_applicable = MODULE_RULE_ENGINE.is_rule_applicable  # profile 解耦的规则选择入口

# AI 信号分类和当前确认状态由独立模块单独拥有。
collect_profile_text = MODULE_AI_APPLICABILITY.collect_profile_text  # profile 提示文本收集入口

# 系统信号分级不读取写作 profile。
classify_ai_signals = MODULE_AI_APPLICABILITY.classify_ai_signals  # hard、soft、none 分类入口

# 活动确认复用 Task1 的目标和哈希新鲜性判定。
has_ai_human_confirmation = MODULE_AI_APPLICABILITY.has_ai_human_confirmation  # 当前 AI 确认判定

# AI 适用状态绑定同一 rule_applicability 当前摘要。
build_ai_applicability = MODULE_AI_APPLICABILITY.build_ai_applicability  # AI 规则适用状态入口

# 加载合同并使用本模块正式 handler 注册表完成闭包。
def load_examination_contract(path_contract: Path | None = None) -> dict[str, Any]:
    """通过独立引擎加载并验证 Contract 2.0。

    参数：
    - `path_contract`：可选合同路径，空值使用正式资产。

    返回：
    - `dict[str, Any]`：通过 schema 等价和 registry 门的合同。

    异常：
    - 合同文件或闭包损坏时由独立引擎上抛。
    """

    # 正式注册表与当前合同必须一一对应。
    return MODULE_RULE_ENGINE.load_examination_contract(path_contract, RULE_HANDLERS)

# 使用调用方明确选择的 handler 映射执行独立规则引擎。
def run_rule_engine(
    dict_contract: Mapping[str, Any],
    dict_context: dict[str, Any],
    dict_handlers: Mapping[str, Callable[[dict[str, Any]], list[dict[str, Any]]]] | None = None,
) -> list[dict[str, Any]]:
    """执行 Contract 2.0 并区分默认注册表与显式空表。

    参数：
    - `dict_contract`：待执行的机器可读合同。
    - `dict_context`：当前案件事实和 AI 状态。
    - `dict_handlers`：可选显式 handler 注册表。

    返回：
    - `list[dict[str, Any]]`：包含证据合同结果的统一 findings。

    异常：
    - 合同、注册或 evidence_required 闭包损坏时由引擎上抛。
    """

    # 只有 None 表示使用正式全局表，显式空映射保持为空并 fail closed。
    dict_selected_handlers = RULE_HANDLERS if dict_handlers is None else dict_handlers  # 本轮明确 handler 注册表

    # 独立引擎拥有注册、适用和证据语义。
    return MODULE_RULE_ENGINE.run_rule_engine(dict_contract, dict_context, dict_selected_handlers)

# 统一执行Contract 2.0规则、AI适用性和状态收敛。
def assess_examination_quality(
    dict_case_config: dict[str, Any],
    dict_research_facts: dict[str, Any],
    list_prior_art_records: list[dict[str, Any]],
    dict_claims_map: dict[str, Any],
    dict_delivery_model: Mapping[str, Any] | None = None,
    path_contract: Path | None = None,
) -> dict[str, Any]:
    """评估当前案件的审查准备度。

    参数：
    - `dict_case_config`：案件写作profile和AI范围配置。
    - `dict_research_facts`：研发事实及AI专项披露。
    - `list_prior_art_records`：已核验最接近现有技术记录。
    - `dict_claims_map`：实际权利要求及省略候选映射。
    - `dict_delivery_model`：可选当前权威Model 4.0。
    - `path_contract`：可选Contract 2.0路径。

    返回：
    - `dict[str, Any]`：合同版本、AI状态、统一状态和findings。

    异常：
    - 合同损坏或注册表漂移时由底层校验异常上抛。
    """

    # 读取并严格校验合同和handler闭包。
    dict_contract = load_examination_contract(path_contract)  # 当前生效Contract2规则

    # 缺少模型时保留None，充分公开handler会形成明确finding。
    obj_delivery_model = dict_delivery_model if isinstance(dict_delivery_model, Mapping) else None  # 当前权威交付模型

    # AI适用性计算使用安全空映射，但上下文仍保留None供充分公开检查。
    dict_ai_model = obj_delivery_model or {}  # AI状态读取使用的安全模型

    # 结合材料信号和Model4人工决定形成独立于写作profile的适用状态。
    dict_ai_applicability = build_ai_applicability(dict_research_facts, dict_ai_model)  # 当前AI规则适用状态

    # 汇总所有handler共享的只读案件事实。
    dict_context = {  # Contract2规则统一输入
        "case_config": dict_case_config,  # 写作profile和AI范围
        "research_facts": dict_research_facts,  # 研发事实与AI披露
        "prior_art_records": list_prior_art_records,  # 已核验现有技术
        "claims_map": dict_claims_map,  # 实际权利要求支撑映射
        "delivery_model": obj_delivery_model,  # 当前权威Model4
        "ai_applicability": dict_ai_applicability,  # 系统与人工合并的AI状态
    }

    # 由引擎选择规则并用JSON元数据标注finding。
    list_findings = run_rule_engine(dict_contract, dict_context)  # 本次统一审查findings

    # 收集问题级别，供状态机按阻断优先级决策。
    set_finding_levels = {str(dict_item["level"]) for dict_item in list_findings}  # 本次finding级别集合

    # blocker存在时案件不能进入正式交付。
    if "blocker" in set_finding_levels:

        # 记录最高风险状态供验证入口直接消费。
        str_status = "blocked"  # 审查评估阻断状态

    # major存在时要求修订，minor本身不阻断主交付。
    elif "major" in set_finding_levels:

        # 记录需要修订状态，等待补齐审查链。
        str_status = "needs_revision"  # 审查评估修订状态

    # 没有blocker或major时视为通过合同规则。
    else:

        # minor提示仍保留在findings中供人工审阅。
        str_status = "pass"  # 审查评估通过状态

    # 返回合同来源、AI解释和写作profile彼此分离的审计结果。
    return {
        "contract_version": str(dict_contract["contract_version"]),  # 审查合同版本
        "effective_from": str(dict_contract["effective_from"]),  # 合同生效日期
        "technical_profile": str(dict_case_config.get("technical_profile", "general")),  # 写作profile原值
        "ai_applicability": dict_ai_applicability,  # AI信号和人工决定解释
        "status": str_status,  # 统一审查状态
        "findings": list_findings,  # 结构化审查问题
    }
