"""把 schema-invalid 的 Model 4 和 claims 容器规整为可安全诊断的副本。"""

# 延迟解析类型注解，保持当前技能支持的 Python 版本兼容。
from __future__ import annotations

# 标准库类型用于识别未知 JSON 映射并声明安全副本边界。
from collections.abc import Mapping
from typing import Any

# 这些 Model 4 顶层字段必须始终能作为数组继续执行深层诊断。
TUPLE_MODEL_LIST_KEYS = (
    "source_manifest",  # 模型来源清单数组
    "data_registry",  # 模型数据登记数组
    "formula_registry",  # 模型公式登记数组
    "term_registry",  # 模型术语登记数组
    "figure_registry",  # 模型附图登记数组
    "sections",  # 模型章节数组
    "cross_references",  # 模型交叉引用数组
    "pending_items",  # 模型待办数组
    "feature_registry",  # 模型技术特征数组
)  # Model 4 数组字段白名单

# 这些审查字段覆盖活动态、不可变历史态和显式待办。
TUPLE_REVIEW_LIST_KEYS = (
    "agent_reviews",  # AI 活动审查数组
    "human_confirmations",  # 人工活动确认数组
    "agent_review_history",  # AI 审查历史数组
    "human_confirmation_history",  # 人工确认历史数组
    "pending_reviews",  # AI 审查待办数组
    "pending_confirmations",  # 人工确认待办数组
)  # 语义审查数组字段白名单

# 把未知值收敛为可迭代数组，避免 schema 失败后的诊断器再次抛出类型异常。
def safe_list(obj_value: Any) -> list[Any]:
    """把未知值收敛为可迭代数组。

    参数：
    - `obj_value`：schema 校验后仍需诊断的未知值。

    返回：
    - `list[Any]`：原数组副本或空数组。

    异常：
    - 无。
    """

    # 只接纳真实 JSON 数组，其他类型统一返回空数组供后续诊断。
    return list(obj_value) if isinstance(obj_value, list) else []

# 把未知值收敛为字符串键映射，避免对列表或标量调用映射接口。
def safe_mapping(obj_value: Any) -> dict[str, Any]:
    """把未知值收敛为字符串键映射副本。

    参数：
    - `obj_value`：schema 校验后仍需诊断的未知值。

    返回：
    - `dict[str, Any]`：映射浅副本或空映射。

    异常：
    - 无。
    """

    # 只复制真实映射，避免后续修复动作反向修改原始输入。
    return dict(obj_value) if isinstance(obj_value, Mapping) else {}

