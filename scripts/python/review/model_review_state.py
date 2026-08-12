"""推进 Model 4 活动审查、不可变历史和待办闭包。"""

# 延迟解析类型注解，保持当前技能支持的 Python 版本兼容。
from __future__ import annotations

# 标准库类型用于复制模型并区分 JSON 映射与未知坏值。
import copy
import importlib.util
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# 当前目录正式验证器提供目标解析和确定性哈希合同。
PATH_VALIDATOR = Path(__file__).resolve().with_name("structured_contract_validator.py")  # 语义审查验证器

# 加载目标解析和哈希实现，状态模块不复制其规范化规则。
def load_validator() -> Any:
    """加载当前技能的正式结构验证器。

    参数：
    - 无。

    返回：
    - `Any`：已经执行的验证器模块。

    异常：
    - `ImportError`：验证器规格不可用时抛出。
    """

    # 根据固定同目录路径创建隔离模块规格。
    obj_specification = importlib.util.spec_from_file_location("patent_review_state_validator", PATH_VALIDATOR)  # 当前验证器规格

    # 缺少加载器时不能凭 verdict 或 decision 推导待办。
    if obj_specification is None or obj_specification.loader is None:

        # 状态闭包必须失败关闭。
        raise ImportError("> ERR: [Python] 无法加载语义审查验证器。")

    # 创建本次重算独享的验证器模块。
    obj_module = importlib.util.module_from_spec(obj_specification)  # 当前验证器模块

    # 执行正式目标解析和哈希规则。
    obj_specification.loader.exec_module(obj_module)

    # 返回供当前状态重算复用的模块。
    return obj_module

# 判断活动记录仍绑定当前事实内容和证据。
def record_hash_is_current(
    dict_model: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None,
    dict_record: Mapping[str, Any],
    str_reviewer_type: str,
    module_validator: Any,
) -> bool:
    """核对活动记录哈希是否仍匹配当前目标事实。

    参数：
    - `dict_model`：当前 Model 4。
    - `dict_claims_map`：可选当前 Claims Map 3。
    - `dict_record`：待核对活动记录。
    - `str_reviewer_type`：`agent` 或 `human`。
    - `module_validator`：正式目标解析和哈希模块。

    返回：
    - `bool`：目标存在且摘要仍新鲜时为真。

    异常：
    - 无。
    """

    # 独立项确认必须从当前 claims 和特征登记重建目标，不能信任记录内嵌快照。
    tuple_target = resolve_current_claim_target(  # 当前记录绑定的实时事实与证据
        dict_model,  # 提供当前稳定特征证据
        dict_claims_map,  # 提供当前独立项特征集合
        str(dict_record.get("target_id", "")),  # 定位当前独立项编号
    ) if (  # 独立项人工确认启用 companion 实时解析
        str_reviewer_type == "human"  # 当前记录属于人工确认集合
        and dict_record.get("target_type") == "independent_claim"  # 独立项必须重读 companion
    ) else (  # 代理或其他人工记录使用模型内事实解析
        module_validator.resolve_review_target(  # 解析当前代理审查事实与证据
            dict_model,  # 提供当前模型事实域
            str(dict_record.get("target_type", "")),  # 定位代理目标类型
            str(dict_record.get("target_id", "")),  # 定位代理目标编号
        )
        if str_reviewer_type == "agent"  # 代理记录走通用目标解析
        else module_validator.resolve_human_confirmation_target(dict_model, dict_record)  # 其他人工事实由模型解析
    )  # 当前记录绑定的实时目标

    # 已删除或无法解析的目标不能关闭待办。
    if tuple_target is None:

        # 返回失效状态供集合推导排除。
        return False

    # 使用当前内容、证据和合同版本重算摘要。
    str_expected_hash = module_validator.calculate_semantic_review_hash(  # 当前事实确定性摘要
        str(dict_record.get("target_type", "")),  # 绑定当前目标类型
        str(dict_record.get("target_id", "")),  # 绑定当前目标编号
        tuple_target[0],  # 绑定当前目标内容
        tuple_target[1],  # 绑定当前证据集合
        str(dict_model.get("contract_version", "")),  # 绑定当前合同版本
    )  # 记录目标在当前合同下的重算摘要

    # 只有完全一致的活动记录仍可关闭目标。
    return dict_record.get("target_hash") == str_expected_hash

