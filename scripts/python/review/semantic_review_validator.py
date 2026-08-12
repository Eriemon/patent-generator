"""校验 Model 4.0 语义审查、人工确认和不可变历史图。"""

# 延迟解析类型注解，兼容技能支持的 Python 版本。
from __future__ import annotations

# 标准库负责内容摘要、容器类型和正式资产路径。
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# 第三方验证器复用 Model 4.0 正式 schema 的审查记录定义。
from jsonschema import Draft202012Validator

# 固定模型 schema 路径，避免为拆分模块复制审查字段合同。
PATH_MODEL_SCHEMA = Path(__file__).resolve().parents[3] / "assets" / "schemas" / "disclosure_model.schema.json"  # Model 4.0 正式结构合同

# 人工确认事项类别只能绑定唯一正式目标类型。
DICT_CONFIRMATION_TARGET_TYPES = {
    "governed_fact": "data",  # 受管事实逐项确认
    "independent_claim_feature_set": "independent_claim",  # 独立项特征集合确认
    "ai_applicability": "ai_applicability",  # AI 规则适用性确认
    "feature_technical_effect": "feature_technical_effect",  # 技术效果确认
}  # 人工确认类型映射

# 将审查缺口统一为聚合验证器可直接消费的 blocker。
def build_blocker(str_code: str, str_message: str, str_suggestion: str) -> dict[str, str]:
    """构造结构化合同 blocker finding。

    参数：
    - `str_code`：稳定规则代码。
    - `str_message`：可定位的问题说明。
    - `str_suggestion`：不虚构事实的修复建议。

    返回：
    - `dict[str, str]`：现有验证报告兼容的 finding。

    异常：
    - 无。
    """

    # 版本二合同缺陷均影响正式可交付性，因此统一使用 blocker 级别。
    return {"level": "blocker", "code": str_code, "message": str_message, "suggestion": str_suggestion}

# 读取正式 JSON Schema 并验证合同自身。
def load_schema(path_schema: Path) -> dict[str, Any]:
    """读取并检查正式 JSON Schema。

    参数：
    - `path_schema`：正式 schema 文件路径。

    返回：
    - `dict[str, Any]`：可交给 Draft 2020-12 验证器的 schema。

    异常：
    - `FileNotFoundError`：schema 缺失时由文件读取上抛。
    - `json.JSONDecodeError`：schema 损坏时由解析器上抛。
    - `jsonschema.exceptions.SchemaError`：schema 不符合 Draft 2020-12 时上抛。
    """

    # 读取 schema 原始内容，确保运行时不使用代码内副本。
    dict_schema = json.loads(path_schema.read_text(encoding="utf-8"))  # 正式 schema 对象

    # 验证 schema 自身后再用于案件数据，避免损坏合同制造假绿。
    Draft202012Validator.check_schema(dict_schema)

    # 返回已验证 schema 供实例校验复用。
    return dict_schema

# 用正式 schema 执行模型实例校验，并转换为统一 blocker。
def validate_review_record_schema(
    dict_record: Mapping[str, Any],
    str_reviewer_type: str,
) -> list[dict[str, str]]:
    """验证单条代理审查或人工确认候选。

    参数：
    - `dict_record`：尚未写入权威模型的审查候选。
    - `str_reviewer_type`：`agent` 或 `human` 审查者类型。

    返回：
    - `list[dict[str, str]]`：候选结构不合规的 blockers。

    异常：
    - schema 文件缺失或损坏时由底层异常上抛。
    """

    # 从正式模型合同复用审查记录定义。
    dict_model_schema = load_schema(PATH_MODEL_SCHEMA)  # 版本四模型结构合同

    # 审查者类型决定候选必须满足的定义。
    str_definition = (
        "agent_review"  # 代理审查候选定义名称
        if str_reviewer_type == "agent"  # 代理类型选择代理记录定义
        else "human_confirmation"  # 人工类型选择确认记录定义
    )  # 当前候选定义名称

    # 构造只引用目标定义的局部验证合同。
    dict_record_schema = {  # 单条审查候选结构合同
        "$schema": "https://json-schema.org/draft/2020-12/schema",  # 合同草案版本
        "$defs": dict_model_schema["$defs"],  # 复用正式模型定义集合
        "$ref": f"#/$defs/{str_definition}",  # 当前候选定义引用
    }

    # 执行候选实例验证并稳定排序失败位置。
    obj_validator = Draft202012Validator(dict_record_schema)  # 单条审查候选验证器

    # 候选错误按实例路径保持跨运行稳定顺序。
    list_errors = sorted(  # 按实例路径排序的候选失败
        obj_validator.iter_errors(dict(dict_record)),  # 当前候选结构错误迭代器
        key=lambda obj_error: list(obj_error.absolute_path),  # 当前错误实例路径
    )

    # 把每个候选失败转换为统一 blocker。
    return [
        build_blocker(
            "REV_SCHEMA",
            (
                "审查候选 schema 失败:"
                f"{'/'.join(str(obj_part) for obj_part in obj_error.absolute_path) or '<root>'}:"
                f"{obj_error.message}"
            ),
            "按 Model 4.0 审查记录合同修复候选后重试",
        )
        for obj_error in list_errors
    ]

# 计算语义审查绑定目标的确定性 SHA-256。
def calculate_semantic_review_hash(
    str_target_type: str,
    str_target_id: str,
    obj_target_content: Any,
    list_evidence_ids: Any,
    str_contract_version: str,
) -> str:
    """计算语义审查记录的规范化目标摘要。

    参数：
    - `str_target_type`：章节、特征、主权项或 AI 适用性等目标类型。
    - `str_target_id`：目标稳定编号。
    - `obj_target_content`：当前目标正文或结构化内容。
    - `list_evidence_ids`：目标当前证据绑定。
    - `str_contract_version`：摘要规则绑定的模型合同版本。

    返回：
    - `str`：跨运行稳定的十六进制 SHA-256。

    异常：
    - `TypeError`：目标内容不是 JSON 兼容值时由编码器上抛。
    """

    # 证据编号排序并去重，使集合语义不受输入排列影响。
    list_normalized_evidence_ids = sorted({str(obj_id) for obj_id in list_evidence_ids or []})  # 规范证据编号

    # 显式列出五个摘要维度，禁止遗漏目标类型或合同版本。
    dict_hash_payload = {
        "target_type": str_target_type,  # 审查目标类型
        "target_id": str_target_id,  # 审查目标稳定编号
        "target_content": obj_target_content,  # 审查目标当前内容
        "evidence_bindings": list_normalized_evidence_ids,  # 审查目标证据集合
        "contract_version": str_contract_version,  # 摘要规则合同版本
    }  # 语义审查规范摘要载荷

    # 排序键和紧凑分隔符固定 UTF-8 输入边界。
    str_canonical = json.dumps(dict_hash_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)  # 规范摘要文本

    # 返回可嵌入 JSON 模型的十六进制摘要。
    return hashlib.sha256(str_canonical.encode("utf-8")).hexdigest()

