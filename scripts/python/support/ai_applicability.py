"""计算 AI 信号、当前人工确认和实体规则适用状态。"""

# 延迟解析类型注解，保持文件路径加载时的解释器兼容性。
from __future__ import annotations

# 标准库负责加载 Task1 正式语义审查接口。
import importlib.util
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# AI 提示术语只形成 soft 信号，不能替代结构化技术事实。
TUPLE_AI_INDICATORS = (
    "人工智能",  # 中文 AI 总称
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

# 人工确认必须复用 Task1 的目标解析、活动记录和摘要新鲜性判定。
PATH_SEMANTIC_REVIEW_VALIDATOR = Path(__file__).resolve().parents[1] / "review" / "semantic_review_validator.py"  # Task1 语义审查实现

# 按正式路径加载语义审查验证器，避免维护第二套哈希协议。
def load_semantic_review_validator() -> Any:
    """加载 Task1 的活动人工确认验证接口。

    参数：
    - 无。

    返回：
    - `Any`：已经执行的语义审查验证模块。

    异常：
    - `ImportError`：正式模块缺失或加载器不可用时抛出。
    """

    # 固定内部模块名不会修改调用方 sys.path。
    str_module_name = "readable_patent_ai_semantic_review_validator"  # 语义审查内部模块名

    # 根据受管文件路径创建隔离加载规格。
    obj_specification = importlib.util.spec_from_file_location(  # Task1 验证器加载规格
        str_module_name,  # 隔离加载使用的稳定内部名称
        PATH_SEMANTIC_REVIEW_VALIDATOR,  # Task1 正式验证器路径
    )

    # 正式验证器缺失时禁止降级为弱布尔检查。
    if obj_specification is None or obj_specification.loader is None:

        # 失败消息点明活动确认的单一事实来源。
        raise ImportError("> ERR: [Python] 无法加载 semantic_review_validator.py。")

    # 创建隔离模块并执行正式验证源码。
    module_validator = importlib.util.module_from_spec(obj_specification)  # Task1 语义审查模块

    # 执行源码后才能取得活动确认判定。
    obj_specification.loader.exec_module(module_validator)

    # 返回当前已初始化验证模块。
    return module_validator

# 模块初始化时绑定同一 Task1 实现，后续状态计算共享相同协议。
MODULE_SEMANTIC_REVIEW_VALIDATOR = load_semantic_review_validator()  # Task1 活动确认验证器

# 汇总研究事实中的候选文本，供关键词信号分类使用。
def collect_profile_text(dict_research_facts: Mapping[str, Any]) -> str:
    """提取研究事实中的术语和候选技术描述。

    参数：
    - `dict_research_facts`：当前案件研究事实。

    返回：
    - `str`：用于关键词匹配的规范化小写文本。

    异常：
    - 无；损坏候选记录按空文本处理。
    """

    # 技术术语是 profile 提示的第一类可观察文本。
    list_text_parts = [
        str(obj_term)  # 当前技术术语文本
        for obj_term in dict_research_facts.get("technical_terms", [])  # 遍历术语数组
    ]  # 当前可检索文本片段

    # 候选创新点可能以字符串或结构化对象存在。
    for obj_candidate in dict_research_facts.get("candidate_invention_points", []):

        # 字符串候选可直接加入提示语料。
        if isinstance(obj_candidate, str):

            # 保留当前候选完整文本供术语匹配。
            list_text_parts.append(obj_candidate)

            # 字符串分支已经完成，不再读取对象字段。
            continue

        # 结构化候选只读取可能承载技术语义的文本字段。
        if isinstance(obj_candidate, Mapping):

            # 标题、摘要、机制和效果共同组成候选提示文本。
            list_candidate_parts = [
                str(obj_candidate.get("title", "")),  # 当前候选标题
                str(obj_candidate.get("summary", "")),  # 当前候选摘要
                str(obj_candidate.get("mechanism", "")),  # 当前候选技术机制
                str(obj_candidate.get("technical_effect", "")),  # 当前候选技术效果
            ]  # 当前候选可检索文本

            # 当前候选文本并入统一信号语料。
            list_text_parts.extend(list_candidate_parts)

    # 小写合并支持中英文术语稳定匹配。
    return " ".join(list_text_parts).lower()

# 根据结构事实和关键词提示区分 hard、soft 与 none。
def classify_ai_signals(dict_research_facts: Mapping[str, Any]) -> dict[str, Any]:
    """分类 AI 技术事实的可观察强度。

    参数：
    - `dict_research_facts`：当前案件研究事实。

    返回：
    - `dict[str, Any]`：信号级别和可解释依据代码。

    异常：
    - 无；损坏 AI 披露容器按空对象处理。
    """

    # 结构化 AI 披露代表比关键词更强的技术事实。
    obj_ai_disclosure = dict_research_facts.get("ai_disclosure")  # 当前 AI 披露原始值

    # 只有映射容器可以提供模型、训练、推理或算法步骤。
    dict_ai_disclosure = obj_ai_disclosure if isinstance(obj_ai_disclosure, Mapping) else {}  # 可读取 AI 披露

    # 模型、训练、推理、算法或场景关系任一非空都形成 hard 信号。
    tuple_hard_fields = (
        "model_structure",  # 模型结构事实
        "training_process",  # 训练过程事实
        "inference_process",  # 推理过程事实
        "algorithm_steps",  # 算法步骤事实
        "scenario_integration",  # AI 与技术场景的明确关系
    )  # hard 信号字段集合

    # 保存实际命中的结构字段，供预览解释。
    list_hard_fields = [
        str_field  # 当前命中的结构事实字段
        for str_field in tuple_hard_fields  # 遍历 hard 字段集合
        if bool(dict_ai_disclosure.get(str_field))  # 仅保留非空事实
    ]  # 当前 hard 信号依据

    # 明确结构事实始终优先于关键词提示。
    if list_hard_fields:

        # 返回强制适用所需的结构依据。
        return {
            "signal_level": "hard",  # 明确 AI 技术事实
            "reason_codes": [f"structured:{str_field}" for str_field in list_hard_fields],  # 命中字段坐标
        }

    # 关键词提示只形成 soft 信号。
    str_profile_text = collect_profile_text(dict_research_facts)  # 当前研究事实提示文本

    # 收集命中的受管 AI 术语。
    list_matched_terms = [
        str_indicator  # 当前命中的 AI 术语
        for str_indicator in TUPLE_AI_INDICATORS  # 遍历受管提示词
        if str_indicator in str_profile_text  # 当前文本包含该术语
    ]  # soft 分类实际命中的术语集合

    # 关键词不能自动决定适用或不适用。
    if list_matched_terms:

        # 返回 disputed 状态使用的术语依据。
        return {
            "signal_level": "soft",  # 关键词提示信号
            "reason_codes": [f"keyword:{str_term}" for str_term in list_matched_terms],  # 命中术语坐标
        }

    # 没有可观察 AI 信号仍需人工确认最终决定。
    return {
        "signal_level": "none",  # 系统未检测到 AI 事实
        "reason_codes": [],  # 当前无自动信号依据
    }

# 判断当前模型是否存在绑定最新 rule_applicability 的活动 confirm。
def has_ai_human_confirmation(dict_delivery_model: Mapping[str, Any]) -> bool:
    """复用 Task1 验证结果判断 AI 适用性确认是否活动有效。

    参数：
    - `dict_delivery_model`：当前权威 Model 4.0。

    返回：
    - `bool`：模型级 AI 目标存在当前 confirm 时为真。

    异常：
    - 无；损坏语义审查容器按未确认处理。
    """

    # 非对象模型无法提供合同版本、规则内容和人工记录。
    if not isinstance(dict_delivery_model, Mapping):

        # 缺少权威模型时禁止推断人工已确认。
        return False

    # 读取活动人工确认数组，历史集合不参与当前状态。
    obj_semantic_review = dict_delivery_model.get("semantic_review")  # 当前语义审查容器

    # 容器损坏时不能安全取得活动确认。
    if not isinstance(obj_semantic_review, Mapping):

        # 损坏语义容器不能产生有效人工确认。
        return False

    # Task1 会选择同目标最后一条活动记录并复算当前 target_hash。
    tuple_validation = MODULE_SEMANTIC_REVIEW_VALIDATOR.validate_human_confirmation_records(  # 当前人工确认验证结果
        dict_delivery_model,  # 当前完整 Model 4.0
        obj_semantic_review.get("human_confirmations", []),  # 当前活动人工确认数组
    )

    # 取得同一目标的最后一条活动记录，避免旧正确类别掩盖新错配记录。
    dict_active_records = MODULE_SEMANTIC_REVIEW_VALIDATOR.collect_active_review_records(  # 当前活动确认映射
        obj_semantic_review.get("human_confirmations", [])  # 用于选择最后决定的原始记录
    )

    # AI 入口同时要求目标坐标、确认事项类别和正式验证均有效。
    dict_ai_confirmation = dict_active_records.get(("ai_applicability", "model"))  # 当前 AI 确认记录

    # 错误 confirmation_type 即使目标和哈希自洽也不能关闭争议。
    return bool(
        isinstance(dict_ai_confirmation, Mapping)  # 当前 AI 记录结构有效
        and dict_ai_confirmation.get("confirmation_type") == "ai_applicability"  # 事项类别明确匹配
        and ("ai_applicability", "model") in tuple_validation[1]  # 正式目标与摘要验证有效
    )

# 合并系统信号、Model 4.0 决定和当前人工确认。
def build_ai_applicability(
    dict_research_facts: Mapping[str, Any],
    dict_delivery_model: Mapping[str, Any],
) -> dict[str, Any]:
    """计算独立于写作 profile 的 AI 规则适用状态。

    参数：
    - `dict_research_facts`：当前案件研究事实。
    - `dict_delivery_model`：当前权威 Model 4.0。

    返回：
    - `dict[str, Any]`：信号、决定、确认和实体规则开关。

    异常：
    - 无；缺失字段保持 pending 或 disputed。
    """

    # 自动信号只来自研发事实，不能由人工字段改写。
    dict_signal = classify_ai_signals(dict_research_facts)  # 当前系统 AI 信号

    # 读取完整 rule_applicability，rationale 与决定共同参与 Task1 哈希。
    obj_rule_applicability = dict_delivery_model.get("rule_applicability")  # 当前规则适用性原始值

    # 损坏规则容器不形成任何人工决定。
    dict_rule_applicability = (  # 可安全读取的规则适用性对象
        obj_rule_applicability  # 保留正式规则决定与理由
        if isinstance(obj_rule_applicability, Mapping)  # 只接受对象合同
        else {}  # 损坏容器不形成决定
    )  # 可读取的规则适用性对象

    # 决定必须使用 Model 4.0 受管枚举。
    str_decision = str(dict_rule_applicability.get("ai_applicability", "pending"))  # 当前人工决定

    # soft 理由是规则目标内容的一部分，旧理由变化会使确认哈希失效。
    str_rationale = str(dict_rule_applicability.get("rationale", "")).strip()  # 当前决定理由

    # 当前确认必须同时通过 Task1 目标、决定和哈希验证。
    bool_human_confirmed = has_ai_human_confirmation(dict_delivery_model)  # 当前 AI 确认是否有效

    # 信号级别决定系统允许的收敛路径。
    str_signal_level = str(dict_signal["signal_level"])  # 当前 AI 信号级别

    # hard 事实始终强制执行 AI 实体规则。
    if str_signal_level == "hard":

        # 人工 not_applicable 由专门 handler 报告越权，但不会关闭规则。
        str_state = "applicable"  # hard 强制适用状态

        # 写作 profile 和人工决定都不能屏蔽明确 AI 技术事实。
        bool_ai_rules_apply = True  # hard 实体规则开关

    # soft 必须具有二值决定、非空理由和同一目标当前确认。
    elif str_signal_level == "soft":

        # 当前摘要确认同时绑定 rationale 与决定。
        bool_soft_decided = bool(  # soft 三条件闭包结果
            str_decision in {"applicable", "not_applicable"}  # 决定属于受管二值
            and str_rationale  # 人工理由具有可见内容
            and bool_human_confirmed  # 确认绑定当前完整目标
        )  # soft 争议是否完成闭包

        # 任一条件缺失都重新打开 disputed。
        str_state = str_decision if bool_soft_decided else "disputed"  # soft 当前状态

        # 只有当前确认的 applicable 执行实体规则。
        bool_ai_rules_apply = bool_soft_decided and str_decision == "applicable"  # soft 最终执行结论

    # none 仍需当前人工确认，但不强制要求 rationale。
    else:

        # 当前确认可以选择 applicable 或 not_applicable。
        bool_none_decided = bool(  # 无信号场景的人工闭包结果
            str_decision in {"applicable", "not_applicable"}  # 人工决定属于受管二值
            and bool_human_confirmed  # 确认摘要仍匹配当前目标
        )  # none 人工决定是否闭包

        # 未确认时保持 pending，系统不替代人工决定。
        str_state = str_decision if bool_none_decided else "pending"  # 无信号人工判断状态

        # none 只有人工确认 applicable 时执行实体规则。
        bool_ai_rules_apply = bool_none_decided and str_decision == "applicable"  # 无信号最终执行结论

    # 返回预览和正式评估共用的可解释状态。
    return {
        "signal_level": str_signal_level,  # 系统 AI 信号级别
        "reason_codes": list(dict_signal["reason_codes"]),  # 系统分类可回查依据
        "decision": str_decision,  # Model 4.0 人工决定
        "rationale": str_rationale,  # 人工适用性判断理由
        "human_confirmed": bool_human_confirmed,  # 当前活动确认真值
        "state": str_state,  # applicable、not_applicable、disputed 或 pending
        "ai_rules_apply": bool_ai_rules_apply,  # AI 实体规则是否执行
    }