# 从当前 Claims Map 和特征登记重建独立项确认目标。
def resolve_current_claim_target(
    dict_model: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None,
    str_claim_id: str,
) -> tuple[list[str], list[str]] | None:
    """解析当前独立权利要求的特征集合和证据闭包。

    参数：
    - `dict_model`：当前 Model 4。
    - `dict_claims_map`：可选当前 Claims Map 3。
    - `str_claim_id`：独立权利要求编号。

    返回：
    - `tuple[list[str], list[str]] | None`：当前特征和证据集合，目标缺失时为空。

    异常：
    - 无。
    """

    # 缺少正式 claims 工件时不能把记录内嵌快照视为当前事实。
    if not isinstance(dict_claims_map, Mapping):

        # 返回缺失标记以保留独立项待确认状态。
        return None

    # 建立当前稳定特征到证据集合的索引。
    dict_feature_evidence = {
        str(dict_feature.get("feature_id")): [  # 当前稳定特征对应的证据数组
            str(obj_id)  # 规范化当前证据编号
            for obj_id in dict_feature.get("evidence_ids", [])  # 遍历特征证据引用
        ]
        for dict_feature in dict_model.get("feature_registry", [])  # 遍历稳定特征登记
        if isinstance(dict_feature, Mapping) and dict_feature.get("feature_id")  # 排除无身份坏记录
    }  # 当前技术特征证据索引

    # 按当前 claim_no 查找独立项并重建其摘要输入。
    for dict_claim in dict_claims_map.get("claims", []):

        # 目标必须是编号匹配的独立权利要求。
        if (
            isinstance(dict_claim, Mapping)
            and str(dict_claim.get("claim_no", "")) == str_claim_id
            and str(dict_claim.get("claim_type", "")).startswith("independent_")
        ):

            # 保留 Claims Map 声明的稳定特征顺序。
            list_feature_ids = [
                str(obj_id)  # 规范化当前特征编号
                for obj_id in dict_claim.get("feature_ids", [])  # 遍历独立项特征引用
            ]  # 当前独立项特征集合

            # 确认摘要绑定这些特征当前证据的确定性并集。
            list_evidence_ids = sorted({  # 当前独立项证据确定性并集
                str_evidence_id  # 保留当前证据编号
                for str_feature_id in list_feature_ids  # 遍历独立项特征
                for str_evidence_id in dict_feature_evidence.get(str_feature_id, [])  # 合并各特征证据
            })  # 当前独立项证据并集

            # 返回与正式 claims 校验器一致的摘要输入。
            return list_feature_ids, list_evidence_ids

    # 编号缺失或类型已变化时旧确认自然失效。
    return None

# 根据审查者类型返回其活动态、历史态和身份字段合同。
def collection_names(str_reviewer_type: str) -> tuple[str, str, str]:
    """返回活动态、历史态和身份字段。

    参数：
    - `str_reviewer_type`：`agent` 或 `human`。

    返回：
    - `tuple[str, str, str]`：活动集合、历史集合和身份字段名。

    异常：
    - 无。
    """

    # AI 审查使用 review_id 和对应两类集合。
    if str_reviewer_type == "agent":

        # 返回 AI 活动态、历史态和身份字段。
        return "agent_reviews", "agent_review_history", "review_id"

    # 非 AI 分支由上游枚举约束为人工确认。
    return "human_confirmations", "human_confirmation_history", "confirmation_id"