# 收集证据登记表中的稳定编号，兼容既有 id 与新 evidence_id 字段。
def collect_evidence_ids(dict_evidence_registry: Any) -> set[str]:
    """收集模型实际存在的证据编号。

    参数：
    - `dict_evidence_registry`：证据登记表对象。

    返回：
    - `set[str]`：非空证据编号集合。

    异常：
    - 无。
    """

    # 非对象登记表无法提供 records 数组。
    if not isinstance(dict_evidence_registry, Mapping):

        # 返回空集合，让引用闭包形成明确 blocker。
        return set()

    # 只接受 records 数组中的映射记录。
    list_records = dict_evidence_registry.get("records", [])  # 证据记录数组

    # records 损坏时不尝试迭代其他类型。
    if not isinstance(list_records, list):

        # 空集合确保所有显式证据引用都被识别为悬空。
        return set()

    # 同时读取新旧证据编号键，保持迁移期间可定位。
    return {
        str(dict_record.get("evidence_id") or dict_record.get("id"))
        for dict_record in list_records
        if isinstance(dict_record, Mapping) and (dict_record.get("evidence_id") or dict_record.get("id"))
    }

# 判断单个技术特征是否形成章节与证据支撑闭包。
def feature_has_support_closure(
    dict_feature: Mapping[str, Any],
    set_section_ids: set[str],
    set_evidence_ids: set[str],
    dict_section_evidence: Mapping[str, set[str]],
) -> bool:
    """判断技术特征的文本、效果、章节和证据是否闭合。

    参数：
    - `dict_feature`：当前稳定技术特征。
    - `set_section_ids`：模型实际章节编号。
    - `set_evidence_ids`：模型实际证据编号。
    - `dict_section_evidence`：章节到证据编号的绑定。

    返回：
    - `bool`：全部支撑条件成立时为真。

    异常：
    - 无。
    """

    # 当前特征声明的章节必须全部存在。
    set_bound_sections = {
        str(obj_id)  # 当前特征声明的规范章节编号
        for obj_id in dict_feature.get("section_ids", [])  # 遍历特征章节绑定
    }  # 当前特征章节集合

    # 当前特征声明的证据必须全部存在。
    set_bound_evidence = {
        str(obj_id)  # 当前特征声明的规范证据编号
        for obj_id in dict_feature.get("evidence_ids", [])  # 遍历特征证据绑定
    }  # 当前特征证据集合

    # 章节实际绑定的证据并集决定真实支撑范围。
    set_section_bound_evidence = {
        str_evidence_id  # 当前绑定章节真实引用的证据
        for str_section_id in set_bound_sections  # 遍历特征声明章节
        for str_evidence_id in dict_section_evidence.get(str_section_id, set())  # 遍历章节证据
    }  # 特征声明章节的实际证据并集

    # 所有语义和引用条件同时成立才构成支撑闭包。
    return bool(
        str(dict_feature.get("text", "")).strip()
        and dict_feature.get("technical_effects")
        and set_bound_sections
        and set_bound_sections <= set_section_ids
        and set_bound_evidence
        and set_bound_evidence <= set_evidence_ids
        and set_bound_evidence <= set_section_bound_evidence
    )

# 检查稳定特征到章节、证据和技术效果的闭包。
def validate_feature_registry(dict_model: Mapping[str, Any]) -> list[dict[str, str]]:
    """验证 Model 4.0 技术特征登记表。

    参数：
    - `dict_model`：待验证版本四模型。

    返回：
    - `list[dict[str, str]]`：特征缺失、重复或悬空引用 blockers。

    异常：
    - 无。
    """

    # 读取新登记表，缺失和空数组使用独立稳定代码。
    obj_features = dict_model.get("feature_registry")  # 原始特征登记表

    # 新字段缺失或不是非空数组时不能继续形成权利要求映射。
    if not isinstance(obj_features, list) or not obj_features:

        # 返回独立模型代码，避免只依赖 schema 文本消息。
        return [build_blocker("MOD004", "Model 4.0 缺少非空 feature_registry", "逐项登记稳定 feature_id、章节、证据和技术效果")]

    # 建立实际章节与证据集合供逐特征引用检查。
    set_section_ids = {
        str(dict_section.get("id"))  # 当前模型章节编号
        for dict_section in dict_model.get("sections", [])  # 遍历模型章节
        if isinstance(dict_section, Mapping) and dict_section.get("id")  # 保留有效章节
    }  # 当前章节编号集合

    # 建立章节证据绑定，特征证据必须由其声明章节实际引用。
    dict_section_evidence = {
        str(dict_section.get("id")): {  # 当前章节稳定编号
            str(obj_evidence_id)  # 当前章节引用的证据编号
            for obj_evidence_id in dict_section.get("evidence_ids", [])  # 提取特征校验章节证据
        }
        for dict_section in dict_model.get("sections", [])  # 建立特征校验章节索引
        if isinstance(dict_section, Mapping) and dict_section.get("id")  # 排除损坏章节
    }  # 章节证据绑定索引

    # 证据集合只来自正式 evidence_registry。
    set_evidence_ids = collect_evidence_ids(dict_model.get("evidence_registry"))  # 当前证据编号集合

    # 汇总稳定特征编号，重复值会破坏权利要求引用身份。
    list_feature_ids = [
        str(dict_feature.get("feature_id", ""))  # 当前稳定特征编号
        for dict_feature in obj_features  # 遍历特征登记表
        if isinstance(dict_feature, Mapping)  # 排除损坏占位值
    ]  # 特征编号序列

    # 准备逐项特征闭包发现。
    list_findings: list[dict[str, str]] = []  # 特征登记表 findings

    # 重复编号必须在进入 claims map 前阻断。
    if len(list_feature_ids) != len(set(list_feature_ids)):

        # 一个稳定代码足以定位当前登记表身份冲突。
        list_findings.append(build_blocker("FT001", "feature_registry 含重复 feature_id", "为每项技术特征分配唯一稳定编号"))

    # 逐特征验证内容、章节、证据和效果都形成闭包。
    for dict_feature in obj_features:

        # 非对象占位符不能形成技术特征。
        if not isinstance(dict_feature, Mapping):

            # 保留损坏值便于上游定位。
            list_findings.append(build_blocker("FT002", f"技术特征不是对象:{dict_feature}", "删除占位值并登记完整技术特征"))

            # 跳过损坏记录的字段读取。
            continue

        # 读取当前特征稳定编号供消息定位。
        str_feature_id = str(dict_feature.get("feature_id", ""))  # 当前技术特征编号

        # 内容、效果或引用任一缺失都不能支撑权利要求。
        if not feature_has_support_closure(
            dict_feature,
            set_section_ids,
            set_evidence_ids,
            dict_section_evidence,
        ):

            # 统一使用闭包代码，消息保留具体 feature_id。
            list_findings.append(build_blocker("FT003", f"技术特征闭包不完整:{str_feature_id}", "补齐非空文本、技术效果及真实章节和证据引用"))

    # 返回全部稳定特征闭包问题。
    return list_findings