# 规整记录数组及其指定嵌套数组字段，过滤无法解释的非映射元素。
def normalize_mapping_records(
    obj_records: Any,
    tuple_list_keys: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """规整记录数组及其嵌套数组字段。

    参数：
    - `obj_records`：可能损坏的记录容器。
    - `tuple_list_keys`：每条记录中必须安全迭代的字段。

    返回：
    - `list[dict[str, Any]]`：只含映射记录的安全副本。

    异常：
    - 无。
    """

    # 先复制可解释记录，非映射元素由 schema finding 负责报告而不进入深层循环。
    list_records = [
        dict(obj_record)  # 当前可解释记录副本
        for obj_record in safe_list(obj_records)  # 逐项读取安全输入数组
        if isinstance(obj_record, Mapping)  # 排除无法解释的标量记录
    ]  # 可安全读取的记录副本

    # 逐条规整调用方声明的嵌套数组字段。
    for dict_record in list_records:

        # 只处理当前记录实际携带的字段，避免凭空添加合同键。
        for str_key in tuple_list_keys:

            # 已存在字段必须变为可迭代数组，保证后续语义验证 type-total。
            if str_key in dict_record:

                # 用安全数组副本替换可能损坏的嵌套值。
                dict_record[str_key] = safe_list(dict_record.get(str_key))  # 当前嵌套数组安全副本

    # 返回与原始输入隔离的记录数组。
    return list_records

# 规整语义审查活动态、历史态和待办容器，供所有审查规则安全读取。
def normalize_review_container(obj_review: Any) -> dict[str, Any]:
    """规整语义审查活动态、历史态和待办。

    参数：
    - `obj_review`：可能损坏的 `semantic_review`。

    返回：
    - `dict[str, Any]`：可供审查验证函数安全读取的副本。

    异常：
    - 无。
    """

    # 先把审查根收敛为独立映射，避免直接改写输入模型。
    dict_review = safe_mapping(obj_review)  # 审查容器安全副本

    # 所有活动态、历史态和待办字段都必须能够安全迭代。
    for str_key in TUPLE_REVIEW_LIST_KEYS:

        # 缺失或损坏字段收敛为空数组，具体合同缺陷仍由 schema 报告。
        dict_review[str_key] = safe_list(dict_review.get(str_key))  # 当前审查数组安全副本

    # 这四类记录共享 evidence_bindings 和可选 coverage 的嵌套结构。
    tuple_record_keys = (
        "agent_reviews",  # AI 活动审查记录
        "human_confirmations",  # 人工活动确认记录
        "agent_review_history",  # AI 不可变历史记录
        "human_confirmation_history",  # 人工不可变历史记录
    )  # 需要深层规整的审查记录字段

    # 逐类复制记录并收敛其嵌套容器。
    for str_key in tuple_record_keys:

        # evidence_bindings 必须始终可迭代，便于证据闭包检查继续运行。
        list_records = normalize_mapping_records(  # 当前审查类型安全记录
            dict_review[str_key],  # 当前审查类别原始数组
            ("evidence_bindings",),  # 审查证据绑定数组字段
        )  # 当前类型审查记录安全副本

        # coverage 仅在记录实际携带时规整为映射。
        for dict_record in list_records:

            # AI 记录的 coverage 损坏时保留 schema finding 并阻止深层异常。
            if "coverage" in dict_record:

                # 将 coverage 收敛为独立映射副本。
                dict_record["coverage"] = safe_mapping(dict_record.get("coverage"))  # coverage 安全副本

        # 用安全记录替换当前审查类别。
        dict_review[str_key] = list_records  # 当前审查类别安全记录

    # 返回可供全部语义规则继续诊断的审查容器。
    return dict_review

# 构造 type-total Model 4 副本，使 schema-invalid 输入仍能产出完整 findings。
def normalize_model(dict_model: Mapping[str, Any]) -> dict[str, Any]:
    """构造 type-total Model 4 诊断副本。

    参数：
    - `dict_model`：原始 Model 4 映射。

    返回：
    - `dict[str, Any]`：嵌套列表和映射均可安全读取的副本。

    异常：
    - 无。
    """

    # Model 4 顶层先做浅复制，保持验证过程不改变调用方输入。
    dict_safe = dict(dict_model)  # 等待嵌套字段收敛的模型副本

    # 逐项收敛所有声明为数组的顶层合同字段。
    for str_key in TUPLE_MODEL_LIST_KEYS:

        # 无论原值为何，深层验证都只消费数组副本。
        dict_safe[str_key] = safe_list(dict_safe.get(str_key))  # 当前模型数组安全副本

    # section 内三个引用集合必须可迭代。
    dict_safe["sections"] = normalize_mapping_records(  # 章节记录安全副本
        dict_safe.get("sections"),  # 原始章节容器
        ("evidence_ids", "data_ids", "formula_ids"),  # 章节引用数组字段
    )

    # feature 内章节、证据和技术效果集合必须可迭代。
    dict_safe["feature_registry"] = normalize_mapping_records(  # 特征记录安全副本
        dict_safe.get("feature_registry"),  # 原始特征容器
        ("section_ids", "evidence_ids", "technical_effects"),  # 特征引用和效果数组字段
    )

    # 来源、数据和交叉引用记录分别收敛为映射数组。
    dict_safe["source_manifest"] = normalize_mapping_records(  # 来源记录安全副本
        dict_safe.get("source_manifest")  # 原始来源清单
    )

    # data_registry 额外规整 evidence_ids 引用集合。
    dict_safe["data_registry"] = normalize_mapping_records(  # 数据记录安全副本
        dict_safe.get("data_registry"),  # 原始数据登记容器
        ("evidence_ids",),  # 数据记录证据引用数组字段
    )

    # 交叉引用和待办记录不含当前验证器需要遍历的嵌套数组。
    dict_safe["cross_references"] = normalize_mapping_records(  # 交叉引用安全副本
        dict_safe.get("cross_references")  # 原始交叉引用容器
    )

    # 待办记录只需保证每项为映射。
    dict_safe["pending_items"] = normalize_mapping_records(  # 待办记录安全副本
        dict_safe.get("pending_items")  # 原始待办容器
    )

    # 规则适用性、迁移和来源链均按映射边界安全读取。
    dict_safe["rule_applicability"] = safe_mapping(  # 规则适用性安全副本
        dict_safe.get("rule_applicability")  # 原始规则适用性容器
    )

    # 迁移元数据损坏时保留空映射供显式迁移规则判定。
    dict_safe["migration"] = safe_mapping(dict_safe.get("migration"))  # 迁移元数据安全副本

    # 来源链损坏时保留空映射供案件绑定规则判定。
    dict_safe["provenance"] = safe_mapping(dict_safe.get("provenance"))  # 来源链安全副本

    # evidence_registry 根和 records 需要分别收敛，避免嵌套类型异常。
    dict_evidence = safe_mapping(  # 证据登记根安全副本
        dict_safe.get("evidence_registry")  # 原始证据登记根
    )  # 已收敛的证据登记根

    # 证据记录只保留可解释映射。
    dict_evidence["records"] = normalize_mapping_records(  # 证据记录安全副本
        dict_evidence.get("records")  # 原始证据记录容器
    )

    # 把安全证据登记根写回模型副本。
    dict_safe["evidence_registry"] = dict_evidence  # 完整证据登记安全副本

    # 审查容器交给专用规整器处理活动态、历史态和待办。
    dict_safe["semantic_review"] = normalize_review_container(  # 活动态和历史态审查副本
        dict_safe.get("semantic_review")  # 原始语义审查容器
    )

    # 返回不会因深层容器类型而中断验证的 Model 4 副本。
    return dict_safe

# 构造 type-total Claims Map 3 副本，保证 feature 和 support 引用检查可继续。
def normalize_claims_map(dict_claims_map: Mapping[str, Any]) -> dict[str, Any]:
    """构造 type-total Claims Map 3 诊断副本。

    参数：
    - `dict_claims_map`：原始 claims map。

    返回：
    - `dict[str, Any]`：嵌套数组均安全的 claims 副本。

    异常：
    - 无。
    """

    # Claims Map 顶层复制用于隔离诊断写入和原始输入。
    dict_safe = dict(dict_claims_map)  # 等待嵌套字段收敛的 claims 副本

    # claims 中五类引用集合必须可迭代，才能完整报告坏引用。
    dict_safe["claims"] = normalize_mapping_records(  # claims 记录安全副本
        dict_safe.get("claims"),  # 原始 claims 记录容器
        (
            "feature_ids",  # 已接纳特征引用数组
            "unsupported_feature_ids",  # 未支持特征引用数组
            "mapped_steps",  # 映射步骤数组
            "support_ids",  # 证据支持引用数组
            "unsupported_features",  # 未支持特征文本数组
        ),
    )

    # 省略候选只需保证每条记录是映射。
    dict_safe["omitted_candidates"] = normalize_mapping_records(  # 省略候选安全副本
        dict_safe.get("omitted_candidates")  # 原始省略候选容器
    )

    # 迁移元数据收敛为映射，供 pending claims 规则安全读取。
    dict_safe["migration"] = safe_mapping(dict_safe.get("migration"))  # claims 迁移元数据副本

    # 返回与原始 claims 输入隔离的安全副本。
    return dict_safe