# 汇总两个记录域的活动态和历史态，供全局 ID 唯一性检查。
def iter_review_records(dict_model: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """汇总两个记录域的活动态和历史态。

    参数：
    - `dict_model`：当前 Model 4。

    返回：
    - `list[Mapping[str, Any]]`：全部可解释活动与历史记录。

    异常：
    - 无。
    """

    # 读取语义审查根，错误类型直接视为无可迭代记录。
    obj_review = dict_model.get("semantic_review")  # 等待活动记录替换的审查根

    # schema-invalid 审查根不参与记录遍历。
    if not isinstance(obj_review, Mapping):

        # 返回空集合，由正式 schema 验证报告根类型错误。
        return []

    # 准备跨活动态和历史态汇总的记录列表。
    list_records: list[Mapping[str, Any]] = []  # 全域可解释审查记录

    # 四类集合共同参与全局身份占用判断。
    for str_key in (
        "agent_reviews",  # AI 活动记录
        "human_confirmations",  # 人工活动记录
        "agent_review_history",  # AI 历史记录
        "human_confirmation_history",  # 人工历史记录
    ):

        # 读取当前类别，坏类型留给 schema 报告。
        obj_records = obj_review.get(str_key)  # 当前审查类别根值

        # 非数组类别无法安全展开。
        if not isinstance(obj_records, list):

            # 跳过坏类别并继续检查其他有效集合。
            continue

        # 只汇总可解释映射，避免标量记录中断身份读取。
        list_records.extend(
            dict_record  # 当前可解释记录
            for dict_record in obj_records  # 当前类别全部记录
            if isinstance(dict_record, Mapping)  # 排除无法解释的标量
        )

    # 返回供全局身份检查消费的记录列表。
    return list_records

# 统一读取 AI 或人工记录身份，不在调用方复制字段分支。
def record_identifier(dict_record: Mapping[str, Any]) -> str:
    """读取代理或人工记录的全局身份。

    参数：
    - `dict_record`：任一活动态或历史态审查记录。

    返回：
    - `str`：记录身份，缺失时为空字符串。

    异常：
    - 无。
    """

    # AI 记录优先读取 review_id，人工记录回退 confirmation_id。
    return str(
        dict_record.get("review_id")  # AI 审查身份
        or dict_record.get("confirmation_id")  # 人工确认身份
        or ""  # 缺失身份由调用方阻断
    )

# 用新活动记录替换同目标旧记录，并把旧记录不可变归档。
def replace_active_review(
    dict_model: dict[str, Any],
    str_reviewer_type: str,
    dict_embedded: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None = None,
) -> None:
    """以不可变历史替换同目标活动记录。

    参数：
    - `dict_model`：待更新的 Model 4。
    - `str_reviewer_type`：`agent` 或 `human`。
    - `dict_embedded`：已经通过单记录 schema 的新记录。
    - `dict_claims_map`：可选当前 Claims Map 3。

    返回：
    - `None`：活动态、历史态和待办已原地更新。

    异常：
    - `ValueError`：容器损坏或记录 ID 不唯一时抛出。
    """

    # 读取待更新的语义审查根。
    obj_review = dict_model.get("semantic_review")  # 当前语义审查根值

    # 状态推进只接受真实可变对象。
    if not isinstance(obj_review, dict):

        # 拒绝在缺失或坏类型容器上静默创建状态。
        raise ValueError("> ERR: [Python] 模型缺少 semantic_review 对象。")

    # 根据审查者类型解析三类字段名，避免两个分支行为漂移。
    tuple_str_active, tuple_str_history, tuple_str_id_key = collection_names(  # 当前类别三类字段名
        str_reviewer_type  # 当前审查者类别
    )  # 活动集合、历史集合和身份字段

    # 读取当前类别活动态。
    obj_active = obj_review.get(tuple_str_active)  # 当前类别活动记录根值

    # 历史态缺失时初始化为空数组，但不修复错误类型。
    obj_history = obj_review.setdefault(tuple_str_history, [])  # 当前类别历史数组

    # 两个容器都必须为数组才能安全替换和归档。
    if not isinstance(obj_active, list) or not isinstance(obj_history, list):

        # 报告具体活动集合名，便于定位坏合同。
        raise ValueError(
            f"> ERR: [Python] semantic_review.{tuple_str_active} 或历史态必须为数组。"
        )

    # 读取本次新记录身份，空值也视为无效。
    str_new_id = str(dict_embedded.get(tuple_str_id_key, ""))  # 新活动记录全局身份

    # 汇总四个集合中全部已占用身份。
    set_existing_ids = {
        record_identifier(dict_record)  # 当前已占用记录身份
        for dict_record in iter_review_records(dict_model)  # 全域活动态和历史态
    }  # 跨 AI 与人工记录的身份集合

    # 新身份必须非空且不得复用任何活动或历史身份。
    if not str_new_id or str_new_id in set_existing_ids:

        # 阻止覆盖审计链或造成跨域身份歧义。
        raise ValueError(f"> ERR: [Python] 审查记录 ID 必须全局唯一:{str_new_id}")

    # 同目标判定由目标类型和目标身份共同组成。
    tuple_target = (
        str(dict_embedded.get("target_type", "")),  # 新记录目标类型
        str(dict_embedded.get("target_id", "")),  # 新记录目标身份
    )  # 本次需要替换的活动目标

    # 复制新记录，后续 supersedes 写入不改变调用方对象。
    dict_new = dict(dict_embedded)  # 待加入活动态的新记录副本

    # 准备保留非同目标记录和坏记录的活动态数组。
    list_retained: list[Any] = []  # 替换后的活动记录数组

    # 逐项扫描当前活动态，只归档同目标记录。
    for obj_record in obj_active:

        # 坏类型记录不能由状态模块猜测修复，原样保留供 schema 报告。
        if not isinstance(obj_record, Mapping):

            # 保留无法解释记录，避免审查动作掩盖既有损坏。
            list_retained.append(obj_record)

            # 当前坏记录没有可比较目标，继续下一项。
            continue

        # 解析旧活动记录目标用于精确匹配。
        tuple_existing = (
            str(obj_record.get("target_type", "")),  # 旧记录目标类型
            str(obj_record.get("target_id", "")),  # 旧记录目标身份
        )  # 当前旧活动记录目标

        # 非同目标记录继续保持活动。
        if tuple_existing != tuple_target:

            # 复制保留记录，隔离后续列表替换。
            list_retained.append(dict(obj_record))

            # 当前记录无需归档，继续下一项。
            continue

        # 同目标旧记录复制后写入反向替代关系。
        dict_archived = dict(obj_record)  # 待归档的旧活动记录副本

        # 保存旧身份供新记录 supersedes 字段引用。
        str_old_id = record_identifier(dict_archived)  # 被替代旧记录身份

        # 历史记录指向本次新活动记录。
        dict_archived["superseded_by"] = str_new_id  # 旧记录的替代者身份

        # 追加不可变历史，不删除前序归档。
        obj_history.append(dict_archived)

        # 新活动记录反向引用被替代旧身份。
        dict_new["supersedes"] = str_old_id  # 新记录替代的旧身份

    # 新记录作为该目标唯一活动态追加。
    list_retained.append(dict_new)

    # 原子替换当前类别活动数组，历史数组已经保留旧记录。
    obj_review[tuple_str_active] = list_retained  # 替换后的当前活动态

    # 每次活动态变化后从事实域完整重算待办和迁移状态。
    refresh_pending_state(dict_model, dict_claims_map)

# 将人工确认的 AI 适用性快照写入候选规则事实域。
def apply_ai_applicability_review(
    dict_candidate: dict[str, Any],
    dict_embedded: Mapping[str, Any],
) -> None:
    """应用单条人工 AI 适用性确认。

    参数：
    - `dict_candidate`：等待状态推进的独立模型候选。
    - `dict_embedded`：已经绑定实时事实的人工确认记录。

    返回：
    - `None`。

    异常：
    - `ValueError`：确认内容不是对象时抛出。
    """

    # 只信任 recorder 已嵌入并参与哈希的目标快照。
    obj_content = dict_embedded.get("target_content")  # 当前 AI 规则确认内容

    # 非对象内容无法形成完整规则结论。
    if not isinstance(obj_content, Mapping):

        # 状态函数失败关闭，不猜测默认适用性。
        raise ValueError("> ERR: [Python] AI 适用性确认内容必须为对象。")

    # 深复制防止活动记录与业务事实共享可变引用。
    dict_candidate["rule_applicability"] = copy.deepcopy(dict(obj_content))  # 当前确认后的规则事实

# 将人工确认的技术效果写入唯一稳定特征。
def apply_feature_effect_review(
    dict_candidate: dict[str, Any],
    dict_embedded: Mapping[str, Any],
) -> None:
    """应用单条人工特征技术效果确认。

    参数：
    - `dict_candidate`：等待状态推进的独立模型候选。
    - `dict_embedded`：已经绑定实时事实的人工确认记录。

    返回：
    - `None`。

    异常：
    - `ValueError`：效果为空或目标特征不存在时抛出。
    """

    # 效果数组来自已经计算 target_hash 的嵌入记录。
    obj_content = dict_embedded.get("target_content")  # 当前确认的技术效果数组

    # 空数组不能制造形式上的因果效果闭包。
    if not isinstance(obj_content, list) or not obj_content:

        # 要求调用方提交实体效果文本。
        raise ValueError("> ERR: [Python] 技术效果确认内容必须为非空数组。")

    # 稳定 feature_id 是允许写入的唯一定位方式。
    str_target_id = str(dict_embedded.get("target_id", ""))  # 当前目标特征身份

    # 记录目标是否真实存在，禁止静默生成新特征。
    bool_updated = False  # 当前候选是否已更新唯一目标

    # 遍历正式特征登记表定位同一稳定身份。
    for dict_feature in dict_candidate.get("feature_registry", []):

        # 非结构化记录或其他特征都不属于当前确认目标。
        if not isinstance(dict_feature, dict) or str(dict_feature.get("feature_id", "")) != str_target_id:

            # 当前特征不能接收本次效果确认，继续定位。
            continue

        # 事实域保存独立效果数组，避免与审查快照共享引用。
        dict_feature["technical_effects"] = copy.deepcopy(obj_content)  # 当前确认后的效果事实

        # 标记唯一写入已经完成。
        bool_updated = True  # 当前稳定特征已经更新

        # feature_id 全局唯一，命中后无需继续扫描。
        break

    # 悬空确认不能进入活动记录或关闭待办。
    if not bool_updated:

        # 目标缺失说明父事实与确认输入不一致。
        raise ValueError("> ERR: [Python] 技术效果确认目标不存在。")

# 按人工复核目标类型分派唯一允许的事实域更新。
def apply_human_fact_review(
    dict_candidate: dict[str, Any],
    dict_embedded: Mapping[str, Any],
) -> None:
    """按目标类型应用人工确认事实，未知类型保持无操作。

    参数：
    - `dict_candidate`：等待状态推进的独立模型候选。
    - `dict_embedded`：已经绑定实时事实的人工确认记录。

    返回：
    - `None`。

    异常：
    - `ValueError`：受支持目标的确认内容无效时抛出。
    """

    # 目标类型决定唯一允许更新的事实域，禁止宽泛顶层白名单。
    str_target_type = str(dict_embedded.get("target_type", ""))  # 当前人工事实目标类型

    # AI 适用性确认写入规则事实域。
    if str_target_type == "ai_applicability":

        # 专用 helper 校验并复制当前确认内容。
        apply_ai_applicability_review(dict_candidate, dict_embedded)

        # 当前目标已完成，避免继续匹配其他事实域。
        return

    # 技术效果确认只允许更新指定稳定特征。
    if str_target_type == "feature_technical_effect":

        # 专用 helper 校验并更新唯一 feature_id。
        apply_feature_effect_review(dict_candidate, dict_embedded)

# 构造 recorder 的唯一纯状态转换候选。
def build_review_candidate(
    dict_parent: Mapping[str, Any],
    dict_embedded: Mapping[str, Any],
    str_reviewer_type: str,
    dict_claims_map: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """从父模型和单条记录构造完整子候选，不修改调用方对象。

    参数：
    - `dict_parent`：当前 recorder 父模型。
    - `dict_embedded`：已经绑定实时事实的审查记录。
    - `str_reviewer_type`：`agent` 或 `human`。
    - `dict_claims_map`：独立项确认使用的当前 Claims Map 3。

    返回：
    - `dict[str, Any]`：除 provenance 外的唯一合法子候选。

    异常：
    - `ValueError`：人工事实内容无效、目标缺失或记录身份冲突时抛出。
    """

    # 深复制把 production 转换和 provenance 重放都固定为无副作用纯函数。
    dict_candidate = copy.deepcopy(dict(dict_parent))  # 等待完整状态推进的独立候选

    # 只有人工确认允许在记录状态推进前更新受控事实域。
    if str_reviewer_type == "human":

        # 分派 helper 只更新当前 target_type 允许的事实域。
        apply_human_fact_review(dict_candidate, dict_embedded)

    # 活动态、不可变历史和迁移待办继续由唯一状态实现推进。
    replace_active_review(
        dict_candidate,
        str_reviewer_type,
        copy.deepcopy(dict(dict_embedded)),
        dict_claims_map,
    )

    # 返回完整候选供 recorder 发布或 provenance canonical 比较。
    return dict_candidate

# 从当前事实域收集全部章节和技术特征 AI 审查目标。
def required_agent_targets(dict_model: Mapping[str, Any]) -> set[tuple[str, str]]:
    """收集所有章节和技术特征审查目标。

    参数：
    - `dict_model`：当前 Model 4。

    返回：
    - `set[tuple[str, str]]`：目标类型与身份集合。

    异常：
    - 无。
    """

    # 先收集带稳定身份的章节目标。
    set_targets = {
        ("section", str(dict_item.get("id")))  # 当前章节目标
        for dict_item in dict_model.get("sections", [])  # 当前模型章节记录
        if isinstance(dict_item, Mapping) and dict_item.get("id")  # 只接纳有身份映射
    }  # 全部章节审查目标

    # 把带稳定 feature_id 的技术特征目标合并进同一集合。
    set_targets.update(
        {
            ("feature", str(dict_item.get("feature_id")))  # 当前技术特征目标
            for dict_item in dict_model.get("feature_registry", [])  # 当前特征登记
            if isinstance(dict_item, Mapping) and dict_item.get("feature_id")  # 排除缺少 feature_id 的记录
        }
    )

    # 返回章节和技术特征联合目标集合。
    return set_targets

# 从当前事实域推导尚未关闭的人工确认类别。
def required_confirmation_categories(
    dict_model: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None,
    set_confirmed_targets: set[tuple[str, str]],
) -> list[str]:
    """从当前事实域推导尚未关闭的人工确认类别。

    参数：
    - `dict_model`：当前 Model 4。
    - `dict_claims_map`：可选当前 Claims Map 3。
    - `set_confirmed_targets`：已确认的人工目标集合。

    返回：
    - `list[str]`：仍需人工关闭的类别列表。

    异常：
    - 无。
    """

    # 准备按固定业务顺序返回的人工待办类别。
    list_pending: list[str] = []  # 当前人工确认待办类别

    # 只收集带 data_id 的可治理数据事实。
    list_data = [
        dict_item  # 当前可治理数据记录
        for dict_item in dict_model.get("data_registry", [])  # 当前数据登记
        if isinstance(dict_item, Mapping) and dict_item.get("data_id")  # 数据事实必须具备可确认身份
    ]  # 需要逐项确认的数据事实

    # 任一数据事实尚未确认时保留 governed_facts 类别。
    if any(
        ("data", str(dict_item["data_id"])) not in set_confirmed_targets  # 当前数据尚未确认
        for dict_item in list_data  # 逐项核对可治理数据
    ):

        # 添加数据事实确认待办。
        list_pending.append("governed_facts")

    # 默认没有可验证的独立权利要求身份。
    list_independent_ids: list[str] = []  # 当前独立权利要求编号

    # 只有真实 claims 映射才参与独立权利要求确认推导。
    if isinstance(dict_claims_map, Mapping):

        # 从当前 claims 事实读取全部独立权利要求编号。
        list_independent_ids = [
            str(dict_claim.get("claim_no"))  # 待人工确认的独立权利要求编号
            for dict_claim in dict_claims_map.get("claims", [])  # 当前 claims 记录
            if isinstance(dict_claim, Mapping)  # 只读取结构化 claim
            and str(dict_claim.get("claim_type", "")).startswith("independent_")  # 只接纳独立类型
        ]  # 当前全部独立权利要求编号

    # 缺少独立权利要求或任一独立项未确认时保留该类别。
    if not list_independent_ids or any(
        ("independent_claim", str_claim_id) not in set_confirmed_targets  # 当前独立项尚未确认
        for str_claim_id in list_independent_ids  # 逐项核对当前独立项
    ):

        # 添加独立权利要求特征集确认待办。
        list_pending.append("independent_claim_feature_sets")

    # 读取 AI 规则适用性事实域。
    obj_rules = dict_model.get("rule_applicability")  # 当前规则适用性根值

    # 缺失规则、仍 pending 或缺少人工确认都保留 AI 适用性待办。
    if (
        not isinstance(obj_rules, Mapping)  # 规则根类型无效
        or obj_rules.get("ai_applicability") == "pending"  # AI 适用性尚未决定
        or ("ai_applicability", "model") not in set_confirmed_targets  # 尚无人工确认
    ):

        # 添加 AI 适用性确认待办。
        list_pending.append("ai_applicability")

    # 任一技术特征缺少效果时保留技术效果确认类别。
    if any(
        isinstance(dict_feature, Mapping)  # 当前特征必须可解释
        and not dict_feature.get("technical_effects")  # 当前特征缺少技术效果
        for dict_feature in dict_model.get("feature_registry", [])  # 用于效果缺口检查的特征登记
    ):

        # 添加技术效果确认待办。
        list_pending.append("feature_technical_effects")

    # 返回由实时事实和活动确认共同推导的待办类别。
    return list_pending

# 从活动记录和当前事实域完整重算待办，禁止增量状态残留。
def refresh_pending_state(
    dict_model: dict[str, Any],
    dict_claims_map: Mapping[str, Any] | None = None,
) -> None:
    """从活动记录和当前事实域完整重算待办。

    参数：
    - `dict_model`：待更新的 Model 4。
    - `dict_claims_map`：可选当前 Claims Map 3。

    返回：
    - `None`：待办和迁移状态已原地刷新。

    异常：
    - 无。
    """

    # 读取可变语义审查根。
    obj_review = dict_model.get("semantic_review")  # 等待待办重算的审查根

    # 坏类型容器留给 schema 报告，状态模块不猜测修复。
    if not isinstance(obj_review, dict):

        # 无可更新容器时直接返回。
        return

    # 加载唯一目标解析和哈希规则。
    module_validator = load_validator()  # 当前待办重算验证器

    # 读取当前 AI 活动记录。
    list_agent = obj_review.get("agent_reviews", [])  # 当前 AI 活动记录根值

    # 只有 verdict=pass 的活动记录才能关闭对应目标。
    set_passed = {
        (str(dict_item.get("target_type")), str(dict_item.get("target_id")))  # 已通过目标
        for dict_item in list_agent  # 当前 AI 活动记录
        if isinstance(dict_item, Mapping)  # 只读取结构化代理记录
        and dict_item.get("verdict") == "pass"  # 只有通过裁决可关闭目标
        and record_hash_is_current(dict_model, dict_claims_map, dict_item, "agent", module_validator)  # 只接纳当前事实上的通过记录
    }  # 当前已通过 AI 审查目标

    # 用全量目标减去已通过目标，重建稳定排序的 AI 待办。
    obj_review["pending_reviews"] = [
        f"{str_type}:{str_id}"  # 对外稳定待办标识
        for str_type, str_id in sorted(  # 按目标类型和身份稳定排序
            required_agent_targets(dict_model) - set_passed  # 尚未通过的目标差集
        )
    ]  # 完整重算后的 AI 审查待办

    # 读取当前人工活动确认记录。
    list_human = obj_review.get("human_confirmations", [])  # 当前人工活动记录根值

    # 只有 decision=confirm 的活动记录才能关闭人工目标。
    set_confirmed = {
        (str(dict_item.get("target_type")), str(dict_item.get("target_id")))  # 已确认目标
        for dict_item in list_human  # 当前人工活动确认记录
        if isinstance(dict_item, Mapping)  # 只读取结构化人工记录
        and dict_item.get("decision") == "confirm"  # 只有确认决定可关闭目标
        and record_hash_is_current(dict_model, dict_claims_map, dict_item, "human", module_validator)  # 只接纳当前事实上的确认
    }  # 当前已经人工确认的目标

    # 从当前事实域和已确认目标完整推导人工待办类别。
    obj_review["pending_confirmations"] = required_confirmation_categories(  # 保存尚未由 confirm 活动记录关闭的事实类别
        dict_model,  # 提供数据、规则和技术效果缺口事实
        dict_claims_map,  # 提供独立权利要求编号事实
        set_confirmed,  # 提供已经由 confirm 决定关闭的目标
    )  # governed_facts、独立项、AI 适用性和技术效果缺口类别

    # 读取可选迁移元数据，只有 pending 迁移需要自动闭包。
    obj_migration = dict_model.get("migration")  # 当前迁移元数据根值

    # 迁移动作由当前事实闭包派生，禁止保留已经完成的静态字符串。
    if isinstance(obj_migration, dict):

        # 从原有动作集合开始逐项移除已经完成的类别。
        list_actions = list(obj_migration.get("pending_actions", []))  # 当前迁移动作副本

        # 全部 AI 目标具有新鲜 pass 时关闭代理审查动作。
        if not obj_review["pending_reviews"]:

            # 移除已经由当前哈希证明完成的代理审查动作。
            list_actions = [  # 删除已闭包的代理审查动作
                str_action  # 保留尚未完成的迁移动作
                for str_action in list_actions  # 遍历当前迁移动作
                if str_action != "record_agent_reviews"  # 排除已完成代理审查
            ]

        # 全部人工目标具有新鲜 confirm 时关闭人工确认动作。
        if not obj_review["pending_confirmations"]:

            # 移除已经由当前哈希证明完成的人工确认动作。
            list_actions = [  # 删除已由有效确认关闭的人工动作
                str_action  # 保留其他待处理迁移事项
                for str_action in list_actions  # 遍历确认前动作快照
                if str_action != "record_human_confirmations"  # 排除已完成人工确认
            ]

        # 保存由当前活动记录派生的剩余动作。
        obj_migration["pending_actions"] = list_actions  # 保存实时闭包后的迁移动作

    # Claims companion 完成也是迁移闭包的必要事实。
    bool_claims_complete = (
        not isinstance(obj_migration, Mapping)  # 原生模型没有迁移对象
        or "claims_state" not in obj_migration  # 旧原生元数据没有 companion 状态
        or obj_migration.get("claims_state") == "complete"  # 迁移模型已完成 companion 映射
    )  # 当前迁移是否已经完成 Claims 映射

    # pending_actions 必须由已完成事实域清空后才能完成迁移。
    list_pending_actions = (
        obj_migration.get("pending_actions", [])  # 读取当前正式动作
        if isinstance(obj_migration, Mapping)  # 只解释结构化迁移对象
        else []  # 原生模型没有迁移动作
    )  # 当前迁移剩余正式动作

    # 全部待办、Claims 和动作均闭包时才可切换 complete。
    if (
        isinstance(obj_migration, dict)  # 迁移元数据必须可变
        and obj_migration.get("state") == "pending"  # 当前确为待复核迁移
        and not obj_review["pending_reviews"]  # AI 待办已经清空
        and not obj_review["pending_confirmations"]  # 人工待办已经清空
        and bool_claims_complete  # Claims companion 已完成映射
        and not list_pending_actions  # 正式迁移动作已经清空
    ):

        # 标记迁移复核闭环完成，不修改其输入摘要和来源版本。
        obj_migration["state"] = "complete"  # 当前迁移最终状态