# 解析代理审查目标的当前内容和证据绑定。
def resolve_review_target(
    dict_model: Mapping[str, Any],
    str_target_type: str,
    str_target_id: str,
) -> tuple[Any, list[str]] | None:
    """解析语义审查当前绑定目标。

    参数：
    - `dict_model`：当前版本四模型。
    - `str_target_type`：`section`、`feature` 或 `model`。
    - `str_target_id`：目标稳定编号。

    返回：
    - `tuple[Any, list[str]] | None`：当前内容和证据编号，目标不存在时为空。

    异常：
    - 无。
    """

    # 章节审查绑定正文内容和章节证据。
    if str_target_type == "section":

        # 逐章按稳定 id 精确匹配，不使用标题或文本相似度。
        for dict_section in dict_model.get("sections", []):

            # 只处理映射章节并要求 id 完全相同。
            if isinstance(dict_section, Mapping) and str(dict_section.get("id", "")) == str_target_id:

                # 返回当前章节正文和证据绑定。
                return dict_section.get("content", ""), list(dict_section.get("evidence_ids", []))

    # 技术特征审查绑定特征文本和其精确证据。
    if str_target_type == "feature":

        # 逐特征按稳定 feature_id 精确匹配。
        for dict_feature in dict_model.get("feature_registry", []):

            # 找到当前技术特征后返回文本和证据集合。
            if isinstance(dict_feature, Mapping) and str(dict_feature.get("feature_id", "")) == str_target_id:

                # 摘要绑定会影响语义结论的完整特征内容，禁止章节或效果变化后沿用旧审查。
                dict_target_content = {  # 完整特征语义审查目标
                    "text": dict_feature.get("text", ""),  # 当前特征正文
                    "section_ids": list(dict_feature.get("section_ids", [])),  # 展开章节
                    "technical_effects": list(dict_feature.get("technical_effects", [])),  # 技术效果
                }

                # 返回完整特征内容及其精确证据集合。
                return dict_target_content, list(dict_feature.get("evidence_ids", []))

    # 模型级审查绑定规则适用性和全部证据编号。
    if str_target_type == "model" and str_target_id == "model":

        # 返回 AI 适用性对象和当前证据全集。
        return (
            dict_model.get("rule_applicability", {}),
            sorted(collect_evidence_ids(dict_model.get("evidence_registry"))),
        )

    # 未找到精确目标时返回空标记。
    return None

# 从实时 Claims Map 和模型特征登记表解析独立项摘要目标。
def resolve_independent_claim_target(
    dict_model: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None,
    str_target_id: str,
) -> tuple[list[str], list[str]] | None:
    """解析实时独立项的特征集合和证据并集。

    参数：
    - `dict_model`：当前版本四模型。
    - `dict_claims_map`：当前实时权利要求映射。
    - `str_target_id`：待解析的独立权利要求编号。

    返回：
    - `tuple[list[str], list[str]] | None`：实时目标，目标不存在时为空。

    异常：
    - 无。
    """

    # 缺少实时映射时禁止相信确认记录自声明的内容。
    if not isinstance(dict_claims_map, Mapping):

        # 无权威目标来源时返回悬空标记。
        return None

    # 特征索引只消费当前模型的稳定 feature_id。
    dict_features = {
        str(dict_item.get("feature_id", "")): dict_item  # 当前稳定特征索引项
        for dict_item in dict_model.get("feature_registry", [])  # 遍历实时特征登记表
        if isinstance(dict_item, Mapping) and dict_item.get("feature_id")  # 排除损坏特征项
    }  # 当前模型实时特征索引

    # 按 claim_no 精确解析当前独立权利要求。
    for dict_claim in dict_claims_map.get("claims", []):

        # 非映射或编号不同的权利要求不是当前目标。
        if not isinstance(dict_claim, Mapping) or str(dict_claim.get("claim_no", "")) != str_target_id:

            # 继续查找具有同一稳定编号的记录。
            continue

        # 从属项不能伪装为独立项确认目标。
        if not str(dict_claim.get("claim_type", "")).startswith("independent_"):

            # 目标类型与实时权利要求类型不一致。
            return None

        # 当前 feature_ids 是摘要内容的唯一权威来源。
        list_feature_ids = [str(obj_id) for obj_id in dict_claim.get("feature_ids", [])]  # 实时特征集合

        # 任一悬空 feature_id 都会使整个独立项目标失效。
        if any(str_feature_id not in dict_features for str_feature_id in list_feature_ids):

            # 把目标交给调用方按 HUM004 阻断。
            return None

        # 证据并集只从当前模型特征登记表重新派生。
        set_evidence_ids = {
            str(obj_evidence_id)  # 规范化当前证据编号
            for str_feature_id in list_feature_ids  # 遍历实时独立项特征
            for obj_evidence_id in dict_features[str_feature_id].get("evidence_ids", [])  # 遍历实时证据
        }  # 当前独立项证据并集

        # 目标摘要只使用实时 feature_ids 和证据并集。
        return list_feature_ids, sorted(set_evidence_ids)

    # Claims Map 中不存在当前 claim_no。
    return None

# 解析人工确认当前绑定目标，独立项必须来自实时 Claims Map。
def resolve_human_confirmation_target(
    dict_model: Mapping[str, Any],
    dict_confirmation: Mapping[str, Any],
    dict_claims_map: Mapping[str, Any] | None = None,
) -> tuple[Any, list[str]] | None:
    """解析受管事实、独立项特征集和 AI 适用性确认目标。

    参数：
    - `dict_model`：当前版本四模型。
    - `dict_confirmation`：待解析的人工确认记录。
    - `dict_claims_map`：与当前模型共同交付的实时权利要求映射。

    返回：
    - `tuple[Any, list[str]] | None`：当前内容和证据，目标不存在时为空。

    异常：
    - 无。
    """

    # 提取人工确认目标坐标。
    str_target_type = str(dict_confirmation.get("target_type", ""))  # 人工确认目标类型

    # 目标编号与类型共同定位当前事实。
    str_target_id = str(dict_confirmation.get("target_id", ""))  # 人工确认目标编号

    # 数据事实目标从正式登记表中精确解析。
    if str_target_type == "data":

        # 按稳定 data_id 查找当前事实记录。
        for dict_record in dict_model.get("data_registry", []):

            # 找到目标后返回事实快照及证据绑定。
            if isinstance(dict_record, Mapping) and str(dict_record.get("data_id", "")) == str_target_id:

                # 数据确认必须绑定完整事实映射。
                return dict(dict_record), [str(obj_id) for obj_id in dict_record.get("evidence_ids", [])]

    # AI 适用性绑定完整规则对象，不使用研发证据。
    if str_target_type == "ai_applicability" and str_target_id == "model":

        # 返回当前模型级规则事实。
        return dict_model.get("rule_applicability", {}), []

    # 技术效果确认绑定当前特征效果和原始研发证据。
    if str_target_type == "feature_technical_effect":

        # 按稳定 feature_id 精确定位当前技术特征。
        for dict_feature in dict_model.get("feature_registry", []):

            # 找到目标后返回当前效果数组和证据绑定。
            if isinstance(dict_feature, Mapping) and str(dict_feature.get("feature_id", "")) == str_target_id:

                # 当前效果变化会自然使旧人工确认摘要失效。
                return (
                    list(dict_feature.get("technical_effects", [])),
                    [str(obj_id) for obj_id in dict_feature.get("evidence_ids", [])],
                )

    # 独立项只能从同一交付版本的 Claims Map 解析。
    if str_target_type == "independent_claim":

        # 委托独立项解析器建立实时目标。
        return resolve_independent_claim_target(dict_model, dict_claims_map, str_target_id)

    # 未找到目标时交给调用方形成悬空确认 blocker。
    return None

# 为同一目标选择数组中最后一条活动记录。
def collect_active_review_records(obj_records: Any) -> dict[tuple[str, str], Any]:
    """按目标坐标确定性选择最新审查记录。

    参数：
    - `obj_records`：代理审查或人工确认原始数组。

    返回：
    - `dict[tuple[str, str], Any]`：每个目标的最后一条活动记录。

    异常：
    - 无。
    """

    # 非数组容器视为空记录集合，由覆盖规则形成缺口。
    list_records = obj_records if isinstance(obj_records, list) else []  # 可安全迭代记录

    # 映射按目标键覆盖，天然保留最后一条记录。
    dict_active_records: dict[tuple[str, str], Any] = {}  # 当前活动审查映射

    # 依次登记记录，后项覆盖同目标前项。
    for obj_record in list_records:

        # 合法映射使用真实目标坐标。
        if isinstance(obj_record, Mapping):

            # 目标类型和编号共同确定活动记录身份。
            tuple_record_key = (
                str(obj_record.get("target_type", "")),  # 当前记录目标类型
                str(obj_record.get("target_id", "")),  # 当前记录目标编号
            )  # 当前记录目标坐标

        # 损坏记录使用唯一伪坐标保留诊断。
        else:

            # 唯一编号防止多个损坏值互相覆盖。
            tuple_record_key = (
                "invalid",  # 损坏记录伪目标类型
                str(len(dict_active_records)),  # 损坏记录唯一序号
            )  # 当前损坏记录伪坐标

        # 后出现的同目标记录成为唯一活动记录。
        dict_active_records[tuple_record_key] = obj_record  # 当前目标最新记录

    # 返回确定性活动记录集合。
    return dict_active_records

# 验证所有活动代理审查并返回有效目标。
def validate_agent_review_records(
    dict_model: Mapping[str, Any],
    obj_records: Any,
) -> tuple[list[dict[str, str]], set[tuple[str, str]]]:
    """验证代理审查的目标、摘要、裁决和五维覆盖。

    参数：
    - `dict_model`：当前版本四模型。
    - `obj_records`：原始代理审查数组。

    返回：
    - `tuple[list[dict[str, str]], set[tuple[str, str]]]`：发现和有效目标。

    异常：
    - 无。
    """

    # 分别收集失败发现和通过目标。
    list_findings: list[dict[str, str]] = []  # 活动代理审查发现

    # 有效目标将在覆盖闭包中与必审目标比较。
    set_valid_targets: set[tuple[str, str]] = set()  # 有效代理审查目标

    # 同目标仅保留输入数组中的最后一条记录。
    dict_active_records = collect_active_review_records(obj_records)  # 最新代理审查

    # 逐条验证当前活动记录，旧记录不参与交付判断。
    for dict_review in dict_active_records.values():

        # 非对象记录不能形成目标或摘要。
        if not isinstance(dict_review, Mapping):

            # 保留损坏值以便上游定位。
            list_findings.append(
                build_blocker(
                    "REV004",
                    f"代理审查记录不是对象:{dict_review}",
                    "删除占位值并重新记录审查",
                )
            )

            # 跳过损坏记录的字段访问。
            continue

        # 当前目标坐标用于解析模型事实。
        str_target_type = str(dict_review.get("target_type", ""))  # 代理审查目标类型

        # 目标编号必须匹配章节或特征登记表。
        str_target_id = str(dict_review.get("target_id", ""))  # 代理审查目标编号

        # 解析当前目标内容及其证据绑定。
        tuple_target = resolve_review_target(  # 当前代理审查目标
            dict_model,  # 提供章节和特征事实的模型
            str_target_type,  # 当前代理目标类型
            str_target_id,  # 当前代理目标编号
        )

        # 悬空目标没有可计算的当前摘要。
        if tuple_target is None:

            # 要求删除悬空记录或恢复稳定目标。
            list_findings.append(
                build_blocker(
                    "REV004",
                    f"语义审查目标不存在:{str_target_type}:{str_target_id}",
                    "删除悬空记录或恢复稳定目标",
                )
            )

            # 当前记录不能计入有效覆盖。
            continue

        # 按当前内容、证据和合同版本复算目标摘要。
        str_expected_hash = calculate_semantic_review_hash(  # 当前代理审查应有摘要
            str_target_type,  # 代理摘要绑定的目标类型
            str_target_id,  # 代理摘要绑定的稳定编号
            tuple_target[0],  # 当前代理目标完整内容
            tuple_target[1],  # 当前代理目标证据绑定
            str(dict_model.get("contract_version", "")),  # 当前模型合同版本
        )

        # 目标变化后旧摘要立即失效。
        if dict_review.get("target_hash") != str_expected_hash:

            # 稳定代码要求依据当前事实重新审查。
            list_findings.append(
                build_blocker(
                    "REV005",
                    f"语义审查哈希过期:{str_target_type}:{str_target_id}",
                    "依据当前内容和证据重新记录审查",
                )
            )

            # 过期记录不能计入有效覆盖。
            continue

        # 五个审查维度必须全部明确为真。
        dict_coverage = dict_review.get("coverage", {})  # 当前代理审查覆盖表

        # 五个维度共同决定代理审查是否完整。
        tuple_coverage_keys = (
            "enablement",  # 可实施性覆盖维度
            "mechanism",  # 技术机制覆盖维度
            "causal_effect",  # 因果效果覆盖维度
            "terminology",  # 术语一致性覆盖维度
            "evidence_consistency",  # 证据一致性覆盖维度
        )  # 必须覆盖的五个审查维度

        # pass 裁决和五个真值必须同时成立。
        bool_complete = bool(  # 当前代理审查是否完整通过
            dict_review.get("verdict") == "pass"  # 当前裁决必须通过
            and isinstance(dict_coverage, Mapping)  # 覆盖表必须是映射
            and all(  # 五个覆盖维度必须全部为真
                dict_coverage.get(str_key)  # 当前覆盖维度真值
                for str_key in tuple_coverage_keys  # 遍历合同规定的覆盖维度
            )
        )

        # revise、block 或维度缺失都保持阻断。
        if not bool_complete:

            # 要求形成覆盖完整的代理裁决。
            list_findings.append(
                build_blocker(
                    "REV004",
                    f"语义审查未完整通过:{str_target_type}:{str_target_id}",
                    "覆盖可实施性、机制、因果效果、术语和证据一致性",
                )
            )

            # 未通过记录不计入覆盖。
            continue

        # 当前记录通过全部活动审查条件。
        set_valid_targets.add((str_target_type, str_target_id))

    # 返回活动记录发现及有效目标。
    return list_findings, set_valid_targets

# 验证所有活动人工确认并返回有效目标。
def validate_human_confirmation_records(
    dict_model: Mapping[str, Any],
    obj_records: Any,
    dict_claims_map: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, str]], set[tuple[str, str]]]:
    """验证人工确认目标、摘要和决定。

    参数：
    - `dict_model`：当前版本四模型。
    - `obj_records`：原始人工确认数组。
    - `dict_claims_map`：与当前模型共同交付的实时权利要求映射。

    返回：
    - `tuple[list[dict[str, str]], set[tuple[str, str]]]`：发现和有效目标。

    异常：
    - 无。
    """

    # 分别收集失败发现和有效确认目标。
    list_findings: list[dict[str, str]] = []  # 活动人工确认发现

    # 有效人工目标用于逐项事实和 AI 确认闭包。
    set_valid_targets: set[tuple[str, str]] = set()  # 有效人工确认目标

    # 同目标仅保留输入数组中的最后一条决定。
    dict_active_records = collect_active_review_records(obj_records)  # 最新人工确认

    # 逐项复算当前活动人工确认。
    for dict_confirmation in dict_active_records.values():

        # 非对象记录无法提供目标坐标。
        if not isinstance(dict_confirmation, Mapping):

            # 保留损坏值以便上游修复。
            list_findings.append(
                build_blocker(
                    "HUM004",
                    f"人工确认记录不是对象:{dict_confirmation}",
                    "删除占位值并重新确认",
                )
            )

            # 跳过损坏记录字段访问。
            continue

        # 解析当前确认目标和稳定坐标。
        str_target_type = str(dict_confirmation.get("target_type", ""))  # 人工目标类型

        # 目标编号与类型共同定位当前确认事实。
        str_target_id = str(dict_confirmation.get("target_id", ""))  # 人工目标编号

        # 事项类别必须与目标类型遵循唯一正式映射。
        str_confirmation_type = str(dict_confirmation.get("confirmation_type", ""))  # 人工确认事项类别

        # 未声明类别或合法类别错配都不能形成有效确认。
        if DICT_CONFIRMATION_TARGET_TYPES.get(str_confirmation_type) != str_target_type:

            # 运行时显式复核 schema 映射，防止绕过结构验证器。
            list_findings.append(
                build_blocker(
                    "HUM004",
                    f"人工确认类型与目标错配:{str_confirmation_type}:{str_target_type}",
                    "按正式 confirmation_type 与 target_type 映射重新确认",
                )
            )

            # 错配记录不能进入目标解析或哈希闭包。
            continue

        # 解析当前人工确认内容及其证据绑定。
        tuple_target = resolve_human_confirmation_target(  # 当前人工确认目标
            dict_model,  # 提供受管事实和规则内容的模型
            dict_confirmation,  # 当前活动人工确认记录
            dict_claims_map,  # 提供实时独立权利要求及其 feature_ids
        )

        # 悬空目标不能形成有效人工决定。
        if tuple_target is None:

            # 要求删除悬空确认或恢复目标。
            list_findings.append(
                build_blocker(
                    "HUM004",
                    f"人工确认目标不存在:{str_target_type}:{str_target_id}",
                    "删除悬空记录或恢复确认目标",
                )
            )

            # 当前悬空记录不能继续复算摘要。
            continue

        # 人工确认与代理审查使用同一摘要协议。
        str_expected_hash = calculate_semantic_review_hash(  # 当前人工确认应有摘要
            str_target_type,  # 当前人工确认目标类型
            str_target_id,  # 当前人工确认目标编号
            tuple_target[0],  # 当前人工确认目标内容
            tuple_target[1],  # 当前人工确认证据绑定
            str(dict_model.get("contract_version", "")),  # 人工摘要绑定的合同版本
        )

        # 内容或证据变化后旧人工决定失效。
        if dict_confirmation.get("target_hash") != str_expected_hash:

            # 要求依据当前事实重新确认。
            list_findings.append(
                build_blocker(
                    "REV005",
                    f"人工确认哈希过期:{str_target_type}:{str_target_id}",
                    "依据当前内容和证据重新确认",
                )
            )

            # 过期记录不能关闭人工确认门。
            continue

        # pending AI 即使记录 confirm 也不能形成实体结论。
        bool_pending_ai = bool(  # 当前确认是否指向待判断 AI 状态
            str_target_type == "ai_applicability"  # 当前目标属于 AI 适用性
            and isinstance(dict_model.get("rule_applicability"), Mapping)  # 规则容器有效
            and dict_model["rule_applicability"].get("ai_applicability") == "pending"  # AI 规则仍待判断
        )

        # 只有非 pending 目标的 confirm 才计入有效覆盖。
        if dict_confirmation.get("decision") == "confirm" and not bool_pending_ai:

            # 登记已由人工明确确认的目标。
            set_valid_targets.add((str_target_type, str_target_id))

    # 返回人工确认发现和有效目标。
    return list_findings, set_valid_targets

# 把集合名称归一为互不混用的代理或人工审查域。
def review_collection_domain(str_collection: str) -> str:
    """返回审查集合所属的身份域。

    参数：
    - `str_collection`：四类审查集合之一。

    返回：
    - `str`：`agent` 或 `human`。

    异常：
    - 无。
    """

    # 集合前缀是 schema 固定合同，不使用记录内容猜测域。
    return "agent" if str_collection.startswith("agent_") else "human"

# 验证一条活动或历史记录的方向和双向链接。
def validate_supersession_record(
    tuple_entry: tuple[str, str, bool, Mapping[str, Any]],
    dict_by_id: Mapping[str, tuple[str, bool, Mapping[str, Any]]],
) -> list[dict[str, str]]:
    """验证单条记录的 supersedes 双向闭包。

    参数：
    - `tuple_entry`：集合、身份字段、活动标志和记录。
    - `dict_by_id`：四个集合的全局身份索引。

    返回：
    - `list[dict[str, str]]`：当前记录的 REV015 findings。

    异常：
    - 无。
    """

    # 拆出集合角色和记录事实，后续链接检查不再重复索引。
    str_collection, str_id_key, bool_active, dict_record = tuple_entry  # 当前记录集合角色与事实

    # 当前身份用于双向链接的反向指针核对。
    str_record_id = str(dict_record.get(str_id_key, ""))  # 当前记录全局身份

    # supersedes 指向当前记录直接替代的历史父节点。
    obj_supersedes = dict_record.get("supersedes")  # 当前记录直接父身份

    # superseded_by 指向直接替代当前历史记录的后继节点。
    obj_superseded_by = dict_record.get("superseded_by")  # 当前记录直接后继身份

    # 收集当前记录全部方向和链接问题。
    list_findings: list[dict[str, str]] = []  # 当前记录 REV015 findings

    # 活动记录不得有后继，历史记录必须明确后继。
    if (bool_active and obj_superseded_by) or (
        not bool_active and not obj_superseded_by
    ):

        # 方向字段错误会破坏从活动记录反向重放的唯一性。
        list_findings.append(
            build_blocker(
                "REV015",
                f"supersession 方向无效:{str_record_id}",
                "活动记录不得有 superseded_by，历史记录必须有 superseded_by",
            )
        )

    # 代理与人工身份即使文本相同也不得跨域连接。
    str_domain = review_collection_domain(str_collection)  # 当前记录审查域

    # 存在历史父节点时必须核对状态、域、目标和反向指针。
    if obj_supersedes:

        # 全局索引定位被当前记录替代的直接父节点。
        tuple_parent = dict_by_id.get(str(obj_supersedes))  # 当前直接历史父节点

        # 父节点必须是同域同目标历史并反向指向当前身份。
        bool_parent_valid = (  # 当前父链接是否形成闭包
            tuple_parent is not None  # 父节点必须真实存在
            and not tuple_parent[1]  # supersedes 只能指向不可变历史
            and review_collection_domain(tuple_parent[0]) == str_domain  # 父节点不得跨审查域
            and tuple_parent[2].get("superseded_by") == str_record_id  # 父节点必须反向指回
            and tuple_parent[2].get("target_type") == dict_record.get("target_type")  # 目标类型稳定
            and tuple_parent[2].get("target_id") == dict_record.get("target_id")  # 目标身份稳定
        )

        # 任一父链接条件缺失都形成稳定审计 blocker。
        if not bool_parent_valid:

            # 错误定位当前记录，修复时同时检查父记录反向字段。
            list_findings.append(
                build_blocker(
                    "REV015",
                    f"supersedes 链未闭合:{str_record_id}",
                    "修复同域同目标的双向链接",
                )
            )

    # 历史记录的后继可以是下一历史节点或最终活动节点。
    if obj_superseded_by:

        # 全局索引定位直接替代当前记录的后继。
        tuple_child = dict_by_id.get(str(obj_superseded_by))  # 当前直接后继节点

        # 后继必须保持同域同目标并通过 supersedes 指回。
        bool_child_valid = (  # 当前后继链接是否形成闭包
            tuple_child is not None  # 后继节点必须真实存在
            and review_collection_domain(tuple_child[0]) == str_domain  # 后继不得跨审查域
            and tuple_child[2].get("supersedes") == str_record_id  # 后继必须指回当前节点
            and tuple_child[2].get("target_type") == dict_record.get("target_type")  # 后继目标类型稳定
            and tuple_child[2].get("target_id") == dict_record.get("target_id")  # 后继目标身份稳定
        )

        # 后继链接不闭合时不能证明不可变历史顺序。
        if not bool_child_valid:

            # 错误定位当前历史记录的后继字段。
            list_findings.append(
                build_blocker(
                    "REV015",
                    f"superseded_by 链未闭合:{str_record_id}",
                    "修复同域同目标的双向链接",
                )
            )

    # 返回当前记录的全部方向和双向链接问题。
    return list_findings

# 验证一个审查域内每个目标的全部历史均由活动节点反向可达。
def validate_history_reachability(
    str_domain: str,
    str_active_collection: str,
    str_history_collection: str,
    list_entries: list[tuple[str, str, bool, Mapping[str, Any]]],
    dict_by_id: Mapping[str, tuple[str, bool, Mapping[str, Any]]],
) -> list[dict[str, str]]:
    """验证同域历史链无分支、环和孤点。

    参数：
    - `str_domain`：`agent` 或 `human`。
    - `str_active_collection`：当前域活动集合名。
    - `str_history_collection`：当前域历史集合名。
    - `list_entries`：四个集合的结构化记录索引。
    - `dict_by_id`：全局记录身份索引。

    返回：
    - `list[dict[str, str]]`：当前域不可达历史 findings。

    异常：
    - 无。
    """

    # 活动节点是每条目标链唯一允许的末端。
    list_active = [
        dict_record  # 当前域活动记录
        for str_collection, _, _, dict_record in list_entries  # 遍历统一索引
        if str_collection == str_active_collection  # 只保留当前域活动集合
    ]  # 当前域全部活动记录

    # 历史节点必须全部出现在某条活动记录的反向链中。
    list_history = [
        dict_record  # 当前域历史记录
        for str_collection, _, _, dict_record in list_entries  # 扫描可能归档的全部记录
        if str_collection == str_history_collection  # 只保留当前域历史集合
    ]  # 当前域全部历史记录

    # 只对真实出现历史的目标执行可达性闭包。
    set_targets = {
        (
            str(dict_record.get("target_type", "")),  # 当前历史目标类型
            str(dict_record.get("target_id", "")),  # 当前历史目标身份
        )
        for dict_record in list_history  # 遍历当前域历史节点
    }  # 当前域需要验证历史链的目标集合

    # 初始化当前域可达性问题。
    list_findings: list[dict[str, str]] = []  # 当前域历史链 findings

    # 每个目标独立比较期望历史集合和反向遍历结果。
    for tuple_target in set_targets:

        # 同目标必须恰有一个活动末端。
        list_target_active = [
            dict_record  # 当前目标活动记录
            for dict_record in list_active  # 遍历当前域活动集合
            if (  # 当前活动坐标是否匹配待验证目标
                str(dict_record.get("target_type", "")),  # 当前活动目标类型
                str(dict_record.get("target_id", "")),  # 当前活动目标稳定身份
            )
            == tuple_target  # 只选择当前目标的活动末端
        ]  # 当前目标活动末端集合

        # 身份字段由审查域固定，禁止记录内容自行选择。
        str_id_key = (  # 当前域稳定身份字段
            "review_id" if str_domain == "agent" else "confirmation_id"  # 域对应身份键
        )

        # 汇总该目标全部历史身份作为反向遍历期望集合。
        set_target_history = {
            str(dict_record.get(str_id_key, ""))  # 当前历史记录身份
            for dict_record in list_history  # 遍历当前域历史集合
            if (  # 当前历史坐标是否匹配待验证目标
                str(dict_record.get("target_type", "")),  # 历史链的目标类型坐标
                str(dict_record.get("target_id", "")),  # 历史链的目标身份坐标
            )
            == tuple_target  # 只汇总当前目标的历史链
        }  # 当前目标全部历史身份

        # 访问集合同时用于检测环并避免无限循环。
        set_reached: set[str] = set()  # 从活动末端反向到达的历史身份

        # 多个或缺失活动末端时不猜测起点，最终集合比较会失败。
        if len(list_target_active) == 1:

            # 第一条反向边由活动记录 supersedes 声明。
            obj_parent_id = list_target_active[0].get("supersedes")  # 当前反向遍历父身份

            # 逐跳访问未见过的历史父节点，环会自然停止。
            while obj_parent_id and str(obj_parent_id) not in set_reached:

                # 规范身份后同时用于索引和访问集合。
                str_parent_id = str(obj_parent_id)  # 当前历史父身份

                # 全局索引保留父节点的状态和完整记录。
                tuple_parent = dict_by_id.get(str_parent_id)  # 当前历史父节点

                # 缺失或意外活动父节点使链在此处失败关闭。
                if tuple_parent is None or tuple_parent[1]:

                    # 停止遍历并由集合不相等报告不可达历史。
                    break

                # 登记当前历史节点，防止后续环路重复访问。
                set_reached.add(str_parent_id)

                # 沿当前历史节点的 supersedes 继续向更早版本回溯。
                obj_parent_id = tuple_parent[2].get("supersedes")  # 下一历史父身份

        # 分支、环、孤点或活动末端异常都会造成集合不相等。
        if set_reached != set_target_history:

            # 一个目标形成一个稳定 finding，避免对同一坏图重复刷屏。
            list_findings.append(
                build_blocker(
                    "REV015",
                    f"历史链存在分支、环或孤点:{str_domain}:{tuple_target}",
                    "从唯一活动记录反向连接全部同目标历史",
                )
            )

    # 返回当前审查域的全部可达性问题。
    return list_findings

# 验证嵌入式语义审查的覆盖维度、裁决和内容哈希。
# 验证四个记录集合的全局身份、活动目标和 supersession 闭包。
def validate_record_audit_invariants(
    obj_review: Mapping[str, Any],
) -> list[dict[str, str]]:
    """验证审查记录跨集合审计不变量。

    参数：
    - `obj_review`：Model 4 语义审查根对象。

    返回：
    - `list[dict[str, str]]`：全局身份、活动目标和历史闭包 findings。

    异常：
    - 无。
    """

    # 集合名决定可信身份键和 active/history 角色，记录内容不能自行改写所属域。
    tuple_collections = (
        ("agent_reviews", "review_id", True),  # 代理域唯一活动末端
        ("agent_review_history", "review_id", False),  # 代理域不可变历史节点
        ("human_confirmations", "confirmation_id", True),  # 人工域唯一活动末端
        ("human_confirmation_history", "confirmation_id", False),  # 人工域不可变历史节点
    )  # 四集合角色与身份字段合同

    # 统一索引携带可信集合角色，后续图检查无需相信记录自报的 active/history 状态。
    list_entries: list[tuple[str, str, bool, Mapping[str, Any]]] = []  # 带审查域角色的图节点

    # schema 负责容器类型错误，本函数只在可解释集合上推导跨节点不变量。
    for str_collection, str_id_key, bool_active in tuple_collections:

        # 缺失集合按空图处理，错误类型则保留给结构门禁报告。
        obj_records = obj_review.get(str_collection, [])  # 当前角色对应的原始节点容器

        # 非数组容器无法形成可靠图节点，参与推导会制造误导性链路发现。
        if not isinstance(obj_records, list):

            # 其他合法集合仍需接受全局身份与历史闭包检查。
            continue

        # 集合合同随节点进入统一索引，防止后续从可篡改字段猜测审查域。
        list_entries.extend(
            (str_collection, str_id_key, bool_active, dict_record)
            for dict_record in obj_records
            if isinstance(dict_record, Mapping)
        )

    # 身份唯一性跨代理、人工、活动和历史四个集合生效，避免链接命中错误域。
    list_ids = [
        str(dict_record.get(str_id_key))  # supersession 查找使用的规范身份
        for _, str_id_key, _, dict_record in list_entries  # 全部可解释审计节点
        if dict_record.get(str_id_key)  # 缺失身份由结构门禁独立报告
    ]  # 全审查域共享的身份空间

    # 三类图不变量共享同一发现序列，保持规则阶段的确定性顺序。
    list_findings: list[dict[str, str]] = []  # REV013 至 REV015 的审计发现

    # 身份碰撞会让 supersession 引用产生歧义，因此不能按集合局部放宽。
    if len(list_ids) != len(set(list_ids)):

        # REV013 明确覆盖全部审查域，而不是只检查当前活动集合。
        list_findings.append(build_blocker("REV013", "审查记录 ID 未保持全局唯一", "为每条活动和历史记录分配唯一身份"))

    # 每个审查域只能保留一个同目标 active，旧版本必须进入对应 history。
    for str_collection in ("agent_reviews", "human_confirmations"):

        # 目标坐标忽略审查内容，只判断 active 末端是否唯一。
        list_targets = [
            (str(dict_record.get("target_type", "")), str(dict_record.get("target_id", "")))  # supersession 链的稳定目标坐标
            for str_name, _, bool_active, dict_record in list_entries  # 带可信角色的统一图索引
            if str_name == str_collection and bool_active  # 当前审查域的 active 末端
        ]  # 当前域需要保持唯一的活动目标

        # 重复坐标表示旧 active 未归档，历史链因此存在多个末端。
        if len(list_targets) != len(set(list_targets)):

            # REV014 在进入链接遍历前固定唯一活动末端合同。
            list_findings.append(build_blocker("REV014", f"活动目标存在重复记录:{str_collection}", "同一目标只保留一条活动记录"))

    # 图索引覆盖四集合，链接校验才能同时识别跨域引用和错误方向。
    dict_by_id = {
        str(dict_record.get(str_id_key)): (  # supersession 引用的全局查找键
            str_collection,  # 节点所属代理域或人工域
            bool_active,  # 节点在链中的末端或历史角色
            dict_record,  # 目标坐标与双向链接事实
        )

        # 无身份记录由结构门禁阻断，不能作为其他节点的合法链接目标。
        for str_collection, str_id_key, bool_active, dict_record in list_entries  # 四集合中的可解释节点
        if dict_record.get(str_id_key)  # 可参与全局引用解析的节点
    }  # 同时保留身份、域、方向和记录事实的图索引

    # 每条直接边必须同域同目标并双向指回，active/history 字段方向也必须匹配。
    for tuple_entry in list_entries:

        # 节点级验证先封闭局部边，避免可达性遍历掩盖错误父子关系。
        list_findings.extend(
            validate_supersession_record(tuple_entry, dict_by_id)
        )

    # 代理域与人工域分别从唯一 active 沿 supersedes 反向覆盖全部 history。
    for str_domain, str_active_collection, str_history_collection in (
        ("agent", "agent_reviews", "agent_review_history"),
        ("human", "human_confirmations", "human_confirmation_history"),
    ):

        # 域级闭包拒绝孤点、分支和环，即使每条局部边看似双向完整。
        list_findings.extend(
            validate_history_reachability(
                str_domain,
                str_active_collection,
                str_history_collection,

                # 统一节点序列确定期望历史集合，全局索引解析每一跳父节点。
                list_entries,
                dict_by_id,
            )
        )

    # 保留各不变量检查的追加顺序，便于调用方按规则执行路径定位审计缺口。
    return list_findings

# 汇总模型内代理审查、人工确认及其审计历史的语义问题。
